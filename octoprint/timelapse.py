# coding=utf-8
import logging

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

from octoprint.settings import settings
import octoprint.util as util

import os
import threading
import urllib
import time
import subprocess
import fnmatch
import datetime

import sys

def getFinishedTimelapses():
	files = []
	basedir = settings().getBaseFolder("timelapse")
	for osFile in os.listdir(basedir):
		if not fnmatch.fnmatch(osFile, "*.mpg"):
			continue
		statResult = os.stat(os.path.join(basedir, osFile))
		files.append({
			"name": osFile,
			"size": util.getFormattedSize(statResult.st_size),
			"bytes": statResult.st_size,
			"date": util.getFormattedDateTime(datetime.datetime.fromtimestamp(statResult.st_ctime))
		})
	return files

class Timelapse(object):
	def __init__(self):
		self._logger = logging.getLogger(__name__)

		self._imageNumber = None
		self._inTimelapse = False
		self._gcodeFile = None

		self._captureDir = settings().getBaseFolder("timelapse_tmp")
		self._movieDir = settings().getBaseFolder("timelapse")
		self._snapshotUrl = settings().get(["webcam", "snapshot"])

		self._renderThread = None
		self._captureMutex = threading.Lock()

	def onPrintjobStarted(self, gcodeFile):
		self.startTimelapse(gcodeFile)

	def onPrintjobStopped(self):
		self.stopTimelapse()

	def onPrintjobProgress(self, oldPos, newPos, percentage):
		pass

	def onZChange(self, oldZ, newZ):
		pass

	def startTimelapse(self, gcodeFile):
		self._logger.debug("Starting timelapse for %s" % gcodeFile)
		self.cleanCaptureDir()

		self._imageNumber = 0
		self._inTimelapse = True
		self._gcodeFile = os.path.basename(gcodeFile)

	def stopTimelapse(self):
		self._logger.debug("Stopping timelapse")
		self._renderThread = threading.Thread(target=self._createMovie)
		self._renderThread.daemon = True
		self._renderThread.start()

		self._imageNumber = None
		self._inTimelapse = False

	def captureImage(self):
		if self._captureDir is None:
			self._logger.warn("Cannot capture image, capture directory is unset")
			return

		with self._captureMutex:
			filename = os.path.join(self._captureDir, "tmp_%05d.jpg" % (self._imageNumber))
			self._imageNumber += 1
		self._logger.debug("Capturing image to %s" % filename)

		captureThread = threading.Thread(target=self._captureWorker, kwargs={"filename": filename})
		captureThread.daemon = True
		captureThread.start()

	def _captureWorker(self, filename):
		urllib.urlretrieve(self._snapshotUrl, filename)
		self._logger.debug("Image %s captured from %s" % (filename, self._snapshotUrl))

	def _createMovie(self):
		ffmpeg = settings().get(["webcam", "ffmpeg"])
		bitrate = settings().get(["webcam", "bitrate"])
		if ffmpeg is None or bitrate is None:
			self._logger.warn("Cannot create movie, path to ffmpeg is unset")
			return

		input = os.path.join(self._captureDir, "tmp_%05d.jpg")
		output = os.path.join(self._movieDir, "%s_%s.mpg" % (os.path.splitext(self._gcodeFile)[0], time.strftime("%Y%m%d%H%M%S")))

		# prepare ffmpeg command
		command = [
			ffmpeg, '-i', input, '-vcodec', 'mpeg2video', '-pix_fmt', 'yuv420p', '-r', '25', '-y', '-b:v', bitrate,
			'-f', 'vob']

		# add watermark if configured
		if settings().getBoolean(["webcam", "watermark"]):
			watermark = os.path.join(os.path.dirname(__file__), "static", "img", "watermark.png")
			if sys.platform == "win32":
				# Because ffmpeg hiccups on windows' drive letters and backslashes we have to give the watermark
				# path a special treatment. Yeah, I couldn't believe it either...
				watermark = watermark.replace("\\", "/").replace(":", "\\\\:")
			command.extend(['-vf', 'movie=%s [wm]; [in][wm] overlay=10:main_h-overlay_h-10 [out]' % watermark])

		# finalize command with output file
		command.append(output)
		subprocess.call(command)
		self._logger.debug("Rendering movie to %s" % output)

	def cleanCaptureDir(self):
		if not os.path.isdir(self._captureDir):
			self._logger.warn("Cannot clean capture directory, it is unset")
			return

		for filename in os.listdir(self._captureDir):
			if not fnmatch.fnmatch(filename, "*.jpg"):
				continue
			os.remove(os.path.join(self._captureDir, filename))

class ZTimelapse(Timelapse):
	def __init__(self):
		Timelapse.__init__(self)
		self._logger.debug("ZTimelapse initialized")

	def onZChange(self, oldZ, newZ):
		self._logger.debug("Z change detected, capturing image")
		self.captureImage()

class TimedTimelapse(Timelapse):
	def __init__(self, interval=1):
		Timelapse.__init__(self)

		self._interval = interval
		if self._interval < 1:
			self._interval = 1 # force minimum interval of 1s

		self._timerThread = None

		self._logger.debug("TimedTimelapse initialized")

	def interval(self):
		return self._interval

	def onPrintjobStarted(self, filename):
		Timelapse.onPrintjobStarted(self, filename)
		if self._timerThread is not None:
			return

		self._timerThread = threading.Thread(target=self.timerWorker)
		self._timerThread.daemon = True
		self._timerThread.start()

	def timerWorker(self):
		self._logger.debug("Starting timer for interval based timelapse")
		while self._inTimelapse:
			self.captureImage()
			time.sleep(self._interval)
