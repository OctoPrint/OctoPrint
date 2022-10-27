__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

from typing import Optional

from octoprint.schema import BaseModel
from octoprint.vendor.with_attrs_docs import with_attrs_docs


@with_attrs_docs
class FolderConfig(BaseModel):
    uploads: Optional[str] = None
    """Absolute path where to store gcode uploads. Defaults to the `uploads` folder in OctoPrint's base folder."""

    timelapse: Optional[str] = None
    """Absolute path where to store finished timelase recordings. Defaults to the `timelapse` folder in OctoPrint's base folder."""

    timelapse_tmp: Optional[str] = None
    """Absolute path where to store temporary timelapse snapshots. Defaults to the `timelapse/tmp` folder in OctoPrint's base folder."""

    logs: Optional[str] = None
    """Absolute path where to store logs. Defaults to the `logs` folder in OctoPrint's base folder."""

    virtualSd: Optional[str] = None
    """Absolute path where to store the virtual printer's SD card files. Defaults to the `virtualSd` folder in OctoPrint's base folder."""

    watched: Optional[str] = None
    """Absolute path to the watched folder. Defaults to the `watched` folder in OctoPrint's base folder."""

    plugins: Optional[str] = None
    """Absolute path where to locate and install single file plugins. Defaults to the `plugins` folder in OctoPrint's base folder."""

    slicingProfiles: Optional[str] = None
    """Absolute path where to store slicing profiles. Defaults to the `slicingProfiles` folder in OctoPrint's base folder."""

    printerProfiles: Optional[str] = None
    """Absolute path where to store printer profiles. Defaults to the `printerProfiles` folder in OctoPrint's base folder."""

    scripts: Optional[str] = None
    """Absolute path where to store (GCODE) scripts. Defaults to the `scripts` folder in OctoPrint's base folder."""

    translations: Optional[str] = None
    """Absolute path where to store additional translations. Defaults to the `translations` folder in OctoPrint's base folder."""

    generated: Optional[str] = None
    """Absolute path where to store generated files. Defaults to the `generated` folder in OctoPrint's base folder."""

    data: Optional[str] = None
    """Absolute path where to store additional data. Defaults to the `data` folder in OctoPrint's base folder."""
