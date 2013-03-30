# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

import time
import datetime
import threading
import copy
import os

import octoprint.util.comm as comm
import octoprint.util as util

from octoprint.settings import settings

def getConnectionOptions():
	"""
	 Retrieves the available ports, baudrates, prefered port and baudrate for connecting to the printer.
	"""
	return {
		"ports": comm.serialList(),
		"baudrates": comm.baudrateList(),
		"portPreference": settings().get(["serial", "port"]),
		"baudratePreference": settings().getInt(["serial", "baudrate"])
	}

class Printer():
	def __init__(self, gcodeManager):
		self._gcodeManager = gcodeManager

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
		self._tempBacklog = []

		self._latestMessage = None
		self._messages = []
		self._messageBacklog = []

		self._latestLog = None
		self._log = []
		self._logBacklog = []

		self._state = None

		self._currentZ = None

		self._progress = None
		self._printTime = None
		self._printTimeLeft = None

		# gcode handling
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

		self._stateMonitor = StateMonitor(
			ratelimit=0.5,
			updateCallback=self._sendCurrentDataCallbacks,
			addTemperatureCallback=self._sendAddTemperatureCallbacks,
			addLogCallback=self._sendAddLogCallbacks,
			addMessageCallback=self._sendAddMessageCallbacks
		)
		self._stateMonitor.reset(
			state={"state": None, "stateString": self.getStateString(), "flags": self._getStateFlags()},
			jobData={"filename": None, "lines": None, "estimatedPrintTime": None, "filament": None},
			gcodeData={"filename": None, "progress": None},
			progress={"progress": None, "printTime": None, "printTimeLeft": None},
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

	def loadGcode(self, file, printAfterLoading=False):
		"""
		 Loads the gcode from the given file as the new print job.
		 Aborts if the printer is currently printing or another gcode file is currently being loaded.
		"""
		if (self._comm is not None and self._comm.isPrinting()) or (self._gcodeLoader is not None):
			return

		self._setJobData(None, None)

		onGcodeLoadedCallback = self._onGcodeLoaded
		if printAfterLoading:
			onGcodeLoadedCallback = self._onGcodeLoadedToPrint

		self._gcodeLoader = GcodeLoader(file, self._onGcodeLoadingProgress, onGcodeLoadedCallback)
		self._gcodeLoader.start()

		self._stateMonitor.setState({"state": self._state, "stateString": self.getStateString(), "flags": self._getStateFlags()})
	
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
			self.commands(["M84", "M104 S0", "M140 S0", "M106 S0"]) # disable motors, switch off heaters and fan

		# reset line, height, print time
		self._setCurrentZ(None)
		self._setProgressData(None, None, None)

		# mark print as failure
		self._gcodeManager.printFailed(self._filename)

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

		formattedCurrentZ = None
		if self._currentZ:
			formattedCurrentZ = "%.2f mm" % (self._currentZ)
		self._stateMonitor.setCurrentZ(formattedCurrentZ)

	def _setState(self, state):
		self._state = state
		self._stateMonitor.setState({"state": self._state, "stateString": self.getStateString(), "flags": self._getStateFlags()})

	def _addLog(self, log):
		self._log.append(log)
		self._log = self._log[-300:]
		self._stateMonitor.addLog(log)

	def _addMessage(self, message):
		self._messages.append(message)
		self._messages = self._messages[-300:]
		self._stateMonitor.addMessage(message)

	def _setProgressData(self, progress, printTime, printTimeLeft):
		self._progress = progress
		self._printTime = printTime
		self._printTimeLeft = printTimeLeft

		formattedPrintTime = None
		if (self._printTime):
			formattedPrintTime = util.getFormattedTimeDelta(datetime.timedelta(seconds=self._printTime))

		formattedPrintTimeLeft = None
		if (self._printTimeLeft):
			formattedPrintTimeLeft = util.getFormattedTimeDelta(datetime.timedelta(minutes=self._printTimeLeft))

		self._stateMonitor.setProgress({"progress": self._progress, "printTime": formattedPrintTime, "printTimeLeft": formattedPrintTimeLeft})

	def _addTemperatureData(self, temp, bedTemp, targetTemp, bedTargetTemp):
		currentTimeUtc = int(time.time() * 1000)

		self._temps["actual"].append((currentTimeUtc, temp))
		self._temps["actual"] = self._temps["actual"][-300:]

		self._temps["target"].append((currentTimeUtc, targetTemp))
		self._temps["target"] = self._temps["target"][-300:]

		self._temps["actualBed"].append((currentTimeUtc, bedTemp))
		self._temps["actualBed"] = self._temps["actualBed"][-300:]

		self._temps["targetBed"].append((currentTimeUtc, bedTargetTemp))
		self._temps["targetBed"] = self._temps["targetBed"][-300:]

		self._temp = temp
		self._bedTemp = bedTemp
		self._targetTemp = targetTemp
		self._targetBedTemp = bedTargetTemp

		self._stateMonitor.addTemperature({"currentTime": currentTimeUtc, "temp": self._temp, "bedTemp": self._bedTemp, "targetTemp": self._targetTemp, "targetBedTemp": self._targetBedTemp})

	def _setJobData(self, filename, gcodeList):
		self._filename = filename
		self._gcodeList = gcodeList

		lines = None
		if self._gcodeList:
			lines = len(self._gcodeList)

		formattedFilename = None
		estimatedPrintTime = None
		filament = None
		if self._filename:
			formattedFilename = os.path.basename(self._filename)

			fileData = self._gcodeManager.getFileData(filename)
			if fileData is not None and "gcodeAnalysis" in fileData.keys():
				if "estimatedPrintTime" in fileData["gcodeAnalysis"].keys():
					estimatedPrintTime = fileData["gcodeAnalysis"]["estimatedPrintTime"]
				if "filament" in fileData["gcodeAnalysis"].keys():
					filament = fileData["gcodeAnalysis"]["filament"]

		self._stateMonitor.setJobData({"filename": formattedFilename, "lines": lines, "estimatedPrintTime": estimatedPrintTime, "filament": filament})

	def _sendInitialStateUpdate(self, callback):
		try:
			data = self._stateMonitor.getCurrentData()
			data.update({
				"temperatureHistory": self._temps,
				"logHistory": self._log,
				"messageHistory": self._messages
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

		# forward relevant state changes to timelapse
		if self._timelapse is not None:
			if oldState == self._comm.STATE_PRINTING and state != self._comm.STATE_PAUSED:
				self._timelapse.onPrintjobStopped()
			elif state == self._comm.STATE_PRINTING and oldState != self._comm.STATE_PAUSED:
				self._timelapse.onPrintjobStarted(self._filename)

		# forward relevant state changes to gcode manager
		if self._comm is not None and oldState == self._comm.STATE_PRINTING:
			if state == self._comm.STATE_OPERATIONAL:
				self._gcodeManager.printSucceeded(self._filename)
			elif state == self._comm.STATE_CLOSED or state == self._comm.STATE_ERROR or state == self._comm.STATE_CLOSED_WITH_ERROR:
				self._gcodeManager.printFailed(self._filename)
			self._gcodeManager.resumeAnalysis() # do not analyse gcode while printing
		elif self._comm is not None and state == self._comm.STATE_PRINTING:
			self._gcodeManager.pauseAnalysis() # printing done, put those cpu cycles to good use

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

	def _onGcodeLoadingProgress(self, filename, progress, mode):
		formattedFilename = None
		if filename is not None:
			formattedFilename = os.path.basename(filename)

		self._stateMonitor.setGcodeData({"filename": formattedFilename, "progress": progress, "mode": mode})

	def _onGcodeLoaded(self, filename, gcodeList):
		self._setJobData(filename, gcodeList)
		self._setCurrentZ(None)
		self._setProgressData(None, None, None)
		self._gcodeLoader = None

		self._stateMonitor.setGcodeData({"filename": None, "progress": None})
		self._stateMonitor.setState({"state": self._state, "stateString": self.getStateString(), "flags": self._getStateFlags()})

	def _onGcodeLoadedToPrint(self, filename, gcodeList):
		self._onGcodeLoaded(filename, gcodeList)
		self.startPrint()

	#~~ state reports

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
		gcodeList = ["M110"]
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
		self._currentZ = None
		self._progress = None

		self._changeEvent = threading.Event()

		self._lastUpdate = time.time()
		self._worker = threading.Thread(target=self._work)
		self._worker.daemon = True
		self._worker.start()

	def reset(self, state=None, jobData=None, gcodeData=None, progress=None, currentZ=None):
		self.setState(state)
		self.setJobData(jobData)
		self.setGcodeData(gcodeData)
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

	def setGcodeData(self, gcodeData):
		self._gcodeData = gcodeData
		self._changeEvent.set()

	def setProgress(self, progress):
		self._progress = progress
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
			"gcode": self._gcodeData,
			"currentZ": self._currentZ,
			"progress": self._progress
		}

