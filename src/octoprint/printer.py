# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

import time
import datetime
import threading
import copy
import os
import logging

#import logging, logging.config

import octoprint.util.comm as comm
import octoprint.util as util

from octoprint.settings import settings
from octoprint.events import eventManager

def getConnectionOptions():
	"""
	 Retrieves the available ports, baudrates, prefered port and baudrate for connecting to the printer.
	"""
	return {
		"ports": comm.serialList(),
		"baudrates": comm.baudrateList(),
		"portPreference": settings().get(["serial", "port"]),
		"baudratePreference": settings().getInt(["serial", "baudrate"]),
		"autoconnect": settings().getBoolean(["serial", "autoconnect"])
	}

class Printer():
	def __init__(self, gcodeManager):
		from collections import deque

		self._gcodeManager = gcodeManager
		self._gcodeManager.registerCallback(self)

		# state
		self._temp = None
		self._bedTemp = None
		self._targetTemp = None
		self._targetBedTemp = None
		self._temps = {
			"actual": deque([], 300),
			"target": deque([], 300),
			"actualBed": deque([], 300),
			"targetBed": deque([], 300)
		}
		self._tempBacklog = []

		self._latestMessage = None
		self._messages = deque([], 300)
		self._messageBacklog = []

		self._latestLog = None
		self._log = deque([], 300)
		self._logBacklog = []

		self._state = None

		self._currentZ = None

		self._progress = None
		self._printTime = None
		self._printTimeLeft = None

		self._printAfterSelect = False

		# sd handling
		self._sdPrinting = False
		self._sdStreaming = False
		self._sdFilelistAvailable = threading.Event()

		self._selectedFile = None

		# comm
		self._comm = None

		# callbacks
		self._callbacks = []
		self._lastProgressReport = None

		self._stateMonitor = StateMonitor(
			ratelimit=0.5,
			updateCallback=self._sendCurrentDataCallbacks,
			addTemperatureCallback=self._sendAddTemperatureCallbacks,
			addLogCallback=self._sendAddLogCallbacks,
			addMessageCallback=self._sendAddMessageCallbacks
		)
		self._stateMonitor.reset(
			state={"state": None, "stateString": self.getStateString(), "flags": self._getStateFlags()},
			jobData={"filename": None, "filesize": None, "estimatedPrintTime": None, "filament": None},
			progress={"progress": None, "filepos": None, "printTime": None, "printTimeLeft": None},
			currentZ=None
		)

	#~~ callback handling

	def registerCallback(self, callback):
		self._callbacks.append(callback)
		self._sendInitialStateUpdate(callback)

	def unregisterCallback(self, callback):
		if callback in self._callbacks:
			self._callbacks.remove(callback)

	def _sendAddTemperatureCallbacks(self, data):
		for callback in self._callbacks:
			try: callback.addTemperature(data)
			except: pass

	def _sendAddLogCallbacks(self, data):
		for callback in self._callbacks:
			try: callback.addLog(data)
			except: pass

	def _sendAddMessageCallbacks(self, data):
		for callback in self._callbacks:
			try: callback.addMessage(data)
			except: pass

	def _sendCurrentDataCallbacks(self, data):
		for callback in self._callbacks:
			try: callback.sendCurrentData(copy.deepcopy(data))
			except: pass

	def _sendTriggerUpdateCallbacks(self, type):
		for callback in self._callbacks:
			try: callback.sendUpdateTrigger(type)
			except: pass

	def _sendFeedbackCommandOutput(self, name, output):
		for callback in self._callbacks:
			try: callback.sendFeedbackCommandOutput(name, output)
			except: pass

	#~~ callback from gcodemanager

	def sendUpdateTrigger(self, type):
		if type == "gcodeFiles" and self._selectedFile:
			self._setJobData(self._selectedFile["filename"],
				self._selectedFile["filesize"],
				self._selectedFile["sd"])

	#~~ printer commands

	def connect(self, port=None, baudrate=None):
		"""
		 Connects to the printer. If port and/or baudrate is provided, uses these settings, otherwise autodetection
		 will be attempted.
		"""
		if self._comm is not None:
			self._comm.close()
		self._comm = comm.MachineCom(port, baudrate, callbackObject=self)

	def disconnect(self):
		"""
		 Closes the connection to the printer.
		"""
		if self._comm is not None:
			self._comm.close()
		self._comm = None
		eventManager().fire("Disconnected")

	def command(self, command):
		"""
		 Sends a single gcode command to the printer.
		"""
		self.commands([command])

	def commands(self, commands):
		"""
		 Sends multiple gcode commands (provided as a list) to the printer.
		"""
		if self._comm is None:
			return

		for command in commands:
			self._comm.sendCommand(command)

	def setTemperatureOffset(self, extruder, bed):
		if self._comm is None:
			return

		self._comm.setTemperatureOffset(extruder, bed)
		self._stateMonitor.setTempOffsets(extruder, bed)

	def selectFile(self, filename, sd, printAfterSelect=False):
		if self._comm is None or (self._comm.isBusy() or self._comm.isStreaming()):
			logging.info("Cannot load file: printer not connected or currently busy")
			return

		self._printAfterSelect = printAfterSelect
		self._comm.selectFile(filename, sd)
		self._setProgressData(0, None, None, None)
		self._setCurrentZ(None)

	def unselectFile(self):
		if self._comm is not None and (self._comm.isBusy() or self._comm.isStreaming()):
			return

		self._comm.unselectFile()
		self._setProgressData(0, None, None, None)
		self._setCurrentZ(None)

	def startPrint(self):
		"""
		 Starts the currently loaded print job.
		 Only starts if the printer is connected and operational, not currently printing and a printjob is loaded
		"""
		if self._comm is None or not self._comm.isOperational() or self._comm.isPrinting():
			return
		if self._selectedFile is None:
			return

		self._setCurrentZ(None)
		self._comm.startPrint()

	def togglePausePrint(self):
		"""
		 Pause the current printjob.
		"""
		if self._comm is None:
			return

		self._comm.setPause(not self._comm.isPaused())

	def cancelPrint(self, disableMotorsAndHeater=True):
		"""
		 Cancel the current printjob.
		"""
		if self._comm is None:
			return

		self._comm.cancelPrint()

		if disableMotorsAndHeater:
			self.commands(["M84", "M104 S0", "M140 S0", "M106 S0"]) # disable motors, switch off heaters and fan

		# reset progress, height, print time
		self._setCurrentZ(None)
		self._setProgressData(None, None, None, None)

		# mark print as failure
		if self._selectedFile is not None:
			self._gcodeManager.printFailed(self._selectedFile["filename"])
			eventManager().fire("PrintFailed", self._selectedFile["filename"])

	#~~ state monitoring

	def _setCurrentZ(self, currentZ):
		self._currentZ = currentZ

		formattedCurrentZ = None
		if self._currentZ:
			formattedCurrentZ = "%.2f mm" % (self._currentZ)
		self._stateMonitor.setCurrentZ(formattedCurrentZ)

	def _setState(self, state):
		self._state = state
		self._stateMonitor.setState({"state": self._state, "stateString": self.getStateString(), "flags": self._getStateFlags()})

	def _addLog(self, log):
		self._log.append(log)
		self._stateMonitor.addLog(log)

	def _addMessage(self, message):
		self._messages.append(message)
		self._stateMonitor.addMessage(message)

	def _setProgressData(self, progress, filepos, printTime, printTimeLeft):
		self._progress = progress
		self._printTime = printTime
		self._printTimeLeft = printTimeLeft

		formattedPrintTime = None
		if (self._printTime):
			formattedPrintTime = util.getFormattedTimeDelta(datetime.timedelta(seconds=self._printTime))

		formattedPrintTimeLeft = None
		if (self._printTimeLeft):
			formattedPrintTimeLeft = util.getFormattedTimeDelta(datetime.timedelta(minutes=self._printTimeLeft))

		formattedFilePos = None
		if (filepos):
			formattedFilePos = util.getFormattedSize(filepos)

		self._stateMonitor.setProgress({"progress": self._progress, "filepos": formattedFilePos, "printTime": formattedPrintTime, "printTimeLeft": formattedPrintTimeLeft})

	def _addTemperatureData(self, temp, bedTemp, targetTemp, bedTargetTemp):
		currentTimeUtc = int(time.time() * 1000)

		self._temps["actual"].append((currentTimeUtc, temp))
		self._temps["target"].append((currentTimeUtc, targetTemp))
		self._temps["actualBed"].append((currentTimeUtc, bedTemp))
		self._temps["targetBed"].append((currentTimeUtc, bedTargetTemp))

		self._temp = temp
		self._bedTemp = bedTemp
		self._targetTemp = targetTemp
		self._targetBedTemp = bedTargetTemp

		self._stateMonitor.addTemperature({"currentTime": currentTimeUtc, "temp": self._temp, "bedTemp": self._bedTemp, "targetTemp": self._targetTemp, "targetBedTemp": self._targetBedTemp})

	def _setJobData(self, filename, filesize, sd):
		if filename is not None:
			self._selectedFile = {
				"filename": filename,
				"filesize": filesize,
				"sd": sd
			}
		else:
			self._selectedFile = None

		formattedFilename = None
		formattedFilesize = None
		estimatedPrintTime = None
		fileMTime = None
		filament = None
		if filename:
			formattedFilename = os.path.basename(filename)

			# Use a string for mtime because it could be float and the
			# javascript needs to exact match
			if not sd:
				fileMTime = str(os.stat(filename).st_mtime)

			if filesize:
				formattedFilesize = util.getFormattedSize(filesize)

			fileData = self._gcodeManager.getFileData(filename)
			if fileData is not None and "gcodeAnalysis" in fileData.keys():
				if "estimatedPrintTime" in fileData["gcodeAnalysis"].keys():
					estimatedPrintTime = fileData["gcodeAnalysis"]["estimatedPrintTime"]
				if "filament" in fileData["gcodeAnalysis"].keys():
					filament = fileData["gcodeAnalysis"]["filament"]

		self._stateMonitor.setJobData({"filename": formattedFilename, "filesize": formattedFilesize, "estimatedPrintTime": estimatedPrintTime, "filament": filament, "sd": sd, "mtime": fileMTime})

	def _sendInitialStateUpdate(self, callback):
		try:
			data = self._stateMonitor.getCurrentData()
			# convert the dict of deques to a dict of lists
			temps = {k: list(v) for (k,v) in self._temps.iteritems()}
			data.update({
				"temperatureHistory": temps,
				"logHistory": list(self._log),
				"messageHistory": list(self._messages)
			})
			callback.sendHistoryData(data)
		except Exception, err:
			import sys
			sys.stderr.write("ERROR: %s\n" % str(err))
			pass

	def _getStateFlags(self):
		if not settings().getBoolean(["feature", "sdSupport"]) or self._comm is None:
			sdReady = False
		else:
			sdReady = self._comm.isSdReady()

		return {
			"operational": self.isOperational(),
			"printing": self.isPrinting(),
			"closedOrError": self.isClosedOrError(),
			"error": self.isError(),
			"paused": self.isPaused(),
			"ready": self.isReady(),
			"sdReady": sdReady
		}

	def getCurrentData(self):
		return self._stateMonitor.getCurrentData()

	#~~ callbacks triggered from self._comm

	def mcLog(self, message):
		"""
		 Callback method for the comm object, called upon log output.
		"""
		self._addLog(message)

	def mcTempUpdate(self, temp, bedTemp, targetTemp, bedTargetTemp):
		self._addTemperatureData(temp, bedTemp, targetTemp, bedTargetTemp)

	def mcStateChange(self, state):
		"""
		 Callback method for the comm object, called if the connection state changes.
		"""
		oldState = self._state

		# forward relevant state changes to gcode manager
		if self._comm is not None and oldState == self._comm.STATE_PRINTING:
			if self._selectedFile is not None:
				if state == self._comm.STATE_OPERATIONAL:
					self._gcodeManager.printSucceeded(self._selectedFile["filename"])
				elif state == self._comm.STATE_CLOSED or state == self._comm.STATE_ERROR or state == self._comm.STATE_CLOSED_WITH_ERROR:
					self._gcodeManager.printFailed(self._selectedFile["filename"])
			self._gcodeManager.resumeAnalysis() # printing done, put those cpu cycles to good use
		elif self._comm is not None and state == self._comm.STATE_PRINTING:
			self._gcodeManager.pauseAnalysis() # do not analyse gcode while printing

		self._setState(state)

	def mcMessage(self, message):
		"""
		 Callback method for the comm object, called upon message exchanges via serial.
		 Stores the message in the message buffer, truncates buffer to the last 300 lines.
		"""
		self._addMessage(message)

	def mcProgress(self):
		"""
		 Callback method for the comm object, called upon any change in progress of the printjob.
		 Triggers storage of new values for printTime, printTimeLeft and the current progress.
		"""

		self._setProgressData(self._comm.getPrintProgress(), self._comm.getPrintFilepos(), self._comm.getPrintTime(), self._comm.getPrintTimeRemainingEstimate())

	def mcZChange(self, newZ):
		"""
		 Callback method for the comm object, called upon change of the z-layer.
		"""
		oldZ = self._currentZ
		if newZ != oldZ:
			# we have to react to all z-changes, even those that might "go backward" due to a slicer's retraction or
			# anti-backlash-routines. Event subscribes should individually take care to filter out "wrong" z-changes
			eventManager().fire("ZChange", newZ)

		self._setCurrentZ(newZ)

	def mcSdStateChange(self, sdReady):
		self._stateMonitor.setState({"state": self._state, "stateString": self.getStateString(), "flags": self._getStateFlags()})

	def mcSdFiles(self, files):
		self._sendTriggerUpdateCallbacks("gcodeFiles")
		self._sdFilelistAvailable.set()

	def mcFileSelected(self, filename, filesize, sd):
		self._setJobData(filename, filesize, sd)
		self._stateMonitor.setState({"state": self._state, "stateString": self.getStateString(), "flags": self._getStateFlags()})

		if self._printAfterSelect:
			self.startPrint()

	def mcPrintjobDone(self):
		self._setProgressData(1.0, self._selectedFile["filesize"], self._comm.getPrintTime(), 0)
		self._stateMonitor.setState({"state": self._state, "stateString": self.getStateString(), "flags": self._getStateFlags()})

	def mcFileTransferStarted(self, filename, filesize):
		self._sdStreaming = True

		self._setJobData(filename, filesize, True)
		self._setProgressData(0.0, 0, 0, None)
		self._stateMonitor.setState({"state": self._state, "stateString": self.getStateString(), "flags": self._getStateFlags()})

	def mcFileTransferDone(self):
		self._sdStreaming = False

		self._setCurrentZ(None)
		self._setJobData(None, None, None)
		self._setProgressData(None, None, None, None)
		self._stateMonitor.setState({"state": self._state, "stateString": self.getStateString(), "flags": self._getStateFlags()})

	def mcReceivedRegisteredMessage(self, command, output):
		self._sendFeedbackCommandOutput(command, output)

	#~~ sd file handling

	def getSdFiles(self):
		if self._comm is None or not self._comm.isSdReady():
			return []
		return self._comm.getSdFiles()

	def addSdFile(self, filename, absolutePath):
		from octoprint.gcodefiles import isGcodeFileName
		from octoprint.gcodefiles import isSTLFileName

		if not self._comm or self._comm.isBusy() or not self._comm.isSdReady():
			logging.error("No connection to printer or printer is busy")
			return

		if isGcodeFileName(filename):
			self.streamSdFile(filename, absolutePath)

		if isSTLFileName(filename):
			gcodePath = util.genGcodeFileName(absolutePath)
			gcodeFileName = util.genGcodeFileName(filename)
			callBackArgs = [gcodeFileName, gcodePath]
			callBack = self.streamSdFile

			self._gcodeManager.processStl(
				absolutePath, callBack, callBackArgs)

	def streamSdFile(self, filename, path):
		if not self._comm or self._comm.isBusy() or not self._comm.isSdReady():
			return

		self.refreshSdFiles(blocking=True)
		existingSdFiles = self._comm.getSdFiles()

		sdFilename = util.getDosFilename(filename, existingSdFiles)
		self._comm.startFileTransfer(path, sdFilename)

	def deleteSdFile(self, filename):
		if not self._comm or not self._comm.isSdReady():
			return
		self._comm.deleteSdFile(filename)

	def initSdCard(self):
		if not self._comm or self._comm.isSdReady():
			return
		self._comm.initSdCard()

	def releaseSdCard(self):
		if not self._comm or not self._comm.isSdReady():
			return
		self._comm.releaseSdCard()

	def refreshSdFiles(self, blocking=False):
		"""
		Refreshs the list of file stored on the SD card attached to printer (if available and printer communication
		available). Optional blocking parameter allows making the method block (max 10s) until the file list has been
		received (and can be accessed via self._comm.getSdFiles()). Defaults to a asynchronous operation.
		"""
		if not self._comm or not self._comm.isSdReady():
			return
		self._sdFilelistAvailable.clear()
		self._comm.refreshSdFiles()
		if blocking:
			self._sdFilelistAvailable.wait(10000)

	#~~ state reports

	def getStateString(self):
		"""
		 Returns a human readable string corresponding to the current communication state.
		"""
		if self._comm is None:
			return "Offline"
		else:
			return self._comm.getStateString()

	def getCurrentData(self):
		return self._stateMonitor.getCurrentData()

	def getCurrentJob(self):
		currentData = self._stateMonitor.getCurrentData()
		return currentData["job"]

	def getCurrentTemperatures(self):
		if self._comm is not None:
			(tempOffset, bedTempOffset) = self._comm.getOffsets()
		else:
			tempOffset = 0
			bedTempOffset = 0

		return {
			"extruder": {
				"current": self._temp,
				"target": self._targetTemp,
				"offset": tempOffset
			},
			"bed": {
				"current": self._bedTemp,
				"target": self._targetBedTemp,
				"offset": bedTempOffset
			}
		}

	def isClosedOrError(self):
		return self._comm is None or self._comm.isClosedOrError()

	def isOperational(self):
		return self._comm is not None and self._comm.isOperational()

	def isPrinting(self):
		return self._comm is not None and self._comm.isPrinting()

	def isPaused(self):
		return self._comm is not None and self._comm.isPaused()

	def isError(self):
		return self._comm is not None and self._comm.isError()

	def isReady(self):
		return self.isOperational() and not self._comm.isStreaming()

	def isLoading(self):
		return self._gcodeLoader is not None

