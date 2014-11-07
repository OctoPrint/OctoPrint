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
from octoprint.comm.protocol.reprap.util import GcodeCommand, CommandQueue, CommandQueueEntry, PrintingGcodeFileInformation, \
	StreamingGcodeFileInformation, TypeAlreadyInQueue, SpecialCommandQueueEntry
from octoprint.comm.transport import SendTimeout
from octoprint.filemanager import valid_file_type
from octoprint.filemanager.destinations import FileDestinations
from octoprint.settings import settings
from octoprint.util import CountedEvent


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
	MESSAGE_ERROR_COMMUNICATION_LINENUMBER = staticmethod(lambda line: 'line number is not line number' in line.lower()
															or 'expected line' in line.lower())
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

		self._clear_for_send = CountedEvent(max=20)

		self._force_checksum = True
		self._wait_for_start = False
		self._sd_always_available = False
		self._rx_cache_size = 0

		self._blocking_command_active = False

		self._temperature_interval = 5.0
		self._sdstatus_interval = 5.0

		self._nack_lines = deque([])
		self._nack_lock = threading.RLock()

		self._previous_resend = False
		self._last_comm_error = None
		self._last_resend_number = None
		self._current_resend_count = 0
		self._nacks_before_resend = 0

		self._send_queue_processing = True
		self._thread = threading.Thread(target=self._handle_send_queue, name="SendQueueHandler")
		self._thread.daemon = True
		self._thread.start()

		self._fill_queue_semaphore = threading.Semaphore(20)
		self._fill_queue_state_signal = threading.Event()
		self._fill_queue_mutex = threading.Lock()
		self._fill_queue_processing = True
		self._fill_thread = threading.Thread(target=self._fill_send_queue, name="FillQueueHandler")
		self._fill_thread.daemon = True
		self._fill_thread.start()

		self._current_line = 1
		self._current_extruder = 0
		self._state = State.OFFLINE

		self._preprocessors = dict()
		self._setup_preprocessors()

		self._reset()

	def _setup_preprocessors(self):
		self._preprocessors.clear()

		for attr in dir(self):
			if attr.startswith("_gcode") and (attr.endswith("_queued") or attr.endswith("_sent") or attr.endswith("_acknowledged")):
				split_attr = attr.split("_")
				if not len(split_attr) == 4:
					continue

				prefix, code, postfix = split_attr[1:]
				if not postfix in self._preprocessors:
					self._preprocessors[postfix] = dict()
				self._preprocessors[postfix][code] = getattr(self, attr)

	def _reset(self, from_start=False):
		with self._nack_lock:
			self._lastTemperatureUpdate = time.time()
			self._lastSdProgressUpdate = time.time()

			self._blocking_command_active = False

			if self._wait_for_start:
				self._startSeen = from_start
			else:
				self._startSeen = True

			if not self._startSeen:
				self._clear_for_send.clear(completely=True)
			else:
				if self._clear_for_send.blocked():
					self._clear_for_send.set()

			self._receivingSdFileList = False

			# clear the the send queue
			self._send_queue.clear()

			self._nack_lines.clear()
			self._current_line = 1
			self._current_extruder = 0

			self._previous_resend = False
			self._last_comm_error = None
			self._last_resend_number = None
			self._current_resend_count = 0
			self._nacks_before_resend = 0

	def connect(self, protocol_options, transport_options):
		self._wait_for_start = protocol_options["waitForStart"] if "waitForStart" in protocol_options else False
		self._force_checksum = protocol_options["checksum"] if "checksum" in protocol_options else True
		self._sd_always_available = protocol_options["sdAlwaysAvailable"] if "sdAlwaysAvailable" in protocol_options else False
		self._rx_cache_size = protocol_options["buffer"] if "buffer" in protocol_options else 0
		self._temperature_interval = protocol_options["timeout"]["temperature"] if "timeout" in protocol_options and "temperature" in protocol_options["timeout"] else 5.0
		self._sdstatus_interval = protocol_options["timeout"]["sdstatus"] if "timeout" in protocol_options and "sdstatus" in protocol_options["timeout"] else 5.0

		self._reset()

		# connect
		Protocol.connect(self, protocol_options, transport_options)

		# we'll send an M110 first to reset line numbers to 0
		self._send(RepRapProtocol.COMMAND_SET_LINE(0), high_priority=True)

		# enqueue our first temperature query so it gets sent right on establishment of the connection
		self._send_temperature_query(with_type=True)

	def disconnect(self, on_error=False):
		self._clear_for_send.clear(completely=True)
		# disconnect
		Protocol.disconnect(self, on_error=on_error)

	def select_file(self, filename, origin):
		if origin == FileDestinations.SDCARD:
			if not self._sd_available:
				return
			self._send(RepRapProtocol.COMMAND_SD_SELECT_FILE(filename), high_priority=True)
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

		with self._fill_queue_mutex:
			self._send_queue.clear(matcher=lambda entry: entry is not None and entry.command is not None and hasattr(entry.command, "progress") and entry.command.progress is not None)

	def init_sd(self):
		Protocol.init_sd(self)
		self._send(RepRapProtocol.COMMAND_SD_INIT())
		if self._sd_always_available:
			self._changeSdState(True)

	def release_sd(self):
		Protocol.release_sd(self)
		self._send(RepRapProtocol.COMMAND_SD_RELEASE())
		if self._sd_always_available:
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
				self._send(c, high_priority=high_priority)
		else:
			self._send(command, high_priority=high_priority)

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
			self._previous_resend = True
			self._handle_resend_request(message)
			return

		if RepRapProtocol.MESSAGE_WAIT(message):
			#self._clear_for_send.set()
			# TODO really?
			pass

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
				self._changeState(State.CONNECTED)
			self._reset(from_start=True)

		if not self.is_streaming():
			if time.time() > self._lastTemperatureUpdate + self._temperature_interval:
				self._send_temperature_query(with_type=True)
			elif self.is_sd_printing() and time.time() > self._lastSdProgressUpdate + self._sdstatus_interval:
				self._send_sd_progress_query(with_type=True)

		# ok == go ahead with sending
		if RepRapProtocol.MESSAGE_OK(message):
			if self._state == State.CONNECTED and self._startSeen:
				# if we are currently connected, have seen start and just gotten an "ok" we are now operational
				self._changeState(State.OPERATIONAL)
			if self.is_heating_up():
				self._heatupDone()

			if not self._previous_resend:
				# our most left line from the nack_lines just got acknowledged
				self._process_acknowledgement()
			else:
				self._previous_resend = False
			self._clear_for_send.set()
			return

	def onTimeoutReceived(self, source):
		if self._transport != source:
			return
		# allow sending to restart communication
		if self._state != State.OFFLINE:
			if self._clear_for_send.blocked():
				self._clear_for_send.set()

	def _stateChanged(self, newState):
		if ((self._state == State.PRINTING and not isinstance(self._current_file, PrintingSdFileInformation))
			or self._state == State.STREAMING):
			self._fill_queue_state_signal.set()
		else:
			self._fill_queue_state_signal.clear()

	##~~ private

	def _process_acknowledgement(self):
		with self._nack_lock:
			if len(self._nack_lines) > 0:
				entry = self._nack_lines.popleft()

				# process command as acknowledged
				self._process_command(entry.command, "acknowledged", with_line_number=entry.line_number)

				if entry.command is not None:
					if entry.command.progress is not None:
						# if we got a progress, report it
						self._reportProgress(**entry.command.progress)

					if entry.command.callback is not None:
						# if we got a callback, call it
						entry.command.callback(entry.command)

				if len(self._nack_lines) > 0:
					# let's take a look at the next item in the nack queue, it might be a special entry demanding some action
					# from us now
					following_entry = self._nack_lines[0]
					if isinstance(following_entry, SpecialCommandQueueEntry):

						if following_entry.type == SpecialCommandQueueEntry.TYPE_JOBDONE:
							# we got a special queue item that marks that we just acknowledged the last command of
							# an ongoing print job, so let's signal that now
							if self.is_streaming():
								self._finishFileTransfer()
							else:
								self._finishPrintjob()

						# let's remove the special command, we should have processed it now...
						self._nack_lines.popleft()

			# since we just got an acknowledgement, no more resends are pending
			self._last_resend_number = None
			self._current_resend_count = 0
			self._nacks_before_resend = 0

	def _evaluate_firmware_specific_messages(self, source, message):
		return True

	def _send(self, command, high_priority=False, command_type=None, with_progress=None):
		if command is None:
			return

		if isinstance(command, CommandQueueEntry):
			entry = command
			if entry.command is not None:
				entry.command.progress = with_progress
		else:
			if not isinstance(command, GcodeCommand):
				command = GcodeCommand.from_line(command)
			command.progress = with_progress

			command, with_line_number = self._process_command(command, "queued")
			if command is None:
				return

			entry = CommandQueueEntry(
				CommandQueueEntry.PRIORITY_HIGH if high_priority else CommandQueueEntry.PRIORITY_NORMAL,
				command,
				line_number=with_line_number,
				command_type=command_type
			)

		try:
			self._send_queue.put(entry)
		except TypeAlreadyInQueue:
			pass

	# Called only from worker thread, not thread safe
	def _send_next(self):
		try:
			command = self._current_file.getNext()
		except ValueError:
			# TODO _current_file might already be closed since the print ended asynchronously between our callee and here, causing a ValueError => find some nicer way to handle this
			return None

		if command is None:
			command = SpecialCommandQueueEntry(SpecialCommandQueueEntry.TYPE_JOBDONE)

		self._send(command, with_progress=dict(completion=self._getPrintCompletion(), filepos=self._getPrintFilepos()))

	def _send_temperature_query(self, with_high_priority=False, with_type=False):
		self._send(RepRapProtocol.COMMAND_GET_TEMP(), high_priority=with_high_priority, command_type=RepRapProtocol.COMMAND_TYPE_TEMPERATURE if with_type else None)
		self._lastTemperatureUpdate = time.time()

	def _send_sd_progress_query(self, with_high_priority=False, with_type=False):
		self._send(RepRapProtocol.COMMAND_SD_STATUS(), high_priority=with_high_priority, command_type=RepRapProtocol.COMMAND_TYPE_SD_PROGRESS if with_type else None)
		self._lastSdProgressUpdate = time.time()

	def _handle_errors(self, line):
		if RepRapProtocol.MESSAGE_ERROR(line):
			if RepRapProtocol.MESSAGE_ERROR_MULTILINE(line):
				error = self._transport.receive()
			else:
				error = RepRapProtocol.TRANSFORM_ERROR(line)

			# skip the communication errors as those get corrected via resend requests
			if RepRapProtocol.MESSAGE_ERROR_COMMUNICATION(error):
				self._last_comm_error = error
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

		import copy
		result = copy.deepcopy(self._current_temperature)

		# extruder temperatures
		if not "T0" in parsedTemps.keys() and not "T1" in parsedTemps.keys() and "T" in parsedTemps.keys():
			# no T1 so only single reporting, "T" is our one and only extruder temperature
			toolNum, actual, target = parsedTemps["T"]

			if target is not None:
				result["tool0"] = (actual, target)
			elif "tool0" in result and result["tool0"] is not None and isinstance(result["tool0"], tuple):
				(oldActual, oldTarget) = result["tool0"]
				result["tool0"] = (actual, oldTarget)
			else:
				result["tool0"] = (actual, None)

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
				key = "tool%d" % toolNum
				if target is not None:
					result[key] = (actual, target)
				elif key in result and result[key] is not None and isinstance(result[key], tuple):
					(oldActual, oldTarget) = result[key]
					result[key] = (actual, oldTarget)
				else:
					result[key] = (actual, None)

		# bed temperature
		if "B" in parsedTemps.keys():
			toolNum, actual, target = parsedTemps["B"]
			if target is not None:
				result["bed"] = (actual, target)
			elif "bed" in result and result["bed"] is not None and isinstance(result["bed"], tuple):
				(oldActual, oldTarget) = result["bed"]
				result["bed"] = (actual, oldTarget)
			else:
				result["bed"] = (actual, None)

		self._updateTemperature(result)

	def _handle_resend_request(self, message):
		line_to_resend = None
		try:
			line_to_resend = int(message.replace("N:", " ").replace("N", " ").replace(":", " ").split()[-1])
		except:
			if "rs" in message:
				line_to_resend = int(message.split()[1])

		last_comm_error = self._last_comm_error
		self._last_comm_error = None

		if line_to_resend is not None:
			with self._nack_lock:
				if len(self._nack_lines) > 0:
					nack_entry = self._nack_lines[0]

					if last_comm_error is not None and \
							RepRapProtocol.MESSAGE_ERROR_COMMUNICATION_LINENUMBER(last_comm_error) \
							and line_to_resend == self._last_resend_number \
							and self._current_resend_count < self._nacks_before_resend:
						# this resend is a complaint about the wrong line_number, we already resent the requested
						# one and didn't see more resend requests for those yet than we had additional lines in the nack
						# buffer back then, so this is probably caused by leftovers in the printer's receive buffer
						# (that got sent after the firmware cleared the receive buffer but before we'd fully processed
						# the old resend request), we'll therefore just increment our counter and ignore this
						self._current_resend_count += 1
						return
					else:
						# this is either a resend request for a new line_number, or a resend request not caused by a
						# line number mismatch, or we now saw more consecutive requests for that line number than there
						# were additional lines in the nack buffer when we saw the first one, so we'll have to handle it
						self._last_resend_number = line_to_resend
						self._current_resend_count = 0
						self._nacks_before_resend = len(self._nack_lines) - 1

					if nack_entry.line_number is not None and nack_entry.line_number == line_to_resend:
						try:
							while True:
								entry = self._nack_lines.popleft()
								entry.priority = CommandQueueEntry.PRIORITY_RESEND
								try:
									self._send_queue.put(entry)
								except TypeAlreadyInQueue:
									pass
						except IndexError:
							# that's ok, the nack lines are just empty
							pass

						return

					elif line_to_resend < nack_entry.line_number:
						# we'll ignore that resend request since that line was already acknowledged in the past
						return

				# if we've reached this point, we could not resend the requested line
				error = "Printer requested line %d but no sufficient history is available, can't resend" % line_to_resend
				self._logger.warn(error)
				if self.is_printing():
					# abort the print, there's nothing we can do to rescue it now
					self.onError(error)

				# reset line number local and remote
				self._current_line = 1
				self._nack_lines.clear()
				self._send(RepRapProtocol.COMMAND_SET_LINE(0))

	##~~ handle queue filling in this thread when printing or streaming

	def _fill_send_queue(self):
		while self._fill_queue_processing:
			with self._fill_queue_mutex:
				self._fill_queue_state_signal.wait(0.1)

				if not ((self._state == State.PRINTING and not isinstance(self._current_file, PrintingSdFileInformation))
				        or self._state == State.STREAMING):
					continue

				if self._fill_queue_semaphore.acquire(0.5):
					self._send_next()


	##~~ the actual send queue handling starts here

	def _handle_send_queue(self):
		while self._send_queue_processing:
			if self._send_queue.qsize() == 0:
				# queue is empty, wait a bit before checking again
				if ((self._state == State.PRINTING and not isinstance(self._current_file, PrintingSdFileInformation))
				    or self._state == State.STREAMING):
					self._logger.warn("Buffer under run while printing!")
				time.sleep(0.1)
				continue

			if self._blocking_command_active:
				# blocking command is active, no use to send anything to the printer right now
				time.sleep(0.1)
				continue

			try:
				with self._nack_lock:
					sent = self._send_from_queue()
			except SendTimeout:
				# we just got a send timeout, so we'll just try again on the next loop iteration
				continue

			if not sent or self._rx_cache_size <= 0:
				# decrease the clear_for_send counter
				self._clear_for_send.clear()
				self._clear_for_send.wait()

	def _send_from_queue(self):
		entry = self._send_queue.peek()
		if entry is None:
			if ((self._state == State.PRINTING and not isinstance(self._current_file, PrintingSdFileInformation))
			    or self._state == State.STREAMING):
				self._logger.warn("Buffer under run while printing!")
			return False

		if not self._startSeen:
			return False

		if isinstance(entry, SpecialCommandQueueEntry):
			self._nack_lines.append(entry)
		else:
			if entry.prepared is None:
				prepared, line_number = self._prepare_for_sending(entry.command, with_line_number=entry.line_number)

				entry.prepared = prepared
				entry.line_number = line_number

			if entry.prepared is not None:
				# only actually send the command if it wasn't filtered out by preprocessing

				current_size = sum(self._nack_lines)
				new_size = current_size + entry.size
				if new_size > self._rx_cache_size > 0 and not (current_size == 0):
					# Do not send if the left over space in the buffer is too small for this line. Exception: the buffer is empty
					# and the line still doesn't fit
					return False

				# send the command - we might get a SendTimeout here which is supposed to bubble up since it's caught in the
				# actual send loop
				self._transport.send(entry.prepared)

				# add the queue entry into the deque of commands not yet acknowledged
				self._nack_lines.append(entry)
			else:
				self._logger.debug("Dropping command which was disabled through preprocessing: %s" % entry.command)

		# remove from send queue
		self._fill_queue_semaphore.release()
		try:
			self._send_queue.get(block=False)
		except Queue.Empty:
			# that's ok, we might just have asynchronously cancelled the whole print job
			# TODO but we only remove the commands from the print job, so this will eat a line!!!
			pass

		return True

	##~~ preprocessing of command in the three phases "queued", "sent" and "acknowledged"

	def _process_command(self, command, phase, with_line_number=None):
		if command is None:
			return None, None, None

		if not phase in ("queued", "sent", "acknowledged"):
			return None

		if phase in self._preprocessors and command.command in self._preprocessors[phase]:
			command, with_line_number = self._preprocessors[phase][command.command](command, with_line_number)

		return command, with_line_number

	def _prepare_for_sending(self, command, with_line_number=None):
		command, with_line_number = self._process_command(command, "sent", with_line_number=with_line_number)
		if command is None:
			return None, None

		if self._force_checksum:
			if with_line_number is not None:
				line_number = with_line_number
			else:
				line_number = self._current_line
			command_to_send = "N%d %s" % (line_number, str(command))

			checksum = reduce(lambda x, y: x ^ y, map(ord, command_to_send))

			if with_line_number is None:
				self._current_line += 1

			return "%s*%d" % (command_to_send, checksum), line_number
		else:
			return str(command), None

	##~~ specific command actions

	def _gcode_T_acknowledged(self, command, with_line_number):
		self._current_extruder = command.tool
		return command, with_line_number

	def _gcode_G0_acknowledged(self, command, with_line_number):
		if command.z is not None:
			z = command.z
			self._reportZChange(z)
		return command, with_line_number
	_gcode_G1_acknowledged = _gcode_G0_acknowledged

	def _gcode_M0_queued(self, command, with_line_number):
		self.pause_print()
		# Don't send the M0 or M1 to the machine, as M0 and M1 are handled as an LCD menu pause.
		return None, with_line_number
	_gcode_M1_queued = _gcode_M0_queued

	def _gcode_M104_sent(self, command, with_line_number):
		key = "tool%d" % command.t if command.t is not None else self._current_extruder
		self._handle_temperature_code(command, key)
		return command, with_line_number

	def _gcode_M109_sent(self, command, with_line_number):
		self._blocking_command_active = True
		self._logger.info("Waiting for a blocking command to finish")
		return self._gcode_M104_sent(command, with_line_number)

	def _gcode_M140_sent(self, command, with_line_number):
		key = "bed"
		self._handle_temperature_code(command, key)
		return command, with_line_number

	def _gcode_M190_sent(self, command, with_line_number):
		self._blocking_command_active = True
		self._logger.info("Waiting for a blocking command to finish")
		return self._gcode_M140_sent(command, with_line_number)

	def _gcode_M109_acknowledged(self, command, with_line_number):
		self._blocking_command_active = False
		self._logger.info("Blocking command finished")
		return command, with_line_number
	_gcode_M190_acknowledged = _gcode_M109_acknowledged

	def _handle_temperature_code(self, command, key):
		if command.s is not None:
			target = command.s
			if key in self._current_temperature and self._current_temperature[key] is not None and isinstance(self._current_temperature[key], tuple):
				actual, old_target = self._current_temperature[key]
				self._current_temperature[key] = (actual, target)
			else:
				self._current_temperature[key] = (None, target)

	def _gcode_M110_sent(self, command, with_line_number):
		if command.n is not None:
			new_line_number = command.n
		else:
			new_line_number = 0

		self._current_line = new_line_number + 1

		# send M110 command with new line number
		return command, new_line_number

	def _gcode_M112_queued(self, command, with_line_number): # It's an emergency what todo? Canceling the print should be the minimum
		self.cancel_print()
		return command, with_line_number

