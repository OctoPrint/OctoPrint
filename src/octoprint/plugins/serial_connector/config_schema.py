from enum import Enum
from typing import Optional

from octoprint.schema import BaseModel
from octoprint.vendor.with_attrs_docs import with_attrs_docs


class AlwaysDetectNeverEnum(str, Enum):
    always = "always"
    detect = "detect"
    never = "never"


class AlwaysPrintNeverEnum(str, Enum):
    always = "always"
    print = "print"
    never = "never"


class InfoWarnNeverEnum(str, Enum):
    info = "info"
    warn = "warn"
    never = "never"


class DisconnectCancelIgnoreEnum(str, Enum):
    disconnect = "disconnect"
    cancel = "cancel"
    ignore = "ignore"


@with_attrs_docs
class SerialTimeoutConfig(BaseModel):
    detectionFirst: float = 10.0
    """Timeout during initial detection attempt, in seconds."""

    detectionConsecutive: float = 2.0
    """Timeout on consecutive detection attempts, in seconds."""

    connection: float = 10.0
    """Timeout for waiting to establish a connection with the selected port, in seconds."""

    communication: float = 30.0
    """Timeout during serial communication, in seconds."""

    communicationBusy: float = 3.0
    """Timeout during serial communication when busy protocol support is detected, in seconds."""

    temperature: float = 5.0
    """Timeout after which to query temperature when no target is set, in seconds."""

    temperatureTargetSet: float = 2.0
    """Timeout after which to query temperature when a target is set, in seconds."""

    temperatureAutoreport: float = 2.0
    """Autoreporting interval to request for the temperature report, in seconds."""

    sdStatus: float = 1.0
    """Timeout after which to query the SD status while SD printing."""

    sdStatusAutoreport: float = 1.0
    """Autoreporting interval to request for the SD status report, in seconds."""

    posAutoreport: float = 5.0
    """Autoreporting interval to request for the position report, in seconds."""

    resendOk: float = 0.5
    """Timeout after which to trigger an internal ``ok`` after a resend is received (works around a bug present in some firmwares), in seconds."""

    baudrateDetectionPause: float = 1.0
    """Pause between baudrate detection attempts, in seconds."""

    positionLogWait: float = 10.0
    """Time to wait to receive a position response before considering it unresponded, in seconds."""


@with_attrs_docs
class SerialMaxTimeouts(BaseModel):
    idle: int = 2
    """Max. timeouts when the printer is idle."""

    printing: int = 5
    """Max. timeouts when the printer is printing."""

    long: int = 5
    """Max. timeouts when a long running command is active."""


@with_attrs_docs
class SerialCapabilities(BaseModel):
    autoreport_temp: bool = True
    """Whether to enable temperature autoreport in the firmware if its support is detected."""

    autoreport_sdstatus: bool = True
    """Whether to enable SD printing autoreport in the firmware if its support is detected."""

    autoreport_pos: bool = True
    """Whether to enable position autoreport in the firmware if its support is detected."""

    busy_protocol: bool = True
    """Whether to shorten the communication timeout if the firmware seems to support the busy protocol."""

    emergency_parser: bool = True
    """Whether to send emergency commands out of band if the firmware seems to support the emergency parser."""

    extended_m20: bool = True
    """Whether to request extended M20 (file list) output from the firmware if its support is detected."""

    lfn_write: bool = True
    """Whether to enable long filename support for SD card writes if the firmware reports support for it."""


