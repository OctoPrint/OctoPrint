__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

from typing import List, Optional

from pydantic import Field

from octoprint.schema import BaseModel
from octoprint.vendor.with_attrs_docs import with_attrs_docs


@with_attrs_docs
class ActionConfig(BaseModel):
    action: str
    """The identifier used internally to identify the action. Set to `divider` to generate a divider in the menu."""

    name: Optional[str] = None
    """The name of the action that will be shown on the menu. Must be set if the action is not a divider."""

    command: Optional[str] = None
    """The command to execute when the action is selected. Must be set if the action is not a divider."""

    async_: bool = Field(False, alias="async")
    """Whether to run the command asynchronously."""

    confirm: Optional[str] = None
    """An optional confirmation message to show before executing the command."""


@with_attrs_docs
class SystemConfig(BaseModel):
    actions: List[ActionConfig] = []
    """A list of system actions to show in the UI."""
