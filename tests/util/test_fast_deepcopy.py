__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2021 The OctoPrint Project - Released under terms of the AGPLv3 License"

import unittest

import octoprint.util


class FastDeepcopyTest(unittest.TestCase):
    def test_clean(self):
        data = {"a": 1, "b": 2, "c": 3}
        self.assertEqual(data, octoprint.util.fast_deepcopy(data))

    def test_function(self):
        data = {"a": 1, "b": 2, "c": 3, "f": lambda x: x + 1}
        self.assertEqual(data, octoprint.util.fast_deepcopy(data))
