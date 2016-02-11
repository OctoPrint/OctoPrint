"""Caches are used for multiple things:

    - To speed up asset building. Filter operations every step
      of the way can be cached, so that individual parts of a
      build that haven't changed can be reused.

    - Bundle definitions are cached when a bundle is built so we
      can determine whether they have changed and whether a rebuild
      is required.

This data is not all stored in the same cache necessarily. The
classes in this module provide the "environment.cache" object, but
also serve in other places.
"""

import os
from os import path
import errno
import tempfile
import warnings
from webassets import six
from webassets.merge import BaseHunk
from webassets.filter import Filter, freezedicts
from webassets.utils import md5_constructor, pickle
import types


__all__ = ('FilesystemCache', 'MemoryCache', 'get_cache',)


def make_hashable(data):
    """Ensures ``data`` can be hashed().

    Mostly needs to support dict. The other special types we use
    as hash keys (Hunks, Filters) already have a proper hash() method.

    See also ``make_md5``.

    Note that we do not actually hash the data for the memory cache.
    """
    return freezedicts(data)


def make_md5(*data):
    """Make a md5 hash based on``data``.

    Specifically, this knows about ``Hunk`` objects, and makes sure
    the actual content is hashed.

    This is very conservative, and raises an exception if there are
    data types that it does not explicitly support. This is because
    we had in the past some debugging headaches with the cache not
    working for this very reason.

    MD5 is faster than sha, and we don't care so much about collisions.
    We care enough however not to use hash().
    """
    def walk(obj):
        if isinstance(obj, (tuple, list, frozenset)):
            for item in obj:
                for d in walk(item): yield d
        elif isinstance(obj, (dict)):
            for k in sorted(obj.keys()):
                for d in walk(k): yield d
                for d in walk(obj[k]): yield d
        elif isinstance(obj, BaseHunk):
            yield obj.data().encode('utf-8')
        elif isinstance(obj, int):
            yield str(obj).encode('utf-8')
        elif isinstance(obj, six.text_type):
            yield obj.encode('utf-8')
        elif isinstance(obj, six.binary_type):
            yield obj
        elif hasattr(obj, "id"):
            for i in walk(obj.id()):
                yield i
        elif obj is None:
            yield "None".encode('utf-8')
        elif isinstance(obj, types.FunctionType):
            yield str(hash(obj)).encode('utf-8')
        else:
            raise ValueError('Cannot MD5 type %s' % type(obj))
    md5 = md5_constructor()
    for d in walk(data):
        md5.update(d)
    return md5.hexdigest()


def safe_unpickle(string):
    """Unpickle the string, or return ``None`` if that fails."""
    try:
        return pickle.loads(string)
    except:
        return None


class BaseCache(object):
    """Abstract base class.

    The cache key must be something that is supported by the Python hash()
    function. The cache value may be a string, or anything that can be pickled.

    Since the cache is used for multiple purposes, all webassets-internal code
    should always tag its keys with an id, like so:

        key = ("tag", actual_key)

    One cache instance can only be used safely with a single Environment.
    """

    def get(self, key):
        """Should return the cache contents, or False.
        """
        raise NotImplementedError()

    def set(self, key, value):
        raise NotImplementedError()


class MemoryCache(BaseCache):
    """Caches stuff in the process memory.

    WARNING: Do NOT use this in a production environment, where you
    are likely going to have multiple processes serving the same app!

    Note that the keys are used as-is, not passed through hash() (which is
    a difference: http://stackoverflow.com/a/9022664/15677). However, the
    reason we don't is because the original value is nicer to debug.
    """

    def __init__(self, capacity):
        self.capacity = capacity
        self.keys = []
        self.cache = {}

    def __eq__(self, other):
        """Return equality with the config values that instantiate
        this instance.
        """
        return False == other or \
               None == other or \
               id(self) == id(other)

    def get(self, key):
        key = make_md5(make_hashable(key))
        return self.cache.get(key, None)

    def set(self, key, value):
        key = make_md5(make_hashable(key))
        self.cache[key] = value
        try:
            self.keys.remove(key)
        except ValueError:
            pass
        self.keys.append(key)

        # limit cache to the given capacity
        to_delete = self.keys[0:max(0, len(self.keys)-self.capacity)]
        self.keys = self.keys[len(to_delete):]
        for item in to_delete:
            del self.cache[item]


class FilesystemCache(BaseCache):
    """Uses a temporary directory on the disk.
    """

    V = 2   # We have changed the cache format once

    def __init__(self, directory):
        self.directory = directory

    def __eq__(self, other):
        """Return equality with the config values
        that instantiate this instance.
        """
        return True == other or \
               self.directory == other or \
               id(self) == id(other)

    def get(self, key):
        filename = path.join(self.directory, '%s' % make_md5(self.V, key))
        try:
            f = open(filename, 'rb')
        except IOError as e:
            if e.errno != errno.ENOENT:
                raise
            return None
        try:
            result = f.read()
        finally:
            f.close()

        unpickled = safe_unpickle(result)
        if unpickled is None:
            warnings.warn('Ignoring corrupted cache file %s' % filename)
        return unpickled

    def set(self, key, data):
        md5 = '%s' % make_md5(self.V, key)
        filename = path.join(self.directory, md5)
        fd, temp_filename = tempfile.mkstemp(prefix='.' + md5,
                dir=self.directory)
        try:
            with os.fdopen(fd, 'wb') as f:
                pickle.dump(data, f)
                f.flush()
            if os.path.isfile(filename):
                os.unlink(filename)
            os.rename(temp_filename, filename)
        except:
            os.unlink(temp_filename)
            raise


def get_cache(option, ctx):
    """Return a cache instance based on ``option``.
    """
    if not option:
        return None

    if isinstance(option, BaseCache):
        return option
    elif isinstance(option, type) and issubclass(option, BaseCache):
        return option()

    if option is True:
        directory = path.join(ctx.directory, '.webassets-cache')
        # Auto-create the default directory
        if not path.exists(directory):
            os.makedirs(directory)
    else:
        directory = option
    return FilesystemCache(directory)
