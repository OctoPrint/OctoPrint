import sys
from unittest import mock

import pytest

from octoprint.plugins.serial_connector.serial_comm import (
    STANDARD_BAUDRATES,
    baudrateList,
    serialList,
)


@pytest.mark.parametrize(
    "ports, additional, hooks, blocklisted, connector, params, expected",
    [
        pytest.param(
            ["ttyUSB0"], [], [], [], "other", {}, ["/dev/ttyUSB0"], id="most basic case"
        ),
        pytest.param(
            ["ttyUSB0", "ttyUSB1", "ttyUSB2"],
            [],
            [],
            [],
            "serial",
            {"port": "/dev/ttyUSB2"},
            ["/dev/ttyUSB2", "/dev/ttyUSB0", "/dev/ttyUSB1"],
            id="sorting changed by preferred connection",
        ),
        pytest.param(
            ["ttyUSB0", "ttyUSB1", "ttyUSB2"],
            [],
            [],
            [],
            "serial",
            {"port": "/dev/ttyUSB4"},
            ["/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyUSB2"],
            id="preferred connection not in found candidates",
        ),
        pytest.param(
            ["ttyUSB0", "ttyUSB1", "ttyUSB2"],
            [],
            [],
            [],
            "serial",
            {},
            ["/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyUSB2"],
            id="preferred connection but no preferred port",
        ),
        pytest.param(
            ["ttyUSB0"],
            ["/foo/bar"],
            [],
            [],
            "other",
            {},
            ["/dev/ttyUSB0", "/foo/bar"],
            id="additional port",
        ),
        pytest.param(
            ["ttyUSB0"],
            [],
            ["VIRTUAL1", "VIRTUAL2"],
            [],
            "other",
            {},
            ["/dev/ttyUSB0", "VIRTUAL1", "VIRTUAL2"],
            id="ports from a hook",
        ),
        pytest.param(
            ["ttyUSB0", "ttyS0", "ttyS1"],
            [],
            [],
            ["/dev/ttyS*"],
            "other",
            {},
            ["/dev/ttyUSB0"],
            id="blocklisted ports",
        ),
        pytest.param(
            ["ttyUSB0"],
            ["/foo/bar"],
            [],
            ["/f*"],
            "other",
            {},
            ["/dev/ttyUSB0"],
            id="blocklist used *after* additional ports get added",
        ),
        pytest.param(
            ["ttyUSB0"],
            [],
            ["/foo/bar"],
            ["/f*"],
            "other",
            {},
            ["/dev/ttyUSB0"],
            id="blocklist used *after* hook results get added",
        ),
    ],
)
def test_serial_list(
    ports,
    additional,
    hooks,
    blocklisted,
    connector,
    params,
    expected,
):
    def settings_get(path):
        if path == ["plugins", "serial_connector", "additionalPorts"]:
            return additional
        elif path == ["plugins", "serial_connector", "blocklistedPorts"]:
            return blocklisted
        elif path == ["printerConnection", "preferred", "connector"]:
            return connector
        elif path == ["printerConnection", "preferred", "parameters"]:
            return params
        return None

    with mock.patch(
        "octoprint.plugins.serial_connector.serial_comm.settings"
    ) as settings_getter:
        patched_settings = mock.MagicMock()
        patched_settings.get.side_effect = settings_get
        settings_getter.return_value = patched_settings

        with mock.patch("octoprint.plugin.plugin_manager") as pmgr_getter:
            patched_pmgr = mock.MagicMock()
            if hooks:

                def hook(candidates):
                    return hooks

                patched_pmgr.get_hooks.return_value = {"some_plugin": hook}
            else:
                patched_pmgr.get_hooks.return_value = {}
            pmgr_getter.return_value = patched_pmgr

            with mock.patch(
                "octoprint.plugins.serial_connector.serial_comm.os"
            ) as patched_os:
                scandir_result = []
                for port in ports:
                    d = mock.MagicMock()
                    d.name = port
                    d.path = f"/dev/{port}"
                    scandir_result.append(d)

                patched_os.name = "linux"
                patched_os.scandir.return_value = scandir_result

                with mock.patch("glob.glob") as patched_glob:
                    patched_glob.return_value = additional

                    # test
                    result = serialList()

                    # verify
                    assert result == expected

                    patched_glob.assert_has_calls(
                        [mock.call(port) for port in additional]
                    )


