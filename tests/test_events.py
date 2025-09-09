__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

from unittest import mock

import pytest

import octoprint.events


@pytest.mark.parametrize(
    "value, expected",
    (
        ("plugin_example_event", "PLUGIN_EXAMPLE_EVENT"),
        ("plugin_Example_event", "PLUGIN_EXAMPLE_EVENT"),
        ("plugin_ExAmple_Event", "PLUGIN_EX_AMPLE_EVENT"),
        ("plugin_exAmple_EvEnt", "PLUGIN_EX_AMPLE_EV_ENT"),
    ),
)
def test_to_identifier(value, expected):
    actual = octoprint.events.Events._to_identifier(value)
    assert actual == expected


@pytest.mark.parametrize(
    "params, shell, expected",
    (
        ({"a": "b"}, False, {"a": "b"}),
        ({"a": "b"}, True, {"a": "b"}),
        (
            {"a": "test.gcode;rm -rf /;#.gcode"},
            False,
            {"a": "test.gcode;rm -rf /;#.gcode"},
        ),
        (
            {"a": "test.gcode;rm -rf /;#.gcode"},
            True,
            {"a": "'test.gcode;rm -rf /;#.gcode'"},
        ),
    ),
)
def test_escape_system_commands(params, shell, expected):
    printer = mock.Mock()
    sub = octoprint.events.SystemEventSubscription(printer, "test123", shell=shell)

    actual = sub._escape_params(params)

    assert actual == expected


@pytest.fixture
def mocked_printer():
    printer = mock.Mock()
    printer.get_current_data.return_value = {}
    return printer


@pytest.mark.parametrize(
    "param, shell, expected_call",
    (
        ("a", True, "a"),
        ("a", False, "a"),
        ("a;b", True, "'a;b'"),
        ("a;b", False, "a;b"),
        ("test.gcode;rm -rf /;#.gcode", True, "'test.gcode;rm -rf /;#.gcode'"),
        ("test.gcode;rm -rf /;#.gcode", False, "test.gcode;rm -rf /;#.gcode"),
    ),
)
def test_handle_system_commands(mocked_printer, param, shell, expected_call):
    sub = octoprint.events.SystemEventSubscription(
        mocked_printer, "test123 {a}", shell=shell
    )

    with mock.patch("subprocess.check_call") as mcc:
        sub.handle("Test", {"a": param})

        mcc.assert_called_once_with(f"test123 {expected_call}", shell=shell, cwd=None)
