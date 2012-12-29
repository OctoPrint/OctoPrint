# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"

import time
import os
from threading import Thread

import Cura.util.machineCom as machineCom
from Cura.util import gcodeInterpreter
from Cura.util import profile

def getConnectionOptions():
	"""
	 Retrieves the available ports, baudrates, prefered port and baudrate for connecting to the printer.
	"""
	return {
		"ports": machineCom.serialList(),
		"baudrates": sorted(machineCom.baudrateList(), key=int, reverse=True),
		"portPreference": profile.getPreference('serial_port_auto'),
		"baudratePreference": int(profile.getPreference('serial_baud_auto'))
	}

class Printer():
	def __init__(self):
		# state
		self.temps = {
			"actual": [],
			"target": [],
			"actualBed": [],
			"targetBed": []
		}
		self.messages = []
		self.log = []
		self.state = None
		self.currentZ = None
		self.progress = None
		self.printTime = None
		self.printTimeLeft = None
		self.currentTemp = None
		self.currentBedTemp = None
		self.currentTargetTemp = None
		self.currentBedTargetTemp = None

		self.gcode = None
		self.gcodeList = None
		self.filename = None

		self.gcodeLoader = None

		self.feedrateModifierMapping = {"outerWall": "WALL-OUTER", "innerWall": "WALL_INNER", "fill": "FILL", "support": "SUPPORT"}

		# comm
		self.comm = None

	def connect(self, port=None, baudrate=None):
		"""
		 Connects to the printer. If port and/or baudrate is provided, uses these settings, otherwise autodetection
		 will be attempted.
		"""
		if self.comm is not None:
			self.comm.close()
		self.comm = machineCom.MachineCom(port, baudrate, callbackObject=self)

	def disconnect(self):
		"""
		 Closes the connection to the printer.
		"""
		if self.comm is not None:
			self.comm.close()
		self.comm = None

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
			self.comm.sendCommand(command)

	def setFeedrateModifier(self, structure, percentage):
		if (not self.feedrateModifierMapping.has_key(structure)) or percentage < 0:
			return

		self.comm.setFeedrateModifier(self.feedrateModifierMapping[structure], percentage / 100.0)

	def mcLog(self, message):
		"""
		 Callback method for the comm object, called upon log output.
		 Log line is stored in internal buffer, which is truncated to the last 300 lines.
		"""
		self.log.append(message)
		self.log = self.log[-300:]

	def mcTempUpdate(self, temp, bedTemp, targetTemp, bedTargetTemp):
		"""
		 Callback method for the comm object, called upon receiving new temperature information.
		 Temperature information (actual and target) for print head and print bed is stored in corresponding
		 temperature history (including timestamp), history is truncated to 300 entries.
		"""
		currentTime = int(time.time() * 1000)

		self.temps["actual"].append((currentTime, temp))
		self.temps["actual"] = self.temps["actual"][-300:]

		self.temps["target"].append((currentTime, targetTemp))
		self.temps["target"] = self.temps["target"][-300:]

		self.temps["actualBed"].append((currentTime, bedTemp))
		self.temps["actualBed"] = self.temps["actualBed"][-300:]

		self.temps["targetBed"].append((currentTime, bedTargetTemp))
		self.temps["targetBed"] = self.temps["targetBed"][-300:]

		self.currentTemp = temp
		self.currentTargetTemp = targetTemp
		self.currentBedTemp = bedTemp
		self.currentBedTargetTemp = bedTargetTemp

	def mcStateChange(self, state):
		"""
		 Callback method for the comm object, called if the connection state changes.
		 New state is stored for retrieval by the frontend.
		"""
		self.state = state

	def mcMessage(self, message):
		"""
		 Callback method for the comm object, called upon message exchanges via serial.
		 Stores the message in the message buffer, truncates buffer to the last 300 lines.
		"""
		self.messages.append(message)
		self.messages = self.messages[-300:]

	def mcProgress(self, lineNr):
		"""
		 Callback method for the comm object, called upon any change in progress of the printjob.
		 Triggers storage of new values for printTime, printTimeLeft and the current line.
		"""
		self.printTime = self.comm.getPrintTime()
		self.printTimeLeft = self.comm.getPrintTimeRemainingEstimate()
		self.progress = self.comm.getPrintPos()

	def mcZChange(self, newZ):
		"""
		 Callback method for the comm object, called upon change of the z-layer.
		"""
		self.currentZ = newZ

	def onGcodeLoaded(self, gcodeLoader):
		"""
		 Callback method for the gcode loader, gets called when the gcode for the new printjob has finished loading.
		 Takes care to set filename, gcode and commandlist from the gcode loader and reset print job progress.
		"""
		self.filename = gcodeLoader.filename
		self.gcode = gcodeLoader.gcode
		self.gcodeList = gcodeLoader.gcodeList
		self.currentZ = None
		self.progress = None
		self.printTime = None
		self.printTimeLeft = None

		self.gcodeLoader = None

	def jobData(self):
		"""
		 Returns statistics regarding the currently loaded printjob, or None if no printjob is loaded.
		"""
		if self.gcode is not None:
			formattedPrintTime = None
			if (self.printTime):
				formattedPrintTime = "%02d:%02d" % (int(self.printTime / 60), int(self.printTime % 60))

			formattedPrintTimeLeft = None
			if (self.printTimeLeft):
				formattedPrintTimeLeft = "%02d:%02d" % (int(self.printTimeLeft / 60), int(self.printTimeLeft % 60))

			data = {
				"filename": self.filename,
				"currentZ": self.currentZ,
				"line": self.progress,
				"totalLines": len(self.gcodeList),
				"printTime": formattedPrintTime,
				"printTimeLeft": formattedPrintTimeLeft,
				"filament": "%.2fm %.2fg" % (
					self.gcode.extrusionAmount / 1000,
					self.gcode.calculateWeight() * 1000
				),
				"estimatedPrintTime": "%02d:%02d" % (
					int(self.gcode.totalMoveTimeMinute / 60),
					int(self.gcode.totalMoveTimeMinute % 60)
				)
			}
		else:
			data = None
		return data

	def gcodeState(self):
		if self.gcodeLoader is not None:
			return {
				"filename": self.gcodeLoader.filename,
				"progress": self.gcodeLoader.progress
			}
		else:
			return None

	def feedrateState(self):
		if self.comm is not None:
			feedrateModifiers = self.comm.getFeedrateModifiers()
			result = {}
			for structure in self.feedrateModifierMapping.keys():
				if (feedrateModifiers.has_key(self.feedrateModifierMapping[structure])):
					result[structure] = int(round(feedrateModifiers[self.feedrateModifierMapping[structure]] * 100))
				else:
					result[structure] = 100
			return result
		else:
			return None

	def getStateString(self):
		"""
		 Returns a human readable string corresponding to the current communication state.
		"""
		if self.comm is None:
			return "Offline"
		else:
			return self.comm.getStateString()

	def isClosedOrError(self):
		return self.comm is None or self.comm.isClosedOrError()

	def isOperational(self):
		return self.comm is not None and self.comm.isOperational()

	def isPrinting(self):
		return self.comm is not None and self.comm.isPrinting()

	def isPaused(self):
		return self.comm is not None and self.comm.isPaused()

	def isError(self):
		return self.comm is not None and self.comm.isError()

	def isReady(self):
		return self.gcodeLoader is None and self.gcodeList and len(self.gcodeList) > 0

	def isLoading(self):
		return self.gcodeLoader is not None

	def loadGcode(self, file):
		"""
		 Loads the gcode from the given file as the new print job.
		 Aborts if the printer is currently printing or another gcode file is currently being loaded.
		"""
		if (self.comm is not None and self.comm.isPrinting()) or (self.gcodeLoader is not None):
			return

		self.filename = None
		self.gcode = None
		self.gcodeList = None

		self.gcodeLoader = GcodeLoader(file, self)
		self.gcodeLoader.start()

	def startPrint(self):
		"""
		 Starts the currently loaded print job.
		 Only starts if the printer is connected and operational, not currently printing and a printjob is loaded
		"""
		if self.comm is None or not self.comm.isOperational():
			return
		if self.gcodeList is None:
			return
		if self.comm.isPrinting():
			return
		self.currentZ = -1
		self.comm.printGCode(self.gcodeList)

	def togglePausePrint(self):
		"""
		 Pause the current printjob.
		"""
		if self.comm is None:
			return
		self.comm.setPause(not self.comm.isPaused())

	def cancelPrint(self, disableMotorsAndHeater=True):
		"""
		 Cancel the current printjob.
		"""
		if self.comm is None:
			return
		self.comm.cancelPrint()
		if disableMotorsAndHeater:
			self.commands(["M84", "M104 S0", "M140 S0"]) # disable motors, switch off heaters

		# reset line, height, print time
		self.currentZ = None
		self.progress = None
		self.printTime = None
		self.printTimeLeft = None

class GcodeLoader(Thread):
	"""
	 The GcodeLoader takes care of loading a gcode-File from disk and parsing it into a gcode object in a separate
	 thread while constantly notifying interested listeners about the current progress.
	 The progress is returned as a float value between 0 and 1 which is to be interpreted as the percentage of completion.
	"""

	def __init__(self, filename, printerCallback):
		Thread.__init__(self);

		self.printerCallback = printerCallback;

		self.filename = filename
		self.progress = None

		self.gcode = None
		self.gcodeList = None

	def run(self):
		#Send an initial M110 to reset the line counter to zero.
		prevLineType = lineType = "CUSTOM"
		gcodeList = ["M110"]
		with open(self.filename, "r") as file:
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

		self.gcodeList = gcodeList
		self.gcode = gcodeInterpreter.gcode()
		self.gcode.progressCallback = self.onProgress
		self.gcode.loadList(self.gcodeList)

		self.printerCallback.onGcodeLoaded(self)

	def onProgress(self, progress):
		self.progress = progress

