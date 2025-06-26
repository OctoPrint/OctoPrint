import warnings

warnings.warn(
    "octoprint.util.comm has been moved into the bundled plugin 'serial_connector' and direct access should be considered deprecated",
    DeprecationWarning,
    stacklevel=0,
)

from octoprint.plugins.serial_connector.serial_comm import *  # noqa: F403
