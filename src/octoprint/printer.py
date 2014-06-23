# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

import time
import datetime
import threading
import copy
import os
import logging

import octoprint.util.comm as comm
import octoprint.util as util

from octoprint.settings import settings
from octoprint.events import eventManager, Events

from octoprint.filemanager.destinations import FileDestinations

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
		# TODO do we really need to hold the temperature here?
		self._temp = None
		self._bedTemp = None
		self._targetTemp = None
		self._targetBedTemp = None
		self._temps = deque([], 300)
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
		self._streamingFinishedCallback = None

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
			state={"text": self.getStateString(), "flags": self._getStateFlags()},
			jobData={
				"file": {
					"name": None,
					"size": None,
					"origin": None,
					"date": None
				},
				"estimatedPrintTime": None,
				"filament": {
					"length": None,
					"volume": None
				}
			},
			progress={"completion": None, "filepos": None, "printTime": None, "printTimeLeft": None},
			currentZ=None
		)

		eventManager().subscribe(Events.METADATA_ANALYSIS_FINISHED, self.onMetadataAnalysisFinished);

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
			try: callback.sendEvent(type)
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

	#~~ callback from metadata analysis event

	def onMetadataAnalysisFinished(self, event, data):
		if self._selectedFile:
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
		eventManager().fire(Events.DISCONNECTED)

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

	def jog(self, axis, amount):
		movementSpeed = settings().get(["printerParameters", "movementSpeed", ["x", "y", "z"]], asdict=True)
		self.commands(["G91", "G1 %s%.4f F%d" % (axis.upper(), amount, movementSpeed[axis]), "G90"])

	def home(self, axes):
		self.commands(["G91", "G28 %s" % " ".join(map(lambda x: "%s0" % x.upper(), axes)), "G90"])

	def extrude(self, amount):
		extrusionSpeed = settings().get(["printerParameters", "movementSpeed", "e"])
		self.commands(["G91", "G1 E%s F%d" % (amount, extrusionSpeed), "G90"])

	def changeTool(self, tool):
		try:
			toolNum = int(tool[len("tool"):])
			self.command("T%d" % toolNum)
		except ValueError:
			pass

	def setTemperature(self, type, value):
		if type.startswith("tool"):
			if settings().getInt(["printerParameters", "numExtruders"]) > 1:
				try:
					toolNum = int(type[len("tool"):])
					self.command("M104 T%d S%f" % (toolNum, value))
				except ValueError:
					pass
			else:
				self.command("M104 S%f" % value)
		elif type == "bed":
			self.command("M140 S%f" % value)

	def setTemperatureOffset(self, offsets={}):
		if self._comm is None:
			return

		tool, bed = self._comm.getOffsets()

		validatedOffsets = {}

		for key in offsets:
			value = offsets[key]
			if key == "bed":
				bed = value
				validatedOffsets[key] = value
			elif key.startswith("tool"):
				try:
					toolNum = int(key[len("tool"):])
					tool[toolNum] = value
					validatedOffsets[key] = value
				except ValueError:
					pass

		self._comm.setTemperatureOffset(tool, bed)
		self._stateMonitor.setTempOffsets(validatedOffsets)

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
			# disable motors, switch off hotends, bed and fan
			commands = ["M84"]
			commands.extend(map(lambda x: "M104 T%d S0" % x, range(settings().getInt(["printerParameters", "numExtruders"]))))
			commands.extend(["M140 S0", "M106 S0"])
			self.commands(commands)

		# reset progress, height, print time
		self._setCurrentZ(None)
		self._setProgressData(None, None, None, None)

		# mark print as failure
		if self._selectedFile is not None:
			self._gcodeManager.printFailed(self._selectedFile["filename"], self._comm.getPrintTime())
			payload = {
				"file": self._selectedFile["filename"],
				"origin": FileDestinations.LOCAL
			}
			if self._selectedFile["sd"]:
				payload["origin"] = FileDestinations.SDCARD
			eventManager().fire(Events.PRINT_FAILED, payload)

	#~~ state monitoring

	def _setCurrentZ(self, currentZ):
		self._currentZ = currentZ
		self._stateMonitor.setCurrentZ(self._currentZ)

	def _setState(self, state):
		self._state = state
		self._stateMonitor.setState({"text": self.getStateString(), "flags": self._getStateFlags()})

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

		self._stateMonitor.setProgress({
			"completion": self._progress * 100 if self._progress is not None else None,
			"filepos": filepos,
			"printTime": int(self._printTime) if self._printTime is not None else None,
			"printTimeLeft": int(self._printTimeLeft * 60) if self._printTimeLeft is not None else None
		})

	def _addTemperatureData(self, temp, bedTemp):
		currentTimeUtc = int(time.time())

		data = {
			"time": currentTimeUtc
		}
		for tool in temp.keys():
			data["tool%d" % tool] = {
				"actual": temp[tool][0],
				"target": temp[tool][1]
			}
		if bedTemp is not None and isinstance(bedTemp, tuple):
			data["bed"] = {
				"actual": bedTemp[0],
				"target": bedTemp[1]
			}

		self._temps.append(data)

		self._temp = temp
		self._bedTemp = bedTemp

		self._stateMonitor.addTemperature(data)

	def _setJobData(self, filename, filesize, sd):
		if filename is not None:
			self._selectedFile = {
				"filename": filename,
				"filesize": filesize,
				"sd": sd
			}
		else:
			self._selectedFile = None

		estimatedPrintTime = None
		date = None
		filament = None
		if filename:
			# Use a string for mtime because it could be float and the
			# javascript needs to exact match
			if not sd:
				date = int(os.stat(filename).st_ctime)

			fileData = self._gcodeManager.getFileData(filename)
			if fileData is not None and "gcodeAnalysis" in fileData.keys():
				if "estimatedPrintTime" in fileData["gcodeAnalysis"].keys():
					estimatedPrintTime = fileData["gcodeAnalysis"]["estimatedPrintTime"]
				if "filament" in fileData["gcodeAnalysis"].keys():
					filament = fileData["gcodeAnalysis"]["filament"]

		self._stateMonitor.setJobData({
			"file": {
				"name": os.path.basename(filename) if filename is not None else None,
				"origin": FileDestinations.SDCARD if sd else FileDestinations.LOCAL,
				"size": filesize,
				"date": date
			},
			"estimatedPrintTime": estimatedPrintTime,
			"filament": filament,
		})

	def _sendInitialStateUpdate(self, callback):
		try:
			data = self._stateMonitor.getCurrentData()
			data.update({
				"temps": list(self._temps),
				"logs": list(self._log),
				"messages": list(self._messages)
			})
			callback.sendHistoryData(data)
		except Exception, err:
			import sys
			sys.stderr.write("ERROR: %s\n" % str(err))
			pass

	def _getStateFlags(self):
		return {
			"operational": self.isOperational(),
			"printing": self.isPrinting(),
			"closedOrError": self.isClosedOrError(),
			"error": self.isError(),
			"paused": self.isPaused(),
			"ready": self.isReady(),
			"sdReady": self.isSdReady()
		}

	#~~ callbacks triggered from self._comm

	def mcLog(self, message):
		"""
		 Callback method for the comm object, called upon log output.
		"""
		self._addLog(message)

	def mcTempUpdate(self, temp, bedTemp):
		self._addTemperatureData(temp, bedTemp)

	def mcStateChange(self, state):
		"""
		 Callback method for the comm object, called if the connection state changes.
		"""
		oldState = self._state

		# forward relevant state changes to gcode manager
		if self._comm is not None and oldState == self._comm.STATE_PRINTING:
			if self._selectedFile is not None:
				if state == self._comm.STATE_OPERATIONAL:
					self._gcodeManager.printSucceeded(self._selectedFile["filename"], self._comm.getPrintTime())
				elif state == self._comm.STATE_CLOSED or state == self._comm.STATE_ERROR or state == self._comm.STATE_CLOSED_WITH_ERROR:
					self._gcodeManager.printFailed(self._selectedFile["filename"], self._comm.getPrintTime())
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
			eventManager().fire(Events.Z_CHANGE, {"new": newZ, "old": oldZ})

		self._setCurrentZ(newZ)

	def mcSdStateChange(self, sdReady):
		self._stateMonitor.setState({"text": self.getStateString(), "flags": self._getStateFlags()})

	def mcSdFiles(self, files):
		eventManager().fire(Events.UPDATED_FILES, {"type": "gcode"})
		self._sdFilelistAvailable.set()

	def mcFileSelected(self, filename, filesize, sd):
		self._setJobData(filename, filesize, sd)
		self._stateMonitor.setState({"text": self.getStateString(), "flags": self._getStateFlags()})

		if self._printAfterSelect:
			self.startPrint()

	def mcPrintjobDone(self):
		self._setProgressData(1.0, self._selectedFile["filesize"], self._comm.getPrintTime(), 0)
		self._stateMonitor.setState({"text": self.getStateString(), "flags": self._getStateFlags()})

	def mcFileTransferStarted(self, filename, filesize):
		self._sdStreaming = True

		self._setJobData(filename, filesize, True)
		self._setProgressData(0.0, 0, 0, None)
		self._stateMonitor.setState({"text": self.getStateString(), "flags": self._getStateFlags()})

	def mcFileTransferDone(self, filename):
		self._sdStreaming = False

		if self._streamingFinishedCallback is not None:
			# in case of SD files, both filename and absolutePath are the same, so we set the (remote) filename for
			# both parameters
			self._streamingFinishedCallback(filename, filename, FileDestinations.SDCARD)

		self._setCurrentZ(None)
		self._setJobData(None, None, None)
		self._setProgressData(None, None, None, None)
		self._stateMonitor.setState({"text": self.getStateString(), "flags": self._getStateFlags()})

	def mcReceivedRegisteredMessage(self, command, output):
		self._sendFeedbackCommandOutput(command, output)

	#~~ sd file handling

	def getSdFiles(self):
		if self._comm is None or not self._comm.isSdReady():
			return []
		return self._comm.getSdFiles()

	def addSdFile(self, filename, absolutePath, streamingFinishedCallback):
		if not self._comm or self._comm.isBusy() or not self._comm.isSdReady():
			logging.error("No connection to printer or printer is busy")
			return

		self._streamingFinishedCallback = streamingFinishedCallback

		self.refreshSdFiles(blocking=True)
		existingSdFiles = map(lambda x: x[0], self._comm.getSdFiles())

		remoteName = util.getDosFilename(filename, existingSdFiles)
		self._comm.startFileTransfer(absolutePath, filename, remoteName)

		return remoteName

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
			tempOffset, bedTempOffset = self._comm.getOffsets()
		else:
			tempOffset = {}
			bedTempOffset = None

		result = {}
		if self._temp is not None:
			for tool in self._temp.keys():
				result["tool%d" % tool] = {
					"actual": self._temp[tool][0],
					"target": self._temp[tool][1],
					"offset": tempOffset[tool] if tool in tempOffset.keys() and tempOffset[tool] is not None else 0
					}
		if self._bedTemp is not None:
			result["bed"] = {
				"actual": self._bedTemp[0],
				"target": self._bedTemp[1],
				"offset": bedTempOffset
			}

		return result

	def getTemperatureHistory(self):
		return self._temps

	def getCurrentConnection(self):
		if self._comm is None:
			return "Closed", None, None

		port, baudrate = self._comm.getConnection()
		return self._comm.getStateString(), port, baudrate

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

	def isSdReady(self):
		if not settings().getBoolean(["feature", "sdSupport"]) or self._comm is None:
			return False
		else:
			return self._comm.isSdReady()

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

		self._offsets = {}

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

	def setTempOffsets(self, offsets):
		self._offsets = offsets
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
			"offsets": self._offsets
		}

