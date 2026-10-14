__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

from octoprint.schema import BaseModel


class FolderConfig(BaseModel):
    uploads: str | None = None
    """Absolute path where to store gcode uploads. Defaults to the ``uploads`` folder in OctoPrint's base folder."""

    timelapse: str | None = None
    """Absolute path where to store finished timelapse recordings. Defaults to the ``timelapse`` folder in OctoPrint's base folder."""

    timelapse_tmp: str | None = None
    """Absolute path where to store temporary timelapse snapshots. Defaults to the ``timelapse/tmp`` folder in OctoPrint's base folder."""

    logs: str | None = None
    """Absolute path where to store logs. Defaults to the ``logs`` folder in OctoPrint's base folder."""

    virtualSd: str | None = None
    """Absolute path where to store the virtual printer's SD card files. Defaults to the ``virtualSd`` folder in OctoPrint's base folder."""

    watched: str | None = None
    """Absolute path to the watched folder. Defaults to the ``watched`` folder in OctoPrint's base folder."""

    plugins: str | None = None
    """Absolute path where to locate and install single file plugins. Defaults to the ``plugins`` folder in OctoPrint's base folder."""

    slicingProfiles: str | None = None
    """Absolute path where to store slicing profiles. Defaults to the ``slicingProfiles`` folder in OctoPrint's base folder."""

    printerProfiles: str | None = None
    """Absolute path where to store printer profiles. Defaults to the ``printerProfiles`` folder in OctoPrint's base folder."""

    scripts: str | None = None
    """Absolute path where to store (GCODE) scripts. Defaults to the ``scripts`` folder in OctoPrint's base folder."""

    translations: str | None = None
    """Absolute path where to store additional translations. Defaults to the ``translations`` folder in OctoPrint's base folder."""

    generated: str | None = None
    """Absolute path where to store generated files. Defaults to the ``generated`` folder in OctoPrint's base folder."""

    data: str | None = None
    """Absolute path where to store additional data. Defaults to the ``data`` folder in OctoPrint's base folder."""

    uploadtemp: str | None = None
    """Absolute path to use for buffering uploads so that they don't have to be held in memory."""
