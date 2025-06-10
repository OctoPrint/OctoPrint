__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"


from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict


class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(use_enum_values=True, validate_default=True)


class BaseModelExtra(PydanticBaseModel):
    model_config = ConfigDict(use_enum_values=True, validate_default=True, extra="allow")
