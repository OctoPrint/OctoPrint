# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import functools
import sys

PY3 = sys.version_info[0] == 3

from past.builtins import unicode

if PY3:
    MAXSIZE = sys.maxsize

    def bytes_to_str(b):
        if isinstance(b, bytes):
            return b.decode('utf8')
        return b

    def str_to_bytes(s):
        if isinstance(s, bytes):
            return s
        return s.encode('utf8')

    import urllib.parse
    unquote_plus = urllib.parse.unquote_plus
else:
    if sys.platform == "java":
        # Jython always uses 32 bits.
        MAXSIZE = int((1 << 31) - 1)
    else:
        # It's possible to have sizeof(long) != sizeof(Py_ssize_t).
        class X(object):
            def __len__(self):
                return 1 << 31
        try:
            len(X())
        except OverflowError:
            # 32-bit
            MAXSIZE = int((1 << 31) - 1)
        else:
            # 64-bit
            MAXSIZE = int((1 << 63) - 1)
            del X

    def bytes_to_str(s):
        if isinstance(s, bytes):
            return s.decode('utf-8')
        return s

    def str_to_bytes(s):
        if isinstance(s, unicode):
            return s.encode('utf8')
        return s

    import urllib
    unquote_plus = urllib.unquote_plus

def no_auto_finish(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        self._auto_finish = False
        return method(self, *args, **kwargs)
    return wrapper

def get_current_ioloop():
    import asyncio

    from tornado.ioloop import IOLoop

    try:
        loop = asyncio.get_running_loop()
        return IOLoop._ioloop_for_asyncio.get(loop)
    except RuntimeError:
        # no current loop
        return None

