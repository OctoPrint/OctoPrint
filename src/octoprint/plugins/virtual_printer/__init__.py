__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"

from typing import Optional

import octoprint.plugin
from octoprint.access.permissions import Permissions
from octoprint.schema import BaseModel


class VirtualPrinterSdFilesConfig(BaseModel):
    size: bool = True
    """
    Whether M20 responses will include filesize or not

    * True: ``<filename> <filesize in bytes>``
    * False: ``<filename>``
    """

    timestamp: bool = False
    """
    Whether M20 responses will include timestamp or not (only if ``size`` is enabled)

    * True: ``<filename> <filesize in bytes> <timestamp as hex>``
    * False: ``<filename> <filesize in bytes>``
    """

    longname: bool = False
    """
    Whether M20 responses will include longname or not (only if ``size`` is enabled)

    Mutually exclusive with ``longname_quoted``

    * True: ``<filename> <filesize in bytes> <longname>``
    * False: ``<filename> <filesize in bytes>``
    """

    longname_quoted: bool = True
    """
    Whether M20 responses will include quoted longname or not (only if ``size`` is enabled)

    Mutually exclusive with ``longname``.

    * True: ``<filename> <filesize in bytes> "<longname>"``
    * False: ``<filename> <filesize in bytes>``
    """

    upper_case: bool = False
    """Whether to uppercase the filenames in M20 responses"""


class VirtualPrinterErrorsConfig(BaseModel):
    checksum_mismatch: str = "Checksum mismatch"
    checksum_missing: str = "Missing checksum"
    lineno_mismatch: str = "expected line {} got {}"
    lineno_missing: str = "No Line Number with checksum, Last Line: {}"
    maxtemp: str = "MAXTEMP triggered!"
    mintemp: str = "MINTEMP triggered!"
    command_unknown: str = "Unknown command {}"


