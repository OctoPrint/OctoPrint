__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2021 The OctoPrint Project - Released under terms of the AGPLv3 License"

import unittest

import octoprint.util


class FastDeepcopyTest(unittest.TestCase):
    def test_clean(self):
        data = {"a": 1, "b": [2, 3], "c": {"d": 4}}
        result = octoprint.util.fast_deepcopy(data)
        self.assertEqual(data, result)
        self.assertIsNot(result, data)
        self.assertIsNot(result["b"], data["b"])
        self.assertIsNot(result["c"], data["c"])

    def test_function(self):
        data = {"a": 1, "b": [2, 3], "f": lambda x: x + 1}
        result = octoprint.util.fast_deepcopy(data)
        self.assertEqual(data, result)
        self.assertIsNot(result, data)
        self.assertIsNot(result["b"], data["b"])
