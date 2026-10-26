__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

from pydantic import Field

from octoprint.schema import BaseModel


class ActionConfig(BaseModel):
    action: str
    """The identifier used internally to identify the action. Set to ``divider`` to generate a divider in the menu."""

    name: str | None = None
    """The name of the action that will be shown on the menu. Must be set if the action is not a divider."""

    command: str | None = None
    """The command to execute when the action is selected. Must be set if the action is not a divider."""

    async_: bool = Field(False, alias="async")
    """Whether to run the command asynchronously."""

    confirm: str | None = None
    """An optional confirmation message to show before executing the command."""

    fresh_credentials: bool | None = False
    """Whether to require a fresh credential check for executing the command."""


class SystemConfig(BaseModel):
    actions: list[ActionConfig] = []
    """A list of system actions to show in the UI."""
