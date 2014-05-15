# coding=utf-8
import Queue
from collections import deque
from octoprint.events import eventManager, Events

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 Gina Häußge - Released under terms of the AGPLv3 License"

import re
import threading
import time
from octoprint.comm.protocol import ProtocolListener, State, Protocol, PrintingSdFileInformation
from octoprint.comm.protocol.reprap.util import GcodeCommand, CommandQueue, PrintingGcodeFileInformation
from octoprint.comm.transport import TransportProperties
from octoprint.filemanager.destinations import FileDestinations
from octoprint.gcodefiles import isGcodeFileName
from octoprint.comm.transport.serialTransport import SerialTransport


class RepRapProtocol(Protocol):

	## Firmware messages
	MESSAGE_OK = staticmethod(lambda line: line.startswith("ok"))
	MESSAGE_START = staticmethod(lambda line: line.startswith("start"))
	MESSAGE_WAIT = staticmethod(lambda line: line.startswith("wait"))
	MESSAGE_TEMPERATURE = staticmethod(lambda line: " T:" in line or line.startswith("T:") or " T0:" in line or line.startswith("T0:"))

	MESSAGE_SD_INIT_OK = staticmethod(lambda line: line.lower() == "sd card ok")
	MESSAGE_SD_INIT_FAIL = staticmethod(lambda line: "sd init fail" in line.lower() or "volume.init failed" in line.lower() or "openroot failed" in line.lower())
	MESSAGE_SD_FILE_OPENED = staticmethod(lambda line: line.lower().startswith("file opened"))
	MESSAGE_SD_FILE_SELECTED = staticmethod(lambda line: line.lower().startswith("file selected"))
	MESSAGE_SD_BEGIN_FILE_LIST = staticmethod(lambda line: line.lower().startswith("begin file list"))
	MESSAGE_SD_END_FILE_LIST = staticmethod(lambda line: line.lower().startswith("end file list"))
	MESSAGE_SD_PRINTING_BYTE = staticmethod(lambda line: "sd printing byte" in line.lower())
	MESSAGE_SD_NOT_PRINTING = staticmethod(lambda line: "not sd printing" in line.lower())
	MESSAGE_SD_DONE_PRINTING = staticmethod(lambda line: "done printing file" in line.lower())
	MESSAGE_SD_BEGIN_WRITING = staticmethod(lambda line: "writing to file" in line.lower())
	MESSAGE_SD_END_WRITING = staticmethod(lambda line: "done saving file" in line.lower())

	MESSAGE_ERROR = staticmethod(lambda line: line.startswith("Error:") or line.startswith("!!"))
	MESSAGE_ERROR_COMMUNICATION = staticmethod(lambda line: 'checksum mismatch' in line.lower()
															or 'wrong checksum' in line.lower()
															or 'line number is not last line number' in line.lower()
															or 'expected line' in line.lower()
															or 'no line number with checksum' in line.lower()
															or 'no checksum with line number' in line.lower()
															or 'missing checksum' in line.lower())
	MESSAGE_RESEND = staticmethod(lambda line: line.lower().startswith("resend") or line.lower().startswith("rs"))

	## Commands
	COMMAND_GET_TEMP = staticmethod(lambda: GcodeCommand("M105"))
	COMMAND_SET_EXTRUDER_TEMP = staticmethod(lambda x, w: GcodeCommand("M109", s=x) if w else GcodeCommand("M104", s=x))
	COMMAND_SET_BED_TEMP = staticmethod(lambda x, w: GcodeCommand("M190", s=x) if w else GcodeCommand("M140", s=x))
	COMMAND_SET_TOOL = staticmethod(lambda t: GcodeCommand("T%d" % t))
	COMMAND_SD_REFRESH = staticmethod(lambda: GcodeCommand("M20"))
	COMMAND_SD_INIT = staticmethod(lambda: GcodeCommand("M21"))
	COMMAND_SD_RELEASE = staticmethod(lambda: GcodeCommand("M22"))
	COMMAND_SD_SELECT_FILE = staticmethod(lambda name: GcodeCommand("M23", param=name))
	COMMAND_SD_START = staticmethod(lambda: GcodeCommand("M24"))
	COMMAND_SD_PAUSE = staticmethod(lambda: GcodeCommand("M25"))
	COMMAND_SD_SET_POS = staticmethod(lambda pos: GcodeCommand("M26", s=pos))
	COMMAND_SD_STATUS = staticmethod(lambda: GcodeCommand("M27"))
	COMMAND_SD_BEGIN_WRITE = staticmethod(lambda name: GcodeCommand("M28", param=name))
	COMMAND_SD_END_WRITE = staticmethod(lambda name: GcodeCommand("M29", param=name))
	COMMAND_SD_DELETE = staticmethod(lambda name: GcodeCommand("M30", param=name))

	## Command types
	COMMAND_TYPE_TEMPERATURE = "temperature"
	COMMAND_TYPE_SD_PROGRESS = "sd_progress"

	# Regex matching temperature entries in line. Groups will be as follows:
	# - 1: whole tool designator incl. optional toolNumber ("T", "Tn", "B")
	# - 2: toolNumber, if given ("", "n", "")
	# - 3: actual temperature
	# - 4: whole target substring, if given (e.g. " / 22.0")
	# - 5: target temperature
	REGEX_TEMPERATURE = re.compile("(B|T(\d*)):\s*([-+]?\d*\.?\d+)(\s*\/?\s*([-+]?\d*\.?\d+))?")

	# Regex matching "File opened" message. Groups will be as follows:
	# - 1: name of the file that got opened (e.g. "file.gco")
	# - 2: size of the file that got opened, in bytes, parseable to integer (e.g. "2392010")
	REGEX_FILE_OPENED = re.compile("File opened:\s*(.*?)\s+Size:\s*([0-9]*)")

	# Regex matching printing byte message. Groups will be as follows:
	# - 1: current file position
	# - 2: file size
	REGEX_SD_PRINTING_BYTE = re.compile("([0-9]*)/([0-9]*)")

	def __init__(self, transportFactory, protocolListener=None):
		Protocol.__init__(self, transportFactory, protocolListener)

		self._lastTemperatureUpdate = time.time()
		self._lastSdProgressUpdate = time.time()

		self._startSeen = False
		self._receivingSdFileList = False

		self._sendQueue = CommandQueue()

		self._clearForSend = threading.Event()
		self._clearForSend.clear()

		self._lastLines = deque([], 50)
		self._resendDelta = None

		self._sendQueueProcessing = True
		self._thread = threading.Thread(target=self._handleSendQueue, name="SendQueueHandler")
		self._thread.daemon = True
		self._thread.start()

		self._currentLine = 1
		self._state = State.OFFLINE

		# enqueue our first temperature query so it get's sent right on establishment of the connection
		self._sendTemperatureQuery(withType=True)


	def selectFile(self, filename, origin):
		if origin == FileDestinations.SDCARD:
			if not self._sdAvailable:
				return
			self._send(RepRapProtocol.COMMAND_SD_SELECT_FILE(filename), highPriority=True)
		else:
			self._currentFile = PrintingGcodeFileInformation(filename, None)

	def startPrint(self):
		wasPaused = self._state == State.PAUSED

		Protocol.startPrint(self)
		if isinstance(self._currentFile, PrintingSdFileInformation):
			if wasPaused:
				self._send(RepRapProtocol.COMMAND_SD_SET_POS(0))
				self._currentFile.setFilepos(0)
			self._send(RepRapProtocol.COMMAND_SD_START())
		else:
			self._sendNext()

	def refreshSdFiles(self):
		if not self._sdAvailable:
			return

		Protocol.refreshSdFiles(self)
		self._send(RepRapProtocol.COMMAND_SD_REFRESH())

	def sendManually(self, command, highPriority=False):
		if self._isStreaming():
			return
		self._send(command, highPriority=highPriority, withChecksum=self._useChecksum())

	##~~ callback methods

	def onMessageReceived(self, source, message):
		if self._transport != source:
			return

		message = self._handleErrors(message.strip())

		# SD file list
		if self._receivingSdFileList and isGcodeFileName(message.strip().lower()) and not RepRapProtocol.MESSAGE_SD_END_FILE_LIST(message):
			self._addSdFile(message.strip().lower())
			return

		##~~ regular message processing

		# temperature updates
		if RepRapProtocol.MESSAGE_TEMPERATURE(message):
			self._processTemperatures(message)
			if not RepRapProtocol.MESSAGE_OK(message):
				self._heatupDetected()

		# sd state
		elif RepRapProtocol.MESSAGE_SD_INIT_OK(message):
			self._changeSdState(True)
		elif RepRapProtocol.MESSAGE_SD_INIT_FAIL(message):
			self._changeSdState(False)

		# sd progress
		elif RepRapProtocol.MESSAGE_SD_PRINTING_BYTE(message):
			match = RepRapProtocol.REGEX_SD_PRINTING_BYTE.search(message)
			self._currentFile.setFilepos(int(match.group(1)))
			self._reportProgress()
		elif RepRapProtocol.MESSAGE_SD_DONE_PRINTING(message):
			self._currentFile.setFilepos(0)
			self._changeState(State.OPERATIONAL)
			self._finishPrintjob()

		# sd file list
		elif RepRapProtocol.MESSAGE_SD_BEGIN_FILE_LIST(message):
			self._resetSdFiles()
			self._receivingSdFileList = True
		elif RepRapProtocol.MESSAGE_SD_END_FILE_LIST(message):
			self._receivingSdFileList = False
			self._sendSdFiles()

		# sd file selection
		elif RepRapProtocol.MESSAGE_SD_FILE_OPENED(message):
			match = RepRapProtocol.REGEX_FILE_OPENED.search(message)
			self._selectFile(PrintingSdFileInformation(match.group(1), int(match.group(2))))

		# sd file streaming
		elif RepRapProtocol.MESSAGE_SD_BEGIN_WRITING(message):
			self._changeState(State.PRINTING)
			self._clearForSend.set()
		elif RepRapProtocol.MESSAGE_SD_END_WRITING(message):
			self.refreshSdFiles()

		# initial handshake with the firmware
		if self._state == State.CONNECTED:
			if RepRapProtocol.MESSAGE_START(message):
				self._startSeen = True
			elif RepRapProtocol.MESSAGE_WAIT(message) and self._startSeen:
				self._clearForSend.set()
			elif RepRapProtocol.MESSAGE_OK(message) and self._startSeen:
				self._changeState(State.OPERATIONAL)

		# resend == roll back time a bit
		if RepRapProtocol.MESSAGE_RESEND(message):
			self._handleResendRequest(message)

		# ok == go ahead with sending
		if RepRapProtocol.MESSAGE_OK(message):
			if self._isHeatingUp():
				self._heatupDone()

			if self._isPrinting():
				self._sendNext()
				if self._resendDelta is None:
					if time.time() > self._lastTemperatureUpdate + 5:
						self._sendTemperatureQuery(withType=True)
					elif self._isSdPrinting() and time.time() > self._lastSdProgressUpdate + 5:
						self._sendSdProgressQuery(withType=True)
			self._clearForSend.set()

	def onTimeoutReceived(self, source):
		if self._transport != source:
			return
		self._sendTemperatureQuery(withType=True)

	##~~ private

	def _send(self, command, highPriority=False, commandType=None, withChecksum=None, withLinenumber=None):
		if withChecksum is None:
			withChecksum = self._useChecksum()
		commandTuple = (str(command), withChecksum, withLinenumber)

		priority = 100
		if highPriority:
			priority = 1
		if commandType is not None:
			self._sendQueue.put((priority, commandTuple, commandType))
		else:
			self._sendQueue.put((priority, commandTuple))

	def _sendNext(self):
		if self._resendDelta is not None:
			command = self._lastLines[-self._resendDelta]
			lineNumber = self._currentLine - self._resendDelta
			self._send(command, withLinenumber=lineNumber)

			self._resendDelta -= 1
			if self._resendDelta <= 0:
				self._resendDelta = None
		else:
			command = self._currentFile.getNext()
			if command is None:
				self._finishPrintjob()
				return

			self._send(command)
			self._reportProgress()

	def _sendTemperatureQuery(self, withType=False):
		if withType:
			self._send(RepRapProtocol.COMMAND_GET_TEMP(), commandType=RepRapProtocol.COMMAND_TYPE_TEMPERATURE)
		else:
			self._send(RepRapProtocol.COMMAND_GET_TEMP())
		self._lastTemperatureUpdate = time.time()

	def _sendSdProgressQuery(self, withType=False):
		if withType:
			self._send(RepRapProtocol.COMMAND_SD_STATUS(), commandType=RepRapProtocol.COMMAND_TYPE_SD_PROGRESS)
		else:
			self._send(RepRapProtocol.COMMAND_SD_STATUS())
		self._lastSdProgressUpdate = time.time()

	def _handleErrors(self, line):
		# TODO Somehow figure out how to handle multiline errors here...

		# No matter the state, if we see an error, goto the error state and store the error for reference.
		if line.startswith('Error:'):
			#Oh YEAH, consistency.
			# Marlin reports an MIN/MAX temp error as "Error:x\n: Extruder switched off. MAXTEMP triggered !\n"
			#	But a bed temp error is reported as "Error: Temperature heated bed switched off. MAXTEMP triggered !!"
			#	So we can have an extra newline in the most common case. Awesome work people.
			if re.match('Error:[0-9]\n', line):
				line = line.rstrip() + self._readline()
			#Skip the communication errors, as those get corrected.
			if RepRapProtocol.MESSAGE_ERROR_COMMUNICATION(line):
				pass
			elif not self._state == State.ERROR:
				self.onError(line[6:])
		return line

	def _parseTemperatures(self, line):
		result = {}
		maxToolNum = 0
		for match in re.finditer(RepRapProtocol.REGEX_TEMPERATURE, line):
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

		result = {}

		# extruder temperatures
		if not "T0" in parsedTemps.keys() and "T" in parsedTemps.keys():
			# only single reporting, "T" is our one and only extruder temperature
			toolNum, actual, target = parsedTemps["T"]
			result["tool0"] = {
			"actual": actual,
			"target": target
			}
		elif "T0" in parsedTemps.keys():
			for n in range(maxToolNum + 1):
				tool = "T%d" % n
				if not tool in parsedTemps.keys():
					continue

				toolNum, actual, target = parsedTemps[tool]
				result["tool%d" % toolNum] = {
				"actual": actual,
				"target": target
				}

		# bed temperature
		if "B" in parsedTemps.keys():
			toolNum, actual, target = parsedTemps["B"]
			result["bed"] = {
			"actual": actual,
			"target": target
			}

		self._updateTemperature(result)

	def _handleResendRequest(self, message):
		lineToResend = None
		try:
			lineToResend = int(message.replace("N:", " ").replace("N", " ").replace(":", " ").split()[-1])
		except:
			if "rs" in message:
				lineToResend = int(message.split()[1])

		if lineToResend is not None:
			self._resendDelta = self._currentLine - lineToResend
			try:
				while not self._sendQueue.empty():
					self._sendQueue.get(False)
			except Queue.Empty:
				pass
			if self._resendDelta > len(self._lastLines) or len(self._lastLines) == 0 or self._resendDelta <= 0:
				error = "Printer requested line %d but no sufficient history is available, can't resend" % lineToResend
				# TODO self._logger.warn(error)
				if self._isPrinting():
					# abort the print, there's nothing we can do to rescue it now
					self.onError(error)
				else:
					# reset resend delta, we can't do anything about it
					self._resendDelta = None

	def _useChecksum(self):
		return not self._transportProperties[TransportProperties.FLOWCONTROL] and self._isBusy()

	##~~ the actual send queue handling starts here

	def _handleSendQueue(self):
		while self._sendQueueProcessing:
			self._clearForSend.wait()
			self._clearForSend.clear()
			entry = self._sendQueue.get()
			if len(entry) == 3:
				priority, commandTuple, commandType = entry
			else:
				priority, commandTuple = entry

			command, withChecksum, lineNumber = commandTuple
			preprocessedCommand = self._preprocessCommand(command, withChecksum=withChecksum, withLinenumber=lineNumber)
			self._transport.send(preprocessedCommand)

			if withChecksum:
				self._lastLines.append(command)

	def _preprocessCommand(self, command, withChecksum=False, withLinenumber=None):
		if withChecksum:
			if withLinenumber is not None:
				commandToSend = "N%d %s" % (withLinenumber, command)
			else:
				commandToSend = "N%d %s" % (self._currentLine, command)

			checksum = reduce(lambda x, y: x ^ y, map(ord, commandToSend))

			if withLinenumber is None:
				self._currentLine += 1

			return "%s*%d" % (commandToSend, checksum)
		else:
			return command