class VirtualPrinterConfig(BaseModel):
    enabled: bool = False
    """Whether to enable the virtual printer and include it in the list of available serial connections."""

    okAfterResend: bool = False
    """Whether to send an additional "ok" after a resend request (like Repetier)"""

    forceChecksum: bool = False
    """
    Whether to force checksums and line number in the communication (like Repetier), if set to true
    printer will only accept commands that come with linenumber and checksum and throw an error for
    lines that don't
    """

    numExtruders: int = 1
    """Number of extruders to simulate on the virtual printer. Map from tool id (0, 1, ...) to temperature in °C"""

    pinnedExtruders: Optional[dict[int, float]] = None
    """Allows pinning certain hotends to a fixed temperature"""

    includeCurrentToolInTemps: bool = True
    """
    Whether to include the current tool temperature in the M105 output as separate T segment or not.

    * True:

      .. code-block:: none

         >>> M105
         <<< ok T:23.5/0.0 T0:34.3/0.0 T1:23.5/0.0 B:43.2/0.0

    * False:

      .. code-block:: none

         >>> M105
         <<< ok T0:34.3/0.0 T1:23.5/0.0 B:43.2/0.0
    """

    includeFilenameInOpened: bool = True
    """
    Whether to include the selected filename in the M23 File opened response.

    * True:

      .. code-block:: none

         >>> M23 filename.gcode
         <<< File opened: filename.gcode  Size: 27

    * False:

      .. code-block:: none

         >>> M23 filename.gcode
         <<< File opened
    """

    hasBed: bool = True
    """Whether the simulated printer should also simulate a heated bed or not"""

    hasChamber: bool = False
    """Whether the simulated printer should also simulate a heated chamber or not"""

    repetierStyleTargetTemperature: bool = False
    """
    If enabled, reports the set target temperatures as separate messages from the firmware

    * True:

      .. code-block:: none

         >>> M109 S220.0
         <<< TargetExtr0:220.0
         <<< ok
         >>> M105
         <<< ok T0:34.3 T1:23.5 B:43.2

    * False:

      .. code-block:: none

         >>> M109 S220.0
         <<< ok
         >>> M105
         <<< ok T0:34.3/220.0 T1:23.5/0.0 B:43.2/0.0
    """

    okBeforeCommandOutput: bool = False
    """
    If enabled, ok will be sent before a commands output, otherwise after or inline (M105)

    * True:

      .. code-block:: none

         >>> M20
         <<< ok
         <<< Begin file list
         <<< End file list

    * False:

      .. code-block:: none

         >>> M20
         <<< Begin file list
         <<< End file list
         <<< ok
    """

    smoothieTemperatureReporting: bool = False
    """
    If enabled, reports the first extruder in M105 responses as T instead of T0

    * True:

      .. code-block:: none

         >>> M105
         <<< ok T:34.3/0.0 T1:23.5/0.0 B:43.2/0.0

    * False:

      .. code-block:: none

         >>> M105
         <<< ok T0:34.3/0.0 T1:23.5/0.0 B:43.2/0.0
    """

    klipperTemperatureReporting: bool = False
    """Whether to report the hotend temperatures as ``T0`` even with a single extruder (Klipper behaviour)"""

    sdFiles: VirtualPrinterSdFilesConfig = VirtualPrinterSdFilesConfig()
    """
    Settings related to the SD file list output

    General format:
    ``<filename>[ <filesize in bytes> [ <timestamp>][ (<longname> | "<longname>")]]``
    """

    throttle: float = 0.01
    """Forced pause for retrieving from the outgoing buffer"""

    sendWait: bool = True
    """Whether to send "wait" responses every "waitInterval" seconds when serial rx buffer is empty"""

    waitInterval: float = 1.0
    """Interval in which to send "wait" lines when rx buffer is empty"""

    rxBuffer: int = 64
    """Size of the simulated RX buffer in bytes, when it's full a send from OctoPrint's side will block"""

    commandBuffer: int = 4
    """Size of simulated command buffer, number of commands. If full, buffered commands will block until a slot frees up"""

    supportM112: bool = True
    """Whether to support the M112 command with simulated kill"""

    echoOnM117: bool = True
    """Whether to send messages received via M117 back as "echo:" lines"""

    brokenM29: bool = True
    """Whether to simulate broken M29 behaviour (missing ok after response)"""

    brokenResend: bool = False
    """Whether to simulate broken resend behaviour (missing ok after response)"""

    supportF: bool = False
    """Whether F is supported as individual command"""

    firmwareName: str = "Virtual Marlin 1.0"
    """Firmware name to report (useful for testing firmware detection)"""

    sharedNozzle: bool = False
    """Simulate a shared nozzle"""

    sendBusy: bool = False
    """Send "busy" messages if busy processing something"""

    busyInterval: float = 2.0
    """Interval in which to send "busy" lines while processing"""

    simulateReset: bool = True
    """Simulate a reset on connect"""

    resetLines: list[str] = ["start", "Marlin: Virtual Marlin!", "\x80", "SD card ok"]
    """Lines to send on simulated reset"""

    preparedOks: list[str] = []
    """Initial set of prepared oks to use instead of regular ok (e.g. to simulate mis-sent oks). Can also be filled at runtime via the debug command prepare_ok"""

    okFormatString: str = "ok"
    """
    Format string for ok response.

    Placeholders:

    * ``lastN``: last acknowledged line number
    * ``buffer``: empty slots in internal command buffer

    Example format string for "extended" ok format:

    .. code-block:: none

       ok N{lastN} P{buffer}
    """

    m115FormatString: str = "FIRMWARE_NAME:{firmware_name} PROTOCOL_VERSION:1.0"
    """
    Format string for M115 output.

    Placeholders:

    * ``firmware_name``: The firmware name as defined in firmwareName
    """

    m115ReportCapabilities: bool = True
    """Whether to include capability report in M115 output"""

    capabilities: dict[str, bool] = {
        "AUTOREPORT_TEMP": True,
        "AUTOREPORT_SD_STATUS": True,
        "AUTOREPORT_POS": False,
        "BUSY_PROTOCOL": False,
        "CHAMBER_TEMPERATURE": False,
        "EMERGENCY_PARSER": True,
        "EXTENDED_M20": False,
        "LFN_WRITE": False,
    }
    """Capabilities to report if capability report is enabled"""

    m115ReportArea: bool = False
    """Whether to include area report in the M115 output (M115_GEOMETRY_REPORT in Marlin)"""

    m114FormatString: str = "X:{x} Y:{y} Z:{z} E:{e[current]} Count: A:{a} B:{b} C:{c}"

    m105TargetFormatString: str = "{heater}:{actual:.2f}/ {target:.2f}"
    """
    Response to M105 when there is a target

    Placeholders:

    * ``heater``: The heater id (eg. ``T0``, ``T1``, ``B``)
    * ``actual``: The actual temperature of the heater
    * ``target``: The target temperature of heater
    """

    m105NoTargetFormatString: str = "{heater}:{actual:.2f}"
    """
    Response to M105 when there is no target

    Placeholders:

    * ``heater``: The heater id (eg. ``T0``, ``T1``, ``B``)
    * ``actual``: The actual temperature of the heater
    """

    m123RPMFormatString: str = "{fan}:{rpm} RPM"
    """
    Response to M123 for fan RPM

    Placeholders:

    * ``fan``: The fan id (e.g. E0)
    * ``rpm``: The rotation speed of the fan
    """

    m123PowerFormatString: str = "{fan}@:{power}"
    """
    Response to M123 for fan power level

    Placeholders:

    * ``fan``: The fan id (e.g. E0)
    * ``power``: The power level being delivered to the fan
    """

    ambientTemperature: float = 21.3
    """Simulated ambient temperature in °C"""

    fanMaxSpeed: int = 4560
    """The maximum speed (in RPM) the virtual printer's virtual fans can spin at"""

    errors: VirtualPrinterErrorsConfig = VirtualPrinterErrorsConfig()
    """Format strings for various error types"""

    enable_eeprom: bool = True
    """
    Enable virtual EEPROM

    If enabled, a file ``eeprom.json`` will be created in the plugin data folder
    to enable settings persistence across connections. Enables ``M50{0124}`` commands
    and a selection of other settings commands. Responses modeled on Marlin 2.0
    """

    support_M503: bool = True
    """Support M503"""

    resend_ratio: float = 0
    """Resend ratio to simulate noise on the line"""

    locked: bool = False
    """Whether the printer starts out as locked (active ``M510``)"""

    passcode: str = "1234"
    """Passcode for unlocking the printer via ``M511``"""

    simulated_errors: list[str] = [
        "100:resend",
        "105:resend_with_timeout",
        "110:missing_lineno",
        "115:checksum_mismatch",
    ]
    """Communication errors to simulate at specific line numbers, format ``<lineno>:<resend type>``"""


