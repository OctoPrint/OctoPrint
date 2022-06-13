__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

from pydantic import BaseModel
from pydantic_settings import with_attrs_docs


@with_attrs_docs
class ApiConfig(BaseModel):
    allowCrossOrigin: bool = False
    """Whether to allow cross origin access to the API or not."""