@with_attrs_docs
class SerialConfig(BaseModel):
    port: Optional[str] = None
    """The default port to use to connect to the printer. If unset or set to ``AUTO``, the port will be auto-detected."""

    baudrate: Optional[int] = None
    """The default baudrate to use to connect to the printer. If unset or set to 0, the baudrate will be auto-detected."""

    exclusive: bool = True
    """Whether to request exclusive access to the serial port."""

    lowLatency: bool = False
    """Whether to request low latency mode on the serial port."""

    autoconnect: bool = False
    """Whether to try to automatically connect to the printer on startup."""

    autorefresh: bool = True
    """Whether to automatically refresh the port list while no connection is established."""

    autorefreshInterval: int = 1
    """Interval in seconds at which to refresh the port list while no connection is established."""

    log: bool = False
    """Whether to log whole communication to ``serial.log`` (warning: might decrease performance)."""

    timeout: SerialTimeoutConfig = SerialTimeoutConfig()
    """Timeouts used for the serial connection to the printer, you might want to adjust these if you are experiencing connection problems."""

    maxCommunicationTimeouts: SerialMaxTimeouts = SerialMaxTimeouts()
    """Maximum number of timeouts to support before going into an error state"""

    maxWritePasses: int = 5
    """Maximum number of write attempts to serial during which nothing can be written before the communication with the printer is considered dead and OctoPrint will disconnect with an error."""

    additionalPorts: list[str] = []
    """Use this to define additional patterns to consider for serial port listing. Must be a list of valid `"glob" pattern <http://docs.python.org/3/library/glob.html>`_"""

    additionalBaudrates: list[int] = []
    """Use this to define additional baud rates to offer for connecting to serial ports. Must be a list of valid integers."""

    blacklistedPorts: list[str] = []
    """Use this to define patterns of ports to ignore"""

    blacklistedBaudrates: list[int] = []
    """Use this to define baudrates to ignore"""

    longRunningCommands: list[str] = [
        "G4",
        "G28",
        "G29",
        "G30",
        "G32",
        "M400",
        "M226",
        "M600",
    ]
    """Commands which are known to take a long time to be acknowledged by the firmware, e.g. homing, dwelling, auto leveling etc."""

    blockedCommands: list[str] = ["M0", "M1"]
    """
    Commands which should not be sent to the printer, e.g. because they are known to block serial communication until
    physical interaction with the printer as is the case on most firmwares with the default ``M0`` and ``M1``.
    """

    ignoredCommands: list[str] = []
    """
    Commands which should not be sent to the printer and just silently ignored. An example of when you may wish to use
    this would be to manually change a filament on M600, by using that as a Pausing command.
    """

    pausingCommands: list[str] = ["M0", "M1", "M25"]
    """Commands which should cause OctoPrint to pause any ongoing prints."""

    emergencyCommands: list[str] = ["M112", "M108", "M410"]
    """Commands which are considered emergency commands and will be sent immediately, jumping OctoPrint's internal queues."""

    checksumRequiringCommands: list[str] = ["M110"]
    """Commands which need to always be send with a checksum."""

    helloCommand: str = "M110 N0"
    """Command to send in order to initiate a handshake with the printer."""

    suppressSecondHello: bool = False
    """Whether to suppress the second hello command. Might be required for some printer configurations with custom hello commands."""

    errorHandling: DisconnectCancelIgnoreEnum = "disconnect"
    """What to do when receiving unhandled errors from the printer."""

    terminalLogSize: int = 20
    """Size of log lines to keep for logging error context."""

    lastLineBufferSize: int = 50

    logResends: bool = True
    """Whether to log resends to octoprint.log or not. Invaluable debug tool without performance impact, leave on if possible please."""

    supportResendsWithoutOk: AlwaysDetectNeverEnum = "detect"
    """Whether to support resends without follow-up ok."""

    logPositionOnPause: bool = True
    """Whether to request and log the current position from the printer on a pause."""

    logPositionOnCancel: bool = False
    """Whether to request and log the current position from the printer on a cancel."""

    abortHeatupOnCancel: bool = True
    """Whether to send an abort heatup command on cancel."""

    waitForStartOnConnect: bool = False
    """Whether OctoPrint should wait for the ``start`` response from the printer before trying to send commands during connect."""

    waitToLoadSdFileList: bool = True
    """Specifies whether OctoPrint should wait to load the SD card file list until the first firmware capability report is processed."""

    sendChecksum: AlwaysPrintNeverEnum = "print"
    """Specifies when OctoPrint should send linenumber + checksum with every GCODE command."""

    sendChecksumWithUnknownCommands: bool = False
    r"""Specifies whether OctoPrint should also send linenumber + checksum with commands that are *not* detected as valid GCODE (as in, they do not match the regular expression ``^\s*([GM]\d+|T)``)."""

    unknownCommandsNeedAck: bool = False
    r"""Specifies whether OctoPrint should also use up acknowledgments (``ok``) for commands that are *not* detected as valid GCODE (as in, they do not match the regular expression ``^\s*([GM]\d+|T)``)."""

    sdRelativePath: bool = False
    """Specifies whether firmware expects relative paths for selecting SD files."""

    sdAlwaysAvailable: bool = False
    """Whether to always assume that an SD card is present in the printer. Needed by some firmwares which don't report the SD card status properly."""

    sdLowerCase: bool = False
    """Whether to treat all sd card file names as lower case"""

    sdCancelCommand: str = "M25"
    """Command to cancel SD prints"""

    maxNotSdPrinting: int = 2
    """Maximum number of 'Not SD Printing' messages to support before assuming the print was cancelled externally"""

    repetierTargetTemp: bool = False
    """Whether the printer sends repetier style target temperatures in the format ``TargetExtr0:<temperature>`` instead of attaching that information to the regular ``M105`` responses."""

    externalHeatupDetection: bool = True
    """
    Whether to enable external heatup detection (to detect heatup triggered e.g. through the printer's LCD panel or while
    printing from the printer's memory). Causes issues with Repetier's "first ok then response" approach to communication,
    so disable for printers running Repetier firmware.
    """

    supportWait: bool = True
    """Whether to support ``wait`` responses from the printer and interpret them as a call to send more commands."""

    ignoreIdenticalResends: bool = False
    """Whether to ignore identical resends from the printer (``true``, repetier) or not (``false``)."""

    identicalResendsCountdown: int = 7
    """If ``ignoreIdenticalResends`` is true, how many consecutive identical resends to ignore."""

    supportFAsCommand: bool = False
    """Whether to support ``F`` on its own as a valid GCODE command (``true``) or not (``false``)."""

    firmwareDetection: bool = True
    """Whether to attempt to auto detect the firmware of the printer and adjust settings accordingly (``true``) or not and rely on manual configuration (``false``)."""

    blockWhileDwelling: bool = False
    """Whether to block all sending to the printer while a ``G4`` (dwell) command is active (``true``, repetier) or not (``false``)."""

    useParityWorkaround: AlwaysDetectNeverEnum = "detect"
    """Whether to use the parity workaround needed for connecting to some printers."""

    maxConsecutiveResends: int = 10
    """Number of times to allow to resend the same line before the print job gets considered as failed."""

    sendM112OnError: bool = True
    """Whether to send an ``M112`` on encountered errors."""

    disableSdPrintingDetection: bool = False
    """Whether to disable the detection of SD print jobs triggered from the printer."""

    ackMax: int = 1
    """Maximum number of ``ok`` acknowledgements to keep active. **DO NOT TOUCH THIS!** Changes can cause completely broken communication."""

    sanityCheckTools: bool = True
    """Whether to senity check the tool count."""

    notifySuppressedCommands: InfoWarnNeverEnum = "warn"
    """Whether to notify about any suppressed commands."""

    capabilities: SerialCapabilities = SerialCapabilities()

    resendRatioThreshold: int = 10
    """Percentage of resend requests among all sent lines that should be considered critical."""

    resendRatioStart: int = 100
    """Initial resend ratio percentage"""

    ignoreEmptyPorts: bool = False
    """Whether to ignore that there are no serial ports detected or show a message"""

    encoding: str = "ascii"
    """
    Encoding to use when talking to a machine. ``ascii`` limits access to characters 0-127,
    ``latin_1`` enables access to the "extended" ascii characters 0-255. Other values can be used,
    see `Python's standard encodings <https://docs.python.org/3/library/codecs.html#standard-encodings>`_.
    """

    enableShutdownActionCommand: bool = False
    """Whether to enable support for the shutdown action command, allowing the printer to shut down OctoPrint and the system it's running on."""

    # command specific flags
    triggerOkForM29: bool = True
    """Whether to automatically trigger an ok for ``M29`` (a lot of versions of this command are buggy and the response skips on the ok)."""

    trustM73: bool = True
    """Whether to trust M73 in printed GCODE files for progress reporting."""
