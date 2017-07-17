# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import unittest

from ddt import ddt, data, unpack

@ddt
class TestCommHelpers(unittest.TestCase):

	@data(
		("M117 Test", "M117 Test"),
		("M117 Test ; foo", "M117 Test "),
		("M117 Test \\; foo", "M117 Test \\; foo"),
		("M117 Test \\\\; foo", "M117 Test \\\\"),
		("M117 Test \\\\\\; foo", "M117 Test \\\\\\; foo"),
		("; foo", "")
	)
	@unpack
	def test_strip_comment(self, input, expected):
		from octoprint.util import comm
		self.assertEqual(expected, comm.strip_comment(input))

	@data(
		("M117 Test", None, None, "M117 Test"),
		("", None, None, None),
		("  \t \r    \n", None, None, None),
		("M117 Test", dict(), 0, "M117 Test")
	)
	@unpack
	def test_process_gcode_line(self, input, offsets, current_tool, expected):
		from octoprint.util import comm
		self.assertEqual(expected, comm.process_gcode_line(input, offsets=offsets, current_tool=current_tool))

	@data(
		("M104 S200", None, None, None),
		("M117 Test", dict(), None, None),
		("M104 T0", dict(), None, None),
		("M104 S220", dict(tool0=10, tool1=20, bed=30), 0, 230.0),
		("M104 T1 S220", dict(tool0=10, tool1=20, bed=30), 0, 240.0),
		("M104 S220", dict(tool0=10, tool1=20, bed=30), 1, 240.0),
		("M140 S100", dict(tool0=10, tool1=20, bed=30), 1, 130.0),
		("M190 S100", dict(tool0=10, tool1=20, bed=30), 1, 130.0),
		("M109 S220", dict(tool0=10, tool1=20, bed=30), 0, 230.0),
		("M109 S220", dict(), 0, None),
		("M140 S100", dict(), 0, None),
		("M104 S220", dict(tool0=0), 0, None),
		("M104 S220", dict(tool0=20), None, None),
		("M104 S0", dict(tool0=20), 0, None)
	)
	@unpack
	def test_apply_temperature_offsets(self, input, offsets, current_tool, expected):
		from octoprint.util import comm
		actual = comm.apply_temperature_offsets(input, offsets, current_tool=current_tool)

		if expected is None:
			self.assertEqual(input, actual)
		else:
			import re
			match = re.search("S(\d+(\.\d+)?)", actual)
			if not match:
				self.fail("No temperature found")
			temperature = float(match.group(1))
			self.assertEqual(expected, temperature)
			self.assertEqual(input[:match.start(1)], actual[:match.start(1)])
			self.assertEqual(input[match.end(1):], actual[match.end(1):])

	def test_convert_pause_triggers(self):
		configured_triggers = [
			dict(regex="pause1", type="enable"),
			dict(regex="pause2", type="enable"),
			dict(regex="resume", type="disable"),
			dict(regex="toggle", type="toggle"),
			dict(type="enable"),
			dict(regex="regex"),
			dict(regex="regex", type="unknown")
		]

		from octoprint.util import comm
		trigger_matchers = comm.convert_pause_triggers(configured_triggers)

		self.assertIsNotNone(trigger_matchers)

		self.assertIn("enable", trigger_matchers)
		self.assertEqual("(pause1)|(pause2)", trigger_matchers["enable"].pattern)

		self.assertIn("disable", trigger_matchers)
		self.assertEqual("(resume)", trigger_matchers["disable"].pattern)

		self.assertIn("toggle", trigger_matchers)
		self.assertEqual("(toggle)", trigger_matchers["toggle"].pattern)

		self.assertNotIn("unknown", trigger_matchers)

	def test_convert_feedback_controls(self):
		def md5sum(input):
			import hashlib
			m = hashlib.md5()
			m.update(input)
			return m.hexdigest()

		temp_regex = "T:((\d*\.)\d+)"
		temp_template = "Temp: {}"
		temp2_template = "Temperature: {}"
		temp_key = md5sum(temp_regex)
		temp_template_key = md5sum(temp_template)
		temp2_template_key = md5sum(temp2_template)

		x_regex = "X:(?P<x>\d+)"
		x_template = "X: {x}"
		x_key = md5sum(x_regex)
		x_template_key = md5sum(x_template)

		configured_controls = [
			dict(key=temp_key, regex=temp_regex, template=temp_template, template_key=temp_template_key),
			dict(command="M117 Hello World", name="Test"),
			dict(children=[
				dict(key=x_key, regex=x_regex, template=x_template, template_key=x_template_key),
				dict(key=temp_key, regex=temp_regex, template=temp2_template, template_key=temp2_template_key)
			])
		]

		from octoprint.util import comm
		controls, matcher = comm.convert_feedback_controls(configured_controls)

		self.assertEqual(2, len(controls))

		# temp_regex is used twice, so we should have two templates for it
		self.assertIn(temp_key, controls)
		temp = controls[temp_key]

		self.assertIsNotNone(temp["matcher"])
		self.assertEqual(temp_regex, temp["matcher"].pattern)
		self.assertEqual(temp_regex, temp["pattern"])

		self.assertEqual(2, len(temp["templates"]))
		self.assertIn(temp_template_key, temp["templates"])
		self.assertEqual(temp_template, temp["templates"][temp_template_key])
		self.assertIn(temp2_template_key, temp["templates"])
		self.assertEqual(temp2_template, temp["templates"][temp2_template_key])

		# x_regex is used once, so we should have only one template for it
		self.assertIn(x_key, controls)
		x = controls[x_key]

		self.assertIsNotNone(x["matcher"])
		self.assertEqual(x_regex, x["matcher"].pattern)
		self.assertEqual(x_regex, x["pattern"])

		self.assertEqual(1, len(x["templates"]))
		self.assertIn(x_template_key, x["templates"])
		self.assertEqual(x_template, x["templates"][x_template_key])

		self.assertEqual("(?P<group{temp_key}>{temp_regex})|(?P<group{x_key}>{x_regex})".format(**locals()), matcher.pattern)

	@data(
		("G4 P2.0", "floatP", True, "2.0"),
		("M109 S220.0", "floatS", True, "220.0"),
		("G1 X10.0 Y10.0 Z0.2", "floatZ", True, "0.2"),
		("G1X10.0Y10.0Z0.2", "floatZ", True, "0.2"),
		("g1x10.0y10.0z0.2", "floatZ", True, "0.2"),
		("M110 N0", "intN", True, "0"),
		("M104 S220.0 T1", "intT", True, "1"),
		("M104 T1 S220.0", "intT", True, "1"),
		("N100 M110", "intN", True, "100"),
		("NP100", "floatP", False, None),
	)
	@unpack
	def test_parameter_regexes(self, line, parameter, should_match, expected_value):
		from octoprint.util.comm import regexes_parameters

		regex = regexes_parameters[parameter]
		match = regex.search(line)

		if should_match:
			self.assertIsNotNone(match)
			self.assertEqual(expected_value, match.group("value"))
		else:
			self.assertIsNone(match)

	@data(
		("G0 X0", "G0"),
		("G28 X0 Y0", "G28"),
		("M109 S220.0 T1", "M109"),
		("M117 Hello World", "M117"),
		("T0", "T"),
		("T3", "T"),
		(None, None),
		("No match", None)
	)
	@unpack
	def test_gcode_command_for_cmd(self, cmd, expected):
		from octoprint.util.comm import gcode_command_for_cmd
		result = gcode_command_for_cmd(cmd)
		self.assertEqual(expected, result)

	@data(
		("G0 X0", "G0", None),
		("M105", "M105", None),
		("T2", "T", None),
		("M80.1", "M80", "1"),
		("G28.2", "G28", "2"),
		("T0.3", "T", None),
		("M80.nosubcode", "M80", None),
		(None, None, None),
		("No match", None, None)
	)
	@unpack
	def test_gcode_and_subcode_for_cmd(self, cmd, expected_gcode, expected_subcode):
		from octoprint.util.comm import gcode_and_subcode_for_cmd
		actual_gcode, actual_subcode = gcode_and_subcode_for_cmd(cmd)
		self.assertEqual(expected_gcode, actual_gcode)
		self.assertEqual(expected_subcode, actual_subcode)

	@data(
		("T:23.0 B:60.0", 0, dict(T0=(23.0, None), B=(60.0, None)), 0),
		("T:23.0 B:60.0", 1, dict(T1=(23.0, None), B=(60.0, None)), 1),
		("T:23.0/220.0 B:60.0/70.0", 0, dict(T0=(23.0, 220.0), B=(60.0, 70.0)), 0),
		("ok T:23.0/220.0 T0:23.0/220.0 T1:50.2/210.0 T2:39.4/220.0 B:60.0", 0, dict(T0=(23.0, 220.0), T1=(50.2, 210.0), T2=(39.4, 220.0), B=(60.0, None)), 2),
		("ok T:50.2/210.0 T0:23.0/220.0 T1:50.2/210.0 T2:39.4/220.0 B:60.0", 1, dict(T0=(23.0, 220.0), T1=(50.2, 210.0), T2=(39.4, 220.0), B=(60.0, None)), 2),
		("ok T:-55.7/0 T0:-55.7/0 T1:150.0/210.0", 0, dict(T0=(-55.7, 0), T1=(150.0, 210.0)), 1),
		("ok T:150.0/210.0 T0:-55.7/0 T1:150.0/210.0", 1, dict(T0=(-55.7, 0), T1=(150.0, 210.0)), 1)
	)
	@unpack
	def test_process_temperature_line(self, line, current, expected_result, expected_max):
		from octoprint.util.comm import parse_temperature_line
		maxtool, result = parse_temperature_line(line, current)
		self.assertDictEqual(expected_result, result)
		self.assertEqual(expected_max, maxtool)

	@data(
		# T => T0
		(dict(T=(23.0,None)), 0, dict(T0=(23.0, None))),

		# T => T1
		(dict(T=(23.0,None)), 1, dict(T1=(23.0, None))),

		# T and Tn present => Tn wins
		(dict(T=(23.0, None), T0=(23.0, None), T1=(42.0, None)), 0, dict(T0=(23.0, None), T1=(42.0, None))),
		(dict(T=(42.0, None), T0=(23.0, None), T1=(42.0, None)), 1, dict(T0=(23.0, None), T1=(42.0, None))),
		(dict(T=(21.0, None), T0=(23.0, None), T1=(42.0, None)), 0, dict(T0=(23.0, None), T1=(42.0, None))),
		(dict(T=(41.0, None), T0=(23.0, None), T1=(42.0, None)), 1, dict(T0=(23.0, None), T1=(42.0, None))),

		# T and no T0 => Smoothieware, T = T0
		(dict(T=(23.0, None), T1=(42.0, None)), 1, dict(T0=(23.0, None), T1=(42.0, None))),

		# no T => as-is
		(dict(T0=(23.0, None), T1=(42.0, None)), 1, dict(T0=(23.0, None), T1=(42.0, None)))
	)
	@unpack
	def test_canonicalize_temperatures(self, parsed, current, expected):
		from octoprint.util.comm import canonicalize_temperatures
		result = canonicalize_temperatures(parsed, current)
		self.assertDictEqual(expected, result)

	@data(
		("KEY1:Value 1 FIRMWARE_NAME:Some Firmware With Spaces KEY2:Value 2",
		 dict(KEY1="Value 1", KEY2="Value 2", FIRMWARE_NAME="Some Firmware With Spaces"))
	)
	@unpack
	def test_parse_firmware_line(self, line, expected):
		from octoprint.util.comm import parse_firmware_line
		result = parse_firmware_line(line)
		self.assertDictEqual(expected, result)

	@data(
		("Cap:EEPROM:1", ("EEPROM", True)),
		("Cap:EEPROM:0", ("EEPROM", False)),
		("AUTOREPORT_TEMP:1", ("AUTOREPORT_TEMP", True)),
		("AUTOREPORT_TEMP:0", ("AUTOREPORT_TEMP", False)),
		("TOO:MANY:FIELDS", None),
		("Cap:", None),
		("TOOLITTLEFIELDS", None),
		("WRONG:FLAG", None),
	)
	@unpack
	def test_parse_capability_line(self, line, expected):
		from octoprint.util.comm import parse_capability_line
		result = parse_capability_line(line)
		self.assertEqual(expected, result)

	@data(
		("Resend:23", 23),
		("Resend: N23", 23),
		("Resend: N:23", 23),
		("rs 23", 23),
		("rs N23", 23),
		("rs N:23", 23),
		("rs N23 expected checksum 109", 23) # teacup, see #300
	)
	@unpack
	def test_parse_resend_line(self, line, expected):
		from octoprint.util.comm import parse_resend_line
		result = parse_resend_line(line)
		self.assertEqual(expected, result)
