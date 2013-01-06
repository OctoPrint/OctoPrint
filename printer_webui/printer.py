# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

import time
from threading import Thread

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

		# callback throttling
		self._lastProgressReport = None

	#~~ callback registration

	def registerCallback(self, callback):
		self._callbacks.append(callback)
		self._sendInitialStateUpdate(callback)

	def unregisterCallback(self, callback):
		if callback in self._callbacks:
			self._callbacks.remove(callback)

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
		print("Setting currentZ=%s" % str(currentZ))
		self._currentZ = currentZ

		for callback in self._callbacks:
			try: callback.zChangeCB(self._currentZ)
			except: pass

	def _setState(self, state):
		self._state = state

		for callback in self._callbacks:
			try: callback.stateChangeCB(self._state, self.getStateString(), self._getStateFlags())
			except: pass

	def _addLog(self, log):
		"""
		 Log line is stored in internal buffer, which is truncated to the last 300 lines.
		"""
		self._latestLog = log
		self._log.append(log)
		self._log = self._log[-300:]

		for callback in self._callbacks:
			try: callback.logChangeCB(log, self._log)
			except: pass

	def _addMessage(self, message):
		self._latestMessage = message
		self._messages.append(message)
		self._messages = self._messages[-300:]

		for callback in self._callbacks:
			try: callback.messageChangeCB(message, self._messages)
			except: pass

	def _setProgressData(self, progress, printTime, printTimeLeft):
		self._progress = progress
		self._printTime = printTime
		self._printTimeLeft = printTimeLeft

		if self._lastProgressReport and self._lastProgressReport + 0.5 > time.time():
			return

		for callback in self._callbacks:
			try: callback.progressChangeCB(self._progress, self._printTime, self._printTimeLeft)
			except: pass
		self._lastProgressReport = time.time()


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

		for callback in self._callbacks:
			try: callback.temperatureChangeCB(self._temp, self._bedTemp, self._targetTemp, self._targetBedTemp, self._temps)
			except: pass

	def _setJobData(self, filename, gcode, gcodeList):
		self._filename = filename
		self._gcode = gcode
		self._gcodeList = gcodeList

		for callback in self._callbacks:
			try: callback.jobDataChangeCB(filename, len(gcodeList), self._gcode.totalMoveTimeMinute, self._gcode.extrusionAmount)
			except: pass

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
			callback.logChangeCB(self._latestLog, self._log)
			callback.messageChangeCB(self._latestMessage, self._messages)
			callback.progressChangeCB(self._progress, self._printTime, self._printTimeLeft)
			callback.temperatureChangeCB(self._temp, self._bedTemp, self._targetTemp, self._targetBedTemp, self._temps)
			callback.jobDataChangeCB(self._filename, lines, estimatedPrintTime, filament)
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
		print("Got callback for z change: " + str(newZ))
		oldZ = self._currentZ
		if self._timelapse is not None:
			self._timelapse.onZChange(oldZ, newZ)

		self._setCurrentZ(newZ)

	#~~ callbacks triggered by gcodeLoader

	def onGcodeLoadingProgress(self, progress):
		for callback in self._callbacks:
			try: callback.gcodeChangeCB(self._gcodeLoader._filename, progress)
			except Exception, err:
				import sys
				sys.stderr.write("ERROR: %s\n" % str(err))
				pass

	def onGcodeLoaded(self):
		self._setJobData(self._gcodeLoader._filename, self._gcodeLoader._gcode, self._gcodeLoader._gcodeList)
		self._setCurrentZ(None)
		self._setProgressData(None, None, None)

		self._gcodeLoader = None

		for callback in self._callbacks:
			try: callback.stateChangeCB(self._state, self.getStateString(), self._getStateFlags())
			except: pass

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
		Thread.__init__(self);

		self._printerCallback = printerCallback;

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

	def temperatureChangeCB(self, temp, bedTemp, targetTemp, bedTargetTemp, history):
		pass

	def stateChangeCB(self, state, stateString, booleanStates):
		pass

	def logChangeCB(self, line, history):
		pass

	def messageChangeCB(self, line, history):
		pass

	def gcodeChangeCB(self, filename, progress):
		pass

	def jobDataChangeCB(self, filename, lines, estimatedPrintTime, filamentLength):
		pass