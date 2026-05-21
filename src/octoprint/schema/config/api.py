__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

from octoprint.schema import BaseModel


class ApiConfig(BaseModel):
    apps: dict[str, str] = {}

    allowCrossOrigin: bool = False
    """Whether to allow cross origin access to the API or not."""
