# coding=utf-8

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

import logging
import os
import threading
import urllib
import time
import subprocess
import fnmatch
import datetime
import sys

import octoprint.util as util

from octoprint.settings import settings
from octoprint.events import eventManager

# currently configured timelapse
current = None


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

validTimelapseTypes = ["off", "timed", "zchange"]

updateCallbacks = []


def registerCallback(callback):
	if not callback in updateCallbacks:
		updateCallbacks.append(callback)


def unregisterCallback(callback):
	if callback in updateCallbacks:
		updateCallbacks.remove(callback)


def notifyCallbacks(timelapse):
	if timelapse is None:
		config = None
	else:
		config = timelapse.configData()
	for callback in updateCallbacks:
		try: callback.sendTimelapseConfig(config)
		except: pass


def configureTimelapse(config=None, persist=False):
	global current

	if config is None:
		config = settings().get(["webcam", "timelapse"])

	if current is not None:
		current.unload()

	type = config["type"]
	if type is None or "off" == type:
		current = None
	elif "zchange" == type:
		current = ZTimelapse()
	elif "timed" == type:
		interval = 10
		if "options" in config and "interval" in config["options"]:
			interval = config["options"]["interval"]
		current = TimedTimelapse(interval)

	notifyCallbacks(current)

	if persist:
		settings().set(["webcam", "timelapse"], config)
		settings().save()


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

		# subscribe events
		eventManager().subscribe("PrintStarted", self.onPrintStarted)
		eventManager().subscribe("PrintFailed", self.onPrintDone)
		eventManager().subscribe("PrintDone", self.onPrintDone)
		eventManager().subscribe("PrintResumed", self.onPrintResumed)
		for (event, callback) in self.eventSubscriptions():
			eventManager().subscribe(event, callback)

	def unload(self):
		if self._inTimelapse:
			self.stopTimelapse(doCreateMovie=False)

		# unsubscribe events
		eventManager().unsubscribe("PrintStarted", self.onPrintStarted)
		eventManager().unsubscribe("PrintFailed", self.onPrintDone)
		eventManager().unsubscribe("PrintDone", self.onPrintDone)
		eventManager().unsubscribe("PrintResumed", self.onPrintResumed)
		for (event, callback) in self.eventSubscriptions():
			eventManager().unsubscribe(event, callback)

	def onPrintStarted(self, event, payload):
		"""
		Override this to perform additional actions upon start of a print job.
		"""
		self.startTimelapse(payload)

	def onPrintDone(self, event, payload):
		"""
		Override this to perform additional actions upon the stop of a print job.
		"""
		self.stopTimelapse()

	def onPrintResumed(self, event, payload):
		"""
		Override this to perform additional actions upon the pausing of a print job.
		"""
		if not self._inTimelapse:
			self.startTimelapse(payload)

	def eventSubscriptions(self):
		"""
		Override this method to subscribe to additional events by returning an array of (event, callback) tuples.

		Events that are already subscribed:
		  * PrintStarted - self.onPrintStarted
		  * PrintResumed - self.onPrintResumed
		  * PrintFailed - self.onPrintDone
		  * PrintDone - self.onPrintDone
		"""
		return []

	def configData(self):
		"""
		Override this method to return the current timelapse configuration data. The data should have the following
		form:

		    type: "<type of timelapse>",
		    options: { <additional options> }
		"""
		return None

	def startTimelapse(self, gcodeFile):
		self._logger.debug("Starting timelapse for %s" % gcodeFile)
		self.cleanCaptureDir()

		self._imageNumber = 0
		self._inTimelapse = True
		self._gcodeFile = os.path.basename(gcodeFile)

	def stopTimelapse(self, doCreateMovie=True):
		self._logger.debug("Stopping timelapse")

		if doCreateMovie:
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
		eventManager().fire("CaptureStart", filename);
		urllib.urlretrieve(self._snapshotUrl, filename)
		self._logger.debug("Image %s captured from %s" % (filename, self._snapshotUrl))
		eventManager().fire("CaptureDone", filename);

	def _createMovie(self):
		ffmpeg = settings().get(["webcam", "ffmpeg"])
		bitrate = settings().get(["webcam", "bitrate"])
		if ffmpeg is None or bitrate is None:
			self._logger.warn("Cannot create movie, path to ffmpeg or desired bitrate is unset")
			return

		input = os.path.join(self._captureDir, "tmp_%05d.jpg")
		output = os.path.join(self._movieDir, "%s_%s.mpg" % (os.path.splitext(self._gcodeFile)[0], time.strftime("%Y%m%d%H%M%S")))

		# prepare ffmpeg command
		command = [
			ffmpeg, '-i', input, '-vcodec', 'mpeg2video', '-pix_fmt', 'yuv420p', '-r', '25', '-y', '-b:v', bitrate,
			'-f', 'vob']

		filters = []

		# flip video if configured
		if settings().getBoolean(["webcam", "flipH"]):
			filters.append('hflip')
		if settings().getBoolean(["webcam", "flipV"]):
			filters.append('vflip')

		# add watermark if configured
		watermarkFilter = None
		if settings().getBoolean(["webcam", "watermark"]):
			watermark = os.path.join(os.path.dirname(__file__), "static", "img", "watermark.png")
			if sys.platform == "win32":
				# Because ffmpeg hiccups on windows' drive letters and backslashes we have to give the watermark
				# path a special treatment. Yeah, I couldn't believe it either...
				watermark = watermark.replace("\\", "/").replace(":", "\\\\:")

			watermarkFilter = "movie=%s [wm]; [%%(inputName)s][wm] overlay=10:main_h-overlay_h-10" % watermark

		filterstring = None
		if len(filters) > 0:
			if watermarkFilter is not None:
				filterstring = "[in] %s [postprocessed]; %s [out]" % (",".join(filters), watermarkFilter % {"inputName": "postprocessed"})
			else:
				filterstring = "[in] %s [out]" % ",".join(filters)
		elif watermarkFilter is not None:
			filterstring = watermarkFilter % {"inputName": "in"} + " [out]"

		if filterstring is not None:
			self._logger.debug("Applying videofilter chain: %s" % filterstring)
			command.extend(["-vf", filterstring])

		# finalize command with output file
		self._logger.debug("Rendering movie to %s" % output)
		command.append(output)
		try:
			subprocess.check_call(command)
			eventManager().fire("MovieDone", output)
		except subprocess.CalledProcessError as (e):
			self._logger.warn("Could not render movie, got return code %r" % e.returncode)

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

	def eventSubscriptions(self):
		return [
			("ZChange", self._onZChange)
		]

	def configData(self):
		return {
			"type": "zchange"
		}

	def _onZChange(self, event, payload):
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

	def configData(self):
		return {
			"type": "timed",
			"options": {
				"interval": self._interval
			}
		}

	def onPrintStarted(self, event, payload):
		Timelapse.onPrintStarted(self, event, payload)
		if self._timerThread is not None:
			return

		self._timerThread = threading.Thread(target=self._timerWorker)
		self._timerThread.daemon = True
		self._timerThread.start()

	def onPrintDone(self, event, payload):
		Timelapse.onPrintDone(self, event, payload)
		self._timerThread = None

	def _timerWorker(self):
		self._logger.debug("Starting timer for interval based timelapse")
		while self._inTimelapse:
			self.captureImage()
			time.sleep(self._interval)
