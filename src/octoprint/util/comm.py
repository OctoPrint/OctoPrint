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

from octoprint.settings import settings, default_settings
from octoprint.events import eventManager, Events
from octoprint.filemanager import valid_file_type
from octoprint.filemanager.destinations import FileDestinations
from octoprint.util import get_exception_string, sanitize_ascii, filter_non_ascii, CountedEvent, RepeatedTimer, \
	to_unicode, bom_aware_open, TypedQueue, TypeAlreadyInQueue

try:
	import _winreg
except:
	pass

_logger = logging.getLogger(__name__)

# a bunch of regexes we'll need for the communication parsing...

regex_float_pattern = "[-+]?[0-9]*\.?[0-9]+"
regex_positive_float_pattern = "[+]?[0-9]*\.?[0-9]+"
regex_int_pattern = "\d+"

regex_command = re.compile("^\s*((?P<commandGM>[GM]\d+)|(?P<commandT>T)\d+)")
"""Regex for a GCODE command."""

regex_float = re.compile(regex_float_pattern)
"""Regex for a float value."""

regexes_parameters = dict(
	floatP=re.compile("(^|[^A-Za-z])[Pp](?P<value>%s)" % regex_float_pattern),
	floatS=re.compile("(^|[^A-Za-z])[Ss](?P<value>%s)" % regex_float_pattern),
	floatZ=re.compile("(^|[^A-Za-z])[Zz](?P<value>%s)" % regex_float_pattern),
	intN=re.compile("(^|[^A-Za-z])[Nn](?P<value>%s)" % regex_int_pattern),
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

regex_temp = re.compile("(?P<tool>B|T(?P<toolnum>\d*)):\s*(?P<actual>%s)(\s*\/?\s*(?P<target>%s))?" % (regex_positive_float_pattern, regex_positive_float_pattern))
"""Regex matching temperature entries in line.

Groups will be as follows:

  * ``tool``: whole tool designator, incl. optional ``toolnum`` (str)
  * ``toolnum``: tool number, if provided (int)
  * ``actual``: actual temperature (float)
  * ``target``: target temperature, if provided (float)
"""

regex_repetierTempExtr = re.compile("TargetExtr(?P<toolnum>\d+):(?P<target>%s)" % regex_positive_float_pattern)
"""Regex for matching target temp reporting from Repetier.

Groups will be as follows:

  * ``toolnum``: number of the extruder to which the target temperature
    report belongs (int)
  * ``target``: new target temperature (float)
"""

regex_repetierTempBed = re.compile("TargetBed:(?P<target>%s)" % regex_positive_float_pattern)
"""Regex for matching target temp reporting from Repetier for beds.

Groups will be as follows:

  * ``target``: new target temperature (float)
"""

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
		self._temp = {}
		self._bedTemp = None
		self._tempOffsets = dict()
		self._command_queue = TypedQueue()
		self._currentZ = None
		self._heatupWaitStartTime = None
		self._heatupWaitTimeLost = 0.0
		self._pauseWaitStartTime = None
		self._pauseWaitTimeLost = 0.0
		self._currentTool = 0
		self._formerTool = None

		self._long_running_command = False
		self._heating = False
		self._connection_closing = False

		self._timeout = None
		self._timeout_intervals = dict()
		for key, value in settings().get(["serial", "timeout"], merged=True, asdict=True).items():
			try:
				self._timeout_intervals[key] = float(value)
			except:
				pass

		self._hello_command = settings().get(["serial", "helloCommand"])
		self._trigger_ok_for_m29 = settings().getBoolean(["serial", "triggerOkForM29"])

		self._alwaysSendChecksum = settings().getBoolean(["feature", "alwaysSendChecksum"])
		self._sendChecksumWithUnknownCommands = settings().getBoolean(["feature", "sendChecksumWithUnknownCommands"])
		self._unknownCommandsNeedAck = settings().getBoolean(["feature", "unknownCommandsNeedAck"])
		self._currentLine = 1
		self._line_mutex = threading.RLock()
		self._resendDelta = None
		self._lastLines = deque([], 50)
		self._lastCommError = None
		self._lastResendNumber = None
		self._currentResendCount = 0
		self._resendSwallowRepetitions = settings().getBoolean(["feature", "ignoreIdenticalResends"])
		self._resendSwallowRepetitionsCounter = 0

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
		self._send_queue = TypedQueue()
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

		self._printer_action_hooks = self._pluginManager.get_hooks("octoprint.comm.protocol.action")
		self._gcodescript_hooks = self._pluginManager.get_hooks("octoprint.comm.protocol.scripts")
		self._serial_factory_hooks = self._pluginManager.get_hooks("octoprint.comm.transport.serial.factory")

		# SD status data
		self._sdEnabled = settings().getBoolean(["feature", "sdSupport"])
		self._sdAvailable = False
		self._sdFileList = False
		self._sdFiles = []
		self._sdFileToSelect = None
		self._ignore_select = False
		self._manualStreaming = False

		# print job
		self._currentFile = None

		# multithreading locks
		self._sendNextLock = threading.Lock()
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

	##~~ internal state management

	def _changeState(self, newState):
		if self._state == newState:
			return

		if newState == self.STATE_CLOSED or newState == self.STATE_CLOSED_WITH_ERROR:
			if settings().get(["feature", "sdSupport"]):
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
			return "Error: %s" % (self.getErrorString())
		if self._state == self.STATE_CLOSED_WITH_ERROR:
			return "Error: %s" % (self.getErrorString())
		if self._state == self.STATE_TRANSFERING_FILE:
			return "Transfering file to SD"
		return "?%d?" % (self._state)

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
			if not is_error and wait:
				self._logger.info("Waiting for command and send queue to finish processing (timeout={}s)".format(timeout))
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
			payload = None
			if self._currentFile is not None:
				payload = {
					"file": self._currentFile.getFilename(),
					"filename": os.path.basename(self._currentFile.getFilename()),
					"origin": self._currentFile.getFileLocation()
				}
			eventManager().fire(Events.PRINT_FAILED, payload)
		eventManager().fire(Events.DISCONNECTED)

	def setTemperatureOffset(self, offsets):
		self._tempOffsets.update(offsets)

	def fakeOk(self):
		self._handle_ok()

	def sendCommand(self, cmd, cmd_type=None, processed=False, force=False):
		cmd = to_unicode(cmd, errors="replace")
		if not processed:
			cmd = process_gcode_line(cmd)
			if not cmd:
				return

		if self.isPrinting() and not self.isSdFileSelected():
			try:
				self._command_queue.put((cmd, cmd_type), item_type=cmd_type)
			except TypeAlreadyInQueue as e:
				self._logger.debug("Type already in command queue: " + e.type)
		elif self.isOperational() or force:
			self._sendCommand(cmd, cmd_type=cmd_type)

	def sendGcodeScript(self, scriptName, replacements=None):
		context = dict()
		if replacements is not None and isinstance(replacements, dict):
			context.update(replacements)
		context.update(dict(
			printer_profile=self._printerProfileManager.get_current_or_default()
		))

		template = settings().loadScript("gcode", scriptName, context=context)
		if template is None:
			scriptLines = []
		else:
			scriptLines = filter(
				lambda x: x is not None and x.strip() != "",
				map(
					lambda x: process_gcode_line(x, offsets=self._tempOffsets, current_tool=self._currentTool),
					template.split("\n")
				)
			)

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
			self._currentFile.start()

			self._changeState(self.STATE_PRINTING)

			self.resetLineNumbers()

			payload = {
				"file": self._currentFile.getFilename(),
				"filename": os.path.basename(self._currentFile.getFilename()),
				"origin": self._currentFile.getFileLocation()
			}
			eventManager().fire(Events.PRINT_STARTED, payload)
			self.sendGcodeScript("beforePrintStarted", replacements=dict(event=payload))

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

	def startFileTransfer(self, filename, localFilename, remoteFilename):
		if not self.isOperational() or self.isBusy():
			logging.info("Printer is not operation or busy")
			return

		self.resetLineNumbers()

		self._currentFile = StreamingGcodeFileInformation(filename, localFilename, remoteFilename)
		self._currentFile.start()

		self.sendCommand("M28 %s" % remoteFilename)
		eventManager().fire(Events.TRANSFER_STARTED, {"local": localFilename, "remote": remoteFilename})
		self._callback.on_comm_file_transfer_started(remoteFilename, self._currentFile.getFilesize())

	def selectFile(self, filename, sd):
		if self.isBusy():
			return

		if sd:
			if not self.isOperational():
				# printer is not connected, can't use SD
				return
			self._sdFileToSelect = filename
			self.sendCommand("M23 %s" % filename)
		else:
			self._currentFile = PrintingGcodeFileInformation(filename, offsets_callback=self.getOffsets, current_tool_callback=self.getCurrentTool)
			eventManager().fire(Events.FILE_SELECTED, {
				"file": self._currentFile.getFilename(),
				"filename": os.path.basename(self._currentFile.getFilename()),
				"origin": self._currentFile.getFileLocation()
			})
			self._callback.on_comm_file_selected(filename, self._currentFile.getFilesize(), False)

	def unselectFile(self):
		if self.isBusy():
			return

		self._currentFile = None
		eventManager().fire(Events.FILE_DESELECTED)
		self._callback.on_comm_file_selected(None, None, False)

	def cancelPrint(self, firmware_error=None):
		if not self.isOperational() or self.isStreaming():
			return

		if not self.isBusy() or self._currentFile is None:
			# we aren't even printing, nothing to cancel...
			return

		self._changeState(self.STATE_OPERATIONAL)

		if self.isSdFileSelected():
			self.sendCommand("M25")    # pause print
			self.sendCommand("M26 S0") # reset position in file to byte 0
			if self._sd_status_timer is not None:
				try:
					self._sd_status_timer.cancel()
				except:
					pass

		self._recordFilePosition()

		payload = {
			"file": self._currentFile.getFilename(),
			"filename": os.path.basename(self._currentFile.getFilename()),
			"origin": self._currentFile.getFileLocation(),
			"firmwareError": firmware_error
		}

		self.sendGcodeScript("afterPrintCancelled", replacements=dict(event=payload))
		eventManager().fire(Events.PRINT_CANCELLED, payload)

	def setPause(self, pause):
		if self.isStreaming():
			return

		if not self._currentFile:
			return

		payload = {
			"file": self._currentFile.getFilename(),
			"filename": os.path.basename(self._currentFile.getFilename()),
			"origin": self._currentFile.getFileLocation()
		}

		if not pause and self.isPaused():
			if self._pauseWaitStartTime:
				self._pauseWaitTimeLost = self._pauseWaitTimeLost + (time.time() - self._pauseWaitStartTime)
				self._pauseWaitStartTime = None

			self._changeState(self.STATE_PRINTING)

			self.sendGcodeScript("beforePrintResumed", replacements=dict(event=payload))

			if self.isSdFileSelected():
				self.sendCommand("M24")
				self.sendCommand("M27")
			else:
				line = self._getNext()
				if line is not None:
					self.sendCommand(line)

			# now make sure we actually do something, up until now we only filled up the queue
			self._sendFromQueue()

			eventManager().fire(Events.PRINT_RESUMED, payload)
		elif pause and self.isPrinting():
			if not self._pauseWaitStartTime:
				self._pauseWaitStartTime = time.time()

			self._changeState(self.STATE_PAUSED)
			if self.isSdFileSelected():
				self.sendCommand("M25") # pause print
			self.sendGcodeScript("afterPrintPaused", replacements=dict(event=payload))

			eventManager().fire(Events.PRINT_PAUSED, payload)

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
		if settings().getBoolean(["feature", "sdAlwaysAvailable"]):
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

	def _recordFilePosition(self):
		if self._currentFile is None:
			return

		origin = self._currentFile.getFileLocation()
		filename = self._currentFile.getFilename()
		pos = self._currentFile.getFilepos()

		self._callback.on_comm_record_fileposition(origin, filename, pos)

	##~~ communication monitoring and handling

	def _processTemperatures(self, line):
		current_tool = self._currentTool if self._currentTool is not None else 0
		maxToolNum, parsedTemps = parse_temperature_line(line, current_tool)

		if "T0" in parsedTemps.keys():
			for n in range(maxToolNum + 1):
				tool = "T%d" % n
				if not tool in parsedTemps.keys():
					continue

				actual, target = parsedTemps[tool]
				if target is not None:
					self._temp[n] = (actual, target)
				elif n in self._temp and self._temp[n] is not None and isinstance(self._temp[n], tuple):
					(oldActual, oldTarget) = self._temp[n]
					self._temp[n] = (actual, oldTarget)
				else:
					self._temp[n] = (actual, None)

		# bed temperature
		if "B" in parsedTemps.keys():
			actual, target = parsedTemps["B"]
			if target is not None:
				self._bedTemp = (actual, target)
			elif self._bedTemp is not None and isinstance(self._bedTemp, tuple):
				(oldActual, oldTarget) = self._bedTemp
				self._bedTemp = (actual, oldTarget)
			else:
				self._bedTemp = (actual, None)

	##~~ Serial monitor processing received messages

	def _monitor(self):
		feedback_controls, feedback_matcher = convert_feedback_controls(settings().get(["controls"]))
		feedback_errors = []
		pause_triggers = convert_pause_triggers(settings().get(["printerParameters", "pauseTriggers"]))

		disable_external_heatup_detection = not settings().getBoolean(["feature", "externalHeatupDetection"])

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
			try:
				line = self._readline()
				if line is None:
					break
				if line.strip() is not "":
					self._timeout = get_new_timeout("communication", self._timeout_intervals)

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
					stripped_line = line.strip()
					return stripped_line, stripped_line.lower()

				##~~ Error handling
				line = self._handleErrors(line)
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
					handled = (line == "wait" or line == "ok" or not ("T:" in line or "T0:" in line or "B:" in line or "C:" in line))

				# process resends
				elif lower_line.startswith("resend") or lower_line.startswith("rs"):
					self._handleResendRequest(line)
					handled = True

				# process timeouts
				elif line == "" and time.time() > self._timeout:
					# timeout only considered handled if the printer is printing
					self._handle_timeout()
					handled = self.isPrinting()

				# we don't have to process the rest if the line has already been handled fully
				if handled and self._state not in (self.STATE_CONNECTING, self.STATE_DETECT_BAUDRATE):
					continue

				##~~ Temperature processing
				if ' T:' in line or line.startswith('T:') or ' T0:' in line or line.startswith('T0:') or ' B:' in line or line.startswith('B:'):
					if not disable_external_heatup_detection and not line.strip().startswith("ok") and not self._heating:
						self._logger.debug("Externally triggered heatup detected")
						self._heating = True
						self._heatupWaitStartTime = time.time()
					self._processTemperatures(line)
					self._callback.on_comm_temperature_update(self._temp, self._bedTemp)

				elif supportRepetierTargetTemp and ('TargetExtr' in line or 'TargetBed' in line):
					matchExtr = regex_repetierTempExtr.match(line)
					matchBed = regex_repetierTempBed.match(line)

					if matchExtr is not None:
						toolNum = int(matchExtr.group(1))
						try:
							target = float(matchExtr.group(2))
							if toolNum in self._temp.keys() and self._temp[toolNum] is not None and isinstance(self._temp[toolNum], tuple):
								(actual, oldTarget) = self._temp[toolNum]
								self._temp[toolNum] = (actual, target)
							else:
								self._temp[toolNum] = (None, target)
							self._callback.on_comm_temperature_update(self._temp, self._bedTemp)
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
							self._callback.on_comm_temperature_update(self._temp, self._bedTemp)
						except ValueError:
							pass

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
					if self._sdFileToSelect:
						name = self._sdFileToSelect
						self._sdFileToSelect = None
					else:
						name = match.group("name")
					self._currentFile = PrintingSdFileInformation(name, int(match.group("size")))
				elif 'File selected' in line:
					if self._ignore_select:
						self._ignore_select = False
					elif self._currentFile is not None and self.isSdFileSelected():
						# final answer to M23, at least on Marlin, Repetier and Sprinter: "File selected"
						self._callback.on_comm_file_selected(self._currentFile.getFilename(), self._currentFile.getFilesize(), True)
						eventManager().fire(Events.FILE_SELECTED, {
							"file": self._currentFile.getFilename(),
							"origin": self._currentFile.getFileLocation()
						})
				elif 'Writing to file' in line and self.isStreaming():
					self._changeState(self.STATE_PRINTING)
				elif 'Done printing file' in line and self.isSdPrinting():
					# printer is reporting file finished printing
					self._sdFilePos = 0
					self._callback.on_comm_print_job_done()
					self._changeState(self.STATE_OPERATIONAL)
					eventManager().fire(Events.PRINT_DONE, {
						"file": self._currentFile.getFilename(),
						"filename": os.path.basename(self._currentFile.getFilename()),
						"origin": self._currentFile.getFileLocation(),
						"time": self.getPrintTime()
					})
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
				elif line != '' \
						and not line.startswith("ok") \
						and not line.startswith("wait") \
						and not line.startswith('Resend:') \
						and line != 'echo:Unknown command:""\n' \
						and self.isOperational():
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
							self.close()
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
					elif line.startswith("ok"):
						self._onConnected()
					elif time.time() > self._timeout:
						self.close()

			except:
				self._logger.exception("Something crashed inside the serial connection loop, please report this in OctoPrint's bug tracker:")

				errorMsg = "See octoprint.log for details"
				self._log(errorMsg)
				self._errorValue = errorMsg
				self._changeState(self.STATE_ERROR)
				eventManager().fire(Events.ERROR, {"error": self.getErrorString()})
		self._log("Connection closed, closing down monitor")

	def _handle_ok(self):
		self._clear_to_send.set()

		# reset long running commands, persisted current tools and heatup counters on ok

		self._long_running_command = False

		if self._formerTool is not None:
			self._currentTool = self._formerTool
			self._formerTool = None

		if self._heatupWaitStartTime:
			self._heatupWaitTimeLost = self._heatupWaitTimeLost + (time.time() - self._heatupWaitStartTime)
			self._heatupWaitStartTime = None
			self._heating = False

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
		if self._state not in (self.STATE_PRINTING,):
			return

		if self._long_running_command:
			self._logger.debug("Ran into a communication timeout, but a command known to be a long runner is currently active")
			return

		general_message = "Configure long running commands or increase communication timeout if that happens regularly on specific commands or long moves."
		if self._resendActive:
			self._log("Communication timeout while printing and during an active resend, resending same line again to trigger response from printer. " + general_message)
			self._resendSameCommand()
			self._clear_to_send.set()

		else:
			self._log("Communication timeout while printing, trying to trigger response from printer. " + general_message)
			self._sendCommand("M105", cmd_type="temperature")
			self._clear_to_send.set()

		return

	def _continue_sending(self):
		if self._state == self.STATE_PRINTING:
			if not self._sendFromQueue() and not self.isSdPrinting():
				self._sendNext()
		elif self._state == self.STATE_OPERATIONAL or self._state == self.STATE_PAUSED:
			self._sendFromQueue()

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

		If the printer is not operational, closing the connection, not printing from sd, busy with a long running
		command or heating, no poll will be done.
		"""

		if self.isOperational() and not self._connection_closing and not self.isStreaming() and not self._long_running_command and not self._heating and not self._manualStreaming:
			self.sendCommand("M105", cmd_type="temperature_poll")

	def _poll_sd_status(self):
		"""
		Polls the sd printing status after the sd status timeout, re-enqueues itself.

		If the printer is not operational, closing the connection, not printing from sd, busy with a long running
		command or heating, no poll will be done.
		"""

		if self.isOperational() and not self._connection_closing and self.isSdPrinting() and not self._long_running_command and not self._heating:
			self.sendCommand("M27", cmd_type="sd_status_poll")

	def _onConnected(self):
		self._serial.timeout = settings().getFloat(["serial", "timeout", "communication"])
		self._temperature_timer = RepeatedTimer(self._timeout_intervals.get("temperature", 4.0), self._poll_temperature, run_first=True)
		self._temperature_timer.start()

		self._changeState(self.STATE_OPERATIONAL)

		self.resetLineNumbers()

		if self._sdAvailable:
			self.refreshSdFiles()
		else:
			self.initSdCard()

		payload = dict(port=self._port, baudrate=self._baudrate)
		eventManager().fire(Events.CONNECTED, payload)
		self.sendGcodeScript("afterPrinterConnected", replacements=dict(event=payload))

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
					if not len(entry) == 2:
						# something with that entry is broken, ignore it and fetch
						# the next one
						continue
					cmd, cmd_type = entry
				else:
					cmd = entry
					cmd_type = None

				if self._sendCommand(cmd, cmd_type=cmd_type):
					# we actually did add this cmd to the send queue, so let's
					# return, we are done here
					return True
			finally:
				self._command_queue.task_done()

	def _detectPort(self, close):
		programmer = stk500v2.Stk500v2()
		self._log("Serial port list: %s" % (str(serialList())))
		for p in serialList():
			serial_obj = None

			try:
				self._log("Connecting to: %s" % (p))
				programmer.connect(p)
				serial_obj = programmer.leaveISP()
			except ispBase.IspError as (e):
				error_message = "Error while connecting to %s: %s" % (p, str(e))
				self._log(error_message)
				self._logger.exception(error_message)
			except:
				error_message = "Unexpected error while connecting to serial port: %s %s" % (p, get_exception_string())
				self._log(error_message)
				self._logger.exception(error_message)
			if serial_obj is not None:
				if (close):
					serial_obj.close()
				return serial_obj

			programmer.close()
		return None

	def _openSerial(self):
		def default(_, port, baudrate, read_timeout):
			if port is None or port == 'AUTO':
				# no known port, try auto detection
				self._changeState(self.STATE_DETECT_SERIAL)
				serial_obj = self._detectPort(True)
				if serial_obj is None:
					self._errorValue = 'Failed to autodetect serial port, please set it manually.'
					self._changeState(self.STATE_ERROR)
					eventManager().fire(Events.ERROR, {"error": self.getErrorString()})
					self._log("Failed to autodetect serial port, please set it manually.")
					return None

				port = serial_obj.port

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

	def _handleErrors(self, line):
		if line is None:
			return

		lower_line = line.lower()

		# No matter the state, if we see an error, goto the error state and store the error for reference.
		if lower_line.startswith('error:') or line.startswith('!!'):
			#Oh YEAH, consistency.
			# Marlin reports an MIN/MAX temp error as "Error:x\n: Extruder switched off. MAXTEMP triggered !\n"
			#	But a bed temp error is reported as "Error: Temperature heated bed switched off. MAXTEMP triggered !!"
			#	So we can have an extra newline in the most common case. Awesome work people.
			if regex_minMaxError.match(line):
				line = line.rstrip() + self._readline()

			if 'line number' in lower_line or 'checksum' in lower_line or 'format error' in lower_line or 'expected line' in lower_line:
				#Skip the communication errors, as those get corrected.
				self._lastCommError = line[6:] if lower_line.startswith("error:") else line[2:]
				pass
			elif 'volume.init' in lower_line or "openroot" in lower_line or 'workdir' in lower_line\
					or "error writing to file" in lower_line or "cannot open" in lower_line\
					or "cannot enter" in lower_line:
				#Also skip errors with the SD card
				pass
			elif 'unknown command' in lower_line:
				#Ignore unkown command errors, it could be a typo or some missing feature
				pass
			elif not self.isError():
				error_text = line[6:] if lower_line.startswith("error:") else line[2:]
				self._to_logfile_with_terminal("Received an error from the printer's firmware: {}".format(error_text), level=logging.WARN)
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
		return line

	def _readline(self):
		if self._serial is None:
			return None

		try:
			ret = self._serial.readline()
		except:
			if not self._connection_closing:
				self._logger.exception("Unexpected error while reading from serial port")
				self._log("Unexpected error while reading serial port, please consult octoprint.log for details: %s" % (get_exception_string()))
				self._errorValue = get_exception_string()
				self.close(True)
			return None

		if ret != "":
			try:
				self._log("Recv: " + sanitize_ascii(ret))
			except ValueError as e:
				self._log("WARN: While reading last line: %s" % e)
				self._log("Recv: " + repr(ret))

		return ret

	def _getNext(self):
		if self._currentFile is None:
			return None

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
				self._callback.on_comm_file_transfer_done(remote)
				eventManager().fire(Events.TRANSFER_DONE, payload)
				self.refreshSdFiles()
			else:
				payload = {
					"file": self._currentFile.getFilename(),
					"filename": os.path.basename(self._currentFile.getFilename()),
					"origin": self._currentFile.getFileLocation(),
					"time": self.getPrintTime()
				}
				self._callback.on_comm_print_job_done()
				self._changeState(self.STATE_OPERATIONAL)
				eventManager().fire(Events.PRINT_DONE, payload)

				self.sendGcodeScript("afterPrintDone", replacements=dict(event=payload))
		return line

	def _sendNext(self):
		with self._sendNextLock:
			line = self._getNext()
			if line is not None:
				self._sendCommand(line)
				self._callback.on_comm_progress()

	def _handleResendRequest(self, line):
		try:
			lineToResend = None
			try:
				lineToResend = int(line.replace("N:", " ").replace("N", " ").replace(":", " ").split()[-1])
			except:
				if "rs" in line:
					lineToResend = int(line.split()[1])

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
				self._logger.debug("Ignoring resend request for line %d == current line, we haven't sent that yet so the printer got N-1 twice from us, probably due to a timeout" % lineToResend)
				return False

			lastCommError = self._lastCommError
			self._lastCommError = None

			resendDelta = self._currentLine - lineToResend

			if lastCommError is not None \
					and ("line number" in lastCommError.lower() or "expected line" in lastCommError.lower()) \
					and lineToResend == self._lastResendNumber \
					and self._resendDelta is not None and self._currentResendCount < self._resendDelta:
				self._logger.debug("Ignoring resend request for line %d, that still originates from lines we sent before we got the first resend request" % lineToResend)
				self._currentResendCount += 1
				return True

			# If we ignore resend repetitions (Repetier firmware...), check if we
			# need to do this now. If the same line number has been requested we
			# already saw and resent, we'll ignore it up to <counter> times.
			if self._resendSwallowRepetitions and lineToResend == self._lastResendNumber and self._resendSwallowRepetitionsCounter > 0:
				self._logger.debug("Ignoring resend request for line %d, that is probably a repetition sent by the firmware to ensure it arrives, not a real request" % lineToResend)
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

			return True
		finally:
			if self._supportResendsWithoutOk:
				# simulate an ok if our flags indicate that the printer needs that for resend requests to work
				self._handle_ok()

	def _resendSameCommand(self):
		self._resendNextCommand(again=True)

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

			self._enqueue_for_sending(cmd, linenumber=lineNumber)

			self._resendDelta -= 1
			if self._resendDelta <= 0:
				self._resendDelta = None
				self._lastResendNumber = None
				self._currentResendCount = 0

	def _sendCommand(self, cmd, cmd_type=None):
		# Make sure we are only handling one sending job at a time
		with self._sendingLock:
			if self._serial is None:
				return False

			gcode = None

			# trigger the "queuing" phase only if we are not streaming to sd right now
			cmd, cmd_type, gcode = self._process_command_phase("queuing", cmd, cmd_type, gcode=gcode)

			if cmd is None:
				# command is no more, return
				return False

			if not self.isStreaming() and gcode and gcode in gcodeToEvent:
				# if this is a gcode bound to an event, trigger that now
				eventManager().fire(gcodeToEvent[gcode])

			# actually enqueue the command for sending
			self._enqueue_for_sending(cmd, command_type=cmd_type)

			self._process_command_phase("queued", cmd, cmd_type, gcode=gcode)

			return True

	##~~ send loop handling

	def _enqueue_for_sending(self, command, linenumber=None, command_type=None):
		"""
		Enqueues a command an optional linenumber to use for it in the send queue.

		Arguments:
		    command (str): The command to send.
		    linenumber (int): The line number with which to send the command. May be ``None`` in which case the command
		        will be sent without a line number and checksum.
		"""

		try:
			self._send_queue.put((command, linenumber, command_type), item_type=command_type)
		except TypeAlreadyInQueue as e:
			self._logger.debug("Type already in send queue: " + e.type)

	def _send_loop(self):
		"""
		The send loop is reponsible of sending commands in ``self._send_queue`` over the line, if it is cleared for
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

					# fetch command and optional linenumber from queue
					command, linenumber, command_type = entry

					# some firmwares (e.g. Smoothie) might support additional in-band communication that will not
					# stick to the acknowledgement behaviour of GCODE, so we check here if we have a GCODE command
					# at hand here and only clear our clear_to_send flag later if that's the case
					gcode = gcode_command_for_cmd(command)

					if linenumber is not None:
						# line number predetermined - this only happens for resends, so we'll use the number and
						# send directly without any processing (since that already took place on the first sending!)
						self._do_send_with_checksum(command, linenumber)

					else:
						# trigger "sending" phase
						command, _, gcode = self._process_command_phase("sending", command, command_type, gcode=gcode)

						if command is None:
							# No, we are not going to send this, that was a last-minute bail.
							# However, since we already are in the send queue, our _monitor
							# loop won't be triggered with the reply from this unsent command
							# now, so we try to tickle the processing of any active
							# command queues manually
							self._continue_sending()

							# and now let's fetch the next item from the queue
							continue

						# now comes the part where we increase line numbers and send stuff - no turning back now
						command_requiring_checksum = gcode is not None and gcode in self._checksum_requiring_commands
						command_allowing_checksum = gcode is not None or self._sendChecksumWithUnknownCommands
						checksum_enabled = self.isPrinting() or self._alwaysSendChecksum

						command_to_send = command.encode("ascii", errors="replace")
						if command_requiring_checksum or (command_allowing_checksum and checksum_enabled):
							self._do_increment_and_send_with_checksum(command_to_send)
						else:
							self._do_send_without_checksum(command_to_send)

					# trigger "sent" phase and use up one "ok"
					self._process_command_phase("sent", command, command_type, gcode=gcode)

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

	def _process_command_phase(self, phase, command, command_type=None, gcode=None):
		if self.isStreaming() or phase not in ("queuing", "queued", "sending", "sent"):
			return command, command_type, gcode

		if gcode is None:
			gcode = gcode_command_for_cmd(command)

		# send it through the phase specific handlers provided by plugins
		for name, hook in self._gcode_hooks[phase].items():
			try:
				hook_result = hook(self, phase, command, command_type, gcode)
			except:
				self._logger.exception("Error while processing hook {name} for phase {phase} and command {command}:".format(**locals()))
			else:
				command, command_type, gcode = self._handle_command_handler_result(command, command_type, gcode, hook_result)
				if command is None:
					# hook handler return None as command, so we'll stop here and return a full out None result
					return None, None, None

		# if it's a gcode command send it through the specific handler if it exists
		if gcode is not None:
			gcodeHandler = "_gcode_" + gcode + "_" + phase
			if hasattr(self, gcodeHandler):
				handler_result = getattr(self, gcodeHandler)(command, cmd_type=command_type)
				command, command_type, gcode = self._handle_command_handler_result(command, command_type, gcode, handler_result)

		# send it through the phase specific command handler if it exists
		commandPhaseHandler = "_command_phase_" + phase
		if hasattr(self, commandPhaseHandler):
			handler_result = getattr(self, commandPhaseHandler)(command, cmd_type=command_type, gcode=gcode)
			command, command_type, gcode = self._handle_command_handler_result(command, command_type, gcode, handler_result)

		# finally return whatever we resulted on
		return command, command_type, gcode

	def _handle_command_handler_result(self, command, command_type, gcode, handler_result):
		original_tuple = (command, command_type, gcode)

		if handler_result is None:
			# handler didn't return anything, we'll just continue
			return original_tuple

		if isinstance(handler_result, basestring):
			# handler did return just a string, we'll turn that into a 1-tuple now
			handler_result = (handler_result,)
		elif not isinstance(handler_result, (tuple, list)):
			# handler didn't return an expected result format, we'll just ignore it and continue
			return original_tuple

		hook_result_length = len(handler_result)
		if hook_result_length == 1:
			# handler returned just the command
			command, = handler_result
		elif hook_result_length == 2:
			# handler returned command and command_type
			command, command_type = handler_result
		else:
			# handler returned a tuple of an unexpected length
			return original_tuple

		gcode = gcode_command_for_cmd(command)
		return command, command_type, gcode

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
		for c in command_to_send:
			checksum ^= ord(c)
		command_to_send = command_to_send + "*" + str(checksum)
		self._do_send_without_checksum(command_to_send)

	def _do_send_without_checksum(self, cmd):
		if self._serial is None:
			return

		self._log("Send: " + str(cmd))
		try:
			self._serial.write(cmd + '\n')
		except serial.SerialTimeoutException:
			self._log("Serial timeout while writing to serial port, trying again.")
			try:
				self._serial.write(cmd + '\n')
			except:
				if not self._connection_closing:
					self._logger.exception("Unexpected error while writing to serial port")
					self._log("Unexpected error while writing to serial port: %s" % (get_exception_string()))
					self._errorValue = get_exception_string()
					self.close(is_error=True)
		except:
			if not self._connection_closing:
				self._logger.exception("Unexpected error while writing to serial port")
				self._log("Unexpected error while writing to serial port: %s" % (get_exception_string()))
				self._errorValue = get_exception_string()
				self.close(is_error=True)

	##~~ command handlers

	def _gcode_T_sent(self, cmd, cmd_type=None):
		toolMatch = regexes_parameters["intT"].search(cmd)
		if toolMatch:
			self._currentTool = int(toolMatch.group("value"))

	def _gcode_G0_sent(self, cmd, cmd_type=None):
		if 'Z' in cmd:
			match = regexes_parameters["floatZ"].search(cmd)
			if match:
				try:
					z = float(match.group("value"))
					if self._currentZ != z:
						self._currentZ = z
						self._callback.on_comm_z_change(z)
				except ValueError:
					pass
	_gcode_G1_sent = _gcode_G0_sent

	def _gcode_M0_queuing(self, cmd, cmd_type=None):
		self.setPause(True)
		return None, # Don't send the M0 or M1 to the machine, as M0 and M1 are handled as an LCD menu pause.
	_gcode_M1_queuing = _gcode_M0_queuing

	def _gcode_M25_queuing(self, cmd, cmd_type=None):
		# M25 while not printing from SD will be handled as pause. This way it can be used as another marker
		# for GCODE induced pausing. Send it to the printer anyway though.
		if self.isPrinting() and not self.isSdPrinting():
			self.setPause(True)

	def _gcode_M28_sent(self, cmd, cmd_type=None):
		if not self.isStreaming():
			self._log("Detected manual streaming. Disabling temperature polling. Finish writing with M29. Do NOT attempt to print while manually streaming!")
			self._manualStreaming = True

	def _gcode_M29_sent(self, cmd, cmd_type=None):
		if self._manualStreaming:
			self._log("Manual streaming done. Re-enabling temperature polling. All is well.")
			self._manualStreaming = False

	def _gcode_M140_queuing(self, cmd, cmd_type=None):
		if not self._printerProfileManager.get_current_or_default()["heatedBed"]:
			self._log("Warn: Not sending \"{}\", printer profile has no heated bed".format(cmd))
			return None, # Don't send bed commands if we don't have a heated bed
	_gcode_M190_queuing = _gcode_M140_queuing

	def _gcode_M104_sent(self, cmd, cmd_type=None, wait=False):
		toolNum = self._currentTool
		toolMatch = regexes_parameters["intT"].search(cmd)

		if toolMatch:
			toolNum = int(toolMatch.group("value"))

			if wait:
				self._formerTool = self._currentTool
				self._currentTool = toolNum

		match = regexes_parameters["floatS"].search(cmd)
		if match:
			try:
				target = float(match.group("value"))
				if toolNum in self._temp.keys() and self._temp[toolNum] is not None and isinstance(self._temp[toolNum], tuple):
					(actual, oldTarget) = self._temp[toolNum]
					self._temp[toolNum] = (actual, target)
				else:
					self._temp[toolNum] = (None, target)
			except ValueError:
				pass

	def _gcode_M140_sent(self, cmd, cmd_type=None, wait=False):
		match = regexes_parameters["floatS"].search(cmd)
		if match:
			try:
				target = float(match.group("value"))
				if self._bedTemp is not None and isinstance(self._bedTemp, tuple):
					(actual, oldTarget) = self._bedTemp
					self._bedTemp = (actual, target)
				else:
					self._bedTemp = (None, target)
			except ValueError:
				pass

	def _gcode_M109_sent(self, cmd, cmd_type=None):
		self._heatupWaitStartTime = time.time()
		self._long_running_command = True
		self._heating = True
		self._gcode_M104_sent(cmd, cmd_type, wait=True)

	def _gcode_M190_sent(self, cmd, cmd_type=None):
		self._heatupWaitStartTime = time.time()
		self._long_running_command = True
		self._heating = True
		self._gcode_M140_sent(cmd, cmd_type, wait=True)

	def _gcode_M110_sending(self, cmd, cmd_type=None):
		newLineNumber = None
		match = regexes_parameters["intN"].search(cmd)
		if match:
			try:
				newLineNumber = int(match.group("value"))
			except:
				pass
		else:
			newLineNumber = 0

		with self._line_mutex:
			# send M110 command with new line number
			self._currentLine = newLineNumber

			# after a reset of the line number we have no way to determine what line exactly the printer now wants
			self._lastLines.clear()
		self._resendDelta = None

	def _gcode_M112_queuing(self, cmd, cmd_type=None):
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

	def _gcode_G4_sent(self, cmd, cmd_type=None):
		# we are intending to dwell for a period of time, increase the timeout to match
		p_match = regexes_parameters["floatP"].search(cmd)
		s_match = regexes_parameters["floatS"].search(cmd)

		_timeout = 0
		if p_match:
			_timeout = float(p_match.group("value")) / 1000.0
		elif s_match:
			_timeout = float(s_match.group("value"))
		self._timeout = get_new_timeout("communication", self._timeout_intervals) + _timeout

	##~~ command phase handlers

	def _command_phase_sending(self, cmd, cmd_type=None, gcode=None):
		if gcode is not None and gcode in self._long_running_commands:
			self._long_running_command = True

### MachineCom callback ################################################################################################

class MachineComPrintCallback(object):
	def on_comm_log(self, message):
		pass

	def on_comm_temperature_update(self, temp, bedTemp):
		pass

	def on_comm_state_change(self, state):
		pass

	def on_comm_message(self, message):
		pass

	def on_comm_progress(self):
		pass

	def on_comm_print_job_done(self):
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

		self._offsets_callback = offsets_callback
		self._current_tool_callback = current_tool_callback

		if not os.path.exists(self._filename) or not os.path.isfile(self._filename):
			raise IOError("File %s does not exist" % self._filename)
		self._size = os.stat(self._filename).st_size
		self._pos = 0
		self._read_lines = 0

	def seek(self, offset):
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
		self._read_lines = 0
		self._handle = bom_aware_open(self._filename, encoding="utf-8", errors="replace")

	def close(self):
		"""
		Closes the file if it's still open.
		"""
		PrintingFileInformation.close(self)
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
				line = to_unicode(self._handle.readline())
				if not line:
					self.close()
				processed = self._process(line, offsets, current_tool)
			self._pos = self._handle.tell()
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
	    * If both ``T`` and ``T0`` are reported set ``Tc`` to ``T``, remove
	      ``T`` from the result.
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
			# Both T and T0 are present, so T contains the current
			# extruder's temperature, e.g. for current_tool == 1:
			#
			#     T:<T1> T0:<T0> T2:<T2> ... B:<B>
			#
			# becomes
			#
			#     T0:<T1> T1:<T1> T2:<T2> ... B:<B>
			#
			# Same goes if Tc is already present, it will be overwritten:
			#
			#     T:<T1> T0:<T0> T1:<T1> T2:<T2> ... B:<B>
			#
			# becomes
			#
			#     T0:<T0> T1:<T1> T2:<T2> ... B:<B>
			result[current_tool_key] = result["T"]
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
		# to T<current> in the parsed data, current should always stay
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

def gcode_command_for_cmd(cmd):
	"""
	Tries to parse the provided ``cmd`` and extract the GCODE command identifier from it (e.g. "G0" for "G0 X10.0").

	Arguments:
	    cmd (str): The command to try to parse.

	Returns:
	    str or None: The GCODE command identifier if it could be parsed, or None if not.
	"""
	if not cmd:
		return None

	gcode = regex_command.search(cmd)
	if not gcode:
		return None

	values = gcode.groupdict()
	if "commandGM" in values and values["commandGM"]:
		return values["commandGM"]
	elif "commandT" in values and values["commandT"]:
		return values["commandT"]
	else:
		# this should never happen
		return None


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
