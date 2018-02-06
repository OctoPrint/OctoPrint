# coding=utf-8
from __future__ import absolute_import, division, print_function

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

import unittest
import ddt

import octoprint.settings

@ddt.ddt
class TestHelpers(unittest.TestCase):

	@ddt.data(
		(True, True),
		("true", True),
		("True", True),
		("tRuE", True),
		("yes", True),
		("YES", True),
		("y", True),
		("Y", True),
		("1", True),
		(1, True),

		(False, False),
		("Truuuuuuuuue", False),
		("Nope", False),
		(None, False)
	)
	@ddt.unpack
	def test_valid_boolean_trues(self, value, expected):
		self.assertEqual(expected, value in octoprint.settings.valid_boolean_trues)
