# coding=utf-8
from __future__ import absolute_import, division, print_function
__author__ = "Gina Häußge <osd@foosel.net> based on work by David Braam"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"


import os
import glob
import time
import re
import threading

try:
	import queue
except ImportError:
	import Queue as queue
from past.builtins import basestring

import logging
import serial

import octoprint.plugin

from collections import deque

from octoprint.util.avr_isp import stk500v2
from octoprint.util.avr_isp import ispBase

from octoprint.settings import settings, default_settings
from octoprint.events import eventManager, Events
from octoprint.filemanager import valid_file_type
from octoprint.filemanager.destinations import FileDestinations
from octoprint.util import get_exception_string, sanitize_ascii, filter_non_ascii, CountedEvent, RepeatedTimer, \
	to_unicode, bom_aware_open, TypedQueue, PrependableQueue, TypeAlreadyInQueue, chunks

try:
	import _winreg
except:
	pass

_logger = logging.getLogger(__name__)

# a bunch of regexes we'll need for the communication parsing...

regex_float_pattern = "[-+]?[0-9]*\.?[0-9]+"
regex_positive_float_pattern = "[+]?[0-9]*\.?[0-9]+"
regex_int_pattern = "\d+"

regex_command = re.compile("^\s*((?P<codeGM>[GM]\d+)(\\.(?P<subcode>\d+))?|(?P<codeT>T)\d+|(?P<codeF>F)\d+)")
"""Regex for a GCODE command."""

regex_float = re.compile(regex_float_pattern)
"""Regex for a float value."""

regexes_parameters = dict(
	floatE=re.compile("(^|[^A-Za-z])[Ee](?P<value>%s)" % regex_float_pattern),
	floatF=re.compile("(^|[^A-Za-z])[Ff](?P<value>%s)" % regex_float_pattern),
	floatP=re.compile("(^|[^A-Za-z])[Pp](?P<value>%s)" % regex_float_pattern),
	floatR=re.compile("(^|[^A-Za-z])[Rr](?P<value>%s)" % regex_float_pattern),
	floatS=re.compile("(^|[^A-Za-z])[Ss](?P<value>%s)" % regex_float_pattern),
	floatX=re.compile("(^|[^A-Za-z])[Xx](?P<value>%s)" % regex_float_pattern),
	floatY=re.compile("(^|[^A-Za-z])[Yy](?P<value>%s)" % regex_float_pattern),
	floatZ=re.compile("(^|[^A-Za-z])[Zz](?P<value>%s)" % regex_float_pattern),
	intN=re.compile("(^|[^A-Za-z])[Nn](?P<value>%s)" % regex_int_pattern),
	intS=re.compile("(^|[^A-Za-z])[Ss](?P<value>%s)" % regex_int_pattern),
	intT=re.compile("(^|[^A-Za-z])[Tt](?P<value>%s)" % regex_int_pattern)
)
"""Regexes for parsing various GCODE command parameters."""

regex_minMaxError = re.compile("Error:[0-9]\n")
"""Regex matching first line of min/max errors from the firmware."""

regex_sdPrintingByte = re.compile("(?P<current>[0-9]*)/(?P<total>[0-9]*)")
"""Regex matching SD printing status reports.

Groups will be as follows:

  * ``current``: current byte position in file being printed
  * ``total``: total size of file being printed
"""

regex_sdFileOpened = re.compile("File opened:\s*(?P<name>.*?)\s+Size:\s*(?P<size>%s)" % regex_int_pattern)
"""Regex matching "File opened" messages from the firmware.

Groups will be as follows:

  * ``name``: name of the file reported as having been opened (str)
  * ``size``: size of the file in bytes (int)
"""

regex_temp = re.compile("(?P<tool>B|T(?P<toolnum>\d*)):\s*(?P<actual>%s)(\s*\/?\s*(?P<target>%s))?" % (regex_float_pattern, regex_float_pattern))
"""Regex matching temperature entries in line.

Groups will be as follows:

  * ``tool``: whole tool designator, incl. optional ``toolnum`` (str)
  * ``toolnum``: tool number, if provided (int)
  * ``actual``: actual temperature (float)
  * ``target``: target temperature, if provided (float)
"""

regex_repetierTempExtr = re.compile("TargetExtr(?P<toolnum>\d+):(?P<target>%s)" % regex_float_pattern)
"""Regex for matching target temp reporting from Repetier.

Groups will be as follows:

  * ``toolnum``: number of the extruder to which the target temperature
    report belongs (int)
  * ``target``: new target temperature (float)
"""

regex_repetierTempBed = re.compile("TargetBed:(?P<target>%s)" % regex_float_pattern)
"""Regex for matching target temp reporting from Repetier for beds.

Groups will be as follows:

  * ``target``: new target temperature (float)
"""

regex_position = re.compile("X:(?P<x>{float})\s*Y:(?P<y>{float})\s*Z:(?P<z>{float})\s*E:(?P<e>{float})".format(float=regex_float_pattern))
"""Regex for matching position reporting.

Groups will be as follows:

  * ``x``: X coordinate
  * ``y``: Y coordinate
  * ``z``: Z coordinate
  * ``e``: E coordinate
"""

regex_firmware_splitter = re.compile("\s*([A-Z0-9_]+):")
"""Regex to use for splitting M115 responses."""

regex_resend_linenumber = re.compile("(N|N:)?(?P<n>%s)" % regex_int_pattern)
"""Regex to use for request line numbers in resend requests"""

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
	# sorted by likelihood
	candidates = [115200, 250000, 230400, 57600, 38400, 19200, 9600]

	# additional baudrates prepended, sorted descending
	additionalBaudrates = settings().get(["serial", "additionalBaudrates"])
	for additional in sorted(additionalBaudrates, reverse=True):
		try:
			candidates.insert(0, int(additional))
		except:
			_logger.warn("{} is not a valid additional baudrate, ignoring it".format(additional))

	# last used baudrate = first to try, move to start
	prev = settings().getInt(["serial", "baudrate"])
	if prev in candidates:
		candidates.remove(prev)
		candidates.insert(0, prev)

	return candidates

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

class PositionRecord(object):
	def __init__(self, *args, **kwargs):
		self.x = kwargs.get("x")
		self.y = kwargs.get("y")
		self.z = kwargs.get("z")
		self.e = kwargs.get("e")
		self.f = kwargs.get("f")
		self.t = kwargs.get("t")

	def copy_from(self, other):
		self.x = other.x
		self.y = other.y
		self.z = other.z
		self.e = other.e
		self.f = other.f
		self.t = other.t

	def as_dict(self):
		return dict(x=self.x,
		            y=self.y,
		            z=self.z,
		            e=self.e,
		            t=self.t,
		            f=self.f)

