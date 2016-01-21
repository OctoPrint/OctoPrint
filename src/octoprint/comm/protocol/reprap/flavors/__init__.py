# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


import re

from octoprint.comm.protocol.reprap import GcodeCommand, regex_positive_float_pattern


class ReprapGcodeFlavor(object):

	key = "generic"

	unknown_requires_ack = False
	unknown_with_checksum = False

	always_send_checksum = False
	never_send_checksum = False

	checksum_requiring_commands = ["M110"]
	long_running_commands = ["G4", "G28", "G29", "G30", "G32", "M400", "M226"]

	regex_temp = re.compile("(?P<tool>B|T(?P<toolnum>\d*)):\s*(?P<actual>%s)(\s*\/?\s*(?P<target>%s))?" % (regex_positive_float_pattern, regex_positive_float_pattern))
	"""Regex matching temperature entries in line.

	Groups will be as follows:

	  * ``tool``: whole tool designator, incl. optional ``toolnum`` (str)
	  * ``toolnum``: tool number, if provided (int)
	  * ``actual``: actual temperature (float)
	  * ``target``: target temperature, if provided (float)
	"""

	regex_sd_file_opened = re.compile("File opened:\s*(?P<name>.*?)(\s+Size:\s*(?P<size>[0-9]+))?")

	##~~ Message matchers

	@classmethod
	def comm_ok(cls, line, lower_line, state):
		return lower_line.startswith("ok")

	@classmethod
	def comm_start(cls, line, lower_line, state):
		return lower_line.startswith("start")

	@classmethod
	def comm_wait(cls, line, lower_line, state):
		return lower_line.startswith("wait")

	@classmethod
	def comm_resend(cls, line, lower_line, state):
		return lower_line.startswith("resend") or lower_line.startswith("rs")

	@classmethod
	def comm_error(cls, line, lower_line, state):
		return line.startswith("Error:") or line.startswith("!!")

	@classmethod
	def comm_error_multiline(cls, line, lower_line, state):
		return False

	@classmethod
	def comm_error_communication(cls, line, lower_line, state):
		return False

	@classmethod
	def message_temperature(cls, line, lower_line, state):
		return " T:" in line or line.startswith("T:") or " T0:" in line or line.startswith("T0:")

	@classmethod
	def message_sd_init_ok(cls, line, lower_line, state):
		return "sd card ok" in lower_line

	@classmethod
	def message_sd_init_fail(cls, line, lower_line, state):
		return "sd init fail" in lower_line or "volume.init failed" in lower_line or "openroot failed" in lower_line

	@classmethod
	def message_sd_file_opened(cls, line, lower_line, state):
		return lower_line.startswith("file opened")

	@classmethod
	def message_sd_file_selected(cls, line, lower_line, state):
		return lower_line.startswith("file selected")

	@classmethod
	def message_sd_begin_file_list(cls, line, lower_line, state):
		return lower_line.startswith("begin file list")

	@classmethod
	def message_sd_end_file_list(cls, line, lower_line, state):
		return lower_line.startswith("end file list")

	@classmethod
	def message_sd_printing_byte(cls, line, lower_line, state):
		return "sd printing byte" in lower_line

	@classmethod
	def message_sd_not_printing(cls, line, lower_line, state):
		return "no sd printing" in lower_line

	@classmethod
	def message_sd_done_printing(cls, line, lower_line, state):
		return "done printing file" in lower_line

	@classmethod
	def message_sd_begin_writing(cls, line, lower_line, state):
		return "writing to file" in lower_line

	@classmethod
	def message_sd_end_writing(cls, line, lower_line, state):
		return "done saving file" in lower_line

	@classmethod
	def message_sd_entry(cls, line, lower_line, state):
		return state["sd_files_temp"] is not None

	##~~ Message parsers

	@classmethod
	def parse_comm_resend(cls, line, lower_line, state):
		line_to_resend = None
		try:
			line_to_resend = int(line.replace("N:", " ").replace("N", " ").replace(":", " ").split()[-1])
		except:
			if "rs" in line:
				line_to_resend = int(line.split()[1])
		return dict(linenumber=line_to_resend)

	@classmethod
	def parse_message_sd_file_opened(cls, line, lower_line, state):
		match = cls.regex_sd_file_opened.match(lower_line)
		return dict(name=match.group("name"), size=match.group("size"))

	@classmethod
	def parse_message_sd_entry(cls, line, lower_line, state):
		name, size = line.split(" ", 2)
		return dict(name=name, size=int(size))

	##~~ Commands

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

	def command_sd_start(cls):
		return GcodeCommand("M24")

	def command_sd_pause(cls):
		return GcodeCommand("M25")

	def command_sd_set_pos(cls, pos):
		return GcodeCommand("M26", s=pos)

	def command_sd_status(cls):
		return GcodeCommand("M27")

	def command_sd_begin_write(cls, name):
		return GcodeCommand("M28", param=name)

	def command_sd_end_write(cls):
		return GcodeCommand("M29")

	def command_sd_delete(cls, name):
		return GcodeCommand("M30", param=name)
