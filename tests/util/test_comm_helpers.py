# coding=utf-8
from __future__ import absolute_import

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
		self.assertEquals(expected, comm.strip_comment(input))

	@data(
		("M117 Test", None, None, "M117 Test"),
		("", None, None, None),
		("  \t \r    \n", None, None, None),
		("M117 Test", dict(), 0, "M117 Test")
	)
	@unpack
	def test_process_gcode_line(self, input, offsets, current_tool, expected):
		from octoprint.util import comm
		self.assertEquals(expected, comm.process_gcode_line(input, offsets=offsets, current_tool=current_tool))

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
			self.assertEquals(input, actual)
		else:
			import re
			match = re.search("S(\d+(\.\d+)?)", actual)
			if not match:
				self.fail("No temperature found")
			temperature = float(match.group(1))
			self.assertEquals(expected, temperature)
			self.assertEquals(input[:match.start(1)], actual[:match.start(1)])
			self.assertEquals(input[match.end(1):], actual[match.end(1):])

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
		self.assertEquals("(pause1)|(pause2)", trigger_matchers["enable"].pattern)

		self.assertIn("disable", trigger_matchers)
		self.assertEquals("(resume)", trigger_matchers["disable"].pattern)

		self.assertIn("toggle", trigger_matchers)
		self.assertEquals("(toggle)", trigger_matchers["toggle"].pattern)

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

		self.assertEquals(2, len(controls))

		# temp_regex is used twice, so we should have two templates for it
		self.assertIn(temp_key, controls)
		temp = controls[temp_key]

		self.assertIsNotNone(temp["matcher"])
		self.assertEquals(temp_regex, temp["matcher"].pattern)
		self.assertEquals(temp_regex, temp["pattern"])

		self.assertEquals(2, len(temp["templates"]))
		self.assertIn(temp_template_key, temp["templates"])
		self.assertEquals(temp_template, temp["templates"][temp_template_key])
		self.assertIn(temp2_template_key, temp["templates"])
		self.assertEquals(temp2_template, temp["templates"][temp2_template_key])

		# x_regex is used once, so we should have only one template for it
		self.assertIn(x_key, controls)
		x = controls[x_key]

		self.assertIsNotNone(x["matcher"])
		self.assertEquals(x_regex, x["matcher"].pattern)
		self.assertEquals(x_regex, x["pattern"])

		self.assertEquals(1, len(x["templates"]))
		self.assertIn(x_template_key, x["templates"])
		self.assertEquals(x_template, x["templates"][x_template_key])

		self.assertEquals("(?P<group{temp_key}>{temp_regex})|(?P<group{x_key}>{x_regex})".format(**locals()), matcher.pattern)