class TemperatureRecord(object):
	def __init__(self):
		self._tools = dict()
		self._bed = (None, None)

	def copy_from(self, other):
		self._tools = other.tools
		self._bed = other.bed

	def set_tool(self, tool, actual=None, target=None):
		current = self._tools.get(tool, (None, None))
		self._tools[tool] = self._to_new_tuple(current, actual, target)

	def set_bed(self, actual=None, target=None):
		current = self._bed
		self._bed = self._to_new_tuple(current, actual, target)

	@property
	def tools(self):
		return dict(self._tools)

	@property
	def bed(self):
		return self._bed

	def as_script_dict(self):
		result = dict()

		tools = self.tools
		for tool, data in tools.items():
			result[tool] = dict(actual=data[0],
			                    target=data[1])

		bed = self.bed
		result["b"] = dict(actual=bed[0],
		                   target=bed[1])

		return result

	@classmethod
	def _to_new_tuple(cls, current, actual, target):
		if current is None or not isinstance(current, tuple) or len(current) != 2:
			current = (None, None)

		if actual is None and target is None:
			return current

		old_actual, old_target = current

		if actual is None:
			return old_actual, target
		elif target is None:
			return actual, old_target
		else:
			return actual, target

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

	CAPABILITY_AUTOREPORT_TEMP = "AUTOREPORT_TEMP"

	def __init__(self, port = None, baudrate=None, callbackObject=None, printerProfileManager=None):
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
		self._printerProfileManager = printerProfileManager
		self._state = self.STATE_NONE
		self._serial = None
		self._baudrateDetectList = baudrateList()
		self._baudrateDetectRetry = 0
		self._temperatureTargetSetThreshold = 25
		self._tempOffsets = dict()
		self._command_queue = TypedQueue()
		self._currentZ = None
		self._currentF = None
		self._heatupWaitStartTime = None
		self._heatupWaitTimeLost = 0.0
		self._pauseWaitStartTime = None
		self._pauseWaitTimeLost = 0.0
		self._currentTool = 0
		self._formerTool = None

		self._long_running_command = False
		self._heating = False
		self._dwelling_until = False
		self._connection_closing = False

		self._timeout = None
		self._timeout_intervals = dict()
		for key, value in settings().get(["serial", "timeout"], merged=True, asdict=True).items():
			try:
				self._timeout_intervals[key] = float(value)
			except:
				pass

		self._consecutive_timeouts = 0
		self._consecutive_timeout_maximums = dict()
		for key, value in settings().get(["serial", "maxCommunicationTimeouts"], merged=True, asdict=True).items():
			try:
				self._consecutive_timeout_maximums[key] = int(value)
			except:
				pass

		self._max_write_passes = settings().getInt(["serial", "maxWritePasses"])

		self._hello_command = settings().get(["serial", "helloCommand"])
		self._trigger_ok_for_m29 = settings().getBoolean(["serial", "triggerOkForM29"])

		self._hello_command = settings().get(["serial", "helloCommand"])

		self._alwaysSendChecksum = settings().getBoolean(["feature", "alwaysSendChecksum"])
		self._neverSendChecksum = settings().getBoolean(["feature", "neverSendChecksum"])
		self._sendChecksumWithUnknownCommands = settings().getBoolean(["feature", "sendChecksumWithUnknownCommands"])
		self._unknownCommandsNeedAck = settings().getBoolean(["feature", "unknownCommandsNeedAck"])
		self._sdAlwaysAvailable = settings().getBoolean(["feature", "sdAlwaysAvailable"])
		self._sdRelativePath = settings().getBoolean(["feature", "sdRelativePath"])
		self._blockWhileDwelling = settings().getBoolean(["feature", "blockWhileDwelling"])
		self._currentLine = 1
		self._line_mutex = threading.RLock()
		self._resendDelta = None
		self._lastLines = deque([], 50)
		self._lastCommError = None
		self._lastResendNumber = None
		self._currentResendCount = 0
		self._resendSwallowRepetitions = settings().getBoolean(["feature", "ignoreIdenticalResends"])
		self._resendSwallowRepetitionsCounter = 0

		self._firmware_detection = settings().getBoolean(["feature", "firmwareDetection"])
		self._firmware_info_received = not self._firmware_detection
		self._firmware_info = dict()
		self._firmware_capabilities = dict()

		self._temperature_autoreporting = False

		self._supportResendsWithoutOk = settings().getBoolean(["serial", "supportResendsWithoutOk"])

		self._resendActive = False

		self._terminal_log = deque([], 20)

		self._disconnect_on_errors = settings().getBoolean(["serial", "disconnectOnErrors"])
		self._ignore_errors = settings().getBoolean(["serial", "ignoreErrorsFromFirmware"])

		self._log_resends = settings().getBoolean(["serial", "logResends"])

		# don't log more resends than 5 / 60s
		self._log_resends_rate_start = None
		self._log_resends_rate_count = 0
		self._log_resends_max = 5
		self._log_resends_rate_frame = 60

		self._long_running_commands = settings().get(["serial", "longRunningCommands"])
		self._checksum_requiring_commands = settings().get(["serial", "checksumRequiringCommands"])

		self._clear_to_send = CountedEvent(max=10, name="comm.clear_to_send")
		self._send_queue = SendQueue()
		self._temperature_timer = None
		self._sd_status_timer = None

		# hooks
		self._pluginManager = octoprint.plugin.plugin_manager()

		self._gcode_hooks = dict(
			queuing=self._pluginManager.get_hooks("octoprint.comm.protocol.gcode.queuing"),
			queued=self._pluginManager.get_hooks("octoprint.comm.protocol.gcode.queued"),
			sending=self._pluginManager.get_hooks("octoprint.comm.protocol.gcode.sending"),
			sent=self._pluginManager.get_hooks("octoprint.comm.protocol.gcode.sent")
		)
		self._received_message_hooks = self._pluginManager.get_hooks("octoprint.comm.protocol.gcode.received")

		self._printer_action_hooks = self._pluginManager.get_hooks("octoprint.comm.protocol.action")
		self._gcodescript_hooks = self._pluginManager.get_hooks("octoprint.comm.protocol.scripts")
		self._serial_factory_hooks = self._pluginManager.get_hooks("octoprint.comm.transport.serial.factory")

		self._temperature_hooks = self._pluginManager.get_hooks("octoprint.comm.protocol.temperatures.received")

		# SD status data
		self._sdEnabled = settings().getBoolean(["feature", "sdSupport"])
		self._sdAvailable = False
		self._sdFileList = False
		self._sdFiles = []
		self._sdFileToSelect = None
		self._ignore_select = False
		self._manualStreaming = False

		self.last_temperature = TemperatureRecord()
		self.pause_temperature = TemperatureRecord()
		self.cancel_temperature = TemperatureRecord()

		self.last_position = PositionRecord()
		self.pause_position = PositionRecord()
		self.cancel_position = PositionRecord()

		self._record_pause_data = False
		self._record_cancel_data = False

		self._log_position_on_pause = settings().getBoolean(["serial", "logPositionOnPause"])
		self._log_position_on_cancel = settings().getBoolean(["serial", "logPositionOnCancel"])

		# print job
		self._currentFile = None

		# multithreading locks
		self._jobLock = threading.RLock()
		self._sendingLock = threading.RLock()

		# monitoring thread
		self._monitoring_active = True
		self.monitoring_thread = threading.Thread(target=self._monitor, name="comm._monitor")
		self.monitoring_thread.daemon = True
		self.monitoring_thread.start()

		# sending thread
		self._send_queue_active = True
		self.sending_thread = threading.Thread(target=self._send_loop, name="comm.sending_thread")
		self.sending_thread.daemon = True
		self.sending_thread.start()

	def __del__(self):
		self.close()

	@property
	def _active(self):
		return self._monitoring_active and self._send_queue_active

	##~~ internal state management

	def _changeState(self, newState):
		if self._state == newState:
			return

		if newState == self.STATE_CLOSED or newState == self.STATE_CLOSED_WITH_ERROR:
			if settings().getBoolean(["feature", "sdSupport"]):
				self._sdFileList = False
				self._sdFiles = []
				self._callback.on_comm_sd_files([])

			if self._currentFile is not None:
				if self.isBusy():
					self._recordFilePosition()
				self._currentFile.close()

		oldState = self.getStateString()
		self._state = newState
		self._log('Changing monitoring state from \'%s\' to \'%s\'' % (oldState, self.getStateString()))
		self._callback.on_comm_state_change(newState)

	def _dual_log(self, message, level=logging.ERROR):
		self._logger.log(level, message)
		self._log(message)

	def _log(self, message):
		self._terminal_log.append(message)
		self._callback.on_comm_log(message)
		self._serialLogger.debug(message)

	def _to_logfile_with_terminal(self, message=None, level=logging.INFO):
		log = "Last lines in terminal:\n" + "\n".join(map(lambda x: "| " + x, list(self._terminal_log)))
		if message is not None:
			log = message + "\n| " + log
		self._logger.log(level, log)

	def _addToLastLines(self, cmd):
		self._lastLines.append(cmd)

	##~~ getters

	def getState(self):
		return self._state

	def getStateId(self, state=None):
		if state is None:
			state = self._state

		possible_states = filter(lambda x: x.startswith("STATE_"), self.__class__.__dict__.keys())
		for possible_state in possible_states:
			if getattr(self, possible_state) == state:
				return possible_state[len("STATE_"):]

		return "UNKNOWN"

	def getStateString(self, state=None):
		if state is None:
			state = self._state

		if state == self.STATE_NONE:
			return "Offline"
		if state == self.STATE_OPEN_SERIAL:
			return "Opening serial port"
		if state == self.STATE_DETECT_SERIAL:
			return "Detecting serial port"
		if state == self.STATE_DETECT_BAUDRATE:
			return "Detecting baudrate"
		if state == self.STATE_CONNECTING:
			return "Connecting"
		if state == self.STATE_OPERATIONAL:
			return "Operational"
		if state == self.STATE_PRINTING:
			if self.isSdFileSelected():
				return "Printing from SD"
			elif self.isStreaming():
				return "Sending file to SD"
			else:
				return "Printing"
		if state == self.STATE_PAUSED:
			return "Paused"
		if state == self.STATE_CLOSED:
			return "Offline"
		if state == self.STATE_ERROR:
			return "Error: %s" % (self.getErrorString())
		if state == self.STATE_CLOSED_WITH_ERROR:
			return "Offline: %s" % (self.getErrorString())
		if state == self.STATE_TRANSFERING_FILE:
			return "Transferring file to SD"
		return "Unknown State (%d)" % (self._state)

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
		return self.last_temperature.tools

	def getBedTemp(self):
		return self.last_temperature.bed

	def getOffsets(self):
		return dict(self._tempOffsets)

	def getCurrentTool(self):
		return self._currentTool

	def getConnection(self):
		return self._port, self._baudrate

	def getTransport(self):
		return self._serial

	##~~ external interface

	def close(self, is_error=False, wait=True, timeout=10.0, *args, **kwargs):
		"""
		Closes the connection to the printer.

		If ``is_error`` is False, will attempt to send the ``beforePrinterDisconnected``
		gcode script. If ``is_error`` is False and ``wait`` is True, will wait
		until all messages in the send queue (including the ``beforePrinterDisconnected``
		gcode script) have been sent to the printer.

		Arguments:
		   is_error (bool): Whether the closing takes place due to an error (True)
		      or not (False, default)
		   wait (bool): Whether to wait for all messages in the send
		      queue to be processed before closing (True, default) or not (False)
		"""

		# legacy parameters
		is_error = kwargs.get("isError", is_error)

		if self._connection_closing:
			return
		self._connection_closing = True

		if self._temperature_timer is not None:
			try:
				self._temperature_timer.cancel()
			except:
				pass

		if self._sd_status_timer is not None:
			try:
				self._sd_status_timer.cancel()
			except:
				pass

		def deactivate_monitoring_and_send_queue():
			self._monitoring_active = False
			self._send_queue_active = False

		printing = self.isPrinting() or self.isPaused()
		if self._serial is not None:
			if not is_error:
				self.sendGcodeScript("beforePrinterDisconnected")
				if wait:
					if timeout is not None:
						stop = time.time() + timeout
						while (self._command_queue.unfinished_tasks or self._send_queue.unfinished_tasks) and time.time() < stop:
							time.sleep(0.1)
					else:
						self._command_queue.join()
						self._send_queue.join()

			deactivate_monitoring_and_send_queue()

			try:
				self._serial.close()
			except:
				self._logger.exception("Error while trying to close serial port")
				is_error = True

			if is_error:
				self._changeState(self.STATE_CLOSED_WITH_ERROR)
			else:
				self._changeState(self.STATE_CLOSED)
		else:
			deactivate_monitoring_and_send_queue()
		self._serial = None

		if settings().getBoolean(["feature", "sdSupport"]):
			self._sdFileList = []

		if printing:
			self._callback.on_comm_print_job_failed()

	def setTemperatureOffset(self, offsets):
		self._tempOffsets.update(offsets)

	def fakeOk(self):
		self._handle_ok()

	def sendCommand(self, cmd, cmd_type=None, processed=False, force=False, on_sent=None):
		cmd = to_unicode(cmd, errors="replace")
		if not processed:
			cmd = process_gcode_line(cmd)
			if not cmd:
				return False

		if self.isPrinting() and not self.isSdFileSelected():
			try:
				self._command_queue.put((cmd, cmd_type, on_sent), item_type=cmd_type)
				return True
			except TypeAlreadyInQueue as e:
				self._logger.debug("Type already in command queue: " + e.type)
				return False
		elif self.isOperational() or force:
			return self._sendCommand(cmd, cmd_type=cmd_type, on_sent=on_sent)

	def _getGcodeScript(self, scriptName, replacements=None):
		context = dict()
		if replacements is not None and isinstance(replacements, dict):
			context.update(replacements)

		context.update(dict(
			printer_profile=self._printerProfileManager.get_current_or_default(),
			last_position=self.last_position,
			last_temperature=self.last_temperature.as_script_dict()
		))

		if scriptName == "afterPrintPaused" or scriptName == "beforePrintResumed":
			context.update(dict(pause_position=self.pause_position,
			                    pause_temperature=self.pause_temperature.as_script_dict()))
		elif scriptName == "afterPrintCancelled":
			context.update(dict(cancel_position=self.cancel_position,
			                    cancel_temperature=self.cancel_temperature.as_script_dict()))

		template = settings().loadScript("gcode", scriptName, context=context)
		if template is None:
			scriptLines = []
		else:
			scriptLines = template.split("\n")

		for hook in self._gcodescript_hooks:
			try:
				retval = self._gcodescript_hooks[hook](self, "gcode", scriptName)
			except:
				self._logger.exception("Error while processing gcodescript hook %s" % hook)
			else:
				if retval is None:
					continue
				if not isinstance(retval, (list, tuple)) or not len(retval) == 2:
					continue

				def to_list(data):
					if isinstance(data, str):
						data = map(str.strip, data.split("\n"))
					elif isinstance(data, unicode):
						data = map(unicode.strip, data.split("\n"))

					if isinstance(data, (list, tuple)):
						return list(data)
					else:
						return None

				prefix, suffix = map(to_list, retval)
				if prefix:
					scriptLines = list(prefix) + scriptLines
				if suffix:
					scriptLines += list(suffix)

		return filter(lambda x: x is not None and x.strip() != "",
		              map(lambda x: process_gcode_line(x, offsets=self._tempOffsets, current_tool=self._currentTool),
		                  scriptLines))


	def sendGcodeScript(self, scriptName, replacements=None):
		scriptLines = self._getGcodeScript(scriptName, replacements=replacements)
		for line in scriptLines:
			self.sendCommand(line)
		return "\n".join(scriptLines)

	def startPrint(self, pos=None):
		if not self.isOperational() or self.isPrinting():
			return

		if self._currentFile is None:
			raise ValueError("No file selected for printing")

		self._heatupWaitStartTime = None
		self._heatupWaitTimeLost = 0.0
		self._pauseWaitStartTime = 0
		self._pauseWaitTimeLost = 0.0

		try:
			with self._jobLock:
				self._currentFile.start()

				self._changeState(self.STATE_PRINTING)

				self.resetLineNumbers()

				self._callback.on_comm_print_job_started()

				if self.isSdFileSelected():
					#self.sendCommand("M26 S0") # setting the sd pos apparently sometimes doesn't work, so we re-select
					                            # the file instead

					# make sure to ignore the "file selected" later on, otherwise we'll reset our progress data
					self._ignore_select = True
					self.sendCommand("M23 {filename}".format(filename=self._currentFile.getFilename()))
					if pos is not None and isinstance(pos, int) and pos > 0:
						self._currentFile.setFilepos(pos)
						self.sendCommand("M26 S{}".format(pos))
					else:
						self._currentFile.setFilepos(0)

					self.sendCommand("M24")

					self._sd_status_timer = RepeatedTimer(self._timeout_intervals.get("sdStatus", 1.0), self._poll_sd_status, run_first=True)
					self._sd_status_timer.start()
				else:
					if pos is not None and isinstance(pos, int) and pos > 0:
						self._currentFile.seek(pos)

					line = self._getNext()
					if line is not None:
						self.sendCommand(line)

				# now make sure we actually do something, up until now we only filled up the queue
				self._sendFromQueue()
		except:
			self._logger.exception("Error while trying to start printing")
			self._errorValue = get_exception_string()
			self._changeState(self.STATE_ERROR)
			eventManager().fire(Events.ERROR, {"error": self.getErrorString()})

	def startFileTransfer(self, filename, localFilename, remoteFilename, special=False):
		if not self.isOperational() or self.isBusy():
			self._logger.info("Printer is not operational or busy")
			return

		with self._jobLock:
			self.resetLineNumbers()

			if special:
				self._currentFile = SpecialStreamingGcodeFileInformation(filename, localFilename, remoteFilename)
			else:
				self._currentFile = StreamingGcodeFileInformation(filename, localFilename, remoteFilename)
			self._currentFile.start()

			self.sendCommand("M28 %s" % remoteFilename)
			eventManager().fire(Events.TRANSFER_STARTED, {"local": localFilename, "remote": remoteFilename})
			self._callback.on_comm_file_transfer_started(remoteFilename, self._currentFile.getFilesize())

	def cancelFileTransfer(self):
		if not self.isOperational() or not self.isStreaming():
			self._logger.info("Printer is not operational or not streaming")
			return

		self._finishFileTransfer(failed=True)

	def _finishFileTransfer(self, failed=False):
		with self._jobLock:
			remote = self._currentFile.getRemoteFilename()

			self._sendCommand("M29")
			if failed:
				self.deleteSdFile(remote)

			payload = {
				"local": self._currentFile.getLocalFilename(),
				"remote": remote,
				"time": self.getPrintTime()
			}

			self._currentFile = None
			self._changeState(self.STATE_OPERATIONAL)

			if failed:
				self._callback.on_comm_file_transfer_failed(remote)
				eventManager().fire(Events.TRANSFER_FAILED, payload)
			else:
				self._callback.on_comm_file_transfer_done(remote)
				eventManager().fire(Events.TRANSFER_DONE, payload)

			self.refreshSdFiles()

	def selectFile(self, filename, sd):
		if self.isBusy():
			return

		if sd:
			if not self.isOperational():
				# printer is not connected, can't use SD
				return

			if filename.startswith("/") and self._sdRelativePath:
				filename = filename[1:]

			self._sdFileToSelect = filename
			self.sendCommand("M23 %s" % filename)
		else:
			self._currentFile = PrintingGcodeFileInformation(filename, offsets_callback=self.getOffsets, current_tool_callback=self.getCurrentTool)
			self._callback.on_comm_file_selected(filename, self._currentFile.getFilesize(), False)

	def unselectFile(self):
		if self.isBusy():
			return

		self._currentFile = None
		self._callback.on_comm_file_selected(None, None, False)

	def _cancel_preparation_done(self):
		self._recordFilePosition()
		self._callback.on_comm_print_job_cancelled()

	def cancelPrint(self, firmware_error=None, disable_log_position=False):
		if not self.isOperational():
			return

		if not self.isBusy() or self._currentFile is None:
			# we aren't even printing, nothing to cancel...
			return

		if self.isStreaming():
			# we are streaming, we handle cancelling that differently...
			self.cancelFileTransfer()
			return

		def _on_M400_sent():
			# we don't call on_print_job_cancelled on our callback here
			# because we do this only after our M114 has been answered
			# by the firmware
			self._record_cancel_data = True
			self.sendCommand("M114")

		with self._jobLock:
			self._changeState(self.STATE_OPERATIONAL)

			if self.isSdFileSelected():
				self.sendCommand("M25")    # pause print
				self.sendCommand("M27")    # get current byte position in file
				self.sendCommand("M26 S0") # reset position in file to byte 0
				if self._sd_status_timer is not None:
					try:
						self._sd_status_timer.cancel()
					except:
						pass

			if self._log_position_on_cancel and not disable_log_position:
				self.sendCommand("M400", on_sent=_on_M400_sent)
			else:
				self._cancel_preparation_done()

	def _pause_preparation_done(self):
		self._callback.on_comm_print_job_paused()

	def setPause(self, pause):
		if self.isStreaming():
			return

		if not self._currentFile:
			return

		with self._jobLock:
			if not pause and self.isPaused():
				if self._pauseWaitStartTime:
					self._pauseWaitTimeLost = self._pauseWaitTimeLost + (time.time() - self._pauseWaitStartTime)
					self._pauseWaitStartTime = None

				self._changeState(self.STATE_PRINTING)
				self._callback.on_comm_print_job_resumed()

				if self.isSdFileSelected():
					self.sendCommand("M24")
					self.sendCommand("M27")
				else:
					line = self._getNext()
					if line is not None:
						self.sendCommand(line)

				# now make sure we actually do something, up until now we only filled up the queue
				self._sendFromQueue()

			elif pause and self.isPrinting():
				if not self._pauseWaitStartTime:
					self._pauseWaitStartTime = time.time()

				self._changeState(self.STATE_PAUSED)
				if self.isSdFileSelected():
					self.sendCommand("M25") # pause print

				def _on_M400_sent():
					# we don't call on_print_job_paused on our callback here
					# because we do this only after our M114 has been answered
					# by the firmware
					self._record_pause_data = True
					self.sendCommand("M114")

				if self._log_position_on_pause:
					self.sendCommand("M400", on_sent=_on_M400_sent)
				else:
					self._pause_preparation_done()

	def getSdFiles(self):
		return self._sdFiles

	def deleteSdFile(self, filename):
		if not self._sdEnabled:
			return

		if not self.isOperational() or (self.isBusy() and
				isinstance(self._currentFile, PrintingSdFileInformation) and
				self._currentFile.getFilename() == filename):
			# do not delete a file from sd we are currently printing from
			return

		self.sendCommand("M30 %s" % filename.lower())
		self.refreshSdFiles()

	def refreshSdFiles(self):
		if not self._sdEnabled:
			return

		if not self.isOperational() or self.isBusy():
			return

		self.sendCommand("M20")

	def initSdCard(self):
		if not self._sdEnabled:
			return

		if not self.isOperational():
			return

		self.sendCommand("M21")
		if self._sdAlwaysAvailable:
			self._sdAvailable = True
			self.refreshSdFiles()
			self._callback.on_comm_sd_state_change(self._sdAvailable)

	def releaseSdCard(self):
		if not self._sdEnabled:
			return

		if not self.isOperational() or (self.isBusy() and self.isSdFileSelected()):
			# do not release the sd card if we are currently printing from it
			return

		self.sendCommand("M22")
		self._sdAvailable = False
		self._sdFiles = []

		self._callback.on_comm_sd_state_change(self._sdAvailable)
		self._callback.on_comm_sd_files(self._sdFiles)

	def sayHello(self):
		self.sendCommand(self._hello_command, force=True)
		self._clear_to_send.set()

	def resetLineNumbers(self, number=0):
		if not self.isOperational():
			return

		self.sendCommand("M110 N%d" % number)

	##~~ record aborted file positions

	def getFilePosition(self):
		if self._currentFile is None:
			return None

		origin = self._currentFile.getFileLocation()
		filename = self._currentFile.getFilename()
		pos = self._currentFile.getFilepos()

		return dict(origin=origin,
		            filename=filename,
		            pos=pos)

	def _recordFilePosition(self):
		if self._currentFile is None:
			return
		data = self.getFilePosition()
		self._callback.on_comm_record_fileposition(data["origin"], data["filename"], data["pos"])

	##~~ communication monitoring and handling

	def _processTemperatures(self, line):
		current_tool = self._currentTool if self._currentTool is not None else 0
		current_tool_key = "T%d" % current_tool
		maxToolNum, parsedTemps = parse_temperature_line(line, current_tool)

		for name, hook in self._temperature_hooks.items():
			try:
				parsedTemps = hook(self, parsedTemps)
				if parsedTemps is None or not parsedTemps:
					return
			except:
				self._logger.exception("Error while processing temperatures in {}, skipping".format(name))

		if current_tool_key in parsedTemps.keys():
			shared_nozzle = self._printerProfileManager.get_current_or_default()["extruder"]["sharedNozzle"]
			for n in range(maxToolNum + 1):
				tool = "T%d" % n
				if not tool in parsedTemps:
					if shared_nozzle:
						actual, target = parsedTemps[current_tool_key]
					else:
						continue
				else:
					actual, target = parsedTemps[tool]
				self.last_temperature.set_tool(n, actual=actual, target=target)

		# bed temperature
		if "B" in parsedTemps.keys():
			actual, target = parsedTemps["B"]
			self.last_temperature.set_bed(actual=actual, target=target)

	##~~ Serial monitor processing received messages

	def _monitor(self):
		feedback_controls, feedback_matcher = convert_feedback_controls(settings().get(["controls"]))
		feedback_errors = []
		pause_triggers = convert_pause_triggers(settings().get(["printerParameters", "pauseTriggers"]))

		disable_external_heatup_detection = not settings().getBoolean(["feature", "externalHeatupDetection"])

		self._consecutive_timeouts = 0

		#Open the serial port.
		if not self._openSerial():
			return

		try_hello = not settings().getBoolean(["feature", "waitForStartOnConnect"])

		self._log("Connected to: %s, starting monitor" % self._serial)
		if self._baudrate == 0:
			self._serial.timeout = 0.01
			try_hello = False
			self._log("Starting baud rate detection")
			self._changeState(self.STATE_DETECT_BAUDRATE)
		else:
			self._changeState(self.STATE_CONNECTING)

		#Start monitoring the serial port.
		self._timeout = get_new_timeout("communication", self._timeout_intervals)

		startSeen = False
		supportRepetierTargetTemp = settings().getBoolean(["feature", "repetierTargetTemp"])
		supportWait = settings().getBoolean(["feature", "supportWait"])

		connection_timeout = settings().getFloat(["serial", "timeout", "connection"])
		detection_timeout = settings().getFloat(["serial", "timeout", "detection"])

		# enqueue the "hello command" first thing
		if try_hello:
			self.sayHello()

		while self._monitoring_active:
			now = time.time()
			try:
				line = self._readline()
				if line is None:
					break
				if line.strip() is not "":
					self._consecutive_timeouts = 0
					self._timeout = get_new_timeout("communication", self._timeout_intervals)

					if self._dwelling_until and now > self._dwelling_until:
						self._dwelling_until = False

				##~~ debugging output handling
				if line.startswith("//"):
					debugging_output = line[2:].strip()
					if debugging_output.startswith("action:"):
						action_command = debugging_output[len("action:"):].strip()

						if action_command == "pause":
							self._log("Pausing on request of the printer...")
							self.setPause(True)
						elif action_command == "resume":
							self._log("Resuming on request of the printer...")
							self.setPause(False)
						elif action_command == "disconnect":
							self._log("Disconnecting on request of the printer...")
							self._callback.on_comm_force_disconnect()
						else:
							for hook in self._printer_action_hooks:
								try:
									self._printer_action_hooks[hook](self, line, action_command)
								except:
									self._logger.exception("Error while calling hook {} with action command {}".format(self._printer_action_hooks[hook], action_command))
									continue
					else:
						continue

				def convert_line(line):
					if line is None:
						return None, None
					stripped_line = line.strip().strip("\0")
					return stripped_line, stripped_line.lower()

				##~~ Error handling
				line = self._handle_errors(line)
				line, lower_line = convert_line(line)

				##~~ SD file list
				# if we are currently receiving an sd file list, each line is just a filename, so just read it and abort processing
				if self._sdFileList and not "End file list" in line:
					preprocessed_line = lower_line
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

					if valid_file_type(filename, "machinecode"):
						if filter_non_ascii(filename):
							self._logger.warn("Got a file from printer's SD that has a non-ascii filename (%s), that shouldn't happen according to the protocol" % filename)
						else:
							if not filename.startswith("/"):
								# file from the root of the sd -- we'll prepend a /
								filename = "/" + filename
							self._sdFiles.append((filename, size))
						continue

				handled = False

				# process oks
				if line.startswith("ok") or (self.isPrinting() and supportWait and line == "wait"):
					# ok only considered handled if it's alone on the line, might be
					# a response to an M105 or an M114
					self._handle_ok()
					needs_further_handling = "T:" in line or "T0:" in line or "B:" in line or "C:" in line or \
					                         "X:" in line or "NAME:" in line
					handled = (line == "wait" or line == "ok" or not needs_further_handling)

				# process resends
				elif lower_line.startswith("resend") or lower_line.startswith("rs"):
					self._handleResendRequest(line)
					handled = True

				# process timeouts
				elif line == "" and (not self._blockWhileDwelling or not self._dwelling_until or now > self._dwelling_until) and now > self._timeout:
					# timeout only considered handled if the printer is printing
					self._handle_timeout()
					handled = self.isPrinting()

				# we don't have to process the rest if the line has already been handled fully
				if handled and self._state not in (self.STATE_CONNECTING, self.STATE_DETECT_BAUDRATE):
					continue

				# position report processing
				if 'X:' in line and 'Y:' in line and 'Z:' in line:
					match = regex_position.search(line)
					if match:
						# we don't know T or F when printing from SD since
						# there's no way to query it from the firmware and
						# no way to track it ourselves when not streaming
						# the file - this all sucks sooo much
						self.last_position.valid = True
						self.last_position.x = float(match.group("x"))
						self.last_position.y = float(match.group("y"))
						self.last_position.z = float(match.group("z"))
						self.last_position.e = float(match.group("e"))
						self.last_position.t = self._currentTool if not self.isSdFileSelected() else None
						self.last_position.f = self._currentF if not self.isSdFileSelected() else None

						reason = None

						if self._record_pause_data:
							reason = "pause"
							self._record_pause_data = False
							self.pause_position.copy_from(self.last_position)
							self.pause_temperature.copy_from(self.last_temperature)
							self._pause_preparation_done()

						if self._record_cancel_data:
							reason = "cancel"
							self._record_cancel_data = False
							self.cancel_position.copy_from(self.last_position)
							self.cancel_temperature.copy_from(self.last_temperature)
							self._cancel_preparation_done()

						self._callback.on_comm_position_update(self.last_position.as_dict(), reason=reason)

				# temperature processing
				elif ' T:' in line or line.startswith('T:') or ' T0:' in line or line.startswith('T0:') \
						or ((' B:' in line or line.startswith('B:')) and not 'A:' in line):

					if not disable_external_heatup_detection and not self._temperature_autoreporting \
							and not line.strip().startswith("ok") and not self._heating \
							and self._firmware_info_received:
						self._logger.debug("Externally triggered heatup detected")
						self._heating = True
						self._heatupWaitStartTime = time.time()

					self._processTemperatures(line)
					self._callback.on_comm_temperature_update(self.last_temperature.tools, self.last_temperature.bed)

				elif supportRepetierTargetTemp and ('TargetExtr' in line or 'TargetBed' in line):
					matchExtr = regex_repetierTempExtr.match(line)
					matchBed = regex_repetierTempBed.match(line)

					if matchExtr is not None:
						toolNum = int(matchExtr.group(1))
						try:
							target = float(matchExtr.group(2))
							self.last_temperature.set_tool(toolNum, target=target)
							self._callback.on_comm_temperature_update(self.last_temperature.tools, self.last_temperature.bed)
						except ValueError:
							pass
					elif matchBed is not None:
						try:
							target = float(matchBed.group(1))
							self.last_temperature.set_bed(target=target)
							self._callback.on_comm_temperature_update(self.last_temperature.tools, self.last_temperature.bed)
						except ValueError:
							pass

				##~~ firmware name & version
				elif "NAME:" in line:
					# looks like a response to M115
					data = parse_firmware_line(line)
					firmware_name = data.get("FIRMWARE_NAME")

					if firmware_name is None:
						# Malyan's "Marlin compatible firmware" isn't actually Marlin compatible and doesn't even
						# report its firmware name properly in response to M115. Wonderful - why stick to established
						# protocol when you can do your own thing, right?
						#
						# Example: NAME: Malyan VER: 2.9 MODEL: M200 HW: HA02
						#
						# We do a bit of manual fiddling around here to circumvent that issue and get ourselves a
						# reliable firmware name (NAME + VER) out of the Malyan M115 response.
						name = data.get("NAME")
						ver = data.get("VER")
						if name and "malyan" in name.lower() and ver:
							firmware_name = name.strip() + " " + ver.strip()

					if not self._firmware_info_received and firmware_name:
						firmware_name = firmware_name.strip()
						self._logger.info("Printer reports firmware name \"{}\"".format(firmware_name))

						if "repetier" in firmware_name.lower() or "anet_a8" in firmware_name.lower():
							self._logger.info("Detected Repetier firmware, enabling relevant features for issue free communication")

							self._alwaysSendChecksum = True
							self._resendSwallowRepetitions = True
							self._blockWhileDwelling = True
							supportRepetierTargetTemp = True
							disable_external_heatup_detection = True

							sd_always_available = self._sdAlwaysAvailable
							self._sdAlwaysAvailable = True
							if not sd_always_available and not self._sdAvailable:
								self.initSdCard()

						elif "reprapfirmware" in firmware_name.lower():
							self._logger.info("Detected RepRapFirmware, enabling relevant features for issue free communication")
							self._sdRelativePath = True

						elif "malyan" in firmware_name.lower():
							self._logger.info("Detected Malyan firmware, enabling relevant features for issue free communication")

							self._alwaysSendChecksum = True
							self._blockWhileDwelling = True

							sd_always_available = self._sdAlwaysAvailable
							self._sdAlwaysAvailable = True
							if not sd_always_available and not self._sdAvailable:
								self.initSdCard()

						self._firmware_info_received = True
						self._firmware_info = data
						self._firmware_name = firmware_name

				##~~ Firmware capability report triggered by M115
				elif lower_line.startswith("cap:"):
					parsed = parse_capability_line(lower_line)
					if parsed is not None:
						capability, enabled = parsed
						self._firmware_capabilities[capability] = enabled

						if capability == self.CAPABILITY_AUTOREPORT_TEMP and enabled:
							self._logger.info("Firmware states that it supports temperature autoreporting")
							self._set_autoreport_temperature()

				##~~ SD Card handling
				elif 'SD init fail' in line or 'volume.init failed' in line or 'openRoot failed' in line:
					self._sdAvailable = False
					self._sdFiles = []
					self._callback.on_comm_sd_state_change(self._sdAvailable)
				elif 'Not SD printing' in line:
					if self.isSdFileSelected() and self.isPrinting():
						# something went wrong, printer is reporting that we actually are not printing right now...
						self._sdFilePos = 0
						self._changeState(self.STATE_OPERATIONAL)
				elif 'SD card ok' in line and not self._sdAvailable:
					self._sdAvailable = True
					self.refreshSdFiles()
					self._callback.on_comm_sd_state_change(self._sdAvailable)
				elif 'Begin file list' in line:
					self._sdFiles = []
					self._sdFileList = True
				elif 'End file list' in line:
					self._sdFileList = False
					self._callback.on_comm_sd_files(self._sdFiles)
				elif 'SD printing byte' in line and self.isSdPrinting():
					# answer to M27, at least on Marlin, Repetier and Sprinter: "SD printing byte %d/%d"
					match = regex_sdPrintingByte.search(line)
					self._currentFile.setFilepos(int(match.group("current")))
					self._callback.on_comm_progress()
				elif 'File opened' in line and not self._ignore_select:
					# answer to M23, at least on Marlin, Repetier and Sprinter: "File opened:%s Size:%d"
					match = regex_sdFileOpened.search(line)
					if match:
						name = match.group("name")
						size = int(match.group("size"))
					else:
						name = "Unknown"
						size = 0
					if self._sdFileToSelect:
						name = self._sdFileToSelect
						self._sdFileToSelect = None
					self._currentFile = PrintingSdFileInformation(name, size)
				elif 'File selected' in line:
					if self._ignore_select:
						self._ignore_select = False
					elif self._currentFile is not None and self.isSdFileSelected():
						# final answer to M23, at least on Marlin, Repetier and Sprinter: "File selected"
						self._callback.on_comm_file_selected(self._currentFile.getFilename(), self._currentFile.getFilesize(), True)
				elif 'Writing to file' in line and self.isStreaming():
					self._changeState(self.STATE_PRINTING)
				elif 'Done printing file' in line and self.isSdPrinting():
					# printer is reporting file finished printing
					self._sdFilePos = 0
					self._callback.on_comm_print_job_done()
					self._changeState(self.STATE_OPERATIONAL)
					if self._sd_status_timer is not None:
						try:
							self._sd_status_timer.cancel()
						except:
							pass
				elif 'Done saving file' in line:
					if self._trigger_ok_for_m29:
						# workaround for most versions of Marlin out in the wild
						# not sending an ok after saving a file
						self._handle_ok()
				elif 'File deleted' in line and line.strip().endswith("ok"):
					# buggy Marlin version that doesn't send a proper line break after the "File deleted" statement, fixed in
					# current versions
					self._handle_ok()

				##~~ Message handling
				self._callback.on_comm_message(line)

				##~~ Parsing for feedback commands
				if feedback_controls and feedback_matcher and not "_all" in feedback_errors:
					try:
						self._process_registered_message(line, feedback_matcher, feedback_controls, feedback_errors)
					except:
						# something went wrong while feedback matching
						self._logger.exception("Error while trying to apply feedback control matching, disabling it")
						feedback_errors.append("_all")

				##~~ Parsing for pause triggers
				if pause_triggers and not self.isStreaming():
					if "enable" in pause_triggers.keys() and pause_triggers["enable"].search(line) is not None:
						self.setPause(True)
					elif "disable" in pause_triggers.keys() and pause_triggers["disable"].search(line) is not None:
						self.setPause(False)
					elif "toggle" in pause_triggers.keys() and pause_triggers["toggle"].search(line) is not None:
						self.setPause(not self.isPaused())

				### Baudrate detection
				if self._state == self.STATE_DETECT_BAUDRATE:
					if line == '' or time.time() > self._timeout:
						if self._baudrateDetectRetry > 0:
							self._serial.timeout = detection_timeout
							self._baudrateDetectRetry -= 1
							self._serial.write('\n')
							self._log("Baudrate test retry: %d" % (self._baudrateDetectRetry))
							self.sayHello()
						elif len(self._baudrateDetectList) > 0:
							baudrate = self._baudrateDetectList.pop(0)
							try:
								self._serial.baudrate = baudrate
								if self._serial.timeout != connection_timeout:
									self._serial.timeout = connection_timeout
								self._log("Trying baudrate: %d" % (baudrate))
								self._baudrateDetectRetry = 5
								self._timeout = get_new_timeout("communication", self._timeout_intervals)
								self._serial.write('\n')
								self.sayHello()
							except:
								self._log("Unexpected error while setting baudrate {}: {}".format(baudrate, get_exception_string()))
								self._logger.exception("Unexpceted error while setting baudrate {}".format(baudrate))
						else:
							self.close(wait=False)
							self._errorValue = "No more baudrates to test, and no suitable baudrate found."
							self._changeState(self.STATE_ERROR)
							eventManager().fire(Events.ERROR, {"error": self.getErrorString()})
					elif 'start' in line or 'ok' in line:
						self._onConnected()
						if 'start' in line:
							self._clear_to_send.set()

				### Connection attempt
				elif self._state == self.STATE_CONNECTING:
					if "start" in line and not startSeen:
						startSeen = True
						self.sayHello()
					elif line.startswith("ok") or (supportWait and line == "wait"):
						if line == "wait":
							# if it was a wait we probably missed an ok, so let's simulate that now
							self._handle_ok()
						self._onConnected()
					elif time.time() > self._timeout:
						self._log("There was a timeout while trying to connect to the printer")
						self.close(wait=False)

				### Operational (idle or busy)
				elif self._state in (self.STATE_OPERATIONAL,
				                     self.STATE_PRINTING,
				                     self.STATE_PAUSED,
				                     self.STATE_TRANSFERING_FILE):
					if line == "start": # exact match, to be on the safe side
						if self._state in (self.STATE_OPERATIONAL,):
							message = "Printer sent 'start' while already operational. External reset? " \
							          "Resetting line numbers to be on the safe side"
							self._log(message)
							self._logger.warn(message)
							self._onExternalReset()

						else:
							verb = "streaming to SD" if self.isStreaming() else "printing"
							message = "Printer sent 'start' while {}. External reset? " \
							          "Aborting job since printer lost state.".format(verb)
							self._log(message)
							self._logger.warn(message)
							self.cancelPrint(disable_log_position=True)
							self._onExternalReset()

						eventManager().fire(Events.PRINTER_RESET)

			except:
				self._logger.exception("Something crashed inside the serial connection loop, please report this in OctoPrint's bug tracker:")

				errorMsg = "See octoprint.log for details"
				self._log(errorMsg)
				self._errorValue = errorMsg
				eventManager().fire(Events.ERROR, {"error": self.getErrorString()})
				self.close(is_error=True)
		self._log("Connection closed, closing down monitor")

	def _handle_ok(self):
		self._clear_to_send.set()

		# reset long running commands, persisted current tools and heatup counters on ok

		self._long_running_command = False

		if self._formerTool is not None:
			self._currentTool = self._formerTool
			self._formerTool = None

		self._finish_heatup()

		if not self._state in (self.STATE_PRINTING, self.STATE_OPERATIONAL, self.STATE_PAUSED):
			return

		# process queues ongoing resend requests and queues if we are operational

		if self._resendDelta is not None:
			self._resendNextCommand()
		else:
			self._resendActive = False
			self._continue_sending()

		return

	def _handle_timeout(self):
		if self._state not in (self.STATE_PRINTING,
		                       self.STATE_PAUSED,
		                       self.STATE_OPERATIONAL):
			return

		general_message = "Configure long running commands or increase communication timeout if that happens regularly on specific commands or long moves."

		# figure out which consecutive timeout maximum we have to use
		if self._long_running_command:
			consecutive_max = self._consecutive_timeout_maximums.get("long", 0)
		elif self._state in (self.STATE_PRINTING,):
			consecutive_max = self._consecutive_timeout_maximums.get("printing", 0)
		else:
			consecutive_max = self._consecutive_timeout_maximums.get("idle", 0)

		# now increment the timeout counter
		self._consecutive_timeouts += 1
		self._logger.debug("Now at {} consecutive timeouts".format(self._consecutive_timeouts))

		if 0 < consecutive_max < self._consecutive_timeouts:
			# too many consecutive timeouts, we give up
			message = "No response from printer after {} consecutive communication timeouts, considering it dead.".format(consecutive_max + 1)
			self._logger.info(message)
			self._log(message + " " + general_message)
			self._errorValue = "Too many consecutive timeouts, printer still connected and alive?"
			eventManager().fire(Events.ERROR, {"error": self._errorValue})
			self.close(is_error=True)

		elif self._resendActive:
			# resend active, resend same command instead of triggering a new one
			message = "Communication timeout during an active resend, resending same line again to trigger response from printer."
			self._logger.info(message)
			self._log(message + " " + general_message)
			if self._resendSameCommand():
				self._clear_to_send.set()

		elif self._heating:
			# blocking heatup active, consider that finished
			message = "Timeout while in an active heatup, considering heatup to be over."
			self._logger.info(message)
			self._finish_heatup()

		elif self._long_running_command:
			# long running command active, ignore timeout
			self._logger.debug("Ran into a communication timeout, but a command known to be a long runner is currently active")

		elif self._state in (self.STATE_PRINTING, self.STATE_PAUSED):
			# printing, try to tickle the printer
			message = "Communication timeout while printing, trying to trigger response from printer."
			self._logger.info(message)
			self._log(message + " " + general_message)
			if self._sendCommand("M105", cmd_type="temperature"):
				self._clear_to_send.set()

		elif self._clear_to_send.blocked():
			# timeout while idle and no oks left, let's try to tickle the printer
			message = "Communication timeout while idle, trying to trigger response from printer."
			self._logger.info(message)
			self._log(message + " " + general_message)
			self._clear_to_send.set()

	def _finish_heatup(self):
		if self._heatupWaitStartTime:
			self._heatupWaitTimeLost = self._heatupWaitTimeLost + (time.time() - self._heatupWaitStartTime)
			self._heatupWaitStartTime = None
			self._heating = False

	def _continue_sending(self):
		while self._active:

			if self._state == self.STATE_OPERATIONAL or self._state == self.STATE_PAUSED or self.isSdPrinting():
				# just send stuff from the command queue and be done with it
				return self._sendFromQueue()

			elif self._state == self.STATE_PRINTING:
				# we are printing, we really want to send either something from the command
				# queue or the next line from our file, so we only return here if we actually DO
				# send something
				if self._sendFromQueue():
					# we found something in the queue to send
					return True

				elif self._sendNext():
					# we sent the next line from the file
					return True

				self._logger.debug("No command sent on ok while printing, doing another iteration")

	def _process_registered_message(self, line, feedback_matcher, feedback_controls, feedback_errors):
		feedback_match = feedback_matcher.search(line)
		if feedback_match is None:
			return

		for match_key in feedback_match.groupdict():
			try:
				feedback_key = match_key[len("group"):]
				if not feedback_key in feedback_controls or feedback_key in feedback_errors or feedback_match.group(match_key) is None:
					continue
				matched_part = feedback_match.group(match_key)

				if feedback_controls[feedback_key]["matcher"] is None:
					continue

				match = feedback_controls[feedback_key]["matcher"].search(matched_part)
				if match is None:
					continue

				outputs = dict()
				for template_key, template in feedback_controls[feedback_key]["templates"].items():
					try:
						output = template.format(*match.groups())
					except KeyError:
						output = template.format(**match.groupdict())
					except:
						output = None

					if output is not None:
						outputs[template_key] = output
				eventManager().fire(Events.REGISTERED_MESSAGE_RECEIVED, dict(key=feedback_key, matched=matched_part, outputs=outputs))
			except:
				self._logger.exception("Error while trying to match feedback control output, disabling key {key}".format(key=match_key))
				feedback_errors.append(match_key)

	def _poll_temperature(self):
		"""
		Polls the temperature after the temperature timeout, re-enqueues itself.

		If the printer is not operational, capable of auto-reporting temperatures, closing the connection, not printing
		from sd, busy with a long running command or heating, no poll will be done.
		"""

		if self.isOperational() and not self._temperature_autoreporting and not self._connection_closing and not self.isStreaming() and not self._long_running_command and not self._heating and not self._dwelling_until and not self._manualStreaming:
			self.sendCommand("M105", cmd_type="temperature_poll")

	def _poll_sd_status(self):
		"""
		Polls the sd printing status after the sd status timeout, re-enqueues itself.

		If the printer is not operational, closing the connection, not printing from sd, busy with a long running
		command or heating, no poll will be done.
		"""

		if self.isOperational() and not self._connection_closing and self.isSdPrinting() and not self._long_running_command and not self._dwelling_until and not self._heating:
			self.sendCommand("M27", cmd_type="sd_status_poll")

	def _set_autoreport_temperature(self, interval=None):
		if interval is None:
			try:
				interval = int(self._timeout_intervals.get("temperatureAutoreport", 2))
			except:
				interval = 2
		self.sendCommand("M155 S{}".format(interval))

	def _onConnected(self):
		self._serial.timeout = settings().getFloat(["serial", "timeout", "communication"])
		self._temperature_timer = RepeatedTimer(self._getTemperatureTimerInterval, self._poll_temperature, run_first=True)
		self._temperature_timer.start()

		self._changeState(self.STATE_OPERATIONAL)

		self.resetLineNumbers()
		if self._firmware_detection:
			self.sendCommand("M115")

		if self._sdAvailable:
			self.refreshSdFiles()
		else:
			self.initSdCard()

		payload = dict(port=self._port, baudrate=self._baudrate)
		eventManager().fire(Events.CONNECTED, payload)
		self.sendGcodeScript("afterPrinterConnected", replacements=dict(event=payload))

	def _onExternalReset(self):
		self.resetLineNumbers()

		if self._temperature_autoreporting:
			self._set_autoreport_temperature()

	def _getTemperatureTimerInterval(self):
		busy_default = 4.0
		target_default = 2.0

		if self.isBusy():
			return self._timeout_intervals.get("temperature", busy_default)

		tools = self.last_temperature.tools
		for temp in [tools[k][1] for k in tools.keys()]:
			if temp > self._temperatureTargetSetThreshold:
				return self._timeout_intervals.get("temperatureTargetSet", target_default)

		bed = self.last_temperature.bed
		if bed and len(bed) > 0 and bed[1] > self._temperatureTargetSetThreshold:
			return self._timeout_intervals.get("temperatureTargetSet", target_default)

		return self._timeout_intervals.get("temperature", busy_default)

	def _sendFromQueue(self):
		# We loop here to make sure that if we do NOT send the first command
		# from the queue, we'll send the second (if there is one). We do not
		# want to get stuck here by throwing away commands.
		while True:
			if self.isStreaming():
				# command queue irrelevant
				return False

			try:
				entry = self._command_queue.get(block=False)
			except queue.Empty:
				# nothing in command queue
				return False

			try:
				if isinstance(entry, tuple):
					if not len(entry) == 3:
						# something with that entry is broken, ignore it and fetch
						# the next one
						continue
					cmd, cmd_type, callback = entry
				else:
					cmd = entry
					cmd_type = None
					callback = None

				if self._sendCommand(cmd, cmd_type=cmd_type, on_sent=callback):
					# we actually did add this cmd to the send queue, so let's
					# return, we are done here
					return True
			finally:
				self._command_queue.task_done()

	def _detect_port(self):
		potentials = serialList()
		self._log("Serial port list: %s" % (str(potentials)))

		if len(potentials) == 1:
			# short cut: only one port, let's try that
			return potentials[0]

		elif len(potentials) > 1:
			programmer = stk500v2.Stk500v2()

			for p in potentials:
				serial_obj = None

				try:
					self._log("Trying {}".format(p))
					programmer.connect(p)
					serial_obj = programmer.leaveISP()
				except ispBase.IspError as e:
					self._log("Could not enter programming mode on {}, might not be a printer or just not allow programming mode".format(p))
					self._logger.info("Could not enter programming mode on {}: {}".format(p, e))
				except:
					self._log("Could not connect to {}: {}".format(p, get_exception_string()))
					self._logger.exception("Could not connect to {}".format(p))

				found = serial_obj is not None
				programmer.close()

				if found:
					return p

		return None

	def _openSerial(self):
		def default(_, port, baudrate, read_timeout):
			if port is None or port == 'AUTO':
				# no known port, try auto detection
				self._changeState(self.STATE_DETECT_SERIAL)
				port = self._detect_port()
				if port is None:
					self._errorValue = 'Failed to autodetect serial port, please set it manually.'
					self._changeState(self.STATE_ERROR)
					eventManager().fire(Events.ERROR, {"error": self.getErrorString()})
					self._log("Failed to autodetect serial port, please set it manually.")
					return None

			# connect to regular serial port
			self._log("Connecting to: %s" % port)
			if baudrate == 0:
				baudrates = baudrateList()
				serial_obj = serial.Serial(str(port), 115200 if 115200 in baudrates else baudrates[0], timeout=read_timeout, writeTimeout=10000, parity=serial.PARITY_ODD)
			else:
				serial_obj = serial.Serial(str(port), baudrate, timeout=read_timeout, writeTimeout=10000, parity=serial.PARITY_ODD)
			serial_obj.close()
			serial_obj.parity = serial.PARITY_NONE
			serial_obj.open()

			return serial_obj

		serial_factories = self._serial_factory_hooks.items() + [("default", default)]
		for name, factory in serial_factories:
			try:
				serial_obj = factory(self, self._port, self._baudrate, settings().getFloat(["serial", "timeout", "connection"]))
			except:
				exception_string = get_exception_string()
				self._errorValue = "Connection error, see Terminal tab"
				self._changeState(self.STATE_ERROR)
				eventManager().fire(Events.ERROR, {"error": self.getErrorString()})

				error_message = "Unexpected error while connecting to serial port: %s %s (hook %s)" % (self._port, exception_string, name)
				self._log(error_message)
				self._logger.exception(error_message)

				if "failed to set custom baud rate" in exception_string.lower():
					self._log("Your installation does not support custom baudrates (e.g. 250000) for connecting to your printer. This is a problem of the pyserial library that OctoPrint depends on. Please update to a pyserial version that supports your baudrate or switch your printer's firmware to a standard baudrate (e.g. 115200). See https://github.com/foosel/OctoPrint/wiki/OctoPrint-support-for-250000-baud-rate-on-Raspbian")

				return False

			if serial_obj is not None:
				# first hook to succeed wins, but any can pass on to the next
				self._changeState(self.STATE_OPEN_SERIAL)
				self._serial = serial_obj
				self._clear_to_send.clear()
				return True

		return False

	_recoverable_communication_errors    = ("no line number with checksum",)
	_resend_request_communication_errors = ("line number", # since this error class get's checked after recoverable
	                                                       # communication errors, we can use this broad term here
	                                        "checksum",    # since this error class get's checked after recoverable
	                                                       # communication errors, we can use this broad term here
	                                        "format error",
	                                        "expected line")
	_sd_card_errors                      = ("volume.init",
	                                        "openroot",
	                                        "workdir",
	                                        "error writing to file",
	                                        "cannot open",
	                                        "open failed",
	                                        "cannot enter")
	def _handle_errors(self, line):
		if line is None:
			return

		lower_line = line.lower()

		if lower_line.startswith('error:') or line.startswith('!!'):
			if regex_minMaxError.match(line):
				# special delivery for firmware that goes "Error:x\n: Extruder switched off. MAXTEMP triggered !\n"
				line = line.rstrip() + self._readline()

			if any(map(lambda x: x in lower_line, self._recoverable_communication_errors)):
				# manually trigger an ack for comm errors the printer doesn't send a resend request for but
				# from which we can recover from by just pushing on (because that then WILL trigger a fitting
				# resend request)
				self._handle_ok()

			elif any(map(lambda x: x in lower_line, self._resend_request_communication_errors)):
				# skip comm errors that the printer sends a resend request for anyhow
				self._lastCommError = line[6:] if lower_line.startswith("error:") else line[2:]

			elif any(map(lambda x: x in lower_line, self._sd_card_errors)):
				# skip errors with the SD card
				pass

			elif 'unknown command' in lower_line:
				# ignore unknown command errors, it could be a typo or some missing feature
				pass

			elif not self.isError():
				# handle everything else
				error_text = line[6:] if lower_line.startswith("error:") else line[2:]
				self._to_logfile_with_terminal("Received an error from the printer's firmware: {}".format(error_text),
				                               level=logging.WARN)

				if not self._ignore_errors:
					if self._disconnect_on_errors:
						self._errorValue = error_text
						self._changeState(self.STATE_ERROR)
						eventManager().fire(Events.ERROR, {"error": self.getErrorString()})
					elif self.isPrinting():
						self.cancelPrint(firmware_error=error_text)
						self._clear_to_send.set()
				else:
					self._log("WARNING! Received an error from the printer's firmware, ignoring that as configured but you might want to investigate what happened here! Error: {}".format(error_text))
					self._clear_to_send.set()

		# finally return the line
		return line

	def _readline(self):
		if self._serial is None:
			return None

		try:
			ret = self._serial.readline()
		except Exception as ex:
			if not self._connection_closing:
				self._logger.exception("Unexpected error while reading from serial port")
				self._log("Unexpected error while reading serial port, please consult octoprint.log for details: %s" % (get_exception_string()))
				if isinstance(ex, serial.SerialException):
					self._dual_log("Please see https://bit.ly/octoserial for possible reasons of this.",
					               level=logging.ERROR)
				self._errorValue = get_exception_string()
				self.close(is_error=True)
			return None

		if ret != "":
			try:
				self._log("Recv: " + sanitize_ascii(ret))
			except ValueError as e:
				self._log("WARN: While reading last line: %s" % e)
				self._log("Recv: " + repr(ret))

		for name, hook in self._received_message_hooks.items():
			try:
				ret = hook(self, ret)
			except:
				self._logger.exception("Error while processing hook {name}:".format(**locals()))
			else:
				if ret is None:
					return ""

		return ret

	def _getNext(self):
		if self._currentFile is None:
			return None

		line = self._currentFile.getNext()
		if line is None:
			if self.isStreaming():
				self._finishFileTransfer()
			else:
				self._callback.on_comm_print_job_done()
				self._changeState(self.STATE_OPERATIONAL)
		return line

	def _sendNext(self):
		with self._jobLock:
			while self._active:
				# we loop until we've actually enqueued a line for sending
				if self._state != self.STATE_PRINTING:
					# we are no longer printing, return false
					return False

				line = self._getNext()
				if line is None:
					# end of file, return false
					return False

				result = self._sendCommand(line)
				self._callback.on_comm_progress()
				if result:
					# line sent, return true
					return True

				self._logger.debug("Command \"{}\" from file not enqueued, doing another iteration".format(line))

	def _handleResendRequest(self, line):
		try:
			lineToResend = parse_resend_line(line)
			if lineToResend is None:
				return False

			if self._resendDelta is None and lineToResend == self._currentLine:
				# We don't expect to have an active resend request and the printer is requesting a resend of
				# a line we haven't yet sent.
				#
				# This means the printer got a line from us with N = self._currentLine - 1 but had already
				# acknowledged that. This can happen if the last line was resent due to a timeout during
				# an active (prior) resend request.
				#
				# We will ignore this resend request and just continue normally.
				self._logger.info("Ignoring resend request for line %d == current line, we haven't sent that yet so "
				                   "the printer got N-1 twice from us, probably due to a timeout" % lineToResend)
				return False

			lastCommError = self._lastCommError
			self._lastCommError = None

			resendDelta = self._currentLine - lineToResend

			if lastCommError is not None \
					and ("line number" in lastCommError.lower() or "expected line" in lastCommError.lower()) \
					and lineToResend == self._lastResendNumber \
					and self._resendDelta is not None and self._currentResendCount < self._resendDelta:
				self._logger.info("Ignoring resend request for line %d, that still originates from lines we sent "
				                   "before we got the first resend request" % lineToResend)
				self._currentResendCount += 1
				return True

			# If we ignore resend repetitions (Repetier firmware...), check if we
			# need to do this now. If the same line number has been requested we
			# already saw and resent, we'll ignore it up to <counter> times.
			if self._resendSwallowRepetitions and lineToResend == self._lastResendNumber and self._resendSwallowRepetitionsCounter > 0:
				self._logger.info("Ignoring resend request for line %d, that is probably a repetition sent by the "
				                   "firmware to ensure it arrives, not a real request" % lineToResend)
				self._resendSwallowRepetitionsCounter -= 1
				return True

			self._resendActive = True
			self._resendDelta = resendDelta
			self._lastResendNumber = lineToResend
			self._currentResendCount = 0
			self._resendSwallowRepetitionsCounter = settings().getInt(["feature", "identicalResendsCountdown"])

			if self._resendDelta > len(self._lastLines) or len(self._lastLines) == 0 or self._resendDelta < 0:
				self._errorValue = "Printer requested line %d but no sufficient history is available, can't resend" % lineToResend
				self._log(self._errorValue)
				self._logger.warn(self._errorValue + ". Printer requested line {}, current line is {}, line history has {} entries.".format(lineToResend, self._currentLine, len(self._lastLines)))
				if self.isPrinting():
					# abort the print, there's nothing we can do to rescue it now
					self._changeState(self.STATE_ERROR)
					eventManager().fire(Events.ERROR, {"error": self.getErrorString()})
				else:
					# reset resend delta, we can't do anything about it
					self._resendDelta = None

			# if we log resends, make sure we don't log more resends than the set rate within a window
			#
			# this it to prevent the log from getting flooded for extremely bad communication issues
			if self._log_resends:
				now = time.time()
				new_rate_window = self._log_resends_rate_start is None or self._log_resends_rate_start + self._log_resends_rate_frame < now
				in_rate = self._log_resends_rate_count < self._log_resends_max

				if new_rate_window or in_rate:
					if new_rate_window:
						self._log_resends_rate_start = now
						self._log_resends_rate_count = 0

					self._to_logfile_with_terminal("Got a resend request from the printer: requested line = {}, current line = {}".format(lineToResend, self._currentLine))
					self._log_resends_rate_count += 1

			self._send_queue.resend_active = True
			return True
		finally:
			if self._supportResendsWithoutOk:
				# simulate an ok if our flags indicate that the printer needs that for resend requests to work
				self._handle_ok()

	def _resendSameCommand(self):
		return self._resendNextCommand(again=True)

	def _resendNextCommand(self, again=False):
		self._lastCommError = None

		# Make sure we are only handling one sending job at a time
		with self._sendingLock:
			if again:
				# If we are about to last line from the active resend request
				# again, we first need to increment resend delta. It might already
				# be set to None if the last resend line was already sent, so
				# if that's the case we set it to 0. It will then be incremented,
				# the last line will be sent again, and then the delta will be
				# decremented and set to None again, completing the cycle.
				if self._resendDelta is None:
					self._resendDelta = 0
				self._resendDelta += 1

			cmd = self._lastLines[-self._resendDelta]
			lineNumber = self._currentLine - self._resendDelta

			result = self._enqueue_for_sending(cmd, linenumber=lineNumber, resend=True)

			self._resendDelta -= 1
			if self._resendDelta <= 0:
				self._resendDelta = None
				self._lastResendNumber = None
				self._currentResendCount = 0

				self._send_queue.resend_active = False

			return result

	def _sendCommand(self, cmd, cmd_type=None, on_sent=None):
		# Make sure we are only handling one sending job at a time
		with self._sendingLock:
			if self._serial is None:
				return False

			gcode, subcode = gcode_and_subcode_for_cmd(cmd)

			if not self.isStreaming():
				# trigger the "queuing" phase only if we are not streaming to sd right now
				results = self._process_command_phase("queuing", cmd, command_type=cmd_type, gcode=gcode, subcode=subcode)

				if not results:
					# command is no more, return
					return False
			else:
				results = [(cmd, cmd_type, gcode, subcode)]

			# process helper
			def process(cmd, cmd_type, gcode, subcode, on_sent=None):
				if cmd is None:
					# no command, next entry
					return False

				if gcode and gcode in gcodeToEvent:
					# if this is a gcode bound to an event, trigger that now
					eventManager().fire(gcodeToEvent[gcode])

				# actually enqueue the command for sending
				if self._enqueue_for_sending(cmd, command_type=cmd_type, on_sent=on_sent):
					if not self.isStreaming():
						# trigger the "queued" phase only if we are not streaming to sd right now
						self._process_command_phase("queued", cmd, cmd_type, gcode=gcode, subcode=subcode)
					return True
				else:
					return False

			# split off the final command, because that needs special treatment
			if len(results) > 1:
				last_command = results[-1]
				results = results[:-1]
			else:
				last_command = results[0]
				results = []

			# track if we enqueued anything at all
			enqueued_something = False

			# process all but the last ...
			for (cmd, cmd_type, gcode, subcode) in results:
				enqueued_something = process(cmd, cmd_type, gcode, subcode) or enqueued_something

			# ... and then process the last one with the on_sent callback attached
			cmd, cmd_type, gcode, subcode = last_command
			enqueued_something = process(cmd, cmd_type, gcode, subcode, on_sent=on_sent) or enqueued_something

			return enqueued_something

	##~~ send loop handling

	def _enqueue_for_sending(self, command, linenumber=None, command_type=None, on_sent=None, resend=False):
		"""
		Enqueues a command and optional linenumber to use for it in the send queue.

		Arguments:
		    command (str): The command to send.
		    linenumber (int): The line number with which to send the command. May be ``None`` in which case the command
		        will be sent without a line number and checksum.
		    command_type (str): Optional command type, if set and command type is already in the queue the
		        command won't be enqueued
		    on_sent (callable): Optional callable to call after command has been sent to printer.
		"""

		try:
			target = "send"
			if resend:
				target = "resend"

			self._send_queue.put((command, linenumber, command_type, on_sent, False), item_type=command_type, target=target)
			return True
		except TypeAlreadyInQueue as e:
			self._logger.debug("Type already in send queue: " + e.type)
			return False

	def _send_loop(self):
		"""
		The send loop is responsible of sending commands in ``self._send_queue`` over the line, if it is cleared for
		sending (through received ``ok`` responses from the printer's firmware.
		"""

		self._clear_to_send.wait()

		while self._send_queue_active:
			try:
				# wait until we have something in the queue
				entry = self._send_queue.get()

				try:
					# make sure we are still active
					if not self._send_queue_active:
						break

					# sleep if we are dwelling
					now = time.time()
					if self._blockWhileDwelling and self._dwelling_until and now < self._dwelling_until:
						time.sleep(self._dwelling_until - now)
						self._dwelling_until = False

					# fetch command, command type and optional linenumber and sent callback from queue
					command, linenumber, command_type, on_sent, processed = entry

					# some firmwares (e.g. Smoothie) might support additional in-band communication that will not
					# stick to the acknowledgement behaviour of GCODE, so we check here if we have a GCODE command
					# at hand here and only clear our clear_to_send flag later if that's the case
					gcode, subcode = gcode_and_subcode_for_cmd(command)

					if linenumber is not None:
						# line number predetermined - this only happens for resends, so we'll use the number and
						# send directly without any processing (since that already took place on the first sending!)
						self._do_send_with_checksum(command, linenumber)

					else:
						if not processed:
							# trigger "sending" phase if we didn't so far
							results = self._process_command_phase("sending", command, command_type, gcode=gcode, subcode=subcode)

							if not results:
								# No, we are not going to send this, that was a last-minute bail.
								# However, since we already are in the send queue, our _monitor
								# loop won't be triggered with the reply from this unsent command
								# now, so we try to tickle the processing of any active
								# command queues manually
								self._continue_sending()

								# and now let's fetch the next item from the queue
								continue

							# we explicitly throw away plugin hook results that try
							# to perform command expansion in the sending/sent phase,
							# so "results" really should only have more than one entry
							# at this point if our core code contains a bug
							assert len(results) == 1

							# we only use the first (and only!) entry here
							command, _, gcode, subcode = results[0]

						if command.strip() == "":
							self._logger.info("Refusing to send an empty line to the printer")

							# same here, tickle the queues manually
							self._continue_sending()

							# and fetch the next item
							continue

						# now comes the part where we increase line numbers and send stuff - no turning back now
						command_requiring_checksum = gcode is not None and gcode in self._checksum_requiring_commands
						command_allowing_checksum = gcode is not None or self._sendChecksumWithUnknownCommands
						checksum_enabled = not self._neverSendChecksum and ((self.isPrinting() and self._currentFile and self._currentFile.checksum) or
						                                                    self._alwaysSendChecksum or
						                                                    not self._firmware_info_received)

						command_to_send = command.encode("ascii", errors="replace")
						if command_requiring_checksum or (command_allowing_checksum and checksum_enabled):
							self._do_increment_and_send_with_checksum(command_to_send)
						else:
							self._do_send_without_checksum(command_to_send)

					# trigger "sent" phase and use up one "ok"
					if on_sent is not None and callable(on_sent):
						# we have a sent callback for this specific command, let's execute it now
						on_sent()
					self._process_command_phase("sent", command, command_type, gcode=gcode, subcode=subcode)

					# we only need to use up a clear if the command we just sent was either a gcode command or if we also
					# require ack's for unknown commands
					use_up_clear = self._unknownCommandsNeedAck
					if gcode is not None:
						use_up_clear = True

					if use_up_clear:
						# if we need to use up a clear, do that now
						self._clear_to_send.clear()
					else:
						# Otherwise we need to tickle the read queue - there might not be a reply
						# to this command, so our _monitor loop will stay waiting until timeout. We
						# definitely do not want that, so we tickle the queue manually here
						self._continue_sending()

				finally:
					# no matter _how_ we exit this block, we signal that we
					# are done processing the last fetched queue entry
					self._send_queue.task_done()

				# now we just wait for the next clear and then start again
				self._clear_to_send.wait()
			except:
				self._logger.exception("Caught an exception in the send loop")
		self._log("Closing down send loop")

	def _process_command_phase(self, phase, command, command_type=None, gcode=None, subcode=None):
		if gcode is None:
			gcode, subcode = gcode_and_subcode_for_cmd(command)
		results = [(command, command_type, gcode, subcode)]

		if (self.isStreaming() and self.isPrinting()) or phase not in ("queuing", "queued", "sending", "sent"):
			return results

		# send it through the phase specific handlers provided by plugins
		for name, hook in self._gcode_hooks[phase].items():
			new_results = []
			for command, command_type, gcode, subcode in results:
				try:
					hook_results = hook(self, phase, command, command_type, gcode, subcode=subcode)
				except:
					self._logger.exception("Error while processing hook {name} for phase {phase} and command {command}:".format(**locals()))
				else:
					normalized = _normalize_command_handler_result(command, command_type, gcode, subcode, hook_results)

					# make sure we don't allow multi entry results in anything but the queuing phase
					if not phase in ("queuing",) and len(normalized) > 1:
						self._logger.error("Error while processing hook {name} for phase {phase} and command {command}: Hook returned multi-entry result for phase {phase} and command {command}. That's not supported, if you need to do multi expansion of commands you need to do this in the queuing phase. Ignoring hook result and sending command as-is.".format(**locals()))
						new_results.append((command, command_type, gcode, subcode))
					else:
						new_results += normalized
			if not new_results:
				# hook handler returned None or empty list for all commands, so we'll stop here and return a full out empty result
				return []
			results = new_results

		# if it's a gcode command send it through the specific handler if it exists
		new_results = []
		modified = False
		for command, command_type, gcode, subcode in results:
			if gcode is not None:
				gcode_handler = "_gcode_" + gcode + "_" + phase
				if hasattr(self, gcode_handler):
					handler_results = getattr(self, gcode_handler)(command, cmd_type=command_type, subcode=subcode)
					new_results += _normalize_command_handler_result(command, command_type, gcode, subcode, handler_results)
					modified = True
				else:
					new_results.append((command, command_type, gcode, subcode))
					modified = True
		if modified:
			if not new_results:
				# gcode handler returned None or empty list for all commands, so we'll stop here and return a full out empty result
				return []
			else:
				results = new_results

		# send it through the phase specific command handler if it exists
		command_phase_handler = "_command_phase_" + phase
		if hasattr(self, command_phase_handler):
			new_results = []
			for command, command_type, gcode, subcode in results:
				handler_results = getattr(self, command_phase_handler)(command, cmd_type=command_type, gcode=gcode, subcode=subcode)
				new_results += _normalize_command_handler_result(command, command_type, gcode, subcode, handler_results)
			results = new_results

		# finally return whatever we resulted on
		return results

	##~~ actual sending via serial

	def _do_increment_and_send_with_checksum(self, cmd):
		with self._line_mutex:
			linenumber = self._currentLine
			self._addToLastLines(cmd)
			self._currentLine += 1
			self._do_send_with_checksum(cmd, linenumber)

	def _do_send_with_checksum(self, command, linenumber):
		command_to_send = "N" + str(linenumber) + " " + command
		checksum = 0
		for c in bytearray(command_to_send):
			checksum ^= c
		command_to_send = command_to_send + "*" + str(checksum)
		self._do_send_without_checksum(command_to_send)

	def _do_send_without_checksum(self, cmd):
		if self._serial is None:
			return

		self._log("Send: " + str(cmd))

		cmd += "\n"
		written = 0
		passes = 0
		while written < len(cmd):
			to_send = cmd[written:]
			old_written = written

			try:
				result = self._serial.write(to_send)
				if result is None or not isinstance(result, int):
					# probably some plugin not returning the written bytes, assuming all of them
					written += len(cmd)
				else:
					written += result
			except serial.SerialTimeoutException:
				self._log("Serial timeout while writing to serial port, trying again.")
				try:
					result = self._serial.write(to_send)
					if result is None or not isinstance(result, int):
						# probably some plugin not returning the written bytes, assuming all of them
						written += len(cmd)
					else:
						written += result
				except Exception as ex:
					if not self._connection_closing:
						self._logger.exception("Unexpected error while writing to serial port")
						self._log("Unexpected error while writing to serial port: %s" % (get_exception_string()))
						if isinstance(ex, serial.SerialException):
							self._dual_log("Please see https://bit.ly/octoserial for possible reasons of this.",
							               level=logging.ERROR)
						self._errorValue = get_exception_string()
						self.close(is_error=True)
					break
			except Exception as ex:
				if not self._connection_closing:
					self._logger.exception("Unexpected error while writing to serial port")
					self._log("Unexpected error while writing to serial port: %s" % (get_exception_string()))
					if isinstance(ex, serial.SerialException):
						self._dual_log("Please see https://bit.ly/octoserial for possible reasons of this.",
						               level=logging.ERROR)
					self._errorValue = get_exception_string()
					self.close(is_error=True)
				break

			if old_written == written:
				# nothing written this pass
				passes += 1
				if passes > self._max_write_passes:
					# nothing written in max consecutive passes, we give up
					message = "Could not write anything to the serial port in {} tries, something appears to be wrong with the printer communication".format(self._max_write_passes)
					self._dual_log(message, level=logging.ERROR)
					self._errorValue = "Could not write to serial port"
					self.close(is_error=True)
					break

	##~~ command handlers

	def _gcode_T_queuing(self, cmd, cmd_type=None, gcode=None, subcode=None, *args, **kwargs):
		toolMatch = regexes_parameters["intT"].search(cmd)
		if toolMatch:
			current_tool = self._currentTool
			new_tool = int(toolMatch.group("value"))

			before = self._getGcodeScript("beforeToolChange", replacements=dict(tool=dict(old=current_tool, new=new_tool)))
			after = self._getGcodeScript("afterToolChange", replacements=dict(tool=dict(old=current_tool, new=new_tool)))

			return before + [cmd] + after

	def _gcode_T_sent(self, cmd, cmd_type=None, gcode=None, subcode=None, *args, **kwargs):
		toolMatch = regexes_parameters["intT"].search(cmd)
		if toolMatch:
			old = self._currentTool
			self._currentTool = int(toolMatch.group("value"))
			eventManager().fire(Events.TOOL_CHANGE, dict(old=old, new=self._currentTool))

	def _gcode_G0_sent(self, cmd, cmd_type=None, gcode=None, subcode=None, *args, **kwargs):
		if "Z" in cmd or "F" in cmd:
			# track Z
			match = regexes_parameters["floatZ"].search(cmd)
			if match:
				try:
					z = float(match.group("value"))
					if self._currentZ != z:
						self._currentZ = z
						self._callback.on_comm_z_change(z)
				except ValueError:
					pass

			# track F
			match = regexes_parameters["floatF"].search(cmd)
			if match:
				try:
					f = float(match.group("value"))
					self._currentF = f
				except ValueError:
					pass
	_gcode_G1_sent = _gcode_G0_sent

	def _gcode_G28_sent(self, cmd, cmd_type=None, gcode=None, subcode=None, *args, **kwargs):
		if "F" in cmd:
			match = regexes_parameters["floatF"].search(cmd)
			if match:
				try:
					f = float(match.group("value"))
					self._currentF = f
				except ValueError:
					pass

	def _gcode_M0_queuing(self, cmd, cmd_type=None, gcode=None, subcode=None, *args, **kwargs):
		self.setPause(True)
		return None, # Don't send the M0 or M1 to the machine, as M0 and M1 are handled as an LCD menu pause.
	_gcode_M1_queuing = _gcode_M0_queuing

	def _gcode_M25_queuing(self, cmd, cmd_type=None, gcode=None, subcode=None, *args, **kwargs):
		# M25 while not printing from SD will be handled as pause. This way it can be used as another marker
		# for GCODE induced pausing. Send it to the printer anyway though.
		if self.isPrinting() and not self.isSdPrinting():
			self.setPause(True)

	def _gcode_M28_sent(self, cmd, cmd_type=None, gcode=None, subcode=None, *args, **kwargs):
		if not self.isStreaming():
			self._log("Detected manual streaming. Disabling temperature polling. Finish writing with M29. Do NOT attempt to print while manually streaming!")
			self._manualStreaming = True

	def _gcode_M29_sent(self, cmd, cmd_type=None, gcode=None, subcode=None, *args, **kwargs):
		if self._manualStreaming:
			self._log("Manual streaming done. Re-enabling temperature polling. All is well.")
			self._manualStreaming = False

	def _gcode_M140_queuing(self, cmd, cmd_type=None, gcode=None, subcode=None, *args, **kwargs):
		if not self._printerProfileManager.get_current_or_default()["heatedBed"]:
			self._log("Warn: Not sending \"{}\", printer profile has no heated bed".format(cmd))
			return None, # Don't send bed commands if we don't have a heated bed
	_gcode_M190_queuing = _gcode_M140_queuing

	def _gcode_M104_sent(self, cmd, cmd_type=None, gcode=None, subcode=None, wait=False, support_r=False, *args, **kwargs):
		toolNum = self._currentTool
		toolMatch = regexes_parameters["intT"].search(cmd)

		if toolMatch:
			toolNum = int(toolMatch.group("value"))

			if wait:
				self._formerTool = self._currentTool
				self._currentTool = toolNum

		match = regexes_parameters["floatS"].search(cmd)
		if not match and support_r:
			match = regexes_parameters["floatR"].search(cmd)

		if match and self.last_temperature.tools.get(toolNum) is not None:
			try:
				target = float(match.group("value"))
				self.last_temperature.set_tool(toolNum, target=target)
				self._callback.on_comm_temperature_update(self.last_temperature.tools, self.last_temperature.bed)
			except ValueError:
				pass

	def _gcode_M140_sent(self, cmd, cmd_type=None, gcode=None, subcode=None, wait=False, support_r=False, *args, **kwargs):
		match = regexes_parameters["floatS"].search(cmd)
		if not match and support_r:
			match = regexes_parameters["floatR"].search(cmd)

		if match:
			try:
				target = float(match.group("value"))
				self.last_temperature.set_bed(target=target)
				self._callback.on_comm_temperature_update(self.last_temperature.tools, self.last_temperature.bed)
			except ValueError:
				pass

	def _gcode_M109_sent(self, cmd, cmd_type=None, gcode=None, subcode=None, *args, **kwargs):
		self._heatupWaitStartTime = time.time()
		self._long_running_command = True
		self._heating = True
		self._gcode_M104_sent(cmd, cmd_type, wait=True, support_r=True)

	def _gcode_M190_sent(self, cmd, cmd_type=None, gcode=None, subcode=None, *args, **kwargs):
		self._heatupWaitStartTime = time.time()
		self._long_running_command = True
		self._heating = True
		self._gcode_M140_sent(cmd, cmd_type, wait=True, support_r=True)

	def _gcode_M116_sent(self, cmd, cmd_type=None, gcode=None, subcode=None, *args, **kwargs):
		self._heatupWaitStartTime = time.time()
		self._long_running_command = True
		self._heating = True

	def _gcode_M155_sending(self, cmd, cmd_type=None, gcode=None, subcode=None, *args, **kwargs):
		match = regexes_parameters["intS"].search(cmd)
		if match:
			try:
				interval = int(match.group("value"))
				self._temperature_autoreporting = self._firmware_capabilities.get(self.CAPABILITY_AUTOREPORT_TEMP, False) \
				                                  and (interval > 0)
			except:
				pass

	def _gcode_M110_sending(self, cmd, cmd_type=None, gcode=None, subcode=None, *args, **kwargs):
		newLineNumber = 0
		match = regexes_parameters["intN"].search(cmd)
		if match:
			try:
				newLineNumber = int(match.group("value"))
			except:
				pass

		with self._line_mutex:
			self._logger.info("M110 detected, setting current line number to {}".format(newLineNumber))

			# send M110 command with new line number
			self._currentLine = newLineNumber

			# after a reset of the line number we have no way to determine what line exactly the printer now wants
			self._lastLines.clear()
		self._resendDelta = None

	def _gcode_M112_queuing(self, cmd, cmd_type=None, gcode=None, subcode=None, *args, **kwargs):
		# emergency stop, jump the queue with the M112
		self._do_send_without_checksum("M112")
		self._do_increment_and_send_with_checksum("M112")

		# No idea if the printer is still listening or if M112 won. Just in case
		# we'll now try to also manually make sure all heaters are shut off - better
		# safe than sorry. We do this ignoring the queue since at this point it
		# is irrelevant whether the printer has sent enough ack's or not, we
		# are going to shutdown the connection in a second anyhow.
		for tool in range(self._printerProfileManager.get_current_or_default()["extruder"]["count"]):
			self._do_increment_and_send_with_checksum("M104 T{tool} S0".format(tool=tool))
		if self._printerProfileManager.get_current_or_default()["heatedBed"]:
			self._do_increment_and_send_with_checksum("M140 S0")

		# close to reset host state
		self._errorValue = "Closing serial port due to emergency stop M112."
		self._log(self._errorValue)
		self.close(is_error=True)

		# fire the M112 event since we sent it and we're going to prevent the caller from seeing it
		gcode = "M112"
		if gcode in gcodeToEvent:
			eventManager().fire(gcodeToEvent[gcode])

		# return None 1-tuple to eat the one that is queuing because we don't want to send it twice
		# I hope it got it the first time because as far as I can tell, there is no way to know
		return None,

	def _gcode_G4_sent(self, cmd, cmd_type=None, gcode=None, subcode=None, *args, **kwargs):
		# we are intending to dwell for a period of time, increase the timeout to match
		p_match = regexes_parameters["floatP"].search(cmd)
		s_match = regexes_parameters["floatS"].search(cmd)

		_timeout = 0
		if p_match:
			_timeout = float(p_match.group("value")) / 1000.0
		elif s_match:
			_timeout = float(s_match.group("value"))

		self._timeout = get_new_timeout("communication", self._timeout_intervals) + _timeout
		self._dwelling_until = time.time() + _timeout

	##~~ command phase handlers

	def _command_phase_sending(self, cmd, cmd_type=None, gcode=None, subcode=None, *args, **kwargs):
		if gcode is not None and gcode in self._long_running_commands:
			self._long_running_command = True

