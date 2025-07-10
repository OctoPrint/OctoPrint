__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2025 The OctoPrint Project - Released under terms of the AGPLv3 License"

from typing import Any

from octoprint.schema import BaseModel
from octoprint.vendor.with_attrs_docs import with_attrs_docs


class PreferredConnection(BaseModel):
    connector: str
    parameters: dict[str, Any] = {}


@with_attrs_docs
class PrinterConnectionConfig(BaseModel):
    autorefresh: bool = True
    autorefreshInterval: int = 1

    autoconnect: bool = False

    preferred: PreferredConnection = PreferredConnection(
        connector="serial", parameters={"port": None, "baudrate": None}
    )
