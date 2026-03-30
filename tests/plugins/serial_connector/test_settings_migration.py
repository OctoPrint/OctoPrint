from copy import copy
from unittest import mock

import pytest

TARGET_SETTINGS_VERSION = 3


@pytest.fixture()
def plugin():
    from octoprint.plugins.serial_connector import SerialConnectorPlugin

    p = SerialConnectorPlugin()
    p._settings = mock.MagicMock()
    p._logger = mock.MagicMock()

    return p


def settings_with_needed_migration(path):
    if path == ["serial"]:
        return {
            "port": "VIRTUAL",
            "baudrate": 115200,
            "autoconnect": True,
            "log": True,
        }
    elif path == ["printerConnection", "preferred", "connector"]:
        return "other"
    elif path == ["plugins", "serial_connector"]:
        return {"blacklistedPorts": []}
    elif path == ["plugins", "logging"]:
        return {"serial_log_warning": False}
    elif path == ["appearance", "components", "disabled", "navbar"] or path == [
        "appearance",
        "components",
        "order",
        "navbar",
    ]:
        return ["foo", "plugin_logging_seriallog", "bar"]
    return None


@pytest.mark.parametrize(
    "preferred_connector, autoconnect, parameters, expected",
    [
        (
            None,
            False,
            {"port": "VIRTUAL", "baudrate": 115200},
            {"port": "VIRTUAL", "baudrate": 115200},
        ),
        (
            "serial",
            False,
            {"port": "VIRTUAL", "baudrate": 115200},
            {"port": "VIRTUAL", "baudrate": 115200},
        ),
        (
            "serial",
            True,
            {"port": "VIRTUAL", "baudrate": 115200},
            {"port": "VIRTUAL", "baudrate": 115200},
        ),
        ("serial", True, {"port": "VIRTUAL"}, {"port": "VIRTUAL", "baudrate": None}),
        ("serial", True, {"baudrate": 115200}, {"port": None, "baudrate": 115200}),
        ("serial", True, {}, {"port": None, "baudrate": None}),
    ],
)
def test_migration_serial_printer_connection(
    plugin, preferred_connector, autoconnect, parameters, expected
):
    """
    Tests correct migration of printer connection settings (autoconnect, port, baudrate)
    for serial or unset preferred connector
    """

    # prep
    current_version = None

    def settings_global_get(path):
        if path == ["serial"]:
            return dict(autoconnect=autoconnect, log=True, **parameters)
        elif path == ["printerConnection", "preferred", "connector"]:
            return preferred_connector
        return None

    plugin._settings.global_get.side_effect = settings_global_get

    # test
    plugin.on_settings_migrate(TARGET_SETTINGS_VERSION, current_version)

    # verify
    plugin._settings.global_set.assert_has_calls(
        [
            mock.call(
                ["printerConnection", "preferred", "parameters"],
                expected,
            ),
            mock.call(["plugins", "serial_connector"], {"log": True}, force=True),
        ]
    )
    plugin._settings.global_set_boolean.assert_called_once_with(
        [
            "printerConnection",
            "autoconnect",
        ],
        autoconnect,
    )
    plugin._settings.global_remove.assert_called_once_with(["serial"])


def test_migration_serial_printer_connection_other_connector(plugin):
    """
    Tests deletion of printer connection settings (autoconnect, port, baudrate)
    for unrelated default connector
    """

    # prep
    current_version = None

    def settings_global_get(path):
        if path == ["serial"]:
            return {
                "port": "VIRTUAL",
                "baudrate": 115200,
                "autoconnect": True,
                "log": True,
            }
        elif path == ["printerConnection", "preferred", "connector"]:
            return "other"
        return None

    plugin._settings.global_get.side_effect = settings_global_get

    # test
    plugin.on_settings_migrate(TARGET_SETTINGS_VERSION, current_version)

    # verify
    plugin._settings.global_set.assert_has_calls(
        [
            mock.call(["plugins", "serial_connector"], {"log": True}, force=True),
        ]
    )
    plugin._settings.global_remove.assert_called_once_with(["serial"])


@pytest.mark.parametrize(
    "config, expected",
    [
        # errorHandling
        ({"disconnectOnErrors": True}, {"errorHandling": "disconnect"}),
        ({"disconnectOnErrors": False}, {"errorHandling": "cancel"}),
        ({"ignoreErrorsFromFirmware": True}, {"errorHandling": "ignore"}),
        ({"ignoreErrorsFromFirmware": False}, {"errorHandling": "cancel"}),
        # sendChecksum
        ({"alwaysSendChecksum": True}, {"sendChecksum": "always"}),
        ({"alwaysSendChecksum": False}, {"sendChecksum": "print"}),
        ({"neverSendChecksum": True}, {"sendChecksum": "never"}),
        ({"neverSendChecksum": False}, {"sendChecksum": "print"}),
    ],
)
def test_migration_serial_behaviour(plugin, config, expected):
    """Tests migration of serial settings to plugins.serial_connector.{errorHandling|sendChecksum}"""

    # prep
    current_version = None

    def settings_global_get(path):
        if path == ["serial"]:
            return config
        return None

    plugin._settings.global_get.side_effect = settings_global_get

    # test
    plugin.on_settings_migrate(TARGET_SETTINGS_VERSION, current_version)

    # verify
    plugin._settings.global_set.assert_has_calls(
        [
            mock.call(["plugins", "serial_connector"], expected, force=True),
        ]
    )
    plugin._settings.global_remove.assert_called_once_with(["serial"])


