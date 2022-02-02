__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2021 The OctoPrint Project - Released under terms of the AGPLv3 License"

import unittest

import ddt
import pkg_resources


@ddt.ddt
class VersionUtilTest(unittest.TestCase):
    @ddt.data(
        ("1.6.0.dev303+g328853170.dirty", None, "1.6.0.dev303+g328853170.dirty"),
        ("1.6.0.dev303+g328853170.dirty", 0, "1.6.0"),
        ("1.6.0.dev303+g328853170.dirty", 1, "1.6"),
        ("1.6.0", 0, "1.6.0"),
        ("1.6.0", 23, "1.6.0"),
        ("1.6.0", -1, ValueError),
    )
    @ddt.unpack
    def test_get_comparable_version(self, version, cut, expected):
        from octoprint.util.version import get_comparable_version

        try:
            actual = get_comparable_version(version, cut=cut)
        except Exception as exc:
            if isinstance(expected, type) and isinstance(exc, expected):
                pass
            else:
                raise
        else:
            self.assertEqual(actual, pkg_resources.parse_version(expected))

    def test_get_comparable_version_base(self):
        from octoprint.util.version import get_comparable_version

        actual = get_comparable_version("1.6.0.dev303+g328853170.dirty", base=True)
        self.assertEqual(actual, pkg_resources.parse_version("1.6.0"))

    @ddt.data(
        ("1.6.0", "1.6.0"),
        ("v1.6.0", "1.6.0"),
        ("V1.6.0", "1.6.0"),
        ("1.6.0+", "1.6.0"),
        ("\t1.6.0  \r\n", "1.6.0"),
    )
    @ddt.unpack
    def test_normalize_version(self, version, expected):
        from octoprint.util.version import normalize_version

        actual = normalize_version(version)

        self.assertEqual(actual, expected)
