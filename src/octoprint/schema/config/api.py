__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

from typing import Dict

from pydantic import BaseModel

from octoprint.vendor.with_attrs_docs import with_attrs_docs


@with_attrs_docs
class ApiConfig(BaseModel):
    key: str = None
    """Global API key, deprecated, use User API keys instead. Unset by default, will be generated on first run."""

    apps: Dict[str, str] = {}

    allowCrossOrigin: bool = False
    """Whether to allow cross origin access to the API or not."""
