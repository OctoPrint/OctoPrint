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

from octoprint.comm.protocol import State as ProtocolState
from octoprint.comm.protocol.reprap import RepRapProtocol
from octoprint.comm.transport.serialTransport import SerialTransport

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
		self._sdRemoteName = None
		self._streamingFinishedCallback = None

		self._selectedFile = None

		# comm
		self._comm = None

		self._protocol = RepRapProtocol(SerialTransport, protocol_listener=self)

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

	#~~ callbacks from protocol

	def onStateChange(self, source, oldState, newState):
		# forward relevant state changes to gcode manager
		if self._comm is not None and oldState == ProtocolState.PRINTING:
			if self._selectedFile is not None:
				if newState == ProtocolState.OPERATIONAL:
					self._gcodeManager.printSucceeded(self._selectedFile["filename"], self._protocol.get_print_time())
				elif newState == ProtocolState.OFFLINE or newState == ProtocolState.ERROR:
					self._gcodeManager.printFailed(self._selectedFile["filename"], self._protocol.get_print_time())
			self._gcodeManager.resumeAnalysis() # printing done, put those cpu cycles to good use
		elif newState == ProtocolState.PRINTING:
			self._gcodeManager.pauseAnalysis() # do not analyse gcode while printing

		self._setState(newState)
		pass

	def onTemperatureUpdate(self, source, temperatureData):
		self._addTemperatureData(temperatureData)

	def onProgress(self, source, progress):
		self._setProgressData(progress["completion"], progress["filepos"], progress["printTime"], progress["printTimeLeft"])

	def onZChange(self, source, oldZ, newZ):
		if newZ != oldZ:
			# we have to react to all z-changes, even those that might "go backward" due to a slicer's retraction or
			# anti-backlash-routines. Event subscribes should individually take care to filter out "wrong" z-changes
			eventManager().fire(Events.Z_CHANGE, {"new": newZ, "old": oldZ})

		self._setCurrentZ(newZ)

	def onFileSelected(self, source, filename, filesize, origin):
		self._setJobData(filename, filesize, origin)
		self._stateMonitor.setState({"state": self._state, "stateString": self.getStateString(), "flags": self._getStateFlags()})

		if self._printAfterSelect:
			self.startPrint()
		pass

	def onPrintjobDone(self, source):
		self._setProgressData(1.0, self._selectedFile["filesize"], self._protocol.get_print_time(), 0)
		self._stateMonitor.setState({"state": self._state, "stateString": self.getStateString(), "flags": self._getStateFlags()})

	def onSdStateChange(self, source, sdAvailable):
		self._stateMonitor.setState({"state": self._state, "stateString": self._state, "flags": self._getStateFlags()})

	def onSdFiles(self, source, files):
		eventManager().fire(Events.UPDATED_FILES, {"type": "gcode"})
		self._sdFilelistAvailable.set()

	def onLogTx(self, source, tx):
		self._addLog("Send: %s" % tx)

	def onLogRx(self, source, rx):
		self._addLog("Recv: %s" % rx)

	def onLogError(self, source, error):
		self._addLog("ERROR: %s" % error)

	#~~ printer commands

	def connect(self, port=None, baudrate=None):
		"""
		 Connects to the printer. If port and/or baudrate is provided, uses these settings, otherwise autodetection
		 will be attempted.
		"""
		self._protocol.disconnect()
		self._protocol.connect({"port": port, "baudrate": baudrate})

	def disconnect(self):
		"""
		 Closes the connection to the printer.
		"""
		self._protocol.disconnect()
		eventManager().fire(Events.DISCONNECTED)

	def getConnectionOptions(self):
		connection_options = self._protocol.get_connection_options()

		return {
		"ports": connection_options["port"],
		"baudrates": connection_options["baudrate"],
		"portPreference": settings().get(["serial", "port"]),
		"baudratePreference": settings().getInt(["serial", "baudrate"]),
		"autoconnect": settings().getBoolean(["serial", "autoconnect"])
		}

	def command(self, command):
		"""
		 Sends a single gcode command to the printer.
		"""
		self.commands([command])

	def commands(self, commands):
		"""
		 Sends multiple gcode commands (provided as a list) to the printer.
		"""
		for command in commands:
			self._protocol.send_manually(command)

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
		# TODO
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

	def selectFile(self, filename, origin, printAfterSelect=False):
		self._printAfterSelect = printAfterSelect
		self._protocol.select_file(filename, origin)
		self._setProgressData(0, None, None, None)
		self._setCurrentZ(None)

	def unselectFile(self):
		self._protocol.deselect_file()
		self._setProgressData(0, None, None, None)
		self._setCurrentZ(None)

	def startPrint(self):
		"""
		 Starts the currently loaded print job.
		 Only starts if the printer is connected and operational, not currently printing and a printjob is loaded
		"""
		if not self._protocol.is_operational() or self._protocol.is_busy():
			return
		if self._selectedFile is None:
			return

		self._setCurrentZ(None)
		self._protocol.start_print()

	def togglePausePrint(self):
		"""
		 Pause the current printjob.
		"""
		self._protocol.pause_print()

	def cancelPrint(self, disableMotorsAndHeater=True):
		"""
		 Cancel the current printjob.
		"""
		self._protocol.cancel_print()

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
			self._gcodeManager.printFailed(self._selectedFile["filename"], self._protocol.get_print_time())
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

		self._stateMonitor.setProgress({
			"completion": self._progress,
			"filepos": filepos,
			"printTime": int(self._printTime) if self._printTime is not None else None,
			"printTimeLeft": int(self._printTimeLeft * 60) if self._printTimeLeft is not None else None
		})

	def _addTemperatureData(self, temperatureData):
		currentTimeUtc = int(time.time())

		data = {
			"time": currentTimeUtc
		}
		data.update(temperatureData)

		temp = {}
		bedTemp = None
		for key in temperatureData.keys():
			if key.startswith("tool"):
				temp[key] = temperatureData[key]
			else:
				bedTemp = temperatureData[key]

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
				"tempHistory": list(self._temps),
				"logHistory": list(self._log),
				"messageHistory": list(self._messages)
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

	def mcFileTransferStarted(self, filename, filesize):
		self._sdStreaming = True

		self._setJobData(filename, filesize, True)
		self._setProgressData(0.0, 0, 0, None)
		self._stateMonitor.setState({"state": self._state, "stateString": self.getStateString(), "flags": self._getStateFlags()})

	def mcFileTransferDone(self, filename):
		self._sdStreaming = False

		if self._streamingFinishedCallback is not None:
			self._streamingFinishedCallback(self._sdRemoteName, FileDestinations.SDCARD)

		self._sdRemoteName = None
		self._setCurrentZ(None)
		self._setJobData(None, None, None)
		self._setProgressData(None, None, None, None)
		self._stateMonitor.setState({"state": self._state, "stateString": self.getStateString(), "flags": self._getStateFlags()})

	def mcReceivedRegisteredMessage(self, command, output):
		self._sendFeedbackCommandOutput(command, output)

	#~~ sd file handling

	def getSdFiles(self):
		if not self._protocol.is_sd_ready():
			return []
		return self._protocol.get_sd_files()

	def addSdFile(self, filename, absolutePath, streamingFinishedCallback):
		if self._protocol.is_busy() or not self._protocol.is_sd_ready():
			logging.error("No connection to printer or printer is busy")
			return

		self._streamingFinishedCallback = streamingFinishedCallback

		self.refreshSdFiles(blocking=True)
		existingSdFiles = self._protocol.get_sd_files()

		remoteName = util.getDosFilename(filename, existingSdFiles)
		# TODO
		self._comm.startFileTransfer(absolutePath, filename, remoteName)

		return remoteName

	def deleteSdFile(self, filename):
		# TODO
		if not self._comm or not self._comm.isSdReady():
			return
		self._comm.deleteSdFile(filename)

	def initSdCard(self):
		self._protocol.init_sd()

	def releaseSdCard(self):
		if not self._protocol.is_sd_ready() or self._protocol.is_busy():
			return
		self._protocol.release_sd()

	def refreshSdFiles(self, blocking=False):
		"""
		Refreshs the list of file stored on the SD card attached to printer (if available and printer communication
		available). Optional blocking parameter allows making the method block (max 10s) until the file list has been
		received (and can be accessed via self._protocol.get_sd_files()). Defaults to a asynchronous operation.
		"""
		if not self._protocol.is_sd_ready():
			return
		self._sdFilelistAvailable.clear()
		self._protocol.refresh_sd_files()
		if blocking:
			self._sdFilelistAvailable.wait(10000)

	#~~ state reports

	def getStateString(self):
		"""
		 Returns a human readable string corresponding to the current communication state.
		"""
		return self._state

	def getCurrentData(self):
		return self._stateMonitor.getCurrentData()

	def getCurrentJob(self):
		currentData = self._stateMonitor.getCurrentData()
		return currentData["job"]

	def getCurrentTemperatures(self):
		# TODO
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
		opt = self._protocol.get_current_connection()
		if "port" in opt.keys() and "baudrate" in opt.keys():
			return self._protocol.get_state(), opt["port"], opt["baudrate"]
		return self._protocol.get_state(), None, None

	def isClosedOrError(self):
		return self._protocol.get_state() == ProtocolState.OFFLINE or self._protocol == ProtocolState.ERROR

	def isOperational(self):
		return not self.isClosedOrError()

	def isPrinting(self):
		return self._protocol.get_state() == ProtocolState.PRINTING

	def isPaused(self):
		return self._protocol.get_state() == ProtocolState.PAUSED

	def isError(self):
		return self._protocol.get_state() == ProtocolState.ERROR

	def isReady(self):
		return self.isOperational() and not self._protocol.is_streaming()

	def isSdReady(self):
		if not settings().getBoolean(["feature", "sdSupport"]):
			return False
		else:
			return self._protocol.is_sd_ready()

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

