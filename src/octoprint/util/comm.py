# coding=utf-8
from __future__ import absolute_import
__author__ = "Gina Häußge <osd@foosel.net> based on work by David Braam"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"


import os
import glob
import time
import re
import threading
import Queue as queue
import logging
import serial
import octoprint.plugin

from collections import deque

from octoprint.util.avr_isp import stk500v2
from octoprint.util.avr_isp import ispBase

from octoprint.settings import settings
from octoprint.events import eventManager, Events
from octoprint.filemanager import valid_file_type
from octoprint.filemanager.destinations import FileDestinations
from octoprint.util import getExceptionString, getNewTimeout, sanitizeAscii, filterNonAscii
from octoprint.util.virtual import VirtualPrinter

try:
	import _winreg
except:
	pass

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
			   + glob.glob("/dev/cuaU*") \
			   + glob.glob("/dev/rfcomm*")

	additionalPorts = settings().get(["serial", "additionalPorts"])
	for additional in additionalPorts:
		baselist += glob.glob(additional)

	prev = settings().get(["serial", "port"])
	if prev in baselist:
		baselist.remove(prev)
		baselist.insert(0, prev)
	if settings().getBoolean(["devel", "virtualPrinter", "enabled"]):
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
	# pause for user input
	"M226": Events.WAITING,
	"M0": Events.WAITING,
	"M1": Events.WAITING,
	# dwell command
	"G4": Events.DWELL,

	# part cooler
	"M245": Events.COOLING,

	# part conveyor
	"M240": Events.CONVEYOR,

	# part ejector
	"M40": Events.EJECT,

	# user alert
	"M300": Events.ALERT,

	# home print head
	"G28": Events.HOME,

	# emergency stop
	"M112": Events.E_STOP,

	# motors on/off
	"M80": Events.POWER_ON,
	"M81": Events.POWER_OFF,
}

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
		self._temp = {}
		self._tempOffset = {}
		self._bedTemp = None
		self._bedTempOffset = 0
		self._commandQueue = queue.Queue()
		self._currentZ = None
		self._heatupWaitStartTime = None
		self._heatupWaitTimeLost = 0.0
		self._pauseWaitStartTime = None
		self._pauseWaitTimeLost = 0.0
		self._currentExtruder = 0

		self._timeout = None

		self._alwaysSendChecksum = settings().getBoolean(["feature", "alwaysSendChecksum"])
		self._currentLine = 1
		self._resendDelta = None
		self._lastLines = deque([], 50)

		# hooks
		self._pluginManager = octoprint.plugin.plugin_manager()
		self._gcode_hooks = self._pluginManager.get_hooks("octoprint.comm.protocol.gcode")

		# SD status data
		self._sdAvailable = False
		self._sdFileList = False
		self._sdFiles = []

		# print job
		self._currentFile = None

		# regexes
		floatPattern = "[-+]?[0-9]*\.?[0-9]+"
		positiveFloatPattern = "[+]?[0-9]*\.?[0-9]+"
		intPattern = "\d+"
		self._regex_command = re.compile("^\s*([GM]\d+|T)")
		self._regex_float = re.compile(floatPattern)
		self._regex_paramZFloat = re.compile("Z(%s)" % floatPattern)
		self._regex_paramSInt = re.compile("S(%s)" % intPattern)
		self._regex_paramNInt = re.compile("N(%s)" % intPattern)
		self._regex_paramTInt = re.compile("T(%s)" % intPattern)
		self._regex_minMaxError = re.compile("Error:[0-9]\n")
		self._regex_sdPrintingByte = re.compile("([0-9]*)/([0-9]*)")
		self._regex_sdFileOpened = re.compile("File opened:\s*(.*?)\s+Size:\s*(%s)" % intPattern)

		# Regex matching temperature entries in line. Groups will be as follows:
		# - 1: whole tool designator incl. optional toolNumber ("T", "Tn", "B")
		# - 2: toolNumber, if given ("", "n", "")
		# - 3: actual temperature
		# - 4: whole target substring, if given (e.g. " / 22.0")
		# - 5: target temperature
		self._regex_temp = re.compile("(B|T(\d*)):\s*(%s)(\s*\/?\s*(%s))?" % (positiveFloatPattern, positiveFloatPattern))
		self._regex_repetierTempExtr = re.compile("TargetExtr([0-9]+):(%s)" % positiveFloatPattern)
		self._regex_repetierTempBed = re.compile("TargetBed:(%s)" % positiveFloatPattern)

		# multithreading locks
		self._sendNextLock = threading.Lock()
		self._sendingLock = threading.Lock()

		# monitoring thread
		self.thread = threading.Thread(target=self._monitor)
		self.thread.daemon = True
		self.thread.start()

	def __del__(self):
		self.close()

	##~~ internal state management

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

	def _log(self, message):
		self._callback.mcLog(message)
		self._serialLogger.debug(message)

	def _addToLastLines(self, cmd):
		self._lastLines.append(cmd)
		self._logger.debug("Got %d lines of history in memory" % len(self._lastLines))

	##~~ getters

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
			return time.time() - self._currentFile.getStartTime() - self._pauseWaitTimeLost

	def getCleanedPrintTime(self):
		printTime = self.getPrintTime()
		if printTime is None:
			return None

		cleanedPrintTime = printTime - self._heatupWaitTimeLost
		if cleanedPrintTime < 0:
			cleanedPrintTime = 0.0
		return cleanedPrintTime

	def getTemp(self):
		return self._temp
	
	def getBedTemp(self):
		return self._bedTemp

	def getOffsets(self):
		return self._tempOffset, self._bedTempOffset

	def getConnection(self):
		return self._port, self._baudrate

	##~~ external interface

	def close(self, isError = False):
		printing = self.isPrinting() or self.isPaused()
		if self._serial is not None:
			if isError:
				self._changeState(self.STATE_CLOSED_WITH_ERROR)
			else:
				self._changeState(self.STATE_CLOSED)
			self._serial.close()
		self._serial = None

		if settings().get(["feature", "sdSupport"]):
			self._sdFileList = []

		if printing:
			payload = None
			if self._currentFile is not None:
				payload = {
					"file": self._currentFile.getFilename(),
					"filename": os.path.basename(self._currentFile.getFilename()),
					"origin": self._currentFile.getFileLocation()
				}
			eventManager().fire(Events.PRINT_FAILED, payload)
		eventManager().fire(Events.DISCONNECTED)

	def setTemperatureOffset(self, tool=None, bed=None):
		if tool is not None:
			self._tempOffset = tool

		if bed is not None:
			self._bedTempOffset = bed

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

		self._heatupWaitStartTime = 0
		self._heatupWaitTimeLost = 0.0
		self._pauseWaitStartTime = 0
		self._pauseWaitTimeLost = 0.0

		try:
			self._currentFile.start()

			wasPaused = self.isPaused()
			self._changeState(self.STATE_PRINTING)
			eventManager().fire(Events.PRINT_STARTED, {
				"file": self._currentFile.getFilename(),
				"filename": os.path.basename(self._currentFile.getFilename()),
				"origin": self._currentFile.getFileLocation()
			})

			if self.isSdFileSelected():
				if wasPaused:
					self.sendCommand("M26 S0")
					self._currentFile.setFilepos(0)
				self.sendCommand("M24")
			else:
				self._sendNext()
		except:
			self._logger.exception("Error while trying to start printing")
			self._errorValue = getExceptionString()
			self._changeState(self.STATE_ERROR)
			eventManager().fire(Events.ERROR, {"error": self.getErrorString()})

	def startFileTransfer(self, filename, localFilename, remoteFilename):
		if not self.isOperational() or self.isBusy():
			logging.info("Printer is not operation or busy")
			return

		self._currentFile = StreamingGcodeFileInformation(filename, localFilename, remoteFilename)
		self._currentFile.start()

		self.sendCommand("M28 %s" % remoteFilename)
		eventManager().fire(Events.TRANSFER_STARTED, {"local": localFilename, "remote": remoteFilename})
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
			self._currentFile = PrintingGcodeFileInformation(filename, self.getOffsets)
			eventManager().fire(Events.FILE_SELECTED, {
				"file": self._currentFile.getFilename(),
				"origin": self._currentFile.getFileLocation()
			})
			self._callback.mcFileSelected(filename, self._currentFile.getFilesize(), False)

	def unselectFile(self):
		if self.isBusy():
			return

		self._currentFile = None
		eventManager().fire(Events.FILE_DESELECTED)
		self._callback.mcFileSelected(None, None, False)

	def cancelPrint(self):
		if not self.isOperational() or self.isStreaming():
			return

		self._changeState(self.STATE_OPERATIONAL)

		if self.isSdFileSelected():
			self.sendCommand("M25")    # pause print
			self.sendCommand("M26 S0") # reset position in file to byte 0

		eventManager().fire(Events.PRINT_CANCELLED, {
			"file": self._currentFile.getFilename(),
			"filename": os.path.basename(self._currentFile.getFilename()),
			"origin": self._currentFile.getFileLocation()
		})

	def setPause(self, pause):
		if self.isStreaming():
			return

		if not pause and self.isPaused():
			if self._pauseWaitStartTime:
				self._pauseWaitTimeLost = self._pauseWaitTimeLost + (time.time() - self._pauseWaitStartTime)
				self._pauseWaitStartTime = None

			self._changeState(self.STATE_PRINTING)
			if self.isSdFileSelected():
				self.sendCommand("M24")
			else:
				self._sendNext()

			eventManager().fire(Events.PRINT_RESUMED, {
				"file": self._currentFile.getFilename(),
				"filename": os.path.basename(self._currentFile.getFilename()),
				"origin": self._currentFile.getFileLocation()
			})
		elif pause and self.isPrinting():
			if not self._pauseWaitStartTime:
				self._pauseWaitStartTime = time.time()

			self._changeState(self.STATE_PAUSED)
			if self.isSdFileSelected():
				self.sendCommand("M25") # pause print

			eventManager().fire(Events.PRINT_PAUSED, {
				"file": self._currentFile.getFilename(),
				"filename": os.path.basename(self._currentFile.getFilename()),
				"origin": self._currentFile.getFileLocation()
			})

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
		if not self.isOperational() or (self.isBusy() and
				isinstance(self._currentFile, PrintingSdFileInformation) and
				self._currentFile.getFilename() == filename):
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
		if settings().getBoolean(["feature", "sdAlwaysAvailable"]):
			self._sdAvailable = True
			self.refreshSdFiles()
			self._callback.mcSdStateChange(self._sdAvailable)

	def releaseSdCard(self):
		if not self.isOperational() or (self.isBusy() and self.isSdFileSelected()):
			# do not release the sd card if we are currently printing from it
			return

		self.sendCommand("M22")
		self._sdAvailable = False
		self._sdFiles = []

		self._callback.mcSdStateChange(self._sdAvailable)
		self._callback.mcSdFiles(self._sdFiles)

	##~~ communication monitoring and handling

	def _parseTemperatures(self, line):
		result = {}
		maxToolNum = 0
		for match in re.finditer(self._regex_temp, line):
			tool = match.group(1)
			toolNumber = int(match.group(2)) if match.group(2) and len(match.group(2)) > 0 else None
			if toolNumber > maxToolNum:
				maxToolNum = toolNumber

			try:
				actual = float(match.group(3))
				target = None
				if match.group(4) and match.group(5):
					target = float(match.group(5))

				result[tool] = (toolNumber, actual, target)
			except ValueError:
				# catch conversion issues, we'll rather just not get the temperature update instead of killing the connection
				pass

		if "T0" in result.keys() and "T" in result.keys():
			del result["T"]

		return maxToolNum, result

	def _processTemperatures(self, line):
		maxToolNum, parsedTemps = self._parseTemperatures(line)

		# extruder temperatures
		if not "T0" in parsedTemps.keys() and not "T1" in parsedTemps.keys() and "T" in parsedTemps.keys():
			# no T1 so only single reporting, "T" is our one and only extruder temperature
			toolNum, actual, target = parsedTemps["T"]

			if target is not None:
				self._temp[0] = (actual, target)
			elif 0 in self._temp.keys() and self._temp[0] is not None and isinstance(self._temp[0], tuple):
				(oldActual, oldTarget) = self._temp[0]
				self._temp[0] = (actual, oldTarget)
			else:
				self._temp[0] = (actual, None)
		elif not "T0" in parsedTemps.keys() and "T" in parsedTemps.keys():
			# Smoothieware sends multi extruder temperature data this way: "T:<first extruder> T1:<second extruder> ..." and therefore needs some special treatment...
			_, actual, target = parsedTemps["T"]
			del parsedTemps["T"]
			parsedTemps["T0"] = (0, actual, target)

		if "T0" in parsedTemps.keys():
			for n in range(maxToolNum + 1):
				tool = "T%d" % n
				if not tool in parsedTemps.keys():
					continue

				toolNum, actual, target = parsedTemps[tool]
				if target is not None:
					self._temp[toolNum] = (actual, target)
				elif toolNum in self._temp.keys() and self._temp[toolNum] is not None and isinstance(self._temp[toolNum], tuple):
					(oldActual, oldTarget) = self._temp[toolNum]
					self._temp[toolNum] = (actual, oldTarget)
				else:
					self._temp[toolNum] = (actual, None)

		# bed temperature
		if "B" in parsedTemps.keys():
			toolNum, actual, target = parsedTemps["B"]
			if target is not None:
				self._bedTemp = (actual, target)
			elif self._bedTemp is not None and isinstance(self._bedTemp, tuple):
				(oldActual, oldTarget) = self._bedTemp
				self._bedTemp = (actual, oldTarget)
			else:
				self._bedTemp = (actual, None)

	def _monitor(self):
		feedbackControls = settings().getFeedbackControls()
		pauseTriggers = settings().getPauseTriggers()
		feedbackErrors = []

		#Open the serial port.
		if not self._openSerial():
			return

		self._log("Connected to: %s, starting monitor" % self._serial)
		if self._baudrate == 0:
			self._log("Starting baud rate detection")
			self._changeState(self.STATE_DETECT_BAUDRATE)
		else:
			self._changeState(self.STATE_CONNECTING)

		#Start monitoring the serial port.
		self._timeout = getNewTimeout("communication")

		tempRequestTimeout = getNewTimeout("temperature")
		sdStatusRequestTimeout = getNewTimeout("sdStatus")

		startSeen = not settings().getBoolean(["feature", "waitForStartOnConnect"])
		heatingUp = False
		swallowOk = False
		supportRepetierTargetTemp = settings().getBoolean(["feature", "repetierTargetTemp"])

		while True:
			try:
				line = self._readline()
				if line is None:
					break
				if line.strip() is not "":
					self._timeout = getNewTimeout("communication")

				##~~ Error handling
				line = self._handleErrors(line)

				##~~ SD file list
				# if we are currently receiving an sd file list, each line is just a filename, so just read it and abort processing
				if self._sdFileList and not "End file list" in line:
					preprocessed_line = line.strip().lower()
					fileinfo = preprocessed_line.rsplit(None, 1)
					if len(fileinfo) > 1:
						# we might have extended file information here, so let's split filename and size and try to make them a bit nicer
						filename, size = fileinfo
						try:
							size = int(size)
						except ValueError:
							# whatever that was, it was not an integer, so we'll just use the whole line as filename and set size to None
							filename = preprocessed_line
							size = None
					else:
						# no extended file information, so only the filename is there and we set size to None
						filename = preprocessed_line
						size = None

					if valid_file_type(filename, "gcode"):
						if filterNonAscii(filename):
							self._logger.warn("Got a file from printer's SD that has a non-ascii filename (%s), that shouldn't happen according to the protocol" % filename)
						else:
							self._sdFiles.append((filename, size))
						continue

				##~~ Temperature processing
				if ' T:' in line or line.startswith('T:') or ' T0:' in line or line.startswith('T0:'):
					self._processTemperatures(line)
					self._callback.mcTempUpdate(self._temp, self._bedTemp)

					#If we are waiting for an M109 or M190 then measure the time we lost during heatup, so we can remove that time from our printing time estimate.
					if 'ok' in line and self._heatupWaitStartTime:
						self._heatupWaitTimeLost = self._heatupWaitTimeLost + (time.time() - self._heatupWaitStartTime)
						self._heatupWaitStartTime = None
				elif supportRepetierTargetTemp and ('TargetExtr' in line or 'TargetBed' in line):
					matchExtr = self._regex_repetierTempExtr.match(line)
					matchBed = self._regex_repetierTempBed.match(line)

					if matchExtr is not None:
						toolNum = int(matchExtr.group(1))
						try:
							target = float(matchExtr.group(2))
							if toolNum in self._temp.keys() and self._temp[toolNum] is not None and isinstance(self._temp[toolNum], tuple):
								(actual, oldTarget) = self._temp[toolNum]
								self._temp[toolNum] = (actual, target)
							else:
								self._temp[toolNum] = (None, target)
							self._callback.mcTempUpdate(self._temp, self._bedTemp)
						except ValueError:
							pass
					elif matchBed is not None:
						try:
							target = float(matchBed.group(1))
							if self._bedTemp is not None and isinstance(self._bedTemp, tuple):
								(actual, oldTarget) = self._bedTemp
								self._bedTemp = (actual, target)
							else:
								self._bedTemp = (None, target)
							self._callback.mcTempUpdate(self._temp, self._bedTemp)
						except ValueError:
							pass

				##~~ SD Card handling
				elif 'SD init fail' in line or 'volume.init failed' in line or 'openRoot failed' in line:
					self._sdAvailable = False
					self._sdFiles = []
					self._callback.mcSdStateChange(self._sdAvailable)
				elif 'Not SD printing' in line:
					if self.isSdFileSelected() and self.isPrinting():
						# something went wrong, printer is reporting that we actually are not printing right now...
						self._sdFilePos = 0
						self._changeState(self.STATE_OPERATIONAL)
				elif 'SD card ok' in line and not self._sdAvailable:
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
					match = self._regex_sdPrintingByte.search(line)
					self._currentFile.setFilepos(int(match.group(1)))
					self._callback.mcProgress()
				elif 'File opened' in line:
					# answer to M23, at least on Marlin, Repetier and Sprinter: "File opened:%s Size:%d"
					match = self._regex_sdFileOpened.search(line)
					self._currentFile = PrintingSdFileInformation(match.group(1), int(match.group(2)))
				elif 'File selected' in line:
					# final answer to M23, at least on Marlin, Repetier and Sprinter: "File selected"
					if self._currentFile is not None:
						self._callback.mcFileSelected(self._currentFile.getFilename(), self._currentFile.getFilesize(), True)
						eventManager().fire(Events.FILE_SELECTED, {
							"file": self._currentFile.getFilename(),
							"origin": self._currentFile.getFileLocation()
						})
				elif 'Writing to file' in line:
					# anwer to M28, at least on Marlin, Repetier and Sprinter: "Writing to file: %s"
					self._printSection = "CUSTOM"
					self._changeState(self.STATE_PRINTING)
					line = "ok"
				elif 'Done printing file' in line:
					# printer is reporting file finished printing
					self._sdFilePos = 0
					self._callback.mcPrintjobDone()
					self._changeState(self.STATE_OPERATIONAL)
					eventManager().fire(Events.PRINT_DONE, {
						"file": self._currentFile.getFilename(),
						"filename": os.path.basename(self._currentFile.getFilename()),
						"origin": self._currentFile.getFileLocation(),
						"time": self.getPrintTime()
					})
				elif 'Done saving file' in line:
					self.refreshSdFiles()

				##~~ Message handling
				elif line.strip() != '' \
						and line.strip() != 'ok' and not line.startswith("wait") \
						and not line.startswith('Resend:') \
						and line != 'echo:Unknown command:""\n' \
						and self.isOperational():
					self._callback.mcMessage(line)

				##~~ Parsing for feedback commands
				if feedbackControls:
					for name, matcher, template in feedbackControls:
						if name in feedbackErrors:
							# we previously had an error with that one, so we'll skip it now
							continue
						try:
							match = matcher.search(line)
							if match is not None:
								formatFunction = None
								if isinstance(template, str):
									formatFunction = str.format
								elif isinstance(template, unicode):
									formatFunction = unicode.format

								if formatFunction is not None:
									self._callback.mcReceivedRegisteredMessage(name, formatFunction(template, *(match.groups("n/a"))))
						except:
							if not name in feedbackErrors:
								self._logger.info("Something went wrong with feedbackControl \"%s\": " % name, exc_info=True)
								feedbackErrors.append(name)
							pass

				##~~ Parsing for pause triggers
				if pauseTriggers and not self.isStreaming():
					if "enable" in pauseTriggers.keys() and pauseTriggers["enable"].search(line) is not None:
						self.setPause(True)
					elif "disable" in pauseTriggers.keys() and pauseTriggers["disable"].search(line) is not None:
						self.setPause(False)
					elif "toggle" in pauseTriggers.keys() and pauseTriggers["toggle"].search(line) is not None:
						self.setPause(not self.isPaused())

				if "ok" in line and heatingUp:
					heatingUp = False

				### Baudrate detection
				if self._state == self.STATE_DETECT_BAUDRATE:
					if line == '' or time.time() > self._timeout:
						if len(self._baudrateDetectList) < 1:
							self.close()
							self._errorValue = "No more baudrates to test, and no suitable baudrate found."
							self._changeState(self.STATE_ERROR)
							eventManager().fire(Events.ERROR, {"error": self.getErrorString()})
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
								self._serial.timeout = settings().getFloat(["serial", "timeout", "detection"])
								self._log("Trying baudrate: %d" % (baudrate))
								self._baudrateDetectRetry = 5
								self._baudrateDetectTestOk = 0
								self._timeout = getNewTimeout("communication")
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
							self._serial.timeout = settings().getFloat(["serial", "timeout", "connection"])
							self._changeState(self.STATE_OPERATIONAL)
							if self._sdAvailable:
								self.refreshSdFiles()
							else:
								self.initSdCard()
							eventManager().fire(Events.CONNECTED, {"port": self._port, "baudrate": self._baudrate})
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
						else:
							self.initSdCard()
						eventManager().fire(Events.CONNECTED, {"port": self._port, "baudrate": self._baudrate})
					elif time.time() > self._timeout:
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
						tempRequestTimeout = getNewTimeout("temperature")
					# resend -> start resend procedure from requested line
					elif line.lower().startswith("resend") or line.lower().startswith("rs"):
						if settings().get(["feature", "swallowOkAfterResend"]):
							swallowOk = True
						self._handleResendRequest(line)

				### Printing
				elif self._state == self.STATE_PRINTING:
					if line == "" and time.time() > self._timeout:
						self._log("Communication timeout during printing, forcing a line")
						line = 'ok'

					if self.isSdPrinting():
						if time.time() > tempRequestTimeout and not heatingUp:
							self._sendCommand("M105")
							tempRequestTimeout = getNewTimeout("temperature")

						if time.time() > sdStatusRequestTimeout and not heatingUp:
							self._sendCommand("M27")
							sdStatusRequestTimeout = getNewTimeout("sdStatus")
					else:
						# Even when printing request the temperature every 5 seconds.
						if time.time() > tempRequestTimeout and not self.isStreaming():
							self._commandQueue.put("M105")
							tempRequestTimeout = getNewTimeout("temperature")

						if "ok" in line and swallowOk:
							swallowOk = False
						elif "ok" in line:
							if self._resendDelta is not None:
								self._resendNextCommand()
							elif not self._commandQueue.empty() and not self.isStreaming():
								self._sendCommand(self._commandQueue.get(), True)
							else:
								self._sendNext()
						elif line.lower().startswith("resend") or line.lower().startswith("rs"):
							if settings().get(["feature", "swallowOkAfterResend"]):
								swallowOk = True
							self._handleResendRequest(line)
			except:
				self._logger.exception("Something crashed inside the serial connection loop, please report this in OctoPrint's bug tracker:")

				errorMsg = "See octoprint.log for details"
				self._log(errorMsg)
				self._errorValue = errorMsg
				self._changeState(self.STATE_ERROR)
				eventManager().fire(Events.ERROR, {"error": self.getErrorString()})
		self._log("Connection closed, closing down monitor")

	def _openSerial(self):
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
			if self._serial is None:
				self._log("Failed to autodetect serial port")
				self._errorValue = 'Failed to autodetect serial port.'
				self._changeState(self.STATE_ERROR)
				eventManager().fire(Events.ERROR, {"error": self.getErrorString()})
				return False
		elif self._port == 'VIRTUAL':
			self._changeState(self.STATE_OPEN_SERIAL)
			self._serial = VirtualPrinter()
		else:
			self._changeState(self.STATE_OPEN_SERIAL)
			try:
				self._log("Connecting to: %s" % self._port)
				if self._baudrate == 0:
					self._serial = serial.Serial(str(self._port), 115200, timeout=settings().getFloat(["serial", "timeout", "connection"]), writeTimeout=10000)
				else:
					self._serial = serial.Serial(str(self._port), self._baudrate, timeout=settings().getFloat(["serial", "timeout", "connection"]), writeTimeout=10000)
			except:
				self._log("Unexpected error while connecting to serial port: %s %s" % (self._port, getExceptionString()))
				self._errorValue = "Failed to open serial port, permissions correct?"
				self._changeState(self.STATE_ERROR)
				eventManager().fire(Events.ERROR, {"error": self.getErrorString()})
				return False
		return True

	def _handleErrors(self, line):
		# No matter the state, if we see an error, goto the error state and store the error for reference.
		if line.startswith('Error:') or line.startswith('!!'):
			#Oh YEAH, consistency.
			# Marlin reports an MIN/MAX temp error as "Error:x\n: Extruder switched off. MAXTEMP triggered !\n"
			#	But a bed temp error is reported as "Error: Temperature heated bed switched off. MAXTEMP triggered !!"
			#	So we can have an extra newline in the most common case. Awesome work people.
			if self._regex_minMaxError.match(line):
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
				eventManager().fire(Events.ERROR, {"error": self.getErrorString()})
		return line

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
		self._log("Recv: %s" % sanitizeAscii(ret))
		return ret

	def _sendNext(self):
		with self._sendNextLock:
			line = self._currentFile.getNext()
			if line is None:
				if self.isStreaming():
					self._sendCommand("M29")

					remote = self._currentFile.getRemoteFilename()
					payload = {
						"local": self._currentFile.getLocalFilename(),
						"remote": remote,
						"time": self.getPrintTime()
					}

					self._currentFile = None
					self._changeState(self.STATE_OPERATIONAL)
					self._callback.mcFileTransferDone(remote)
					eventManager().fire(Events.TRANSFER_DONE, payload)
					self.refreshSdFiles()
				else:
					payload = {
						"file": self._currentFile.getFilename(),
						"filename": os.path.basename(self._currentFile.getFilename()),
						"origin": self._currentFile.getFileLocation(),
						"time": self.getPrintTime()
					}
					self._callback.mcPrintjobDone()
					self._changeState(self.STATE_OPERATIONAL)
					eventManager().fire(Events.PRINT_DONE, payload)
				return

			self._sendCommand(line, True)
			self._callback.mcProgress()

	def _handleResendRequest(self, line):
		lineToResend = None
		try:
			lineToResend = int(line.replace("N:", " ").replace("N", " ").replace(":", " ").split()[-1])
		except:
			if "rs" in line:
				lineToResend = int(line.split()[1])

		if lineToResend is not None:
			self._resendDelta = self._currentLine - lineToResend
			if self._resendDelta > len(self._lastLines) or len(self._lastLines) == 0 or self._resendDelta <= 0:
				self._errorValue = "Printer requested line %d but no sufficient history is available, can't resend" % lineToResend
				self._logger.warn(self._errorValue)
				if self.isPrinting():
					# abort the print, there's nothing we can do to rescue it now
					self._changeState(self.STATE_ERROR)
					eventManager().fire(Events.ERROR, {"error": self.getErrorString()})
				else:
					# reset resend delta, we can't do anything about it
					self._resendDelta = None
			else:
				self._resendNextCommand()

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
				for hook in self._gcode_hooks:
					hook_cmd = self._gcode_hooks[hook](self, cmd)
					if hook_cmd and isinstance(hook_cmd, basestring):
						cmd = hook_cmd
				gcode = self._regex_command.search(cmd)
				if gcode:
					gcode = gcode.group(1)

					if gcode in gcodeToEvent:
						eventManager().fire(gcodeToEvent[gcode])

					gcodeHandler = "_gcode_" + gcode
					if hasattr(self, gcodeHandler):
						cmd = getattr(self, gcodeHandler)(cmd)

			if cmd is not None:
				self._doSend(cmd, sendChecksum)

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

		commandToSend = "N%d %s" % (lineNumber, cmd)
		checksum = reduce(lambda x,y:x^y, map(ord, commandToSend))
		commandToSend = "%s*%d" % (commandToSend, checksum)
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

	def _gcode_T(self, cmd):
		toolMatch = self._regex_paramTInt.search(cmd)
		if toolMatch:
			self._currentExtruder = int(toolMatch.group(1))
		return cmd

	def _gcode_G0(self, cmd):
		if 'Z' in cmd:
			match = self._regex_paramZFloat.search(cmd)
			if match:
				try:
					z = float(match.group(1))
					if self._currentZ != z:
						self._currentZ = z
						self._callback.mcZChange(z)
				except ValueError:
					pass
		return cmd
	_gcode_G1 = _gcode_G0

	def _gcode_M0(self, cmd):
		self.setPause(True)
		return "M105" # Don't send the M0 or M1 to the machine, as M0 and M1 are handled as an LCD menu pause.
	_gcode_M1 = _gcode_M0

	def _gcode_M104(self, cmd):
		toolNum = self._currentExtruder
		toolMatch = self._regex_paramTInt.search(cmd)
		if toolMatch:
			toolNum = int(toolMatch.group(1))
		match = self._regex_paramSInt.search(cmd)
		if match:
			try:
				target = float(match.group(1))
				if toolNum in self._temp.keys() and self._temp[toolNum] is not None and isinstance(self._temp[toolNum], tuple):
					(actual, oldTarget) = self._temp[toolNum]
					self._temp[toolNum] = (actual, target)
				else:
					self._temp[toolNum] = (None, target)
			except ValueError:
				pass
		return cmd

	def _gcode_M140(self, cmd):
		match = self._regex_paramSInt.search(cmd)
		if match:
			try:
				target = float(match.group(1))
				if self._bedTemp is not None and isinstance(self._bedTemp, tuple):
					(actual, oldTarget) = self._bedTemp
					self._bedTemp = (actual, target)
				else:
					self._bedTemp = (None, target)
			except ValueError:
				pass
		return cmd

	def _gcode_M109(self, cmd):
		self._heatupWaitStartTime = time.time()
		return self._gcode_M104(cmd)

	def _gcode_M190(self, cmd):
		self._heatupWaitStartTime = time.time()
		return self._gcode_M140(cmd)

	def _gcode_M110(self, cmd):
		newLineNumber = None
		match = self._regex_paramNInt.search(cmd)
		if match:
			try:
				newLineNumber = int(match.group(1))
			except:
				pass
		else:
			newLineNumber = 0

		# send M110 command with new line number
		self._doSendWithChecksum(cmd, newLineNumber)
		self._currentLine = newLineNumber + 1

		# after a reset of the line number we have no way to determine what line exactly the printer now wants
		self._lastLines.clear()
		self._resendDelta = None

		return None

	def _gcode_M112(self, cmd): # It's an emergency what todo? Canceling the print should be the minimum
		self.cancelPrint()
		return cmd

	def _gcode_G4(self, cmd):
		# we are intending to dwell for a period of time, increase the timeout to match
		cmd = cmd.upper()
		p_idx = cmd.find('P')
		s_idx = cmd.find('S')
		_timeout = 0
		if p_idx != -1:
			# dwell time is specified in milliseconds
			_timeout = int(cmd[p_idx+1:]) / 1000.0
		elif s_idx != -1:
			# dwell time is specified in seconds
			_timeout = int(cmd[s_idx+1:])
		self._timeout = getNewTimeout("communication") + _timeout
		return cmd

