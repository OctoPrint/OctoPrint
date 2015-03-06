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