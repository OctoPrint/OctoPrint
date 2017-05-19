# coding=utf-8
"""
Unit tests for ``octoprint.server.util.flask``.
"""

from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2016 The OctoPrint Project - Released under terms of the AGPLv3 License"


import unittest
import ddt

from octoprint.server.util.webassets import replace_url

@ddt.ddt
class UrlReplaceTest(unittest.TestCase):

	@ddt.data(
		("mytest/some/path/", "mytest/another/longer/path/", "http://example.com/foo.html", "http://example.com/foo.html"),
		("mytest/some/path/", "mytest/another/longer/path/", "/path/foo.html", "/path/foo.html"),
		("http://example.com/mytest/some/path/", "mytest/another/longer/path/", "../foo.html", "http://example.com/mytest/some/foo.html"),
		("mytest/some/path/", "mytest/another/longer/path/", "../foo.html", "../../../some/foo.html")
	)
	@ddt.unpack
	def test_replace_url(self, source_url, output_url, url, expected):
		actual = replace_url(source_url, output_url, url)
		self.assertEqual(actual, expected)
