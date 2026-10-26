__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

from octoprint.schema import BaseModel


class GcodeScriptsConfig(BaseModel):
    afterPrinterConnected: str | None = None
    """Script run after the connection to the printer has been established."""

    beforePrinterDisconnected: str | None = None
    """Script run before the printer gets disconnected."""

    beforePrintStarted: str | None = None
    """Script run before a print job is started."""

    afterPrintCancelled: str | None = (
        "; disable motors\nM84\n\n;disable all heaters\n{% snippet 'disable_hotends' %}\n{% snippet 'disable_bed' %}\n;disable fan\nM106 S0"
    )
    """Script run after a print job has been cancelled."""

    afterPrintDone: str | None = None
    """Script run after a print job completes."""

    beforePrintPaused: str | None = None
    """Script run on pausing a print job."""

    afterPrintResumed: str | None = None
    """Script run on resuming a print job."""

    beforeToolChange: str | None = None
    """Script run before sending a tool change command to the printer."""

    afterToolChange: str | None = None
    """Script run after sending a tool change command to the printer."""

    snippets: dict[str, str] = {
        "disable_hotends": "{% if printer_profile.extruder.sharedNozzle %}M104 T0 S0\n{% else %}{% for tool in range(printer_profile.extruder.count) %}M104 T{{ tool }} S0\n{% endfor %}{% endif %}",
        "disable_bed": "{% if printer_profile.heatedBed %}M140 S0\n{% endif %}",
    }
    """Additional snippets that can be used in other scripts."""


class ScriptsConfig(BaseModel):
    gcode: GcodeScriptsConfig = GcodeScriptsConfig()
    """GCODE scripts configuration"""
