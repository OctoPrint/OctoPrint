__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

from enum import Enum
from typing import List, Optional

from octoprint.schema import BaseModel
from octoprint.vendor.with_attrs_docs import with_attrs_docs


class AlwaysDetectNeverEnum(str, Enum):
    always = "always"
    detect = "detect"
    never = "never"


class InfoWarnNeverEnum(str, Enum):
    info = "info"
    warn = "warn"
    never = "never"


@with_attrs_docs
class SerialTimeoutConfig(BaseModel):
    detectionFirst: float = 10.0
    detectionConsecutive: float = 2.0

    connection: float = 10.0
    """Timeout for waiting to establish a connection with the selected port, in seconds"""

    communication: float = 30.0
    """Timeout during serial communication, in seconds"""

    communicationBusy: float = 3.0
    """Timeout during serial communication when busy protocol support is detected, in seconds"""

    temperature: float = 5.0
    """Timeout after which to query temperature when no target is set"""

    temperatureTargetSet: float = 2.0
    """Timeout after which to query temperature when a target is set"""

    temperatureAutoreport: float = 2.0

    sdStatus: float = 1.0
    """Timeout after which to query the SD status while SD printing"""

    sdStatusAutoreport: float = 1.0
    posAutoreport: float = 5.0
    resendOk: float = 0.5
    baudrateDetectionPause: float = 1.0
    positionLogWait: float = 10.0


@with_attrs_docs
class SerialMaxTimeouts(BaseModel):
    idle: int = 2
    """Max. timeouts when the printer is idle"""

    printing: int = 5
    """Max. timeouts when the printer is printing"""

    long: int = 5
    """Max. timeouts when a long running command is active"""


@with_attrs_docs
class SerialCapabilities(BaseModel):
    autoreport_temp: bool = True
    """Whether to enable temperature autoreport in the firmware if its support is detected"""

    autoreport_sdstatus: bool = True
    """Whether to enable SD printing autoreport in the firmware if its support is detected"""

    autoreport_pos: bool = True
    """Whether to enable position autoreport in the firmware if its support is detected"""

    busy_protocol: bool = True
    """Whether to shorten the communication timeout if the firmware seems to support the busy protocol"""

    emergency_parser: bool = True
    """Whether to send emergency commands out of band if the firmware seems to support the emergency parser"""

    extended_m20: bool = True
    """Whether to request extended M20 (file list) output from the firmware if its support is detected"""

    lfn_write: bool = True
    """Whether to enable long filename support for SD card writes if the firmware reports support for it"""


