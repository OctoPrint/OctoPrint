# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


import io
import time
import os
import re
import threading
import math
try:
	import queue
except ImportError:
	import Queue as queue

# noinspection PyCompatibility
from past.builtins import basestring

from serial import SerialTimeoutException

from octoprint.plugin import plugin_manager
from octoprint.util import RepeatedTimer, monotonic_time, to_bytes, to_unicode

from typing import Any


# noinspection PyBroadException
class VirtualPrinter(object):
	command_regex = re.compile(r"^([GMTF])(\d+)")
	sleep_regex = re.compile(r"sleep (\d+)")
	sleep_after_regex = re.compile(r"sleep_after ([GMTF]\d+) (\d+)")
	sleep_after_next_regex = re.compile(r"sleep_after_next ([GMTF]\d+) (\d+)")
	custom_action_regex = re.compile(r"action_custom ([a-zA-Z0-9_]+)(\s+.*)?")
	prepare_ok_regex = re.compile(r"prepare_ok (.*)")
	send_regex = re.compile(r"send (.*)")
	set_ambient_regex = re.compile(r"set_ambient ([-+]?[0-9]*\.?[0-9]+)")
	start_sd_regex = re.compile(r"start_sd (.*)")
	select_sd_regex = re.compile(r"select_sd (.*)")

	def __init__(self, settings, seriallog_handler=None, read_timeout=5.0, write_timeout=10.0, faked_baudrate=115200):
		import logging
		self._logger = logging.getLogger("octoprint.plugins.virtual_printer.VirtualPrinter")

		self._settings = settings
		self._faked_baudrate = faked_baudrate

		self._seriallog = logging.getLogger("octoprint.plugin.virtual_printer.VirtualPrinter.serial")
		self._seriallog.setLevel(logging.CRITICAL)
		self._seriallog.propagate = False

		if seriallog_handler is not None:
			import logging.handlers
			self._seriallog.addHandler(seriallog_handler)
			self._seriallog.setLevel(logging.INFO)

		self._seriallog.info(u"-"*78)

		self._read_timeout = read_timeout
		self._write_timeout = write_timeout

		self._rx_buffer_size = self._settings.get_int(["rxBuffer"])

		self.incoming = CharCountingQueue(self._rx_buffer_size, name="RxBuffer")
		self.outgoing = queue.Queue()
		self.buffered = queue.Queue(maxsize=self._settings.get_int(["commandBuffer"]))

		if self._settings.get_boolean(["simulateReset"]):
			for item in self._settings.get(["resetLines"]):
				self._send(item + "\n")

		self._prepared_oks = []
		prepared = self._settings.get(["preparedOks"])
		if prepared and isinstance(prepared, list):
			for prep in prepared:
				self._prepared_oks.append(prep)

		self._prepared_errors = []

		self._errors = self._settings.get(["errors"], merged=True)

		self.currentExtruder = 0
		self.extruderCount = self._settings.get_int(["numExtruders"])
		self.pinnedExtruders = self._settings.get(["pinnedExtruders"])
		if self.pinnedExtruders is None:
			self.pinnedExtruders = dict()
		self.sharedNozzle = self._settings.get_boolean(["sharedNozzle"])
		self.temperatureCount = (1 if self.sharedNozzle else self.extruderCount)

		self._ambient_temperature = self._settings.get_float(["ambientTemperature"])

		self.temp = [self._ambient_temperature] * self.temperatureCount
		self.targetTemp = [0.0] * self.temperatureCount
		self.bedTemp = self._ambient_temperature
		self.bedTargetTemp = 0.0
		self.chamberTemp = self._ambient_temperature
		self.chamberTargetTemp = 0.0
		self.lastTempAt = monotonic_time()

		self._relative = True
		self._lastX = 0.0
		self._lastY = 0.0
		self._lastZ = 0.0
		self._lastE = [0.0] * self.extruderCount
		self._lastF = 200

		self._unitModifier = 1
		self._feedrate_multiplier = 100
		self._flowrate_multiplier = 100

		self._virtualSd = self._settings.global_get_basefolder("virtualSd")
		self._sdCardReady = True
		self._sdPrinter = None
		self._sdPrintingSemaphore = threading.Event()
		self._selectedSdFile = None
		self._selectedSdFileSize = None
		self._selectedSdFilePos = None

		self._writingToSd = False
		self._writingToSdHandle = None
		self._newSdFilePos = None

		self._heatingUp = False

		self._okBeforeCommandOutput = self._settings.get_boolean(["okBeforeCommandOutput"])
		self._supportM112 = self._settings.get_boolean(["supportM112"])
		self._supportF = self._settings.get_boolean(["supportF"])

		self._sendWait = self._settings.get_boolean(["sendWait"])
		self._sendBusy = self._settings.get_boolean(["sendBusy"])
		self._waitInterval = self._settings.get_float(["waitInterval"])
		self._busyInterval = self._settings.get_float(["busyInterval"])

		self._echoOnM117 = self._settings.get_boolean(["echoOnM117"])

		self._brokenM29 = self._settings.get_boolean(["brokenM29"])
		self._brokenResend = self._settings.get_boolean(["brokenResend"])

		self._m115FormatString = self._settings.get(["m115FormatString"])
		self._firmwareName = self._settings.get(["firmwareName"])

		self._okFormatString = self._settings.get(["okFormatString"])

		self._capabilities = self._settings.get(["capabilities"], merged=True)

		self._temperature_reporter = None
		self._sdstatus_reporter = None

		self.current_line = 0
		self.lastN = 0

		self._incoming_lock = threading.RLock()

		self._debug_awol = False
		self._debug_sleep = 0
		self._sleepAfterNext = dict()
		self._sleepAfter = dict()
		self._rerequest_last = False

		self._dont_answer = False

		self._debug_drop_connection = False

		self._action_hooks = plugin_manager().get_hooks("octoprint.plugin.virtual_printer.custom_action")

		self._killed = False

		self._triggerResendAt100 = True
		self._triggerResendWithTimeoutAt105 = True
		self._triggerResendWithMissingLinenoAt110 = True
		self._triggerResendWithChecksumMismatchAt115 = True

		readThread = threading.Thread(target=self._processIncoming, name="octoprint.plugins.virtual_printer.wait_thread")
		readThread.start()

		bufferThread = threading.Thread(target=self._processBuffer, name="octoprint.plugins.virtual_printer.buffer_thread")
		bufferThread.start()

	def __str__(self):
		return "VIRTUAL(read_timeout={read_timeout},write_timeout={write_timeout},options={options})"\
			.format(read_timeout=self._read_timeout, write_timeout=self._write_timeout, options=self._settings.get([]))

	def _reset(self):
		with self._incoming_lock:
			self._relative = True
			self._lastX = 0.0
			self._lastY = 0.0
			self._lastZ = 0.0
			self._lastE = [0.0] * self.extruderCount
			self._lastF = 200

			self._unitModifier = 1
			self._feedrate_multiplier = 100
			self._flowrate_multiplier = 100

			self._sdCardReady = True
			self._sdPrinting = False
			if self._sdPrinter:
				self._sdPrinting = False
				self._sdPrintingSemaphore.set()
			self._sdPrinter = None
			self._selectedSdFile = None
			self._selectedSdFileSize = None
			self._selectedSdFilePos = None

			if self._writingToSdHandle:
				try:
					self._writingToSdHandle.close()
				except Exception:
					pass
			self._writingToSd = False
			self._writingToSdHandle = None
			self._newSdFilePos = None

			self._heatingUp = False

			self.current_line = 0
			self.lastN = 0

			self._debug_awol = False
			self._debug_sleep = 0
			self._sleepAfterNext.clear()
			self._sleepAfter.clear()

			self._dont_answer = False

			self._debug_drop_connection = False

			self._killed = False

			self._triggerResendAt100 = True
			self._triggerResendWithTimeoutAt105 = True
			self._triggerResendWithMissingLinenoAt110 = True
			self._triggerResendWithChecksumMismatchAt115 = True

			if self._temperature_reporter is not None:
				self._temperature_reporter.cancel()
				self._temperature_reporter = None

			if self._sdstatus_reporter is not None:
				self._sdstatus_reporter.cancel()
				self._sdstatus_reporter = None

			self._clearQueue(self.incoming)
			self._clearQueue(self.outgoing)
			self._clearQueue(self.buffered)

			if self._settings.get_boolean(["simulateReset"]):
				for item in self._settings.get(["resetLines"]):
					self._send(item + "\n")

	@property
	def timeout(self):
		return self._read_timeout

	@timeout.setter
	def timeout(self, value):
		self._logger.debug("Setting read timeout to {}s".format(value))
		self._read_timeout = value

	@property
	def write_timeout(self):
		return self._write_timeout

	@write_timeout.setter
	def write_timeout(self, value):
		self._logger.debug("Setting write timeout to {}s".format(value))
		self._write_timeout = value

	@property
	def port(self):
		return "VIRTUAL"

	@property
	def baudrate(self):
		return self._faked_baudrate

	# noinspection PyMethodMayBeStatic
	def _clearQueue(self, q):
		try:
			while q.get(block=False):
				q.task_done()
				continue
		except queue.Empty:
			pass

	def _processIncoming(self):
		next_wait_timeout = monotonic_time() + self._waitInterval
		buf = b""
		while self.incoming is not None and not self._killed:
			self._simulateTemps()

			if self._heatingUp:
				time.sleep(1)
				continue

			try:
				data = self.incoming.get(timeout=0.01)
				data = to_bytes(data, encoding="ascii", errors="replace")
				self.incoming.task_done()
			except queue.Empty:
				if self._sendWait and monotonic_time() > next_wait_timeout:
					self._send("wait")
					next_wait_timeout = monotonic_time() + self._waitInterval
				continue
			except Exception:
				if self.incoming is None:
					# just got closed
					break

			if data is not None:
				buf += data
				nl = buf.find(b"\n")+1
				if nl > 0:
					data = buf[:nl]
					buf = buf[nl:]
				else:
					continue

			next_wait_timeout = monotonic_time() + self._waitInterval

			if data is None:
				continue

			if self._dont_answer:
				self._dont_answer = False
				continue

			# strip checksum
			if b"*" in data:
				checksum = int(data[data.rfind(b"*") + 1:])
				data = data[:data.rfind(b"*")]
				if not checksum == self._calculate_checksum(data):
					self._triggerResend(expected=self.current_line + 1)
					continue

				self.current_line += 1
			elif self._settings.get_boolean(["forceChecksum"]):
				self._send(self._error("checksum_missing"))
				continue

			# track N = N + 1
			if data.startswith(b"N") and b"M110" in data:
				linenumber = int(re.search(b"N([0-9]+)", data).group(1))
				self.lastN = linenumber
				self.current_line = linenumber

				self._triggerResendAt100 = True
				self._triggerResendWithTimeoutAt105 = True

				self._sendOk()
				continue
			elif data.startswith(b"N"):
				linenumber = int(re.search(b"N([0-9]+)", data).group(1))
				expected = self.lastN + 1
				if linenumber != expected:
					self._triggerResend(actual=linenumber)
					continue
				elif linenumber == 100 and self._triggerResendAt100:
					# simulate a resend at line 100
					self._triggerResendAt100 = False
					self._triggerResend(expected=100)
					continue
				elif linenumber == 105 and self._triggerResendWithTimeoutAt105 and not self._writingToSd:
					# simulate a resend with timeout at line 105
					self._triggerResendWithTimeoutAt105 = False
					self._triggerResend(expected=105)
					self._dont_answer = True
					self.lastN = linenumber
					continue
				elif linenumber == 110 and self._triggerResendWithMissingLinenoAt110 and not self._writingToSd:
					self._triggerResendWithMissingLinenoAt110 = False
					self._send(self._error("lineno_missing", self.lastN))
					continue
				elif linenumber == 115 and self._triggerResendWithChecksumMismatchAt115 and not self._writingToSd:
					self._triggerResendWithChecksumMismatchAt115 = False
					self._triggerResend(checksum=True)
					continue
				elif len(self._prepared_errors):
					prepared = self._prepared_errors.pop(0)
					# noinspection PyCompatibility
					if callable(prepared):
						prepared(linenumber, self.lastN, data)
						continue
					elif isinstance(prepared, basestring):
						self._send(prepared)
						continue
				elif self._rerequest_last:
					self._triggerResend(actual=linenumber)
					continue
				else:
					self.lastN = linenumber
				data = data.split(None, 1)[1].strip()

			data += b"\n"

			data = to_unicode(data, encoding="ascii", errors="replace").strip()

			if data.startswith("!!DEBUG:") or data.strip() == "!!DEBUG":
				debug_command = ""
				if data.startswith("!!DEBUG:"):
					debug_command = data[len("!!DEBUG:"):].strip()
				self._debugTrigger(debug_command)
				continue

			# shortcut for writing to SD
			if self._writingToSd and self._writingToSdHandle is not None and not "M29" in data:
				self._writingToSdHandle.write(data)
				self._sendOk()
				continue

			if data.strip() == "version":
				from octoprint import __version__
				self._send("OctoPrint VirtualPrinter v" + __version__)
				continue

			# if we are sending oks before command output, send it now
			if len(data.strip()) > 0 and self._okBeforeCommandOutput:
				self._sendOk()

			# actual command handling
			command_match = VirtualPrinter.command_regex.match(data)
			if command_match is not None:
				command = command_match.group(0)
				letter = command_match.group(1)

				try:
					# if we have a method _gcode_G, _gcode_M or _gcode_T, execute that first
					letter_handler = "_gcode_{}".format(letter)
					if hasattr(self, letter_handler):
						code = command_match.group(2)
						handled = getattr(self, letter_handler)(code, data)
						if handled:
							continue

					# then look for a method _gcode_<command> and execute that if it exists
					command_handler = "_gcode_{}".format(command)
					if hasattr(self, command_handler):
						handled = getattr(self, command_handler)(data)
						if handled:
							continue

				finally:
					# make sure that the debug sleepAfter and sleepAfterNext stuff works even
					# if we continued above
					if len(self._sleepAfter) or len(self._sleepAfterNext):
						interval = None
						if command in self._sleepAfter:
							interval = self._sleepAfter[command]
						elif command in self._sleepAfterNext:
							interval = self._sleepAfterNext[command]
							del self._sleepAfterNext[command]

						if interval is not None:
							self._send("// sleeping for {interval} seconds".format(interval=interval))
							time.sleep(interval)

			# if we are sending oks after command output, send it now
			if len(data.strip()) > 0 and not self._okBeforeCommandOutput:
				self._sendOk()

		self._logger.info("Closing down read loop")

	##~~ command implementations

	# noinspection PyUnusedLocal
	def _gcode_T(self, code, data):
		# type: (str, str) -> None
		t = int(code)
		if 0 <= t < self.extruderCount:
			self.currentExtruder = t
			self._send("Active Extruder: %d" % self.currentExtruder)
		else:
			self._send("echo:T{} Invalid extruder ".format(t))

	# noinspection PyUnusedLocal
	def _gcode_F(self, code, data):
		# type: (str, str) -> bool
		if self._supportF:
			self._send("echo:changed F value")
			return False
		else:
			self._send(self._error("command_unknown", "F"))
			return True

	def _gcode_M104(self, data):
		# type: (str) -> None
		self._parseHotendCommand(data)

	def _gcode_M109(self, data):
		# type: (str) -> None
		self._parseHotendCommand(data, wait=True, support_r=True)

	def _gcode_M140(self, data):
		# type: (str) -> None
		self._parseBedCommand(data)

	def _gcode_M190(self, data):
		# type: (str) -> None
		self._parseBedCommand(data, wait=True, support_r=True)

	def _gcode_M141(self, data):
		self._parseChamberCommand(data)

	def _gcode_M191(self, data):
		self._parseChamberCommand(data, wait=True, support_r=True)

	# noinspection PyUnusedLocal
	def _gcode_M105(self, data):
		# type: (str) -> bool
		self._processTemperatureQuery()
		return True

	# noinspection PyUnusedLocal
	def _gcode_M20(self, data):
		# type: (str) -> None
		if self._sdCardReady:
			self._listSd()

	# noinspection PyUnusedLocal
	def _gcode_M21(self, data):
		# type: (str) -> None
		self._sdCardReady = True
		self._send("SD card ok")

	# noinspection PyUnusedLocal
	def _gcode_M22(self, data):
		# type: (str) -> None
		self._sdCardReady = False

	def _gcode_M23(self, data):
		# type: (str) -> None
		if self._sdCardReady:
			filename = data.split(None, 1)[1].strip()
			self._selectSdFile(filename)

	# noinspection PyUnusedLocal
	def _gcode_M24(self, data):
		# type: (str) -> None
		if self._sdCardReady:
			self._startSdPrint()

	# noinspection PyUnusedLocal
	def _gcode_M25(self, data):
		# type: (str) -> None
		if self._sdCardReady:
			self._pauseSdPrint()

	def _gcode_M26(self, data):
		# type: (str) -> None
		if self._sdCardReady:
			pos = int(re.search(r"S([0-9]+)", data).group(1))
			self._setSdPos(pos)

	def _gcode_M27(self, data):
		# type: (str) -> None
		def report():
			if self._sdCardReady:
				self._reportSdStatus()

		matchS = re.search(r"S([0-9]+)", data)
		if matchS:
			interval = int(matchS.group(1))
			if self._sdstatus_reporter is not None:
				self._sdstatus_reporter.cancel()

			if interval > 0:
				self._sdstatus_reporter = RepeatedTimer(interval, report)
				self._sdstatus_reporter.start()
			else:
				self._sdstatus_reporter = None

		report()

	def _gcode_M28(self, data):
		# type: (str) -> None
		if self._sdCardReady:
			filename = data.split(None, 1)[1].strip()
			self._writeSdFile(filename)

	# noinspection PyUnusedLocal
	def _gcode_M29(self, data):
		# type: (str) -> None
		if self._sdCardReady:
			self._finishSdFile()

	def _gcode_M30(self, data):
		# type: (str) -> None
		if self._sdCardReady:
			filename = data.split(None, 1)[1].strip()
			self._deleteSdFile(filename)

	def _gcode_M113(self, data):
		# type: (str) -> None
		matchS = re.search(r"S([0-9]+)", data)
		if matchS is not None:
			interval = int(matchS.group(1))
			if 0 <= interval <= 60:
				self._busyInterval = interval

	# noinspection PyUnusedLocal
	def _gcode_M114(self, data):
		# type: (str) -> bool
		m114FormatString = self._settings.get(["m114FormatString"])
		e = dict((index, value) for index, value in enumerate(self._lastE))
		e["current"] = self._lastE[self.currentExtruder]
		e["all"] = " ".join(["E{}:{}".format(num, self._lastE[self.currentExtruder]) for num in range(self.extruderCount)])
		output = m114FormatString.format(x=self._lastX,
										 y=self._lastY,
										 z=self._lastZ,
										 e=e,
										 f=self._lastF,
										 a=int(self._lastX*100),
										 b=int(self._lastY*100),
										 c=int(self._lastZ*100))

		if not self._okBeforeCommandOutput:
			ok = self._ok()
			if ok:
				output = "{} {}".format(self._ok(), output)
		self._send(output)
		return True

	# noinspection PyUnusedLocal
	def _gcode_M115(self, data):
		# type: (str) -> None
		output = self._m115FormatString.format(firmware_name=self._firmwareName)
		self._send(output)

		if self._settings.get_boolean(["m115ReportCapabilities"]):
			for cap, enabled in self._capabilities.items():
				self._send("Cap:{}:{}".format(cap.upper(), "1" if enabled else "0"))

	def _gcode_M117(self, data):
		# type: (str) -> None
		# we'll just use this to echo a message, to allow playing around with pause triggers
		if self._echoOnM117:
			self._send("echo:%s" % re.search(r"M117\s+(.*)", data).group(1))

	def _gcode_M155(self, data):
		# type: (str) -> None
		matchS = re.search(r"S([0-9]+)", data)
		if matchS is not None:
			interval = int(matchS.group(1))
			if self._temperature_reporter is not None:
				self._temperature_reporter.cancel()

			if interval > 0:
				self._temperature_reporter = RepeatedTimer(interval, lambda: self._send(self._generateTemperatureOutput()))
				self._temperature_reporter.start()
			else:
				self._temperature_reporter = None

	def _gcode_M220(self, data):
		# type: (str) -> None
		matchS = re.search(r"S([0-9]+)", data)
		if matchS is not None:
			self._feedrate_multiplier = float(matchS.group(1))

	def _gcode_M221(self, data):
		# type: (str) -> None
		matchS = re.search(r"S([0-9]+)", data)
		if matchS is not None:
			self._flowrate_multiplier = float(matchS.group(1))

	# noinspection PyUnusedLocal
	def _gcode_M400(self, data):
		# type: (str) -> None
		self.buffered.join()

	# noinspection PyUnusedLocal
	def _gcode_M999(self, data):
		# type: (str) -> None
		# mirror Marlin behaviour
		self._send("Resend: 1")

	# noinspection PyUnusedLocal
	def _gcode_G20(self, data):
		# type: (str) -> None
		self._unitModifier = 1.0 / 2.54
		if self._lastX is not None:
			self._lastX *= 2.54
		if self._lastY is not None:
			self._lastY *= 2.54
		if self._lastZ is not None:
			self._lastZ *= 2.54
		if self._lastE is not None:
			self._lastE = [e * 2.54 if e is not None else None for e in self._lastE]

	# noinspection PyUnusedLocal
	def _gcode_G21(self, data):
		# type: (str) -> None
		self._unitModifier = 1.0
		if self._lastX is not None:
			self._lastX /= 2.54
		if self._lastY is not None:
			self._lastY /= 2.54
		if self._lastZ is not None:
			self._lastZ /= 2.54
		if self._lastE is not None:
			self._lastE = [e / 2.54 if e is not None else None for e in self._lastE]

	# noinspection PyUnusedLocal
	def _gcode_G90(self, data):
		# type: (str) -> None
		self._relative = False

	# noinspection PyUnusedLocal
	def _gcode_G91(self, data):
		# type: (str) -> None
		self._relative = True

	def _gcode_G92(self, data):
		# type: (str) -> None
		self._setPosition(data)

	def _gcode_G28(self, data):
		# type: (str) -> None
		self._home(data)

	def _gcode_G0(self, data):
		# type: (str) -> None
		# simulate reprap buffered commands via a Queue with maxsize which internally simulates the moves
		self.buffered.put(data)
	_gcode_G1 = _gcode_G0
	_gcode_G2 = _gcode_G0
	_gcode_G3 = _gcode_G0

	def _gcode_G4(self, data):
		# type: (str) -> None
		matchS = re.search(r'S([0-9]+)', data)
		matchP = re.search(r'P([0-9]+)', data)

		_timeout = 0
		if matchP:
			_timeout = float(matchP.group(1)) / 1000.0
		elif matchS:
			_timeout = float(matchS.group(1))

		if self._sendBusy and self._busyInterval > 0:
			until = monotonic_time() + _timeout
			while monotonic_time() < until:
				time.sleep(self._busyInterval)
				self._send("busy:processing")
		else:
			time.sleep(_timeout)

	# noinspection PyUnusedLocal
	def _gcode_G33(self, data):
		# type: (str) -> None
		self._send("G33 Auto Calibrate")
		self._send("Will take ~60s")
		timeout = 60

		if self._sendBusy and self._busyInterval > 0:
			until = monotonic_time() + timeout
			while monotonic_time() < until:
				time.sleep(self._busyInterval)
				self._send("busy:processing")
		else:
			time.sleep(timeout)

	##~~ further helpers

	# noinspection PyMethodMayBeStatic
	def _calculate_checksum(self, line):
		# type: (bytes) -> int
		checksum = 0
		for c in bytearray(line):
			checksum ^= c
		return checksum

	def _kill(self):
		if not self._supportM112:
			return
		self._killed = True
		self._send("echo:EMERGENCY SHUTDOWN DETECTED. KILLED.")

	def _triggerResend(self, expected=None, actual=None, checksum=None):
		# type: (int, int, int) -> None
		with self._incoming_lock:
			if expected is None:
				expected = self.lastN + 1
			else:
				self.lastN = expected - 1

			if actual is None:
				if checksum:
					self._send(self._error("checksum_mismatch"))
				else:
					self._send(self._error("checksum_missing"))
			else:
				self._send(self._error("lineno_mismatch", expected, actual))

			def request_resend():
				self._send("Resend:%d" % expected)
				if not self._brokenResend:
					self._sendOk()

			request_resend()

	def _debugTrigger(self, data):
		# type: (str) -> None
		if data == "" or data == "help" or data == "?":
			usage = """
			OctoPrint Virtual Printer debug commands

			help
			?
			| This help.

			# Action Triggers

			action_pause
			| Sends a "// action:pause" action trigger to the host.
			action_resume
			| Sends a "// action:resume" action trigger to the host.
			action_disconnect
			| Sends a "// action:disconnect" action trigger to the
			| host.
			action_custom <action>[ <parameters>]
			| Sends a custom "// action:<action> <parameters>"
			| action trigger to the host.

			# Communication Errors

			dont_answer
			| Will not acknowledge the next command.
			go_awol
			| Will completely stop replying
			trigger_resend_lineno
			| Triggers a resend error with a line number mismatch
			trigger_resend_checksum
			| Triggers a resend error with a checksum mismatch
			trigger_missing_checksum
			| Triggers a resend error with a missing checksum
			trigger_missing_lineno
			| Triggers a "no line number with checksum" error w/o resend request
			trigger_fatal_error_marlin
			| Triggers a fatal error/simulated heater fail, Marlin style
			trigger_fatal_error_repetier
			| Triggers a fatal error/simulated heater fail, Repetier style
			drop_connection
			| Drops the serial connection
			prepare_ok <broken ok>
			| Will cause <broken ok> to be enqueued for use,
			| will be used instead of actual "ok"
			rerequest_last
			| Will cause the last line number + 1 to be rerequest add infinitum

			# Reply Timing / Sleeping

			sleep <int:seconds>
			| Sleep <seconds> s
			sleep_after <str:command> <int:seconds>
			| Sleeps <seconds> s after each execution of <command>
			sleep_after_next <str:command> <int:seconds>
			| Sleeps <seconds> s after execution of next <command>

			# SD printing

			start_sd <str:file>
			| Select and start printing file <file> from SD
			select_sd <str:file>
			| Select file <file> from SD, don't start printing it yet. Use
			| start_sd to start the print
			cancel_sd
			| Cancels an ongoing SD print

			# Misc

			send <str:message>
			| Sends back <message>
			reset
			| Simulates a reset. Internal state will be lost.
			"""
			for line in usage.split("\n"):
				self._send("echo: {}".format(line.strip()))
		elif data == "action_pause":
			self._send("// action:pause")
		elif data == "action_resume":
			self._send("// action:resume")
		elif data == "action_disconnect":
			self._send("// action:disconnect")
		elif data == "dont_answer":
			self._dont_answer = True
		elif data == "trigger_resend_lineno":
			self._prepared_errors.append(lambda cur, last, ln: self._triggerResend(expected=last, actual=last+1))
		elif data == "trigger_resend_checksum":
			self._prepared_errors.append(lambda cur, last, ln: self._triggerResend(expected=last, checksum=True))
		elif data == "trigger_missing_checksum":
			self._prepared_errors.append(lambda cur, last, ln: self._triggerResend(expected=last, checksum=False))
		elif data == "trigger_missing_lineno":
			self._prepared_errors.append(lambda cur, last, ln: self._send(self._error("lineno_missing", last)))
		elif data == "trigger_fatal_error_marlin":
			self._send("Error:Thermal Runaway, system stopped! Heater_ID: bed")
			self._send("Error:Printer halted. kill() called!")
		elif data == "trigger_fatal_error_repetier":
			self._send("fatal: Heater/sensor error - Printer stopped and heaters disabled due to this error. Fix error and restart with M999.")
		elif data == "drop_connection":
			self._debug_drop_connection = True
		elif data == "reset":
			self._reset()
		elif data == "mintemp_error":
			self._send(self._error("mintemp"))
		elif data == "maxtemp_error":
			self._send(self._error("maxtemp"))
		elif data == "go_awol":
			self._send("// Going AWOL")
			self._debug_awol = True
		elif data == "rerequest_last":
			self._send("// Entering rerequest loop")
			self._rerequest_last = True
		elif data == "cancel_sd":
			if self._sdPrinting and self._sdPrinter:
				self._pauseSdPrint()
				self._sdPrinting = False
				self._sdPrintingSemaphore.set()
				self._sdPrinter.join()
				self._finishSdPrint()
		else:
			try:
				sleep_match = VirtualPrinter.sleep_regex.match(data)
				sleep_after_match = VirtualPrinter.sleep_after_regex.match(data)
				sleep_after_next_match = VirtualPrinter.sleep_after_next_regex.match(data)
				custom_action_match = VirtualPrinter.custom_action_regex.match(data)
				prepare_ok_match = VirtualPrinter.prepare_ok_regex.match(data)
				send_match = VirtualPrinter.send_regex.match(data)
				set_ambient_match = VirtualPrinter.set_ambient_regex.match(data)
				start_sd_match = VirtualPrinter.start_sd_regex.match(data)
				select_sd_match = VirtualPrinter.select_sd_regex.match(data)

				if sleep_match is not None:
					interval = int(sleep_match.group(1))
					self._send("// sleeping for {interval} seconds".format(interval=interval))
					self._debug_sleep = interval
				elif sleep_after_match is not None:
					command = sleep_after_match.group(1)
					interval = int(sleep_after_match.group(2))
					self._sleepAfter[command] = interval
					self._send("// going to sleep {interval} seconds after each {command}".format(**locals()))
				elif sleep_after_next_match is not None:
					command = sleep_after_next_match.group(1)
					interval = int(sleep_after_next_match.group(2))
					self._sleepAfterNext[command] = interval
					self._send("// going to sleep {interval} seconds after next {command}".format(**locals()))
				elif custom_action_match is not None:
					action = custom_action_match.group(1)
					params = custom_action_match.group(2)
					params = params.strip() if params is not None else ""
					self._send("// action:{action} {params}".format(**locals()).strip())
				elif prepare_ok_match is not None:
					ok = prepare_ok_match.group(1)
					self._prepared_oks.append(ok)
				elif send_match is not None:
					self._send(send_match.group(1))
				elif set_ambient_match is not None:
					self._ambient_temperature = float(set_ambient_match.group(1))
					self._send("// set ambient temperature to {}".format(self._ambient_temperature))
				elif start_sd_match is not None:
					self._selectSdFile(start_sd_match.group(1), check_already_open=True)
					self._startSdPrint()
				elif select_sd_match is not None:
					self._selectSdFile(select_sd_match.group(1))
			except Exception:
				self._logger.exception("While handling %r", data)

	def _listSd(self):
		self._send("Begin file list")
		if self._settings.get_boolean(["extendedSdFileList"]):
			items = map(
				lambda x: "%s %d" % (x.upper(), os.stat(os.path.join(self._virtualSd, x)).st_size),
				os.listdir(self._virtualSd)
			)
		else:
			items = map(
				lambda x: x.upper(),
				os.listdir(self._virtualSd)
			)
		for item in items:
			self._send(item)
		self._send("End file list")

	def _selectSdFile(self, filename, check_already_open=False):
		# type: (str, bool) -> None
		if filename.startswith("/"):
			filename = filename[1:]

		file = os.path.join(self._virtualSd, filename.lower())
		if self._selectedSdFile == file and check_already_open:
			return

		if not os.path.exists(file) or not os.path.isfile(file):
			self._send("open failed, File: %s." % filename)
		else:
			self._selectedSdFile = file
			self._selectedSdFileSize = os.stat(file).st_size
			if self._settings.get_boolean(["includeFilenameInOpened"]):
				self._send("File opened: %s  Size: %d" % (filename, self._selectedSdFileSize))
			else:
				self._send("File opened")
			self._send("File selected")

	def _startSdPrint(self):
		if self._selectedSdFile is not None:
			if self._sdPrinter is None:
				self._sdPrinting = True
				self._sdPrinter = threading.Thread(target=self._sdPrintingWorker)
				self._sdPrinter.start()
		self._sdPrintingSemaphore.set()

	def _pauseSdPrint(self):
		self._sdPrintingSemaphore.clear()

	def _setSdPos(self, pos):
		self._newSdFilePos = pos

	def _reportSdStatus(self):
		if self._sdPrinter is not None and self._sdPrintingSemaphore.is_set:
			self._send("SD printing byte %d/%d" % (self._selectedSdFilePos, self._selectedSdFileSize))
		else:
			self._send("Not SD printing")

	def _generateTemperatureOutput(self):
		# type: () -> str
		includeTarget = not self._settings.get_boolean(["repetierStyleTargetTemperature"])

		# send simulated temperature data
		if self.temperatureCount > 1:
			allTemps = []
			for i in range(len(self.temp)):
				allTemps.append((i, self.temp[i], self.targetTemp[i]))
			allTempsString = " ".join(map(lambda x: "T%d:%.2f /%.2f" % x if includeTarget else "T%d:%.2f" % (x[0], x[1]), allTemps))

			if self._settings.get_boolean(["smoothieTemperatureReporting"]):
				allTempsString = allTempsString.replace("T0:", "T:")

			if self._settings.get_boolean(["hasBed"]):
				if includeTarget:
					allTempsString = "B:%.2f /%.2f %s" % (self.bedTemp, self.bedTargetTemp, allTempsString)
				else:
					allTempsString = "B:%.2f %s" % (self.bedTemp, allTempsString)

			if self._settings.get_boolean(["hasChamber"]):
				if includeTarget:
					allTempsString = "C:%.2f /%.2f %s" % (self.chamberTemp, self.chamberTargetTemp, allTempsString)
				else:
					allTempsString = "C:%.2f %s" % (self.chamberTemp, allTempsString)

			if self._settings.get_boolean(["includeCurrentToolInTemps"]):
				if includeTarget:
					output = "T:%.2f /%.2f %s" % (self.temp[self.currentExtruder], self.targetTemp[self.currentExtruder], allTempsString)
				else:
					output = "T:%.2f %s" % (self.temp[self.currentExtruder], allTempsString)
			else:
				output = allTempsString
		else:
			prefix = "T"
			if self._settings.get_boolean(["klipperTemperatureReporting"]):
				prefix = "T0"

			if includeTarget:
				t = "%s:%.2f /%.2f" % (prefix, self.temp[0], self.targetTemp[0])
			else:
				t = "%s:%.2f" % (prefix, self.temp[0])

			if self._settings.get_boolean(["hasBed"]):
				if includeTarget:
					b = "B:%.2f /%.2f" % (self.bedTemp, self.bedTargetTemp)
				else:
					b = "B:%.2f" % self.bedTemp
			else:
				b = ""

			if self._settings.get_boolean(["hasChamber"]):
				if includeTarget:
					c = "C:%.2f /%.2f" % (self.chamberTemp, self.chamberTargetTemp)
				else:
					c = "C:%.2f" % self.chamberTemp
			else:
				c = ""

			output = t + " " + b + " " + c
			output = output.strip()

		output += " @:64\n"
		return output

	def _processTemperatureQuery(self):
		includeOk = not self._okBeforeCommandOutput
		output = self._generateTemperatureOutput()

		if includeOk:
			ok = self._ok()
			if ok:
				output = "{} {}".format(ok, output)
		self._send(output)

	def _parseHotendCommand(self, line, wait=False, support_r=False):
		# type: (str, bool, bool) -> None
		only_wait_if_higher = True
		tool = 0
		toolMatch = re.search(r'T([0-9]+)', line)
		if toolMatch:
			tool = int(toolMatch.group(1))

		if tool >= self.temperatureCount:
			return

		try:
			self.targetTemp[tool] = float(re.search(r'S([0-9]+)', line).group(1))
		except Exception:
			if support_r:
				try:
					self.targetTemp[tool] = float(re.search(r'R([0-9]+)', line).group(1))
					only_wait_if_higher = False
				except Exception:
					pass

		if wait:
			self._waitForHeatup("tool%d" % tool, only_wait_if_higher)
		if self._settings.get_boolean(["repetierStyleTargetTemperature"]):
			self._send("TargetExtr%d:%d" % (tool, self.targetTemp[tool]))

	def _parseBedCommand(self, line, wait=False, support_r=False):
		# type: (str, bool, bool) -> None
		if not self._settings.get_boolean(["hasBed"]):
			return

		only_wait_if_higher = True
		try:
			self.bedTargetTemp = float(re.search(r'S([0-9]+)', line).group(1))
		except Exception:
			if support_r:
				try:
					self.bedTargetTemp = float(re.search(r'R([0-9]+)', line).group(1))
					only_wait_if_higher = False
				except Exception:
					pass

		if wait:
			self._waitForHeatup("bed", only_wait_if_higher)
		if self._settings.get_boolean(["repetierStyleTargetTemperature"]):
			self._send("TargetBed:%d" % self.bedTargetTemp)

	def _parseChamberCommand(self, line, wait=False, support_r=False):
		if not self._settings.get_boolean(["hasChamber"]):
			return

		only_wait_if_higher = True
		try:
			self.chamberTargetTemp = float(re.search('S([0-9]+)', line).group(1))
		except:
			if support_r:
				try:
					self.chamberTargetTemp = float(re.search('R([0-9]+)', line).group(1))
					only_wait_if_higher = False
				except:
					pass

		if wait:
			self._waitForHeatup("chamber", only_wait_if_higher)

	def _performMove(self, line):
		# type: (str) -> None
		matchX = re.search(r"X(-?[0-9.]+)", line)
		matchY = re.search(r"Y(-?[0-9.]+)", line)
		matchZ = re.search(r"Z(-?[0-9.]+)", line)
		matchE = re.search(r"E(-?[0-9.]+)", line)
		matchF = re.search(r"F([0-9.]+)", line)

		duration = 0.0
		if matchF is not None:
			try:
				self._lastF = float(matchF.group(1))
			except ValueError:
				pass

		speedXYZ = self._lastF * (self._feedrate_multiplier / 100.0)
		speedE = self._lastF * (self._flowrate_multiplier / 100.0)
		if speedXYZ == 0:
			speedXYZ = 999999999999
		if speedE == 0:
			speedE = 999999999999

		if matchX is not None:
			try:
				x = float(matchX.group(1))
			except ValueError:
				pass
			else:
				if self._relative or self._lastX is None:
					duration = max(duration, x * self._unitModifier / speedXYZ * 60.0)
				else:
					duration = max(duration, (x - self._lastX) * self._unitModifier / speedXYZ * 60.0)

				if self._relative and self._lastX is not None:
					self._lastX += x
				else:
					self._lastX = x
		if matchY is not None:
			try:
				y = float(matchY.group(1))
			except ValueError:
				pass
			else:
				if self._relative or self._lastY is None:
					duration = max(duration, y * self._unitModifier / speedXYZ * 60.0)
				else:
					duration = max(duration, (y - self._lastY) * self._unitModifier / speedXYZ * 60.0)

				if self._relative and self._lastY is not None:
					self._lastY += y
				else:
					self._lastY = y
		if matchZ is not None:
			try:
				z = float(matchZ.group(1))
			except ValueError:
				pass
			else:
				if self._relative or self._lastZ is None:
					duration = max(duration, z * self._unitModifier / speedXYZ * 60.0)
				else:
					duration = max(duration, (z - self._lastZ) * self._unitModifier / speedXYZ * 60.0)

				if self._relative and self._lastZ is not None:
					self._lastZ += z
				else:
					self._lastZ = z
		if matchE is not None:
			try:
				e = float(matchE.group(1))
			except ValueError:
				pass
			else:
				lastE = self._lastE[self.currentExtruder]
				if self._relative or lastE is None:
					duration = max(duration, e * self._unitModifier / speedE * 60.0)
				else:
					duration = max(duration, (e - lastE) * self._unitModifier / speedE * 60.0)

				if self._relative and lastE is not None:
					self._lastE[self.currentExtruder] += e
				else:
					self._lastE[self.currentExtruder] = e

		if duration:
			duration *= 0.1
			if duration > self._read_timeout:
				slept = 0
				while duration - slept > self._read_timeout and not self._killed:
					time.sleep(self._read_timeout)
					slept += self._read_timeout
			else:
				time.sleep(duration)

	def _setPosition(self, line):
		# type: (str) -> None
		matchX = re.search(r"X(-?[0-9.]+)", line)
		matchY = re.search(r"Y(-?[0-9.]+)", line)
		matchZ = re.search(r"Z(-?[0-9.]+)", line)
		matchE = re.search(r"E(-?[0-9.]+)", line)

		if matchX is None and matchY is None and matchZ is None and matchE is None:
			self._lastX = self._lastY = self._lastZ = self._lastE[self.currentExtruder] = 0
		else:
			if matchX is not None:
				try:
					self._lastX = float(matchX.group(1))
				except ValueError:
					pass
			if matchY is not None:
				try:
					self._lastY = float(matchY.group(1))
				except ValueError:
					pass
			if matchZ is not None:
				try:
					self._lastZ = float(matchZ.group(1))
				except ValueError:
					pass
			if matchE is not None:
				try:
					self._lastE[self.currentExtruder] = float(matchE.group(1))
				except ValueError:
					pass

	def _home(self, line):
		x = y = z = e = None

		if "X" in line:
			x = True
		if "Y" in line:
			y = True
		if "Z" in line:
			z = True
		if "E" in line:
			e = True

		if x is None and y is None and z is None and e is None:
			self._lastX = self._lastY = self._lastZ = self._lastE[self.currentExtruder] = 0
		else:
			if x:
				self._lastX = 0
			if y:
				self._lastY = 0
			if z:
				self._lastZ = 0
			if e:
				self._lastE = 0

	def _writeSdFile(self, filename):
		# type: (str) -> None
		filename = filename
		if filename.startswith("/"):
			filename = filename[1:]
		file = os.path.join(self._virtualSd, filename).lower()
		if os.path.exists(file):
			if os.path.isfile(file):
				os.remove(file)
			else:
				self._send("error writing to file")

		handle = None
		try:
			handle = io.open(file, 'wt', encoding='utf-8')
		except Exception:
			self._send("error writing to file")
		self._writingToSdHandle = handle
		self._writingToSd = True
		self._selectedSdFile = file
		self._send("Writing to file: %s" % filename)

	def _finishSdFile(self):
		try:
			self._writingToSdHandle.close()
		except Exception:
			pass
		finally:
			self._writingToSdHandle = None
		self._writingToSd = False
		self._selectedSdFile = None
		self._send("Done saving file")

	def _sdPrintingWorker(self):
		self._selectedSdFilePos = 0
		try:
			with io.open(self._selectedSdFile, 'rt', encoding='utf-8') as f:
				for line in iter(f.readline, ""):
					if self._killed or not self._sdPrinting:
						break

					# reset position if requested by client
					if self._newSdFilePos is not None:
						f.seek(self._newSdFilePos)
						self._newSdFilePos = None

					# read current file position
					self._selectedSdFilePos = f.tell()

					# if we are paused, wait for resuming
					self._sdPrintingSemaphore.wait()
					if self._killed or not self._sdPrinting:
						break

					# set target temps
					if 'M104' in line or 'M109' in line:
						self._parseHotendCommand(line, wait='M109' in line)
					elif 'M140' in line or 'M190' in line:
						self._parseBedCommand(line, wait='M190' in line)
					elif line.startswith("G0") or line.startswith("G1") or line.startswith("G2") or line.startswith("G3"):
						# simulate reprap buffered commands via a Queue with maxsize which internally simulates the moves
						self.buffered.put(line)

		except AttributeError:
			if self.outgoing is not None:
				raise

		self._finishSdPrint()

	def _finishSdPrint(self):
		if not self._killed:
			self._sdPrintingSemaphore.clear()
			self._send("Done printing file")
			self._selectedSdFilePos = 0
			self._sdPrinting = False
			self._sdPrinter = None

	def _waitForHeatup(self, heater, only_wait_if_higher):
		# type: (str, bool) -> None
		delta = 1
		delay = 1
		last_busy = monotonic_time()

		self._heatingUp = True
		try:
			if heater.startswith("tool"):
				toolNum = int(heater[len("tool"):])
				test = lambda: self.temp[toolNum] < self.targetTemp[toolNum] - delta or (not only_wait_if_higher and self.temp[toolNum] > self.targetTemp[toolNum] + delta)
				output = lambda: "T:%0.2f" % self.temp[toolNum]
			elif heater == "bed":
				test = lambda: self.bedTemp < self.bedTargetTemp - delta or (not only_wait_if_higher and self.bedTemp > self.bedTargetTemp + delta)
				output = lambda: "B:%0.2f" % self.bedTemp
			elif heater == "chamber":
				test = lambda: self.chamberTemp < self.chamberTargetTemp - delta or (not only_wait_if_higher and self.chamberTemp > self.chamberTargetTemp + delta)
				output = lambda: "C:%0.2f" % self.chamberTemp
			else:
				return

			while not self._killed and self._heatingUp and test():
				self._simulateTemps(delta=delta)
				self._send(output())
				if self._sendBusy and monotonic_time() - last_busy >= self._busyInterval:
					self._send("echo:busy: processing")
					last_busy = monotonic_time()
				time.sleep(delay)
		except AttributeError:
			if self.outgoing is not None:
				raise
		finally:
			self._heatingUp = False

	def _deleteSdFile(self, filename):
		# type: (str) -> None
		if filename.startswith("/"):
			filename = filename[1:]
		f = os.path.join(self._virtualSd, filename)
		if os.path.exists(f) and os.path.isfile(f):
			os.remove(f)

	def _simulateTemps(self, delta=0.5):
		timeDiff = self.lastTempAt - monotonic_time()
		self.lastTempAt = monotonic_time()

		def simulate(actual, target, ambient):
			if target > 0:
				goal = target
				remaining = abs(actual - target)
				if remaining > delta:
					factor = 10
				elif remaining < delta:
					factor = remaining
			elif not target and abs(actual - ambient) > delta:
				goal = ambient
				factor = 2
			else:
				return actual

			old = actual
			actual += math.copysign(timeDiff * factor, goal - actual)

			if math.copysign(1, goal - old) != math.copysign(1, goal - actual):
				actual = goal

			return actual

		for i in range(len(self.temp)):
			if i in self.pinnedExtruders:
				self.temp[i] = self.pinnedExtruders[i]
				continue
			self.temp[i] = simulate(self.temp[i], self.targetTemp[i], self._ambient_temperature)
		self.bedTemp = simulate(self.bedTemp, self.bedTargetTemp, self._ambient_temperature)
		self.chamberTemp = simulate(self.chamberTemp, self.chamberTargetTemp, self._ambient_temperature)

	def _processBuffer(self):
		while self.buffered is not None:
			try:
				line = self.buffered.get(timeout=0.5)
			except queue.Empty:
				continue

			if line is None:
				continue

			self._performMove(line)
			self.buffered.task_done()

		self._logger.info("Closing down buffer loop")

	def write(self, data):
		# type: (bytes) -> int
		data = to_bytes(data, errors="replace")
		u_data = to_unicode(data, errors="replace")

		if self._debug_awol:
			return len(data)

		if self._debug_drop_connection:
			self._logger.info("Debug drop of connection requested, raising SerialTimeoutException")
			raise SerialTimeoutException()

		with self._incoming_lock:
			if self.incoming is None or self.outgoing is None:
				return 0

			if b"M112" in data and self._supportM112:
				self._seriallog.info("<<< {}".format(u_data))
				self._kill()
				return len(data)

			try:
				written = self.incoming.put(data, timeout=self._write_timeout, partial=True)
				self._seriallog.info("<<< {}".format(u_data))
				return written
			except queue.Full:
				self._logger.info("Incoming queue is full, raising SerialTimeoutException")
				raise SerialTimeoutException()

	def readline(self):
		# type: () -> bytes
		if self._debug_awol:
			time.sleep(self._read_timeout)
			return b""

		if self._debug_drop_connection:
			raise SerialTimeoutException()

		if self._debug_sleep > 0:
			# if we are supposed to sleep, we sleep not longer than the read timeout
			# (and then on the next call sleep again if there's time to sleep left)
			sleep_for = min(self._debug_sleep, self._read_timeout)
			self._debug_sleep -= sleep_for
			time.sleep(sleep_for)

			if self._debug_sleep > 0:
				# we slept the full read timeout, return an empty line
				return b""

			# otherwise our left over timeout is the read timeout minus what we already
			# slept for
			timeout = self._read_timeout - sleep_for

		else:
			# use the full read timeout as timeout
			timeout = self._read_timeout

		try:
			# fetch a line from the queue, wait no longer than timeout
			line = to_unicode(self.outgoing.get(timeout=timeout), errors="replace")
			self._seriallog.info(u">>> {}".format(line.strip()))
			self.outgoing.task_done()
			return to_bytes(line)
		except queue.Empty:
			# queue empty? return empty line
			return b""

	def close(self):
		self._killed = True
		self.incoming = None
		self.outgoing = None
		self.buffered = None

	def _sendOk(self):
		if self.outgoing is None:
			return
		ok = self._ok()
		if ok:
			self._send(ok)

	def _sendWaitAfterTimeout(self, timeout=5):
		time.sleep(timeout)
		if self.outgoing is not None:
			self._send("wait")

	def _send(self, line):
		# type: (str) -> None
		if self.outgoing is not None:
			self.outgoing.put(line)

	def _ok(self):
		ok = self._okFormatString
		if self._prepared_oks:
			ok = self._prepared_oks.pop(0)
			if ok is None:
				return ok

		return ok.format(ok, lastN=self.lastN, buffer=self.buffered.maxsize - self.buffered.qsize())

	def _error(self, error, *args, **kwargs):
		# type: (str, Any, Any) -> str
		return "Error: {}".format(self._errors.get(error).format(*args, **kwargs))