### MachineCom callback ################################################################################################

class MachineComPrintCallback(object):
	def on_comm_log(self, message):
		pass

	def on_comm_temperature_update(self, temp, bedTemp):
		pass

	def on_comm_position_update(self, position, reason=None):
		pass

	def on_comm_state_change(self, state):
		pass

	def on_comm_message(self, message):
		pass

	def on_comm_progress(self):
		pass

	def on_comm_print_job_started(self):
		pass

	def on_comm_print_job_failed(self):
		pass

	def on_comm_print_job_done(self):
		pass

	def on_comm_print_job_cancelled(self):
		pass

	def on_comm_print_job_paused(self):
		pass

	def on_comm_print_job_resumed(self):
		pass

	def on_comm_z_change(self, newZ):
		pass

	def on_comm_file_selected(self, filename, filesize, sd):
		pass

	def on_comm_sd_state_change(self, sdReady):
		pass

	def on_comm_sd_files(self, files):
		pass

	def on_comm_file_transfer_started(self, filename, filesize):
		pass

	def on_comm_file_transfer_done(self, filename):
		pass

	def on_comm_file_transfer_failed(self, filename):
		pass

	def on_comm_force_disconnect(self):
		pass

	def on_comm_record_fileposition(self, origin, name, pos):
		pass