class VirtualPrinterPlugin(
    octoprint.plugin.SettingsPlugin, octoprint.plugin.TemplatePlugin
):
    def get_template_configs(self):
        return [{"type": "settings", "custom_bindings": False}]

    def get_settings_defaults(self):
        return VirtualPrinterConfig().model_dump()

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

    def get_settings_restricted_paths(self):
        return {
            Permissions.SETTINGS: [[key] for key in self.get_settings_defaults().keys()]
        }

    def virtual_printer_factory(self, comm_instance, port, baudrate, read_timeout):
        if not port == "VIRTUAL":
            return None

        if not self._settings.get_boolean(["enabled"]):
            return None

        import logging.handlers

        from octoprint.logging.handlers import CleaningTimedRotatingFileHandler

        seriallog_handler = CleaningTimedRotatingFileHandler(
            self._settings.get_plugin_logfile_path(postfix="serial"),
            when="D",
            backupCount=3,
        )
        seriallog_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        seriallog_handler.setLevel(logging.DEBUG)

        from . import virtual

        serial_obj = virtual.VirtualPrinter(
            self._settings,
            self._printer_profile_manager,
            data_folder=self.get_plugin_data_folder(),
            seriallog_handler=seriallog_handler,
            read_timeout=float(read_timeout),
            faked_baudrate=baudrate,
        )
        return serial_obj

    def get_additional_port_names(self, *args, **kwargs):
        if self._settings.get_boolean(["enabled"]):
            return ["VIRTUAL"]
        else:
            return []


__plugin_name__ = "Virtual Printer"
__plugin_author__ = "Gina Häußge, based on work by Daid Braam"
__plugin_homepage__ = (
    "https://docs.octoprint.org/en/main/development/virtual_printer.html"
)
__plugin_license__ = "AGPLv3"
__plugin_description__ = "Provides a virtual printer via a virtual serial port for development and testing purposes"
__plugin_pythoncompat__ = ">=3.10,<4"


def __plugin_load__():
    plugin = VirtualPrinterPlugin()

    global __plugin_implementation__
    __plugin_implementation__ = plugin

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.comm.transport.serial.factory": plugin.virtual_printer_factory,
        "octoprint.comm.transport.serial.additional_port_names": plugin.get_additional_port_names,
    }
