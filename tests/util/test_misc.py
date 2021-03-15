# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"


import unittest

import ddt

try:
    from immutabledict import immutabledict
except ImportError:
    # Python 2
    from frozendict import frozendict as immutabledict

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
        (immutabledict(a=1, b=2, c=3), {"a": 1, "b": 2, "c": 3}),
        (
            immutabledict(a=1, b=2, c=immutabledict(c1=1, c2=2)),
            {"a": 1, "b": 2, "c": {"c1": 1, "c2": 2}},
        ),
        ({"a": 1, "b": 2, "c": 3}, {"a": 1, "b": 2, "c": 3}),
        (
            {"a": 1, "b": 2, "c": immutabledict(c1=1, c2=2)},
            {"a": 1, "b": 2, "c": {"c1": 1, "c2": 2}},
        ),
        (
            {
                "a": 1,
                "b": 2,
                "c": {"c1": 1, "c2": 2, "c3": immutabledict(c11=11, c12=12)},
            },
            {"a": 1, "b": 2, "c": {"c1": 1, "c2": 2, "c3": {"c11": 11, "c12": 12}}},
        ),
    )
    @ddt.unpack
    def test_unfreeze_immutabledict(self, input, expected):
        result = octoprint.util.thaw_immutabledict(input)
        self.assertIsInstance(result, dict)
        self.assertDictEqual(result, expected)

    @ddt.data(None, "invalid", 3, [1, 2], (3, 4))
    def test_unfreeze_immutabledict_invalid(self, input):
        try:
            octoprint.util.thaw_immutabledict(input)
            self.fail("expected ValueError")
        except ValueError:
            # expected
            pass