### Printing file information classes ##################################################################################

class PrintingFileInformation(object):
	"""
	Encapsulates information regarding the current file being printed: file name, current position, total size and
	time the print started.
	Allows to reset the current file position to 0 and to calculate the current progress as a floating point
	value between 0 and 1.
	"""

	checksum = True

	def __init__(self, filename):
		self._logger = logging.getLogger(__name__)
		self._filename = filename
		self._pos = 0
		self._size = None
		self._start_time = None

	def getStartTime(self):
		return self._start_time

	def getFilename(self):
		return self._filename

	def getFilesize(self):
		return self._size

	def getFilepos(self):
		return self._pos

	def getFileLocation(self):
		return FileDestinations.LOCAL

	def getProgress(self):
		"""
		The current progress of the file, calculated as relation between file position and absolute size. Returns -1
		if file size is None or < 1.
		"""
		if self._size is None or not self._size > 0:
			return -1
		return float(self._pos) / float(self._size)

	def reset(self):
		"""
		Resets the current file position to 0.
		"""
		self._pos = 0

	def start(self):
		"""
		Marks the print job as started and remembers the start time.
		"""
		self._start_time = time.time()

	def close(self):
		"""
		Closes the print job.
		"""
		pass

class PrintingSdFileInformation(PrintingFileInformation):
	"""
	Encapsulates information regarding an ongoing print from SD.
	"""

	checksum = False

	def __init__(self, filename, size):
		PrintingFileInformation.__init__(self, filename)
		self._size = size

	def setFilepos(self, pos):
		"""
		Sets the current file position.
		"""
		self._pos = pos

	def getFileLocation(self):
		return FileDestinations.SDCARD

