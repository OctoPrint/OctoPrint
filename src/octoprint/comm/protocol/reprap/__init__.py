# coding=utf-8
import Queue
from collections import deque
from octoprint.events import eventManager, Events
from octoprint.util import filterNonAscii

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 Gina Häußge - Released under terms of the AGPLv3 License"

import re
import threading
import time
from octoprint.comm.protocol import State, Protocol, PrintingSdFileInformation
from octoprint.comm.protocol.reprap.util import GcodeCommand, CommandQueue, PrintingGcodeFileInformation, \
	StreamingGcodeFileInformation, TypeAlreadyInQueue
from octoprint.filemanager import valid_file_type
from octoprint.filemanager.destinations import FileDestinations
from octoprint.settings import settings


class RepRapProtocol(Protocol):

	__protocolinfo__ = ("reprap", "RepRap", False)

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
	MESSAGE_ERROR_MULTILINE = staticmethod(lambda line: RepRapProtocol.REGEX_ERROR_MULTILINE.match(line))
	MESSAGE_ERROR_COMMUNICATION = staticmethod(lambda line: 'checksum mismatch' in line.lower()
															or 'wrong checksum' in line.lower()
															or 'line number is not last line number' in line.lower()
															or 'expected line' in line.lower()
															or 'no line number with checksum' in line.lower()
															or 'no checksum with line number' in line.lower()
															or 'missing checksum' in line.lower())
	MESSAGE_RESEND = staticmethod(lambda line: line.lower().startswith("resend") or line.lower().startswith("rs"))

	TRANSFORM_ERROR = staticmethod(lambda line: line[6:] if line.startswith("Error:") else line[2:])

	## Commands
	COMMAND_GET_TEMP = staticmethod(lambda: GcodeCommand("M105"))
	COMMAND_SET_EXTRUDER_TEMP = staticmethod(lambda s, t, w: GcodeCommand("M109", s=s, t=t) if w else GcodeCommand("M104", s=s, t=t))
	COMMAND_SET_LINE = staticmethod(lambda n: GcodeCommand("M110 N%d" % n))
	COMMAND_SET_BED_TEMP = staticmethod(lambda s, w: GcodeCommand("M190", s=s) if w else GcodeCommand("M140", s=s))
	COMMAND_SET_RELATIVE_POSITIONING = staticmethod(lambda: GcodeCommand("G91"))
	COMMAND_SET_ABSOLUTE_POSITIONING = staticmethod(lambda: GcodeCommand("G90"))
	COMMAND_MOVE_AXIS = staticmethod(lambda axis, amount, speed: GcodeCommand("G1", x=amount if axis=='x' else None, y=amount if axis=='y' else None, z=amount if axis=='z' else None, f=speed))
	COMMAND_EXTRUDE = staticmethod(lambda amount, speed: GcodeCommand("G1", e=amount, f=speed))
	COMMAND_HOME_AXIS = staticmethod(lambda x, y, z: GcodeCommand("G28", x=0 if x else None, y=0 if y else None, z=0 if z else None))
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

	# Regex matching multi line errors
	#
	# Marlin reports MAXTEMP issues on extruders in the format
	#
	#   Error:{int}
	#   Extruder switched off. {MIN|MAX}TEMP triggered !
	#
	# This regex matches the line initiating those multiline errors. If it is encountered, the next line has
	# to be fetched from the transport layer in order to fully handle the error at hand.
	REGEX_ERROR_MULTILINE = re.compile("Error:[0-9]\n")

	def __init__(self, transport_factory, protocol_listener=None):
		Protocol.__init__(self, transport_factory, protocol_listener)

		self._lastTemperatureUpdate = time.time()
		self._lastSdProgressUpdate = time.time()

		self._startSeen = False
		self._receivingSdFileList = False

		self._send_queue = CommandQueue()

		self._clear_for_send = threading.Event()

		self._last_lines = deque([], 50)
		self._resend_delta = None
		self._last_resend_request = None

		self._force_checksum = False
		self._rx_cache_size = settings().getInt(["communication", "protocolOptions", "buffer"])
		self._nack_lines = deque([])
		self._nack_lock = threading.Lock()

		self._send_queue_processing = True
		self._thread = threading.Thread(target=self._handle_send_queue, name="SendQueueHandler")
		self._thread.daemon = True
		self._thread.start()

		self._fill_queue_processing = True
		self._fill_thread = threading.Thread(target=self._fill_send_queue, name="FillQueueHandler")
		self._fill_thread.daemon = True
		self._fill_thread.start()

		self._current_line = 1
		self._currentExtruder = 0
		self._state = State.OFFLINE

		self._reset()

	def _reset(self):
		self._lastTemperatureUpdate = time.time()
		self._lastSdProgressUpdate = time.time()

		if settings().get(["feature", "waitForStartOnConnect"]) == True:
			self._startSeen = False
			self._clear_for_send.clear()
		else:
			self._startSeen = True
			self._clear_for_send.set()

		self._receivingSdFileList = False

		# create a new queue to clear the old one
		self._send_queue = CommandQueue()

		self._last_lines.clear()
		self._resend_delta = None
		self._last_resend_request = None

		self._force_checksum = settings().getBoolean(["feature", "alwaysSendChecksum"])
		self._nack_lines.clear()

		self._current_line = 1
		self._currentExtruder = 0

	def connect(self, opt):
		self._reset()

		# connect
		Protocol.connect(self, opt)

		# enqueue our first temperature query so it get's sent right on establishment of the connection
		self._send_temperature_query(withType=True)

	def disconnect(self, on_error=False):
		self._clear_for_send.clear()
		# disconnect
		Protocol.disconnect(self, on_error=on_error)

	def select_file(self, filename, origin):
		if origin == FileDestinations.SDCARD:
			if not self._sd_available:
				return
			self._send(RepRapProtocol.COMMAND_SD_SELECT_FILE(filename), highPriority=True)
		else:
			self._selectFile(PrintingGcodeFileInformation(filename, self.get_temperature_offsets))

	def start_print(self):
		wasPaused = self._state == State.PAUSED

		Protocol.start_print(self)
		if isinstance(self._current_file, PrintingSdFileInformation):
			if wasPaused:
				self._send(RepRapProtocol.COMMAND_SD_SET_POS(0))
				self._current_file.setFilepos(0)
			self._send(RepRapProtocol.COMMAND_SD_START())

	def cancel_print(self):
		if isinstance(self._current_file, PrintingSdFileInformation):
			self._send(RepRapProtocol.COMMAND_SD_PAUSE)
			self._send(RepRapProtocol.COMMAND_SD_SET_POS(0))

		Protocol.cancel_print(self)

	def init_sd(self):
		Protocol.init_sd(self)
		self._send(RepRapProtocol.COMMAND_SD_INIT())
		if settings().getBoolean(["feature", "sdAlwaysAvailable"]) == True:
			self._changeSdState(True)

	def release_sd(self):
		Protocol.release_sd(self)
		self._send(RepRapProtocol.COMMAND_SD_RELEASE())
		if settings().getBoolean(["feature", "sdAlwaysAvailable"]) == True:
			self._changeSdState(False)

	def refresh_sd_files(self):
		if not self._sd_available:
			return

		Protocol.refresh_sd_files(self)
		self._send(RepRapProtocol.COMMAND_SD_REFRESH())

	def add_sd_file(self, path, local, remote):
		Protocol.add_sd_file(self, path, local, remote)
		if not self.is_operational() or self.is_busy():
			return

		self.send_manually(RepRapProtocol.COMMAND_SD_BEGIN_WRITE(remote))

		self._current_file = StreamingGcodeFileInformation(path, local, remote)

		self._current_file.start()

		eventManager().fire(Events.TRANSFER_STARTED, {"local": local, "remote": remote})

		self._startFileTransfer(remote, self._current_file.getFilesize())
		self._changeState(State.STREAMING)

	def remove_sd_file(self, filename):
		Protocol.remove_sd_file(self, filename)
		if not self.is_operational() or \
				(self.is_busy() and isinstance(self._current_file, PrintingSdFileInformation) and
						 self._current_file.getFilename() == filename):
			return

		self.send_manually(RepRapProtocol.COMMAND_SD_DELETE(filename))
		self.refresh_sd_files()

	def set_temperature(self, type, value):
		if type.startswith("tool"):
			if settings().getInt(["printerParameters", "numExtruders"]) > 1:
				try:
					tool_num = int(type[len("tool"):])
					self.send_manually(RepRapProtocol.COMMAND_SET_EXTRUDER_TEMP(value, tool_num, False))
				except ValueError:
					pass
			else:
				# set temperature without tool number
				self.send_manually(RepRapProtocol.COMMAND_SET_EXTRUDER_TEMP(value, None, False))
		elif type == "bed":
			self.send_manually(RepRapProtocol.COMMAND_SET_BED_TEMP(value, False))

	def jog(self, axis, amount):
		speeds = settings().get(["printerParameters", "movementSpeed", ["x", "y", "z"]], asdict=True)
		commands = (
			RepRapProtocol.COMMAND_SET_RELATIVE_POSITIONING(),
			RepRapProtocol.COMMAND_MOVE_AXIS(axis, amount, speeds[axis]),
			RepRapProtocol.COMMAND_SET_ABSOLUTE_POSITIONING()
		)
		self.send_manually(commands)

	def home(self, axes):

		commands = (
			RepRapProtocol.COMMAND_SET_RELATIVE_POSITIONING(),
			RepRapProtocol.COMMAND_HOME_AXIS('x' in axes, 'y' in axes, 'z' in axes),
			RepRapProtocol.COMMAND_SET_ABSOLUTE_POSITIONING()
		)
		self.send_manually(commands)

	def extrude(self, amount):
		extrusionSpeed = settings().get(["printerParameters", "movementSpeed", "e"])

		commands = (
			RepRapProtocol.COMMAND_SET_RELATIVE_POSITIONING(),
			RepRapProtocol.COMMAND_EXTRUDE(amount, extrusionSpeed),
			RepRapProtocol.COMMAND_SET_ABSOLUTE_POSITIONING()
		)
		self.send_manually(commands)

	def change_tool(self, tool):
		try:
			tool_num = int(tool[len("tool"):])
			self.send_manually(RepRapProtocol.COMMAND_SET_TOOL(tool_num))
		except ValueError:
			pass

	def send_manually(self, command, high_priority=False):
		if self.is_streaming():
			return
		if isinstance(command, (tuple, list)):
			for c in command:
				self._send(c, highPriority=high_priority)
		else:
			self._send(command, highPriority=high_priority)

	def _fileTransferFinished(self, current_file):
		if isinstance(current_file, StreamingGcodeFileInformation):
			self.send_manually(RepRapProtocol.COMMAND_SD_END_WRITE(current_file.getRemoteFilename()))
			eventManager().fire(Events.TRANSFER_DONE, {
				"local": current_file.getLocalFilename(),
				"remote": current_file.getRemoteFilename(),
				"time": self.get_print_time()
			})
		else:
			self._logger.warn("Finished file transfer to printer's SD card, but could not determine remote filename, assuming 'unknown.gco' for end-write-command")
			self.send_manually(RepRapProtocol.COMMAND_SD_END_WRITE("unknown.gco"))
		self.refresh_sd_files()

	##~~ callback methods

	def onMessageReceived(self, source, message):
		if self._transport != source:
			return

		message = self._handle_errors(message.strip())

		# resend == roll back time a bit
		if RepRapProtocol.MESSAGE_RESEND(message):
			# zero cache fill count
			with self._nack_lock:
				self._nack_lines.clear()
			self._handle_resend_request(message)
			return

		if self._resend_delta is None and not self.is_streaming():
			if time.time() > self._lastTemperatureUpdate + 5:
				self._send_temperature_query(withType=True)
			elif self.is_sd_printing() and time.time() > self._lastSdProgressUpdate + 5:
				self._send_sd_progress_query(withType=True)

		# ok == go ahead with sending
		if RepRapProtocol.MESSAGE_OK(message):
			if self._state == State.CONNECTED and self._startSeen:
				# if we are currently connected, have seen start and just gotten an "ok" we are now operational
				self._changeState(State.OPERATIONAL)
			if self.is_heating_up():
				self._heatupDone()

			# lower cache fill count since the command went through
			with self._nack_lock:
				if len(self._nack_lines) > 0:
					self._nack_lines.popleft()
			self._clear_for_send.set()
			return

		if RepRapProtocol.MESSAGE_WAIT(message):
			with self._nack_lock:
				self._clear_for_send.set()

		# SD file list
		if self._receivingSdFileList and not RepRapProtocol.MESSAGE_SD_END_FILE_LIST(message):
			fileinfo = message.strip().split(None, 2)
			if len(fileinfo) > 1:
				filename, size = fileinfo
				filename = filename.lower()
				try:
					size = int(size)
				except ValueError:
					# whatever that was, it was not an integer, so we'll ignore it and set size to None
					size = None
			else:
				filename = fileinfo[0].lower()
				size = None

			if valid_file_type(filename, "gcode"):
				if filterNonAscii(filename):
					self._logger.warn("Got a file from printer's SD that has a non-ascii filename (%s), that shouldn't happen according to the protocol" % filename)
				else:
					self._addSdFile(filename, size)
				return

		##~~ regular message processing

		# temperature updates
		if RepRapProtocol.MESSAGE_TEMPERATURE(message):
			self._process_temperatures(message)
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
			if isinstance(self._current_file, PrintingSdFileInformation):
				self._current_file.setFilepos(int(match.group(1)))
			self._reportProgress()
		elif RepRapProtocol.MESSAGE_SD_DONE_PRINTING(message):
			if isinstance(self._current_file, PrintingSdFileInformation):
				self._current_file.setFilepos(0)
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
			self._changeState(State.STREAMING)
		elif RepRapProtocol.MESSAGE_SD_END_WRITING(message):
			self.refresh_sd_files()

		# firmware specific messages
		if not self._evaluate_firmware_specific_messages(source, message):
			return

		# initial handshake with the firmware
		if RepRapProtocol.MESSAGE_START(message):
			if self._state != State.CONNECTED:
				# we received a "start" while running, this means the printer has unexpectedly reset
				self._reset()
				self._changeState(State.CONNECTED)
			# otherwise we did not see "start" from the firmware yet and we just did; we are cleared for sending
			self._startSeen = True
			self._clear_for_send.set()

	def onTimeoutReceived(self, source):
		if self._transport != source:
			return
		self._logger.warn("Communication timeout")
		# allow sending to restart communcation
		if self._state != State.OFFLINE:
			self._clear_for_send.set()

	##~~ private

	def _evaluate_firmware_specific_messages(self, source, message):
		return True

	def _send(self, command, highPriority=False, commandType=None, withChecksum=None, withLinenumber=None):
		if command is None:
			return

		if withChecksum is None:
			withChecksum = self._force_checksum

		priority = 100
		if highPriority:
			priority = 1

		if not isinstance(command, GcodeCommand):
			command = GcodeCommand.from_line(command)
		preprocessed = self._preprocess_command(command, with_checksum=withChecksum, with_line_number=withLinenumber)

		if preprocessed is None:
			return

		try:
			if commandType is not None:
				self._send_queue.put((priority, command, preprocessed, commandType))
			else:
				self._send_queue.put((priority, command, preprocessed))
		except TypeAlreadyInQueue:
			self._rollback_preprocessing(command, with_checksum=withChecksum, with_line_number=withLinenumber)

	# Called only from worker thread, not thread safe
	def _send_next(self):
		if self._resend_delta is not None:
			command = self._last_lines[-self._resend_delta]
			lineNumber = self._current_line - self._resend_delta
			self._send(command, withLinenumber=lineNumber)

			self._resend_delta -= 1
			if self._resend_delta <= 0:
				self._resend_delta = None
		else:
			command = self._current_file.getNext()
			if command is None:
				if self.is_streaming():
					self._finishFileTransfer()
				else:
					self._finishPrintjob()
				return

			self._send(command)
			self._reportProgress()

	def _send_temperature_query(self, withType=False):
		if withType:
			self._send(RepRapProtocol.COMMAND_GET_TEMP(), commandType=RepRapProtocol.COMMAND_TYPE_TEMPERATURE)
		else:
			self._send(RepRapProtocol.COMMAND_GET_TEMP())
		self._lastTemperatureUpdate = time.time()

	def _send_sd_progress_query(self, withType=False):
		if withType:
			self._send(RepRapProtocol.COMMAND_SD_STATUS(), commandType=RepRapProtocol.COMMAND_TYPE_SD_PROGRESS)
		else:
			self._send(RepRapProtocol.COMMAND_SD_STATUS())
		self._lastSdProgressUpdate = time.time()

	def _handle_errors(self, line):
		if RepRapProtocol.MESSAGE_ERROR(line):
			if RepRapProtocol.MESSAGE_ERROR_MULTILINE(line):
				error = self._transport.receive()
			else:
				error = RepRapProtocol.TRANSFORM_ERROR(line)

			# skip the communication errors as those get corrected via resend requests
			if RepRapProtocol.MESSAGE_ERROR_COMMUNICATION(error):
				pass
			# handle the error
			elif not self._state == State.ERROR:
				self.onError(error)
		return line

	def _parse_temperatures(self, line):
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

	def _process_temperatures(self, line):
		maxToolNum, parsedTemps = self._parse_temperatures(line)

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

	def _handle_resend_request(self, message):
		line_to_resend = None
		try:
			line_to_resend = int(message.replace("N:", " ").replace("N", " ").replace(":", " ").split()[-1])
		except:
			if "rs" in message:
				line_to_resend = int(message.split()[1])

		if line_to_resend is not None:
			self._resend_delta = self._current_line - line_to_resend

			try:
				while self._send_queue.get(block=False):
					continue
			except Queue.Empty:
				pass

			if self._resend_delta > len(self._last_lines) or len(self._last_lines) == 0 or self._resend_delta <= 0:
				error = "Printer requested line %d but no sufficient history is available, can't resend" % line_to_resend
				self._logger.warn(error)
				if self.is_printing():
					# abort the print, there's nothing we can do to rescue it now
					self.onError(error)
				else:
					# reset resend delta, we can't do anything about it
					self._resend_delta = None

				# reset line number local and remote
				self._current_line = 1
				self._last_lines.clear()
				self._resend_delta = None
				self._send(RepRapProtocol.COMMAND_SET_LINE(0))

	##~~ specific command actions

	def _gcode_T(self, command, with_checksum, with_line_number):
		self._currentExtruder = command.tool
		return command, with_checksum, with_line_number

	def _gcode_G0(self, command, with_checksum, with_line_number):
		if command.z is not None:
			z = command.z
			self._reportZChange(z)
		return command, with_checksum, with_line_number
	_gcode_G1 = _gcode_G0

	def _gcode_M0(self, command, with_checksum, with_line_number):
		self.pause_print()
		# Don't send the M0 or M1 to the machine, as M0 and M1 are handled as an LCD menu pause.
		return None, with_checksum, with_line_number
	_gcode_M1 = _gcode_M0

	def _gcode_M104(self, command, with_checksum, with_line_number):
		tool = self._currentExtruder
		if command.t is not None:
			tool = command.t
		if command.s is not None:
			target = command.s
			tool_key = "tool%d" % tool
			if tool_key in self._current_temperature.keys() and self._current_temperature[tool_key] is not None and isinstance(self._current_temperature[tool_key], tuple):
				actual, old_target = self._current_temperature[tool_key]
				self._current_temperature[tool_key] = (actual, target)
			else:
				self._current_temperature[tool_key] = (None, target)
		return command, with_checksum, with_line_number
	_gcode_M109 = _gcode_M104

	def _gcode_M140(self, command, with_checksum, with_line_number):
		if command.s is not None:
			target = command.s
			if "bed" in self._current_temperature.keys() and self._current_temperature["bed"] is not None and isinstance(self._current_temperature["bed"], tuple):
				actual, old_target = self._current_temperature["bed"]
				self._current_temperature["bed"] = (actual, target)
			else:
				self._current_temperature["bed"] = (None, target)
		return command, with_checksum, with_line_number
	_gcode_M190 = _gcode_M140

	def _gcode_M110(self, command, with_checksum, with_line_number):
		if command.n is not None:
			new_line_number = command.n
		else:
			new_line_number = 0

		self._current_line = new_line_number + 1

		# after a reset of the line number we have no way to determine what line exactly the printer now wants
		self._last_lines.clear()
		self._resend_delta = None

		# send M110 command with new line number
		return command, with_checksum, new_line_number

	def _gcode_M112(self, command, with_checksum, with_line_number): # It's an emergency what todo? Canceling the print should be the minimum
		self.cancel_print()
		return command, with_checksum, with_line_number


	##~~ handle queue filling in this thread when printing or streaming

	def _fill_send_queue(self):
		while self._fill_queue_processing:
			# queue is full, wait a bit before checking again
			if self._send_queue.qsize() > 20:
				time.sleep(0.05)

			# send_next only if printing (not SD) or streaming
			elif ((self._state == State.PRINTING and not isinstance(self._current_file, PrintingSdFileInformation))
			     or self._state == State.STREAMING):
				self._send_next()

			# not printing or streaming
			else:
				time.sleep(0.1)


	##~~ the actual send queue handling starts here

	def _handle_send_queue(self):
		while self._send_queue_processing:
			if self._send_queue.qsize() == 0:
				# queue is empty, wait a bit before checking again
				time.sleep(0.1)
				continue
			entry = self._send_queue.peek()
			if len(entry) == 4:
				priority, command, preprocessed, command_type = entry
			else:
				priority, command, preprocessed = entry

			size = len(preprocessed) + 1
			# deassert _clear_for_send to wait for an "ok" if cache full
			self._nack_lock.acquire()
			if sum(self._nack_lines) + size > self._rx_cache_size > 0:
				self._nack_lock.release()
				self._clear_for_send.clear()
				self._clear_for_send.wait()
				continue
			# put tx size into the list so we can pop it later when we get "ok"
			self._nack_lines.append(size)
			self._nack_lock.release()
			# send the command
			self._transport.send(preprocessed)
			# remove from queue
			self._send_queue.get()

			if command is not None:
				self._last_lines.append(command)
			if self._rx_cache_size <= 0:
				self._clear_for_send.clear()
				self._clear_for_send.wait()


	def _preprocess_command(self, command, with_checksum=False, with_line_number=None):
		if command is None:
			return None

		gcode_command_handler = "_gcode_%s" % command.command
		if hasattr(self, gcode_command_handler) and not self.is_streaming():
			command, with_checksum, with_line_number = getattr(self, gcode_command_handler)(command, with_checksum, with_line_number)
			if command is None:
				return None

		if with_checksum:
			if with_line_number is not None:
				command_to_send = "N%d %s" % (with_line_number, str(command))
			else:
				command_to_send = "N%d %s" % (self._current_line, str(command))

			checksum = reduce(lambda x, y: x ^ y, map(ord, command_to_send))

			if with_line_number is None:
				self._current_line += 1

			return "%s*%d" % (command_to_send, checksum)
		else:
			return str(command)

	def _rollback_preprocessing(self, command, with_checksum=False, with_line_number=None):
		if with_checksum and with_line_number is None:
			self._current_line -= 1


class NopContext(object):
	def __enter__(self):
		pass

	def __exit__(self, *args):
		pass
