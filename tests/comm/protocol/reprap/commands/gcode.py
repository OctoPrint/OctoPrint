# coding=utf-8
from __future__ import absolute_import, unicode_literals, print_function, \
	division

"""
Unit tests for ``octoprint.comm.protocol.reprap.commands.gcode.``.
"""

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

import unittest
import ddt

from octoprint.comm.protocol.reprap.commands.gcode import GcodeCommand

@ddt.ddt
class GcodeCommandTest(unittest.TestCase):

	@ddt.data(
		("M105", dict(code="M105")),
		("M30 some_file.gco", dict(code="M30", param="some_file.gco")),
		("G28 X0 Y0", dict(code="G28", x=0, y=0)),
		("G28X0Y0", dict(code="G28", x=0, y=0)),
		("M104 S220.0 T1", dict(code="M104", s=220.0, t=1)),
		("M123.456 my parameter is long", dict(code="M123", subcode=456, param="my parameter is long")),
		("M123 Hello there", dict(code="M123", param="Hello there")),
		("M123 C P1 X0 Y2.3 Z-23.42 E+5", dict(code="M123", c=True, p=1, x=0, y=2.3, z=-23.42, e=5)),
		("M123 P1 And a parameter too", dict(code="M123", p=1, param="And a parameter too")),
		("T123", dict(code="T", tool=123)),
		("F200", dict(code="F", feedrate=200))
	)
	@ddt.unpack
	def test_from_line(self, line, expected_args):
		actual = GcodeCommand.from_line(line)
		for arg, value in expected_args.items():
			self.assertEqual(value, getattr(actual, arg))

	@ddt.data(
		("G28 X0 Y0", "GcodeCommand(u'G28',x=0,y=0,original=u'G28 X0 Y0',type=None,tags=set([]))"),
		("M30 some_file.gco", "GcodeCommand(u'M30',param=u'some_file.gco',original=u'M30 some_file.gco',type=None,tags=set([]))"),
		("T1", "GcodeCommand(u'T',tool=1,original=u'T1',type=None,tags=set([]))"),
		("F6000", "GcodeCommand(u'F',feedrate=6000,original=u'F6000',type=None,tags=set([]))"),
		("M27 C", "GcodeCommand(u'M27',c=True,original=u'M27 C',type=None,tags=set([]))"),
	)
	@ddt.unpack
	def test_repr(self, line, expected):
		gcode = GcodeCommand.from_line(line)
		self.assertEqual(expected, repr(gcode))
