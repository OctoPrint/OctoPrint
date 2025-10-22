__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

from typing import Optional

from octoprint.schema import BaseModel
from octoprint.vendor.with_attrs_docs import with_attrs_docs


@with_attrs_docs
class GcodeScriptsConfig(BaseModel):
    afterPrinterConnected: Optional[str] = None
    """Script run after the connection to the printer has been established."""

    beforePrinterDisconnected: Optional[str] = None
    """Script run before the printer gets disconnected."""

    beforePrintStarted: Optional[str] = None
    """Script run before a print job is started."""

    afterPrintCancelled: Optional[str] = (
        "; disable motors\nM84\n\n;disable all heaters\n{% snippet 'disable_hotends' %}\n{% snippet 'disable_bed' %}\n;disable fan\nM106 S0"
    )
    """Script run after a print job has been cancelled."""

    afterPrintDone: Optional[str] = None
    """Script run after a print job completes."""

    beforePrintPaused: Optional[str] = None
    """Script run on pausing a print job."""

    afterPrintResumed: Optional[str] = None
    """Script run on resuming a print job."""

    beforeToolChange: Optional[str] = None
    """Script run before sending a tool change command to the printer."""

    afterToolChange: Optional[str] = None
    """Script run after sending a tool change command to the printer."""

    snippets: dict[str, str] = {
        "disable_hotends": "{% if printer_profile.extruder.sharedNozzle %}M104 T0 S0\n{% else %}{% for tool in range(printer_profile.extruder.count) %}M104 T{{ tool }} S0\n{% endfor %}{% endif %}",
        "disable_bed": "{% if printer_profile.heatedBed %}M140 S0\n{% endif %}",
    }
    """Additional snippets that can be used in other scripts."""


@with_attrs_docs
class ScriptsConfig(BaseModel):
    gcode: GcodeScriptsConfig = GcodeScriptsConfig()
    """GCODE scripts configuration"""
