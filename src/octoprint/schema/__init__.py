__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"


from pydantic import BaseModel as PydanticBaseModel

try:
    # pydantic 2.x
    import pydantic.v1 as pydantic_v1  # noqa: F401

    del pydantic_v1

    from pydantic import ConfigDict

    class BaseModel(PydanticBaseModel):
        model_config = ConfigDict(use_enum_values=True)

except ImportError:
    # pydantic 1.x

    class BaseModel(PydanticBaseModel):
        class Config:
            use_enum_values = True

        def model_dump(self, *args, **kwargs):
            # not supported in pydantic 1.x
            kwargs.pop("mode")
            kwargs.pop("context")
            kwargs.pop("round_trip")
            kwargs.pop("warnings")
            kwargs.pop("serialize_as_any")

            return self.dict(*args, **kwargs)
