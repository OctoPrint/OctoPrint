__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

from enum import Enum
from typing import List, Optional

from octoprint.schema import BaseModel
from octoprint.vendor.with_attrs_docs import with_attrs_docs


class SubscriptionTypeEnum(str, Enum):
    system = "system"
    gcode = "gcode"


@with_attrs_docs
class EventSubscription(BaseModel):
    event: str
    """The event to subscribe to."""

    name: Optional[str] = None
    """The event name to show on the UI"""

    command: str
    """The command to execute when the event is triggered, either a GCODE or a system command."""

    type: SubscriptionTypeEnum
    """The type of the command."""

    enabled: bool = True
    """Whether the event subscription should be enabled."""

    debug: bool = False
    """If set to `true`, OctoPrint will log the command after performing all placeholder replacements."""


@with_attrs_docs
class EventsConfig(BaseModel):
    enabled: bool = True
    """Whether event subscriptions should be enabled or not."""

    subscriptions: List[EventSubscription] = []
    """A list of event subscriptions."""
