from flask_babel import gettext

import octoprint.plugin
from octoprint.logging.handlers import TriggeredRolloverLogHandler


class SerialLogHandler(TriggeredRolloverLogHandler):
    pass


class SerialConnectorPlugin(
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.TemplatePlugin,
):
    def initialize(self):
        from .connector import ConnectedSerialPrinter  # noqa: F401

        ConnectedSerialPrinter._event_bus = self._event_bus
        ConnectedSerialPrinter._file_manager = self._file_manager
        ConnectedSerialPrinter._plugin_manager = self._plugin_manager
        ConnectedSerialPrinter._plugin_settings = self._settings
        ConnectedSerialPrinter._serial_logger = self._configure_serial_logger()

    def _configure_serial_logger(self):
        import logging
        import os

        from octoprint.logging import LOGGING_TIMED_MESSAGE_ONLY_FORMAT

        serial_log_handler = SerialLogHandler(
            os.path.join(
                self._settings.global_get_basefolder("logs"), "serial.log"
            ),  # for backwards compatibility reasons we'll continue to use the name serial.log
            encoding="utf-8",
            backupCount=3,
            delay=True,
        )
        serial_log_handler.setFormatter(
            logging.Formatter(LOGGING_TIMED_MESSAGE_ONLY_FORMAT)
        )
        serial_log_handler.setLevel(logging.DEBUG)

        serial_logger = logging.getLogger(
            "octoprint.plugins.serial_connector.connector.console"
        )
        serial_logger.addHandler(serial_log_handler)
        serial_logger.setLevel(logging.INFO)
        serial_logger.propagate = False

        return serial_logger

    ##~~ SettingsPlugin mixin

    def get_settings_defaults(self):
        from .config_schema import SerialConfig

        return SerialConfig().model_dump()

    def get_settings_version(self):
        return 2

    def on_settings_migrate(self, target, current):
        if current is None:
            config = self._settings.global_get(["serial"])
            if config:
                self._logger.info(
                    "Migrating settings from serial to plugins.serial_connector..."
                )

                if "disconnectOnErrors" in config or "ignoreErrorsFromFirmware" in config:
                    if config.get("disconnectOnErrors", False):
                        config["errorHandling"] = "disconnect"
                    elif config.get("ignoreErrorsFromFirmware", False):
                        config["errorHandling"] = "ignore"
                    else:
                        config["errorHandling"] = "cancel"

                    for key in ("disconnectOnErrors", "ignoreErrorsFromFirmware"):
                        try:
                            del config[key]
                        except KeyError:
                            pass

                if "alwaysSendChecksum" in config or "neverSendChecksum" in config:
                    if config.get("alwaysSendChecksum", False):
                        config["sendChecksum"] = "always"
                    elif config.get("neverSendChecksum", False):
                        config["sendChecksum"] = "never"
                    else:
                        config["sendChecksum"] = "print"

                    for key in ("alwaysSendChecksum", "neverSendChecksum"):
                        try:
                            del config[key]
                        except KeyError:
                            pass

                self._settings.global_set(
                    ["plugins", "serial_connector"], config, force=True
                )
                self._settings.global_remove(["serial"])

        if current is None or current < 2:
            config = self._settings.global_get(["plugins", "serial_connector"])
            modified = False

            if config:
                if "blacklistedPorts" in config:
                    config["blocklistedPorts"] = config["blacklistedPorts"]
                    del config["blacklistedPorts"]
                    modified = True
                if "blacklistedBaudrates" in config:
                    config["blocklistedBaudrates"] = config["blacklistedBaudrates"]
                    del config["blacklistedBaudrates"]
                    modified = True

                if modified:
                    self._settings.global_set(
                        ["plugins", "serial_connector"], config, force=True
                    )

            # TODO: migration should be in version 3
            logging_config = self._settings.global_get(["plugins", "logging"])
            if logging_config and "serial_log_warning" in logging_config:
                self._settings.global_set(
                    ["plugins", "serial_connector", "logWarning"],
                    logging_config["serial_log_warning"],
                )
                del logging_config["serial_log_warning"]
                self._settings.global_set(
                    ["plugins", "logging"], logging_config, force=True
                )

    ##~~ TemplatePlugin mixin

    def get_template_configs(self):
        return [
            {
                "type": "connection_options",
                "name": gettext("Serial Connection"),
                "connector": "serial",
                "template": "serial_connector_connection_option.jinja2",
                "custom_bindings": True,
            },
            {
                "type": "settings",
                "name": gettext("Serial Connection"),
                "template": "serial_connector_settings.jinja2",
                "custom_bindings": True,
            },
            {
                "type": "navbar",
                "template": "serial_connector_navbar_seriallog.jinja2",
                "suffix": "_seriallog",
            },
        ]

    def is_template_autoescaped(self):
        return True


__plugin_name__ = "Serial Connector"
__plugin_author__ = "Gina Häußge"
__plugin_description__ = (
    "A printer connector plugin to support serial communication (e.g. Marlin, Prusa, ...)"
)
__plugin_license__ = "AGPLv3"
__plugin_pythoncompat__ = ">=3.9,<4"
__plugin_disabling_discouraged__ = gettext(
    "Without this plugin you will no longer be able to connect "
    "to printers based on serial communication."
)
__plugin_implementation__ = SerialConnectorPlugin()
