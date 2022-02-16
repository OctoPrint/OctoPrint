__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

import unittest

import ddt

import octoprint.settings


@ddt.ddt
class TestHelpers(unittest.TestCase):
    @ddt.data(
        (True, True),
        ("true", True),
        ("True", True),
        ("tRuE", True),
        ("yes", True),
        ("YES", True),
        ("y", True),
        ("Y", True),
        ("1", True),
        (1, True),
        (False, False),
        ("Truuuuuuuuue", False),
        ("Nope", False),
        (None, False),
    )
    @ddt.unpack
    def test_valid_boolean_trues(self, value, expected):
        self.assertEqual(expected, value in octoprint.settings.valid_boolean_trues)


def _key(*path):
    return octoprint.settings._CHAINMAP_SEP.join(path)


@ddt.ddt
class ChainmapTest(unittest.TestCase):
    @ddt.data(
        (
            {"a": 1},
            {_key("a"): 1},
        ),
        ({"a": {"b": "b"}}, {_key("a", "b"): "b"}),
        (
            {"a": {"b": "b", "c": "c", "d": {"e": "e"}}},
            {_key("a", "b"): "b", _key("a", "c"): "c", _key("a", "d", "e"): "e"},
        ),
    )
    @ddt.unpack
    def test_flatten(self, value, expected):
        self.assertEqual(
            expected, octoprint.settings.HierarchicalChainMap._flatten(value)
        )

    @ddt.data(
        (
            {_key("a"): 1},
            {"a": 1},
        ),
        (
            {_key("a", "b"): "b"},
            {"a": {"b": "b"}},
        ),
        (
            {_key("a", "b"): "b", _key("a", "c"): "c", _key("a", "d", "e"): "e"},
            {"a": {"b": "b", "c": "c", "d": {"e": "e"}}},
        ),
        (
            {_key("a"): None, _key("a", "b"): "b"},
            {"a": {"b": "b"}},
        ),
    )
    @ddt.unpack
    def test_unflatten(self, value, expected):
        self.assertEqual(
            expected, octoprint.settings.HierarchicalChainMap._unflatten(value)
        )