def test_migration_autorefresh(plugin):
    """Tests migration of serial settings to printerConnection.autorefresh"""

    # prep
    current_version = None

    def settings_global_get(path):
        if path == ["serial"]:
            return {"autorefresh": True}
        elif path == ["printerConnection", "preferred", "connector"]:
            return "other"
        return None

    plugin._settings.global_get.side_effect = settings_global_get

    # test
    plugin.on_settings_migrate(TARGET_SETTINGS_VERSION, current_version)

    # verify
    plugin._settings.global_set_boolean.assert_called_once_with(
        ["printerConnection", "autorefresh"], True
    )
    plugin._settings.global_set.assert_called_once_with(
        ["plugins", "serial_connector"], {}, force=True
    )
    plugin._settings.global_remove.assert_called_once_with(["serial"])


def test_migration_autorefresh_interval(plugin):
    """Tests migration of serial settings to printerConnection.autorefreshInterval"""

    # prep
    current_version = None

    def settings_global_get(path):
        if path == ["serial"]:
            return {"autorefreshInterval": 5}
        elif path == ["printerConnection", "preferred", "connector"]:
            return "other"
        return None

    plugin._settings.global_get.side_effect = settings_global_get

    # test
    plugin.on_settings_migrate(TARGET_SETTINGS_VERSION, current_version)

    # verify
    plugin._settings.global_set_int.assert_called_once_with(
        ["printerConnection", "autorefreshInterval"], 5
    )
    plugin._settings.global_set.assert_called_once_with(
        ["plugins", "serial_connector"], {}, force=True
    )
    plugin._settings.global_remove.assert_called_once_with(["serial"])


@pytest.mark.parametrize(
    "current_version, config, expected",
    [
        (None, {"blacklistedPorts": []}, {"blocklistedPorts": []}),
        (1, {"blacklistedPorts": []}, {"blocklistedPorts": []}),
        (None, {"blacklistedBaudrates": []}, {"blocklistedBaudrates": []}),
        (1, {"blacklistedBaudrates": []}, {"blocklistedBaudrates": []}),
    ],
)
def test_migration_blocklists(plugin, current_version, config, expected):
    """Tests migration of blacklisted{ports|Baudrates} to blocklisted{Ports|Baudrates}"""

    # prep
    def settings_global_get(path):
        if path == ["plugins", "serial_connector"]:
            return config
        return None

    plugin._settings.global_get.side_effect = settings_global_get

    # test
    plugin.on_settings_migrate(TARGET_SETTINGS_VERSION, current_version)

    # verify
    plugin._settings.global_set.assert_has_calls(
        [
            mock.call(["plugins", "serial_connector"], expected, force=True),
        ]
    )


def test_migration_blocklists_unmodified(plugin):
    """Tests unnecessary blacklist migration"""

    # prep
    current_version = None

    def settings_global_get(path):
        if path == ["plugins", "serial_connector"]:
            return {"log": True}
        return None

    plugin._settings.global_get.side_effect = settings_global_get

    # test
    plugin.on_settings_migrate(TARGET_SETTINGS_VERSION, current_version)

    # verify
    plugin._settings.global_set.assert_not_called()


@pytest.mark.parametrize("current_version", [None, 2])
@pytest.mark.parametrize(
    "serial_log_warning, navbar_disabled_components, expected_calls",
    [
        # warning enabled and component not disabled
        (
            True,
            ["foo", "bar"],
            [
                mock.call(["plugins", "logging"], {}, force=True),
            ],
        ),
        # warning enabled and component disabled
        (
            True,
            ["foo", "plugin_logging_seriallog", "bar"],
            [
                mock.call(["plugins", "logging"], {}, force=True),
                mock.call(
                    ["appearance", "components", "disabled", "navbar"],
                    ["foo", "plugin_serial_connector_seriallog", "bar"],
                ),
            ],
        ),
        # warning disabled and component not disabled
        (
            False,
            ["foo", "bar"],
            [
                mock.call(["plugins", "logging"], {}, force=True),
                mock.call(
                    ["appearance", "components", "disabled", "navbar"],
                    ["foo", "bar", "plugin_serial_connector_seriallog"],
                ),
            ],
        ),
        # warning disabled and component disabled
        (
            False,
            ["foo", "plugin_logging_seriallog", "bar"],
            [
                mock.call(["plugins", "logging"], {}, force=True),
                mock.call(
                    ["appearance", "components", "disabled", "navbar"],
                    ["foo", "plugin_serial_connector_seriallog", "bar"],
                ),
            ],
        ),
    ],
)
def test_migration_logging_warning(
    plugin,
    current_version,
    serial_log_warning,
    navbar_disabled_components,
    expected_calls,
):
    """Tests log warning flag gets migrated correctly"""

    # prep
    def settings_global_get(path):
        if path == ["plugins", "logging"]:
            return {"serial_log_warning": serial_log_warning}
        elif path == ["appearance", "components", "disabled", "navbar"]:
            return copy(navbar_disabled_components)
        return None

    plugin._settings.global_get.side_effect = settings_global_get

    # test
    plugin.on_settings_migrate(TARGET_SETTINGS_VERSION, current_version)

    # verify
    plugin._settings.global_set.assert_has_calls(expected_calls)
    assert plugin._settings.global_set.call_count == len(expected_calls)


