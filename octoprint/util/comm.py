from __future__ import absolute_import

import os
import glob
import sys
import time
import math
import re
import traceback
import threading
import Queue as queue
import logging

import serial

from octoprint.util.avr_isp import stk500v2
from octoprint.util.avr_isp import ispBase

from octoprint.util import matchesGcode

from octoprint.settings import settings
from octoprint.events import eventManager

try:
	import _winreg
except:
	pass

def isDevVersion():
	gitPath = os.path.abspath(os.path.join(os.path.split(os.path.abspath(__file__))[0], "../../.git"))
	return os.path.exists(gitPath)

def serialList():
	baselist=[]
	if os.name=="nt":
		try:
			key=_winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,"HARDWARE\\DEVICEMAP\\SERIALCOMM")
			i=0
			while(1):
				baselist+=[_winreg.EnumValue(key,i)[1]]
				i+=1
		except:
			pass
	baselist = baselist \
			   + glob.glob("/dev/ttyUSB*") \
			   + glob.glob("/dev/ttyACM*") \
			   + glob.glob("/dev/ttyAMA*") \
			   + glob.glob("/dev/tty.usb*") \
			   + glob.glob("/dev/cu.*") \
			   + glob.glob("/dev/rfcomm*")
	prev = settings().get(["serial", "port"])
	if prev in baselist:
		baselist.remove(prev)
		baselist.insert(0, prev)
	if isDevVersion():
		baselist.append("VIRTUAL")
	return baselist

def baudrateList():
	ret = [250000, 230400, 115200, 57600, 38400, 19200, 9600]
	prev = settings().getInt(["serial", "baudrate"])
	if prev in ret:
		ret.remove(prev)
		ret.insert(0, prev)
	return ret

gcodeToEvent = {
	"M226": "Waiting",  # pause for user input
	"M0": "Waiting",
	"M1": "Waiting",
	"M245": "Cooling",  # part cooler
	"M240": "Conveyor", # part conveyor
	"M40": "Eject",     # part ejector
	"M300": "Alert",    # user alert
	"G28": "Home",      # home print head
	"M112": "EStop",
	"M80": "PowerOn",
	"M81": "PowerOff"
}