class PrintingGcodeFileInformation(PrintingFileInformation):
	"""
	Encapsulates information regarding an ongoing direct print. Takes care of the needed file handle and ensures
	that the file is closed in case of an error.
	"""

	def __init__(self, filename, offsets_callback=None, current_tool_callback=None):
		PrintingFileInformation.__init__(self, filename)

		self._handle = None
		self._handle_mutex = threading.RLock()

		self._offsets_callback = offsets_callback
		self._current_tool_callback = current_tool_callback

		if not os.path.exists(self._filename) or not os.path.isfile(self._filename):
			raise IOError("File %s does not exist" % self._filename)
		self._size = os.stat(self._filename).st_size
		self._pos = 0
		self._read_lines = 0

	def seek(self, offset):
		with self._handle_mutex:
			if self._handle is None:
				return

			self._handle.seek(offset)
			self._pos = self._handle.tell()
			self._read_lines = 0

	def start(self):
		"""
		Opens the file for reading and determines the file size.
		"""
		PrintingFileInformation.start(self)
		with self._handle_mutex:
			self._handle = bom_aware_open(self._filename, encoding="utf-8", errors="replace")
			self._pos = self._handle.tell()
			if self._handle.encoding.endswith("-sig"):
				# Apparently we found an utf-8 bom in the file.
				# We need to add its length to our pos because it will
				# be stripped transparently and we'll have no chance
				# catching that.
				import codecs
				self._pos += len(codecs.BOM_UTF8)
			self._read_lines = 0

	def close(self):
		"""
		Closes the file if it's still open.
		"""
		PrintingFileInformation.close(self)
		with self._handle_mutex:
			if self._handle is not None:
				try:
					self._handle.close()
				except:
					pass
			self._handle = None

	def getNext(self):
		"""
		Retrieves the next line for printing.
		"""
		with self._handle_mutex:
			if self._handle is None:
				raise ValueError("File %s is not open for reading" % self._filename)

			try:
				offsets = self._offsets_callback() if self._offsets_callback is not None else None
				current_tool = self._current_tool_callback() if self._current_tool_callback is not None else None

				processed = None
				while processed is None:
					if self._handle is None:
						# file got closed just now
						self._pos = self._size
						self._report_stats()
						return None

					# we need to manually keep track of our pos here since
					# codecs' readline will make our handle's tell not
					# return the actual number of bytes read, but also the
					# already buffered bytes (for detecting the newlines)
					line = self._handle.readline()
					self._pos += len(line.encode("utf-8"))

					if not line:
						self.close()
					processed = self._process(line, offsets, current_tool)
				self._read_lines += 1
				return processed
			except Exception as e:
				self.close()
				self._logger.exception("Exception while processing line")
				raise e

	def _process(self, line, offsets, current_tool):
		return process_gcode_line(line, offsets=offsets, current_tool=current_tool)

	def _report_stats(self):
		duration = time.time() - self._start_time
		self._logger.info("Finished in {:.3f} s.".format(duration))
		pass

