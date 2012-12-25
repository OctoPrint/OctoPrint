# coding=utf-8
__author__ = 'Gina Häußge <osd@foosel.net>'

import time
import os

import Cura.util.machineCom as machineCom
from Cura.util import gcodeInterpreter

class Printer():
	def __init__(self):
		# state
		self.temps = {
			'actual': [],
			'target': [],
			'actualBed': [],
			'targetBed': []
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

		self.gcode = None
		self.gcodeList = None
		self.filename = None

		# comm
		self.comm = None

	def connect(self):
		if self.comm != None:
			self.comm.close()
		self.comm = machineCom.MachineCom(port='VIRTUAL', callbackObject=self)

	def disconnect(self):
		if self.comm != None:
			self.comm.close()
		self.comm = None

	def command(self, command):
		self.comm.sendCommand(command)

	def mcLog(self, message):
		self.log.append(message)
		self.log = self.log[-300:]

	def mcTempUpdate(self, temp, bedTemp, targetTemp, bedTargetTemp):
		currentTime = time.time()

		self.temps['actual'].append((currentTime, temp))
		self.temps['actual'] = self.temps['actual'][-300:]

		self.temps['target'].append((currentTime, targetTemp))
		self.temps['target'] = self.temps['target'][-300:]

		self.temps['actualBed'].append((currentTime, bedTemp))
		self.temps['actualBed'] = self.temps['actualBed'][-300:]

		self.temps['targetBed'].append((currentTime, bedTargetTemp))
		self.temps['targetBed'] = self.temps['targetBed'][-300:]

		self.currentTemp = temp
		self.currentBedTemp = bedTemp

	def mcStateChange(self, state):
		self.state = state

	def mcMessage(self, message):
		self.messages.append(message)
		self.messages = self.message[-300:]

	def mcProgress(self, lineNr):
		self.printTime = self.comm.getPrintTime()
		self.printTimeLeft = self.comm.getPrintTimeRemainingEstimate()
		self.progress = self.comm.getPrintPos()

	def mcZChange(self, newZ):
		self.currentZ = newZ

	def jobData(self):
		if self.gcode != None:
			formattedPrintTime = None
			if (self.printTime):
				"%02d:%02d" % (int(self.printTime / 60), int(self.printTime % 60))

			formattedPrintTimeLeft = None
			if (self.printTimeLeft):
				"%02d:%02d" % (int(self.printTimeLeft / 60), int(self.printTimeLeft % 60))

			data = {
				'currentZ': self.currentZ,
				'line': self.progress,
				'totalLines': len(self.gcodeList),
				'printTime': formattedPrintTime,
				'printTimeLeft': formattedPrintTimeLeft,
				'filament': "%.2fm %.2fg" % (
					self.gcode.extrusionAmount / 1000,
					self.gcode.calculateWeight() * 1000
				),
				'estimatedPrintTime': "%02d:%02d" % (
					int(self.gcode.totalMoveTimeMinute / 60),
					int(self.gcode.totalMoveTimeMinute % 60)
				)
			}
		else:
			data = None
		return data

	def getStateString(self):
		if self.comm == None:
			return 'Offline'
		else:
			return self.comm.getStateString()

	def isClosedOrError(self):
		return self.comm == None or self.comm.isClosedOrError()

	def isOperational(self):
		return self.comm != None and self.comm.isOperational()

	def loadGcode(self, file):
		if self.comm != None and self.comm.isPrinting():
			return

		# delete old temporary file
		if self.filename != None:
			os.remove(self.filename)

		#Send an initial M110 to reset the line counter to zero.
		prevLineType = lineType = 'CUSTOM'
		gcodeList = ["M110"]
		for line in open(file, 'r'):
			if line.startswith(';TYPE:'):
				lineType = line[6:].strip()
			if ';' in line:
				line = line[0:line.find(';')]
			line = line.strip()
			if len(line) > 0:
				if prevLineType != lineType:
					gcodeList.append((line, lineType, ))
				else:
					gcodeList.append(line)
				prevLineType = lineType
		gcode = gcodeInterpreter.gcode()
		gcode.loadList(gcodeList)
		#print "Loaded: %s (%d)" % (filename, len(gcodeList))
		self.filename = file
		self.gcode = gcode
		self.gcodeList = gcodeList

	def startPrint(self):
		if self.comm == None or not self.comm.isOperational():
			return
		if self.gcodeList == None:
			return
		if self.comm.isPrinting():
			return
		self.currentZ = -1
		self.comm.printGCode(self.gcodeList)

	def togglePausePrint(self):
		if self.comm == None:
			return
		self.comm.setPause(not self.comm.isPaused())

	def cancelPrint(self):
		if self.comm == None:
			return
		self.comm.cancelPrint()
		self.comm.sendCommand("M84")

class Temperature():
	def __init__(self, actual=None, target=None):
		self._actual = actual
		self._target = target

	def actual(self):
		return self._actual

	def target(self):
		return self._target

	def asDict(self):
		return {'actual': self._actual, 'target': self._target}

class Position():
	def __init__(self, x=None, y=None, z=None):
		self._x = x
		self._y = y
		self._z = z

	def update(self, x=None, y=None, z=None):
		if x != None:
			self._x = x
		if y != None:
			self._y = y
		if z != None:
			self._z = z

	def get(self):
		return {'x': self._x, 'y': self._y, 'z': self._z}

