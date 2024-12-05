import warnings

warnings.warn(
    "octoprint.util.comm has been renamed to octoprint.printer.connection.serial.comm",
    DeprecationWarning,
    stacklevel=0,
)

from octoprint.printer.connection.serial.comm import *  # noqa: F403
