# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2019 The OctoPrint Project - Released under terms of the AGPLv3 License"

import unittest

from past.builtins import unicode

import octoprint.util


class StringHelperTest(unittest.TestCase):
    def test_to_unicode_unicode(self):
        result = octoprint.util.to_unicode("test")
        self.assertEqual(result, "test")
        self.assertIsInstance(result, unicode)

    def test_to_unicode_bytes(self):
        result = octoprint.util.to_unicode(b"test")
        self.assertEqual(result, "test")
        self.assertIsInstance(result, unicode)

    def test_to_unicode_bytes_utf8(self):
        data = "äöüß"
        result = octoprint.util.to_unicode(data.encode("utf-8"), encoding="utf-8")
        self.assertEqual(result, data)
        self.assertIsInstance(result, unicode)

    def test_to_unicode_bytes_utf8_vs_ascii(self):
        self.assertRaises(
            UnicodeDecodeError,
            octoprint.util.to_unicode,
            "äöüß".encode("utf-8"),
            encoding="ascii",
        )

    def test_to_unicode_bytes_utf8_vs_ascii_replace(self):
        data = "äöüß"
        result = octoprint.util.to_unicode(
            data.encode("utf-8"), encoding="ascii", errors="replace"
        )
        self.assertEqual(result, data.encode("utf-8").decode("ascii", errors="replace"))
        self.assertIsInstance(result, unicode)

    def test_to_bytes_bytes(self):
        result = octoprint.util.to_bytes(b"test")
        self.assertEqual(result, b"test")
        self.assertIsInstance(result, bytes)

    def test_to_bytes_unicode(self):
        result = octoprint.util.to_bytes("test")
        self.assertEqual(result, b"test")
        self.assertIsInstance(result, bytes)

    def test_to_bytes_unicode_utf8(self):
        data = "äöüß"
        result = octoprint.util.to_bytes(data, encoding="utf-8")
        self.assertEqual(result, data.encode("utf-8"))
        self.assertIsInstance(result, bytes)

    def test_to_bytes_unicode_utf8_vs_ascii(self):
        self.assertRaises(
            UnicodeEncodeError, octoprint.util.to_bytes, "äöüß", encoding="ascii"
        )

    def test_to_bytes_unicode_utf8_vs_ascii_replace(self):
        data = "äöüß"
        result = octoprint.util.to_bytes(data, encoding="ascii", errors="replace")
        self.assertEqual(result, data.encode("ascii", errors="replace"))
        self.assertIsInstance(result, bytes)

    def test_to_str_still_works(self):
        result = octoprint.util.to_str("test")
        self.assertEqual(result, b"test")
        self.assertIsInstance(result, bytes)
