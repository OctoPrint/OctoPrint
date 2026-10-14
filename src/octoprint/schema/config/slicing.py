__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

from octoprint.schema import BaseModel


class SlicingConfig(BaseModel):
    enabled: bool = True
    """Whether to enable slicing support or not."""

    defaultSlicer: str | None = None
    """Default slicer to use."""

    defaultProfiles: dict[str, str] = {}
    """Default slicing profiles per slicer, maps slicer identifier to profile identifier."""
