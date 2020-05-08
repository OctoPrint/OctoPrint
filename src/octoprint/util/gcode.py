# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import re

from octoprint.settings import settings

regex_command = re.compile(
	r"^\s*((?P<codeGM>[GM]\d+)(\.(?P<subcode>\d+))?|(?P<codeT>T)\d+|(?P<codeF>F)\d+)"
)
"""Regex for a GCODE command."""

def process_gcode_line(line, offsets=None, current_tool=None):
	line = strip_comment(line).strip()
	if not len(line):
		return None

	if offsets is not None:
		line = apply_temperature_offsets(line,
										 offsets,
										 current_tool=current_tool)

	return line


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


_temp_command_regex = re.compile(
	r"^M(?P<command>104|109|140|190)(\s+T(?P<tool>\d+)|\s+S(?P<temperature>[-+]?\d*\.?\d*))+"
)


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
	if current_tool is not None and (groups["command"] == "104"
									 or groups["command"] == "109"):
		# extruder temperature, determine which one and retrieve corresponding offset
		tool_num = current_tool
		if "tool" in groups and groups["tool"] is not None:
			tool_num = int(groups["tool"])

		tool_key = "tool%d" % tool_num
		offset = offsets[
			tool_key] if tool_key in offsets and offsets[tool_key] else 0

	elif groups["command"] == "140" or groups["command"] == "190":
		# bed temperature
		offset = offsets["bed"] if "bed" in offsets else 0

	if offset == 0:
		return line

	temperature = float(groups["temperature"])
	if temperature == 0:
		return line

	return line[:match.start("temperature")] + "%f" % (
		temperature + offset) + line[match.end("temperature"):]


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
	elif settings().getBoolean(["serial", "supportFAsCommand"
								]) and "codeF" in values and values["codeF"]:
		gcode = values["codeF"]
	else:
		# this should never happen
		return None, None

	return gcode, values.get("subcode", None)
