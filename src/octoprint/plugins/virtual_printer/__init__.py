__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"

import octoprint.plugin
from octoprint.comm.transport.serialtransport import SerialTransport


class VirtualSerialTransport(SerialTransport):
    name = "Virtual Connection"
    key = "virtual"

    settings = {}
    datafolder = None

    @classmethod
    def with_settings_and_data(cls, settings, datafolder):
        return type(
            f"{cls.__name__}WithSettingsAndData",
            (cls,),
            {"settings": settings, "datafolder": datafolder},
        )

    @classmethod
    def get_connection_options(cls):
        return []

    def create_connection(self, *args, **kwargs):
        from . import virtual

        self._serial = virtual.VirtualPrinter(self.settings, self.datafolder)


class VirtualPrinterPlugin(
    octoprint.plugin.SettingsPlugin, octoprint.plugin.TemplatePlugin
):
    def get_template_configs(self):
        return [{"type": "settings", "custom_bindings": False}]

    def get_settings_defaults(self):
        return {
            "enabled": False,
            "okAfterResend": False,
            "forceChecksum": False,
            "numExtruders": 1,
            "pinnedExtruders": None,
            "includeCurrentToolInTemps": True,
            "includeFilenameInOpened": True,
            "hasBed": True,
            "hasChamber": False,
            "repetierStyleTargetTemperature": False,
            "okBeforeCommandOutput": False,
            "smoothieTemperatureReporting": False,
            "klipperTemperatureReporting": False,
            "reprapfwM114": False,
            "sdFiles": {"size": True, "longname": False},
            "throttle": 0.01,
            "sendWait": True,
            "waitInterval": 1.0,
            "rxBuffer": 64,
            "commandBuffer": 4,
            "supportM112": True,
            "echoOnM117": True,
            "brokenM29": True,
            "brokenResend": False,
            "supportF": False,
            "firmwareName": "Virtual Marlin 1.0",
            "sharedNozzle": False,
            "sendBusy": False,
            "busyInterval": 2.0,
            "simulateReset": True,
            "resetLines": ["start", "Marlin: Virtual Marlin!", "\x80", "SD card ok"],
            "preparedOks": [],
            "okFormatString": "ok",
            "m115FormatString": "FIRMWARE_NAME:{firmware_name} PROTOCOL_VERSION:1.0",
            "m115ReportCapabilities": True,
            "capabilities": {
                "AUTOREPORT_TEMP": True,
                "AUTOREPORT_SD_STATUS": True,
                "EMERGENCY_PARSER": True,
            },
            "m114FormatString": "X:{x} Y:{y} Z:{z} E:{e[current]} Count: A:{a} B:{b} C:{c}",
            "m105TargetFormatString": "{heater}:{actual:.2f}/ {target:.2f}",
            "m105NoTargetFormatString": "{heater}:{actual:.2f}",
            "ambientTemperature": 21.3,
            "errors": {
                "checksum_mismatch": "Checksum mismatch",
                "checksum_missing": "Missing checksum",
                "lineno_mismatch": "expected line {} got {}",
                "lineno_missing": "No Line Number with checksum, Last Line: {}",
                "maxtemp": "MAXTEMP triggered!",
                "mintemp": "MINTEMP triggered!",
                "command_unknown": "Unknown command {}",
            },
            "enable_eeprom": True,
            "support_M503": True,
            "resend_ratio": 0,
        }

    def get_settings_version(self):
        return 1

    def on_settings_migrate(self, target, current):
        if current is None:
            config = self._settings.global_get(["devel", "virtualPrinter"])
            if config:
                self._logger.info(
                    "Migrating settings from devel.virtualPrinter to plugins.virtual_printer..."
                )
                self._settings.global_set(
                    ["plugins", "virtual_printer"], config, force=True
                )
                self._settings.global_remove(["devel", "virtualPrinter"])

    def register_transport_hook(self, *args, **kwargs):
        return [
            VirtualSerialTransport.with_settings_and_data(
                self._settings, self.get_plugin_data_folder()
            )
        ]


__plugin_name__ = "Virtual Printer"
__plugin_author__ = "Gina Häußge, based on work by Daid Braam"
__plugin_homepage__ = (
    "https://docs.octoprint.org/en/master/development/virtual_printer.html"
)
__plugin_license__ = "AGPLv3"
__plugin_description__ = "Provides a virtual printer via a virtual serial port for development and testing purposes"
__plugin_pythoncompat__ = ">=2.7,<4"


def __plugin_load__():
    plugin = VirtualPrinterPlugin()

    global __plugin_implementation__
    __plugin_implementation__ = plugin

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.comm.transport.register": plugin.register_transport_hook
    }