if __name__ == "__main__":
	from octoprint.settings import settings
	settings(True)

	class DummyProtocolListener(ProtocolListener):
		def __init__(self):
			self.firstPrint = True

		def onStateChange(self, source, oldState, newState):
			print "New State: %s" % newState
			if newState == State.OPERATIONAL and self.firstPrint:
				self.firstPrint = False
				print "Selecting file and starting print job"
				protocol.selectFile("C:/Users/Gina/AppData/Roaming/OctoPrint/uploads/whistle.gcode", FileDestinations.LOCAL)
				protocol.startPrint()

		def onTemperatureUpdate(self, source, temperatureData):
			print "### Temperature update: %r" % temperatureData

		def onPrintjobDone(self, source):
			print "### Printjob done!"

		def onSdFiles(self, source, files):
			print "### SD Files: %r" % files

		def onProgress(self, source, progress):
			print "### Progress: %r" % progress

		def onLogTx(self, source, tx):
			print ">> %s" % tx

		def onLogRx(self, source, rx):
			print "<< %s" % rx

		def onLogError(self, source, error):
			print "Error: %s" % error

	protocol = RepRapProtocol(SerialTransport, protocolListener=DummyProtocolListener())
	#from octoprint.comm.protocol.repetier import RepetierTextualProtocol
	#protocol = RepetierTextualProtocol(SerialTransport, protocolListener=DummyProtocolListener())
	protocol.connect({"port": "VIRTUAL"})

	import time
	while True:
		time.sleep(0.1)