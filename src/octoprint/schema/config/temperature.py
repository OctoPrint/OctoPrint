__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

from typing import List

from pydantic import BaseModel

from octoprint.vendor.with_attrs_docs import with_attrs_docs


@with_attrs_docs
class TemperatureProfile(BaseModel):
    name: str
    """Name of the profile."""

    extruder: int
    """Hotend temperature to set with the profile."""

    bed: int
    """Bed temperature to set with the profile."""


@with_attrs_docs
class TemperatureConfig(BaseModel):
    profiles: List[TemperatureProfile] = [
        TemperatureProfile(name="ABS", extruder=210, bed=100),
        TemperatureProfile(name="PLA", extruder=180, bed=60),
    ]
    """Temperature profiles to offer in the UI for quick pre-heating."""

    cutoff: int = 30
    """Cut off time for the temperature data, in minutes."""

    sendAutomatically: bool = False
    """Whether to send new temperature settings made in the UI automatically."""

    sendAutomaticallyAfter: int = 1
    """After what time to send the new temperature settings automatically, in seconds."""
