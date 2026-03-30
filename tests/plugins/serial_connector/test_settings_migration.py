from unittest import mock

import pytest


@pytest.fixture()
def plugin():
    from octoprint.plugins.serial_connector import SerialConnectorPlugin

    p = SerialConnectorPlugin()
    p._settings = mock.MagicMock()
    p._logger = mock.MagicMock()

    return p


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
    target = 2
    current_version = None

    def settings_global_get(path):
        if path == ["serial"]:
            return dict(autoconnect=autoconnect, log=True, **parameters)
        elif path == ["printerConnection", "preferred", "connector"]:
            return preferred_connector
        return None

    plugin._settings.global_get.side_effect = settings_global_get

    # test
    plugin.on_settings_migrate(target, current_version)

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
    target = 2
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
    plugin.on_settings_migrate(target, current_version)

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
    target = 2
    current_version = None

    def settings_global_get(path):
        if path == ["serial"]:
            return config
        return None

    plugin._settings.global_get.side_effect = settings_global_get

    # test
    plugin.on_settings_migrate(target, current_version)

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
    target = 2
    current_version = None

    def settings_global_get(path):
        if path == ["serial"]:
            return {"autorefresh": True}
        elif path == ["printerConnection", "preferred", "connector"]:
            return "other"
        return None

    plugin._settings.global_get.side_effect = settings_global_get

    # test
    plugin.on_settings_migrate(target, current_version)

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
    target = 2
    current_version = None

    def settings_global_get(path):
        if path == ["serial"]:
            return {"autorefreshInterval": 5}
        elif path == ["printerConnection", "preferred", "connector"]:
            return "other"
        return None

    plugin._settings.global_get.side_effect = settings_global_get

    # test
    plugin.on_settings_migrate(target, current_version)

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
    target = 2

    def settings_global_get(path):
        if path == ["plugins", "serial_connector"]:
            return config
        return None

    plugin._settings.global_get.side_effect = settings_global_get

    # test
    plugin.on_settings_migrate(target, current_version)

    # verify
    plugin._settings.global_set.assert_has_calls(
        [
            mock.call(["plugins", "serial_connector"], expected, force=True),
        ]
    )


def test_migration_blocklists_unmodified(plugin):
    """Tests unnecessary blacklist migration"""

    # prep
    target = 2
    current_version = None

    def settings_global_get(path):
        if path == ["plugins", "serial_connector"]:
            return {"log": True}
        return None

    plugin._settings.global_get.side_effect = settings_global_get

    # test
    plugin.on_settings_migrate(target, current_version)

    # verify
    plugin._settings.global_set.assert_not_called()


def test_migration_path_version_none(plugin):
    """Tests both migrations are done"""

    # prep
    target = 2
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
        elif path == ["plugins", "serial_connector"]:
            return {"blacklistedPorts": []}
        return None

    plugin._settings.global_get.side_effect = settings_global_get

    # test
    plugin.on_settings_migrate(target, current_version)

    # verify
    plugin._settings.global_set.assert_has_calls(
        [
            mock.call(["plugins", "serial_connector"], {"log": True}, force=True),
            mock.call(
                ["plugins", "serial_connector"], {"blocklistedPorts": []}, force=True
            ),
        ]
    )
    plugin._settings.global_remove.assert_called_once_with(["serial"])


def test_migration_path_version_1(plugin):
    """Tests only the blocklist migration is done"""

    # prep
    target = 2
    current_version = 1

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
        elif path == ["plugins", "serial_connector"]:
            return {"blacklistedPorts": []}
        return None

    plugin._settings.global_get.side_effect = settings_global_get

    # test
    plugin.on_settings_migrate(target, current_version)

    # verify
    plugin._settings.global_set.assert_has_calls(
        [
            mock.call(
                ["plugins", "serial_connector"], {"blocklistedPorts": []}, force=True
            ),
        ]
    )
    plugin._settings.global_remove.assert_not_called()


def test_migration_path_version_2(plugin):
    """Tests no migration is done"""

    # prep
    target = 2
    current_version = 2

    def settings_global_get(path):
        return None

    plugin._settings.global_get.side_effect = settings_global_get

    # test
    plugin.on_settings_migrate(target, current_version)

    # verify
    plugin._settings.global_set.assert_not_called()
    plugin._settings.global_remove.assert_not_called()