class VirtualPrinter():
	def __init__(self):
		self.readList = ['start\n', 'Marlin: Virtual Marlin!\n', '\x80\n', 'SD init fail\n'] # no sd card as default startup scenario
		self.temp = 0.0
		self.targetTemp = 0.0
		self.lastTempAt = time.time()
		self.bedTemp = 1.0
		self.bedTargetTemp = 1.0

		self._virtualSd = settings().getBaseFolder("virtualSd")
		self._sdCardReady = False
		self._sdPrinter = None
		self._sdPrintingSemaphore = threading.Event()
		self._selectedSdFile = None
		self._selectedSdFileSize = None
		self._selectedSdFilePos = None
		self._writingToSd = False
		self._newSdFilePos = None

		self.currentLine = 0

		waitThread = threading.Thread(target=self._sendWaitAfterTimeout)
		waitThread.start()

	def write(self, data):
		if self.readList is None:
			return

		# strip checksum
		data = data.strip()
		if "*" in data:
			data = data[:data.rfind("*")]
			self.currentLine += 1
		data += "\n"

		# shortcut for writing to SD
		if self._writingToSd and not self._selectedSdFile is None and not "M29" in data:
			with open(self._selectedSdFile, "a") as f:
				f.write(data)
			self.readList.append("ok")
			return

		#print "Send: %s" % (data.rstrip())
		if 'M104' in data or 'M109' in data:
			try:
				self.targetTemp = float(re.search('S([0-9]+)', data).group(1))
			except:
				pass
		if 'M140' in data or 'M190' in data:
			try:
				self.bedTargetTemp = float(re.search('S([0-9]+)', data).group(1))
			except:
				pass

		if 'M105' in data:
			# send simulated temperature data
			self.readList.append("ok T:%.2f /%.2f B:%.2f /%.2f @:64\n" % (self.temp, self.targetTemp, self.bedTemp, self.bedTargetTemp))
		elif 'M20' in data:
			if self._sdCardReady:
				self._listSd()
		elif 'M21' in data:
			self._sdCardReady = True
			self.readList.append("SD card ok")
		elif 'M22' in data:
			self._sdCardReady = False
		elif 'M23' in data:
			if self._sdCardReady:
				filename = data.split(None, 1)[1].strip()
				self._selectSdFile(filename)
		elif 'M24' in data:
			if self._sdCardReady:
				self._startSdPrint()
		elif 'M25' in data:
			if self._sdCardReady:
				self._pauseSdPrint()
		elif 'M26' in data:
			if self._sdCardReady:
				pos = int(re.search("S([0-9]+)", data).group(1))
				self._setSdPos(pos)
		elif 'M27' in data:
			if self._sdCardReady:
				self._reportSdStatus()
		elif 'M28' in data:
			if self._sdCardReady:
				filename = data.split(None, 1)[1].strip()
				self._writeSdFile(filename)
		elif 'M29' in data:
			if self._sdCardReady:
				self._finishSdFile()
		elif 'M30' in data:
			if self._sdCardReady:
				filename = data.split(None, 1)[1].strip()
				self._deleteSdFile(filename)
		elif "M110" in data:
			# reset current line
			self.currentLine = int(re.search('^N([0-9]+)', data).group(1))
			self.readList.append("reset line to %r\n" % self.currentLine)
			self.readList.append("ok\n")
		elif "M114" in data:
			# send dummy position report
			self.readList.append("ok C: X:10.00 Y:3.20 Z:5.20 E:1.24")
		elif "M999" in data:
			# mirror Marlin behaviour
			self.readList.append("Resend: 1")
		elif self.currentLine == 100:
			# simulate a resend at line 100 of the last 5 lines
			self.readList.append("Error: Line Number is not Last Line Number\n")
			self.readList.append("rs %d\n" % (self.currentLine - 5))
		elif len(data.strip()) > 0:
			self.readList.append("ok\n")

	def _listSd(self):
		self.readList.append("Begin file list")
		for osFile in os.listdir(self._virtualSd):
			self.readList.append(osFile.upper())
		self.readList.append("End file list")
		self.readList.append("ok")

	def _selectSdFile(self, filename):
		file = os.path.join(self._virtualSd, filename).lower()
		if not os.path.exists(file) or not os.path.isfile(file):
			self.readList.append("open failed, File: %s." % filename)
		else:
			self._selectedSdFile = file
			self._selectedSdFileSize = os.stat(file).st_size
			self.readList.append("File opened: %s  Size: %d" % (filename, self._selectedSdFileSize))
			self.readList.append("File selected")

	def _startSdPrint(self):
		if self._selectedSdFile is not None:
			if self._sdPrinter is None:
				self._sdPrinter = threading.Thread(target=self._sdPrintingWorker)
				self._sdPrinter.start()
		self._sdPrintingSemaphore.set()
		self.readList.append("ok")

	def _pauseSdPrint(self):
		self._sdPrintingSemaphore.clear()
		self.readList.append("ok")

	def _setSdPos(self, pos):
		self._newSdFilePos = pos

	def _reportSdStatus(self):
		if self._sdPrinter is not None and self._sdPrintingSemaphore.is_set:
			self.readList.append("SD printing byte %d/%d" % (self._selectedSdFilePos, self._selectedSdFileSize))
		else:
			self.readList.append("Not SD printing")

	def _writeSdFile(self, filename):
		file = os.path.join(self._virtualSd, filename).lower()
		if os.path.exists(file):
			if os.path.isfile(file):
				os.remove(file)
			else:
				self.readList.append("error writing to file")

		self._writingToSd = True
		self._selectedSdFile = file
		self.readList.append("Writing to file: %s" % filename)
		self.readList.append("ok")

	def _finishSdFile(self):
		self._writingToSd = False
		self._selectedSdFile = None
		self.readList.append("ok")

	def _sdPrintingWorker(self):
		self._selectedSdFilePos = 0
		with open(self._selectedSdFile, "r") as f:
			for line in f:
				# reset position if requested by client
				if self._newSdFilePos is not None:
					f.seek(self._newSdFilePos)
					self._newSdFilePos = None

				# read current file position
				self._selectedSdFilePos = f.tell()

				# if we are paused, wait for unpausing
				self._sdPrintingSemaphore.wait()

				# set target temps
				if 'M104' in line or 'M109' in line:
					try:
						self.targetTemp = float(re.search('S([0-9]+)', line).group(1))
					except:
						pass
				if 'M140' in line or 'M190' in line:
					try:
						self.bedTargetTemp = float(re.search('S([0-9]+)', line).group(1))
					except:
						pass

				time.sleep(0.01)

		self._sdPrintingSemaphore.clear()
		self._selectedSdFilePos = 0
		self._sdPrinter = None
		self.readList.append("Done printing file")

	def _deleteSdFile(self, filename):
		file = os.path.join(self._virtualSd, filename)
		if os.path.exists(file) and os.path.isfile(file):
			os.remove(file)
		self.readList.append("ok")

	def readline(self):
		if self.readList is None:
			return ''
		n = 0
		timeDiff = self.lastTempAt - time.time()
		self.lastTempAt = time.time()
		if abs(self.temp - self.targetTemp) > 1:
			self.temp += math.copysign(timeDiff * 10, self.targetTemp - self.temp)
			if self.temp < 0:
				self.temp = 0
		if abs(self.bedTemp - self.bedTargetTemp) > 1:
			self.bedTemp += math.copysign(timeDiff * 10, self.bedTargetTemp - self.bedTemp)
			if self.bedTemp < 0:
				self.bedTemp = 0
		while len(self.readList) < 1:
			time.sleep(0.1)
			n += 1
			if n == 20:
				return ''
			if self.readList is None:
				return ''
		time.sleep(0.001)
		return self.readList.pop(0)
	
	def close(self):
		self.readList = None

	def _sendWaitAfterTimeout(self, timeout=5):
		time.sleep(timeout)
		self.readList.append("wait")

class MachineComPrintCallback(object):
	def mcLog(self, message):
		pass
	
	def mcTempUpdate(self, temp, bedTemp, targetTemp, bedTargetTemp):
		pass
	
	def mcStateChange(self, state):
		pass
	
	def mcMessage(self, message):
		pass
	
	def mcProgress(self):
		pass

	def mcZChange(self, newZ):
		pass

	def mcFileSelected(self, filename, filesize, sd):
		pass

	def mcSdStateChange(self, sdReady):
		pass

	def mcSdFiles(self, files):
		pass

	def mcSdPrintingDone(self):
		pass

	def mcFileTransferStarted(self, filename, filesize):
		pass

	def mcReceivedRegisteredMessage(self, command, message):
		pass

