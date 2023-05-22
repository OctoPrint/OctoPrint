__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

from typing import Dict, Optional

from octoprint.schema import BaseModel
from octoprint.vendor.with_attrs_docs import with_attrs_docs


@with_attrs_docs
class SlicingConfig(BaseModel):
    enabled: bool = True
    """Whether to enable slicing support or not."""

    defaultSlicer: Optional[str] = None
    """Default slicer to use."""

    defaultProfiles: Dict[str, str] = {}
    """Default slicing profiles per slicer, maps slicer identifier to profile identifier."""
