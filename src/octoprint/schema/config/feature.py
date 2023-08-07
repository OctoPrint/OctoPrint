__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

from typing import List

from octoprint.schema import BaseModel
from octoprint.vendor.with_attrs_docs import with_attrs_docs


@with_attrs_docs
class FeatureConfig(BaseModel):
    temperatureGraph: bool = True
    """Whether to enable the temperature graph in the UI or not."""

    sdSupport: bool = True
    """Specifies whether support for SD printing and file management should be enabled."""

    keyboardControl: bool = True
    """Whether to enable the keyboard control feature in the control tab."""

    pollWatched: bool = False
    """Whether to actively poll the watched folder (true) or to rely on the OS's file system notifications instead (false)."""

    modelSizeDetection: bool = True
    """Whether to enable model size detection and warning (true) or not (false)."""

    rememberFileFolder: bool = False
    """Whether to remember the selected folder on the file manager."""

    printStartConfirmation: bool = False
    """Whether to show a confirmation on print start (true) or not (false)"""

    printCancelConfirmation: bool = True
    """Whether to show a confirmation on print cancelling (true) or not (false)"""

    uploadOverwriteConfirmation: bool = True

    autoUppercaseBlacklist: List[str] = ["M117", "M118"]
    """Commands that should never be auto-uppercased when sent to the printer through the Terminal tab."""

    g90InfluencesExtruder: bool = False
    """Whether `G90`/`G91` also influence absolute/relative mode of extruders."""

    enforceReallyUniversalFilenames: bool = False
    """Replace all special characters and spaces with text equivalent to make them universally compatible. Most OS filesystems work fine with unicode characters, but just in case you can revert to the older behaviour by setting this to true."""

    enableDragDropUpload: bool = True
    """Enable drag and drop upload overlay"""