### MachineCom callback ################################################################################################

class MachineComPrintCallback(object):
	def mcLog(self, message):
		pass

	def mcTempUpdate(self, temp, bedTemp):
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

### Printing file information classes ##################################################################################

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

	def getFileLocation(self):
		return FileDestinations.LOCAL

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

	def getFileLocation(self):
		return FileDestinations.SDCARD

class PrintingGcodeFileInformation(PrintingFileInformation):
	"""
	Encapsulates information regarding an ongoing direct print. Takes care of the needed file handle and ensures
	that the file is closed in case of an error.
	"""

	def __init__(self, filename, offsetCallback):
		PrintingFileInformation.__init__(self, filename)

		self._filehandle = None

		self._filesetMenuModehandle = None
		self._lineCount = None
		self._firstLine = None
		self._currentTool = 0

		self._offsetCallback = offsetCallback
		self._regex_tempCommand = re.compile("M(104|109|140|190)")
		self._regex_tempCommandTemperature = re.compile("S([-+]?\d*\.?\d*)")
		self._regex_tempCommandTool = re.compile("T(\d+)")
		self._regex_toolCommand = re.compile("^T(\d+)")

		if not os.path.exists(self._filename) or not os.path.isfile(self._filename):
			raise IOError("File %s does not exist" % self._filename)
		self._filesize = os.stat(self._filename).st_size

	def start(self):
		"""
		Opens the file for reading and determines the file size. Start time won't be recorded until 100 lines in
		"""
		PrintingFileInformation.start(self)
		self._filehandle = open(self._filename, "r")
		self._lineCount = None

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

			return processedLine
		except Exception as (e):
			if self._filehandle is not None:
				self._filehandle.close()
				self._filehandle = None
			raise e

	def _processLine(self, line):
		if ";" in line:
			line = line[0:line.find(";")]
		line = line.strip()
		if len(line) > 0:
			toolMatch = self._regex_toolCommand.match(line)
			if toolMatch is not None:
				# track tool changes
				self._currentTool = int(toolMatch.group(1))
			else:
				## apply offsets
				if self._offsetCallback is not None:
					tempMatch = self._regex_tempCommand.match(line)
					if tempMatch is not None:
						# if we have a temperature command, retrieve current offsets
						tempOffset, bedTempOffset = self._offsetCallback()
						if tempMatch.group(1) == "104" or tempMatch.group(1) == "109":
							# extruder temperature, determine which one and retrieve corresponding offset
							toolNum = self._currentTool

							toolNumMatch = self._regex_tempCommandTool.search(line)
							if toolNumMatch is not None:
								try:
									toolNum = int(toolNumMatch.group(1))
								except ValueError:
									pass

							offset = tempOffset[toolNum] if toolNum in tempOffset.keys() and tempOffset[toolNum] is not None else 0
						elif tempMatch.group(1) == "140" or tempMatch.group(1) == "190":
							# bed temperature
							offset = bedTempOffset
						else:
							# unknown, should never happen
							offset = 0

						if not offset == 0:
							# if we have an offset != 0, we need to get the temperature to be set and apply the offset to it
							tempValueMatch = self._regex_tempCommandTemperature.search(line)
							if tempValueMatch is not None:
								try:
									temp = float(tempValueMatch.group(1))
									if temp > 0:
										newTemp = temp + offset
										line = line.replace("S" + tempValueMatch.group(1), "S%f" % newTemp)
								except ValueError:
									pass
			return line
		else:
			return None

class StreamingGcodeFileInformation(PrintingGcodeFileInformation):
	def __init__(self, path, localFilename, remoteFilename):
		PrintingGcodeFileInformation.__init__(self, path, None)
		self._localFilename = localFilename
		self._remoteFilename = remoteFilename

	def start(self):
		PrintingGcodeFileInformation.start(self)
		self._startTime = time.time()

	def getLocalFilename(self):
		return self._localFilename

	def getRemoteFilename(self):
		return self._remoteFilename
