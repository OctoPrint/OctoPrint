# coding=utf-8
from __future__ import absolute_import, division, print_function
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


import time
import os
import re
import threading
import math
try:
	import queue
except ImportError:
	import Queue as queue

from serial import SerialTimeoutException

from octoprint.settings import settings
from octoprint.plugin import plugin_manager
from octoprint.util import RepeatedTimer

class VirtualPrinter(object):
	command_regex = re.compile("^([GMTF])(\d+)")
	sleep_regex = re.compile("sleep (\d+)")
	sleep_after_regex = re.compile("sleep_after ([GMTF]\d+) (\d+)")
	sleep_after_next_regex = re.compile("sleep_after_next ([GMTF]\d+) (\d+)")
	custom_action_regex = re.compile("action_custom ([a-zA-Z0-9_]+)(\s+.*)?")
	prepare_ok_regex = re.compile("prepare_ok (.*)")
	send_regex = re.compile("send (.*)")
	set_ambient_regex = re.compile("set_ambient ([-+]?[0-9]*\.?[0-9]+)")

	def __init__(self, seriallog_handler=None, read_timeout=5.0, write_timeout=10.0):
		import logging
		self._logger = logging.getLogger("octoprint.plugins.virtual_printer.VirtualPrinter")

		self._seriallog = logging.getLogger("octoprint.plugin.virtual_printer.VirtualPrinter.serial")
		self._seriallog.setLevel(logging.CRITICAL)
		self._seriallog.propagate = False

		if seriallog_handler is not None:
			import logging.handlers
			self._seriallog.addHandler(seriallog_handler)
			self._seriallog.setLevel(logging.INFO)

		self._seriallog.info("-"*78)

		self._read_timeout = read_timeout
		self._write_timeout = write_timeout

		self._rx_buffer_size = settings().getInt(["devel", "virtualPrinter", "rxBuffer"])

		self.incoming = CharCountingQueue(self._rx_buffer_size, name="RxBuffer")
		self.outgoing = queue.Queue()
		self.buffered = queue.Queue(maxsize=settings().getInt(["devel", "virtualPrinter", "commandBuffer"]))

		if settings().getBoolean(["devel", "virtualPrinter", "simulateReset"]):
			for item in settings().get(["devel", "virtualPrinter", "resetLines"]):
				self._send(item + "\n")

		self._prepared_oks = []
		prepared = settings().get(["devel", "virtualPrinter", "preparedOks"])
		if prepared and isinstance(prepared, list):
			for prep in prepared:
				self._prepared_oks.append(prep)

		self._prepared_errors = []

		self._errors = settings().get(["devel", "virtualPrinter", "errors"], merged=True)

		self.currentExtruder = 0
		self.extruderCount = settings().getInt(["devel", "virtualPrinter", "numExtruders"])
		self.pinnedExtruders = settings().get(["devel", "virtualPrinter", "pinnedExtruders"])
		if self.pinnedExtruders is None:
			self.pinnedExtruders = dict()
		self.sharedNozzle = settings().getBoolean(["devel", "virtualPrinter", "sharedNozzle"])
		self.temperatureCount = (1 if self.sharedNozzle else self.extruderCount)

		self._ambient_temperature = settings().getFloat(["devel", "virtualPrinter", "ambientTemperature"])

		self.temp = [self._ambient_temperature] * self.temperatureCount
		self.targetTemp = [0.0] * self.temperatureCount
		self.bedTemp = self._ambient_temperature
		self.bedTargetTemp = 0.0
		self.lastTempAt = time.time()

		self._relative = True
		self._lastX = 0.0
		self._lastY = 0.0
		self._lastZ = 0.0
		self._lastE = 0.0
		self._lastF = 200

		self._unitModifier = 1
		self._feedrate_multiplier = 100
		self._flowrate_multiplier = 100

		self._virtualSd = settings().getBaseFolder("virtualSd")
		self._sdCardReady = True
		self._sdPrinter = None
		self._sdPrintingSemaphore = threading.Event()
		self._selectedSdFile = None
		self._selectedSdFileSize = None
		self._selectedSdFilePos = None
		self._writingToSd = False
		self._writingToSdHandle = None
		self._newSdFilePos = None
		self._heatupThread = None

		self._okBeforeCommandOutput = settings().getBoolean(["devel", "virtualPrinter", "okBeforeCommandOutput"])
		self._supportM112 = settings().getBoolean(["devel", "virtualPrinter", "supportM112"])
		self._supportF = settings().getBoolean(["devel", "virtualPrinter", "supportF"])

		self._sendWait = settings().getBoolean(["devel", "virtualPrinter", "sendWait"])
		self._sendBusy = settings().getBoolean(["devel", "virtualPrinter", "sendBusy"])
		self._waitInterval = settings().getFloat(["devel", "virtualPrinter", "waitInterval"])

		self._echoOnM117 = settings().getBoolean(["devel", "virtualPrinter", "echoOnM117"])

		self._brokenM29 = settings().getBoolean(["devel", "virtualPrinter", "brokenM29"])

		self._m115FormatString = settings().get(["devel", "virtualPrinter", "m115FormatString"])
		self._firmwareName = settings().get(["devel", "virtualPrinter", "firmwareName"])

		self._okFormatString = settings().get(["devel", "virtualPrinter", "okFormatString"])

		self._capabilities = settings().get(["devel", "virtualPrinter", "capabilities"])

		self._temperature_reporter = None

		self.currentLine = 0
		self.lastN = 0

		self._incoming_lock = threading.RLock()

		self._debug_awol = False
		self._debug_sleep = None
		self._sleepAfterNext = dict()
		self._sleepAfter = dict()

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
			.format(read_timeout=self._read_timeout, write_timeout=self._write_timeout, options=settings().get(["devel", "virtualPrinter"]))

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

	def _clearQueue(self, queue):
		try:
			while queue.get(block=False):
				continue
		except queue.Empty:
			pass

	def _processIncoming(self):
		next_wait_timeout = time.time() + self._waitInterval
		buf = ""
		while self.incoming is not None and not self._killed:
			self._simulateTemps()

			try:
				data = self.incoming.get(timeout=0.01)
				self.incoming.task_done()
			except queue.Empty:
				if self._sendWait and time.time() > next_wait_timeout:
					self._send("wait")
					next_wait_timeout = time.time() + self._waitInterval
				continue

			buf += data
			if "\n" in buf:
				data = buf[:buf.find("\n") + 1]
				buf = buf[buf.find("\n") + 1:]
			else:
				continue

			next_wait_timeout = time.time() + self._waitInterval

			if data is None:
				continue

			if self._dont_answer:
				self._dont_answer = False
				continue

			data = data.strip()

			# strip checksum
			if "*" in data:
				checksum = int(data[data.rfind("*") + 1:])
				data = data[:data.rfind("*")]
				if not checksum == self._calculate_checksum(data):
					self._triggerResend(expected=self.currentLine + 1)
					continue

				self.currentLine += 1
			elif settings().getBoolean(["devel", "virtualPrinter", "forceChecksum"]):
				self._send(self._error("checksum_missing"))
				continue

			# track N = N + 1
			if data.startswith("N") and "M110" in data:
				linenumber = int(re.search("N([0-9]+)", data).group(1))
				self.lastN = linenumber
				self.currentLine = linenumber

				self._triggerResendAt100 = True
				self._triggerResendWithTimeoutAt105 = True

				self._sendOk()
				continue
			elif data.startswith("N"):
				linenumber = int(re.search("N([0-9]+)", data).group(1))
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
					if callable(prepared):
						prepared(linenumber, self.lastN, data)
						continue
					elif isinstance(prepared, basestring):
						self._send(prepared)
						continue
				else:
					self.lastN = linenumber
				data = data.split(None, 1)[1].strip()

			data += "\n"

			if data.startswith("!!DEBUG:") or data.strip() == "!!DEBUG":
				debug_command = ""
				if data.startswith("!!DEBUG:"):
					debug_command = data[len("!!DEBUG:"):].strip()
				self._debugTrigger(debug_command)
				continue

			# shortcut for writing to SD
			if self._writingToSdHandle is not None and not "M29" in data:
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

	def _gcode_T(self, code, data):
		t = int(code)
		if 0 <= t <= self.extruderCount:
			self.currentExtruder = t
			self._send("Active Extruder: %d" % self.currentExtruder)

	def _gcode_F(self, code, data):
		if self._supportF:
			self._send("echo:changed F value")
			return False
		else:
			self._send(self._error("command_unknown", "F"))
			return True

	def _gcode_M104(self, data):
		self._parseHotendCommand(data)

	def _gcode_M109(self, data):
		self._parseHotendCommand(data, wait=True, support_r=True)

	def _gcode_M140(self, data):
		self._parseBedCommand(data)

	def _gcode_M190(self, data):
		self._parseBedCommand(data, wait=True, support_r=True)

	def _gcode_M105(self, data):
		self._processTemperatureQuery()
		return True

	def _gcode_M20(self, data):
		if self._sdCardReady:
			self._listSd()

	def _gcode_M21(self, data):
		self._sdCardReady = True
		self._send("SD card ok")

	def _gcode_M22(self, data):
		self._sdCardReady = False

	def _gcode_M23(self, data):
		if self._sdCardReady:
			filename = data.split(None, 1)[1].strip()
			self._selectSdFile(filename)

	def _gcode_M24(self, data):
		if self._sdCardReady:
			self._startSdPrint()

	def _gcode_M25(self, data):
		if self._sdCardReady:
			self._pauseSdPrint()

	def _gcode_M26(self, data):
		if self._sdCardReady:
			pos = int(re.search("S([0-9]+)", data).group(1))
			self._setSdPos(pos)

	def _gcode_M27(self, data):
		if self._sdCardReady:
			self._reportSdStatus()

	def _gcode_M28(self, data):
		if self._sdCardReady:
			filename = data.split(None, 1)[1].strip()
			self._writeSdFile(filename)

	def _gcode_M29(self, data):
		if self._sdCardReady:
			self._finishSdFile()

	def _gcode_M30(self, data):
		if self._sdCardReady:
			filename = data.split(None, 1)[1].strip()
			self._deleteSdFile(filename)

	def _gcode_M114(self, data):
		output = "X:{} Y:{} Z:{} E:{} Count: A:{} B:{} C:{}".format(self._lastX, self._lastY, self._lastZ, self._lastE, int(self._lastX*100), int(self._lastY*100), int(self._lastZ*100))
		if not self._okBeforeCommandOutput:
			ok = self._ok()
			if ok:
				output = "{} {}".format(self._ok(), output)
		self._send(output)
		return True

	def _gcode_M115(self, data):
		output = self._m115FormatString.format(firmware_name=self._firmwareName)
		self._send(output)

		if settings().getBoolean(["devel", "virtualPrinter", "m115ReportCapabilities"]):
			for cap, enabled in self._capabilities.items():
				self._send("Cap:{}:{}".format(cap.upper(), "1" if enabled else "0"))

	def _gcode_M117(self, data):
		# we'll just use this to echo a message, to allow playing around with pause triggers
		if self._echoOnM117:
			self._send("echo:%s" % re.search("M117\s+(.*)", data).group(1))

	def _gcode_M155(self, data):
		interval = int(re.search("S([0-9]+)", data).group(1))
		if self._temperature_reporter is not None:
			self._temperature_reporter.cancel()

		if interval > 0:
			self._temperature_reporter = RepeatedTimer(interval, lambda: self._send(self._generateTemperatureOutput()))
			self._temperature_reporter.start()
		else:
			self._temperature_reporter = None

	def _gcode_M220(self, data):
		self._feedrate_multiplier = float(re.search('S([0-9]+)', data).group(1))

	def _gcode_M221(self, data):
		self._flowrate_multiplier = float(re.search('S([0-9]+)', data).group(1))

	def _gcode_M400(self, data):
		self.buffered.join()

	def _gcode_M999(self, data):
		# mirror Marlin behaviour
		self._send("Resend: 1")

	def _gcode_G20(self, data):
		self._unitModifier = 1.0 / 2.54
		if self._lastX is not None:
			self._lastX *= 2.54
		if self._lastY is not None:
			self._lastY *= 2.54
		if self._lastZ is not None:
			self._lastZ *= 2.54
		if self._lastE is not None:
			self._lastE *= 2.54

	def _gcode_G21(self, data):
		self._unitModifier = 1.0
		if self._lastX is not None:
			self._lastX /= 2.54
		if self._lastY is not None:
			self._lastY /= 2.54
		if self._lastZ is not None:
			self._lastZ /= 2.54
		if self._lastE is not None:
			self._lastE /= 2.54

	def _gcode_G90(self, data):
		self._relative = False

	def _gcode_G91(self, data):
		self._relative = True

	def _gcode_G92(self, data):
		self._setPosition(data)

	def _gcode_G28(self, data):
		self._performMove(data)

	def _gcode_G0(self, data):
		# simulate reprap buffered commands via a Queue with maxsize which internally simulates the moves
		self.buffered.put(data)
	_gcode_G1 = _gcode_G0
	_gcode_G2 = _gcode_G0
	_gcode_G3 = _gcode_G0

	def _gcode_G4(self, data):
		matchS = re.search('S([0-9]+)', data)
		matchP = re.search('P([0-9]+)', data)

		_timeout = 0
		if matchP:
			_timeout = float(matchP.group(1)) / 1000.0
		elif matchS:
			_timeout = float(matchS.group(1))

		if self._sendBusy:
			until = time.time() + _timeout
			while time.time() < until:
				time.sleep(1.0)
				self._send("busy:processing")
		else:
			time.sleep(_timeout)

	##~~ further helpers

	def _calculate_checksum(self, line):
		checksum = 0
		for c in line:
			checksum ^= ord(c)
		return checksum

	def _kill(self):
		if not self._supportM112:
			return
		self._killed = True
		self._send("echo:EMERGENCY SHUTDOWN DETECTED. KILLED.")

	def _triggerResend(self, expected=None, actual=None, checksum=None):
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
				self._sendOk()

			if settings().getBoolean(["devel", "virtualPrinter", "repetierStyleResends"]):
				request_resend()
			request_resend()

	def _debugTrigger(self, data):
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
			drop_connection
			| Drops the serial connection
			prepare_ok <broken ok>
			| Will cause <broken ok> to be enqueued for use,
			| will be used instead of actual "ok"

			# Reply Timing / Sleeping

			sleep <int:seconds>
			| Sleep <seconds> s
			sleep_after <str:command> <int:seconds>
			| Sleeps <seconds> s after each execution of <command>
			sleep_after_next <str:command> <int:seconds>
			| Sleeps <seconds> s after execution of next <command>

			# Misc

			send <str:message>
			| Sends back <message>
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
			self._prepared_errors.append(lambda cur, last, line: self._triggerResend(expected=last, actual=last+1))
		elif data == "trigger_resend_checksum":
			self._prepared_errors.append(lambda cur, last, line: self._triggerResend(expected=last, checksum=True))
		elif data == "trigger_missing_checksum":
			self._prepared_errors.append(lambda cur, last, line: self._triggerResend(expected=last, checksum=False))
		elif data == "trigger_missing_lineno":
			self._prepared_errors.append(lambda cur, last, line: self._send(self._error("lineno_missing", last)))
		elif data == "drop_connection":
			self._debug_drop_connection = True
		elif data == "mintemp_error":
			self._send(self._error("mintemp"))
		elif data == "maxtemp_error":
			self._send(self._error("maxtemp"))
		elif data == "go_awol":
			self._send("// Going AWOL")
			self._debug_awol = True
		else:
			try:
				sleep_match = VirtualPrinter.sleep_regex.match(data)
				sleep_after_match = VirtualPrinter.sleep_after_regex.match(data)
				sleep_after_next_match = VirtualPrinter.sleep_after_next_regex.match(data)
				custom_action_match = VirtualPrinter.custom_action_regex.match(data)
				prepare_ok_match = VirtualPrinter.prepare_ok_regex.match(data)
				send_match = VirtualPrinter.send_regex.match(data)
				set_ambient_match = VirtualPrinter.set_ambient_regex.match(data)

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
			except:
				pass

	def _listSd(self):
		self._send("Begin file list")
		if settings().getBoolean(["devel", "virtualPrinter", "extendedSdFileList"]):
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

	def _selectSdFile(self, filename):
		if filename.startswith("/"):
			filename = filename[1:]
		file = os.path.join(self._virtualSd, filename.lower())
		if not os.path.exists(file) or not os.path.isfile(file):
			self._send("open failed, File: %s." % filename)
		else:
			self._selectedSdFile = file
			self._selectedSdFileSize = os.stat(file).st_size
			if settings().getBoolean(["devel", "virtualPrinter", "includeFilenameInOpened"]):
				self._send("File opened: %s  Size: %d" % (filename, self._selectedSdFileSize))
			else:
				self._send("File opened")
			self._send("File selected")

	def _startSdPrint(self):
		if self._selectedSdFile is not None:
			if self._sdPrinter is None:
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
		includeTarget = not settings().getBoolean(["devel", "virtualPrinter", "repetierStyleTargetTemperature"])

		# send simulated temperature data
		if self.temperatureCount > 1:
			allTemps = []
			for i in range(len(self.temp)):
				allTemps.append((i, self.temp[i], self.targetTemp[i]))
			allTempsString = " ".join(map(lambda x: "T%d:%.2f /%.2f" % x if includeTarget else "T%d:%.2f" % (x[0], x[1]), allTemps))

			if settings().getBoolean(["devel", "virtualPrinter", "smoothieTemperatureReporting"]):
				allTempsString = allTempsString.replace("T0:", "T:")

			if settings().getBoolean(["devel", "virtualPrinter", "hasBed"]):
				if includeTarget:
					allTempsString = "B:%.2f /%.2f %s" % (self.bedTemp, self.bedTargetTemp, allTempsString)
				else:
					allTempsString = "B:%.2f %s" % (self.bedTemp, allTempsString)

			if settings().getBoolean(["devel", "virtualPrinter", "includeCurrentToolInTemps"]):
				if includeTarget:
					output = "T:%.2f /%.2f %s" % (self.temp[self.currentExtruder], self.targetTemp[self.currentExtruder], allTempsString)
				else:
					output = "T:%.2f %s" % (self.temp[self.currentExtruder], allTempsString)
			else:
				output = allTempsString
		else:
			if includeTarget:
				output = "T:%.2f /%.2f B:%.2f /%.2f" % (self.temp[0], self.targetTemp[0], self.bedTemp, self.bedTargetTemp)
			else:
				output = "T:%.2f B:%.2f" % (self.temp[0], self.bedTemp)

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
		only_wait_if_higher = True
		tool = 0
		toolMatch = re.search('T([0-9]+)', line)
		if toolMatch:
			try:
				tool = int(toolMatch.group(1))
			except:
				pass

		if tool >= self.temperatureCount:
			return

		try:
			self.targetTemp[tool] = float(re.search('S([0-9]+)', line).group(1))
		except:
			if support_r:
				try:
					self.targetTemp[tool] = float(re.search('R([0-9]+)', line).group(1))
					only_wait_if_higher = False
				except:
					pass

		if wait:
			self._waitForHeatup("tool%d" % tool, only_wait_if_higher)
		if settings().getBoolean(["devel", "virtualPrinter", "repetierStyleTargetTemperature"]):
			self._send("TargetExtr%d:%d" % (tool, self.targetTemp[tool]))

	def _parseBedCommand(self, line, wait=False, support_r=False):
		only_wait_if_higher = True
		try:
			self.bedTargetTemp = float(re.search('S([0-9]+)', line).group(1))
		except:
			if support_r:
				try:
					self.bedTargetTemp = float(re.search('R([0-9]+)', line).group(1))
					only_wait_if_higher = False
				except:
					pass

		if wait:
			self._waitForHeatup("bed", only_wait_if_higher)
		if settings().getBoolean(["devel", "virtualPrinter", "repetierStyleTargetTemperature"]):
			self._send("TargetBed:%d" % self.bedTargetTemp)

	def _performMove(self, line):
		matchX = re.search("X([0-9.]+)", line)
		matchY = re.search("Y([0-9.]+)", line)
		matchZ = re.search("Z([0-9.]+)", line)
		matchE = re.search("E([0-9.]+)", line)
		matchF = re.search("F([0-9.]+)", line)

		duration = 0
		if matchF is not None:
			try:
				self._lastF = float(matchF.group(1))
			except:
				pass

		speedXYZ = self._lastF * (self._feedrate_multiplier / 100.0)
		speedE = self._lastF * (self._flowrate_multiplier / 100.0)

		if matchX is not None:
			try:
				x = float(matchX.group(1))
				if self._relative or self._lastX is None:
					duration = max(duration, x * self._unitModifier / speedXYZ * 60.0)
				else:
					duration = max(duration, (x - self._lastX) * self._unitModifier / speedXYZ * 60.0)

				if self._relative and self._lastX is not None:
					self._lastX += x
				else:
					self._lastX = x
			except:
				pass
		if matchY is not None:
			try:
				y = float(matchY.group(1))
				if self._relative or self._lastY is None:
					duration = max(duration, y * self._unitModifier / speedXYZ * 60.0)
				else:
					duration = max(duration, (y - self._lastY) * self._unitModifier / speedXYZ * 60.0)

				if self._relative and self._lastY is not None:
					self._lastY += y
				else:
					self._lastY = y
			except:
				pass
		if matchZ is not None:
			try:
				z = float(matchZ.group(1))
				if self._relative or self._lastZ is None:
					duration = max(duration, z * self._unitModifier / speedXYZ * 60.0)
				else:
					duration = max(duration, (z - self._lastZ) * self._unitModifier / speedXYZ * 60.0)

				if self._relative and self._lastZ is not None:
					self._lastZ += z
				else:
					self._lastZ = z
			except:
				pass
		if matchE is not None:
			try:
				e = float(matchE.group(1))
				if self._relative or self._lastE is None:
					duration = max(duration, e * self._unitModifier / speedE * 60.0)
				else:
					duration = max(duration, (e - self._lastE) * self._unitModifier / speedE * 60.0)

				if self._relative and self._lastE is not None:
					self._lastE += e
				else:
					self._lastE = e
			except:
				pass

		if duration:
			if duration > self._read_timeout:
				slept = 0
				while duration - slept > self._read_timeout and not self._killed:
					time.sleep(self._read_timeout)
					slept += self._read_timeout
			else:
				time.sleep(duration)

	def _setPosition(self, line):
		matchX = re.search("X([0-9.]+)", line)
		matchY = re.search("Y([0-9.]+)", line)
		matchZ = re.search("Z([0-9.]+)", line)
		matchE = re.search("E([0-9.]+)", line)

		if matchX is None and matchY is None and matchZ is None and matchE is None:
			self._lastX = self._lastY = self._lastZ = self._lastE = 0
		else:
			if matchX is not None:
				try:
					self._lastX = float(matchX.group(1))
				except:
					pass
			if matchY is not None:
				try:
					self._lastY = float(matchY.group(1))
				except:
					pass
			if matchZ is not None:
				try:
					self._lastZ = float(matchZ.group(1))
				except:
					pass
			if matchE is not None:
				try:
					self._lastE = float(matchE.group(1))
				except:
					pass

	def _writeSdFile(self, filename):
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
			handle = open(file, "w")
		except:
			self._output("error writing to file")
			if handle is not None:
				try:
					handle.close()
				except:
					pass
		self._writingToSdHandle = handle
		self._writingToSd = True
		self._selectedSdFile = file
		self._send("Writing to file: %s" % filename)

	def _finishSdFile(self):
		try:
			self._writingToSdHandle.close()
		except:
			pass
		finally:
			self._writingToSdHandle = None
		self._writingToSd = False
		self._selectedSdFile = None
		self._output("Done saving file")

	def _sdPrintingWorker(self):
		self._selectedSdFilePos = 0
		try:
			with open(self._selectedSdFile, "r") as f:
				for line in iter(f.readline, ""):
					if self._killed:
						break

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
						self._parseHotendCommand(line)
					elif 'M140' in line or 'M190' in line:
						self._parseBedCommand(line)
					elif line.startswith("G0") or line.startswith("G1") or line.startswith("G2") or line.startswith("G3"):
						# simulate reprap buffered commands via a Queue with maxsize which internally simulates the moves
						self.buffered.put(line)

		except AttributeError:
			if self.outgoing is not None:
				raise

		if not self._killed:
			self._sdPrintingSemaphore.clear()
			self._selectedSdFilePos = 0
			self._sdPrinter = None
			self._output("Done printing file")

	def _waitForHeatup(self, heater, only_wait_if_higher):
		delta = 1
		delay = 1

		try:
			if heater.startswith("tool"):
				toolNum = int(heater[len("tool"):])
				while not self._killed and (self.temp[toolNum] < self.targetTemp[toolNum] - delta or (not only_wait_if_higher and self.temp[toolNum] > self.targetTemp[toolNum] + delta)):
					self._simulateTemps(delta=delta)
					self._output("T:%0.2f" % self.temp[toolNum])
					time.sleep(delay)
			elif heater == "bed":
				while not self._killed and (self.bedTemp < self.bedTargetTemp - delta or (not only_wait_if_higher and self.bedTemp > self.bedTargetTemp + delta)):
					self._simulateTemps(delta=delta)
					self._output("B:%0.2f" % self.bedTemp)
					time.sleep(delay)
		except AttributeError:
			if self.outgoing is not None:
				raise

	def _deleteSdFile(self, filename):
		if filename.startswith("/"):
			filename = filename[1:]
		f = os.path.join(self._virtualSd, filename)
		if os.path.exists(f) and os.path.isfile(f):
			os.remove(f)

	def _simulateTemps(self, delta=0.5):
		timeDiff = self.lastTempAt - time.time()
		self.lastTempAt = time.time()

		def simulate(actual, target, ambient):
			if target > 0 and abs(actual - target) > delta:
				goal = target
				factor = 10
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

	def _output(self, line):
		try:
			self.outgoing.put(line)
		except:
			if self.outgoing is None:
				pass

	def write(self, data):
		if self._debug_awol:
			return len(data)

		if self._debug_drop_connection:
			self._logger.info("Debug drop of connection requested, raising SerialTimeoutException")
			raise SerialTimeoutException()

		with self._incoming_lock:
			if self.incoming is None or self.outgoing is None:
				return 0

			if "M112" in data and self._supportM112:
				self._seriallog.info("<<< {}".format(data.strip()))
				self._kill()
				return len(data)

			try:
				written = self.incoming.put(data, timeout=self._write_timeout, partial=True)
				self._seriallog.info("<<< {}".format(data.strip()))
				return written
			except queue.Full:
				self._logger.info("Incoming queue is full, raising SerialTimeoutException")
				raise SerialTimeoutException()

	def readline(self):
		if self._debug_awol:
			time.sleep(self._read_timeout)
			return ""

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
				return ""

			# otherwise our left over timeout is the read timeout minus what we already
			# slept for
			timeout = self._read_timeout - sleep_for

		else:
			# use the full read timeout as timeout
			timeout = self._read_timeout

		try:
			# fetch a line from the queue, wait no longer than timeout
			line = self.outgoing.get(timeout=timeout)
			self._seriallog.info(">>> {}".format(line.strip()))
			self.outgoing.task_done()
			return line
		except queue.Empty:
			# queue empty? return empty line
			return ""

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
		return "Error: {}".format(self._errors.get(error).format(*args, **kwargs))

class CharCountingQueue(queue.Queue):

	def __init__(self, maxsize, name=None):
		queue.Queue.__init__(self, maxsize=maxsize)
		self._size = 0
		self._name = name

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
				endtime = time.time() + timeout
				while not self._will_it_fit(item):
					remaining = endtime - time.time()
					if remaining <= 0.0:
						raise queue.Full
					self.not_full.wait(remaining)

			self._put(item)
			self.unfinished_tasks += 1
			self.not_empty.notify()

			return self._len(item)
		finally:
			self.not_full.release()

	def _len(self, item):
		return len(item)

	def _qsize(self, len=len):
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
