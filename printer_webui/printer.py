# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

import time
from threading import Thread
import Queue
import collections

import printer_webui.util.comm as comm
from printer_webui.util import gcodeInterpreter

from printer_webui.settings import settings

def getConnectionOptions():
	"""
	 Retrieves the available ports, baudrates, prefered port and baudrate for connecting to the printer.
	"""
	return {
		"ports": comm.serialList(),
		"baudrates": comm.baudrateList(),
		"portPreference": settings().get("serial", "port"),
		"baudratePreference": settings().getInt("serial", "baudrate")
	}

class Printer():
	def __init__(self):
		# state
		self._temp = None
		self._bedTemp = None
		self._targetTemp = None
		self._targetBedTemp = None
		self._temps = {
			"actual": [],
			"target": [],
			"actualBed": [],
			"targetBed": []
		}

		self._latestMessage = None
		self._messages = []

		self._latestLog = None
		self._log = []

		self._state = None

		self._currentZ = None

		self._progress = None
		self._printTime = None
		self._printTimeLeft = None

		# gcode handling
		self._gcode = None
		self._gcodeList = None
		self._filename = None
		self._gcodeLoader = None

		# feedrate
		self._feedrateModifierMapping = {"outerWall": "WALL-OUTER", "innerWall": "WALL_INNER", "fill": "FILL", "support": "SUPPORT"}

		# timelapse
		self._timelapse = None

		# comm
		self._comm = None

		# callbacks
		self._callbacks = []
		self._lastProgressReport = None

		self._updateQueue = MessageQueue()
		self._updateQueue.registerMessageType("zchange", self._sendZChangeCallbacks, overwrite=True)
		self._updateQueue.registerMessageType("state", self._sendStateCallbacks)
		self._updateQueue.registerMessageType("temperature", self._sendTemperatureCallbacks, mergeFunction=(lambda x,y: x + y))
		self._updateQueue.registerMessageType("log", self._sendLogCallbacks, mergeFunction=(lambda x, y: x + y))
		self._updateQueue.registerMessageType("message", self._sendMessageCallbacks, mergeFunction=(lambda x, y: x + y))
		self._updateQueue.registerMessageType("progress", self._sendProgressCallbacks, overwrite=True)
		self._updateQueue.registerMessageType("job", self._sendJobCallbacks, throttling=0.5)
		self._updateQueue.registerMessageType("gcode", self._sendGcodeCallbacks, throttling=0.5)

		self._updateQueueWorker = Thread(target=self._processQueue)
		self._updateQueueWorker.start()

	#~~ callback handling

	def registerCallback(self, callback):
		self._callbacks.append(callback)
		self._sendInitialStateUpdate(callback)

	def unregisterCallback(self, callback):
		if callback in self._callbacks:
			self._callbacks.remove(callback)

	def _sendZChangeCallbacks(self, data):
		for callback in self._callbacks:
			try: callback.zChangeCB(data["currentZ"])
			except: pass

	def _sendStateCallbacks(self, data):
		for callback in self._callbacks:
			try: callback.stateChangeCB(data["state"], data["stateString"], data["stateFlags"])
			except: pass

	def _sendTemperatureCallbacks(self, data):
		for callback in self._callbacks:
			try: callback.temperatureChangeCB(data)
			except: pass

	def _sendLogCallbacks(self, data):
		for callback in self._callbacks:
			try: callback.logChangeCB(data)
			except: pass

	def _sendMessageCallbacks(self, data):
		for callback in self._callbacks:
			try: callback.messageChangeCB(data)
			except: pass

	def _sendProgressCallbacks(self, data):
		for callback in self._callbacks:
			try: callback.progressChangeCB(data["progress"], data["printTime"], data["printTimeLeft"])
			except: pass

	def _sendJobCallbacks(self, data):
		for callback in self._callbacks:
			try: callback.jobDataChangeCB(data["filename"], data["lines"], data["estimatedPrintTime"], data["filament"])
			except: pass

	def _sendGcodeCallbacks(self, data):
		for callback in self._callbacks:
			try: callback.gcodeChangeCB(data["filename"], data["progress"])
			except:
				pass

	def _processQueue(self):
		while True:
			(target, data) = self._updateQueue.read()
			target(data)
			self._updateQueue.task_done()

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
			self._comm.sendCommand(command)

	def setFeedrateModifier(self, structure, percentage):
		if (not self._feedrateModifierMapping.has_key(structure)) or percentage < 0:
			return

		self._comm.setFeedrateModifier(self._feedrateModifierMapping[structure], percentage / 100.0)

	def loadGcode(self, file):
		"""
		 Loads the gcode from the given file as the new print job.
		 Aborts if the printer is currently printing or another gcode file is currently being loaded.
		"""
		if (self._comm is not None and self._comm.isPrinting()) or (self._gcodeLoader is not None):
			return

		self._setJobData(None, None, None)

		self._gcodeLoader = GcodeLoader(file, self)
		self._gcodeLoader.start()

	def startPrint(self):
		"""
		 Starts the currently loaded print job.
		 Only starts if the printer is connected and operational, not currently printing and a printjob is loaded
		"""
		if self._comm is None or not self._comm.isOperational():
			return
		if self._gcodeList is None:
			return
		if self._comm.isPrinting():
			return

		self._setCurrentZ(-1)
		self._comm.printGCode(self._gcodeList)

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
			self.commands(["M84", "M104 S0", "M140 S0"]) # disable motors, switch off heaters

		# reset line, height, print time
		self._setCurrentZ(None)
		self._setProgressData(None, None, None)

	#~~ state monitoring

	def setTimelapse(self, timelapse):
		if self._timelapse is not None and self.isPrinting():
			self._timelapse.onPrintjobStopped()
			del self._timelapse
		self._timelapse = timelapse

	def getTimelapse(self):
		return self._timelapse

	def _setCurrentZ(self, currentZ):
		self._currentZ = currentZ
		self._updateQueue.message("zchange", {"currentZ": self._currentZ})

	def _setState(self, state):
		self._state = state
		self._updateQueue.message("state", {"state": self._state, "stateString": self.getStateString(), "stateFlags": self._getStateFlags()})

	def _addLog(self, log):
		"""
		 Log line is stored in internal buffer, which is truncated to the last 300 lines.
		"""
		self._latestLog = log
		self._log.append(log)
		self._log = self._log[-300:]
		self._updateQueue.message("log", [self._latestLog])

	def _addMessage(self, message):
		self._latestMessage = message
		self._messages.append(message)
		self._messages = self._messages[-300:]
		self._updateQueue.message("message", [self._latestLog])

	def _setProgressData(self, progress, printTime, printTimeLeft):
		self._progress = progress
		self._printTime = printTime
		self._printTimeLeft = printTimeLeft

		#if not self._lastProgressReport or self._lastProgressReport + 0.5 <= time.time():
		self._updateQueue.message("progress", {"progress": self._progress, "printTime": self._printTime, "printTimeLeft": self._printTimeLeft})
		#	self._lastProgressReport = time.time()

	def _addTemperatureData(self, temp, bedTemp, targetTemp, bedTargetTemp):
		"""
		 Temperature information (actual and target) for print head and print bed is stored in corresponding
		 temperature history (including timestamp), history is truncated to 300 entries.
		"""
		currentTime = int(time.time() * 1000)

		self._temps["actual"].append((currentTime, temp))
		self._temps["actual"] = self._temps["actual"][-300:]

		self._temps["target"].append((currentTime, targetTemp))
		self._temps["target"] = self._temps["target"][-300:]

		self._temps["actualBed"].append((currentTime, bedTemp))
		self._temps["actualBed"] = self._temps["actualBed"][-300:]

		self._temps["targetBed"].append((currentTime, bedTargetTemp))
		self._temps["targetBed"] = self._temps["targetBed"][-300:]

		self._temp = temp
		self._bedTemp = bedTemp
		self._targetTemp = targetTemp
		self._targetBedTemp = bedTargetTemp

		self._updateQueue.message("temperature", [{"currentTime": currentTime, "temp": self._temp, "bedTemp": self._bedTemp, "targetTemp": self._targetTemp, "targetBedTemp": self._targetBedTemp, "history": self._temps}])

	def _setJobData(self, filename, gcode, gcodeList):
		self._filename = filename
		self._gcode = gcode
		self._gcodeList = gcodeList

		lines = None
		if self._gcodeList:
			lines = len(self._gcodeList)

		estimatedPrintTime = None
		filament = None
		if self._gcode:
			estimatedPrintTime = self._gcode.totalMoveTimeMinute
			filament = self._gcode.extrusionAmount

		self._updateQueue.message("job", {"filename": self._filename, "lines": lines, "estimatedPrintTime": estimatedPrintTime, "filament": filament})

	def _sendInitialStateUpdate(self, callback):
		lines = None
		if self._gcodeList:
			lines = len(self._gcodeList)

		estimatedPrintTime = None
		filament = None
		if self._gcode:
			estimatedPrintTime = self._gcode.totalMoveTimeMinute
			filament = self._gcode.extrusionAmount

		try:
			callback.zChangeCB(self._currentZ)
			callback.stateChangeCB(self._state, self.getStateString(), self._getStateFlags())
			callback.progressChangeCB(self._progress, self._printTime, self._printTimeLeft)
			callback.temperatureChangeCB([{"currentTime": time.time() * 1000, "temp": self._temp, "bedTemp": self._bedTemp, "targetTemp": self._targetTemp, "bedTargetTemp": self._targetBedTemp}])
			callback.jobDataChangeCB(self._filename, lines, estimatedPrintTime, filament)
			callback.sendHistoryData(self._temps, self._log, self._messages)
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
			"loading": self.isLoading(),
			"paused": self.isPaused(),
			"ready": self.isReady()
		}

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

		if self._timelapse is not None:
			if oldState == self._comm.STATE_PRINTING:
				self._timelapse.onPrintjobStopped()
			elif state == self._comm.STATE_PRINTING:
				self._timelapse.onPrintjobStarted(self._filename)

		self._setState(state)


	def mcMessage(self, message):
		"""
		 Callback method for the comm object, called upon message exchanges via serial.
		 Stores the message in the message buffer, truncates buffer to the last 300 lines.
		"""
		self._addMessage(message)

	def mcProgress(self, lineNr):
		"""
		 Callback method for the comm object, called upon any change in progress of the printjob.
		 Triggers storage of new values for printTime, printTimeLeft and the current line.
		"""
		oldProgress = self._progress

		if self._timelapse is not None:
			try: self._timelapse.onPrintjobProgress(oldProgress, self._progress, int(round(self._progress * 100 / len(self._gcodeList))))
			except: pass

		self._setProgressData(self._comm.getPrintPos(), self._comm.getPrintTime(), self._comm.getPrintTimeRemainingEstimate())

	def mcZChange(self, newZ):
		"""
		 Callback method for the comm object, called upon change of the z-layer.
		"""
		oldZ = self._currentZ
		if self._timelapse is not None:
			self._timelapse.onZChange(oldZ, newZ)

		self._setCurrentZ(newZ)

	#~~ callbacks triggered by gcodeLoader

	def onGcodeLoadingProgress(self, progress):
		self._updateQueue.message("gcode", {"filename": self._gcodeLoader._filename, "progress": progress})

	def onGcodeLoaded(self):
		self._setJobData(self._gcodeLoader._filename, self._gcodeLoader._gcode, self._gcodeLoader._gcodeList)
		self._setCurrentZ(None)
		self._setProgressData(None, None, None)
		self._gcodeLoader = None

		self._updateQueue.message("state", {"state": self._state, "stateString": self.getStateString(), "stateFlags": self._getStateFlags()})

	#~~ state reports


	def gcodeState(self):
		if self.gcodeLoader is not None:
			return {
				"filename": self.gcodeLoader.filename,
				"progress": self.gcodeLoader.progress
			}
		else:
			return None

	def feedrateState(self):
		if self._comm is not None:
			feedrateModifiers = self._comm.getFeedrateModifiers()
			result = {}
			for structure in self._feedrateModifierMapping.keys():
				if (feedrateModifiers.has_key(self._feedrateModifierMapping[structure])):
					result[structure] = int(round(feedrateModifiers[self._feedrateModifierMapping[structure]] * 100))
				else:
					result[structure] = 100
			return result
		else:
			return None

	def getStateString(self):
		"""
		 Returns a human readable string corresponding to the current communication state.
		"""
		if self._comm is None:
			return "Offline"
		else:
			return self._comm.getStateString()

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
		return self._gcodeLoader is None and self._gcodeList and len(self._gcodeList) > 0

	def isLoading(self):
		return self._gcodeLoader is not None

