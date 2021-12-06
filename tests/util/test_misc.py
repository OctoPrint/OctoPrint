__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"


import unittest

import ddt
from frozendict import frozendict

import octoprint.util


@ddt.ddt
class MiscTestCase(unittest.TestCase):
    def test_get_class(self):
        octoprint.util.get_class("octoprint.access.users.FilebasedUserManager")

    def test_get_class_wrongmodule(self):
        try:
            octoprint.util.get_class("octoprint2.users.FilebasedUserManager")
            self.fail("This should have thrown an ImportError")
        except ImportError:
            # success
            pass

    def test_get_class_wrongclass(self):
        try:
            octoprint.util.get_class(
                "octoprint.access.users.FilebasedUserManagerBzzztWrong"
            )
            self.fail("This should have thrown an ImportError")
        except ImportError:
            # success
            pass

    @ddt.data(
        (
            "http://example.com",
            {"source": "source"},
            "http://example.com?utm_source=source",
        ),
        (
            "http://example.com?q=1",
            {"source": "source"},
            "http://example.com?q=1&utm_source=source",
        ),
        (
            "http://example.com",
            {"source": "source", "medium": "medium"},
            "http://example.com?utm_source=source&utm_medium=medium",
        ),
        (
            "http://example.com",
            {"source": "source", "medium": "medium", "content": "content with spaces"},
            "http://example.com?utm_source=source&utm_medium=medium&utm_content=content+with+spaces",
        ),
        # no handling
        ("http://example.com", {}, "http://example.com"),
    )
    @ddt.unpack
    def test_utmify(self, link, kwargs, expected):
        actual = octoprint.util.utmify(link, **kwargs)
        self.assertEqual(actual, expected)

    @ddt.data(
        (frozendict(a=1, b=2, c=3), {"a": 1, "b": 2, "c": 3}),
        (
            frozendict(a=1, b=2, c=frozendict(c1=1, c2=2)),
            {"a": 1, "b": 2, "c": {"c1": 1, "c2": 2}},
        ),
        ({"a": 1, "b": 2, "c": 3}, {"a": 1, "b": 2, "c": 3}),
        (
            {"a": 1, "b": 2, "c": frozendict(c1=1, c2=2)},
            {"a": 1, "b": 2, "c": {"c1": 1, "c2": 2}},
        ),
        (
            {
                "a": 1,
                "b": 2,
                "c": {"c1": 1, "c2": 2, "c3": frozendict(c11=11, c12=12)},
            },
            {"a": 1, "b": 2, "c": {"c1": 1, "c2": 2, "c3": {"c11": 11, "c12": 12}}},
        ),
    )
    @ddt.unpack
    def test_unfreeze_frozendict(self, input, expected):
        result = octoprint.util.thaw_frozendict(input)
        self.assertIsInstance(result, dict)
        self.assertDictEqual(result, expected)

    @ddt.data(None, "invalid", 3, [1, 2], (3, 4))
    def test_unfreeze_frozendict_invalid(self, input):
        try:
            octoprint.util.thaw_frozendict(input)
            self.fail("expected ValueError")
        except ValueError:
            # expected
            pass