class StreamingGcodeFileInformation(PrintingGcodeFileInformation):
	def __init__(self, path, localFilename, remoteFilename):
		PrintingGcodeFileInformation.__init__(self, path)
		self._localFilename = localFilename
		self._remoteFilename = remoteFilename

	def start(self):
		PrintingGcodeFileInformation.start(self)
		self._start_time = time.time()

	def getLocalFilename(self):
		return self._localFilename

	def getRemoteFilename(self):
		return self._remoteFilename

	def _process(self, line, offsets, current_tool):
		return process_gcode_line(line)

	def _report_stats(self):
		duration = time.time() - self._start_time
		stats = dict(lines=self._read_lines,
		             rate=float(self._read_lines) / duration,
		             time_per_line=duration * 1000.0 / float(self._read_lines),
		             duration=duration)
		self._logger.info("Finished in {duration:.3f} s. Approx. transfer rate of {rate:.3f} lines/s or {time_per_line:.3f} ms per line".format(**stats))


class SpecialStreamingGcodeFileInformation(StreamingGcodeFileInformation):
	"""
	For streaming files to the printer that aren't GCODE.

	Difference to regular StreamingGcodeFileInformation: no checksum requirement, only rudimentary line processing
	(stripping of whitespace from the end and ignoring of empty lines)
	"""

	checksum = False

	def _process(self, line, offsets, current_tool):
		line = line.rstrip()
		if not len(line):
			return None
		return line