# noinspection PyUnresolvedReferences
class CharCountingQueue(queue.Queue):

	def __init__(self, maxsize, name=None):
		queue.Queue.__init__(self, maxsize=maxsize)
		self._size = 0
		self._name = name

	def clear(self):
		with self.mutex:
			self.queue.clear()

	def put(self, item, block=True, timeout=None, partial=False):
		self.not_full.acquire()

		try:
			if not self._will_it_fit(item) and partial:
				space_left = self.maxsize - self._qsize()
				if space_left:
					item = item[:space_left]

			if not block:
				if not self._will_it_fit(item):
					raise queue.Full
			elif timeout is None:
				while not self._will_it_fit(item):
					self.not_full.wait()
			elif timeout < 0:
				raise ValueError("'timeout' must be a positive number")
			else:
				endtime = monotonic_time() + timeout
				while not self._will_it_fit(item):
					remaining = endtime - monotonic_time()
					if remaining <= 0.0:
						raise queue.Full
					self.not_full.wait(remaining)

			self._put(item)
			self.unfinished_tasks += 1
			self.not_empty.notify()

			return self._len(item)
		finally:
			self.not_full.release()

	# noinspection PyMethodMayBeStatic
	def _len(self, item):
		return len(item)

	def _qsize(self, l=len):
		return self._size

	# Put a new item in the queue
	def _put(self, item):
		self.queue.append(item)
		self._size += self._len(item)

	# Get an item from the queue
	def _get(self):
		item = self.queue.popleft()
		self._size -= self._len(item)
		return item

	def _will_it_fit(self, item):
		return self.maxsize - self._qsize() >= self._len(item)
