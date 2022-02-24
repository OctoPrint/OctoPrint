__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

import unittest

import ddt

import octoprint.events


@ddt.ddt
class TestEvents(unittest.TestCase):
    @ddt.data(
        ("plugin_example_event", "PLUGIN_EXAMPLE_EVENT"),
        ("plugin_Example_event", "PLUGIN_EXAMPLE_EVENT"),
        ("plugin_ExAmple_Event", "PLUGIN_EX_AMPLE_EVENT"),
        ("plugin_exAmple_EvEnt", "PLUGIN_EX_AMPLE_EV_ENT"),
    )
    @ddt.unpack
    def test_to_identifier(self, value, expected):
        actual = octoprint.events.Events._to_identifier(value)
        self.assertEqual(actual, expected)
