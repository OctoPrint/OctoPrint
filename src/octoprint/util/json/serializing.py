__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

import base64
import datetime
import json
import time
from collections import OrderedDict
from typing import Any, Callable, Dict, List

try:
    from typing import OrderedDict as OrderedDictType
except ImportError:
    OrderedDictType = Dict  # py3.7.{0,1}

from frozendict import frozendict

from .encoding import JsonEncoding


class SerializableJsonEncoding(JsonEncoding):
    """
    A JSON encoding that can serialize and deserialize objects, including additional
    objects otherwise not serializable by the standard JSON encoder:

      * ``bytes``
      * ``frozendict.frozendict``
      * ``datetime.datetime``
      * ``time.struct_time``
    """

    encoders: OrderedDictType[type, Callable[[Any], Any]] = OrderedDict()
    decoders: OrderedDictType[str, Callable[[dict], object]] = OrderedDict()

    @classmethod
    def add_decoder(cls, classname, decoder):
        cls.decoders[classname] = decoder

    @classmethod
    def remove_decoder(cls, classname):
        try:
            del cls.decoders[classname]
        except KeyError:
            pass

    @classmethod
    def dumps(cls, obj: Any) -> str:
        return json.dumps(
            cls.encode(obj), separators=(",", ":"), indent=None, allow_nan=False
        )

    @classmethod
    def loads(cls, s: str) -> Any:
        return json.loads(s, object_hook=cls.decode)

    @classmethod
    def encode(cls, val):
        """
        Recursively replace all instances of encodable types with their encoded
        value. This is useful over the ``default=`` functionallity of the JSON
        encoder because JSON will not call default for tuples, lists, ints, etc:
        https://docs.python.org/3/library/json.html#json.JSONEncoder

        Cannot handle circular references.
        """

        if isinstance(val, tuple(cls.encoders.keys())):
            # we can't directly index into the encoders dict because
            # we need to be able to handle subclasses
            encoder = next(
                encoder for typ, encoder in cls.encoders.items() if isinstance(val, typ)
            )
            return cls.encode(encoder(val))
        elif isinstance(val, dict):
            return {k: cls.encode(v) for k, v in val.items()}
        elif isinstance(val, (tuple, list)):
            return [cls.encode(v) for v in val]
        elif isinstance(val, (bool, int, float, str)) or val is None:
            return val
        else:
            raise TypeError(f"Unserializable type {type(val)}")

    @classmethod
    def decode(cls, dct):
        """
        Recursively replace all instances of decodable types with their decoded
        values.

        You'll want to have used ``class_encode()`` in your encoder to get this
        to work properly.
        """
        if "__jsonclass__" not in dct:
            return dct

        if len(dct["__jsonclass__"]) == 0:
            raise ValueError("__jsonclass__ must not be empty")

        decoded_name = dct["__jsonclass__"][0]
        params = dct["__jsonclass__"][1:]

        for classname, decoder in cls.decoders.items():
            if decoded_name == classname:
                return decoder(*params)
        return dct


def class_encode(name: str, *params: Any) -> Dict[str, List]:
    """
    Encode a class name and parameters into a serializable dict. You'll
    probably want to use this if you're going to set a custom decoder.

    This stores the class names in a format inspired by the JSON-RPC spec at
    https://www.jsonrpc.org/specification_v1#a3.JSONClasshinting
    """
    return {"__jsonclass__": [name] + list(params)}


# frozendict

SerializableJsonEncoding.add_encoder(
    frozendict, lambda obj: class_encode("frozendict.frozendict", dict(obj))
)
SerializableJsonEncoding.add_decoder("frozendict.frozendict", lambda obj: frozendict(obj))

# bytes

SerializableJsonEncoding.add_encoder(
    bytes, lambda obj: class_encode("bytes", base64.b85encode(obj).decode("ascii"))
)
SerializableJsonEncoding.add_decoder("bytes", lambda obj: base64.b85decode(obj))

# time.struct_time


def _struct_time_decoder(params):
    if len(params) == 9 and all(isinstance(p, int) and p >= 0 for p in params):
        return time.struct_time(params)
    raise ValueError(f"Invalid time.struct_time params `{params}`")


SerializableJsonEncoding.add_encoder(
    time.struct_time, lambda obj: class_encode("time.struct_time", list(obj))
)
SerializableJsonEncoding.add_decoder("time.struct_time", _struct_time_decoder)

# datetime.datetime

SerializableJsonEncoding.add_encoder(
    datetime.datetime, lambda obj: class_encode("datetime.datetime", obj.isoformat())
)
SerializableJsonEncoding.add_decoder(
    "datetime.datetime", lambda params: datetime.datetime.fromisoformat(params)
)

# shortcut for dumps and loads

dumps = SerializableJsonEncoding.dumps
loads = SerializableJsonEncoding.loads