class SendQueue(PrependableQueue):

	def __init__(self, maxsize=0):
		PrependableQueue.__init__(self, maxsize=maxsize)

		self._resend_queue = PrependableQueue()
		self._send_queue = PrependableQueue()
		self._lookup = set()

		self._resend_active = False

	@property
	def resend_active(self):
		return self._resend_active

	@resend_active.setter
	def resend_active(self, resend_active):
		with self.mutex:
			self._resend_active = resend_active

	def prepend(self, item, item_type=None, target=None, block=True, timeout=None):
		PrependableQueue.prepend(self, (item, item_type, target), block=block, timeout=timeout)

	def put(self, item, item_type=None, target=None, block=True, timeout=None):
		PrependableQueue.put(self, (item, item_type, target), block=block, timeout=timeout)

	def get(self, block=True, timeout=None):
		item, _, _ = PrependableQueue.get(self, block=block, timeout=timeout)
		return item

	def _put(self, item):
		_, item_type, target = item
		if item_type is not None:
			if item_type in self._lookup:
				raise TypeAlreadyInQueue(item_type, "Type {} is already in queue".format(item_type))
			else:
				self._lookup.add(item_type)

		if target == "resend":
			self._resend_queue.put(item)
		else:
			self._send_queue.put(item)

		pass

	def _prepend(self, item):
		_, item_type, target = item
		if item_type is not None:
			if item_type in self._lookup:
				raise TypeAlreadyInQueue(item_type, "Type {} is already in queue".format(item_type))
			else:
				self._lookup.add(item_type)

		if target == "resend":
			self._resend_queue.prepend(item)
		else:
			self._send_queue.prepend(item)

	def _get(self):
		if self.resend_active:
			item = self._resend_queue.get(block=False)
		else:
			try:
				item = self._resend_queue.get(block=False)
			except queue.Empty:
				item = self._send_queue.get(block=False)

		_, item_type, _ = item
		if item_type is not None:
			if item_type in self._lookup:
				self._lookup.remove(item_type)

		return item

	def _qsize(self):
		if self.resend_active:
			return self._resend_queue.qsize()
		else:
			return self._resend_queue.qsize() + self._send_queue.qsize()


def get_new_timeout(type, intervals):
	now = time.time()
	return now + intervals.get(type, 0.0)


_temp_command_regex = re.compile("^M(?P<command>104|109|140|190)(\s+T(?P<tool>\d+)|\s+S(?P<temperature>[-+]?\d*\.?\d*))+")

def apply_temperature_offsets(line, offsets, current_tool=None):
	if offsets is None:
		return line

	match = _temp_command_regex.match(line)
	if match is None:
		return line

	groups = match.groupdict()
	if not "temperature" in groups or groups["temperature"] is None:
		return line

	offset = 0
	if current_tool is not None and (groups["command"] == "104" or groups["command"] == "109"):
		# extruder temperature, determine which one and retrieve corresponding offset
		tool_num = current_tool
		if "tool" in groups and groups["tool"] is not None:
			tool_num = int(groups["tool"])

		tool_key = "tool%d" % tool_num
		offset = offsets[tool_key] if tool_key in offsets and offsets[tool_key] else 0

	elif groups["command"] == "140" or groups["command"] == "190":
		# bed temperature
		offset = offsets["bed"] if "bed" in offsets else 0

	if offset == 0:
		return line

	temperature = float(groups["temperature"])
	if temperature == 0:
		return line

	return line[:match.start("temperature")] + "%f" % (temperature + offset) + line[match.end("temperature"):]

def strip_comment(line):
	if not ";" in line:
		# shortcut
		return line

	escaped = False
	result = []
	for c in line:
		if c == ";" and not escaped:
			break
		result += c
		escaped = (c == "\\") and not escaped
	return "".join(result)

def process_gcode_line(line, offsets=None, current_tool=None):
	line = strip_comment(line).strip()
	if not len(line):
		return None

	if offsets is not None:
		line = apply_temperature_offsets(line, offsets, current_tool=current_tool)

	return line

def convert_pause_triggers(configured_triggers):
	if not configured_triggers:
		return dict()

	triggers = {
		"enable": [],
		"disable": [],
		"toggle": []
	}
	for trigger in configured_triggers:
		if not "regex" in trigger or not "type" in trigger:
			continue

		try:
			regex = trigger["regex"]
			t = trigger["type"]
			if t in triggers:
				# make sure regex is valid
				re.compile(regex)
				# add to type list
				triggers[t].append(regex)
		except:
			# invalid regex or something like this, we'll just skip this entry
			pass

	result = dict()
	for t in triggers.keys():
		if len(triggers[t]) > 0:
			result[t] = re.compile("|".join(map(lambda pattern: "({pattern})".format(pattern=pattern), triggers[t])))
	return result


