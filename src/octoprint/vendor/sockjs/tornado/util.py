import functools
import sys

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