@pytest.mark.parametrize("current_version", [None, 2])
def test_migration_logging_navbar_order(plugin, current_version):
    """Tests navbar order list gets migrated correctly"""

    # prep
    def settings_global_get(path):
        if path == ["appearance", "components", "order", "navbar"]:
            return ["foo", "plugin_logging_seriallog", "bar"]
        return None

    plugin._settings.global_get.side_effect = settings_global_get

    # test
    plugin.on_settings_migrate(TARGET_SETTINGS_VERSION, current_version)

    # verify
    plugin._settings.global_set.assert_called_once_with(
        ["appearance", "components", "order", "navbar"],
        ["foo", "plugin_serial_connector_seriallog", "bar"],
    )


@pytest.mark.parametrize("current_version", [None, 2])
def test_migration_logging_navbar_disabled(plugin, current_version):
    """Tests navbar disabled list gets migrated correctly"""

    # prep
    def settings_global_get(path):
        if path == ["appearance", "components", "disabled", "navbar"]:
            return ["foo", "plugin_logging_seriallog", "bar"]
        return None

    plugin._settings.global_get.side_effect = settings_global_get

    # test
    plugin.on_settings_migrate(TARGET_SETTINGS_VERSION, current_version)

    # verify
    plugin._settings.global_set.assert_called_once_with(
        ["appearance", "components", "disabled", "navbar"],
        ["foo", "plugin_serial_connector_seriallog", "bar"],
    )


EXPECTED_CALLS_BY_VERSION = {
    "none_to_1": [
        mock.call(["plugins", "serial_connector"], {"log": True}, force=True),
    ],
    "1_to_2": [
        mock.call(["plugins", "serial_connector"], {"blocklistedPorts": []}, force=True)
    ],
    "2_to_3": [
        mock.call(["plugins", "logging"], {}, force=True),
        mock.call(
            ["appearance", "components", "order", "navbar"],
            ["foo", "plugin_serial_connector_seriallog", "bar"],
        ),
        mock.call(
            ["appearance", "components", "disabled", "navbar"],
            ["foo", "plugin_serial_connector_seriallog", "bar"],
        ),
    ],
}


def test_migration_path_version_none(plugin):
    """Tests all migrations are done"""

    # prep
    current_version = None

    plugin._settings.global_get.side_effect = settings_with_needed_migration

    # test
    plugin.on_settings_migrate(TARGET_SETTINGS_VERSION, current_version)

    # verify
    plugin._settings.global_set.assert_has_calls(
        EXPECTED_CALLS_BY_VERSION["none_to_1"]
        + EXPECTED_CALLS_BY_VERSION["1_to_2"]
        + EXPECTED_CALLS_BY_VERSION["2_to_3"]
    )
    plugin._settings.global_remove.assert_called_once_with(["serial"])


def test_migration_path_version_1(plugin):
    """Tests only migrations to version 2 & 3 are done"""

    # prep
    current_version = 1

    plugin._settings.global_get.side_effect = settings_with_needed_migration

    # test
    plugin.on_settings_migrate(TARGET_SETTINGS_VERSION, current_version)

    # verify
    plugin._settings.global_set.assert_has_calls(
        EXPECTED_CALLS_BY_VERSION["1_to_2"] + EXPECTED_CALLS_BY_VERSION["2_to_3"]
    )
    plugin._settings.global_remove.assert_not_called()


def test_migration_path_version_2(plugin):
    """Tests only migrations to version 3 are done"""

    # prep
    current_version = 2

    plugin._settings.global_get.side_effect = settings_with_needed_migration

    # test
    plugin.on_settings_migrate(TARGET_SETTINGS_VERSION, current_version)

    # verify
    plugin._settings.global_set.assert_has_calls(EXPECTED_CALLS_BY_VERSION["2_to_3"])
    plugin._settings.global_remove.assert_not_called()


def test_migration_path_current_version(plugin):
    """Tests no migration is done"""

    # prep
    plugin._settings.global_get.side_effect = settings_with_needed_migration

    # test
    plugin.on_settings_migrate(TARGET_SETTINGS_VERSION, TARGET_SETTINGS_VERSION)

    # verify
    plugin._settings.global_set.assert_not_called()
    plugin._settings.global_remove.assert_not_called()