class GcodeLoader(Thread):
	"""
	 The GcodeLoader takes care of loading a gcode-File from disk and parsing it into a gcode object in a separate
	 thread while constantly notifying interested listeners about the current progress.
	 The progress is returned as a float value between 0 and 1 which is to be interpreted as the percentage of completion.
	"""

	def __init__(self, filename, printerCallback):
		Thread.__init__(self)

		self._printerCallback = printerCallback

		self._filename = filename
		self._progress = None

		self._gcode = None
		self._gcodeList = None

	def run(self):
		#Send an initial M110 to reset the line counter to zero.
		prevLineType = lineType = "CUSTOM"
		gcodeList = ["M110"]
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

		self._gcodeList = gcodeList
		self._gcode = gcodeInterpreter.gcode()
		self._gcode.progressCallback = self.onProgress
		self._gcode.loadList(self._gcodeList)

		self._printerCallback.onGcodeLoaded()

	def onProgress(self, progress):
		self._progress = progress
		self._printerCallback.onGcodeLoadingProgress(progress)

class PrinterCallback(object):
	def zChangeCB(self, newZ):
		pass

	def progressChangeCB(self, currentLine, printTime, printTimeLeft):
		pass

	def temperatureChangeCB(self, currentTime, temp, bedTemp, targetTemp, bedTargetTemp):
		pass

	def stateChangeCB(self, state, stateString, booleanStates):
		pass

	def logChangeCB(self, line):
		pass

	def messageChangeCB(self, line):
		pass

	def gcodeChangeCB(self, filename, progress):
		pass

	def jobDataChangeCB(self, filename, lines, estimatedPrintTime, filamentLength):
		pass

	def sendHistoryData(self, tempHistory, logHistory, messageHistory):
		pass