def test_serial_list_windows():
    with mock.patch(
        "octoprint.plugins.serial_connector.serial_comm.settings"
    ) as settings_getter:
        patched_settings = mock.MagicMock()
        patched_settings.get.return_value = None
        settings_getter.return_value = patched_settings

        with mock.patch("octoprint.plugin.plugin_manager") as pmgr_getter:
            patched_pmgr = mock.MagicMock()
            patched_pmgr.get_hooks.return_value = {}
            pmgr_getter.return_value = patched_pmgr

            with mock.patch(
                "octoprint.plugins.serial_connector.serial_comm.os"
            ) as patched_os:
                patched_os.name = "nt"

                def mocked_enumvalue(key, idx):
                    if idx < 2:
                        return ("", f"COM{idx}")
                    raise OSError("bzzzt")

                mocked_openkey = mock.MagicMock()
                mocked_openkey.__enter__.return_value = "some_key"

                mocked_winreg = mock.Mock()
                mocked_winreg.HKEY_LOCAL_MACHINE = "HKEY_LOCAL_MACHINE"
                mocked_winreg.OpenKey.return_value = mocked_openkey
                mocked_winreg.EnumValue.side_effect = mocked_enumvalue

                with mock.patch.dict(sys.modules, {"winreg": mocked_winreg}):
                    # test
                    result = serialList()

                    # verify
                    assert result == ["COM0", "COM1"]

                    mocked_winreg.EnumValue.assert_has_calls(
                        [
                            mock.call("some_key", 0),
                            mock.call("some_key", 1),
                            mock.call("some_key", 2),
                        ]
                    )


@pytest.mark.parametrize(
    "baudrates, additional, blocklisted, connector, params, expected",
    [
        pytest.param(None, [], [], "other", {}, STANDARD_BAUDRATES, id="most basic case"),
        pytest.param(
            [], [], [], "other", {}, [], id="empty candidates, no defaults used"
        ),
        pytest.param([], [300000], [], "other", {}, [300000], id="additional baudrate"),
        pytest.param(
            [115200, 250000, 9600],
            [],
            [],
            "serial",
            {"baudrate": 9600},
            [9600, 115200, 250000],
            id="sorting changed by preferred connection",
        ),
        pytest.param(
            [115200, 250000, 9600],
            [],
            [],
            "serial",
            {"baudrate": 300000},
            [115200, 250000, 9600],
            id="preferred connection not found in candidates",
        ),
        pytest.param(
            [115200, 250000, 9600],
            [],
            [],
            "serial",
            {},
            [115200, 250000, 9600],
            id="preferred connection but no preferred baudrate",
        ),
        pytest.param(
            [115200, 250000],
            [],
            [250000],
            "other",
            {},
            [115200],
            id="blocklisted baudrate",
        ),
        pytest.param(
            [115200],
            [300000],
            [300000],
            "other",
            {},
            [115200],
            id="blocklist used *after* additional baudrates get added",
        ),
    ],
)
def test_baudrate_list(
    baudrates,
    additional,
    blocklisted,
    connector,
    params,
    expected,
):
    def settings_get(path):
        if path == ["plugins", "serial_connector", "additionalBaudrates"]:
            return additional
        elif path == ["plugins", "serial_connector", "blocklistedBaudrates"]:
            return blocklisted
        elif path == ["printerConnection", "preferred", "connector"]:
            return connector
        elif path == ["printerConnection", "preferred", "parameters"]:
            return params
        return None

    with mock.patch(
        "octoprint.plugins.serial_connector.serial_comm.settings"
    ) as settings_getter:
        patched_settings = mock.MagicMock()
        patched_settings.get.side_effect = settings_get
        settings_getter.return_value = patched_settings

        # test
        result = baudrateList(baudrates)

        # verify
        assert result == expected


def test_baudrate_list_copied():
    additional = [300000]

    def settings_get(path):
        if path == ["plugins", "serial_connector", "additionalBaudrates"]:
            return additional
        elif path == ["plugins", "serial_connector", "blocklistedBaudrates"]:
            return []
        elif path == ["printerConnection", "preferred", "connector"]:
            return "other"
        elif path == ["printerConnection", "preferred", "parameters"]:
            return {}
        return None

    with mock.patch(
        "octoprint.plugins.serial_connector.serial_comm.settings"
    ) as settings_getter:
        patched_settings = mock.MagicMock()
        patched_settings.get.side_effect = settings_get
        settings_getter.return_value = patched_settings

        expected = additional + STANDARD_BAUDRATES

        # test & verify
        result = baudrateList()  # first call
        assert result == expected

        result = baudrateList()  # second call
        assert result == expected  # should not have additional in there twice now
