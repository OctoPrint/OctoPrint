# coding=utf-8
from octoprint.comm.protocol.repetier import RepetierTextualProtocol
from octoprint.comm.transport import Transport

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

import time
import datetime
import threading
import copy
import os
import re
import logging

import octoprint.util.comm as comm
import octoprint.util as util

from octoprint.settings import settings
from octoprint.events import eventManager, Events

from octoprint.filemanager.destinations import FileDestinations

from octoprint.comm.protocol import State as ProtocolState, Protocol
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

		self._protocol = self._createProtocol()

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
				"lastPrintTime": None,
				"filament": {
					"length": None,
					"volume": None
				}
			},
			progress={"completion": None, "filepos": None, "printTime": None, "printTimeLeft": None},
			currentZ=None
		)

		eventManager().subscribe(Events.METADATA_ANALYSIS_FINISHED, self.onMetadataAnalysisFinished)

	def _getTransportFactory(self):
		transports = self._getSubclassAttributes(Transport, "__transportinfo__", validator=lambda x: not x[2])

		transportType = settings().get(["communication", "transport"])
		for t in transports:
			id, name, abstract, factory = t
			if transportType == id:
				return factory

		return SerialTransport

	def _createProtocol(self):
		transport = self._getTransportFactory()
		protocol_type = settings().get(["communication", "protocol"])

		protocols = self._getSubclassAttributes(Protocol, "__protocolinfo__", validator=lambda x: not x[2])

		protocol_factory = RepRapProtocol
		for p in protocols:
			id, name, abstract, factory = p
			if protocol_type == id:
				protocol_factory = factory
				break

		return protocol_factory(transport, protocol_listener=self)

	def _getSubclassAttributes(self, origin, attribute, converter=lambda o, v: v, validator=lambda x: True):
		result = []

		if hasattr(origin, attribute):
			value = getattr(origin, attribute)
			if validator(value):
				converted = list(converter(origin, value))
				converted.append(origin)
				result.append(converted)

		subclasses = origin.__subclasses__()
		if subclasses:
			for s in subclasses:
				result.extend(self._getSubclassAttributes(s, attribute, converter, validator))

		return result

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
		if not source == self._protocol:
			return

		# forward relevant state changes to gcode manager
		if oldState == ProtocolState.PRINTING:
			if self._selectedFile is not None:
				if newState == ProtocolState.OPERATIONAL:
					self._gcodeManager.printSucceeded(self._selectedFile["filename"], self._protocol.get_print_time())
				elif newState == ProtocolState.OFFLINE or newState == ProtocolState.ERROR:
					self._gcodeManager.printFailed(self._selectedFile["filename"], self._protocol.get_print_time())

			# printing done, put those cpu cycles to good use
			self._gcodeManager.resumeAnalysis()
		elif newState == ProtocolState.PRINTING:
			# do not analyse gcode while printing
			self._gcodeManager.pauseAnalysis()

		self._setState(newState)
		pass

	def onTemperatureUpdate(self, source, temperatureData):
		if not source == self._protocol:
			return

		self._addTemperatureData(temperatureData)

	def onProgress(self, source, progress):
		if not source == self._protocol:
			return

		self._setProgressData(progress["completion"], progress["filepos"], progress["printTime"], progress["printTimeLeft"])

	def onZChange(self, source, oldZ, newZ):
		if not source == self._protocol:
			return

		if newZ != oldZ:
			# we have to react to all z-changes, even those that might "go backward" due to a slicer's retraction or
			# anti-backlash-routines. Event subscribes should individually take care to filter out "wrong" z-changes
			eventManager().fire(Events.Z_CHANGE, {"new": newZ, "old": oldZ})

		self._setCurrentZ(newZ)

	def onFileSelected(self, source, filename, filesize, origin):
		if not source == self._protocol:
			return

		self._setJobData(filename, filesize, origin)
		self._stateMonitor.setState({"state": self._state, "stateString": self.getStateString(), "flags": self._getStateFlags()})

		if self._printAfterSelect:
			self.startPrint()
		pass

	def onPrintjobDone(self, source):
		if not source == self._protocol:
			return

		self._setProgressData(100.0, self._selectedFile["filesize"], self._protocol.get_print_time(), 0)
		self._stateMonitor.setState({"state": self._state, "stateString": self.getStateString(), "flags": self._getStateFlags()})

	def onFileTransferStarted(self, source, filename, filesize):
		if not source == self._protocol:
			return

		self._sdStreaming = True

		self._setJobData(filename, filesize, FileDestinations.SDCARD)
		self._setProgressData(0.0, 0, 0, None)
		self._stateMonitor.setState({"state": self._state, "stateString": self.getStateString(), "flags": self._getStateFlags()})

	def onFileTransferDone(self, source):
		if not source == self._protocol:
			return

		self._sdStreaming = False

		if self._streamingFinishedCallback is not None:
			self._streamingFinishedCallback(self._sdRemoteName, FileDestinations.SDCARD)

		self._sdRemoteName = None
		self._setCurrentZ(None)
		self._setJobData(None, None, None)
		self._setProgressData(None, None, None, None)
		self._stateMonitor.setState({"state": self._state, "stateString": self.getStateString(), "flags": self._getStateFlags()})

	def onSdStateChange(self, source, sdAvailable):
		if not source == self._protocol:
			return

		self._stateMonitor.setState({"state": self._state, "stateString": self._state, "flags": self._getStateFlags()})

	def onSdFiles(self, source, files):
		if not source == self._protocol:
			return

		eventManager().fire(Events.UPDATED_FILES, {"type": "gcode"})
		self._sdFilelistAvailable.set()

	def onLogTx(self, source, tx):
		if not source == self._protocol:
			return

		self._addLog("Send: %s" % tx)

	def onLogRx(self, source, rx):
		if not source == self._protocol:
			return

		self._addLog("Recv: %s" % rx)

	def onLogError(self, source, error):
		if not source == self._protocol:
			return

		self._addLog("ERROR: %s" % error)

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
		self._protocol.send_manually(command)

	def commands(self, commands):
		self.command(commands)

	def jog(self, axis, amount):
		self._protocol.jog(axis, amount)

	def home(self, axes):
		self._protocol.home(axes)

	def extrude(self, amount):
		self._protocol.extrude(amount)

	def changeTool(self, tool):
		self._protocol.change_tool(tool)

	def setTemperature(self, type, value):
		self._protocol.set_temperature(type, value)

	def setTemperatureOffset(self, offsets):
		current_offsets = self._protocol.get_temperature_offsets()

		new_offsets = {}
		new_offsets.update(current_offsets)

		for key in offsets:
			if key == "bed" or re.match("tool\d+", key):
				new_offsets[key] = offsets[key]

		self._protocol.set_temperature_offsets(new_offsets)
		self._stateMonitor.setTempOffsets(new_offsets)

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
			"completion": self._progress,
			"filepos": filepos,
			"printTime": int(self._printTime) if self._printTime is not None else None,
			"printTimeLeft": int(self._printTimeLeft) if self._printTimeLeft is not None else None
		})

	def _addTemperatureData(self, temperatureData):
		currentTimeUtc = int(time.time())

		data = {
			"time": currentTimeUtc
		}
		data.update(temperatureData)

		self._temps.append(data)

		self._stateMonitor.addTemperature(data)

	def _setJobData(self, filename, filesize, origin):
		sd = origin == FileDestinations.SDCARD
		if filename is not None:
			self._selectedFile = {
				"filename": filename,
				"filesize": filesize,
				"sd": sd
			}
		else:
			self._selectedFile = None

		estimatedPrintTime = None
		lastPrintTime = None
		date = None
		filament = None
		if filename:
			# Use a string for mtime because it could be float and the
			# javascript needs to exact match
			if not sd:
				date = int(os.stat(filename).st_ctime)

			fileData = self._gcodeManager.getFileData(filename)
			if fileData is not None:
				if "gcodeAnalysis" in fileData:
					if estimatedPrintTime is None and "estimatedPrintTime" in fileData["gcodeAnalysis"]:
						estimatedPrintTime = fileData["gcodeAnalysis"]["estimatedPrintTime"]
					if "filament" in fileData["gcodeAnalysis"].keys():
						filament = fileData["gcodeAnalysis"]["filament"]
				if "prints" in fileData and fileData["prints"] and "last" in fileData["prints"] and fileData["prints"]["last"] and "lastPrintTime" in fileData["prints"]["last"]:
					lastPrintTime = fileData["prints"]["last"]["lastPrintTime"]

		self._stateMonitor.setJobData({
			"file": {
				"name": os.path.basename(filename) if filename is not None else None,
				"origin": origin,
				"size": filesize,
				"date": date
			},
			"estimatedPrintTime": estimatedPrintTime,
			"lastPrintTime": lastPrintTime,
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
		existingSdFiles = map(lambda x: x[0], self._protocol.get_sd_files())

		self._sdRemoteName = util.getDosFilename(filename, existingSdFiles)
		self._protocol.add_sd_file(absolutePath, filename, self._sdRemoteName)

		return self._sdRemoteName

	def deleteSdFile(self, filename):
		if not self._protocol.is_sd_ready():
			return
		self._protocol.remove_sd_file(filename)

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
		temperatures = self._protocol.get_current_temperatures()
		offsets = self._protocol.get_temperature_offsets()

		result = {}
		result.update(temperatures)
		for key, tool in result:
			tool["offset"] = offsets[key] if key in offsets and offsets[key] is not None else 0

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
		self._stateMutex = threading.Lock()

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
		with self._stateMutex:
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

			with self._stateMutex:
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

