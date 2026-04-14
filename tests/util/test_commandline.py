__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

import pytest

import octoprint.util.commandline


@pytest.mark.parametrize(
    "input, expected",
    [
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
    ],
)
def test_clean_ansi(input, expected):
    actual = octoprint.util.commandline.clean_ansi(input)
    assert expected == actual
