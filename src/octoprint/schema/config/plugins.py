__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

from typing import Dict, List

from pydantic import BaseModel, Field

from octoprint.vendor.with_attrs_docs import with_attrs_docs


@with_attrs_docs
class PluginsConfig(BaseModel):
    disabled: List[str] = Field([], alias="_disabled")
    """Identifiers of installed but disabled plugins."""

    forced_compatible: List[str] = Field([], alias="_forcedCompatible")
    """Identifiers of plugins for which python compatibility information will be ignored and the plugin considered compatible in any case. Only for development, do **NOT** use in production."""

    sorting_order: Dict[str, Dict[str, int]] = Field({}, alias="_sortingOrder")
    """Custom sorting of hooks and implementations provided by plugins. Two-tiered dictionary structure, plugin identifier mapping to a dictionary of order overrides mapped by sorting context/hook name."""
