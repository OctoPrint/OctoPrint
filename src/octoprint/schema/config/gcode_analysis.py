__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

from enum import Enum

from pydantic import BaseModel

from octoprint.vendor.with_attrs_docs import with_attrs_docs


class RunAtEnum(str, Enum):
    never: str = "never"
    idle: str = "idle"
    always: str = "always"


@with_attrs_docs
class GcodeAnalysisConfig(BaseModel):
    maxExtruders: int = 10
    """Maximum number of extruders to support/to sanity check for."""

    throttle_normalprio: float = 0.01
    """Pause between each processed GCODE line batch in normal priority mode, seconds."""

    throttle_highprio: float = 0.0
    """Pause between each processed GCODE line batch in high priority mode (e.g. on fresh uploads), seconds."""

    throttle_lines: int = 100
    """GCODE line batch size."""

    runAt: RunAtEnum = "idle"
    """Whether to run the analysis only when idle (not printing), regardless of printing state or never."""

    bedZ: float = 0.0
    """Z position considered the location of the bed."""
