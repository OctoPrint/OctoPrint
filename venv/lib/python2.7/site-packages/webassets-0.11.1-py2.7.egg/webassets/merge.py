"""Contains the core functionality that manages merging of assets.
"""
from __future__ import with_statement
import contextlib

try:
    from urllib.request import Request as URLRequest, urlopen
    from urllib.error import HTTPError
except ImportError:
    from urllib2 import Request as URLRequest, urlopen
    from urllib2 import HTTPError
import logging
from io import open
from webassets.six.moves import filter

from .utils import cmp_debug_levels, StringIO, hash_func


__all__ = ('FileHunk', 'MemoryHunk', 'merge', 'FilterTool',
           'MoreThanOneFilterError', 'NoFilters')


# Log which is used to output low-level information about what the build does.
# This is setup such that it does not output just because the root level
# "webassets" logger is set to level DEBUG (for example via the commandline
# --verbose option). Instead, the messages are only shown when an environment
# variable is set.
# However, we might want to change this in the future. The CLI --verbose option
# could instead just set the level to NOTICE, for example.
log = logging.getLogger('webassets.debug')
log.addHandler(logging.StreamHandler())
import os
if os.environ.get('WEBASSETS_DEBUG'):
    log.setLevel(logging.DEBUG)
else:
    log.setLevel(logging.ERROR)


class BaseHunk(object):
    """Abstract base class.
    """

    def mtime(self):
        raise NotImplementedError()

    def id(self):
        return hash_func(self.data())

    def __eq__(self, other):
        if isinstance(other, BaseHunk):
            # Allow class to be used as a unique dict key.
            return hash_func(self) == hash_func(other)
        return False

    def data(self):
        raise NotImplementedError()

    def save(self, filename):
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(self.data())


class FileHunk(BaseHunk):
    """Exposes a single file through as a hunk.
    """

    def __init__(self, filename):
        self.filename = filename

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.filename)

    def mtime(self):
        pass

    def data(self):
        f = open(self.filename, 'r', encoding='utf-8')
        try:
            return f.read()
        finally:
            f.close()


class UrlHunk(BaseHunk):
    """Represents a file that is referenced by an Url.

    If an environment is given, it's cache will be used to cache the url
    contents, and to access it, as allowed by the etag/last modified headers.
    """

    def __init__(self, url, env=None):
        self.url = url
        self.env = env

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.url)

    def data(self):
        if not hasattr(self, '_data'):
            request = URLRequest(self.url)

            # Look in the cache for etag / last modified headers to use
            # TODO: "expires" header could be supported
            if self.env and self.env.cache:
                headers = self.env.cache.get(
                    ('url', 'headers', self.url))
                if headers:
                    etag, lmod = headers
                    if etag: request.add_header('If-None-Match', etag)
                    if lmod: request.add_header('If-Modified-Since', lmod)

            # Make a request
            try:
                response = urlopen(request)
            except HTTPError as e:
                if e.code != 304:
                    raise
                    # Use the cached version of the url
                self._data = self.env.cache.get(('url', 'contents', self.url))
            else:
                with contextlib.closing(response):
                    self._data = response.read()

                # Cache the info from this request
                if self.env and self.env.cache:
                    self.env.cache.set(
                        ('url', 'headers', self.url),
                        (response.headers.getheader("ETag"),
                         response.headers.getheader("Last-Modified")))
                    self.env.cache.set(('url', 'contents', self.url), self._data)
        return self._data


class MemoryHunk(BaseHunk):
    """Content that is no longer a direct representation of a source file. It
    might have filters applied, and is probably the result of merging multiple
    individual source files together.
    """

    def __init__(self, data, files=None):
        self._data = data
        self.files = files or []

    def __repr__(self):
        # Include  a has of the data. We want this during logging, so we
        # can see which hunks contain identical content. Because this is
        # a question of performance, make sure to log in such a way that
        # when logging is disabled, this won't be called, i.e.: don't
        # %s-format yourself, let logging do it as needed.
        return '<%s %s>' % (self.__class__.__name__, hash_func(self))

    def mtime(self):
        pass

    def data(self):
        if hasattr(self._data, 'read'):
            return self._data.read()
        return self._data

    def save(self, filename):
        f = open(filename, 'w', encoding='utf-8')
        try:
            f.write(self.data())
        finally:
            f.close()


def merge(hunks, separator=None):
    """Merge the given list of hunks, returning a new ``MemoryHunk`` object.
    """
    # TODO: combine the list of source files, we'd like to collect them
    # The linebreak is important in certain cases for Javascript
    # files, like when a last line is a //-comment.
    if not separator:
        separator = '\n'
    return MemoryHunk(separator.join([h.data() for h in hunks]))


class MoreThanOneFilterError(Exception):

    def __init__(self, message, filters):
        Exception.__init__(self, message)
        self.filters = filters


class NoFilters(Exception):
    pass


