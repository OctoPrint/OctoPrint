# coding=utf-8
from __future__ import absolute_import, unicode_literals, print_function, division

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2016 The OctoPrint Project - Released under terms of the AGPLv3 License"

import re
import Queue as queue

regex_float_pattern = "[-+]?[0-9]*\.?[0-9]+"
regex_positive_float_pattern = "[+]?[0-9]*\.?[0-9]+"
regex_int_pattern = "\d+"

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


class GcodeCommand(object):

	known_float_attributes = ("x", "y", "z", "e", "s", "p", "r")
	known_int_attributes = ("f", "t", "n")
	known_attributes = known_float_attributes + known_int_attributes

	command_regex = re.compile("^\s*((?P<GM>[GM](?P<number>\d+))|(?P<T>T(?P<tool>\d+))|(?P<F>F(?P<feedrate>\d+)))")

	argument_pattern = "\s*([{float_args}]{float}|[{int_args}]{int})".format(float_args="".join(map(lambda x: x.upper(), known_float_attributes)),
	                                                                         int_args="".join(map(lambda x: x.upper(), known_int_attributes)),
	                                                                         float=regex_float_pattern,
	                                                                         int=regex_int_pattern)
	argument_regex = re.compile(argument_pattern)
	param_regex = re.compile("^[GMT]\d+\s+(.*?)$")

	@staticmethod
	def from_line(line):
		"""
		>>> gcode = GcodeCommand.from_line("M30 some_file.gco")
		>>> gcode.command
		'M30'
		>>> gcode.param
		'some_file.gco'
		>>> gcode = GcodeCommand.from_line("G28 X0 Y0")
		>>> gcode.command
		'G28'
		>>> gcode.x
		0.0
		>>> gcode.y
		0.0
		>>> gcode = GcodeCommand.from_line("M104 S220.0 T1")
		>>> gcode.command
		'M104'
		>>> gcode.s
		220.0
		>>> gcode.t
		1
		"""

		if isinstance(line, GcodeCommand):
			return line

		line = line.strip()
		command = ""
		args = {"original": line}
		match = GcodeCommand.command_regex.match(line)
		if match is None:
			args["unknown"] = True
		else:
			if match.group("GM"):
				command = match.group("GM")

				matched_args = GcodeCommand.argument_regex.findall(line)
				if not matched_args:
					param_match = GcodeCommand.param_regex.match(line)
					if param_match is not None:
						args["param"] = param_match.group(1)
				else:
					for arg in matched_args:
						key = arg[0].lower()
						if key in GcodeCommand.known_int_attributes:
							value = int(arg[1:])
						elif key in GcodeCommand.known_float_attributes:
							value = float(arg[1:])
						else:
							value = str(arg[1:])
						args[key] = value
			elif match.group("T"):
				command = "T"
				args["tool"] = match.group("tool")
			elif match.group("F"):
				command = "F"
				args["f"] = match.group("feedrate")

		return GcodeCommand(command, **args)

	def __init__(self, command, **kwargs):
		self.command = command
		self.x = None
		self.y = None
		self.z = None
		self.e = None
		self.s = None
		self.p = None
		self.r = None
		self.f = None
		self.t = None
		self.n = None

		self.tool = None
		self.original = None
		self.param = None

		self.progress = None
		self.callback = None

		self.unknown = False

		for key, value in kwargs.iteritems():
			if key in GcodeCommand.known_attributes + ("tool", "original", "param", "progress", "callback", "unknown"):
				self.__setattr__(key, value)

	def __repr__(self):
		return "GcodeCommand(\"{str}\",progress={progress})".format(str=str(self), progress=self.progress)

	def __str__(self):
		if self.original is not None:
			return self.original
		else:
			attr = []
			for key in GcodeCommand.known_attributes:
				value = self.__getattribute__(key)
				if value is not None:
					if key in GcodeCommand.known_int_attributes:
						attr.append("%s%d" % (key.upper(), value))
					elif key in GcodeCommand.known_float_attributes:
						attr.append("%s%f" % (key.upper(), value))
					else:
						attr.append("%s%r" % (key.upper(), value))
			attributeStr = " ".join(attr)
			return "%s%s%s" % (self.command.upper(), " " + attributeStr if attributeStr else "", " " + self.param if self.param else "")

class TypedQueue(queue.Queue):

	def __init__(self, maxsize=0):
		queue.Queue.__init__(self, maxsize=maxsize)
		self._lookup = []

	def _put(self, item):
		if isinstance(item, tuple) and len(item) == 3:
			cmd, line, cmd_type = item
			if cmd_type is not None:
				if cmd_type in self._lookup:
					raise TypeAlreadyInQueue(cmd_type, "Type {cmd_type} is already in queue".format(**locals()))
				else:
					self._lookup.append(cmd_type)

		queue.Queue._put(self, item)

	def _get(self):
		item = queue.Queue._get(self)

		if isinstance(item, tuple) and len(item) == 3:
			cmd, line, cmd_type = item
			if cmd_type is not None and cmd_type in self._lookup:
				self._lookup.remove(cmd_type)

		return item


class TypeAlreadyInQueue(Exception):
	def __init__(self, t, *args, **kwargs):
		Exception.__init__(self, *args, **kwargs)
		self.type = t


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

