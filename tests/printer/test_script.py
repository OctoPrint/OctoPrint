__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2021 The OctoPrint Project - Released under terms of the AGPLv3 License"

import unittest
from unittest.mock import ANY, MagicMock, call, patch

from octoprint.printer.standard import Printer


class ScriptsTestCase(unittest.TestCase):
    def setUp(self):
        # mock comm
        self.comm = MagicMock()

        # mock event manager
        self.event_manager = MagicMock()

        self.event_manager_patcher = patch("octoprint.printer.standard.eventManager")
        self.event_manager_getter = self.event_manager_patcher.start()
        self.event_manager_getter.return_value = self.event_manager

        # mock plugin manager
        self.plugin_manager = MagicMock()
        self.plugin_manager.get_hooks.return_value = {}

        self.plugin_manager_patcher = patch("octoprint.printer.standard.plugin_manager")
        self.plugin_manager_getter = self.plugin_manager_patcher.start()
        self.plugin_manager_getter.return_value = self.plugin_manager

        # mock settings
        self.settings = MagicMock()
        self.settings.getInt.return_value = 1
        self.settings.getBoolean.return_value = False

        self.settings_patcher = patch("octoprint.printer.standard.settings")
        self.settings_getter = self.settings_patcher.start()
        self.settings_getter.return_value = self.settings

        self.printer = Printer(MagicMock(), MagicMock(), MagicMock())
        self.printer._comm = self.comm

    def tearDown(self):
        self.settings_patcher.stop()
        self.plugin_manager_patcher.stop()
        self.event_manager_patcher.stop()

    def test_event_name(self):
        self.printer.script("testEvent")

        self.event_manager.fire.assert_any_call("GcodeScriptTestEventRunning", ANY)

    def test_event_order(self):
        self.printer.script("EventOrder")

        expected_order = [
            call("GcodeScriptEventOrderRunning", ANY),
            call("GcodeScriptEventOrderFinished", ANY),
        ]

        self.event_manager.fire.assert_has_calls(expected_order)

    def test_payload_handling(self):
        expected_paylod = {"payloadKey": "payloadValue"}
        context = {"event": expected_paylod}

        self.printer.script("GetPayload", context)

        self.event_manager.fire.assert_called_with(ANY, expected_paylod)

        self.printer.script("WrongPayload", [])

        self.event_manager.fire.assert_called_with(ANY, None)

        self.printer.script("WrongContext", {"noEvent": {}})

        self.event_manager.fire.assert_called_with(ANY, None)
