__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

import json
import time
import typing
from collections import OrderedDict
from typing import Any, Callable

from frozendict import frozendict

from octoprint.util import to_unicode


def dumps(obj: Any) -> str:
    """
    Dump an object to JSON, handles additional types that the JSON encoder can't, like
    datetime.struct_time, bytes, and frozendicts.

    Cannot handle circular references.

    Note: at the moment, datetime.struct_time are only supported if they are in dicts
    """
    return json.dumps(
        JsonEncoding.encode(obj),
        separators=(",", ":"),
        indent=None,
        allow_nan=False,
    )


def loads(s: str) -> Any:
    return json.loads(s, object_hook=JsonEncoding.decode)


class JsonEncoding:
    decoders: typing.OrderedDict[str, Callable[[dict], object]] = OrderedDict()
    encoders: typing.OrderedDict[type, Callable[[Any], Any]] = OrderedDict()

    @classmethod
    def add_encoder(cls, typ: type, encoder: Callable[[Any], Any]) -> None:
        """
        Add an encoder for a type.

        :param typ: the type to add an encoder for
        :param encoder: the encoder. Must take a single argument and return a
            tuple (name, parameters...)
        """
        cls.encoders[typ] = encoder

    @classmethod
    def remove_encoder(cls, typ):
        try:
            del cls.encoders[typ]
        except KeyError:
            pass

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


def class_encode(name: str, *params: Any):
    """
    Encode a class name and parameters into a serializable dict. You'll
    probably want to use this if you're going to set a custom decoder.

    This stores the class names in a format inspired by the JSON-RPC spec at
    https://www.jsonrpc.org/specification_v1#a3.JSONClasshinting
    """
    return {"__jsonclass__": [name] + list(params)}


JsonEncoding.add_encoder(frozendict, lambda obj: dict(obj))
JsonEncoding.add_encoder(bytes, lambda obj: to_unicode(obj))


def _struct_time_decoder(params):
    if len(params) == 9 and all(isinstance(p, int) and p >= 0 for p in params):
        return time.struct_time(params)
    raise ValueError(f"Invalid time.struct_time params `{params}`")


JsonEncoding.add_encoder(
    time.struct_time, lambda obj: class_encode("struct_time", list(obj))
)
JsonEncoding.add_decoder("struct_time", _struct_time_decoder)
