# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import glob
import os
import re

try:
	import queue
except ImportError:
	import Queue as queue
from past.builtins import basestring

import logging

# from .machine_com import MachineCom, MachineComPrintCallback

from octoprint.settings import settings
from octoprint.events import Events
from octoprint.util import chunks
from octoprint.util.gcode import gcode_and_subcode_for_cmd

try:
	import winreg
except ImportError:
	try:
		import _winreg as winreg
	except ImportError:
		pass

_logger = logging.getLogger(__name__)

# a bunch of regexes we'll need for the communication parsing...

regex_float_pattern = r"[-+]?[0-9]*\.?[0-9]+"
regex_positive_float_pattern = r"[+]?[0-9]*\.?[0-9]+"
regex_int_pattern = r"\d+"

regex_float = re.compile(regex_float_pattern)
"""Regex for a float value."""

regexes_parameters = dict(
	floatE=re.compile(r"(^|[^A-Za-z])[Ee](?P<value>%s)" % regex_float_pattern),
	floatF=re.compile(r"(^|[^A-Za-z])[Ff](?P<value>%s)" % regex_float_pattern),
	floatP=re.compile(r"(^|[^A-Za-z])[Pp](?P<value>%s)" % regex_float_pattern),
	floatR=re.compile(r"(^|[^A-Za-z])[Rr](?P<value>%s)" % regex_float_pattern),
	floatS=re.compile(r"(^|[^A-Za-z])[Ss](?P<value>%s)" % regex_float_pattern),
	floatX=re.compile(r"(^|[^A-Za-z])[Xx](?P<value>%s)" % regex_float_pattern),
	floatY=re.compile(r"(^|[^A-Za-z])[Yy](?P<value>%s)" % regex_float_pattern),
	floatZ=re.compile(r"(^|[^A-Za-z])[Zz](?P<value>%s)" % regex_float_pattern),
	intN=re.compile(r"(^|[^A-Za-z])[Nn](?P<value>%s)" % regex_int_pattern),
	intS=re.compile(r"(^|[^A-Za-z])[Ss](?P<value>%s)" % regex_int_pattern),
	intT=re.compile(r"(^|[^A-Za-z])[Tt](?P<value>%s)" % regex_int_pattern))
"""Regexes for parsing various GCODE command parameters."""

regex_minMaxError = re.compile(r"Error:[0-9]\n")
"""Regex matching first line of min/max errors from the firmware."""

regex_marlinKillError = re.compile(
	r"Heating failed|Thermal Runaway|MAXTEMP triggered|MINTEMP triggered|Invalid extruder number|Watchdog barked|KILL caused"
)
"""Regex matching first line of kill causing errors from Marlin."""

regex_sdPrintingByte = re.compile(r"(?P<current>[0-9]+)/(?P<total>[0-9]+)")
"""Regex matching SD printing status reports.

Groups will be as follows:

  * ``current``: current byte position in file being printed
  * ``total``: total size of file being printed
"""

regex_sdFileOpened = re.compile(
	r"File opened:\s*(?P<name>.*?)\s+Size:\s*(?P<size>%s)" % regex_int_pattern)
"""Regex matching "File opened" messages from the firmware.

Groups will be as follows:

  * ``name``: name of the file reported as having been opened (str)
  * ``size``: size of the file in bytes (int)
"""

regex_temp = re.compile(
	r"(?P<tool>B|C|T(?P<toolnum>\d*)):\s*(?P<actual>%s)(\s*\/?\s*(?P<target>%s))?"
	% (regex_float_pattern, regex_float_pattern))
"""Regex matching temperature entries in line.

Groups will be as follows:

  * ``tool``: whole tool designator, incl. optional ``toolnum`` (str)
  * ``toolnum``: tool number, if provided (int)
  * ``actual``: actual temperature (float)
  * ``target``: target temperature, if provided (float)
"""

regex_repetierTempExtr = re.compile(
	r"TargetExtr(?P<toolnum>\d+):(?P<target>%s)" % regex_float_pattern)
"""Regex for matching target temp reporting from Repetier.

Groups will be as follows:

  * ``toolnum``: number of the extruder to which the target temperature
	report belongs (int)
  * ``target``: new target temperature (float)
"""

