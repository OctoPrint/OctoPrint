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
	floatR=re.compile("(^|[^A-Za-z])[Rr](?P<value>%s)" % regex_float_pattern),
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

	command_regex = re.compile("^\s*((?P<GM>[GM](?P<number>\d+))(\\.(?P<subcode>\d+))?|(?P<T>T(?P<tool>\d+))|(?P<F>F(?P<feedrate>\d+)))")

	argument_pattern = "\s*([{float_args}]{float}|[{int_args}]{int})".format(float_args="".join(map(lambda x: x.upper(), known_float_attributes)),
	                                                                         int_args="".join(map(lambda x: x.upper(), known_int_attributes)),
	                                                                         float=regex_float_pattern,
	                                                                         int=regex_int_pattern)
	argument_regex = re.compile(argument_pattern)
	param_regex = re.compile("^[GMTF]\d+(\\.\d+)?\s+(?P<param>.*?)$")

	@staticmethod
	def from_line(line, tags=None):
		"""
		>>> gcode = GcodeCommand.from_line("M30 some_file.gco")
		>>> gcode.code
		u'M30'
		>>> gcode.param
		u'some_file.gco'
		>>> gcode = GcodeCommand.from_line("G28 X0 Y0")
		>>> gcode.code
		u'G28'
		>>> gcode.x
		0.0
		>>> gcode.y
		0.0
		>>> gcode = GcodeCommand.from_line("M104 S220.0 T1")
		>>> gcode.code
		u'M104'
		>>> gcode.s
		220.0
		>>> gcode.t
		1
		>>> gcode = GcodeCommand.from_line("M123.456 my parameter is long")
		>>> gcode.code
		u'M123'
		>>> gcode.subcode
		456
		>>> gcode.param
		u'my parameter is long'
		"""

		if isinstance(line, GcodeCommand):
			return line

		if tags is None:
			tags = set()

		line = line.strip()
		code = ""
		subcode = None
		args = {"original": line, "tags": tags}
		match = GcodeCommand.command_regex.match(line)
		if match is None:
			args["unknown"] = True
		else:
			if match.group("GM"):
				code = match.group("GM")

				if match.group("subcode"):
					subcode = int(match.group("subcode"))

				matched_args = GcodeCommand.argument_regex.findall(line)
				if not matched_args:
					param = line[len(match.group(0)):].lstrip()
					if param:
						args["param"] = param
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
				code = "T"
				args["tool"] = match.group("tool")
			elif match.group("F"):
				code = "F"
				args["f"] = match.group("feedrate")

		return GcodeCommand(code, subcode=subcode, **args)

	def __init__(self, command, subcode=None, **kwargs):
		self.code = command
		self.subcode = subcode

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
		self.tags = set()

		self.unknown = False

		for key, value in kwargs.items():
			if key in GcodeCommand.known_attributes + ("tool", "original", "param", "progress", "callback", "tags", "unknown"):
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
					attr.append("{}{!r}".format(key.upper(), value))
			attribute_str = " ".join(attr)
			return "{}{}{}".format(self.code.upper(), " " + attribute_str if attribute_str else "", " " + self.param if self.param else "")


class TypedQueue(queue.Queue):

	def __init__(self, maxsize=0):
		queue.Queue.__init__(self, maxsize=maxsize)
		self._lookup = set()

	def put(self, item, item_type=None, *args, **kwargs):
		queue.Queue.put(self, (item, item_type), *args, **kwargs)

	def get(self, *args, **kwargs):
		item, _ = queue.Queue.get(self, *args, **kwargs)
		return item

	def _put(self, item):
		_, item_type = item
		if item_type is not None:
			if item_type in self._lookup:
				raise TypeAlreadyInQueue(item_type, "Type {} is already in queue".format(item_type))
			else:
				self._lookup.add(item_type)

		queue.Queue._put(self, item)

	def _get(self):
		item = queue.Queue._get(self)
		_, item_type = item

		if item_type is not None:
			self._lookup.discard(item_type)

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
	return "".join(result).strip()

