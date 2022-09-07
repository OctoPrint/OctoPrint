__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2021 The OctoPrint Project - Released under terms of the AGPLv3 License"

import datetime
import os
import re
import unittest

import pytest
from ddt import data, ddt, unpack

from octoprint.util.files import (
    m20_timestamp_to_unix_timestamp,
    sanitize_filename,
    search_through_file,
    search_through_file_python,
    unix_timestamp_to_m20_timestamp,
)


@ddt
class FilesUtilTest(unittest.TestCase):
    @data(
        ("some_file.gcode", "some_file.gcode", False),
        ("NUL.gcode", "NUL_.gcode", False),
        ("LPT1", "LPT1_", False),
        (".test.gcode", "test.gcode", False),
        ("..test.gcode", "test.gcode", False),
        ("file with space.gcode", "file with space.gcode", False),
        ("Wölfe 🐺.gcode", "Wölfe 🐺.gcode", False),
        ("file with space.gcode", "file_with_space.gcode", True),
        ("Wölfe 🐺.gcode", "Wolfe_wolf.gcode", True),
    )
    @unpack
    def test_sanitize_filename(self, filename, expected, really_universal):
        actual = sanitize_filename(filename, really_universal=really_universal)
        self.assertEqual(actual, expected)

    @data("file/with/slash.gcode", "file\\with\\backslash.gcode")
    def test_sanitize_filename_invalid(self, filename):
        try:
            sanitize_filename(filename)
            self.fail("expected ValueError")
        except ValueError as ex:
            self.assertEqual(str(ex), "name must not contain / or \\")

    @data(
        ("umlaut", False, True),
        ("BOM", False, True),
        (r"^[^#]*BOM", True, False),
    )
    @unpack
    def test_search_through_file(self, term, regex, expected):
        path = os.path.join(
            os.path.abspath(os.path.dirname(__file__)), "_files", "utf8_without_bom.txt"
        )
        actual = search_through_file(path, term, regex=regex)
        self.assertEqual(actual, expected)

    @data(
        ("umlaut", True),
        ("BOM", True),
        (r"^[^#]*BOM", False),
    )
    @unpack
    def test_search_through_file_python(self, term, expected):
        compiled = re.compile(term)
        path = os.path.join(
            os.path.abspath(os.path.dirname(__file__)), "_files", "utf8_without_bom.txt"
        )
        actual = search_through_file_python(path, term, compiled)
        self.assertEqual(actual, expected)


# based on https://github.com/nathanhi/pyfatfs/blob/master/tests/test_DosDateTime.py
m20_timestamp_tests = [
    ("0x210000", datetime.datetime(1980, 1, 1).timestamp()),
    ("0x21bf7d", datetime.datetime(1980, 1, 1, 23, 59, 58).timestamp()),
    ("0x549088aa", datetime.datetime(2022, 4, 16, 17, 5, 20).timestamp()),
    ("0x28210800", datetime.datetime(2000, 1, 1, 1, 0).timestamp()),
]

# 32bit time_t systems will fail with:
# "OverflowError: timestamp out of range for platform time_t"
# for this date.
try:
    m20_timestamp_tests.append(
        ("0xff9f0000", datetime.datetime(2107, 12, 31).timestamp())
    )
except OverflowError:
    pass


@pytest.mark.parametrize("val,expected", m20_timestamp_tests)
def test_m20_timestamp_to_unix_timestamp(val, expected):
    assert m20_timestamp_to_unix_timestamp(val) == expected


@pytest.mark.parametrize("expected,val", m20_timestamp_tests)
def test_unix_timestamp_to_m20_timestamp(expected, val):
    assert unix_timestamp_to_m20_timestamp(val) == expected