class GcodeLoader(threading.Thread):
	"""
	 The GcodeLoader takes care of loading a gcode-File from disk and parsing it into a gcode object in a separate
	 thread while constantly notifying interested listeners about the current progress.
	 The progress is returned as a float value between 0 and 1 which is to be interpreted as the percentage of completion.
	"""

	def __init__(self, filename, progressCallback, loadedCallback):
		threading.Thread.__init__(self)

		self._progressCallback = progressCallback
		self._loadedCallback = loadedCallback

		self._filename = filename
		self._gcodeList = None

	def run(self):
		#Send an initial M110 to reset the line counter to zero.
		prevLineType = lineType = "CUSTOM"
		gcodeList = ["M110 N0"]
		filesize = os.stat(self._filename).st_size
		with open(self._filename, "r") as file:
			for line in file:
				if line.startswith(";TYPE:"):
					lineType = line[6:].strip()
				if ";" in line:
					line = line[0:line.find(";")]
				line = line.strip()
				if len(line) > 0:
					if prevLineType != lineType:
						gcodeList.append((line, lineType, ))
					else:
						gcodeList.append(line)
					prevLineType = lineType
				self._onLoadingProgress(float(file.tell()) / float(filesize))

		self._gcodeList = gcodeList
		self._loadedCallback(self._filename, self._gcodeList)

	def _onLoadingProgress(self, progress):
		self._progressCallback(self._filename, progress, "loading")

	def _onParsingProgress(self, progress):
		self._progressCallback(self._filename, progress, "parsing")

