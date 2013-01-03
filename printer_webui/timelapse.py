# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

from printer_webui.settings import settings

import os
import threading
import urllib
import time
import subprocess
import glob

class Timelapse(object):
	def __init__(self):
		self.imageNumber = None
		self.inTimelapse = False
		self.gcodeFile = None

		self.captureDir = settings().getBaseFolder("timelapse_tmp")
		self.movieDir = settings().getBaseFolder("timelapse")
		self.snapshotUrl = settings().get("webcam", "snapshot")

	def onPrintjobStarted(self, gcodeFile):
		self.startTimelapse(gcodeFile)

	def onPrintjobStopped(self):
		self.stopTimelapse()

	def onPrintjobProgress(self, oldPos, newPos, percentage):
		pass

	def onZChange(self, oldZ, newZ):
		pass

	def startTimelapse(self, gcodeFile):
		self.cleanCaptureDir()

		self.imageNumber = 0
		self.inTimelapse = True
		self.gcodeFile = os.path.basename(gcodeFile)

	def stopTimelapse(self):
		self.createMovie()

		self.imageNumber = None
		self.inTimelapse = False

	def captureImage(self):
		if self.captureDir is None:
			return

		filename = os.path.join(self.captureDir, "tmp_%05d.jpg" % (self.imageNumber))
		self.imageNumber += 1;

		captureThread = threading.Thread(target=self.captureWorker, kwargs={"filename": filename})
		captureThread.start()

	def captureWorker(self, filename):
		urllib.urlretrieve(self.snapshotUrl, filename)

	def createMovie(self):
		ffmpeg = settings().get("webcam", "ffmpeg")
		if ffmpeg is None:
			return

		input = os.path.join(self.captureDir, "tmp_%05d.jpg")
		output = os.path.join(self.movieDir, "%s_%s.mpg" % (os.path.splitext(self.gcodeFile)[0], time.strftime("%Y%m%d%H%M%S")))
		subprocess.call([
			ffmpeg, '-i', input, '-vcodec', 'mpeg2video', '-pix_fmt', 'yuv420p', '-r', '25', '-y',
			 '-b:v', '1500k', '-f', 'vob', output
		])

	def cleanCaptureDir(self):
		if not os.path.isdir(self.captureDir):
			return

		for filename in glob.glob(os.path.join(self.captureDir, "*.jpg")):
			os.remove(filename)

class ZTimelapse(Timelapse):
	def __init__(self):
		Timelapse.__init__(self)

	def onZChange(self, oldZ, newZ):
		self.captureImage()

class TimedTimelapse(Timelapse):
	def __init__(self, interval=1):
		Timelapse.__init__(self)

		self.interval = interval
		if self.interval < 1:
			self.interval = 1 # force minimum interval of 1s

		self.timerThread = None

	def onPrintjobStarted(self):
		Timelapse.onPrintjobStarted(self)
		if self.timerThread is not None:
			return

		self.timerThread = threading.Thread(target=self.timerWorker)
		self.timerThread.start()

	def timerWorker(self):
		while self.inTimelapse:
			self.captureImage()
			time.sleep(self.interval)
