# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 Gina Häußge - Released under terms of the AGPLv3 License"

import re
import threading
import time
from octoprint.comm.protocol import State, Protocol, PrintingSdFileInformation
from octoprint.comm.protocol.reprap.util import GcodeCommand, CommandQueue, PrintingGcodeFileInformation
from octoprint.comm.transport import TransportProperties
from octoprint.filemanager.destinations import FileDestinations


class RepRapProtocol(Protocol):

	MESSAGE_OK = staticmethod(lambda line: line.startswith("ok"))
	MESSAGE_START = staticmethod(lambda line: line.startswith("start"))
	MESSAGE_WAIT = staticmethod(lambda line: line.startswith("wait"))

	MESSAGE_SD_INIT_OK = staticmethod(lambda line: line == "SD card ok")
	MESSAGE_SD_INIT_FAIL = staticmethod(lambda line: "SD init fail" in line or "volume.init failed" in line or "" in line)
	MESSAGE_SD_FILE_OPENED = staticmethod(lambda line: line.startswith("File opened"))
	MESSAGE_SD_FILE_SELECTED = staticmethod(lambda line: line.startswith("File selected"))

	MESSAGE_ERROR = staticmethod(lambda line: line.startswith("Error:") or line.startswith("!!"))
	MESSAGE_ERROR_COMMUNICATION = staticmethod(lambda line: 'checksum mismatch' in line.lower()
			or 'wrong checksum' in line.lower()
			or 'line number is not last line number' in line.lower()
			or 'expected line' in line.lower()
			or 'no line number with checksum' in line.lower()
			or 'no checksum with line number' in line.lower()
			or 'missing checksum' in line.lower())
	MESSAGE_RESEND = staticmethod(lambda line: line.lower().startswith("resend") or line.lower().startswith("rs"))

	MESSAGE_TEMPERATURE = staticmethod(lambda x: ' T:' in x or x.startswith('T:') or ' T0:' in x or x.startswith('T0:'))

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

	def __init__(self, transportFactory, protocolListener=None):
		Protocol.__init__(self, transportFactory, protocolListener)

		self._lastTemperatureUpdate = time.time()
		self._startSeen = False
		self._sdAvailable = False

		self._sendQueue = CommandQueue()

		self._clearForSend = threading.Event()
		self._clearForSend.clear()

		self._sendQueueProcessing = True
		self._thread = threading.Thread(target=self._handleSendQueue, name="SendQueueHandler")
		self._thread.daemon = True
		self._thread.start()

		self._currentLine = 1
		self._state = State.OFFLINE

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

	def onMessageReceived(self, source, message):
		if self._transport != source:
			return

		message = self._handleErrors(message.strip())

		# message processing
		if RepRapProtocol.MESSAGE_TEMPERATURE(message):
			self._processTemperatures(message)

		elif RepRapProtocol.MESSAGE_SD_INIT_OK(message):
			self._sdAvailable = True

		elif RepRapProtocol.MESSAGE_SD_INIT_FAIL(message):
			self._sdAvailable = False

		elif RepRapProtocol.MESSAGE_SD_FILE_OPENED(message):
			match = RepRapProtocol.REGEX_FILE_OPENED.search(message)
			self._currentFile = PrintingSdFileInformation(match.group(1), int(match.group(2)))

		elif RepRapProtocol.MESSAGE_SD_FILE_SELECTED(message):
			# trigger callback and stuff
			pass

		# initial handshake with the firmware
		if self._state == State.CONNECTED:

			if RepRapProtocol.MESSAGE_START(message):
				self._startSeen = True
			elif RepRapProtocol.MESSAGE_WAIT(message) and self._startSeen:
				self._clearForSend.set()
				self._sendTemperatureQuery(withType=True)
			elif RepRapProtocol.MESSAGE_OK(message):
				self._changeState(State.OPERATIONAL)

		# ok == go ahead with sending
		if RepRapProtocol.MESSAGE_OK(message):
			if self._state == State.PRINTING:
				if time.time() > self._lastTemperatureUpdate + 5:
					self._sendTemperatureQuery(withType=True)
				self._sendNext()
			self._clearForSend.set()

	def onTimeoutReceived(self, source):
		if self._transport != source:
			return
		self._sendTemperatureQuery(withType=True)

	def sendManually(self, command, highPriority=False):
		self._send(command, highPriority=highPriority, withChecksum=self._useChecksum())

	def _send(self, command, highPriority=False, commandType=None, withChecksum=False):
		commandTuple = (str(command), withChecksum)

		priority = 100
		if highPriority:
			priority = 1
		if commandType is not None:
			self._sendQueue.put((priority, commandTuple, commandType))
		else:
			self._sendQueue.put((priority, commandTuple))

	def _sendNext(self):
		command = self._currentFile.getNext()
		if command is None:
			self._changeState(State.OPERATIONAL)
			return

		self._send(command, withChecksum=self._useChecksum())

	def _sendTemperatureQuery(self, withType=False):
		if withType:
			self._send(RepRapProtocol.COMMAND_GET_TEMP(), commandType=RepRapProtocol.COMMAND_TYPE_TEMPERATURE)
		else:
			self._send(RepRapProtocol.COMMAND_GET_TEMP())
		self._lastTemperatureUpdate = time.time()

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

	def _useChecksum(self):
		return not self._transportProperties[TransportProperties.FLOWCONTROL] and \
			   (self._state == State.PRINTING or self._state == State.HEATING)

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

			command, withChecksum = commandTuple
			self._transport._send(self._preprocessCommand(command, withChecksum=withChecksum))

	def _preprocessCommand(self, command, withChecksum=False):
		if withChecksum:
			commandToSend = "N%d %s" % (self._currentLine, command)
			checksum = reduce(lambda x, y: x ^ y, map(ord, commandToSend))
			self._currentLine += 1
			return "%s*%d" % (commandToSend, checksum)
		else:
			return command

