# coding=utf-8
from __future__ import absolute_import, unicode_literals, print_function, \
	division

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

import re

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

class Command(object):
	@staticmethod
	def from_line(line, type=None, tags=None, **kwargs):
		if isinstance(line, Command):
			return line

		line = line.strip()
		if GcodeCommand.command_regex.match(line):
			return GcodeCommand.from_line(line, type=type, tags=tags, **kwargs)
		elif line.startswith("@"):
			return AtCommand.from_line(line, type=type, tags=tags, **kwargs)
		else:
			return Command(line, type=type, tags=tags)

	def __init__(self, line, type=None, tags=None):
		if tags is None:
			tags = set()

		self.line = line
		self.type = type
		self.tags = tags

	def __repr__(self):
		return "{}({!r},type={!r},tags={!r})".format(self.__class__.__name__, self.line, self.type, self.tags)

	def __str__(self):
		return self.line

	def __key(self):
		return self.line, self.type

	def __eq__(self, other):
		return self.__key() == other.__key()

	def __hash__(self):
		return hash(self.__key())

class AtCommand(Command):
	@staticmethod
	def from_line(line, **kwargs):
		split = line.split(None, 1)
		if len(split) == 2:
			atcommand = split[0]
			parameters = split[1]
		else:
			atcommand = split[0]
			parameters = ""

		atcommand = atcommand[1:]

		return AtCommand(line, atcommand, parameters, **kwargs)

	def __init__(self, line, atcommand, parameters, **kwargs):
		self.atcommand = atcommand
		self.parameters = parameters
		super(AtCommand, self).__init__(line, **kwargs)

	def __repr__(self):
		return "AtCommand({!r},{!r},{!r},type={!r},tags={!r}".format(self.line,
		                                                             self.atcommand,
		                                                             self.parameters,
		                                                             self.type,
		                                                             self.tags)

class GcodeCommand(Command):

	known_float_attributes = (b"x", b"y", b"z", b"e", b"s", b"p", b"r")
	known_int_attributes = (b"f", b"t", b"n")
	known_attributes = known_float_attributes + known_int_attributes

	command_regex = re.compile("^\s*((?P<GM>[GM](?P<number>\d+))(\\.(?P<subcode>\d+))?|(?P<T>T(?P<tool>\d+))|(?P<F>F(?P<feedrate>\d+)))")

	argument_pattern = "\s*([{float_args}]{float}|[{int_args}]{int})".format(float_args="".join(map(lambda x: x.upper(), known_float_attributes)),
	                                                                         int_args="".join(map(lambda x: x.upper(), known_int_attributes)),
	                                                                         float=regex_float_pattern,
	                                                                         int=regex_int_pattern)
	argument_regex = re.compile(argument_pattern)
	param_regex = re.compile("^[GMTF]\d+(\\.\d+)?\s+(?P<param>.*?)$")

	command_parameters = known_attributes + (b"subcode", b"tool", b"param")

	@staticmethod
	def from_line(line, **kwargs):
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

		tags = kwargs.get(b"tags")
		if tags is None:
			tags = set()

		type = kwargs.get(b"type")

		line = line.strip()
		code = ""
		args = {"original": line, "type": type, "tags": tags}
		match = GcodeCommand.command_regex.match(line)
		if match is None:
			args["unknown"] = True
		else:
			if match.group("GM"):
				code = match.group("GM")

				if match.group("subcode"):
					args[b"subcode"] = int(match.group("subcode"))

				matched_args = GcodeCommand.argument_regex.findall(line)
				if not matched_args:
					param = line[len(match.group(0)):].lstrip()
					if param:
						args[b"param"] = param
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
				args[b"tool"] = match.group("tool")
			elif match.group("F"):
				code = "F"
				args[b"f"] = match.group("feedrate")

		return GcodeCommand(code, **args)

	def __init__(self, code, **kwargs):
		self.code = code

		for key in GcodeCommand.command_parameters:
			try:
				setattr(self, key, kwargs[key])
			except KeyError:
				setattr(self, key, None)

		original = kwargs.get(b"original")
		if original is None:
			line = self._to_line()
		else:
			line = original

		super(GcodeCommand, self).__init__(line, type=kwargs.get(b"type", None), tags=kwargs.get(b"tags", None))

	def __str__(self):
		kwargs = dict((k, self.getattr(k)) for k in GcodeCommand.command_parameters if self.getattr(k) is not None)
		return "GcodeCommand({},original={},type={},tags={})".format(self.code, self.line, ["{}={!r}".format(key, value) for key, value in kwargs.items()], self.type, self.tags)

	def _to_line(self):
		attr = []
		for key in GcodeCommand.known_attributes:
			value = getattr(self, key, None)
			if value is not None:
				attr.append("{}{!r}".format(key.upper(), value))
		attribute_str = " ".join(attr)
		return "{}{}{}".format(self.code.upper(), " " + attribute_str if attribute_str else "",
		                       " " + self.param if self.param else "")
