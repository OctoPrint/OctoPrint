__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"


import collections
import json
import math
import os
import queue
import re
import threading
import time

from serial import SerialTimeoutException

from octoprint.plugin import plugin_manager
from octoprint.util import RepeatedTimer, get_dos_filename, to_bytes, to_unicode
from octoprint.util.files import unix_timestamp_to_m20_timestamp


# noinspection PyBroadException
class VirtualPrinter:
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
    resend_ratio_regex = re.compile(r"resend_ratio (\d+)")

    def __init__(
        self,
        settings,
        data_folder,
        seriallog_handler=None,
        read_timeout=5.0,
        write_timeout=10.0,
        faked_baudrate=115200,
    ):
        import logging

        self._logger = logging.getLogger(
            "octoprint.plugins.virtual_printer.VirtualPrinter"
        )

        self._settings = settings
        self._faked_baudrate = faked_baudrate
        self._plugin_data_folder = data_folder

        self._seriallog = logging.getLogger(
            "octoprint.plugin.virtual_printer.VirtualPrinter.serial"
        )
        self._seriallog.setLevel(logging.CRITICAL)
        self._seriallog.propagate = False

        if seriallog_handler is not None:
            import logging.handlers

            self._seriallog.addHandler(seriallog_handler)
            self._seriallog.setLevel(logging.INFO)

        self._seriallog.info("-" * 78)

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
            self.pinnedExtruders = {}
        self.sharedNozzle = self._settings.get_boolean(["sharedNozzle"])
        self.temperatureCount = 1 if self.sharedNozzle else self.extruderCount

        self._ambient_temperature = self._settings.get_float(["ambientTemperature"])

        self.temp = [self._ambient_temperature] * self.temperatureCount
        self.targetTemp = [0.0] * self.temperatureCount
        self.bedTemp = self._ambient_temperature
        self.bedTargetTemp = 0.0
        self.chamberTemp = self._ambient_temperature
        self.chamberTargetTemp = 0.0
        self.lastTempAt = time.monotonic()

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
        self._writingToSdFile = None
        self._newSdFilePos = None

        self._heatingUp = False

        self._virtual_eeprom = (
            VirtualEEPROM(self._plugin_data_folder)
            if self._settings.get_boolean(["enable_eeprom"])
            else None
        )
        self._support_M503 = self._settings.get_boolean(["support_M503"])

        self._okBeforeCommandOutput = self._settings.get_boolean(
            ["okBeforeCommandOutput"]
        )
        self._supportM112 = self._settings.get_boolean(["supportM112"])
        self._supportF = self._settings.get_boolean(["supportF"])

        self._sendWait = self._settings.get_boolean(["sendWait"])
        self._sendBusy = self._settings.get_boolean(["sendBusy"])
        self._waitInterval = self._settings.get_float(["waitInterval"])
        self._busyInterval = self._settings.get_float(["busyInterval"])

        self._busy = None
        self._busy_loop = None

        self._echoOnM117 = self._settings.get_boolean(["echoOnM117"])

        self._brokenM29 = self._settings.get_boolean(["brokenM29"])
        self._brokenResend = self._settings.get_boolean(["brokenResend"])

        self._m115FormatString = self._settings.get(["m115FormatString"])
        self._firmwareName = self._settings.get(["firmwareName"])

        self._okFormatString = self._settings.get(["okFormatString"])

        self._capabilities = self._settings.get(["capabilities"], merged=True)

        self._locked = self._settings.get_boolean(["locked"])

        self._temperature_reporter = None
        self._sdstatus_reporter = None
        self._pos_reporter = None

        self.current_line = 0
        self.lastN = 0

        self._incoming_lock = threading.RLock()

        self._debug_awol = False
        self._debug_sleep = 0
        self._sleepAfterNext = {}
        self._sleepAfter = {}
        self._rerequest_last = False

        self._received_lines = 0
        self._resend_every_n = 0
        self._calculate_resend_every_n(self._settings.get_int(["resend_ratio"]))

        self._dont_answer = False
        self._broken_klipper_connection = False

        self._debug_drop_connection = False

        self._action_hooks = plugin_manager().get_hooks(
            "octoprint.plugin.virtual_printer.custom_action"
        )

        self._killed = False

        self._triggerResendAt100 = True
        self._triggerResendWithTimeoutAt105 = True
        self._triggerResendWithMissingLinenoAt110 = True
        self._triggerResendWithChecksumMismatchAt115 = True

        readThread = threading.Thread(
            target=self._processIncoming,
            name="octoprint.plugins.virtual_printer.wait_thread",
        )
        readThread.start()

        bufferThread = threading.Thread(
            target=self._processBuffer,
            name="octoprint.plugins.virtual_printer.buffer_thread",
        )
        bufferThread.start()

    def __str__(self):
        return "VIRTUAL(read_timeout={read_timeout},write_timeout={write_timeout},options={options})".format(
            read_timeout=self._read_timeout,
            write_timeout=self._write_timeout,
            options=self._settings.get([]),
        )

    def _calculate_resend_every_n(self, resend_ratio):
        self._resend_every_n = (100 // resend_ratio) if resend_ratio else 0

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

            # read eeprom from disk
            if self._virtual_eeprom:
                self._virtual_eeprom.read_settings()

            if self._writingToSdHandle:
                try:
                    self._writingToSdHandle.close()
                except Exception:
                    pass
            self._writingToSd = False
            self._writingToSdHandle = None
            self._writingToSdFile = None
            self._newSdFilePos = None

            self._heatingUp = False

            self.current_line = 0
            self.lastN = 0

            self._debug_awol = False
            self._debug_sleep = 0
            self._sleepAfterNext.clear()
            self._sleepAfter.clear()

            self._dont_answer = False
            self._broken_klipper_connection = False

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

            self._locked = self._settings.get_boolean(["locked"])

    @property
    def timeout(self):
        return self._read_timeout

    @timeout.setter
    def timeout(self, value):
        self._logger.debug(f"Setting read timeout to {value}s")
        self._read_timeout = value

    @property
    def write_timeout(self):
        return self._write_timeout

    @write_timeout.setter
    def write_timeout(self, value):
        self._logger.debug(f"Setting write timeout to {value}s")
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
        next_wait_timeout = time.monotonic() + self._waitInterval
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
                if self._sendWait and time.monotonic() > next_wait_timeout:
                    self._send("wait")
                    next_wait_timeout = time.monotonic() + self._waitInterval
                continue
            except Exception:
                if self.incoming is None:
                    # just got closed
                    break

            if data is not None:
                buf += data
                nl = buf.find(b"\n") + 1
                if nl > 0:
                    data = buf[:nl]
                    buf = buf[nl:]
                else:
                    continue

            next_wait_timeout = time.monotonic() + self._waitInterval

            if data is None:
                continue

            if self._dont_answer:
                self._dont_answer = False
                continue

            self._received_lines += 1

            # strip checksum
            if b"*" in data:
                checksum = int(data[data.rfind(b"*") + 1 :])
                data = data[: data.rfind(b"*")]
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
                elif (
                    linenumber == 105
                    and self._triggerResendWithTimeoutAt105
                    and not self._writingToSd
                ):
                    # simulate a resend with timeout at line 105
                    self._triggerResendWithTimeoutAt105 = False
                    self._triggerResend(expected=105)
                    self._dont_answer = True
                    self.lastN = linenumber
                    continue
                elif (
                    linenumber == 110
                    and self._triggerResendWithMissingLinenoAt110
                    and not self._writingToSd
                ):
                    self._triggerResendWithMissingLinenoAt110 = False
                    self._send(self._error("lineno_missing", self.lastN))
                    continue
                elif (
                    linenumber == 115
                    and self._triggerResendWithChecksumMismatchAt115
                    and not self._writingToSd
                ):
                    self._triggerResendWithChecksumMismatchAt115 = False
                    self._triggerResend(checksum=True)
                    continue
                elif len(self._prepared_errors):
                    prepared = self._prepared_errors.pop(0)
                    if callable(prepared):
                        prepared(linenumber, self.lastN, data)
                        continue
                    elif isinstance(prepared, str):
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
                    debug_command = data[len("!!DEBUG:") :].strip()
                self._debugTrigger(debug_command)
                continue

            if self._resend_every_n and self._received_lines % self._resend_every_n == 0:
                self._triggerResend(checksum=True)
                continue

            # shortcut for writing to SD
            if (
                self._writingToSd
                and self._writingToSdHandle is not None
                and "M29" not in data
            ):
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
                if self._broken_klipper_connection:
                    self._send("!! Lost communication with MCU 'mcu'")
                    self._sendOk()
                    continue

                command = command_match.group(0)
                letter = command_match.group(1)

                if self._locked and command != "M511":
                    self._send("echo:Printer locked! (Unlock with M511 or LCD)")
                    self._sendOk()
                    continue

                try:
                    # if we have a method _gcode_G, _gcode_M or _gcode_T, execute that first
                    letter_handler = f"_gcode_{letter}"
                    if hasattr(self, letter_handler):
                        code = command_match.group(2)
                        handled = getattr(self, letter_handler)(code, data)
                        if handled:
                            continue

                    # then look for a method _gcode_<command> and execute that if it exists
                    command_handler = f"_gcode_{command}"
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
                            self._send(
                                "// sleeping for {interval} seconds".format(
                                    interval=interval
                                )
                            )
                            time.sleep(interval)

            # if we are sending oks after command output, send it now
            if len(data.strip()) > 0 and not self._okBeforeCommandOutput:
                self._sendOk()

        self._logger.info("Closing down read loop")

    ##~~ command implementations

    # noinspection PyUnusedLocal
    def _gcode_T(self, code: str, data: str) -> None:
        t = int(code)
        if 0 <= t < self.extruderCount:
            self.currentExtruder = t
            self._send("Active Extruder: %d" % self.currentExtruder)
        else:
            self._send(f"echo:T{t} Invalid extruder ")

    # noinspection PyUnusedLocal
    def _gcode_F(self, code: str, data: str) -> bool:
        if self._supportF:
            self._send("echo:changed F value")
            return False
        else:
            self._send(self._error("command_unknown", "F"))
            return True

    def _gcode_M104(self, data: str) -> None:
        self._parseHotendCommand(data)

    def _gcode_M109(self, data: str) -> None:
        self._parseHotendCommand(data, wait=True, support_r=True)

    def _gcode_M140(self, data: str) -> None:
        self._parseBedCommand(data)

    def _gcode_M190(self, data: str) -> None:
        self._parseBedCommand(data, wait=True, support_r=True)

    def _gcode_M141(self, data: str) -> None:
        self._parseChamberCommand(data)

    def _gcode_M191(self, data: str) -> None:
        self._parseChamberCommand(data, wait=True, support_r=True)

    # noinspection PyUnusedLocal
    def _gcode_M105(self, data: str) -> bool:
        self._processTemperatureQuery()
        return True

    # noinspection PyUnusedLocal
    def _gcode_M20(self, data: str) -> None:
        if self._sdCardReady:
            self._listSd(incl_long="L" in data, incl_timestamp="T" in data)

    # noinspection PyUnusedLocal
    def _gcode_M21(self, data: str) -> None:
        self._sdCardReady = True
        self._send("SD card ok")

    # noinspection PyUnusedLocal
    def _gcode_M22(self, data: str) -> None:
        self._sdCardReady = False

    def _gcode_M23(self, data: str) -> None:
        if self._sdCardReady:
            filename = data.split(None, 1)[1].strip()
            self._selectSdFile(filename)

    # noinspection PyUnusedLocal
    def _gcode_M24(self, data: str) -> None:
        if self._sdCardReady:
            self._startSdPrint()

    # noinspection PyUnusedLocal
    def _gcode_M25(self, data: str) -> None:
        if self._sdCardReady:
            self._pauseSdPrint()

    def _gcode_M26(self, data: str) -> None:
        if self._sdCardReady:
            pos = int(re.search(r"S([0-9]+)", data).group(1))
            self._setSdPos(pos)

    def _gcode_M27(self, data: str) -> None:
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

    def _gcode_M28(self, data: str) -> None:
        if self._sdCardReady:
            filename = data.split(None, 1)[1].strip()
            self._writeSdFile(filename)

    # noinspection PyUnusedLocal
    def _gcode_M29(self, data: str) -> None:
        if self._sdCardReady:
            self._finishSdFile()

    def _gcode_M30(self, data: str) -> None:
        if self._sdCardReady:
            filename = data.split(None, 1)[1].strip()
            self._deleteSdFile(filename)

    def _gcode_M33(self, data: str) -> None:
        if self._sdCardReady:
            filename = data.split(None, 1)[1].strip()
            if filename.startswith("/"):
                filename = filename[1:]
            files = self._mappedSdList()
            file = files.get(filename.lower())
            if file is not None:
                self._send(file["name"])

    def _gcode_M113(self, data: str) -> None:
        matchS = re.search(r"S([0-9]+)", data)
        if matchS is not None:
            interval = int(matchS.group(1))
            if 0 <= interval <= 60:
                self._busyInterval = interval

    # noinspection PyUnusedLocal
    def _gcode_M114(self, data: str) -> bool:
        output = self._generatePositionOutput()
        if not self._okBeforeCommandOutput:
            ok = self._ok()
            if ok:
                output = f"{self._ok()} {output}"
        self._send(output)
        return True

    # noinspection PyUnusedLocal
    def _gcode_M115(self, data: str) -> None:
        output = self._m115FormatString.format(firmware_name=self._firmwareName)
        self._send(output)

        if self._settings.get_boolean(["m115ReportCapabilities"]):
            for cap, enabled in self._capabilities.items():
                self._send("Cap:{}:{}".format(cap.upper(), "1" if enabled else "0"))

    def _gcode_M117(self, data: str) -> None:
        # we'll just use this to echo a message, to allow playing around with pause triggers
        if self._echoOnM117:
            try:
                result = re.search(r"M117\s+(.*)", data).group(1)
                self._send(f"echo:{result}")
            except AttributeError:
                self._send("echo:")

    def _gcode_M118(self, data: str) -> None:
        match = re.search(r"M118 (?:(?P<parameter>A1|E1|Pn[012])\s)?(?P<text>.*)", data)
        if not match:
            self._send("Unrecognized command parameters for M118")
        else:
            result = match.groupdict()
            text = result["text"]
            parameter = result["parameter"]

            if parameter == "A1":
                self._send(f"//{text}")
            elif parameter == "E1":
                self._send(f"echo:{text}")
            else:
                self._send(text)

    def _gcode_M154(self, data: str) -> None:
        matchS = re.search(r"S([0-9]+)", data)
        if matchS is not None:
            interval = int(matchS.group(1))
            if self._pos_reporter is not None:
                self._pos_reporter.cancel()

            if interval > 0:
                self._pos_reporter = RepeatedTimer(
                    interval, lambda: self._send(self._generatePositionOutput())
                )
                self._pos_reporter.start()
            else:
                self._pos_reporter = None

    def _gcode_M155(self, data: str) -> None:
        matchS = re.search(r"S([0-9]+)", data)
        if matchS is not None:
            interval = int(matchS.group(1))
            if self._temperature_reporter is not None:
                self._temperature_reporter.cancel()

            if interval > 0:
                self._temperature_reporter = RepeatedTimer(
                    interval, lambda: self._send(self._generateTemperatureOutput())
                )
                self._temperature_reporter.start()
            else:
                self._temperature_reporter = None

    def _gcode_M220(self, data: str) -> None:
        matchS = re.search(r"S([0-9]+)", data)
        if matchS is not None:
            self._feedrate_multiplier = float(matchS.group(1))

    def _gcode_M221(self, data: str) -> None:
        matchS = re.search(r"S([0-9]+)", data)
        if matchS is not None:
            self._flowrate_multiplier = float(matchS.group(1))

    # noinspection PyUnusedLocal
    def _gcode_M400(self, data: str) -> None:
        self.buffered.join()

    # noinspection PyUnusedLocal
    def _gcode_M600(self, data: str) -> None:
        self._send("//action:paused")
        self._showPrompt(
            "Heater Timeout",
            [
                "Reheat",
            ],
        )
        self._setBusy("paused for user")
        return True  # handled as we don't want to send an ok now, only when finishing the busy

    # noinspection PyUnusedLocal
    def _gcode_M876(self, data: str) -> None:
        self._hidePrompt()
        if self._busy == "paused for user":
            self._busy = None

    # noinspection PyUnusedLocal
    def _gcode_M999(self, data: str) -> None:
        # mirror Marlin behaviour
        self._send("Resend: 1")

    # noinspection PyUnusedLocal
    def _gcode_G20(self, data: str) -> None:
        self._unitModifier = 1 / 2.54
        if self._lastX is not None:
            self._lastX *= 2.54
        if self._lastY is not None:
            self._lastY *= 2.54
        if self._lastZ is not None:
            self._lastZ *= 2.54
        if self._lastE is not None:
            self._lastE = [e * 2.54 if e is not None else None for e in self._lastE]

    # noinspection PyUnusedLocal
    def _gcode_G21(self, data: str) -> None:
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
    def _gcode_G90(self, data: str) -> None:
        self._relative = False

    # noinspection PyUnusedLocal
    def _gcode_G91(self, data: str) -> None:
        self._relative = True

    def _gcode_G92(self, data: str) -> None:
        self._setPosition(data)

    def _gcode_G28(self, data: str) -> None:
        self._home(data)

    def _gcode_G0(self, data: str) -> None:
        # simulate reprap buffered commands via a Queue with maxsize which internally simulates the moves
        self.buffered.put(data)

    _gcode_G1 = _gcode_G0
    _gcode_G2 = _gcode_G0
    _gcode_G3 = _gcode_G0

    def _gcode_G4(self, data: str) -> None:
        matchS = re.search(r"S([0-9]+)", data)
        matchP = re.search(r"P([0-9]+)", data)

        _timeout = 0
        if matchP:
            _timeout = float(matchP.group(1)) / 1000
        elif matchS:
            _timeout = float(matchS.group(1))

        if self._sendBusy and self._busyInterval > 0:
            until = time.monotonic() + _timeout
            while time.monotonic() < until:
                time.sleep(self._busyInterval)
                self._send("busy:processing")
        else:
            time.sleep(_timeout)

    # noinspection PyUnusedLocal
    def _gcode_G33(self, data: str) -> None:
        self._send("G33 Auto Calibrate")
        self._send("Will take ~60s")
        timeout = 60

        if self._sendBusy and self._busyInterval > 0:
            until = time.monotonic() + timeout
            while time.monotonic() < until:
                time.sleep(self._busyInterval)
                self._send("busy:processing")
        else:
            time.sleep(timeout)

    # Passcode Feature - lock with M510, unlock with M511 P<passcode>.
    # https://marlinfw.org/docs/gcode/M510.html / https://marlinfw.org/docs/gcode/M511.html

    def _gcode_M510(self, data: str) -> None:
        self._locked = True

    def _gcode_M511(self, data: str) -> None:
        if self._locked:
            matchP = re.search(r"P([0-9]+)", data)
            if matchP:
                passcode = matchP.group(1)
                if passcode == self._settings.get(["passcode"]):
                    self._locked = False
                else:
                    self._send("Incorrect passcode")

    # EEPROM management commands

    def _gcode_M500(self, data: str) -> None:
        # Stores settings to disk
        if self._virtual_eeprom:
            self._virtual_eeprom.save_settings()
        else:
            self._send(self._error("command_unknown", "M500"))

    def _gcode_M501(self, data: str) -> None:
        # Read from EEPROM
        if self._virtual_eeprom:
            self._virtual_eeprom.read_settings()
            for line in self._construct_eeprom_values():
                self._send(line)
        else:
            self._send(self._error("command_unknown", "M501"))

    def _gcode_M502(self, data: str) -> None:
        # reset to default values
        if self._virtual_eeprom:
            self._virtual_eeprom.load_defaults()
            for line in self._construct_eeprom_values():
                self._send(line)
        else:
            self._send(self._error("command_unknown", "M502"))

    def _gcode_M503(self, data: str) -> None:
        # echo all eeprom data
        if self._virtual_eeprom and self._support_M503:
            for line in self._construct_eeprom_values():
                self._send(line)
        else:
            self._send(self._error("command_unknown", "M503"))

    def _gcode_M504(self, data: str) -> None:
        if self._virtual_eeprom:
            self._send("echo:EEPROM OK")
        else:
            self._send(self._error("command_unknown", "M504"))

    # EEPROM settings commands

    def _gcode_M92(self, data: str) -> None:
        # Steps per unit
        if not self._virtual_eeprom:
            self._send(self._error("command_unknown", "M92"))
            return
        if not self._check_param_letters("XYZE", data):
            # no params, report values
            self._send(self._construct_echo_values("steps", "XYZE"))
        else:
            for key, value in self._parse_eeprom_params("XYZE", data).items():
                self._virtual_eeprom.eeprom["steps"]["params"][key] = float(value)

    def _gcode_M203(self, data: str) -> None:
        # Maximum feedrates (units/s)
        if not self._virtual_eeprom:
            self._send(self._error("command_unknown", "M203"))
            return
        if not self._check_param_letters("XYZE", data):
            # no params, report values
            self._send(self._construct_echo_values("feedrate", "XYZE"))
        else:
            for key, value in self._parse_eeprom_params("XYZE", data).items():
                self._virtual_eeprom.eeprom["feedrate"]["params"][key] = float(value)

    def _gcode_M201(self, data: str) -> None:
        # Maximum Acceleration (units/s2)
        if not self._virtual_eeprom:
            self._send(self._error("command_unknown", "M201"))
            return
        if not self._check_param_letters("EXYZ", data):
            # no params, report values
            self._send(self._construct_echo_values("max_accel", "EXYZ"))
        else:
            for key, value in self._parse_eeprom_params("EXYZ", data).items():
                self._virtual_eeprom.eeprom["max_accel"]["params"][key] = float(value)

    def _gcode_M204(self, data: str) -> None:
        # Starting Acceleration (units/s2)
        if not self._virtual_eeprom:
            self._send(self._error("command_unknown", "M204"))
            return
        if not self._check_param_letters("PRTS", data):
            # no params, report values
            self._send(self._construct_echo_values("start_accel", "PRTS"))
        else:
            for key, value in self._parse_eeprom_params("PRTS", data).items():
                self._virtual_eeprom.eeprom["start_accel"]["params"][key] = float(value)

    def _gcode_M206(self, data: str) -> None:
        # Home offset
        if not self._virtual_eeprom:
            self._send(self._error("command_unknown", "M206"))
            return
        if not self._check_param_letters("XYZ", data):
            # no params, report values
            self._send(self._construct_echo_values("home_offset", "XYZ"))
        else:
            for key, value in self._parse_eeprom_params("XYZ", data).items():
                self._virtual_eeprom.eeprom["home_offset"]["params"][key] = float(value)

    def _gcode_M851(self, data: str) -> None:
        if not self._virtual_eeprom:
            self._send(self._error("command_unknown", "M851"))
            return
        if not self._check_param_letters("XYZ", data):
            self._send(self._construct_echo_values("probe_offset", "XYZ"))
        else:
            for key, value in self._parse_eeprom_params("XYZ", data).items():
                self._virtual_eeprom.eeprom["probe_offset"]["params"][key] = float(value)

    def _gcode_M200(self, data: str) -> None:
        if not self._virtual_eeprom:
            self._send(self._error("command_unknown", "M200"))
            return
        if not self._check_param_letters("DS", data):
            self._send(self._construct_echo_values("filament", "DS"))
        else:
            for key, value in self._parse_eeprom_params("DS", data).items():
                self._virtual_eeprom.eeprom["filament"]["params"][key] = float(value)

    def _gcode_M666(self, data: str) -> None:
        if not self._virtual_eeprom:
            self._send(self._error("command_unknown", "M666"))
            return
        if not self._check_param_letters("XYZ", data):
            self._send(self._construct_echo_values("endstop", "XYZ"))
        else:
            for key, value in self._parse_eeprom_params("XYZ", data).items():
                self._virtual_eeprom.eeprom["endstop"]["params"][key] = float(value)

    def _gcode_M665(self, data: str) -> None:
        if not self._virtual_eeprom:
            self._send(self._error("command_unknown", "M665"))
            return
        if not self._check_param_letters("BHLRSXYZ", data):
            self._send(self._construct_echo_values("delta", "BHLRSXYZ"))
        else:
            for key, value in self._parse_eeprom_params("BHLRSXYZ", data).items():
                self._virtual_eeprom.eeprom["delta"]["params"][key] = float(value)

    def _gcode_M420(self, data: str) -> None:
        if not self._virtual_eeprom:
            self._send(self._error("command_unknown", "M420"))
            return
        if not self._check_param_letters("SZ", data):
            self._send(self._construct_echo_values("auto_level", "SZ"))
        else:
            for key, value in self._parse_eeprom_params("SZ", data).items():
                self._virtual_eeprom.eeprom["auto_level"]["params"][key] = float(value)

    def _gcode_M900(self, data: str) -> None:
        if not self._virtual_eeprom:
            self._send(self._error("command_unknown", "M900"))
            return
        if not self._check_param_letters("K", data):
            self._send(self._construct_echo_values("linear_advance", "K"))
        else:
            for key, value in self._parse_eeprom_params("K", data).items():
                self._virtual_eeprom.eeprom["linear_advance"]["params"][key] = float(
                    value
                )

    def _gcode_M205(self, data: str) -> None:
        if not self._virtual_eeprom:
            self._send(self._error("command_unknown", "M205"))
            return
        if not self._check_param_letters("BSTXYZEJ", data):
            self._send(self._construct_echo_values("advanced", "BSTXYZEJ"))
        else:
            for key, value in self._parse_eeprom_params("BSTXYZEJ", data).items():
                self._virtual_eeprom.eeprom["advanced"]["params"][key] = float(value)

    def _gcode_M145(self, data: str) -> None:
        # M145 is a bit special, since it refers to 2 sets of values under the same params
        if not self._virtual_eeprom:
            self._send(self._error("command_unknown", "M145"))
            return
        if not self._check_param_letters("S", data):
            config = self._virtual_eeprom.eeprom["material"]
            for material in ["0", "1"]:
                line = "echo: " + config["command"] + " S" + material
                for param, saved_value in config["params"][material].items():
                    line = line + " " + param + str(saved_value)
                self._send(line)
        else:
            parsed = self._parse_eeprom_params("SBFH", data)
            try:
                material_no = parsed["S"]
            except KeyError:
                self._send("Need to specify a material (S0/S1)")
                return
            for key, value in parsed.items():
                if key == "S":
                    pass
                else:
                    self._virtual_eeprom.eeprom["material"]["params"][material_no][
                        key
                    ] = float(value)

    def _gcode_M301(self, data: str) -> None:
        if not self._virtual_eeprom:
            self._send(self._error("command_unknown", "M301"))
            return
        if not self._check_param_letters("PID", data):
            self._send(self._construct_echo_values("pid", "PID"))
        else:
            for key, value in self._parse_eeprom_params("PID", data).items():
                self._virtual_eeprom.eeprom["pid"]["params"][key] = float(value)

    def _gcode_M304(self, data: str) -> None:
        if not self._virtual_eeprom:
            self._send(self._error("command_unknown", "M304"))
            return
        if not self._check_param_letters("PID", data):
            self._send(self._construct_echo_values("pid_bed", "PID"))
        else:
            for key, value in self._parse_eeprom_params("PID", data).items():
                self._virtual_eeprom.eeprom["pid_bed"]["params"][key] = float(value)

    # EEPROM Helpers

    def _construct_eeprom_values(self):
        lines = []
        # Iterate over the dict, and echo each command/value etc.
        for key, value in self._virtual_eeprom.eeprom.items():
            # echo, description
            lines.append("echo:; " + value["description"])
            if key == "material":  # material gets special handling...
                lines.extend(self._m145_handling())
            else:
                # echo, command, params
                line = "echo: " + value["command"]
                for param, saved_value in value["params"].items():
                    line = line + " " + param + str(saved_value)
                lines.append(line)
        return lines

    def _m145_handling(self):
        config = self._virtual_eeprom.eeprom["material"]
        lines = []
        for material in ["0", "1"]:
            line = "echo: " + config["command"] + " S" + material
            for param, saved_value in config["params"][material].items():
                line = line + " " + param + str(saved_value)
            lines.append(line)
        return lines

    @staticmethod
    def _parse_eeprom_params(letters: str, line: str) -> dict:
        # letters provided in a string (eg "XYZ") and line (eg. M92 X20 Y20 Z20)
        # are parsed into a dict
        params = list(letters)
        output = {}
        for param in params:
            match = re.search(param + r"([0-9]+(\.[0-9]{1,2})?)", line)
            if match:
                output[param] = match.group(1)
        return output

    def _construct_echo_values(self, name, letters):
        # Construct a line like 'echo: M92 X100 Y120 Z130' based on type & letters
        config = self._virtual_eeprom.eeprom[name]
        line = "echo: " + config["command"]
        for param in list(letters):
            line = line + " " + param + str(config["params"][param])
        return line

    @staticmethod
    def _check_param_letters(letters, data):
        # Checks if any of the params (letters) are included in data
        # Purely for saving typing :)
        for param in list(letters):
            if param in data:
                return True

    ##~~ further helpers

    # noinspection PyMethodMayBeStatic
    def _calculate_checksum(self, line: bytes) -> int:
        checksum = 0
        for c in bytearray(line):
            checksum ^= c
        return checksum

    def _kill(self):
        if not self._supportM112:
            return
        self._killed = True
        self._send("echo:EMERGENCY SHUTDOWN DETECTED. KILLED.")

    def _triggerResend(
        self, expected: int = None, actual: int = None, checksum: int = None
    ) -> None:
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

    def _debugTrigger(self, data: str) -> None:
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
            resend_ratio <int:percentage>
            | Sets the resend ratio to the given percentage, simulating noisy lines.
            | Set to 0 to disable noise simulation.
            toggle_klipper_connection
            | Toggles the Klipper connection state. If disabled, the printer will
            | respond to all commands with "!! Lost communication with MCU 'mcu'"

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
            unbusy
            | Unsets the busy loop.
            """
            for line in usage.split("\n"):
                self._send(f"echo: {line.strip()}")
        elif data == "action_pause":
            self._send("// action:pause")
        elif data == "action_resume":
            self._send("// action:resume")
        elif data == "action_disconnect":
            self._send("// action:disconnect")
        elif data == "dont_answer":
            self._dont_answer = True
        elif data == "toggle_klipper_connection":
            self._broken_klipper_connection = not self._broken_klipper_connection
        elif data == "trigger_resend_lineno":
            self._prepared_errors.append(
                lambda cur, last, ln: self._triggerResend(expected=last, actual=last + 1)
            )
        elif data == "trigger_resend_checksum":
            self._prepared_errors.append(
                lambda cur, last, ln: self._triggerResend(expected=last, checksum=True)
            )
        elif data == "trigger_missing_checksum":
            self._prepared_errors.append(
                lambda cur, last, ln: self._triggerResend(expected=last, checksum=False)
            )
        elif data == "trigger_missing_lineno":
            self._prepared_errors.append(
                lambda cur, last, ln: self._send(self._error("lineno_missing", last))
            )
        elif data == "trigger_fatal_error_marlin":
            self._send("Error:Thermal Runaway, system stopped! Heater_ID: bed")
            self._send("Error:Printer halted. kill() called!")
        elif data == "trigger_fatal_error_repetier":
            self._send(
                "fatal: Heater/sensor error - Printer stopped and heaters disabled due to this error. Fix error and restart with M999."
            )
        elif data == "drop_connection":
            self._debug_drop_connection = True
        elif data == "reset":
            self._reset()
        elif data == "unbusy":
            self._setUnbusy()
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
                resend_ratio_match = VirtualPrinter.resend_ratio_regex.match(data)

                if sleep_match is not None:
                    interval = int(sleep_match.group(1))
                    self._send(f"// sleeping for {interval} seconds")
                    self._debug_sleep = interval
                elif sleep_after_match is not None:
                    command = sleep_after_match.group(1)
                    interval = int(sleep_after_match.group(2))
                    self._sleepAfter[command] = interval
                    self._send(
                        f"// going to sleep {interval} seconds after each {command}"
                    )
                elif sleep_after_next_match is not None:
                    command = sleep_after_next_match.group(1)
                    interval = int(sleep_after_next_match.group(2))
                    self._sleepAfterNext[command] = interval
                    self._send(
                        f"// going to sleep {interval} seconds after next {command}"
                    )
                elif custom_action_match is not None:
                    action = custom_action_match.group(1)
                    params = custom_action_match.group(2)
                    params = params.strip() if params is not None else ""
                    self._send(f"// action:{action} {params}".strip())
                elif prepare_ok_match is not None:
                    ok = prepare_ok_match.group(1)
                    self._prepared_oks.append(ok)
                elif send_match is not None:
                    self._send(send_match.group(1))
                elif set_ambient_match is not None:
                    self._ambient_temperature = float(set_ambient_match.group(1))
                    self._send(
                        "// set ambient temperature to {}".format(
                            self._ambient_temperature
                        )
                    )
                elif start_sd_match is not None:
                    self._selectSdFile(start_sd_match.group(1), check_already_open=True)
                    self._startSdPrint()
                elif select_sd_match is not None:
                    self._selectSdFile(select_sd_match.group(1))
                elif resend_ratio_match is not None:
                    resend_ratio = int(resend_ratio_match.group(1))
                    if 0 <= resend_ratio <= 100:
                        self._calculate_resend_every_n(resend_ratio)
            except Exception:
                self._logger.exception("While handling %r", data)

    def _listSd(self, incl_long=False, incl_timestamp=False):
        line = "{dosname}"
        if self._settings.get_boolean(["sdFiles", "size"]):
            line += " {size}"
            if self._settings.get_boolean(["sdFiles", "timestamp"]) or incl_timestamp:
                line += " {timestamp}"
            if self._settings.get_boolean(["sdFiles", "longname"]) or incl_long:
                if self._settings.get_boolean(["sdFiles", "longname_quoted"]):
                    line += ' "{name}"'
                else:
                    line += " {name}"

        files = self._mappedSdList()
        items = map(lambda x: line.format(**x), files.values())

        self._send("Begin file list")
        for item in items:
            self._send(item)
        self._send("End file list")

    def _mappedSdList(self) -> collections.OrderedDict:
        result = collections.OrderedDict()
        for entry in os.scandir(self._virtualSd):
            if not entry.is_file():
                continue
            dosname = get_dos_filename(
                entry.name, existing_filenames=list(result.keys())
            ).lower()
            if entry.name.startswith("."):
                dosname = "." + dosname
            result[dosname] = {
                "name": entry.name,
                "path": entry.path,
                "dosname": dosname,
                "size": entry.stat().st_size,
                "timestamp": unix_timestamp_to_m20_timestamp(entry.stat().st_mtime),
            }
        return result

    def _selectSdFile(self, filename: str, check_already_open: bool = False) -> None:
        if filename.startswith("/"):
            filename = filename[1:]

        files = self._mappedSdList()
        file = files.get(filename)
        if (
            file is None
            or not os.path.exists(file["path"])
            or not os.path.isfile(file["path"])
        ):
            self._send("open failed, File: %s." % filename)
            return

        if self._selectedSdFile == file["path"] and check_already_open:
            return

        self._selectedSdFile = file["path"]
        self._selectedSdFileSize = file["size"]
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
            self._send(
                "SD printing byte %d/%d"
                % (self._selectedSdFilePos, self._selectedSdFileSize)
            )
        else:
            self._send("Not SD printing")

    def _generatePositionOutput(self) -> str:
        m114FormatString = self._settings.get(["m114FormatString"])
        e = {index: value for index, value in enumerate(self._lastE)}
        e["current"] = self._lastE[self.currentExtruder]
        e["all"] = " ".join(
            [
                f"E{num}:{self._lastE[self.currentExtruder]}"
                for num in range(self.extruderCount)
            ]
        )
        output = m114FormatString.format(
            x=self._lastX,
            y=self._lastY,
            z=self._lastZ,
            e=e,
            f=self._lastF,
            a=int(self._lastX * 100),
            b=int(self._lastY * 100),
            c=int(self._lastZ * 100),
        )
        return output

    def _generateTemperatureOutput(self) -> str:
        if self._settings.get_boolean(["repetierStyleTargetTemperature"]):
            template = self._settings.get(["m105NoTargetFormatString"])
        else:
            template = self._settings.get(["m105TargetFormatString"])

        temps = collections.OrderedDict()

        # send simulated temperature data
        if self.temperatureCount > 1:
            if self._settings.get_boolean(["smoothieTemperatureReporting"]):
                temps["T"] = (self.temp[0], self.targetTemp[0])
            elif self._settings.get_boolean(["includeCurrentToolInTemps"]):
                temps["T"] = (
                    self.temp[self.currentExtruder],
                    self.targetTemp[self.currentExtruder],
                )

            for i in range(len(self.temp)):
                if i == 0 and self._settings.get_boolean(
                    ["smoothieTemperatureReporting"]
                ):
                    continue
                temps[f"T{i}"] = (self.temp[i], self.targetTemp[i])

            if self._settings.get_boolean(["hasBed"]):
                temps["B"] = (self.bedTemp, self.bedTargetTemp)

            if self._settings.get_boolean(["hasChamber"]):
                temps["C"] = (self.chamberTemp, self.chamberTargetTemp)

        else:
            heater = "T"
            if self._settings.get_boolean(["klipperTemperatureReporting"]):
                heater = "T0"

            temps[heater] = (self.temp[0], self.targetTemp[0])

            if self._settings.get_boolean(["hasBed"]):
                temps["B"] = (self.bedTemp, self.bedTargetTemp)

            if self._settings.get_boolean(["hasChamber"]):
                temps["C"] = (self.chamberTemp, self.chamberTargetTemp)

        output = " ".join(
            map(
                lambda x: template.format(heater=x[0], actual=x[1][0], target=x[1][1]),
                temps.items(),
            )
        )
        output += " @:64\n"
        return output

    def _processTemperatureQuery(self):
        includeOk = not self._okBeforeCommandOutput
        output = self._generateTemperatureOutput()

        if includeOk:
            ok = self._ok()
            if ok:
                output = f"{ok} {output}"
        self._send(output)

    def _parseHotendCommand(
        self, line: str, wait: bool = False, support_r: bool = False
    ) -> None:
        only_wait_if_higher = True
        tool = 0
        toolMatch = re.search(r"T([0-9]+)", line)
        if toolMatch:
            tool = int(toolMatch.group(1))

        if tool >= self.temperatureCount:
            return

        try:
            self.targetTemp[tool] = float(re.search(r"S([0-9]+)", line).group(1))
        except Exception:
            if support_r:
                try:
                    self.targetTemp[tool] = float(re.search(r"R([0-9]+)", line).group(1))
                    only_wait_if_higher = False
                except Exception:
                    pass

        if wait:
            self._waitForHeatup("tool%d" % tool, only_wait_if_higher)
        if self._settings.get_boolean(["repetierStyleTargetTemperature"]):
            self._send("TargetExtr%d:%d" % (tool, self.targetTemp[tool]))

    def _parseBedCommand(self, line: str, wait: bool = False, support_r: bool = False):
        if not self._settings.get_boolean(["hasBed"]):
            return

        only_wait_if_higher = True
        try:
            self.bedTargetTemp = float(re.search(r"S([0-9]+)", line).group(1))
        except Exception:
            if support_r:
                try:
                    self.bedTargetTemp = float(re.search(r"R([0-9]+)", line).group(1))
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
            self.chamberTargetTemp = float(re.search("S([0-9]+)", line).group(1))
        except Exception:
            if support_r:
                try:
                    self.chamberTargetTemp = float(re.search("R([0-9]+)", line).group(1))
                    only_wait_if_higher = False
                except Exception:
                    pass

        if wait:
            self._waitForHeatup("chamber", only_wait_if_higher)

    def _performMove(self, line: str) -> None:
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

        speedXYZ = self._lastF * (self._feedrate_multiplier / 100)
        speedE = self._lastF * (self._flowrate_multiplier / 100)
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
                    duration = max(duration, x * self._unitModifier / speedXYZ * 60)
                else:
                    duration = max(
                        duration, (x - self._lastX) * self._unitModifier / speedXYZ * 60
                    )

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
                    duration = max(duration, y * self._unitModifier / speedXYZ * 60)
                else:
                    duration = max(
                        duration, (y - self._lastY) * self._unitModifier / speedXYZ * 60
                    )

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
                    duration = max(duration, z * self._unitModifier / speedXYZ * 60)
                else:
                    duration = max(
                        duration, (z - self._lastZ) * self._unitModifier / speedXYZ * 60
                    )

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
                    duration = max(duration, e * self._unitModifier / speedE * 60)
                else:
                    duration = max(
                        duration, (e - lastE) * self._unitModifier / speedE * 60
                    )

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

    def _setPosition(self, line: str) -> None:
        matchX = re.search(r"X(-?[0-9.]+)", line)
        matchY = re.search(r"Y(-?[0-9.]+)", line)
        matchZ = re.search(r"Z(-?[0-9.]+)", line)
        matchE = re.search(r"E(-?[0-9.]+)", line)

        if matchX is None and matchY is None and matchZ is None and matchE is None:
            self._lastX = self._lastY = self._lastZ = self._lastE[
                self.currentExtruder
            ] = 0
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
            self._lastX = self._lastY = self._lastZ = self._lastE[
                self.currentExtruder
            ] = 0
        else:
            if x:
                self._lastX = 0
            if y:
                self._lastY = 0
            if z:
                self._lastZ = 0
            if e:
                self._lastE = 0

    def _writeSdFile(self, filename: str) -> None:
        filename = filename
        if filename.startswith("/"):
            filename = filename[1:]
        file = os.path.join(self._virtualSd, filename.lower())
        if os.path.exists(file):
            if os.path.isfile(file):
                os.remove(file)
            else:
                self._send("error writing to file")

        handle = None
        try:
            handle = open(file, "wt", encoding="utf-8")
        except Exception:
            self._send("error writing to file")
        self._writingToSdHandle = handle
        self._writingToSdFile = file
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
        # Most printers don't have RTC and set some ancient date
        # by default. Emulate that using 2000-01-01 01:00:00
        # (taken from prusa firmware behaviour)
        st = os.stat(self._writingToSdFile)
        os.utime(self._writingToSdFile, (st.st_atime, 946684800))
        self._writingToSdFile = None
        self._send("Done saving file")

    def _sdPrintingWorker(self):
        self._selectedSdFilePos = 0
        try:
            with open(self._selectedSdFile, encoding="utf-8") as f:
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
                    if "M104" in line or "M109" in line:
                        self._parseHotendCommand(line, wait="M109" in line)
                    elif "M140" in line or "M190" in line:
                        self._parseBedCommand(line, wait="M190" in line)
                    elif (
                        line.startswith("G0")
                        or line.startswith("G1")
                        or line.startswith("G2")
                        or line.startswith("G3")
                    ):
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

    def _waitForHeatup(self, heater: str, only_wait_if_higher: bool) -> None:
        delta = 1
        delay = 1
        last_busy = time.monotonic()

        self._heatingUp = True
        try:
            if heater.startswith("tool"):
                toolNum = int(heater[len("tool") :])
                test = lambda: self.temp[toolNum] < self.targetTemp[toolNum] - delta or (
                    not only_wait_if_higher
                    and self.temp[toolNum] > self.targetTemp[toolNum] + delta
                )
                output = lambda: "T:%0.2f" % self.temp[toolNum]
            elif heater == "bed":
                test = lambda: self.bedTemp < self.bedTargetTemp - delta or (
                    not only_wait_if_higher and self.bedTemp > self.bedTargetTemp + delta
                )
                output = lambda: "B:%0.2f" % self.bedTemp
            elif heater == "chamber":
                test = lambda: self.chamberTemp < self.chamberTargetTemp - delta or (
                    not only_wait_if_higher
                    and self.chamberTemp > self.chamberTargetTemp + delta
                )
                output = lambda: "C:%0.2f" % self.chamberTemp
            else:
                return

            while not self._killed and self._heatingUp and test():
                self._simulateTemps(delta=delta)
                self._send(output())
                if self._sendBusy and time.monotonic() - last_busy >= self._busyInterval:
                    self._send("echo:busy: processing")
                    last_busy = time.monotonic()
                time.sleep(delay)
        except AttributeError:
            if self.outgoing is not None:
                raise
        finally:
            self._heatingUp = False

    def _deleteSdFile(self, filename: str) -> None:
        if filename.startswith("/"):
            filename = filename[1:]
        files = self._mappedSdList()
        file = files.get(filename)
        if (
            file is not None
            and os.path.exists(file["path"])
            and os.path.isfile(file["path"])
        ):
            os.remove(file["path"])

    def _simulateTemps(self, delta=0.5):
        timeDiff = self.lastTempAt - time.monotonic()
        self.lastTempAt = time.monotonic()

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
            self.temp[i] = simulate(
                self.temp[i], self.targetTemp[i], self._ambient_temperature
            )
        self.bedTemp = simulate(
            self.bedTemp, self.bedTargetTemp, self._ambient_temperature
        )
        self.chamberTemp = simulate(
            self.chamberTemp, self.chamberTargetTemp, self._ambient_temperature
        )

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

    def _setBusy(self, reason="processing"):
        if not self._sendBusy:
            return

        def loop():
            while self._busy:
                self._send(f"echo:busy {self._busy}")
                time.sleep(self._busyInterval)
            self._sendOk()

        self._busy = reason
        self._busy_loop = threading.Thread(target=loop)
        self._busy_loop.daemon = True
        self._busy_loop.start()

    def _setUnbusy(self):
        self._busy = None

    def _showPrompt(self, text, choices):
        self._hidePrompt()
        self._send(f"//action:prompt_begin {text}")
        for choice in choices:
            self._send(f"//action:prompt_button {choice}")
        self._send("//action:prompt_show")

    def _hidePrompt(self):
        self._send("//action:prompt_end")

    def write(self, data: bytes) -> int:
        data = to_bytes(data, errors="replace")
        u_data = to_unicode(data, errors="replace")

        if self._debug_awol:
            return len(data)

        if self._debug_drop_connection:
            self._logger.info(
                "Debug drop of connection requested, raising SerialTimeoutException"
            )
            raise SerialTimeoutException()

        with self._incoming_lock:
            if self.incoming is None or self.outgoing is None:
                return 0

            if b"M112" in data and self._supportM112:
                self._seriallog.info(f"<<< {u_data}")
                self._kill()
                return len(data)

            try:
                written = self.incoming.put(
                    data, timeout=self._write_timeout, partial=True
                )
                self._seriallog.info(f"<<< {u_data}")
                return written
            except queue.Full:
                self._logger.info(
                    "Incoming queue is full, raising SerialTimeoutException"
                )
                raise SerialTimeoutException()

    def readline(self) -> bytes:
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
            self._seriallog.info(f">>> {line.strip()}")
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

    def _send(self, line: str) -> None:
        if self.outgoing is not None:
            self.outgoing.put(line)

    def _ok(self):
        ok = self._okFormatString
        if self._prepared_oks:
            ok = self._prepared_oks.pop(0)
            if ok is None:
                return ok

        return ok.format(
            ok, lastN=self.lastN, buffer=self.buffered.maxsize - self.buffered.qsize()
        )

    def _error(self, error: str, *args, **kwargs) -> str:
        return f"Error: {self._errors.get(error).format(*args, **kwargs)}"


class VirtualEEPROM:
    def __init__(self, data_folder):
        self._data_folder = data_folder
        self._eeprom_file_path = os.path.join(self._data_folder, "eeprom.json")
        self._eeprom = self._initialise_eeprom()

    def _initialise_eeprom(self):
        if os.path.exists(self._eeprom_file_path):
            # file exists, read it
            with open(self._eeprom_file_path, encoding="utf-8") as eeprom_file:
                data = json.load(eeprom_file)
            return data
        else:
            # no eeprom file, make new one with defaults
            data = self.get_default_settings()
            with open(self._eeprom_file_path, "wt", encoding="utf-8") as eeprom_file:
                eeprom_file.write(to_unicode(json.dumps(data)))
            return data

    @staticmethod
    def get_default_settings():
        return {
            "steps": {
                "command": "M92",
                "description": "Steps per unit:",
                "params": {"X": 80.0, "Y": 80.0, "Z": 800.0, "E": 90.0},
            },
            "feedrate": {
                "command": "M203",
                "description": "Maximum feedrates (units/s):",
                "params": {"X": 500.0, "Y": 500.0, "Z": 5.0, "E": 25.0},
            },
            "max_accel": {
                "command": "M201",
                "description": "Maximum Acceleration (units/s2):",
                "params": {"E": 74.0, "X": 2000.0, "Y": 2000.0, "Z": 10.0},
            },
            "start_accel": {
                "command": "M204",
                "description": "Acceleration (units/s2): P<print_accel> R<retract_accel>"
                " T<travel_accel>",
                "params": {"P": 750.0, "R": 1000.0, "T": 300.0, "S": 300.0},
                # S is deprecated, use P & T instead
            },
            "home_offset": {
                "command": "M206",
                "description": "Home offset:",
                "params": {"X": 0.0, "Y": 0.0, "Z": 0.0},
            },  # TODO below are not yet implemented in gcode, just settings
            "probe_offset": {
                "command": "M851",
                "description": "Z-Probe Offset (mm):",
                "params": {"X": 5.0, "Y": 5.0, "Z": 0.2},
            },
            "filament": {
                "command": "M200",
                "description": "Filament settings: Disabled",
                "params": {"D": 1.75, "S": 0},
            },
            "endstop": {
                "command": "M666",
                "description": "Enstop adjustment:",  # TODO description needed
                "params": {"X": -1.0, "Y": 0.0, "Z": 0.0},
            },
            "delta": {
                "command": "M665",
                "description": "Delta config:",  # TODO description
                "params": {
                    "B": 0.0,
                    "H": 100.0,
                    "L": 25.0,
                    "R": 6.5,
                    "S": 100.0,
                    "X": 20.0,
                    "Y": 20.0,
                    "Z": 20.0,
                },
            },
            "auto_level": {
                "command": "M420",
                "description": "Bed Levelling:",
                "params": {"S": 0, "Z": 0.0},
            },
            "linear_advance": {
                "command": "M900",
                "description": "Linear Advance:",
                "params": {"K": 0.01},
            },
            "advanced": {
                "command": "M205",
                "description": "Advanced: B<min_segment_time_us> S<min_feedrate> "
                "T<min_travel_feedrate> X<max_x_jerk> Y<max_y_jerk> "
                "Z<max_z_jerk> E<max_e_jerk>",
                "params": {
                    "B": 20000.0,
                    "S": 0.0,
                    "T": 0.0,
                    "X": 10.0,
                    "Y": 10.0,
                    "Z": 0.3,
                    "E": 5.0,
                    "J": 0.0,
                },
            },
            "material": {  # TODO This ones going to need some special handling...
                "command": "M145",
                "description": "Material heatup parameters:",
                "params": {
                    "0": {"B": 50, "F": 255, "H": "205"},
                    "1": {"B": 75, "F": 0, "H": 240},
                },
            },
            "pid": {
                "command": "M301",
                "description": "PID settings:",
                "params": {"P": 27.08, "I": 2.51, "D": 73.09},
            },
            "pid_bed": {
                "command": "M304",
                "description": "PID settings:",
                "params": {"P": 131.06, "I": 11.79, "D": 971.23},
            },
        }

    def save_settings(self):
        # M500 behind-the-scenes
        with open(self._eeprom_file_path, "wt", encoding="utf-8") as eeprom_file:
            eeprom_file.write(to_unicode(json.dumps(self._eeprom)))

    def read_settings(self):
        # M501 - if the file has disappeared, then recreate it
        if not os.path.exists(self._eeprom_file_path):
            self.load_defaults()
            self.save_settings()
        with open(self._eeprom_file_path) as eeprom_file:
            self._eeprom = json.load(eeprom_file)

    def load_defaults(self):
        # M502
        self._eeprom = self.get_default_settings()

    @property
    def eeprom(self):
        return self._eeprom


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
                endtime = time.monotonic() + timeout
                while not self._will_it_fit(item):
                    remaining = endtime - time.monotonic()
                    if remaining <= 0:
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

    def _qsize(self, l=len):  # noqa: E741
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
