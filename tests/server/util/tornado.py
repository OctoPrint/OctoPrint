# coding=utf-8
"""
Unit tests for ``octoprint.server.util.tornado``.
"""

from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2016 The OctoPrint Project - Released under terms of the AGPLv3 License"


import unittest
import mock
from ddt import ddt, data, unpack


##~~ _parse_header

@ddt
class ParseHeaderTest(unittest.TestCase):

	@data(
		("form-data; filename=test.gco", "form-data", dict(filename="test.gco")),
		("form-data; filename=\"test.gco\"", "form-data", dict(filename="test.gco")),
		("form-data; filename=test\\\\.gco", "form-data", dict(filename="test\\\\.gco")),
		("form-data; filename=\"test\\\\.gco\"", "form-data", dict(filename="test\\.gco"))
	)
	@unpack
	def test_parse_header_strip_quotes(self, value, expected_key, expected_dict):
		from octoprint.server.util.tornado import _parse_header
		actual_key, actual_dict = _parse_header(value)

		self.assertEqual(expected_key, actual_key)
		self.assertDictEqual(expected_dict, actual_dict)

	@data(
		("form-data; filename=test.gco", "form-data", dict(filename="test.gco")),
		("form-data; filename=\"test.gco\"", "form-data", dict(filename="\"test.gco\"")),
		("form-data; filename=test\\\\.gco", "form-data", dict(filename="test\\\\.gco")),
		("form-data; filename=\"test\\\\.gco\"", "form-data", dict(filename="\"test\\\\.gco\"")),
		("form-data; filename=iso-8859-1'en'test.gco", "form-data", dict(filename="iso-8859-1'en'test.gco"))
	)
	@unpack
	def test_parse_header_leave_quotes(self, value, expected_key, expected_dict):
		from octoprint.server.util.tornado import _parse_header
		actual_key, actual_dict = _parse_header(value, strip_quotes=False)

		self.assertEqual(expected_key, actual_key)
		self.assertDictEqual(expected_dict, actual_dict)


##~~ _strip_value_quotes

@ddt
class StripValueQuotesTest(unittest.TestCase):

	@data(
		("", ""),
		(None, None),
		('"test.gco"', "test.gco"),
		('"test".gco', '"test".gco'),
		("test\\\\.gco", "test\\\\.gco"),
		('"test\\\\.gco"', "test\\.gco")
	)
	@unpack
	def test_strip_value_quotes(self, value, expected):
		from octoprint.server.util.tornado import _strip_value_quotes
		actual = _strip_value_quotes(value)

		self.assertEqual(expected, actual)

##~~ _extended_header_value

@ddt
class ExtendedHeaderValueTest(unittest.TestCase):

	@data(
		(u"", u""),
		(None, None),
		(u'"quoted-string"', u"quoted-string"),
		(u'"qüöted-string"', u"qüöted-string"),
		(u"iso-8859-1'en'%A3%20rates", u"£ rates"),
		(u"UTF-8''%c2%a3%20and%20%e2%82%ac%20rates", u"£ and € rates"),
		('"quoted-string"', u"quoted-string"),
		('"qüöted-string"', u"qüöted-string"),
		("iso-8859-1'en'%A3%20rates", u"£ rates"),
		("UTF-8''%c2%a3%20and%20%e2%82%ac%20rates", u"£ and € rates")
	)
	@unpack
	def test_extended_header_value(self, value, expected):
		from octoprint.server.util.tornado import _extended_header_value
		actual = _extended_header_value(value)

		self.assertEqual(expected, actual)
