from flask_babel import gettext

import octoprint.plugin


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

    ##~~ SettingsPlugin mixin

    def get_settings_defaults(self):
        from .config_schema import SerialConfig

        return SerialConfig().model_dump()

    def get_settings_version(self):
        return 1

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
