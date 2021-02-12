__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging
import re
import time

from octoprint.comm.protocol.reprap.commands.gcode import GcodeCommand
from octoprint.comm.protocol.reprap.util import (
    regex_float_pattern,
    regex_int_pattern,
    regex_positive_float_pattern,
)
from octoprint.events import Events
from octoprint.util import chunks

_flavor_registry = {}


def _register_flavor(cls):
    key = getattr(cls, "key", None)
    if key and key not in _flavor_registry:
        _flavor_registry[key] = cls


def all_flavors():
    return _flavor_registry.values()


def lookup_flavor(key):
    return _flavor_registry.get(key)


class FlavorMeta(type):
    def __new__(mcs, name, bases, class_dict):
        cls = type.__new__(mcs, name, bases, class_dict)
        _register_flavor(cls)
        return cls


# noinspection PyMethodMayBeStatic
class StandardFlavor(metaclass=FlavorMeta):

    key = "standard"
    name = "Standard Flavor"

    unknown_requires_ack = False
    unknown_with_checksum = False

    send_checksum = "printing"

    detect_external_heatups = True
    block_while_dwelling = False

    trigger_ok_after_resend = "detect"

    sd_relative_path = False
    sd_always_available = False

    checksum_requiring_commands = ["M110"]
    long_running_commands = [
        "G4",
        "G28",
        "G29",
        "G30",
        "G32",
        "M190",
        "M109",
        "M400",
        "M226",
    ]
    asynchronous_commands = ["G0", "G1", "G2", "G3"]
    blocked_commands = ["M0", "M1"]
    pausing_commands = ["M0", "M1", "M25"]
    emergency_commands = ["M112", "M108", "M410"]

    heatup_abortable = False

    ok_buffer_size = 1

    overridable = (
        "unknown_requires_ack",
        "unknown_with_checksum",
        "send_checksum",
        "detect_external_heatups",
        "block_while_dwelling",
        "trigger_ok_after_resend",
        "sd_relative_path",
        "checksum_requiring_commands",
        "long_running_commands",
        "asynchronous_commands",
        "blocked_commands",
        "pausing_commands",
        "emergency_commands",
        "heatup_abortable",
        "ok_buffer_size",
    )

    regex_min_max_error = re.compile(r"Error:[0-9]\n")
    """Regex matching first line of min/max errors from legacy firmware."""

    regex_resend_linenumber = re.compile(r"(N|N:)?(?P<n>%s)" % regex_int_pattern)
    """Regex to use for request line numbers in resend requests"""

    regex_temp = re.compile(
        r"(?P<tool>B|T(?P<toolnum>\d*)):\s*(?P<actual>%s)(\s*/?\s*(?P<target>%s))?"
        % (regex_positive_float_pattern, regex_positive_float_pattern)
    )
    """Regex matching temperature entries in line.

    Groups will be as follows:

      * ``tool``: whole tool designator, incl. optional ``toolnum`` (str)
      * ``toolnum``: tool number, if provided (int)
      * ``actual``: actual temperature (float)
      * ``target``: target temperature, if provided (float)
    """

    regex_position = re.compile(
        r"(?P<axis>[XYZE]):(?P<pos>{float})\s*".format(float=regex_float_pattern)
    )
    """Regex for matching position entries in line.

    Groups will be as follows:

      * ``axis``: axis designator, either ``X``, ``Y``, ``Z`` or ``E`` (str)
      * ``pos``: axis position (float)
    """

    regex_firmware_splitter = re.compile(r"\s*([A-Z0-9_]+):")
    """Regex to use for splitting M115 responses."""

    regex_sd_file_opened = re.compile(
        r"file opened:\s*(?P<name>.*?)(\s+size:\s*(?P<size>[0-9]+)|$)"
    )

    regex_sd_printing_byte = re.compile(
        r"sd printing byte (?P<current>[0-9]*)/(?P<total>[0-9]*)"
    )
    """Regex matching SD printing status reports.

    Groups will be as follows:

      * ``current``: current byte position in file being printed
      * ``total``: total size of file being printed
    """

    regex_invalid_tool_1 = re.compile(r"t(?P<tool>[0-9]+) invalid extruder")
    """Regex matching "invalid tool" messages, variant 1.

    Matches messages like

        echo:T1 Invalid extruder

    Groups will be as follows:

      * ``tool``: tool number reported as invalid
    """

    regex_invalid_tool_2 = re.compile(r"invalid extruder t?(?P<tool>[0-9]+)")
    """ Regex matching "invalid tool" messages, variant 2.

    Matches messages like

        echo:M104 Invalid extruder 1
        echo:M104 Invalid extruder T2

    Groups will be as follows:

      * ``tool``: tool number reported as invalid
    """

    gcode_to_event = {
        "M226": Events.WAITING,  # pause of user input
        "M0": Events.WAITING,  # pause of user input
        "M1": Events.WAITING,  # pause of user input
        "G4": Events.DWELL,  # dwell
        "M245": Events.COOLING,  # part cooler
        "M240": Events.CONVEYOR,  # part conveyor
        "M40": Events.EJECT,  # part ejector
        "M300": Events.ALERT,  # user alert
        "G28": Events.HOME,  # home print head
        "M112": Events.E_STOP,  # emergency stop
        "M80": Events.POWER_ON,  # motors on
        "M81": Events.POWER_OFF,  # motors off
    }

    def __init__(self, protocol, **kwargs):
        from octoprint.comm.protocol.reprap import ReprapGcodeProtocol

        if not isinstance(protocol, ReprapGcodeProtocol):
            raise ValueError("protocol must be a ReprapGcodeProtocol instance")

        self._protocol = protocol
        self._logger = logging.getLogger(__name__)
        for key in self.overridable:
            setattr(self, key, kwargs.get(key, getattr(self.__class__, key)))

    ##~~ Identifier

    @classmethod
    def identifier(cls, firmware_name, firmware_info):
        return False

    ##~~ Message matchers

    def comm_timeout(self, line, lower_line):
        now = time.monotonic()
        matches = (
            (line == "" and now > self._protocol.internal_state.timeout)
            or (
                self._protocol.internal_state.expect_continuous_comms
                and not self._protocol.internal_state.job_on_hold
                and not self._protocol.internal_state.long_running_command
                and not self._protocol.internal_state.heating
                and now > self._protocol.internal_state.ok_timeout
            )
        ) and (
            not self.block_while_dwelling
            or not self._protocol.internal_state.dwelling_until
            or now > self._protocol.internal_state.dwelling_until
        )
        continue_further = line != ""
        return matches, continue_further

    def comm_ok(self, line, lower_line):
        matches = lower_line.startswith("ok")
        continue_further = (
            not matches
            or self.message_temperature(line, lower_line)
            or self.message_position(line, lower_line)
            or self.message_firmware_info(line, lower_line)
        )
        return matches, continue_further

    def comm_start(self, line, lower_line):
        return lower_line == "start"

    def comm_wait(self, line, lower_line):
        return lower_line == "wait"

    def comm_resend(self, line, lower_line):
        return lower_line.startswith("resend") or lower_line.startswith("rs")

    def comm_action_command(self, line, lower_line):
        return line.startswith("//") and line[2:].strip().startswith("action:")

    def comm_error(self, line, lower_line):
        single_line = line.startswith("Error:") or line.startswith("!!")
        multi_line = self._protocol.internal_state.multiline_error is not False

        if self.regex_min_max_error.match(line):
            self._protocol.internal_state.multiline_error = line

        return single_line or multi_line

    def comm_ignore_ok(self, line, lower_line):
        return False

    def comm_busy(self, line, lower_line):
        return line.startswith("echo:busy:") or line.startswith("busy:")

    def error_communication(self, line, lower_line, error):
        return any(
            map(
                lambda x: x in lower_line,
                ("line number", "checksum", "format error", "expected line"),
            )
        )

    def error_sdcard(self, line, lower_line, error):
        return any(
            map(
                lambda x: x in lower_line,
                (
                    "volume.init",
                    "openroot",
                    "workdir",
                    "error writing to file",
                    "cannot open",
                    "open failed",
                    "cannot enter",
                ),
            )
        )

    def error_fatal(self, line, lower_line, error):
        return any(map(lambda x: x in lower_line, ("kill() called", "fatal:")))

    def message_temperature(self, line, lower_line):
        return "T:" in line or "T0:" in line or "B:" in line

    def message_position(self, line, lower_lines):
        return "X:" in line and "Y:" in line and "Z:" in line

    def message_firmware_info(self, line, lower_line):
        return "NAME:" in line

    def message_firmware_capability(self, line, lower_line):
        return lower_line.startswith("cap:")

    def message_sd_init_ok(self, line, lower_line):
        return "sd card ok" in lower_line

    def message_sd_init_fail(self, line, lower_line):
        return (
            "sd init fail" in lower_line
            or "volume.init failed" in lower_line
            or "openroot failed" in lower_line
        )

    def message_sd_file_opened(self, line, lower_line):
        return lower_line.startswith("file opened")

    def message_sd_file_selected(self, line, lower_line):
        return lower_line.startswith("file selected")

    def message_sd_begin_file_list(self, line, lower_line):
        return lower_line.startswith("begin file list")

    def message_sd_end_file_list(self, line, lower_line):
        return lower_line.startswith("end file list")

    def message_sd_printing_byte(self, line, lower_line):
        return "sd printing byte" in lower_line

    def message_sd_not_printing(self, line, lower_line):
        return "not sd printing" in lower_line

    def message_sd_done_printing(self, line, lower_line):
        return "done printing file" in lower_line

    def message_sd_begin_writing(self, line, lower_line):
        return "writing to file" in lower_line

    def message_sd_end_writing(self, line, lower_line):
        return "done saving file" in lower_line

    def message_sd_entry(self, line, lower_line):
        return self._protocol.internal_state.sd_files_temp is not None

    def message_invalid_tool(self, line, lower_line):
        return "invalid extruder" in lower_line

    ##~~ Message parsers

    def parse_comm_error(self, line, lower_line):
        multiline = self._protocol.internal_state.multiline_error
        if multiline:
            self._protocol.internal_state.multiline_error = False
            line = line.rstrip() + " - " + multiline
            lower_line = line.lower()

        error = (line[6:] if lower_line.startswith("error:") else line[2:]).strip()
        return {"line": line, "lower_line": lower_line, "error": error}

    def parse_comm_timeout(self, line, lower_line):
        return {"line": line, "lower_line": lower_line}

    def parse_comm_action_command(self, line, lower_line):
        action = line[2:].strip()[len("action:") :].strip()
        return {"line": line, "lower_line": lower_line, "action": action}

    def parse_error_communication(self, line, lower_line, error):
        if "line number" in lower_line or "expected line" in lower_line:
            error_type = "linenumber"
        elif "checksum" in lower_line:
            error_type = "checksum"
        else:
            error_type = "other"

        self._protocol.internal_state.last_communication_error = error_type
        return {"error_type": error_type}

    def parse_comm_resend(self, line, lower_line):
        line_to_resend = None
        match = self.regex_resend_linenumber.search(line)
        if match is not None:
            line_to_resend = int(match.group("n"))
        return {"linenumber": line_to_resend}

    def parse_message_temperature(self, line, lower_line):
        """
        Parses the provided temperature line.

        The result will be a dictionary mapping from the extruder or bed key to
        a tuple with current and target temperature. The result will be canonicalized
        with :func:`canonicalize_temperatures` before returning.

        Returns:
            tuple: a 2-tuple with the maximum tool number and a dict mapping from
              key to (actual, target) tuples, with key either matching ``Tn`` for ``n >= 0`` or ``B``
        """

        current_tool = self._protocol.internal_state.current_tool

        result = {}
        max_tool_num = 0
        for match in re.finditer(self.regex_temp, line):
            values = match.groupdict()
            tool = values["tool"]
            if tool == "T" and "toolnum" in values and values["toolnum"]:
                tool_num = int(values["toolnum"])
                if tool_num > max_tool_num:
                    max_tool_num = tool_num

            try:
                actual = (
                    float(values.get("actual", None))
                    if values.get("actual", None) is not None
                    else None
                )
                target = (
                    float(values.get("target", None))
                    if values.get("target", None) is not None
                    else None
                )
                result[tool] = actual, target
            except ValueError:
                # catch conversion issues, we'll rather just not get the temperature update instead of killing the connection
                pass

        heatup_detected = (
            not lower_line.startswith("ok")
            and not self._protocol.internal_state.heating
            and not self._protocol.internal_state.temperature_autoreporting
        )

        return {
            "max_tool_num": max(max_tool_num, current_tool),
            "temperatures": self._canonicalize_temperatures(result, current_tool),
            "heatup_detected": heatup_detected,
        }

    def parse_message_position(self, line, lower_line):
        position = {"x": None, "y": None, "z": None, "e": None}
        for match in re.finditer(self.regex_position, line):
            position[match.group("axis").lower()] = float(match.group("pos"))
        return {"position": position}

    def parse_message_firmware_info(self, line, lower_line):
        data = self._parse_firmware_line(line)
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
            if "malyan" in name.lower() and ver:
                firmware_name = name.strip() + " " + ver.strip()

        if firmware_name is not None:
            firmware_name = firmware_name.strip()

        return {"firmware_name": firmware_name, "data": data}

    def parse_message_firmware_capability(self, line, lower_line):
        result = self._parse_capability_line(line)
        if not result:
            return
        cap, enabled = result
        return {"cap": cap, "enabled": enabled}

    def parse_message_sd_file_opened(self, line, lower_line):
        match = self.regex_sd_file_opened.match(lower_line)
        if not match:
            return

        name = match.group("name")
        size = int(match.group("size"))
        return {"name": name, "long_name": name, "size": size}

    def parse_message_sd_entry(self, line, lower_line):
        fileinfo = lower_line.rsplit(None, 1)
        if len(fileinfo) > 1:
            # we might have extended file information here, so let's split filename and size and try to make them a bit nicer
            filename, size = fileinfo
            try:
                size = int(size)
            except ValueError:
                # whatever that was, it was not an integer, so we'll just use the whole line as filename and set size to None
                filename = lower_line
                size = None
        else:
            # no extended file information, so only the filename is there and we set size to None
            filename = lower_line
            size = None

        from octoprint.util import filter_non_ascii

        if filter_non_ascii(filename):
            return None
        else:
            if not filename.startswith("/"):
                # file from the root of the sd -- we'll prepend a /
                filename = "/" + filename

        return {
            "name": filename,
            "long_name": filename,
            "size": int(size) if size is not None else None,
        }

    def parse_message_sd_printing_byte(self, line, lower_line):
        match = self.regex_sd_printing_byte.match(lower_line)
        if not match:
            return None
        return {
            "current": int(match.group("current")),
            "total": int(match.group("total")),
        }

    def parse_message_invalid_tool(self, line, lower_line):
        for pattern in (self.regex_invalid_tool_1, self.regex_invalid_tool_2):
            match = pattern.search(lower_line)
            if match:
                return {"tool": int(match.group("tool"))}
        return None

    ##~~ Commands

    def command_hello(self):
        return self.command_set_line(0)

    def command_get_firmware_info(self):
        return GcodeCommand("M115")

    def command_finish_moving(self):
        return GcodeCommand("M400")

    def command_get_position(self):
        return GcodeCommand("M114")

    def command_get_temp(self):
        return GcodeCommand("M105")

    def command_set_line(self, n):
        return GcodeCommand("M110", n=n)

    def command_emergency_stop(self):
        return GcodeCommand("M112")

    def command_abort_heatup(self):
        return GcodeCommand("M108")

    def command_set_extruder_temp(self, temperature, tool=None, wait=False):
        command = "M109" if wait else "M104"
        args = {"s": temperature}
        if tool is not None:
            args["t"] = tool
        return GcodeCommand(command, **args)

    def command_set_bed_temp(self, temperature, wait=False):
        return GcodeCommand("M190" if wait else "M140", s=temperature)

    def command_set_chamber_temp(self, temperature, wait=False):
        return GcodeCommand("M191" if wait else "M141", s=temperature)

    def command_set_relative_positioning(self):
        return GcodeCommand("G91")

    def command_set_absolute_positioning(self):
        return GcodeCommand("G90")

    def command_move(self, x=None, y=None, z=None, e=None, f=None):
        return GcodeCommand("G1", x=x, y=y, z=z, e=e, f=f)

    def command_extrude(self, e=None, f=None):
        return self.command_move(e=e, f=f)

    def command_home(self, x=False, y=False, z=False):
        return GcodeCommand(
            "G28", x=0 if x else None, y=0 if y else None, z=0 if z else None
        )

    def command_set_tool(self, tool):
        return GcodeCommand("T", tool=tool)

    def command_set_feedrate_multiplier(self, multiplier):
        return GcodeCommand("M220", s=multiplier)

    def command_set_extrusion_multiplier(self, multiplier):
        return GcodeCommand("M221", s=multiplier)

    def command_set_fan_speed(self, speed):
        return GcodeCommand("M106", s=speed)

    def command_set_motors(self, enable):
        return GcodeCommand("M17") if enable else GcodeCommand("M18")

    def command_sd_refresh(self):
        return GcodeCommand("M20")

    def command_sd_init(self):
        return GcodeCommand("M21")

    def command_sd_release(self):
        return GcodeCommand("M22")

    def command_sd_select_file(self, name):
        return GcodeCommand("M23", param=name)

    def command_sd_start(self):
        return GcodeCommand("M24")

    def command_sd_pause(self):
        return GcodeCommand("M25")

    def command_sd_resume(self):
        return GcodeCommand("M24")

    def command_sd_set_pos(self, pos):
        return GcodeCommand("M26", s=pos)

    def command_sd_status(self):
        return GcodeCommand("M27")

    def command_sd_begin_write(self, name):
        return GcodeCommand("M28", param=name)

    def command_sd_end_write(self):
        return GcodeCommand("M29")

    def command_sd_delete(self, name):
        return GcodeCommand("M30", param=name)

    def command_autoreport_temperature(self, interval):
        return GcodeCommand("M155", s=interval)

    def command_autoreport_sd_status(self, interval):
        return GcodeCommand("M27", s=interval)

    def command_busy_protocol_interval(self, interval):
        return GcodeCommand("M113", s=interval)

    ##~~ gcode handlers

    def handle_gcode_T_queuing(self, command):
        old_tool = self._protocol.internal_state.current_tool
        new_tool = command.tool

        if not self._protocol.validate_tool(new_tool):
            message = (
                "Not queuing T{}, that tool doesn't exist according to the printer profile or "
                "was reported as invalid by the firmware. Make sure your "
                "printer profile is set up correctly.".format(new_tool)
            )
            self._protocol.process_protocol_log(self._protocol.LOG_PREFIX_WARN + message)
            self._protocol.notify_listeners(
                "on_protocol_message_suppressed",
                self._protocol,
                str(command),
                message,
                "warn",
            )

            return (None,)

        before = self._protocol.get_script(
            "beforeToolChange",
            context={"tool": {"old": old_tool, "new": new_tool}},
            allow_missing=True,
        )
        after = self._protocol.get_script(
            "afterToolChange",
            context={"tool": {"old": old_tool, "new": new_tool}},
            allow_missing=True,
        )

        return before + [command] + after

    def handle_gcode_T_sending(self, command):
        new_tool = command.tool

        if not self._protocol.validate_tool(new_tool):
            message = (
                "Not sending T{}, that tool doesn't exist according to the printer profile or "
                "was reported as invalid by the firmware. Make sure your "
                "printer profile is set up correctly.".format(new_tool)
            )
            self._protocol.process_protocol_log(self._protocol.LOG_PREFIX_WARN + message)
            self._protocol.notify_listeners(
                "on_protocol_message_suppressed",
                self._protocol,
                str(command),
                message,
                "warn",
            )

            return (None,)

    def handle_gcode_T_sent(self, command):
        current_tool = self._protocol.internal_state.current_tool
        new_tool = command.tool

        if new_tool is not None and new_tool != current_tool:
            self._protocol.internal_state.former_tool = current_tool
            self._protocol.internal_state.current_tool = new_tool
            self._protocol.notify_listeners(
                "on_protocol_tool_change",
                self._protocol,
                current_tool,
                new_tool,
            )

    def handle_gcode_G0_sent(self, command):
        if command.z is not None and self._protocol.internal_state.current_z != command.z:
            self._protocol.internal_state.current_z = command.z
            self._protocol.notify_listeners(
                "on_protocol_position_z_update",
                self._protocol,
                self._protocol.internal_state.current_z,
            )
        if command.f is not None:
            self._protocol.internal_state.current_f = command.f

    handle_gcode_G1_sent = handle_gcode_G0_sent

    def handle_gcode_G2_sent(self, command):
        if command.f is not None:
            self._protocol.internal_state.current_f = command.f

    handle_gcode_G3_sent = handle_gcode_G2_sent
    handle_gcode_G28_sent = handle_gcode_G2_sent

    def handle_gcode_M140_queuing(self, command):
        if not self._protocol.printer_profile["heatedBed"]:
            self._protocol.process_protocol_log(
                'Warn: Not sending "{}", printer profile has no heated bed'.format(
                    command
                )
            )
            return (None,)  # Don't send bed commands if we don't have a heated bed

    handle_gcode_M190_queuing = handle_gcode_M140_queuing

    def handle_gcode_M155_sending(self, command):
        try:
            interval = int(command.s)
            self._protocol.internal_state.temperature_autoreporting = (
                self._protocol.internal_state.firmware_capabilities.get(
                    self._protocol.CAPABILITY_AUTOREPORT_TEMP, False
                )
                and (interval > 0)
            )
        except Exception:
            pass

    def handle_gcode_M27_sending(self, command):
        try:
            interval = int(command.s)
            self._protocol.internal_state.sd_status_autoreporting = (
                self._protocol.internal_state.firmware_capabilities.get(
                    self._protocol.CAPABILITY_AUTOREPORT_SD_STATUS, False
                )
                and (interval > 0)
            )
        except Exception:
            pass

    def _apply_temperature_offset(self, heater, command, support_r=False):
        offset = self._protocol.internal_state.temperature_offsets.get(heater, 0)
        if offset == 0 or "source:file" not in command.tags:
            return

        try:
            if command.s is not None:
                return command.with_args(s=float(command.s) + offset)
            elif command.r is not None and support_r:
                return command.with_args(r=float(command.r) + offset)
        except Exception:
            self._logger.exception("Error applying temperature offset")

    def handle_gcode_M104_sending(self, command, support_r=False):
        if command.t:
            tool_num = command.t
        else:
            tool_num = self._protocol.internal_state.current_tool

        return self._apply_temperature_offset(
            "tool{}".format(tool_num), command, support_r=support_r
        )

    def handle_gcode_M109_sending(self, command):
        return self.handle_gcode_M104_sending(command, support_r=True)

    def handle_gcode_M140_sending(self, command):
        return self._apply_temperature_offset("bed", command, support_r=False)

    def handle_gcode_M190_sending(self, command):
        return self._apply_temperature_offset("bed", command, support_r=True)

    def handle_gcode_M141_sending(self, command):
        return self._apply_temperature_offset("chamber", command, support_r=False)

    def handle_gcode_M191_sending(self, command):
        return self._apply_temperature_offset("chamber", command, support_r=True)

    def handle_gcode_M104_sent(self, command, wait=False, support_r=False):
        tool_num = self._protocol.internal_state.current_tool
        if command.t:
            tool_num = command.t

            if wait:
                self._protocol.internal_state.former_tool = (
                    self._protocol.internal_state.current_tool
                )
                self._protocol.internal_state.current_tool = tool_num

        target = None
        if command.s is not None:
            target = float(command.s)
        elif command.r is not None and support_r:
            target = float(command.r)

        if target:
            self._protocol.internal_state.temperatures.set_tool(tool_num, target=target)
            self._protocol.notify_listeners(
                "on_protocol_temperature",
                self._protocol,
                self._protocol.internal_state.temperatures.as_dict(),
            )

    def handle_gcode_M140_sent(self, command, wait=False, support_r=False):
        target = None
        if command.s is not None:
            target = float(command.s)
        elif command.r is not None and support_r:
            target = float(command.r)

        if target:
            self._protocol.internal_state.temperatures.set_bed(target=target)
            self._protocol.notify_listeners(
                "on_protocol_temperature",
                self._protocol,
                self._protocol.internal_state.temperatures.as_dict(),
            )

    def handle_gcode_M141_sent(self, command, wait=False, support_r=False):
        target = None
        if command.s is not None:
            target = float(command.s)
        elif command.r is not None and support_r:
            target = float(command.r)

        if target:
            self._protocol.internal_state.temperatures.set_chamber(target=target)
            self._protocol.notify_listeners(
                "on_protocol_temperature",
                self._protocol,
                self._protocol.internal_state.temperatures.as_dict(),
            )

    def handle_gcode_M109_sent(self, command):
        self._protocol.internal_state.heatup_start = time.monotonic()
        self._protocol.internal_state.long_running_command = True
        self._protocol.internal_state.heating = True
        self.handle_gcode_M104_sent(command, wait=True, support_r=True)

    def handle_gcode_M190_sent(self, command):
        self._protocol.internal_state.heatup_start = time.monotonic()
        self._protocol.internal_state.long_running_command = True
        self._protocol.internal_state.heating = True
        self.handle_gcode_M140_sent(command, wait=True, support_r=True)

    def handle_gcode_M191_sent(self, command):
        self._protocol.internal_state.heatup_start = time.monotonic()
        self._protocol.internal_state.long_running_command = True
        self._protocol.internal_state.heating = True
        self.handle_gcode_M141_sent(command, wait=True, support_r=True)

    def handle_gcode_M116_sent(self, command):
        self._protocol.internal_state.heatup_start = time.monotonic()
        self._protocol.internal_state.long_running_command = True
        self._protocol.internal_state.heating = True

    def handle_gcode_M110_sending(self, command):
        new_line_number = None
        if command.n:
            try:
                new_line_number = int(command.n)
            except Exception:
                pass
        else:
            new_line_number = 0

        self._protocol.reset_linenumber(linenumber=new_line_number)
        self._protocol.internal_state.resend_linenumber = None

    def handle_gcode_M114_queued(self, command):
        self._protocol.reset_position_timers()

    handle_gcode_M114_sent = handle_gcode_M114_queued

    def handle_gcode_G4_sent(self, command):
        timeout = 0
        if command.p is not None:
            try:
                timeout = float(command.p) / 1000.0
            except ValueError:
                pass
        elif command.s is not None:
            try:
                timeout = float(command.s)
            except ValueError:
                pass

        self._protocol.internal_state.timeout = (
            self._protocol.get_timeout(
                "communication_busy"
                if self._protocol.internal_state.busy_detected
                else "communication"
            )
            + timeout
        )
        self._protocol.internal_state.dwelling_until = time.monotonic() + timeout

    ##~~ Helpers

    def _canonicalize_temperatures(self, parsed, current):
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

        reported_extruders = list(filter(lambda x: x.startswith("T"), parsed.keys()))
        if "T" not in reported_extruders:
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

    def _parse_firmware_line(self, line):
        """
        Parses the provided firmware info line.

        The result will be a dictionary mapping from the contained keys to the contained
        values.

        Arguments:
            line (unicode): the line to parse

        Returns:
            dict: a dictionary with the parsed data
        """

        result = {}
        split_line = self.regex_firmware_splitter.split(line.strip())[
            1:
        ]  # first entry is empty start of trimmed string
        for key, value in chunks(split_line, 2):
            result[key] = value
        return result

    def _parse_capability_line(self, line):
        """
        Parses the provided firmware capability line.

        Lines are expected to be of the format

            Cap:<capability name in caps>:<0 or 1>

        e.g.

            Cap:AUTOREPORT_TEMP:1
            Cap:TOGGLE_LIGHTS:0

        Args:
                line (unicode): the line to parse

        Returns:
                tuple: a 2-tuple of the parsed capability name and whether it's on (true) or off (false), or None if the line
                    could not be parsed
        """

        line = line.lower()
        if line.startswith("cap:"):
            line = line[len("cap:") :]

        parts = line.split(":")
        if len(parts) != 2:
            # wrong format, can't parse this
            return None

        capability, flag = parts
        if flag not in ("0", "1"):
            # wrong format, can't parse this
            return None

        return capability.upper(), flag == "1"


# Only import these at the end, otherwise we'll have a circular dependency on
# StandardFlavor!

from .anet import *  # noqa: F401,F403
from .klipper import *  # noqa: F401,F403
from .malyan import *  # noqa: F401,F403
from .marlin import *  # noqa: F401,F403
from .repetier import *  # noqa: F401,F403
from .reprapfirmware import *  # noqa: F401,F403
from .smoothieware import *  # noqa: F401,F403