class MachineCom(object):
	STATE_NONE = 0
	STATE_OPEN_SERIAL = 1
	STATE_DETECT_SERIAL = 2
	STATE_DETECT_BAUDRATE = 3
	STATE_CONNECTING = 4
	STATE_OPERATIONAL = 5
	STATE_PRINTING = 6
	STATE_PAUSED = 7
	STATE_CLOSED = 8
	STATE_ERROR = 9
	STATE_CLOSED_WITH_ERROR = 10
	STATE_TRANSFERING_FILE = 11
	
	def __init__(self, port = None, baudrate = None, callbackObject = None):
		self._logger = logging.getLogger(__name__)
		self._serialLogger = logging.getLogger("SERIAL")

		if port == None:
			port = settings().get(["serial", "port"])
		if baudrate == None:
			settingsBaudrate = settings().getInt(["serial", "baudrate"])
			if settingsBaudrate is None:
				baudrate = 0
			else:
				baudrate = settingsBaudrate
		if callbackObject == None:
			callbackObject = MachineComPrintCallback()

		self._port = port
		self._baudrate = baudrate
		self._callback = callbackObject
		self._state = self.STATE_NONE
		self._serial = None
		self._baudrateDetectList = baudrateList()
		self._baudrateDetectRetry = 0
		self._temp = 0
		self._bedTemp = 0
		self._targetTemp = 0
		self._bedTargetTemp = 0
		self._commandQueue = queue.Queue()
		self._logQueue = queue.Queue(256)
		self._currentZ = None
		self._heatupWaitStartTime = 0
		self._heatupWaitTimeLost = 0.0

		self._alwaysSendChecksum = settings().getBoolean(["feature", "alwaysSendChecksum"])
		self._currentLine = 0
		self._resendDelta = None
		self._lastLines = []

		self._sendNextLock = threading.Lock()
		self._sendingLock = threading.Lock()

		self.thread = threading.Thread(target=self._monitor)
		self.thread.daemon = True
		self.thread.start()

		# SD status data
		self._sdAvailable = False
		self._sdFileList = False
		self._sdFiles = []

		# print job
		self._currentFile = None

	def _changeState(self, newState):
		if self._state == newState:
			return

		if newState == self.STATE_CLOSED or newState == self.STATE_CLOSED_WITH_ERROR:
			if settings().get(["feature", "sdSupport"]):
				self._sdFileList = False
				self._sdFiles = []
				self._callback.mcSdFiles([])

		oldState = self.getStateString()
		self._state = newState
		self._log('Changing monitoring state from \'%s\' to \'%s\'' % (oldState, self.getStateString()))
		self._callback.mcStateChange(newState)
	
	def getState(self):
		return self._state
	
	def getStateString(self):
		if self._state == self.STATE_NONE:
			return "Offline"
		if self._state == self.STATE_OPEN_SERIAL:
			return "Opening serial port"
		if self._state == self.STATE_DETECT_SERIAL:
			return "Detecting serial port"
		if self._state == self.STATE_DETECT_BAUDRATE:
			return "Detecting baudrate"
		if self._state == self.STATE_CONNECTING:
			return "Connecting"
		if self._state == self.STATE_OPERATIONAL:
			return "Operational"
		if self._state == self.STATE_PRINTING:
			if self.isSdFileSelected():
				return "Printing from SD"
			elif self.isStreaming():
				return "Sending file to SD"
			else:
				return "Printing"
		if self._state == self.STATE_PAUSED:
			return "Paused"
		if self._state == self.STATE_CLOSED:
			return "Closed"
		if self._state == self.STATE_ERROR:
			return "Error: %s" % (self.getShortErrorString())
		if self._state == self.STATE_CLOSED_WITH_ERROR:
			return "Error: %s" % (self.getShortErrorString())
		if self._state == self.STATE_TRANSFERING_FILE:
			return "Transfering file to SD"
		return "?%d?" % (self._state)
	
	def getShortErrorString(self):
		if len(self._errorValue) < 20:
			return self._errorValue
		return self._errorValue[:20] + "..."

	def getErrorString(self):
		return self._errorValue
	
	def isClosedOrError(self):
		return self._state == self.STATE_ERROR or self._state == self.STATE_CLOSED_WITH_ERROR or self._state == self.STATE_CLOSED

	def isError(self):
		return self._state == self.STATE_ERROR or self._state == self.STATE_CLOSED_WITH_ERROR
	
	def isOperational(self):
		return self._state == self.STATE_OPERATIONAL or self._state == self.STATE_PRINTING or self._state == self.STATE_PAUSED or self._state == self.STATE_TRANSFERING_FILE
	
	def isPrinting(self):
		return self._state == self.STATE_PRINTING

	def isSdPrinting(self):
		return self.isSdFileSelected() and self.isPrinting()

	def isSdFileSelected(self):
		return self._currentFile is not None and isinstance(self._currentFile, PrintingSdFileInformation)

	def isStreaming(self):
		return self._currentFile is not None and isinstance(self._currentFile, StreamingGcodeFileInformation)

	def isPaused(self):
		return self._state == self.STATE_PAUSED

	def isBusy(self):
		return self.isPrinting() or self.isPaused()

	def isSdReady(self):
		return self._sdAvailable

	def getPrintProgress(self):
		if self._currentFile is None:
			return None
		return self._currentFile.getProgress()

	def getPrintFilepos(self):
		if self._currentFile is None:
			return None
		return self._currentFile.getFilepos()

	def getPrintTime(self):
		if self._currentFile is None or self._currentFile.getStartTime() is None:
			return None
		else:
			return time.time() - self._currentFile.getStartTime()

	def getPrintTimeRemainingEstimate(self):
		printTime = self.getPrintTime()
		if printTime is None:
			return None

		printTime /= 60
		progress = self._currentFile.getProgress()
		if progress:
			printTimeTotal = printTime / progress
			return printTimeTotal - printTime
		else:
			return None

	def getTemp(self):
		return self._temp
	
	def getBedTemp(self):
		return self._bedTemp
	
	def getLog(self):
		ret = []
		while not self._logQueue.empty():
			ret.append(self._logQueue.get())
		for line in ret:
			self._logQueue.put(line, False)
		return ret
	
	def _monitor(self):
		feedbackControls = settings().getFeedbackControls()

		#Open the serial port.
		if self._port == 'AUTO':
			self._changeState(self.STATE_DETECT_SERIAL)
			programmer = stk500v2.Stk500v2()
			self._log("Serial port list: %s" % (str(serialList())))
			for p in serialList():
				try:
					self._log("Connecting to: %s" % (p))
					programmer.connect(p)
					self._serial = programmer.leaveISP()
					break
				except ispBase.IspError as (e):
					self._log("Error while connecting to %s: %s" % (p, str(e)))
					pass
				except:
					self._log("Unexpected error while connecting to serial port: %s %s" % (p, getExceptionString()))
				programmer.close()
		elif self._port == 'VIRTUAL':
			self._changeState(self.STATE_OPEN_SERIAL)
			self._serial = VirtualPrinter()
		else:
			self._changeState(self.STATE_OPEN_SERIAL)
			try:
				self._log("Connecting to: %s" % (self._port))
				if self._baudrate == 0:
					self._serial = serial.Serial(str(self._port), 115200, timeout=0.1, writeTimeout=10000)
				else:
					self._serial = serial.Serial(str(self._port), self._baudrate, timeout=2, writeTimeout=10000)
			except:
				self._log("Unexpected error while connecting to serial port: %s %s" % (self._port, getExceptionString()))
		if self._serial == None:
			self._log("Failed to open serial port (%s)" % (self._port))
			self._errorValue = 'Failed to autodetect serial port.'
			self._changeState(self.STATE_ERROR)
			eventManager().fire("Error", self.getErrorString())
			return
		self._log("Connected to: %s, starting monitor" % (self._serial))
		if self._baudrate == 0:
			self._changeState(self.STATE_DETECT_BAUDRATE)
		else:
			self._changeState(self.STATE_CONNECTING)

		#Start monitoring the serial port.
		timeout = time.time() + 5
		tempRequestTimeout = timeout
		sdStatusRequestTimeout = timeout
		startSeen = not settings().getBoolean(["feature", "waitForStartOnConnect"])
		heatingUp = False
		while True:
			try:
				line = self._readline()
				if line == None:
					break

				##~~ Error handling
				# No matter the state, if we see an error, goto the error state and store the error for reference.
				if line.startswith('Error:'):
					#Oh YEAH, consistency.
					# Marlin reports an MIN/MAX temp error as "Error:x\n: Extruder switched off. MAXTEMP triggered !\n"
					#	But a bed temp error is reported as "Error: Temperature heated bed switched off. MAXTEMP triggered !!"
					#	So we can have an extra newline in the most common case. Awesome work people.
					if re.match('Error:[0-9]\n', line):
						line = line.rstrip() + self._readline()
					#Skip the communication errors, as those get corrected.
					if 'checksum mismatch' in line \
							or 'Wrong checksum' in line \
							or 'Line Number is not Last Line Number' in line \
							or 'expected line' in line \
							or 'No Line Number with checksum' in line \
							or 'No Checksum with line number' in line \
							or 'Missing checksum' in line:
						pass
					elif not self.isError():
						self._errorValue = line[6:]
						self._changeState(self.STATE_ERROR)
						eventManager().fire("Error", self.getErrorString())

				##~~ SD file list
				# if we are currently receiving an sd file list, each line is just a filename, so just read it and abort processing
				if self._sdFileList and not 'End file list' in line:
					self._sdFiles.append(line.strip().lower())
					continue

				##~~ Temperature processing
				if ' T:' in line or line.startswith('T:'):
					try:
						self._temp = float(re.search("-?[0-9\.]*", line.split('T:')[1]).group(0))
						if ' B:' in line:
							self._bedTemp = float(re.search("-?[0-9\.]*", line.split(' B:')[1]).group(0))

						self._callback.mcTempUpdate(self._temp, self._bedTemp, self._targetTemp, self._bedTargetTemp)
					except ValueError:
						# catch conversion issues, we'll rather just not get the temperature update instead of killing the connection
						pass

					#If we are waiting for an M109 or M190 then measure the time we lost during heatup, so we can remove that time from our printing time estimate.
					if not 'ok' in line:
						heatingUp = True
						if self._heatupWaitStartTime != 0:
							t = time.time()
							self._heatupWaitTimeLost = t - self._heatupWaitStartTime
							self._heatupWaitStartTime = t

				##~~ SD Card handling
				elif 'SD init fail' in line:
					self._sdAvailable = False
					self._sdFiles = []
					self._callback.mcSdStateChange(self._sdAvailable)
				elif 'Not SD printing' in line:
					if self.isSdFileSelected() and self.isPrinting():
						# something went wrong, printer is reporting that we actually are not printing right now...
						self._sdFilePos = 0
						self._changeState(self.STATE_OPERATIONAL)
				elif 'SD card ok' in line:
					self._sdAvailable = True
					self.refreshSdFiles()
					self._callback.mcSdStateChange(self._sdAvailable)
				elif 'Begin file list' in line:
					self._sdFiles = []
					self._sdFileList = True
				elif 'End file list' in line:
					self._sdFileList = False
					self._callback.mcSdFiles(self._sdFiles)
				elif 'SD printing byte' in line:
					# answer to M27, at least on Marlin, Repetier and Sprinter: "SD printing byte %d/%d"
					match = re.search("([0-9]*)/([0-9]*)", line)
					self._currentFile.setFilepos(int(match.group(1)))
					self._callback.mcProgress()
				elif 'File opened' in line:
					# answer to M23, at least on Marlin, Repetier and Sprinter: "File opened:%s Size:%d"
					match = re.search("File opened:\s*(.*?)\s+Size:\s*([0-9]*)", line)
					self._currentFile = PrintingSdFileInformation(match.group(1), int(match.group(2)))
				elif 'File selected' in line:
					# final answer to M23, at least on Marlin, Repetier and Sprinter: "File selected"
					self._callback.mcFileSelected(self._currentFile.getFilename(), self._currentFile.getFilesize(), True)
					eventManager().fire("FileSelected", self._currentFile.getFilename())
				elif 'Writing to file' in line:
					# anwer to M28, at least on Marlin, Repetier and Sprinter: "Writing to file: %s"
					self._printSection = "CUSTOM"
					self._changeState(self.STATE_PRINTING)
				elif 'Done printing file' in line:
					# printer is reporting file finished printing
					self._sdFilePos = 0
					self._callback.mcPrintjobDone()
					self._changeState(self.STATE_OPERATIONAL)
					eventManager().fire("PrintDone")

				##~~ Message handling
				elif line.strip() != '' and line.strip() != 'ok' and not line.startswith("wait") and not line.startswith('Resend:') and line != 'echo:Unknown command:""\n' and self.isOperational():
					self._callback.mcMessage(line)

				##~~ Parsing for feedback commands
				if feedbackControls:
					for name, matcher, template in feedbackControls:
						try:
							match = matcher.search(line)
							if match is not None:
								self._callback.mcReceivedRegisteredMessage(name, str.format(template, *(match.groups("n/a"))))
						except:
							# ignored on purpose
							pass

				if "ok" in line and heatingUp:
					heatingUp = False

				### Baudrate detection
				if self._state == self.STATE_DETECT_BAUDRATE:
					if line == '' or time.time() > timeout:
						if len(self._baudrateDetectList) < 1:
							self.close()
							self._errorValue = "No more baudrates to test, and no suitable baudrate found."
							self._changeState(self.STATE_ERROR)
							eventManager().fire("Error", self.getErrorString())
						elif self._baudrateDetectRetry > 0:
							self._baudrateDetectRetry -= 1
							self._serial.write('\n')
							self._log("Baudrate test retry: %d" % (self._baudrateDetectRetry))
							self._sendCommand("M105")
							self._testingBaudrate = True
						else:
							baudrate = self._baudrateDetectList.pop(0)
							try:
								self._serial.baudrate = baudrate
								self._serial.timeout = 0.5
								self._log("Trying baudrate: %d" % (baudrate))
								self._baudrateDetectRetry = 5
								self._baudrateDetectTestOk = 0
								timeout = time.time() + 5
								self._serial.write('\n')
								self._sendCommand("M105")
								self._testingBaudrate = True
							except:
								self._log("Unexpected error while setting baudrate: %d %s" % (baudrate, getExceptionString()))
					elif 'ok' in line and 'T:' in line:
						self._baudrateDetectTestOk += 1
						if self._baudrateDetectTestOk < 10:
							self._log("Baudrate test ok: %d" % (self._baudrateDetectTestOk))
							self._sendCommand("M105")
						else:
							self._sendCommand("M999")
							self._serial.timeout = 2
							self._changeState(self.STATE_OPERATIONAL)
							if self._sdAvailable:
								self.refreshSdFiles()
							eventManager().fire("Connected", "%s at %s baud" % (self._port, self._baudrate))
					else:
						self._testingBaudrate = False

				### Connection attempt
				elif self._state == self.STATE_CONNECTING:
					if (line == "" or "wait" in line) and startSeen:
						self._sendCommand("M105")
					elif "start" in line:
						startSeen = True
					elif "ok" in line and startSeen:
						self._changeState(self.STATE_OPERATIONAL)
						if self._sdAvailable:
							self.refreshSdFiles()
						eventManager().fire("Connected", "%s at %s baud" % (self._port, self._baudrate))
					elif time.time() > timeout:
						self.close()

				### Operational
				elif self._state == self.STATE_OPERATIONAL or self._state == self.STATE_PAUSED:
					#Request the temperature on comm timeout (every 5 seconds) when we are not printing.
					if line == "" or "wait" in line:
						if self._resendDelta is not None:
							self._resendNextCommand()
						elif not self._commandQueue.empty():
							self._sendCommand(self._commandQueue.get())
						else:
							self._sendCommand("M105")
						tempRequestTimeout = time.time() + 5
					# resend -> start resend procedure from requested line
					elif "resend" in line.lower() or "rs" in line:
						self._handleResendRequest(line)

				### Printing
				elif self._state == self.STATE_PRINTING:
					if line == "" and time.time() > timeout:
						self._log("Communication timeout during printing, forcing a line")
						line = 'ok'

					if self.isSdPrinting():
						if time.time() > tempRequestTimeout and not heatingUp:
							self._sendCommand("M105")
							tempRequestTimeout = time.time() + 5

						if time.time() > sdStatusRequestTimeout and not heatingUp:
							self._sendCommand("M27")
							sdStatusRequestTimeout = time.time() + 1

						if 'ok' or 'SD printing byte' in line:
							timeout = time.time() + 5
					else:
						# Even when printing request the temperature every 5 seconds.
						if time.time() > tempRequestTimeout and not self.isStreaming():
							self._commandQueue.put("M105")
							tempRequestTimeout = time.time() + 5

						if 'ok' in line:
							timeout = time.time() + 5
							if self._resendDelta is not None:
								self._resendNextCommand()
							elif not self._commandQueue.empty() and not self.isStreaming():
								self._sendCommand(self._commandQueue.get())
							else:
								self._sendNext()
						elif "resend" in line.lower() or "rs" in line:
							self._handleResendRequest(line)
			except:
				self._logger.exception("Something crashed inside the serial connection loop, please report this in OctoPrint's bug tracker:")

				errorMsg = "See octoprint.log for details"
				self._log(errorMsg)
				self._errorValue = errorMsg
				self._changeState(self.STATE_ERROR)
				eventManager().fire("Error", self.getErrorString())
		self._log("Connection closed, closing down monitor")

	def _handleResendRequest(self, line):
		lineToResend = None
		try:
			lineToResend = int(line.replace("N:"," ").replace("N"," ").replace(":"," ").split()[-1])
		except:
			if "rs" in line:
				lineToResend = int(line.split()[1])

		if lineToResend is not None:
			self._resendDelta = self._currentLine - lineToResend
			if self._resendDelta > len(self._lastLines) or len(self._lastLines) == 0:
				self._errorValue = "Printer requested line %d but no sufficient history is available, can't resend" % lineToResend
				self._logger.warn(self._errorValue)
				if self.isPrinting():
					# abort the print, there's nothing we can do to rescue it now
					self._changeState(self.STATE_ERROR)
					eventManager().fire("Error", self.getErrorString())
				else:
					# reset resend delta, we can't do anything about it
					self._resendDelta = None
			else:
				self._resendNextCommand()

	def _log(self, message):
		self._callback.mcLog(message)
		self._serialLogger.debug(message)
		try:
			self._logQueue.put(message, False)
		except:
			#If the log queue is full, remove the first message and append the new message again
			self._logQueue.get()
			try:
				self._logQueue.put(message, False)
			except:
				pass

	def _readline(self):
		if self._serial == None:
			return None
		try:
			ret = self._serial.readline()
		except:
			self._log("Unexpected error while reading serial port: %s" % (getExceptionString()))
			self._errorValue = getExceptionString()
			self.close(True)
			return None
		if ret == '':
			#self._log("Recv: TIMEOUT")
			return ''
		self._log("Recv: %s" % (unicode(ret, 'ascii', 'replace').encode('ascii', 'replace').rstrip()))
		return ret
	
	def close(self, isError = False):
		printing = self.isPrinting() or self.isPaused()
		if self._serial is not None:
			self._serial.close()
			if isError:
				self._changeState(self.STATE_CLOSED_WITH_ERROR)
			else:
				self._changeState(self.STATE_CLOSED)
		self._serial = None

		if settings().get(["feature", "sdSupport"]):
			self._sdFileList = []

		if printing:
			eventManager().fire("PrintFailed")
		eventManager().fire("Disconnected")

	def __del__(self):
		self.close()

	def _resendNextCommand(self):
		# Make sure we are only handling one sending job at a time
		with self._sendingLock:
			self._logger.debug("Resending line %d, delta is %d, history log is %s items strong" % (self._currentLine - self._resendDelta, self._resendDelta, len(self._lastLines)))
			cmd = self._lastLines[-self._resendDelta]
			lineNumber = self._currentLine - self._resendDelta

			self._doSendWithChecksum(cmd, lineNumber)

			self._resendDelta -= 1
			if self._resendDelta <= 0:
				self._resendDelta = None

	def _sendCommand(self, cmd, sendChecksum=False):
		# Make sure we are only handling one sending job at a time
		with self._sendingLock:
			if self._serial is None:
				return

			if not self.isStreaming():
				for gcode in gcodeToEvent.keys():
					if matchesGcode(cmd, gcode):
						eventManager().fire(gcodeToEvent[gcode])

				if matchesGcode(cmd, "M109") or matchesGcode(cmd, "M190"):
					self._heatupWaitStartTime = time.time()
				if matchesGcode(cmd, "M104") or matchesGcode(cmd, "M109"):
					try:
						self._targetTemp = float(re.search('S([0-9]+)', cmd).group(1))
					except:
						pass
				if matchesGcode(cmd, "M140") or matchesGcode(cmd, "M190"):
					try:
						self._bedTargetTemp = float(re.search('S([0-9]+)', cmd).group(1))
					except:
						pass

				if matchesGcode(cmd, "M110"):
					newLineNumber = None
					if " N" in cmd:
						try:
							newLineNumber = int(re.search("N([0-9]+)", cmd).group(1))
						except:
							pass
					else:
						newLineNumber = 0

					# send M110 command with new line number
					self._doSendWithChecksum(cmd, newLineNumber)
					self._currentLine = newLineNumber + 1

					# after a reset of the line number we have no way to determine what line exactly the printer now wants
					self._lastLines = []
					self._resendDelta = None
					return
			self._doSend(cmd, sendChecksum)

	def _addToLastLines(self, cmd):
		self._lastLines.append(cmd)
		if len(self._lastLines) > 50:
			self._lastLines = self._lastLines[-50:] # only keep the last 50 lines in memory
		self._logger.debug("Got %d lines of history in memory" % len(self._lastLines))

	def _doSend(self, cmd, sendChecksum=False):
		if sendChecksum or self._alwaysSendChecksum:
			lineNumber = self._currentLine
			self._addToLastLines(cmd)
			self._currentLine += 1
			self._doSendWithChecksum(cmd, lineNumber)
		else:
			self._doSendWithoutChecksum(cmd)

	def _doSendWithChecksum(self, cmd, lineNumber):
		self._logger.debug("Sending cmd '%s' with lineNumber %r" % (cmd, lineNumber))

		checksum = reduce(lambda x,y:x^y, map(ord, "N%d %s" % (lineNumber, cmd)))
		commandToSend = "N%d %s*%d" % (lineNumber, cmd, checksum)
		self._doSendWithoutChecksum(commandToSend)

	def _doSendWithoutChecksum(self, cmd):
		self._log("Send: %s" % cmd)
		try:
			self._serial.write(cmd + '\n')
		except serial.SerialTimeoutException:
			self._log("Serial timeout while writing to serial port, trying again.")
			try:
				self._serial.write(cmd + '\n')
			except:
				self._log("Unexpected error while writing serial port: %s" % (getExceptionString()))
				self._errorValue = getExceptionString()
				self.close(True)
		except:
			self._log("Unexpected error while writing serial port: %s" % (getExceptionString()))
			self._errorValue = getExceptionString()
			self.close(True)

	def _sendNext(self):
		with self._sendNextLock:
			line = self._currentFile.getNext()
			if line is None:
				if self.isStreaming():
					self._sendCommand("M29")
					filename = self._currentFile.getFilename()
					self._currentFile = None
					self._callback.mcFileTransferDone()
					self._changeState(self.STATE_OPERATIONAL)
					eventManager().fire("TransferDone", filename)
				else:
					self._callback.mcPrintjobDone()
					self._changeState(self.STATE_OPERATIONAL)
					eventManager().fire("PrintDone", self._currentFile.getFilename())
				return

			if type(line) is tuple:
				self._printSection = line[1]
				line = line[0]

			if not self.isStreaming():
				try:
					if matchesGcode(line, "M0") or matchesGcode(line, "M1"):
						self.setPause(True)
						line = "M105" # Don't send the M0 or M1 to the machine, as M0 and M1 are handled as an LCD menu pause.
					if (matchesGcode(line, "G0") or matchesGcode(line, "G1")) and 'Z' in line:
						z = float(re.search('Z([0-9\.]*)', line).group(1))
						if self._currentZ != z:
							self._currentZ = z
							self._callback.mcZChange(z)
				except:
					self._log("Unexpected error: %s" % (getExceptionString()))
			self._sendCommand(line, True)
			self._callback.mcProgress()
	
	def sendCommand(self, cmd):
		cmd = cmd.encode('ascii', 'replace')
		if self.isPrinting() and not self.isSdFileSelected():
			self._commandQueue.put(cmd)
		elif self.isOperational():
			self._sendCommand(cmd)
	
	def startPrint(self):
		if not self.isOperational() or self.isPrinting():
			return

		if self._currentFile is None:
			raise ValueError("No file selected for printing")

		self._printSection = "CUSTOM"
		self._changeState(self.STATE_PRINTING)
		eventManager().fire("PrintStarted", self._currentFile.getFilename())

		try:
			self._currentFile.start()
			if self.isSdFileSelected():
				if self.isPaused():
					self.sendCommand("M26 S0")
					self._currentFile.setFilepos(0)
				self.sendCommand("M24")
			else:
				self._sendNext()
		except:
			self._errorValue = getExceptionString()
			self._changeState(self.STATE_ERROR)
			eventManager().fire("Error", self.getErrorString())

	def startFileTransfer(self, filename, remoteFilename):
		if not self.isOperational() or self.isBusy():
			return

		self._currentFile = StreamingGcodeFileInformation(filename)
		self._currentFile.start()

		self.sendCommand("M28 %s" % remoteFilename)
		eventManager().fire("TransferStart", remoteFilename)
		self._callback.mcFileTransferStarted(remoteFilename, self._currentFile.getFilesize())

	def selectFile(self, filename, sd):
		if self.isBusy():
			return

		if sd:
			if not self.isOperational():
				# printer is not connected, can't use SD
				return
			self.sendCommand("M23 %s" % filename)
		else:
			self._currentFile = PrintingGcodeFileInformation(filename)
			eventManager().fire("FileSelected", filename)
			self._callback.mcFileSelected(filename, self._currentFile.getFilesize(), False)

	def cancelPrint(self):
		if not self.isOperational() or self.isStreaming():
			return

		self._changeState(self.STATE_OPERATIONAL)

		if self.isSdFileSelected():
			self.sendCommand("M25")    # pause print
			self.sendCommand("M26 S0") # reset position in file to byte 0
	
		eventManager().fire("PrintCancelled")

	def setPause(self, pause):
		if self.isStreaming():
			return

		if not pause and self.isPaused():
			self._changeState(self.STATE_PRINTING)
			if self.isSdFileSelected():
				self.sendCommand("M24")
			else:
				self._sendNext()
		if pause and self.isPrinting():
			self._changeState(self.STATE_PAUSED)
			if self.isSdFileSelected():
				self.sendCommand("M25") # pause print

			eventManager().fire("Paused")
	
	##~~ SD card handling
	def getSdFiles(self):
		return self._sdFiles

	def startSdFileTransfer(self, filename):
		if not self.isOperational() or self.isBusy():
			return

		self._changeState(self.STATE_TRANSFERING_FILE)
		self.sendCommand("M28 %s" % filename.lower())

	def endSdFileTransfer(self, filename):
		if not self.isOperational() or self.isBusy():
			return

		self.sendCommand("M29 %s" % filename.lower())
		self._changeState(self.STATE_OPERATIONAL)
		self.refreshSdFiles()

	def deleteSdFile(self, filename):
		if not self.isOperational() or (self.isBusy() and self._sdFile == filename.lower()):
			# do not delete a file from sd we are currently printing from
			return

		self.sendCommand("M30 %s" % filename.lower())
		self.refreshSdFiles()

	def refreshSdFiles(self):
		if not self.isOperational() or self.isBusy():
			return
		self.sendCommand("M20")

	def initSdCard(self):
		if not self.isOperational():
			return
		self.sendCommand("M21")

	def releaseSdCard(self):
		if not self.isOperational() or (self.isBusy() and self.isSdFileSelected()):
			# do not release the sd card if we are currently printing from it
			return

		self.sendCommand("M22")
		self._sdAvailable = False
		self._sdFiles = []

		self._callback.mcSdStateChange(self._sdAvailable)
		self._callback.mcSdFiles(self._sdFiles)

