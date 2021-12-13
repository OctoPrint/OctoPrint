# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2021 The OctoPrint Project - Released under terms of the AGPLv3 License"


import io


def _validate(module, name, allowed=None):
    if allowed is None:
        return None
    return allowed.get((module, name), None)


try:
    import cPickle as pickle  # Python 2

    def safe_load(f, allowed=None):
        unpickler = pickle.Unpickler(f)
        unpickler.find_global = lambda m, n: _validate(m, n, allowed=allowed)
        return unpickler.load()

    def safe_loads(s, allowed=None):
        return safe_load(io.BytesIO(s), allowed=allowed)


except ImportError:
    import pickle  # Python 3

    class RestrictedUnpickler(pickle.Unpickler):
        def __init__(self, f, *args, **kwargs):
            self.allowed = kwargs.get("allowed")
            super(RestrictedUnpickler, self).__init__(f, *args, **kwargs)

        def find_class(self, module, name):
            return _validate(module, name, allowed=self.allowed)

    def safe_load(f, allowed=None):
        return RestrictedUnpickler(f, allowed=allowed).load()

    def safe_loads(s, allowed=None):
        return safe_load(io.BytesIO(s), allowed=allowed)


dump = pickle.dump
dumps = pickle.dumps
