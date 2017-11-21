# coding=utf-8
from __future__ import absolute_import

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"

import unittest
import ddt
import mock

@ddt.ddt
class PlatformUtilTest(unittest.TestCase):

	@ddt.data(
		("win32", "windows"),
		("linux2", "linux"),
		("darwin", "macos"),
		("linux", "linux"),
		("linux3", "linux"),
		("freebsd", "freebsd"),
		("freebsd2342", "freebsd"),
		("os2", "unmapped"),
		("sunos5", "unmapped")
	)
	@ddt.unpack
	def test_get_os(self, sys_platform, expected):
		with mock.patch("sys.platform", sys_platform):
			from octoprint.util.platform import get_os
			actual = get_os()
			self.assertEqual(actual, expected)