def getExceptionString():
	locationInfo = traceback.extract_tb(sys.exc_info()[2])[0]
	return "%s: '%s' @ %s:%s:%d" % (str(sys.exc_info()[0].__name__), str(sys.exc_info()[1]), os.path.basename(locationInfo[0]), locationInfo[2], locationInfo[1])

class PrintingFileInformation(object):
	"""
	Encapsulates information regarding the current file being printed: file name, current position, total size and
	time the print started.
	Allows to reset the current file position to 0 and to calculate the current progress as a floating point
	value between 0 and 1.
	"""

	def __init__(self, filename):
		self._filename = filename
		self._filepos = 0
		self._filesize = None
		self._startTime = None

	def getStartTime(self):
		return self._startTime

	def getFilename(self):
		return self._filename

	def getFilesize(self):
		return self._filesize

	def getFilepos(self):
		return self._filepos

	def getProgress(self):
		"""
		The current progress of the file, calculated as relation between file position and absolute size. Returns -1
		if file size is None or < 1.
		"""
		if self._filesize is None or not self._filesize > 0:
			return -1
		return float(self._filepos) / float(self._filesize)

	def reset(self):
		"""
		Resets the current file position to 0.
		"""
		self._filepos = 0

	def start(self):
		"""
		Marks the print job as started and remembers the start time.
		"""
		self._startTime = time.time()

