__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2021 The OctoPrint Project - Released under terms of the AGPLv3 License"

import os
import re
import unittest

from ddt import data, ddt, unpack

from octoprint.util.files import (
    sanitize_filename,
    search_through_file,
    search_through_file_python,
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
