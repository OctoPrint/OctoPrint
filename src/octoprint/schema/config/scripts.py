__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

from typing import Dict, Optional

from pydantic import BaseModel

from octoprint.vendor.with_attrs_docs import with_attrs_docs


@with_attrs_docs
class GcodeScriptsConfig(BaseModel):
    afterPrinterConnected: Optional[str] = None
    beforePrinterDisconnected: Optional[str] = None
    beforePrintStarted: Optional[str] = None
    afterPrintCancelled: Optional[
        str
    ] = "; disable motors\nM84\n\n;disable all heaters\n{% snippet 'disable_hotends' %}\n{% snippet 'disable_bed' %}\n;disable fan\nM106 S0"
    afterPrintDone: Optional[str] = None
    beforePrintPaused: Optional[str] = None
    afterPrintResumed: Optional[str] = None
    beforeToolChange: Optional[str] = None
    afterToolChange: Optional[str] = None
    snippets: Dict[str, str] = {
        "disable_hotends": "{% if printer_profile.extruder.sharedNozzle %}M104 T0 S0\n{% else %}{% for tool in range(printer_profile.extruder.count) %}M104 T{{ tool }} S0\n{% endfor %}{% endif %}",
        "disable_bed": "{% if printer_profile.heatedBed %}M140 S0\n{% endif %}",
    }


@with_attrs_docs
class ScriptsConfig(BaseModel):
    gcode: GcodeScriptsConfig = GcodeScriptsConfig()