class PrintingSdFileInformation(PrintingFileInformation):
	"""
	Encapsulates information regarding an ongoing print from SD.
	"""

	def __init__(self, filename, filesize):
		PrintingFileInformation.__init__(self, filename)
		self._filesize = filesize

	def setFilepos(self, filepos):
		"""
		Sets the current file position.
		"""
		self._filepos = filepos

class PrintingGcodeFileInformation(PrintingFileInformation):
	"""
	Encapsulates information regarding an ongoing direct print. Takes care of the needed file handle and ensures
	that the file is closed in case of an error.
	"""

	def __init__(self, filename):
		PrintingFileInformation.__init__(self, filename)
		self._filehandle = None
		self._lineCount = None
		self._firstLine = None
		self._prevLineType = None

		if not os.path.exists(self._filename) or not os.path.isfile(self._filename):
			raise IOError("File %s does not exist" % self._filename)
		self._filesize = os.stat(self._filename).st_size

	def start(self):
		"""
		Opens the file for reading and determines the file size. Start time won't be recorded until 100 lines in
		"""
		self._filehandle = open(self._filename, "r")
		self._lineCount = None
		self._prevLineType = "CUSTOM"

	def getNext(self):
		"""
		Retrieves the next line for printing.
		"""
		if self._filehandle is None:
			raise ValueError("File %s is not open for reading" % self._filename)

		if self._lineCount is None:
			self._lineCount = 0
			return "M110 N0"

		try:
			processedLine = None
			while processedLine is None:
				if self._filehandle is None:
					# file got closed just now
					return None
				line = self._filehandle.readline()
				if not line:
					self._filehandle.close()
					self._filehandle = None
				processedLine = self._processLine(line)
			self._lineCount += 1
			self._filepos = self._filehandle.tell()

			if self._lineCount >= 100 and self._startTime is None:
				self._startTime = time.time()

			return processedLine
		except Exception as (e):
			if self._filehandle is not None:
				self._filehandle.close()
				self._filehandle = None
			raise e

	def _processLine(self, line):
		lineType = self._prevLineType
		if line.startswith(";TYPE:"):
			lineType = line[6:].strip()
		if ";" in line:
			line = line[0:line.find(";")]
		line = line.strip()
		if len(line) > 0:
			if self._prevLineType != lineType:
				return line, lineType
			else:
				return line
		else:
			return None

class StreamingGcodeFileInformation(PrintingGcodeFileInformation):
	pass
