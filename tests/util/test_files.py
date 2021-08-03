# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2021 The OctoPrint Project - Released under terms of the AGPLv3 License"

import unittest

import pytest
from ddt import data, ddt, unpack

from octoprint.util.files import sanitize_filename

try:
    import pathvalidate  # noqa: F401

    HAS_PATHVALIDATE = True
except ImportError:
    HAS_PATHVALIDATE = False

pathvalidate_unavailable_only = pytest.mark.skipif(
    HAS_PATHVALIDATE, reason="pathvalidate available"
)
pathvalidate_available_only = pytest.mark.skipif(
    not HAS_PATHVALIDATE, reason="pathvalidate unavailable"
)


@ddt
class FilesUtilTest(unittest.TestCase):
    @data(
        ("some_file.gcode", "some_file.gcode"),
        ("NUL.gcode", "NUL_.gcode"),
        ("LPT1", "LPT1_"),
        (".test.gcode", "test.gcode"),
        ("..test.gcode", "test.gcode"),
    )
    @unpack
    def test_sanitize_filename(self, filename, expected):
        actual = sanitize_filename(filename)
        self.assertEqual(actual, expected)

    @data("file/with/slash.gcode", "file\\with\\backslash.gcode")
    def test_sanitize_filename_invalid(self, filename):
        try:
            sanitize_filename(filename)
            self.fail("expected ValueError")
        except ValueError as ex:
            self.assertEqual(str(ex), "name must not contain / or \\")

    @pathvalidate_unavailable_only
    @data(
        ("file with space.gcode", "file_with_space.gcode"),
        ("Wölfe 🐺.gcode", "Wolfe_wolf.gcode"),
    )
    @unpack
    def test_sanitize_filename_pvu(self, filename, expected):
        actual = sanitize_filename(filename)
        self.assertEqual(actual, expected)

    @pathvalidate_available_only
    @data(
        ("file with space.gcode", "file with space.gcode"),
        ("Wölfe 🐺.gcode", "Wölfe 🐺.gcode"),
    )
    @unpack
    def test_sanitize_filename_pva(self, filename, expected):
        actual = sanitize_filename(filename)
        self.assertEqual(actual, expected)
