# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

import os
import Queue
import threading
import datetime
import yaml
import time
import logging
import octoprint.util as util
import octoprint.util.gcodeInterpreter as gcodeInterpreter

from octoprint.settings import settings
from octoprint.events import eventManager

from werkzeug.utils import secure_filename

GCODE_EXTENSIONS = ["gcode", "gco", "g"]
STL_EXTENSIONS = ["stl"]
SUPPORTED_EXTENSIONS = GCODE_EXTENSIONS + STL_EXTENSIONS

def isGcodeFileName(filename):
	"""Simple helper to determine if a filename has the .gcode extension.

	:param filename: :class: `str`

	:returns boolean:
	"""
	return "." in filename and filename.rsplit(".", 1)[1].lower() in GCODE_EXTENSIONS


def isSTLFileName(filename):
	"""Simple helper to determine if a filename has the .stl extension.

	:param filename: :class: `str`

	:returns boolean:
	"""
	return "." in filename and filename.rsplit(".", 1)[1].lower() in STL_EXTENSIONS


def genGcodeFileName(filename):
	if not filename:
		return None

	name, ext = filename.rsplit(".", 1)
	return name + ".gcode"


def genStlFileName(filename):
	if not filename:
		return None

	name, ext = filename.rsplit(".", 1)
	return name + ".stl"


