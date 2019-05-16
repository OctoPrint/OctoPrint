# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

import re
import logging
import time

from octoprint.comm.protocol.reprap.commands.gcode import GcodeCommand
from octoprint.comm.protocol.reprap.util import regex_float_pattern, regex_positive_float_pattern, regex_int_pattern

from octoprint.util import chunks, monotonic_time

from future.utils import with_metaclass

_flavor_registry = dict()


def _register_flavor(cls):
	key = getattr(cls, "key", None)
	if key and not key in _flavor_registry:
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


class GenericFlavor(with_metaclass(FlavorMeta, object)):

	key = "generic"
	name = "Generic Flavor"

	logger = logging.getLogger(__name__)

	unknown_requires_ack = False
	unknown_with_checksum = False

	always_send_checksum = False
	never_send_checksum = False

	detect_external_heatups = True
	block_while_dwelling = False

	trigger_ok_after_resend = "detect"

	sd_relative_path = False

	checksum_requiring_commands = ["M110"]
	long_running_commands = ["G4", "G28", "G29", "G30", "G32", "M190", "M109", "M400", "M226"]
	asynchronous_commands = ["G0", "G1", "G2", "G3"]

	regex_resend_linenumber = re.compile(r"(N|N:)?(?P<n>%s)" % regex_int_pattern)
	"""Regex to use for request line numbers in resend requests"""

	regex_temp = re.compile(r"(?P<tool>B|T(?P<toolnum>\d*)):\s*(?P<actual>%s)(\s*/?\s*(?P<target>%s))?" % (
	regex_positive_float_pattern, regex_positive_float_pattern))
	"""Regex matching temperature entries in line.

	Groups will be as follows:

	  * ``tool``: whole tool designator, incl. optional ``toolnum`` (str)
	  * ``toolnum``: tool number, if provided (int)
	  * ``actual``: actual temperature (float)
	  * ``target``: target temperature, if provided (float)
	"""

	regex_position = re.compile(r"(?P<axis>[XYZE]):(?P<pos>{float})\s*".format(float=regex_float_pattern))
	"""Regex for matching position entries in line.

	Groups will be as follows:

	  * ``axis``: axis designator, either ``X``, ``Y``, ``Z`` or ``E`` (str)
	  * ``pos``: axis position (float)
	"""

	regex_firmware_splitter = re.compile(r"\s*([A-Z0-9_]+):")
	"""Regex to use for splitting M115 responses."""

	regex_sd_file_opened = re.compile(r"file opened:\s*(?P<name>.*?)(\s+size:\s*(?P<size>[0-9]+)|$)")

	regex_sd_printing_byte = re.compile(r"sd printing byte (?P<current>[0-9]*)/(?P<total>[0-9]*)")
	"""Regex matching SD printing status reports.

	Groups will be as follows:

	  * ``current``: current byte position in file being printed
	  * ``total``: total size of file being printed
	"""

	##~~ Identifier

	@classmethod
	def identifier(cls, firmware_name, firmware_info):
		return False

	##~~ Message matchers

	@classmethod
	def comm_timeout(cls, line, lower_line, state, flags):
		now = monotonic_time()
		matches = ((line == "" and now > flags["timeout"]) or (flags["expect_continous_comms"]
		                                                       and not flags["job_on_hold"]
		                                                       and not flags["long_running_command"]
		                                                       and not flags["heating"]
		                                                       and now > flags["ok_timeout"])) and \
		          (not cls.block_while_dwelling or not flags["dwelling_until"] or now > flags["dwelling_until"])
		continue_further = line != ""
		return matches, continue_further

	@classmethod
	def comm_ok(cls, line, lower_line, state, flags):
		matches = lower_line.startswith("ok")
		continue_further = not matches \
		                   or cls.message_temperature(line, lower_line, state, flags) \
		                   or cls.message_position(line, lower_line, state, flags) \
		                   or cls.message_firmware_info(line, lower_line, state, flags)
		return matches, continue_further

	@classmethod
	def comm_start(cls, line, lower_line, state, flags):
		return lower_line == "start"

	@classmethod
	def comm_wait(cls, line, lower_line, state, flags):
		return lower_line == "wait"

	@classmethod
	def comm_resend(cls, line, lower_line, state, flags):
		return lower_line.startswith("resend") or lower_line.startswith("rs")

	@classmethod
	def comm_action_command(cls, line, lower_line, state, flags):
		return line.startswith("//") and line[2:].strip().startswith("action:")

	@classmethod
	def comm_error(cls, line, lower_line, state, flags):
		return line.startswith("Error:") or line.startswith("!!")

	@classmethod
	def comm_ignore_ok(cls, line, lower_line, state, flags):
		return False

	@classmethod
	def comm_busy(cls, line, lower_line, state, flags):
		return line.startswith("echo:busy:") or line.startswith("busy:")

	@classmethod
	def error_multiline(cls, line, lower_line, state, flags):
		return False

	@classmethod
	def error_communication(cls, line, lower_line, state, flags):
		return "line number" in lower_line or "checksum" in lower_line or "format error" in lower_line or "expected line" in lower_line

	@classmethod
	def message_temperature(cls, line, lower_line, state, flags):
		return "T:" in line or "T0:" in line or "B:" in line

	@classmethod
	def message_position(cls, line, lower_line, state, flags):
		return 'X:' in line and 'Y:' in line and 'Z:' in line

	@classmethod
	def message_firmware_info(cls, line, lower_line, state, flags):
		return "NAME:" in line

	@classmethod
	def message_firmware_capability(cls, line, lower_line, state, flags):
		return lower_line.startswith("cap:")

	@classmethod
	def message_sd_init_ok(cls, line, lower_line, state, flags):
		return "sd card ok" in lower_line

	@classmethod
	def message_sd_init_fail(cls, line, lower_line, state, flags):
		return "sd init fail" in lower_line or "volume.init failed" in lower_line or "openroot failed" in lower_line

	@classmethod
	def message_sd_file_opened(cls, line, lower_line, state, flags):
		return lower_line.startswith("file opened")

	@classmethod
	def message_sd_file_selected(cls, line, lower_line, state, flags):
		return lower_line.startswith("file selected")

	@classmethod
	def message_sd_begin_file_list(cls, line, lower_line, state, flags):
		return lower_line.startswith("begin file list")

	@classmethod
	def message_sd_end_file_list(cls, line, lower_line, state, flags):
		return lower_line.startswith("end file list")

	@classmethod
	def message_sd_printing_byte(cls, line, lower_line, state, flags):
		return "sd printing byte" in lower_line

	@classmethod
	def message_sd_not_printing(cls, line, lower_line, state, flags):
		return "not sd printing" in lower_line

	@classmethod
	def message_sd_done_printing(cls, line, lower_line, state, flags):
		return "done printing file" in lower_line

	@classmethod
	def message_sd_begin_writing(cls, line, lower_line, state, flags):
		return "writing to file" in lower_line

	@classmethod
	def message_sd_end_writing(cls, line, lower_line, state, flags):
		return "done saving file" in lower_line

	@classmethod
	def message_sd_entry(cls, line, lower_line, state, flags):
		return flags["sd_files_temp"] is not None

	##~~ Message parsers

	@classmethod
	def parse_comm_error(cls, line, lower_line, state, flags):
		return dict(line=line, lower_line=lower_line)

	@classmethod
	def parse_comm_timeout(cls, line, lower_line, state, flags):
		return dict(line=line, lower_line=lower_line)

	@classmethod
	def parse_comm_action_command(cls, line, lower_line, state, flags):
		action = line[2:].strip()[len("action:"):].strip()
		return dict(line=line, lower_line=lower_line, action=action)

	@classmethod
	def parse_error_communication(cls, line, lower_line, state, flags):
		if "line number" in lower_line or "expected line" in lower_line:
			error_type = "linenumber"
		elif "checksum" in lower_line:
			error_type = "checksum"
		else:
			error_type = "other"

		flags["last_communication_error"] = error_type
		return dict(error_type=error_type)

	@classmethod
	def parse_comm_resend(cls, line, lower_line, state, flags):
		line_to_resend = None
		match = cls.regex_resend_linenumber.search(line)
		if match is not None:
			line_to_resend = int(match.group("n"))
		return dict(linenumber=line_to_resend)

	@classmethod
	def parse_message_temperature(cls, line, lower_line, state, flags):
		"""
		Parses the provided temperature line.

		The result will be a dictionary mapping from the extruder or bed key to
		a tuple with current and target temperature. The result will be canonicalized
		with :func:`canonicalize_temperatures` before returning.

		Returns:
		    tuple: a 2-tuple with the maximum tool number and a dict mapping from
		      key to (actual, target) tuples, with key either matching ``Tn`` for ``n >= 0`` or ``B``
		"""

		current_tool = flags["current_tool"]

		result = {}
		max_tool_num = 0
		for match in re.finditer(cls.regex_temp, line):
			values = match.groupdict()
			tool = values["tool"]
			if tool == "T" and "toolnum" in values and values["toolnum"]:
				tool_num = int(values["toolnum"])
				if tool_num > max_tool_num:
					max_tool_num = tool_num

			try:
				actual = float(values.get("actual", None)) if values.get("actual", None) is not None else None
				target = float(values.get("target", None)) if values.get("target", None) is not None else None
				result[tool] = actual, target
			except ValueError:
				# catch conversion issues, we'll rather just not get the temperature update instead of killing the connection
				pass

		heatup_detected = not lower_line.startswith("ok") and not flags["heating"] and not flags["temperature_autoreporting"]

		return dict(max_tool_num=max(max_tool_num, current_tool),
		            temperatures=cls._canonicalize_temperatures(result, current_tool),
		            heatup_detected=heatup_detected)

	@classmethod
	def parse_message_position(cls, line, lower_line, state, flags):
		position = dict(x=None, y=None, z=None, e=None)
		for match in re.finditer(cls.regex_position, line):
			position[match.group("axis").lower()] = float(match.group("pos"))
		return dict(position=position)

	@classmethod
	def parse_message_firmware_info(cls, line, lower_line, state, flags):
		data = cls._parse_firmware_line(line)
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

		return dict(firmware_name=firmware_name,
		            data=data)

	@classmethod
	def parse_message_firmware_capability(cls, line, lower_line, state, flags):
		result = cls._parse_capability_line(line)
		if not result:
			return
		cap, enabled = result
		return dict(cap=cap, enabled=enabled)

	@classmethod
	def parse_message_sd_file_opened(cls, line, lower_line, state, flags):
		match = cls.regex_sd_file_opened.match(lower_line)
		if not match:
			return

		name = match.group("name")
		size = int(match.group("size"))
		return dict(name=name, long_name=name, size=size)

	@classmethod
	def parse_message_sd_entry(cls, line, lower_line, state, flags):
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

		return dict(name=filename, long_name=filename, size=int(size) if size is not None else None)

	@classmethod
	def parse_message_sd_printing_byte(cls, line, lower_line, state, flags):
		match = cls.regex_sd_printing_byte.match(lower_line)
		if not match:
			return None
		return dict(current=int(match.group("current")), total=int(match.group("total")))

	##~~ Commands

	@classmethod
	def command_hello(cls):
		return cls.command_set_line(0)

	@classmethod
	def command_get_firmware_info(cls):
		return GcodeCommand("M115")

	@classmethod
	def command_finish_moving(cls):
		return GcodeCommand("M400")

	@classmethod
	def command_get_position(cls):
		return GcodeCommand("M114")

	@classmethod
	def command_get_temp(cls):
		return GcodeCommand("M105")

	@classmethod
	def command_set_line(cls, n):
		return GcodeCommand("M110", n=n)

	@classmethod
	def command_emergency_stop(cls):
		return GcodeCommand("M112")

	@classmethod
	def command_set_extruder_temp(cls, temperature, tool=None, wait=False):
		command = "M109" if wait else "M104"
		args = dict(s=temperature)
		if tool is not None:
			args["t"] = tool
		return GcodeCommand(command, **args)

	@classmethod
	def command_set_bed_temp(cls, temperature, wait=False):
		return GcodeCommand("M190" if wait else "M140", s=temperature)

	@classmethod
	def command_set_chamber_temp(cls, temperature, wait=False):
		return GcodeCommand("M191" if wait else "M141", s=temperature)

	@classmethod
	def command_set_relative_positioning(cls):
		return GcodeCommand("G91")

	@classmethod
	def command_set_absolute_positioning(cls):
		return GcodeCommand("G90")

	@classmethod
	def command_move(cls, x=None, y=None, z=None, e=None, f=None):
		return GcodeCommand("G1", x=x, y=y, z=z, e=e, f=f)

	@classmethod
	def command_extrude(cls, e=None, f=None):
		return cls.command_move(e=e, f=f)

	@classmethod
	def command_home(cls, x=False, y=False, z=False):
		return GcodeCommand("G28", x=0 if x else None, y=0 if y else None, z=0 if z else None)

	@classmethod
	def command_set_tool(cls, tool):
		return GcodeCommand("T{}".format(tool))

	@classmethod
	def command_set_feedrate_multiplier(cls, multiplier):
		return GcodeCommand("M220", s=multiplier)

	@classmethod
	def command_set_extrusion_multiplier(cls, multiplier):
		return GcodeCommand("M221", s=multiplier)

	@classmethod
	def command_set_fan_speed(cls, speed):
		return GcodeCommand("M106", s=speed)

	@classmethod
	def command_set_motors(cls, enable):
		return GcodeCommand("M17") if enable else GcodeCommand("M18")

	@classmethod
	def command_sd_refresh(cls):
		return GcodeCommand("M20")

	@classmethod
	def command_sd_init(cls):
		return GcodeCommand("M21")

	@classmethod
	def command_sd_release(cls):
		return GcodeCommand("M22")

	@classmethod
	def command_sd_select_file(cls, name):
		return GcodeCommand("M23", param=name)

	@classmethod
	def command_sd_start(cls):
		return GcodeCommand("M24")

	@classmethod
	def command_sd_pause(cls):
		return GcodeCommand("M25")

	@classmethod
	def command_sd_resume(cls):
		return GcodeCommand("M24")

	@classmethod
	def command_sd_set_pos(cls, pos):
		return GcodeCommand("M26", s=pos)

	@classmethod
	def command_sd_status(cls):
		return GcodeCommand("M27")

	@classmethod
	def command_sd_begin_write(cls, name):
		return GcodeCommand("M28", param=name)

	@classmethod
	def command_sd_end_write(cls):
		return GcodeCommand("M29")

	@classmethod
	def command_sd_delete(cls, name):
		return GcodeCommand("M30", param=name)

	@classmethod
	def command_autoreport_temperature(cls, interval):
		return GcodeCommand("M155", s=interval)

	@classmethod
	def command_autoreport_sd_status(cls, interval):
		return GcodeCommand("M27", s=interval)

	@classmethod
	def command_busy_protocol_interval(cls, interval):
		return GcodeCommand("M113", s=interval)

	##~~ Helpers

	@classmethod
	def _canonicalize_temperatures(cls, parsed, current):
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

	@classmethod
	def _parse_firmware_line(cls, line):
		"""
		Parses the provided firmware info line.

		The result will be a dictionary mapping from the contained keys to the contained
		values.

		Arguments:
		    line (unicode): the line to parse

		Returns:
		    dict: a dictionary with the parsed data
		"""

		result = dict()
		split_line = cls.regex_firmware_splitter.split(line.strip())[1:]  # first entry is empty start of trimmed string
		for key, value in chunks(split_line, 2):
			result[key] = value
		return result

	@classmethod
	def _parse_capability_line(cls, line):
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