def convert_feedback_controls(configured_controls):
	if not configured_controls:
		return dict(), None

	def preprocess_feedback_control(control, result):
		if "key" in control and "regex" in control and "template" in control:
			# key is always the md5sum of the regex
			key = control["key"]

			if result[key]["pattern"] is None or result[key]["matcher"] is None:
				# regex has not been registered
				try:
					result[key]["matcher"] = re.compile(control["regex"])
					result[key]["pattern"] = control["regex"]
				except Exception as exc:
					logging.getLogger(__name__).warn("Invalid regex {regex} for custom control: {exc}".format(regex=control["regex"], exc=str(exc)))

			result[key]["templates"][control["template_key"]] = control["template"]

		elif "children" in control:
			for c in control["children"]:
				preprocess_feedback_control(c, result)

	def prepare_result_entry():
		return dict(pattern=None, matcher=None, templates=dict())

	from collections import defaultdict
	feedback_controls = defaultdict(prepare_result_entry)

	for control in configured_controls:
		preprocess_feedback_control(control, feedback_controls)

	feedback_pattern = []
	for match_key, entry in feedback_controls.items():
		if entry["matcher"] is None or entry["pattern"] is None:
			continue
		feedback_pattern.append("(?P<group{key}>{pattern})".format(key=match_key, pattern=entry["pattern"]))
	feedback_matcher = re.compile("|".join(feedback_pattern))

	return feedback_controls, feedback_matcher

def canonicalize_temperatures(parsed, current):
	"""
	Canonicalizes the temperatures provided in parsed.

	Will make sure that returned result only contains extruder keys
	like Tn, so always qualified with a tool number.

	The algorithm for cleaning up the parsed keys is the following:

	  * If ``T`` is not included with the reported extruders, return
	  * If more than just ``T`` is reported:
	    * If both ``T`` and ``T0`` are reported, remove ``T`` from
	      the result.
	    * Else set ``T0`` to ``T`` and delete ``T`` (Smoothie extra).
	  * If only ``T`` is reported, set ``Tc`` to ``T`` and delete ``T``
	  * return

	Arguments:
	    parsed (dict): the parsed temperatures (mapping tool => (actual, target))
	      to canonicalize
	    current (int): the current active extruder
	Returns:
	    dict: the canonicalized version of ``parsed``
	"""

	reported_extruders = filter(lambda x: x.startswith("T"), parsed.keys())
	if not "T" in reported_extruders:
		# Our reported_extruders are either empty or consist purely
		# of Tn keys, no need for any action
		return parsed

	current_tool_key = "T%d" % current
	result = dict(parsed)

	if len(reported_extruders) > 1:
		if "T0" in reported_extruders:
			# Both T and T0 are present, let's check if Tc is too.
			# If it is, we just throw away T (it's redundant). It
			# it isn't, we first copy T to Tc, then throw T away.
			#
			# The easier construct would be to always overwrite Tc
			# with T and throw away T, but that assumes that if
			# both are present, T has the same value as Tc. That
			# might not necessarily be the case (weird firmware)
			# so we err on the side of caution here and trust Tc
			# over T.
			if current_tool_key not in reported_extruders:
				# T and T0 are present, but Tc is missing - copy
				# T to Tc
				result[current_tool_key] = result["T"]
			# throw away T, it's redundant (now)
			del result["T"]
		else:
			# So T is there, but T0 isn't. That looks like Smoothieware which
			# always reports the first extruder T0 as T:
			#
			#     T:<T0> T1:<T1> T2:<T2> ... B:<B>
			#
			# becomes
			#
			#     T0:<T0> T1:<T1> T2:<T2> ... B:<B>
			result["T0"] = result["T"]
			del result["T"]

	else:
		# We only have T. That can mean two things:
		#
		#   * we only have one extruder at all, or
		#   * we are currently parsing a response to M109/M190, which on
		#     some firmwares doesn't report the full M105 output while
		#     waiting for the target temperature to be reached but only
		#     reports the current tool and bed
		#
		# In both cases it is however safe to just move our T over
		# to Tc in the parsed data, current should always stay
		# 0 for single extruder printers. E.g. for current_tool == 1:
		#
		#     T:<T1>
		#
		# becomes
		#
		#     T1:<T1>

		result[current_tool_key] = result["T"]
		del result["T"]

	return result

def parse_temperature_line(line, current):
	"""
	Parses the provided temperature line.

	The result will be a dictionary mapping from the extruder or bed key to
	a tuple with current and target temperature. The result will be canonicalized
	with :func:`canonicalize_temperatures` before returning.

	Arguments:
	    line (str): the temperature line to parse
	    current (int): the current active extruder

	Returns:
	    tuple: a 2-tuple with the maximum tool number and a dict mapping from
	      key to (actual, target) tuples, with key either matching ``Tn`` for ``n >= 0`` or ``B``
	"""

	result = {}
	maxToolNum = 0
	for match in re.finditer(regex_temp, line):
		values = match.groupdict()
		tool = values["tool"]
		toolnum = values.get("toolnum", None)
		toolNumber = int(toolnum) if toolnum is not None and len(toolnum) else None
		if toolNumber > maxToolNum:
			maxToolNum = toolNumber

		try:
			actual = float(match.group(3))
			target = None
			if match.group(4) and match.group(5):
				target = float(match.group(5))

			result[tool] = (actual, target)
		except ValueError:
			# catch conversion issues, we'll rather just not get the temperature update instead of killing the connection
			pass

	return max(maxToolNum, current), canonicalize_temperatures(result, current)

def parse_firmware_line(line):
	"""
	Parses the provided firmware info line.

	The result will be a dictionary mapping from the contained keys to the contained
	values.

	Arguments:
	    line (str): the line to parse

	Returns:
	    dict: a dictionary with the parsed data
	"""

	result = dict()
	split_line = regex_firmware_splitter.split(line.strip())[1:] # first entry is empty start of trimmed string
	for key, value in chunks(split_line, 2):
		result[key] = value
	return result

def parse_capability_line(line):
	"""
	Parses the provided firmware capability line.

	Lines are expected to be of the format

	    Cap:<capability name in caps>:<0 or 1>

	e.g.

	    Cap:AUTOREPORT_TEMP:1
	    Cap:TOGGLE_LIGHTS:0

	Args:
		line (str): the line to parse

	Returns:
		tuple: a 2-tuple of the parsed capability name and whether it's on (true) or off (false), or None if the line
		    could not be parsed
	"""

	line = line.lower()
	if line.startswith("cap:"):
		line = line[len("cap:"):]

	parts = line.split(":")
	if len(parts) != 2:
		# wrong format, can't parse this
		return None

	capability, flag = parts
	if not flag in ("0", "1"):
		# wrong format, can't parse this
		return None

	return capability.upper(), flag == "1"

def parse_resend_line(line):
	"""
	Parses the provided resend line and returns requested line number.

	Args:
		line (str): the line to parse

	Returns:
		int or None: the extracted line number to resend, or None if no number could be extracted
	"""

	match = regex_resend_linenumber.search(line)
	if match is not None:
		return int(match.group("n"))

	return None


def gcode_command_for_cmd(cmd):
	"""
	Tries to parse the provided ``cmd`` and extract the GCODE command identifier from it (e.g. "G0" for "G0 X10.0").

	Arguments:
	    cmd (str): The command to try to parse.

	Returns:
	    str or None: The GCODE command identifier if it could be parsed, or None if not.
	"""

	gcode, _ = gcode_and_subcode_for_cmd(cmd)
	return gcode


def gcode_and_subcode_for_cmd(cmd):
	if not cmd:
		return None, None

	match = regex_command.search(cmd)
	if not match:
		return None, None

	values = match.groupdict()
	if "codeGM" in values and values["codeGM"]:
		gcode = values["codeGM"]
	elif "codeT" in values and values["codeT"]:
		gcode = values["codeT"]
	elif settings().getBoolean(["feature", "supportFAsCommand"]) and "codeF" in values and values["codeF"]:
		gcode = values["codeF"]
	else:
		# this should never happen
		return None, None

	return gcode, values.get("subcode", None)


def _normalize_command_handler_result(command, command_type, gcode, subcode, handler_results):
	"""
	Normalizes a command handler result.

	Handler results can be either ``None``, a single result entry or a list of result
	entries.

	``None`` results are ignored, the provided ``command``, ``command_type``,
	``gcode`` and ``subcode`` are returned in that case (as single-entry list with
	one 4-tuple as entry).

	Single result entries are either:

	  * a single string defining a replacement ``command``
	  * a 1-tuple defining a replacement ``command``
	  * a 2-tuple defining a replacement ``command`` and ``command_type``

	A ``command`` that is ``None`` will lead to the entry being ignored for
	the normalized result.

	The method returns a list of normalized result entries. Normalized result
	entries always are a 4-tuple consisting of ``command``, ``command_type``,
	``gcode`` and ``subcode``, the latter three being allowed to be ``None``. The list may
	be empty in which case the command is to be suppressed.

	Examples:
	    >>> _normalize_command_handler_result("M105", None, "M105", None, None)
	    [('M105', None, 'M105', None)]
	    >>> _normalize_command_handler_result("M105", None, "M105", None, "M110")
	    [('M110', None, 'M110', None)]
	    >>> _normalize_command_handler_result("M105", None, "M105", None, ["M110"])
	    [('M110', None, 'M110', None)]
	    >>> _normalize_command_handler_result("M105", None, "M105", None, ["M110", "M117 Foobar"])
	    [('M110', None, 'M110', None), ('M117 Foobar', None, 'M117', None)]
	    >>> _normalize_command_handler_result("M105", None, "M105", None, [("M110",), "M117 Foobar"])
	    [('M110', None, 'M110', None), ('M117 Foobar', None, 'M117', None)]
	    >>> _normalize_command_handler_result("M105", None, "M105", None, [("M110", "lineno_reset"), "M117 Foobar"])
	    [('M110', 'lineno_reset', 'M110', None), ('M117 Foobar', None, 'M117', None)]
	    >>> _normalize_command_handler_result("M105", None, "M105", None, [])
	    []
	    >>> _normalize_command_handler_result("M105", None, "M105", None, ["M110", None])
	    [('M110', None, 'M110', None)]
	    >>> _normalize_command_handler_result("M105", None, "M105", None, [("M110",), (None, "ignored")])
	    [('M110', None, 'M110', None)]
	    >>> _normalize_command_handler_result("M105", None, "M105", None, [("M110",), ("M117 Foobar", "display_message"), ("tuple", "of unexpected", "length"), ("M110", "lineno_reset")])
	    [('M110', None, 'M110', None), ('M117 Foobar', 'display_message', 'M117', None), ('M110', 'lineno_reset', 'M110', None)]

	Arguments:
	    command (str or None): The command for which the handler result was
	        generated
	    command_type (str or None): The command type for which the handler
	        result was generated
	    gcode (str or None): The GCODE for which the handler result was
	        generated
	    subcode (str or None): The GCODE subcode for which the handler result
	        was generated
	    handler_results: The handler result(s) to normalized. Can be either
	        a single result entry or a list of result entries.

	Returns:
	    (list) - A list of normalized handler result entries, which are
	        4-tuples consisting of ``command``, ``command_type``, ``gcode``
	        and ``subcode``, the latter three of which may be ``None``.
	"""

	original = (command, command_type, gcode, subcode)

	if handler_results is None:
		# handler didn't return anything, we'll just continue
		return [original]

	if not isinstance(handler_results, list):
		handler_results = [handler_results,]

	result = []
	for handler_result in handler_results:
		# we iterate over all handler result entries and process each one
		# individually here

		if handler_result is None:
			# entry is None, we'll ignore that entry and continue
			continue

		if isinstance(handler_result, basestring):
			# entry is just a string, replace command with it
			command = handler_result
			gcode, subcode = gcode_and_subcode_for_cmd(command)
			result.append((command, command_type, gcode, subcode))

		elif isinstance(handler_result, tuple):
			# entry is a tuple, extract command and command_type
			hook_result_length = len(handler_result)
			if hook_result_length == 1:
				# handler returned just the command
				command, = handler_result
			elif hook_result_length == 2:
				# handler returned command and command_type
				command, command_type = handler_result
			else:
				# handler returned a tuple of an unexpected length, ignore
				# and continue
				continue

			if command is None:
				# command is None, ignore it and continue
				continue

			gcode, subcode = gcode_and_subcode_for_cmd(command)
			result.append((command, command_type, gcode, subcode))

		# reset to original
		command, command_type, gcode, subcode = original

	return result


# --- Test code for speed testing the comm layer via command line follows


def upload_cli():
	"""
	Usage: python -m octoprint.util.comm <port> <baudrate> <local path> <remote path>

	Uploads <local path> to <remote path> on SD card of printer on port <port>, using baudrate <baudrate>.
	"""

	import sys
	from octoprint.util import Object

	logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
	logger = logging.getLogger(__name__)

	# fetch port, baudrate, filename and target from commandline
	if len(sys.argv) < 5:
		print("Usage: comm.py <port> <baudrate> <local path> <target path>")
		sys.exit(-1)

	port = sys.argv[1]
	baudrate = sys.argv[2]
	path = sys.argv[3]
	target = sys.argv[4]

	# init settings & plugin manager
	settings(init=True)
	octoprint.plugin.plugin_manager(init=True)

	# create dummy callback
	class MyMachineComCallback(MachineComPrintCallback):
		progress_interval = 1

		def __init__(self, path, target):
			self.finished = threading.Event()
			self.finished.clear()

			self.comm = None
			self.error = False
			self.started = False

			self._path = path
			self._target = target

		def on_comm_file_transfer_started(self, filename, filesize):
			# transfer started, report
			logger.info("Started file transfer of {}, size {}B".format(filename, filesize))
			self.started = True

		def on_comm_file_transfer_done(self, filename):
			# transfer done, report, print stats and finish
			logger.info("Finished file transfer of {}".format(filename))
			self.finished.set()

		def on_comm_state_change(self, state):
			if state in (MachineCom.STATE_ERROR, MachineCom.STATE_CLOSED_WITH_ERROR):
				# report and exit on errors
				logger.error("Error/closed with error, exiting.")
				self.error = True
				self.finished.set()

			elif state in (MachineCom.STATE_OPERATIONAL,) and not self.started:
				# start transfer once we are operational
				self.comm.startFileTransfer(self._path, os.path.basename(self._path), self._target)

	callback = MyMachineComCallback(path, target)

	# mock printer profile manager
	profile = dict(heatedBed=False,
	               extruder=dict(count=1))
	printer_profile_manager = Object()
	printer_profile_manager.get_current_or_default = lambda: profile

	# initialize serial
	comm = MachineCom(port=port, baudrate=baudrate, callbackObject=callback, printerProfileManager=printer_profile_manager)
	callback.comm = comm

	# wait for file transfer to finish
	callback.finished.wait()

	# close connection
	comm.close()

	logger.info("Done, exiting...")

if __name__ == "__main__":
	upload_cli()
