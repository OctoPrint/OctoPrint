# coding=utf-8
from __future__ import absolute_import

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"


import unittest
import ddt

import octoprint.util

@ddt.ddt
class MiscTestCase(unittest.TestCase):

	def test_get_class(self):
		octoprint.util.get_class("octoprint.users.FilebasedUserManager")

	def test_get_class_wrongmodule(self):
		try:
			octoprint.util.get_class("octoprint2.users.FilebasedUserManager")
			self.fail("This should have thrown an ImportError")
		except ImportError:
			# success
			pass

	def test_get_class_wrongclass(self):
		try:
			octoprint.util.get_class("octoprint.users.FilebasedUserManagerBzzztWrong")
			self.fail("This should have thrown an ImportError")
		except ImportError:
			# success
			pass

	@ddt.data(
		("http://example.com", dict(source="source"), "http://example.com?utm_source=source"),
		("http://example.com?q=1", dict(source="source"), "http://example.com?q=1&utm_source=source"),
		("http://example.com", dict(source="source", medium="medium"), "http://example.com?utm_source=source&utm_medium=medium"),
		("http://example.com", dict(source="source", medium="medium", content="content with spaces"), "http://example.com?utm_source=source&utm_medium=medium&utm_content=content+with+spaces"),

		# no handling
		("http://example.com", dict(), "http://example.com"),
	)
	@ddt.unpack
	def test_utmify(self, link, kwargs, expected):
		actual = octoprint.util.utmify(link, **kwargs)
		self.assertEqual(actual, expected)