@with_attrs_docs
class SerialConfig(BaseModel):
    port: Optional[str] = None
    """The default port to use to connect to the printer. If unset or set to `AUTO`, the port will be auto-detected."""

    baudrate: Optional[int] = None
    """The default baudrate to use to connect to the printer. If unset or set to 0, the baudrate will be auto-detected."""

    exclusive: bool = True
    """Whether to request the serial port exclusively or not"""

    lowLatency: bool = False
    """Whether to request low latency mode on the serial port or not"""

    autoconnect: bool = False
    """Whether to try to automatically connect to the printer on startup or not"""

    autorefresh: bool = True
    """Whether to automatically refresh the port list while no connection is established"""

    autorefreshInterval: int = 1
    """Interval in seconds at which to refresh the port list while no connection is established"""

    log: bool = False
    """Whether to log whole communication to serial.log (warning: might decrease performance)"""

    timeout: SerialTimeoutConfig = SerialTimeoutConfig()
    """Timeouts used for the serial connection to the printer, you might want to adjust these if you are experiencing connection problems"""

    maxCommunicationTimeouts: SerialMaxTimeouts = SerialMaxTimeouts()

    maxWritePasses: int = 5
    """Maximum number of write attempts to serial during which nothing can be written before the communication with the printer is considered dead and OctoPrint will disconnect with an error"""

    additionalPorts: List[str] = []
    """Use this to define additional patterns to consider for serial port listing. Must be a valid ["glob" pattern](http://docs.python.org/3/library/glob.html)"""

    additionalBaudrates: List[int] = []
    """Use this to define additional baud rates to offer for connecting to serial ports. Must be a valid integer"""

    blacklistedPorts: List[str] = []
    blacklistedBaudrates: List[int] = []

    longRunningCommands: List[str] = [
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

    blockedCommands: List[str] = ["M0", "M1"]
    """Commands which should not be sent to the printer, e.g. because they are known to block serial communication until physical interaction with the printer as is the case on most firmwares with the default M0 and M1."""

    ignoredCommands: List[str] = []
    """Commands which should not be sent to the printer and just silently ignored. An example of when you may wish to use this could be useful if you wish to manually change a filament on M600, by using that as a Pausing command."""

    pausingCommands: List[str] = ["M0", "M1", "M25"]
    """Commands which should cause OctoPrint to pause any ongoing prints."""

    emergencyCommands: List[str] = ["M112", "M108", "M410"]

    checksumRequiringCommands: List[str] = ["M110"]
    """Commands which need to always be send with a checksum."""

    helloCommand: str = "M110 N0"
    """Command to send in order to initiate a handshake with the printer."""

    disconnectOnErrors: bool = True
    """Whether to disconnect from the printer on errors or not."""

    ignoreErrorsFromFirmware: bool = False
    """Whether to completely ignore errors from the firmware or not."""

    terminalLogSize: int = 20
    lastLineBufferSize: int = 50

    logResends: bool = True
    """Whether to log resends to octoprint.log or not. Invaluable debug tool without performance impact, leave on if possible please."""

    supportResendsWithoutOk: AlwaysDetectNeverEnum = "detect"
    """Whether to support resends without follow-up ok or not."""

    logPositionOnPause: bool = True
    logPositionOnCancel: bool = False
    abortHeatupOnCancel: bool = True

    waitForStartOnConnect: bool = False
    """Whether OctoPrint should wait for the `start` response from the printer before trying to send commands during connect."""

    waitToLoadSdFileList: bool = True
    """Specifies whether OctoPrint should wait to load the SD card file list until the first firmware capability report is processed."""

    alwaysSendChecksum: bool = False
    """Specifies whether OctoPrint should send linenumber + checksum with every printer command. Needed for successful communication with Repetier firmware."""

    neverSendChecksum: bool = False

    sendChecksumWithUnknownCommands: bool = False
    r"""Specifies whether OctoPrint should also send linenumber + checksum with commands that are *not* detected as valid GCODE (as in, they do not match the regular expression `^\s*([GM]\d+|T)`)."""

    unknownCommandsNeedAck: bool = False
    r"""Specifies whether OctoPrint should also use up acknowledgments (`ok`) for commands that are *not* detected as valid GCODE (as in, they do not match the regular expression `^\s*([GM]\d+|T)`)."""

    sdRelativePath: bool = False
    """Specifies whether firmware expects relative paths for selecting SD files."""

    sdAlwaysAvailable: bool = False
    """Whether to always assume that an SD card is present in the printer. Needed by some firmwares which don't report the SD card status properly."""

    sdLowerCase: bool = False
    sdCancelCommand: str = "M25"
    maxNotSdPrinting: int = 2
    swallowOkAfterResend: bool = True

    repetierTargetTemp: bool = False
    """Whether the printer sends repetier style target temperatures in the format `TargetExtr0:<temperature>` instead of attaching that information to the regular `M105` responses."""

    externalHeatupDetection: bool = True
    """Whether to enable external heatup detection (to detect heatup triggered e.g. through the printer's LCD panel or while printing from SD) or not. Causes issues with Repetier's "first ok then response" approach to communication, so disable for printers running Repetier firmware."""

    supportWait: bool = True

    ignoreIdenticalResends: bool = False
    """Whether to ignore identical resends from the printer (true, repetier) or not (false)."""

    identicalResendsCountdown: int = 7
    """If `ignoreIdenticalResends` is true, how many consecutive identical resends to ignore."""

    supportFAsCommand: bool = False
    """Whether to support `F` on its own as a valid GCODE command (true) or not (false)."""

    firmwareDetection: bool = True
    """Whether to attempt to auto detect the firmware of the printer and adjust settings accordingly (true) or not and rely on manual configuration (false)."""

    blockWhileDwelling: bool = False
    """Whether to block all sending to the printer while a G4 (dwell) command is active (true, repetier) or not (false)."""

    useParityWorkaround: AlwaysDetectNeverEnum = "detect"
    maxConsecutiveResends: int = 10
    sendM112OnError: bool = True
    disableSdPrintingDetection: bool = False
    ackMax: int = 1
    sanityCheckTools: bool = True
    notifySuppressedCommands: InfoWarnNeverEnum = "warn"
    capabilities: SerialCapabilities = SerialCapabilities()

    resendRatioThreshold: int = 10
    """Percentage of resend requests among all sent lines that should be considered critical."""

    resendRatioStart: int = 100
    ignoreEmptyPorts: bool = False

    encoding: str = "ascii"
    """Encoding to use when talking to a machine. `ascii` limits access to characters 0-127, `latin_1` enables access to the "extended" ascii characters 0-255. Other values can be used, see [Python's standard encodings](https://docs.python.org/3/library/codecs.html#standard-encodings)."""

    enableShutdownActionCommand: bool = False
    """Whether to enable support for the shutdown action command, allowing the printer to shut down OctoPrint and the system it's running on."""

    # command specific flags
    triggerOkForM29: bool = True
    """Whether to automatically trigger an ok for `M29` (a lot of versions of this command are buggy and the response skips on the ok)."""