class GcodeManager:
	def __init__(self):
		self._logger = logging.getLogger(__name__)

		self._settings = settings()

		self._uploadFolder = self._settings.getBaseFolder("uploads")

		self._callbacks = []

		self._metadata = {}
		self._metadataDirty = False
		self._metadataFile = os.path.join(self._uploadFolder, "metadata.yaml")
		self._metadataTempFile = os.path.join(self._uploadFolder, "metadata.yaml.tmp")
		self._metadataFileAccessMutex = threading.Lock()

		self._metadataAnalyzer = MetadataAnalyzer(getPathCallback=self.getAbsolutePath, loadedCallback=self._onMetadataAnalysisFinished)

		self._loadMetadata()
		self._processAnalysisBacklog()

	def _processAnalysisBacklog(self):
		for osFile in os.listdir(self._uploadFolder):
			filename = self._getBasicFilename(osFile)
			if not isGcodeFileName(filename):
				continue

			absolutePath = self.getAbsolutePath(filename)
			if absolutePath is None:
				continue

			fileData = self.getFileData(filename)
			if fileData is not None and "gcodeAnalysis" in fileData.keys():
				continue

			self._metadataAnalyzer.addFileToBacklog(filename)

	def _onMetadataAnalysisFinished(self, filename, gcode):
		if filename is None or gcode is None:
			return

		basename = os.path.basename(filename)

		absolutePath = self.getAbsolutePath(basename)
		if absolutePath is None:
			return

		analysisResult = {}
		dirty = False
		if gcode.totalMoveTimeMinute:
			analysisResult["estimatedPrintTime"] = util.getFormattedTimeDelta(datetime.timedelta(minutes=gcode.totalMoveTimeMinute))
			dirty = True
		if gcode.extrusionAmount:
			analysisResult["filament"] = "%.2fm" % (gcode.extrusionAmount / 1000)
			if gcode.calculateVolumeCm3():
				analysisResult["filament"] += " / %.2fcm³" % gcode.calculateVolumeCm3()
			dirty = True

		if dirty:
			metadata = self.getFileMetadata(basename)
			metadata["gcodeAnalysis"] = analysisResult
			self._metadata[basename] = metadata
			self._metadataDirty = True
			self._saveMetadata()

	def _loadMetadata(self):
		if os.path.exists(self._metadataFile) and os.path.isfile(self._metadataFile):
			with self._metadataFileAccessMutex:
				with open(self._metadataFile, "r") as f:
					self._metadata = yaml.safe_load(f)
		if self._metadata is None:
			self._metadata = {}

	def _saveMetadata(self, force=False):
		if not self._metadataDirty and not force:
			return

		with self._metadataFileAccessMutex:
			with open(self._metadataTempFile, "wb") as f:
				yaml.safe_dump(self._metadata, f, default_flow_style=False, indent="    ", allow_unicode=True)
				self._metadataDirty = False
			util.safeRename(self._metadataTempFile, self._metadataFile)

		self._loadMetadata()
		self._sendUpdateTrigger("gcodeFiles")

	def _getBasicFilename(self, filename):
		if filename.startswith(self._uploadFolder):
			return filename[len(self._uploadFolder + os.path.sep):]
		else:
			return filename

	#~~ callback handling

	def registerCallback(self, callback):
		self._callbacks.append(callback)

	def unregisterCallback(self, callback):
		if callback in self._callbacks:
			self._callbacks.remove(callback)

	def _sendUpdateTrigger(self, type):
		for callback in self._callbacks:
			try: callback.sendUpdateTrigger(type)
			except: pass

	#~~ file handling

	def addFile(self, file, destination):
		from octoprint.filemanager.destinations import FileDestinations

		if not file or not destination:
			return None, True

		curaEnabled = self._settings.getBoolean(["cura", "enabled"])
		filename = file.filename

		absolutePath = self.getAbsolutePath(filename, mustExist=False)
		gcode = isGcodeFileName(filename)

		if absolutePath is None or (not curaEnabled and not gcode):
			return None, True

		file.save(absolutePath)

		if gcode:
			return self.processGcode(absolutePath), True
		else:
			local = (destination == FileDestinations.LOCAL)
			if curaEnabled and isSTLFileName(filename) and local:
				self.processStl(absolutePath)
			return filename, False


	def getFutureFileName(self, file):
		if not file:
			return None

		absolutePath = self.getAbsolutePath(file.filename, mustExist=False)
		if absolutePath is None:
			return None

		return self._getBasicFilename(absolutePath)


	def processStl(self, absolutePath):
		from octoprint.slicers.cura import CuraFactory

		cura = CuraFactory.create_slicer()
		gcodePath = genGcodeFileName(absolutePath)
		config = self._settings.get(["cura", "config"])

		slicingStart = time.time()
		def stlProcessed(stlPath, gcodePath, error=None):
			if error:
				eventManager().fire("SlicingFailed", {"stl": self._getBasicFilename(stlPath), "gcode": self._getBasicFilename(gcodePath), "reason": error})
				if os.path.exists(stlPath):
					os.remove(stlPath)
			else:
				slicingStop = time.time()
				eventManager().fire("SlicingDone", {"stl": self._getBasicFilename(stlPath), "gcode": self._getBasicFilename(gcodePath), "time": "%.2f" % (slicingStop - slicingStart)})
				self.processGcode(gcodePath)

		eventManager().fire("SlicingStarted", {"stl": self._getBasicFilename(absolutePath), "gcode": self._getBasicFilename(gcodePath)})
		cura.process_file(config, gcodePath, absolutePath, stlProcessed, [absolutePath, gcodePath])


	def processGcode(self, absolutePath):
		if absolutePath is None:
			return None

		filename = self._getBasicFilename(absolutePath)

		if filename in self._metadata.keys():
			# delete existing metadata entry, since the file is going to get overwritten
			del self._metadata[filename]
			self._metadataDirty = True
			self._saveMetadata()

		self._metadataAnalyzer.addFileToQueue(os.path.basename(absolutePath))

		return filename 

	def getFutureFilename(self, file):
		if not file:
			return None

		absolutePath = self.getAbsolutePath(file.filename, mustExist=False)
		if absolutePath is None:
			return None

		return self._getBasicFilename(absolutePath)

	def removeFile(self, filename):
		filename = self._getBasicFilename(filename)
		absolutePath = self.getAbsolutePath(filename)
		stlPath = genStlFileName(absolutePath)

		if absolutePath is None:
			return

		os.remove(absolutePath)
		if os.path.exists(stlPath):
			os.remove(stlPath)

		if filename in self._metadata.keys():
			del self._metadata[filename]
			self._metadataDirty = True
			self._saveMetadata()

	def getAbsolutePath(self, filename, mustExist=True):
		"""
		Returns the absolute path of the given filename in the correct upload folder.

		Ensures that the file
		<ul>
		  <li>has any of the extensions listed in SUPPORTED_EXTENSIONS</li>
		  <li>exists and is a file (not a directory) if "mustExist" is set to True</li>
		</ul>

		@param filename the name of the file for which to determine the absolute path
		@param mustExist if set to true, the method also checks if the file exists and is a file
		@return the absolute path of the file or None if the file is not valid
		"""
		filename = self._getBasicFilename(filename)

		if not util.isAllowedFile(filename.lower(), set(SUPPORTED_EXTENSIONS)):
			return None

		# TODO: detect which type of file and add in the extra folder portion 
		secure = os.path.join(self._uploadFolder, secure_filename(self._getBasicFilename(filename)))
		if mustExist and (not os.path.exists(secure) or not os.path.isfile(secure)):
			return None

		return secure

	def getAllFileData(self):
		files = []
		for osFile in os.listdir(self._uploadFolder):
			fileData = self.getFileData(osFile)
			if fileData is not None:
				files.append(fileData)
		return files

	def getFileData(self, filename):
		if not filename:
			return

		filename = self._getBasicFilename(filename)

		# TODO: Make this more robust when STLs will be viewable from the client
		if isSTLFileName(filename):
			return
	
		absolutePath = self.getAbsolutePath(filename)
		if absolutePath is None:
			return None

		statResult = os.stat(absolutePath)
		fileData = {
			"name": filename,
			"size": util.getFormattedSize(statResult.st_size),
			"bytes": statResult.st_size,
			"date": util.getFormattedDateTime(datetime.datetime.fromtimestamp(statResult.st_ctime))
		}

		# enrich with additional metadata from analysis if available
		if filename in self._metadata.keys():
			for key in self._metadata[filename].keys():
				if key == "prints":
					val = self._metadata[filename][key]
					formattedLast = None
					if "last" in val and val["last"] is not None:
						formattedLast = {
							"date": util.getFormattedDateTime(datetime.datetime.fromtimestamp(val["last"]["date"])),
							"success": val["last"]["success"]
						}
					formattedPrints = {
						"success": val["success"],
						"failure": val["failure"],
						"last": formattedLast
					}
					fileData["prints"] = formattedPrints
				else:
					fileData[key] = self._metadata[filename][key]

		return fileData

	def getFileMetadata(self, filename):
		filename = self._getBasicFilename(filename)
		if filename in self._metadata.keys():
			return self._metadata[filename]
		else:
			return {
				"prints": {
					"success": 0,
					"failure": 0,
					"last": None
				}
			}

	def setFileMetadata(self, filename, metadata):
		filename = self._getBasicFilename(filename)
		self._metadata[filename] = metadata
		self._metadataDirty = True

	#~~ print job data

	def printSucceeded(self, filename):
		filename = self._getBasicFilename(filename)
		absolutePath = self.getAbsolutePath(filename)
		if absolutePath is None:
			return

		metadata = self.getFileMetadata(filename)
		metadata["prints"]["success"] += 1
		metadata["prints"]["last"] = {
			"date": time.time(),
			"success": True
		}
		self.setFileMetadata(filename, metadata)
		self._saveMetadata()

	def printFailed(self, filename):
		filename = self._getBasicFilename(filename)
		absolutePath = self.getAbsolutePath(filename)
		if absolutePath is None:
			return

		metadata = self.getFileMetadata(filename)
		metadata["prints"]["failure"] += 1
		metadata["prints"]["last"] = {
			"date": time.time(),
			"success": False
		}
		self.setFileMetadata(filename, metadata)
		self._saveMetadata()

	def changeLastPrintSuccess(self, filename, succeeded):
		filename = self._getBasicFilename(filename)
		absolutePath = self.getAbsolutePath(filename)
		if absolutePath is None:
			return

		metadata = self.getFileMetadata(filename)
		if metadata is None:
			return

		if "prints" in metadata.keys():
			if "last" in metadata.keys() and metadata["prints"]["last"] is not None:
				currentSucceeded = metadata["prints"]["last"]["success"]
				if currentSucceeded != succeeded:
					metadata["prints"]["last"]["success"] = succeeded
					if currentSucceeded:
						# last print job was counted as success but actually failed
						metadata["prints"]["success"] -= 1
						metadata["prints"]["failure"] += 1
					else:
						# last print job was counted as a failure but actually succeeded
						metadata["prints"]["success"] += 1
						metadata["prints"]["failure"] -= 1
					self.setFileMetadata(filename, metadata)
					self._saveMetadata()

	#~~ analysis control

	def pauseAnalysis(self):
		self._metadataAnalyzer.pause()

	def resumeAnalysis(self):
		self._metadataAnalyzer.resume()