class SdFileStreamer(threading.Thread):
	def __init__(self, comm, filename, file, progressCallback, finishCallback):
		threading.Thread.__init__(self)

		self._comm = comm
		self._filename = filename
		self._file = file
		self._progressCallback = progressCallback
		self._finishCallback = finishCallback

	def run(self):
		if self._comm.isBusy():
			return

		name = self._filename[:self._filename.rfind(".")]
		sdFilename = name[:8].lower() + ".gco"
		try:
			size = os.stat(self._file).st_size
			with open(self._file, "r") as f:
				self._comm.startSdFileTransfer(sdFilename)
				for line in f:
					if ";" in line:
						line = line[0:line.find(";")]
					line = line.strip()
					if len(line) > 0:
						self._comm.sendCommand(line)
						time.sleep(0.001) # do not send too fast
					self._progressCallback(sdFilename, float(f.tell()) / float(size))
		finally:
			self._comm.endSdFileTransfer(sdFilename)
			self._finishCallback(sdFilename)

class StateMonitor(object):
	def __init__(self, ratelimit, updateCallback, addTemperatureCallback, addLogCallback, addMessageCallback):
		self._ratelimit = ratelimit
		self._updateCallback = updateCallback
		self._addTemperatureCallback = addTemperatureCallback
		self._addLogCallback = addLogCallback
		self._addMessageCallback = addMessageCallback

		self._state = None
		self._jobData = None
		self._gcodeData = None
		self._sdUploadData = None
		self._currentZ = None
		self._progress = None

		self._tempOffset = 0
		self._bedTempOffset = 0

		self._changeEvent = threading.Event()

		self._lastUpdate = time.time()
		self._worker = threading.Thread(target=self._work)
		self._worker.daemon = True
		self._worker.start()

	def reset(self, state=None, jobData=None, progress=None, currentZ=None):
		self.setState(state)
		self.setJobData(jobData)
		self.setProgress(progress)
		self.setCurrentZ(currentZ)

	def addTemperature(self, temperature):
		self._addTemperatureCallback(temperature)
		self._changeEvent.set()

	def addLog(self, log):
		self._addLogCallback(log)
		self._changeEvent.set()

	def addMessage(self, message):
		self._addMessageCallback(message)
		self._changeEvent.set()

	def setCurrentZ(self, currentZ):
		self._currentZ = currentZ
		self._changeEvent.set()

	def setState(self, state):
		self._state = state
		self._changeEvent.set()

	def setJobData(self, jobData):
		self._jobData = jobData
		self._changeEvent.set()

	def setProgress(self, progress):
		self._progress = progress
		self._changeEvent.set()

	def setTempOffsets(self, tempOffset, bedTempOffset):
		if tempOffset is not None:
			self._tempOffset = tempOffset
		if bedTempOffset is not None:
			self._bedTempOffset = bedTempOffset
		self._changeEvent.set()

	def _work(self):
		while True:
			self._changeEvent.wait()

			now = time.time()
			delta = now - self._lastUpdate
			additionalWaitTime = self._ratelimit - delta
			if additionalWaitTime > 0:
				time.sleep(additionalWaitTime)

			data = self.getCurrentData()
			self._updateCallback(data)
			self._lastUpdate = time.time()
			self._changeEvent.clear()

	def getCurrentData(self):
		return {
			"state": self._state,
			"job": self._jobData,
			"currentZ": self._currentZ,
			"progress": self._progress,
			"offsets": (self._tempOffset, self._bedTempOffset)
		}

