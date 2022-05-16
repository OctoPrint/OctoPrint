__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"


import unittest

import ddt

import octoprint.util


@ddt.ddt
class TestCaseInsensitiveSet(unittest.TestCase):
    def setUp(self):
        self.set = octoprint.util.CaseInsensitiveSet("A", "FoO", True, 23)

    @ddt.data("A", "a", "foo", True, 23)
    def test_contained(self, value):
        self.assertIn(value, self.set)

    @ddt.data("b", "fnord", False, 42)
    def test_not_contained(self, value):
        self.assertNotIn(value, self.set)
