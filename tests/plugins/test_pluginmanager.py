# coding=utf-8
"""
Unit tests for bundled plugin "PluginManager".
"""

from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"

import unittest
import mock
import ddt

from octoprint.plugins.pluginmanager import PluginManagerPlugin

@ddt.ddt
class PluginManagerPluginTests(unittest.TestCase):

	@ddt.data(
		("linux", "linux2", [], True),
		("linux", "linux2", ["linux", "freebsd"], True),
		("windows", "win32", ["linux", "freebsd"], False),
		("linux", "linux2", ["!windows"], True),
		("windows", "win32", ["!windows"], False),
		("unmapped", "os2", [], True),
		("unmapped", "os2", ["linux", "freebsd"], False),
		("unmapped", "os2", ["!os2"], False),
		("unmapped", "sunos5", ["linux", "freebsd", "sunos"], True),
		("unmapped", "sunos5", ["!sunos", "!os2"], False),

		# both black and white listing at the same time usually doesn't
		# make a whole lot of sense, but let's test it anyhow
		("linux", "linux2", ["!windows", "linux", "freebsd"], True),
		("linux", "linux2", ["!windows", "freebsd"], False),
		("windows", "win32", ["!windows", "linux", "freebsd"], False),
		("unmapped", "sunos5", ["!windows", "linux", "freebsd"], False)
	)
	@ddt.unpack
	def test_is_os_compatible(self, current_os, sys_platform, entries, expected):
		with mock.patch("sys.platform", sys_platform):
			actual = PluginManagerPlugin._is_os_compatible(current_os, entries)
			self.assertEqual(actual, expected)
