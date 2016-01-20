# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"

from . import Protocol, FileStreamingProtocolMixin, MotorControlProtocolMixin, FanControlProtocolMixin

import re

regex_float_pattern = "[-+]?[0-9]*\.?[0-9]+"
regex_positive_float_pattern = "[+]?[0-9]*\.?[0-9]+"
regex_int_pattern = "\d+"

regex_float = re.compile(regex_float_pattern)
"""Regex for a float value."""

class ReprapGcodeProtocol(Protocol, MotorControlProtocolMixin, FanControlProtocolMixin, FileStreamingProtocolMixin):

	def __init__(self, flavor):
		super(Protocol, self).__init__()
		self.flavor = flavor

		self._transport = None

	def connect(self, transport):
		self._transport = transport

	def move(self, x=None, y=None, z=None, e=None, feedrate=None, relative=False):
		commands = [self.flavor.command_move(x=x, y=y, z=z, e=e, f=feedrate)]

		if relative:
			commands = [self.flavor.command_set_relative_positioning()] + commands + [self.flavor.command_set_absolute_positioning()]

		self._send(*commands)

	def home(self, x=False, y=False, z=False):
		self._send(self.flavor.command_home(x=x, y=y, z=z))

	def set_feedrate_multiplier(self, multiplier):
		self._send(self.flavor.command_set_feedrate_multiplier(multiplier))

	def set_extrusion_multiplier(self, multiplier):
		self._send(self.flavor.command.set_extrusion_multiplier(multiplier))

	##~~ MotorControlProtocolMixin

	def set_motors(self, enabled):
		self._send(self.flavor.command.set_motors(enabled))

	##~~ FanControlProtocolMixin

	def set_fan_speed(self, speed):
		self._send(self.flavor.command.set_fan_speed(speed))

	##~~ FileStreamingProtocolMixin

	def init_file_storage(self):
		pass

	def list_files(self):
		pass

	def start_file_print(self, name):
		pass

	def pause_file_print(self):
		pass

	def resume_file_print(self):
		pass

	def delete_file(self, name):
		pass

	def record_file(self, name, job):
		pass

	def stop_recording_file(self):
		pass

	def _send(self, *commands):
		pass

class ReprapGcodeFlavor(object):

	regex_temp = re.compile("(?P<tool>B|T(?P<toolnum>\d*)):\s*(?P<actual>%s)(\s*\/?\s*(?P<target>%s))?" % (regex_positive_float_pattern, regex_positive_float_pattern))
	"""Regex matching temperature entries in line.

	Groups will be as follows:

	  * ``tool``: whole tool designator, incl. optional ``toolnum`` (str)
	  * ``toolnum``: tool number, if provided (int)
	  * ``actual``: actual temperature (float)
	  * ``target``: target temperature, if provided (float)
	"""

	@classmethod
	def message_ok(cls, line, lower_line):
		return lower_line.startswith("ok")

	@classmethod
	def message_start(cls, line, lower_line):
		return lower_line.startswith("start")

	@classmethod
	def message_wait(cls, line, lower_line):
		return lower_line.startswith("wait")

	@classmethod
	def message_resend(cls, line, lower_line):
		return lower_line.startswith("resend") or lower_line.startswith("rs")

	@classmethod
	def message_temperature(cls, line, lower_line):
		return " T:" in line or line.startswith("T:") or " T0:" in line or line.startswith("T0:")

	@classmethod
	def message_error(cls, line, lower_line):
		return line.startswith("Error:") or line.startswith("!!")

	@classmethod
	def message_error_multiline(cls, line, lower_line):
		return False

	@classmethod
	def message_error_communication(cls, line, lower_line):
		return False

	@classmethod
	def command_get_temp(cls):
		return GcodeCommand("M105")

	@classmethod
	def command_set_extruder_temp(cls, s, t, w):
		return GcodeCommand("M109", s=s, t=t) if w else GcodeCommand("M104", s=s, t=t)

	@classmethod
	def command_set_line(cls, n):
		return GcodeCommand("M110", n=n)

	@classmethod
	def command_set_bed_temp(cls, s, w):
		return GcodeCommand("M190", s=s) if w else GcodeCommand("M140", s=s)

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
	def set_tool(cls, tool):
		return GcodeCommand("T{}".format(tool))

	@classmethod
	def set_feedrate_multiplier(cls, multiplier):
		return GcodeCommand("M220", s=multiplier)

	@classmethod
	def set_extrusion_multiplier(cls, multiplier):
		return GcodeCommand("M221", s=multiplier)

	@classmethod
	def set_fan_speed(cls, speed):
		return GcodeCommand("M106", s=speed)

	@classmethod
	def set_motors(cls, enable):
		return GcodeCommand("M17") if enable else GcodeCommand("M18")



class GcodeCommand(object):

	known_float_attributes = ("x", "y", "z", "e", "s", "p", "r")
	known_int_attributes = ("f", "t", "n")
	known_attributes = known_float_attributes + known_int_attributes

	command_regex = re.compile("^\s*((?P<commandGM>[GM]\d+)|(?P<commandT>T)\d+|(?P<commandF>F)\d+)")
	argument_regex = re.compile("\s+([%s][-+]?\d*\.?\d+|[%s][-+]?\d+)" % ("".join(map(lambda x: x.upper(), known_float_attributes)), "".join(map(lambda x: x.upper(), known_int_attributes))))
	param_regex = re.compile("^[GMT]\d+\s+(.*?)$")

	@staticmethod
	def from_line(line):
		line = line.strip()
		command = ""
		args = {"original": line}
		match = GcodeCommand.command_regex.match(line)
		if match is None:
			args["unknown"] = True
		else:
			commandType = match.group(1)
			commandNumber = int(match.group(2))
			command = "%s%d" % (commandType, commandNumber)


			if commandType == "T":
				args["tool"] = commandNumber
			else:
				matchedArgs = GcodeCommand.argument_regex.findall(line)
				if len(matchedArgs) == 0:
					paramMatch = GcodeCommand.param_regex.match(line)
					if paramMatch is not None:
						args["param"] = paramMatch.group(1)
				else:
					for arg in matchedArgs:
						key = arg[0].lower()
						if key in GcodeCommand.known_int_attributes:
							value = int(arg[1:])
						elif key in GcodeCommand.known_float_attributes:
							value = float(arg[1:])
						else:
							value = str(arg[1:])
						args[key] = value

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

	def isGetTemperatureCommand(self):
		return self.command == "M105"

	def isSetTemperatureCommand(self):
		return self.command in ("M104", "M140", "M109", "M190")

	def isSelectToolCommand(self):
		return self.command.startswith("T")

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