regex_repetierTempBed = re.compile(r"TargetBed:(?P<target>%s)" %
								   regex_float_pattern)
"""Regex for matching target temp reporting from Repetier for beds.

Groups will be as follows:

  * ``target``: new target temperature (float)
"""

regex_position = re.compile(
	r"X:\s*(?P<x>{float})\s*Y:\s*(?P<y>{float})\s*Z:\s*(?P<z>{float})\s*((E:\s*(?P<e>{float}))|(?P<es>(E\d+:\s*{float}\s*)+))"
		.format(float=regex_float_pattern))
"""Regex for matching position reporting.

Groups will be as follows:

  * ``x``: X coordinate
  * ``y``: Y coordinate
  * ``z``: Z coordinate
  * ``e``: E coordinate if present, or
  * ``es``: multiple E coordinates if present, to be parsed further with regex_e_positions
"""

regex_e_positions = re.compile(
	r"E(?P<id>\d+):\s*(?P<value>{float})".format(float=regex_float_pattern))
"""Regex for matching multiple E coordinates in a position report.

Groups will be as follows:

  * ``id``: id of the extruder or which the position is reported
  * ``value``: reported position value
"""

regex_firmware_splitter = re.compile(r"\s*([A-Z0-9_]+):\s*")
"""Regex to use for splitting M115 responses."""

regex_resend_linenumber = re.compile(r"(N|N:)?(?P<n>%s)" % regex_int_pattern)
"""Regex to use for request line numbers in resend requests"""


def serialList():
	baselist = []
	if os.name == "nt":
		try:
			key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
								 "HARDWARE\\DEVICEMAP\\SERIALCOMM")
			i = 0
			while (1):
				baselist += [winreg.EnumValue(key, i)[1]]
				i += 1
		except Exception:
			pass
	baselist = baselist \
			   + glob.glob("/dev/ttyUSB*") \
			   + glob.glob("/dev/ttyACM*") \
			   + glob.glob("/dev/tty.usb*") \
			   + glob.glob("/dev/cu.*") \
			   + glob.glob("/dev/cuaU*") \
			   + glob.glob("/dev/ttyS*") \
			   + glob.glob("/dev/rfcomm*")

	additionalPorts = settings().get(["serial", "additionalPorts"])
	if additionalPorts:
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
		except Exception:
			_logger.warning(
				"{} is not a valid additional baudrate, ignoring it".format(
					additional))

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


def convert_pause_triggers(configured_triggers):
	if not configured_triggers:
		return dict()

	triggers = {"enable": [], "disable": [], "toggle": []}
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
		except Exception as exc:
			# invalid regex or something like this
			_logger.debug("Problem with trigger %r: %s", trigger, str(exc))

	result = dict()
	for t in triggers.keys():
		if len(triggers[t]) > 0:
			result[t] = re.compile("|".join(
				map(lambda pattern: "({pattern})".format(pattern=pattern),
					triggers[t])))
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
					_logger.warn(
						"Invalid regex {regex} for custom control: {exc}".
							format(regex=control["regex"], exc=str(exc)))

			result[key]["templates"][
				control["template_key"]] = control["template"]

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
		feedback_pattern.append("(?P<group{key}>{pattern})".format(
			key=match_key, pattern=entry["pattern"]))
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

	reported_extruders = list(
		filter(lambda x: x.startswith("T"), parsed.keys()))
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
		toolNumber = int(
			toolnum) if toolnum is not None and len(toolnum) else None
		if toolNumber and toolNumber > maxToolNum:
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

	if line.startswith("NAME."):
		# Good job Malyan. Why use a : when you can also just use a ., right? Let's revert that.
		line = list(line)
		line[4] = ":"
		line = "".join(line)

	result = dict()
	split_line = regex_firmware_splitter.split(
		line.strip())[1:]  # first entry is empty start of trimmed string
	for key, value in chunks(split_line, 2):
		result[key] = value.strip()
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


