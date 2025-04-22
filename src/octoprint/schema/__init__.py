__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"


from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict
from pydantic import __version__ as pydantic_version

if pydantic_version.startswith("1."):
    # pydantic 1.x
    class BaseModel(PydanticBaseModel):
        class Config:
            use_enum_values = True

        def model_dump(self, *args, **kwargs):
            # not supported in pydantic 1.x
            kwargs.pop("mode", None)
            kwargs.pop("context", None)
            kwargs.pop("round_trip", None)
            kwargs.pop("warnings", None)
            kwargs.pop("serialize_as_any", None)

            return self.dict(*args, **kwargs)

        def model_dump_json(self, *args, **kwargs):
            # not supported in pydantic 1.x
            kwargs.pop("context", None)
            kwargs.pop("round_trip", None)
            kwargs.pop("warnings", None)
            kwargs.pop("serialize_as_any", None)

            return self.json(*args, **kwargs)

else:
    # pydantic 2.x
    from pydantic import ConfigDict

    class BaseModel(PydanticBaseModel):
        model_config = ConfigDict(use_enum_values=True, validate_default=True)
