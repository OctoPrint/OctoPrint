__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

import unittest

import ddt
import pytest

import octoprint.util.commandline


@ddt.ddt
class CommandlineTest(unittest.TestCase):
    @ddt.data(
        (
            "Some text with some \x1b[31mred words\x1b[39m in it",
            "Some text with some red words in it",
        ),
        (
            "We \x1b[?25lhide the cursor here and then \x1b[?25hshow it again here",
            "We hide the cursor here and then show it again here",
        ),
        (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 6.5/6.5 MB 1.1 MB/s eta 0:00:00",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 6.5/6.5 MB 1.1 MB/s eta 0:00:00",
        ),
    )
    @ddt.unpack
    def test_clean_ansi(self, input, expected):
        actual = octoprint.util.commandline.clean_ansi(input)
        self.assertEqual(expected, actual)

    def test_clean_ansi_deprecated(self):
        with pytest.deprecated_call():
            actual = octoprint.util.commandline.clean_ansi(
                b"Some bytes with some \x1b[31mred words\x1b[39m in it"
            )
            self.assertEqual(b"Some bytes with some red words in it", actual)