def parse_position_line(line):
	"""
	Parses the provided M114 response line and returns the parsed coordinates.

	Args:
		line (str): the line to parse

	Returns:
		dict or None: the parsed coordinates, or None if no coordinates could be parsed
	"""

	match = regex_position.search(line)
	if match is not None:
		result = dict(x=float(match.group("x")),
					  y=float(match.group("y")),
					  z=float(match.group("z")))
		if match.group("e") is not None:
			# report contains only one E
			result["e"] = float(match.group("e"))

		elif match.group("es") is not None:
			# report contains individual entries for multiple extruders ("E0:... E1:... E2:...")
			es = match.group("es")
			for m in regex_e_positions.finditer(es):
				result["e{}".format(m.group("id"))] = float(m.group("value"))

		else:
			# apparently no E at all, should never happen but let's still handle this
			return None

		return result

	return None


def normalize_command_handler_result(command,
									 command_type,
									 gcode,
									 subcode,
									 tags,
									 handler_results,
									 tags_to_add=None):
	"""
	Normalizes a command handler result.

	Handler results can be either ``None``, a single result entry or a list of result
	entries.

	``None`` results are ignored, the provided ``command``, ``command_type``,
	``gcode``, ``subcode`` and ``tags`` are returned in that case (as single-entry list with
	one 5-tuple as entry).

	Single result entries are either:

	  * a single string defining a replacement ``command``
	  * a 1-tuple defining a replacement ``command``
	  * a 2-tuple defining a replacement ``command`` and ``command_type``
	  * a 3-tuple defining a replacement ``command`` and ``command_type`` and additional ``tags`` to set

	A ``command`` that is ``None`` will lead to the entry being ignored for
	the normalized result.

	The method returns a list of normalized result entries. Normalized result
	entries always are a 4-tuple consisting of ``command``, ``command_type``,
	``gcode`` and ``subcode``, the latter three being allowed to be ``None``. The list may
	be empty in which case the command is to be suppressed.

	Examples:
		>>> _normalize_command_handler_result("M105", None, "M105", None, None, None) # doctest: +ALLOW_UNICODE
		[('M105', None, 'M105', None, None)]
		>>> _normalize_command_handler_result("M105", None, "M105", None, None, "M110") # doctest: +ALLOW_UNICODE
		[('M110', None, 'M110', None, None)]
		>>> _normalize_command_handler_result("M105", None, "M105", None, None, ["M110"]) # doctest: +ALLOW_UNICODE
		[('M110', None, 'M110', None, None)]
		>>> _normalize_command_handler_result("M105", None, "M105", None, None, ["M110", "M117 Foobar"]) # doctest: +ALLOW_UNICODE
		[('M110', None, 'M110', None, None), ('M117 Foobar', None, 'M117', None, None)]
		>>> _normalize_command_handler_result("M105", None, "M105", None, None, [("M110",), "M117 Foobar"]) # doctest: +ALLOW_UNICODE
		[('M110', None, 'M110', None, None), ('M117 Foobar', None, 'M117', None, None)]
		>>> _normalize_command_handler_result("M105", None, "M105", None, None, [("M110", "lineno_reset"), "M117 Foobar"]) # doctest: +ALLOW_UNICODE
		[('M110', 'lineno_reset', 'M110', None, None), ('M117 Foobar', None, 'M117', None, None)]
		>>> _normalize_command_handler_result("M105", None, "M105", None, None, []) # doctest: +ALLOW_UNICODE
		[]
		>>> _normalize_command_handler_result("M105", None, "M105", None, None, ["M110", None]) # doctest: +ALLOW_UNICODE
		[('M110', None, 'M110', None, None)]
		>>> _normalize_command_handler_result("M105", None, "M105", None, None, [("M110",), (None, "ignored")]) # doctest: +ALLOW_UNICODE
		[('M110', None, 'M110', None, None)]
		>>> _normalize_command_handler_result("M105", None, "M105", None, None, [("M110",), ("M117 Foobar", "display_message"), ("tuple", "of", "unexpected", "length"), ("M110", "lineno_reset")]) # doctest: +ALLOW_UNICODE
		[('M110', None, 'M110', None, None), ('M117 Foobar', 'display_message', 'M117', None, None), ('M110', 'lineno_reset', 'M110', None, None)]
		>>> _normalize_command_handler_result("M105", None, "M105", None, {"tag1", "tag2"}, ["M110", "M117 Foobar"]) # doctest: +ALLOW_UNICODE
		[('M110', None, 'M110', None, {'tag1', 'tag2'}), ('M117 Foobar', None, 'M117', None, {'tag1', 'tag2'})]
		>>> _normalize_command_handler_result("M105", None, "M105", None, {"tag1", "tag2"}, ["M110", "M105", "M117 Foobar"], tags_to_add={"tag3"}) # doctest: +ALLOW_UNICODE
		[('M110', None, 'M110', None, {'tag1', 'tag2', 'tag3'}), ('M105', None, 'M105', None, {'tag1', 'tag2'}), ('M117 Foobar', None, 'M117', None, {'tag1', 'tag2', 'tag3'})]
		>>> _normalize_command_handler_result("M105", None, "M105", None, {"tag1", "tag2"}, ["M110", ("M105", "temperature_poll"), "M117 Foobar"], tags_to_add={"tag3"}) # doctest: +ALLOW_UNICODE
		[('M110', None, 'M110', None, {'tag1', 'tag2', 'tag3'}), ('M105', 'temperature_poll', 'M105', None, {'tag1', 'tag2', 'tag3'}), ('M117 Foobar', None, 'M117', None, {'tag1', 'tag2', 'tag3'})]

	Arguments:
		command (str or None): The command for which the handler result was
			generated
		command_type (str or None): The command type for which the handler
			result was generated
		gcode (str or None): The GCODE for which the handler result was
			generated
		subcode (str or None): The GCODE subcode for which the handler result
			was generated
		tags (set of str or None): The tags associated with the GCODE for which
			the handler result was generated
		handler_results: The handler result(s) to normalized. Can be either
			a single result entry or a list of result entries.
		tags_to_add (set of str or None): List of tags to add to expanded result
			entries

	Returns:
		(list) - A list of normalized handler result entries, which are
			5-tuples consisting of ``command``, ``command_type``, ``gcode``
			``subcode`` and ``tags``, the latter three of which may be ``None``.
	"""

	original = (command, command_type, gcode, subcode, tags)

	if handler_results is None:
		# handler didn't return anything, we'll just continue
		return [original]

	if not isinstance(handler_results, list):
		handler_results = [
			handler_results,
		]

	result = []
	for handler_result in handler_results:
		# we iterate over all handler result entries and process each one
		# individually here

		if handler_result is None:
			# entry is None, we'll ignore that entry and continue
			continue

		if tags:
			# copy the tags
			tags = set(tags)

		if isinstance(handler_result, basestring):
			# entry is just a string, replace command with it
			command = handler_result

			if command != original[0]:
				# command changed, re-extract gcode and subcode and add tags if necessary
				gcode, subcode = gcode_and_subcode_for_cmd(command)

				if tags_to_add and isinstance(tags_to_add,
											  set) and command != original[0]:
					if tags is None:
						tags = set()
					tags |= tags_to_add

			result.append((command, command_type, gcode, subcode, tags))

		elif isinstance(handler_result, tuple):
			# entry is a tuple, extract command and command_type
			hook_result_length = len(handler_result)
			handler_tags = None

			if hook_result_length == 1:
				# handler returned just the command
				command, = handler_result
			elif hook_result_length == 2:
				# handler returned command and command_type
				command, command_type = handler_result
			elif hook_result_length == 3:
				# handler returned command, command type and additional tags
				command, command_type, handler_tags = handler_result
			else:
				# handler returned a tuple of an unexpected length, ignore
				# and continue
				continue

			if command is None:
				# command is None, ignore it and continue
				continue

			if command != original[0] or command_type != original[2]:
				# command or command_type changed, re-extract gcode and subcode and add tags if necessary
				gcode, subcode = gcode_and_subcode_for_cmd(command)

				if tags_to_add and isinstance(tags_to_add, set):
					if tags is None:
						tags = set()
					tags |= tags_to_add

			if handler_tags and isinstance(handler_tags, set):
				# handler provided additional tags, add them
				if tags is None:
					tags = set()
				tags |= handler_tags

			result.append((command, command_type, gcode, subcode, tags))

		# reset to original
		command, command_type, gcode, subcode, tags = original

	return result

# --- Test code for speed testing the comm layer via command line follows
