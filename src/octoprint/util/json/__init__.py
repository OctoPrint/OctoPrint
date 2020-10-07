# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"


import collections

import frozendict

from octoprint.util import to_unicode


class JsonEncoding(object):

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


JsonEncoding.add_encoder(frozendict.frozendict, lambda obj: dict(obj))
JsonEncoding.add_encoder(bytes, lambda obj: to_unicode(obj))