class FilterTool(object):
    """Can apply filters to hunk objects, while using the cache.

    If ``no_cache_read`` is given, then the cache will not be considered for
    this operation (though the result will still be written to the cache).

    ``kwargs`` are options that should be passed along to the filters.
    """

    VALID_TRANSFORMS = ('input', 'output',)
    VALID_FUNCS =  ('open', 'concat',)

    def __init__(self, cache=None, no_cache_read=False, kwargs=None):
        self.cache = cache
        self.no_cache_read = no_cache_read
        self.kwargs = kwargs or {}

    def _wrap_cache(self, key, func):
        """Return cache value ``key``, or run ``func``.
        """
        if self.cache:
            if not self.no_cache_read:
                log.debug('Checking cache for key %s', key)
                content = self.cache.get(key)
                if not content in (False, None):
                    log.debug('Using cached result for %s', key)
                    return MemoryHunk(content)

        content = func().getvalue()
        if self.cache:
            log.debug('Storing result in cache with key %s', key,)
            self.cache.set(key, content)
        return MemoryHunk(content)

    def apply(self, hunk, filters, type, kwargs=None):
        """Apply the given list of filters to the hunk, returning a new
        ``MemoryHunk`` object.

        ``kwargs`` are options that should be passed along to the filters.
        If ``hunk`` is a file hunk, a ``source_path`` key will automatically
        be added to ``kwargs``.
        """
        assert type in self.VALID_TRANSFORMS
        log.debug('Need to run method "%s" of filters (%s) on hunk %s with '
                  'kwargs=%s', type, filters, hunk, kwargs)

        filters = [f for f in filters if getattr(f, type, None)]
        if not filters:  # Short-circuit
            log.debug('No filters have "%s" methods, returning hunk '
                      'unchanged' % (type,))
            return hunk

        kwargs_final = self.kwargs.copy()
        kwargs_final.update(kwargs or {})

        def func():
            data = StringIO(hunk.data())
            for filter in filters:
                log.debug('Running method "%s" of  %s with kwargs=%s',
                    type, filter, kwargs_final)
                out = StringIO(u'') # For 2.x, StringIO().getvalue() returns str
                getattr(filter, type)(data, out, **kwargs_final)
                data = out
                data.seek(0)

            return data

        additional_cache_keys = []
        if kwargs_final:
            for filter in filters:
                additional_cache_keys += filter.get_additional_cache_keys(**kwargs_final)

        # Note that the key used to cache this hunk is different from the key
        # the hunk will expose to subsequent merges, i.e. hunk.key() is always
        # based on the actual content, and does not match the cache key. The
        # latter also includes information about for example the filters used.
        #
        # It wouldn't have to be this way. Hunk could subsequently expose their
        # cache key through hunk.key(). This would work as well, but would be
        # an inferior solution: Imagine a source file which receives
        # non-substantial changes, in the sense that they do not affect the
        # filter output, for example whitespace. If a hunk's key is the cache
        # key, such a change would invalidate the caches for all subsequent
        # operations on this hunk as well, even though it didn't actually
        # change after all.
        key = ("hunk", hunk, tuple(filters), type, additional_cache_keys)
        return self._wrap_cache(key, func)

    def apply_func(self, filters, type, args, kwargs=None, cache_key=None):
        """Apply a filter that is not a "stream in, stream out" transform (i.e.
        like the input() and output() filter methods).  Instead, the filter
        method is given the arguments in ``args`` and should then produce an
        output stream. This is used, e.g., for the concat() and open() filter
        methods.

        Only one such filter can run per operation.

        ``cache_key`` may be a list of additional values to use as the cache
        key, in addition to the default key (the filter and arguments).
        """
        assert type in self.VALID_FUNCS
        log.debug('Need to run method "%s" of one of the filters (%s) '
                  'with args=%s, kwargs=%s', type, filters, args, kwargs)

        filters = [f for f in filters if getattr(f, type, None)]
        if not filters:  # Short-circuit
            log.debug('No filters have a "%s" method' % type)
            raise NoFilters()

        if len(filters) > 1:
            raise MoreThanOneFilterError(
                'These filters cannot be combined: %s' % (
                    ', '.join([f.name for f in filters])), filters)

        kwargs_final = self.kwargs.copy()
        kwargs_final.update(kwargs or {})

        def func():
            filter = filters[0]
            out = StringIO(u'')  # For 2.x, StringIO().getvalue() returns str
            log.debug('Running method "%s" of %s with args=%s, kwargs=%s',
                type, filter, args, kwargs)
            getattr(filter, type)(out, *args, **kwargs_final)
            return out

        additional_cache_keys = []
        if kwargs_final:
            for filter in filters:
                additional_cache_keys += filter.get_additional_cache_keys(**kwargs_final)

        key = ("hunk", args, tuple(filters), type, cache_key or [], additional_cache_keys)
        return self._wrap_cache(key, func)


def merge_filters(filters1, filters2):
    """Merge two filter lists into one.

    Duplicate filters are removed. Since filter order is important, the order
    of the arguments to this function also matter. Duplicates are always
    removed from the second filter set if they exist in the first.

    The result will always be ``filters1``, with additional unique filters
    from ``filters2`` appended. Within the context of a hierarchy, you want
    ``filters2`` to be the parent.

    This function presumes that all the given filters inherit from ``Filter``,
    which properly implements operators to determine duplicate filters.
    """
    result = list(filters1[:])
    if filters2:
        for f in filters2:
            if not f in result:
                result.append(f)
    return result


def select_filters(filters, level):
    """Return from the list in ``filters`` those filters which indicate that
    they should run for the given debug level.
    """
    return [f for f in filters
            if f.max_debug_level is None or
               cmp_debug_levels(level, f.max_debug_level) <= 0]
