__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

import json
from collections import OrderedDict
from typing import Any, Callable, Dict

try:
    from typing import OrderedDict as OrderedDictType
except ImportError:
    OrderedDictType = Dict  # py3.7.{0,1}

from frozendict import frozendict

from octoprint.util import to_unicode


class JsonEncoding:
    encoders: OrderedDictType[type, Callable[[Any], Any]] = OrderedDict()

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
    def dumps(cls, obj: Any) -> str:
        """
        Dump an object to JSON, handles additional types that the JSON encoder can't, like
        bytes and frozendicts.
        """
        return json.dumps(
            obj,
            default=cls.encode,
            separators=(",", ":"),
            indent=None,
            allow_nan=False,
        )

    @classmethod
    def loads(cls, s: str) -> Any:
        return json.loads(s)

    @classmethod
    def encode(cls, obj):
        for type, encoder in cls.encoders.items():
            if isinstance(obj, type):
                return encoder(obj)
        raise TypeError(f"Unserializable type {type(obj)}")


JsonEncoding.add_encoder(frozendict, lambda obj: dict(obj))
JsonEncoding.add_encoder(bytes, lambda obj: to_unicode(obj))

dumps = JsonEncoding.dumps
loads = JsonEncoding.loads
