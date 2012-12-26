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
		self.currentTargetTemp = None
		self.currentBedTargetTemp = None

		self.gcode = None
		self.gcodeList = None
		self.filename = None

		# comm
		self.comm = None

	def connect(self):
		if self.comm != None:
			self.comm.close()
		self.comm = machineCom.MachineCom(callbackObject=self)

	def disconnect(self):
		if self.comm != None:
			self.comm.close()
		self.comm = None

	def command(self, command):
		self.commands([command])

	def commands(self, commands):
		for command in commands:
			self.comm.sendCommand(command)

	def mcLog(self, message):
		self.log.append(message)
		self.log = self.log[-300:]

	def mcTempUpdate(self, temp, bedTemp, targetTemp, bedTargetTemp):
		currentTime = int(time.time() * 1000)

		self.temps['actual'].append((currentTime, temp))
		self.temps['actual'] = self.temps['actual'][-300:]

		self.temps['target'].append((currentTime, targetTemp))
		self.temps['target'] = self.temps['target'][-300:]

		self.temps['actualBed'].append((currentTime, bedTemp))
		self.temps['actualBed'] = self.temps['actualBed'][-300:]

		self.temps['targetBed'].append((currentTime, bedTargetTemp))
		self.temps['targetBed'] = self.temps['targetBed'][-300:]

		self.currentTemp = temp
		self.currentTargetTemp = targetTemp
		self.currentBedTemp = bedTemp
		self.currentBedTargetTemp = bedTargetTemp

	def mcStateChange(self, state):
		self.state = state

	def mcMessage(self, message):
		self.messages.append(message)
		self.messages = self.messages[-300:]

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
				formattedPrintTime = "%02d:%02d" % (int(self.printTime / 60), int(self.printTime % 60))

			formattedPrintTimeLeft = None
			if (self.printTimeLeft):
				formattedPrintTimeLeft = "%02d:%02d" % (int(self.printTimeLeft / 60), int(self.printTimeLeft % 60))

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

	def isPrinting(self):
		return self.comm != None and self.comm.isPrinting()

	def isPaused(self):
		return self.comm != None and self.comm.isPaused()

	def isError(self):
		return self.comm != None and self.comm.isError()

	def isReady(self):
		return self.gcodeList and len(self.gcodeList) > 0

	def loadGcode(self, file):
		if self.comm != None and self.comm.isPrinting():
			return

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
		self.currentZ = None
		self.progress = None
		self.printTime = None
		self.printTimeLeft = None

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
		self.comm.sendCommands(["M84", "M104 S0", "M140 S0"]) # disable motors, switch off heaters