class MessageQueue(Queue.Queue):
	def __init__(self, maxsize=0):
		Queue.Queue.__init__(self, maxsize)
		self._messageTypes = dict()
		self._lastSends = dict()

	def registerMessageType(self, messageType, callback, overwrite=False, throttling=None, mergeFunction=None):
		self._messageTypes[messageType] = (callback, overwrite, throttling, mergeFunction)
		if throttling is not None:
			self._lastSends[messageType] = time.time()

	def message(self, messageType, data, timestamp=time.time()):
		if not self._messageTypes.has_key(messageType):
			return

		(callback, overwrite, throttling, merger) = self._messageTypes[messageType]
		updated = False
		try:
			self.mutex.acquire()
			if overwrite or throttling is not None or merger is not None:
				for item in self.queue:
					if item.type == messageType and ((throttling is not None and item.timestamp + throttling < time.time()) or overwrite or merger is not None):
						if merger is not None:
							item.payload = merger(item.payload, data)
						else:
							item.payload = data
						updated = True
						break
		finally:
			self.mutex.release()

		if not updated:
			item = MessageQueueItem(messageType, timestamp, data)
			self.put(item)

	def read(self):
		item = None
		while item is None:
			item = self.get()
			if not self._messageTypes.has_key(item.type):
				self.task_done()
				item = None
			(callback, overwrite, throttling, merger) = self._messageTypes[item.type]
			if throttling and self._lastSends[item.type] + throttling > time.time():
				self.message(item.type, item.payload, item.timestamp)
				item = None

		self._lastSends[item.type] = time.time()
		return (callback, item.payload)

class MessageQueueItem(object):
	def __init__(self, type, timestamp, payload):
		self.type = type
		self.timestamp = timestamp
		self.payload = payload