class MetadataAnalyzer:
	def __init__(self, getPathCallback, loadedCallback):
		self._logger = logging.getLogger(__name__)

		self._getPathCallback = getPathCallback
		self._loadedCallback = loadedCallback

		self._active = threading.Event()
		self._active.set()

		self._currentFile = None
		self._currentProgress = None

		self._queue = Queue.PriorityQueue()
		self._gcode = None

		self._worker = threading.Thread(target=self._work)
		self._worker.daemon = True
		self._worker.start()

	def addFileToQueue(self, filename):
		self._logger.debug("Adding file %s to analysis queue (high priority)" % filename)
		self._queue.put((0, filename))

	def addFileToBacklog(self, filename):
		self._logger.debug("Adding file %s to analysis backlog (low priority)" % filename)
		self._queue.put((100, filename))

	def working(self):
		return self.isActive() and not (self._queue.empty() and self._currentFile is None)

	def isActive(self):
		return self._active.is_set()

	def pause(self):
		self._logger.debug("Pausing Gcode analyzer")
		self._active.clear()
		if self._gcode is not None:
			self._logger.debug("Aborting running analysis, will restart when Gcode analyzer is resumed")
			self._gcode.abort()

	def resume(self):
		self._logger.debug("Resuming Gcode analyzer")
		self._active.set()

	def _work(self):
		aborted = None
		while True:
			self._active.wait()

			if aborted is not None:
				filename = aborted
				aborted = None
				self._logger.debug("Got an aborted analysis job for file %s, processing this instead of first item in queue" % filename)
			else:
				(priority, filename) = self._queue.get()
				self._logger.debug("Processing file %s from queue (priority %d)" % (filename, priority))

			try:
				self._analyzeGcode(filename)
				self._queue.task_done()
			except gcodeInterpreter.AnalysisAborted:
				aborted = filename
				self._logger.debug("Running analysis of file %s aborted" % filename)

	def _analyzeGcode(self, filename):
		path = self._getPathCallback(filename)
		if path is None or not os.path.exists(path):
			return

		self._currentFile = filename
		self._currentProgress = 0

		try:
			self._logger.debug("Starting analysis of file %s" % filename)
			self._gcode = gcodeInterpreter.gcode()
			self._gcode.progressCallback = self._onParsingProgress
			self._gcode.load(path)
			self._logger.debug("Analysis of file %s finished, notifying callback" % filename)
			self._loadedCallback(self._currentFile, self._gcode)
		finally:
			self._gcode = None
			self._currentProgress = None
			self._currentFile = None

	def _onParsingProgress(self, progress):
		self._currentProgress = progress
