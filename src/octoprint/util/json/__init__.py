__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"


import collections
import json

from frozendict import frozendict

from octoprint.util import to_str


def dump(obj):
    return json.dumps(
        obj,
        separators=(",", ":"),
        default=JsonEncoding.encode,
        allow_nan=False,
    )


class JsonEncoding:

    encoders = collections.OrderedDict()

    @classmethod
    def add_encoder(cls, type, encoder):
        cls.encoders[type] = encoder

    @classmethod
    def remove_encoder(cls, type):
        try:
            del cls.encoders[type]
        except KeyError:
            pass

    @classmethod
    def encode(cls, obj):
        for type, encoder in cls.encoders.items():
            if isinstance(obj, type):
                return encoder(obj)
        raise TypeError


JsonEncoding.add_encoder(frozendict, lambda obj: dict(obj))
JsonEncoding.add_encoder(bytes, lambda obj: to_str(obj))
