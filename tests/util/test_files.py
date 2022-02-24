__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2021 The OctoPrint Project - Released under terms of the AGPLv3 License"

import unittest

from ddt import data, ddt, unpack

from octoprint.util.files import sanitize_filename


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
