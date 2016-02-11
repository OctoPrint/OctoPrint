import os
from os import path
from itertools import chain
from webassets import six
from webassets.six.moves import map
from webassets.six.moves import zip
from webassets.utils import is_url

try:
    import glob2 as glob
    from glob import has_magic
except ImportError:
    import glob
    from glob import has_magic

from .cache import get_cache
from .version import get_versioner, get_manifest
from .updater import get_updater
from .utils import urlparse


__all__ = ('Environment', 'RegisterError')


class RegisterError(Exception):
    pass


class ConfigStorage(object):
    """This is the backend which :class:`Environment` uses to store
    its configuration values.

    Environment-subclasses like the one used by ``django-assets`` will
    often want to use a custom ``ConfigStorage`` as well, building upon
    whatever configuration the framework is using.

    The goal in designing this class therefore is to make it easy for
    subclasses to change the place the data is stored: Only
    _meth:`__getitem__`, _meth:`__setitem__`, _meth:`__delitem__` and
    _meth:`__contains__` need to be implemented.

    One rule: The default storage is case-insensitive, and custom
    environments should maintain those semantics.

    A related reason is why we don't inherit from ``dict``. It would
    require us to re-implement a whole bunch of methods, like pop() etc.
    """

    def __init__(self, env):
        self.env = env

    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

    def update(self, d):
        for key in d:
            self.__setitem__(key, d[key])

    def setdefault(self, key, value):
        if not key in self:
            self.__setitem__(key, value)
            return value
        return self.__getitem__(key)

    def __contains__(self, key):
        raise NotImplementedError()

    def __getitem__(self, key):
        raise NotImplementedError()

    def __setitem__(self, key, value):
        raise NotImplementedError()

    def __delitem__(self, key):
        raise NotImplementedError()

    def _get_deprecated(self, key):
        """For deprecated keys, fake the values as good as we can.
        Subclasses need to call this in __getitem__."""
        pass

    def _set_deprecated(self, key, value):
        """Same for __setitem__."""
        pass


def url_prefix_join(prefix, fragment):
    """Join url prefix with fragment."""
    # Ensures urljoin will not cut the last part.
    prefix += prefix[-1:] != '/' and '/' or ''
    return urlparse.urljoin(prefix, fragment)


class Resolver(object):
    """Responsible for resolving user-specified :class:`Bundle`
    contents to actual files, as well as to urls.

    In this base version, this is essentially responsible for searching
    the load path for the queried file.

    A custom implementation of this class is tremendously useful when
    integrating with frameworks, which usually have some system to
    spread static files across applications or modules.

    The class is designed for maximum extensibility.
    """

    def glob(self, basedir, expr):
        """Generator that runs when a glob expression needs to be
        resolved. Yields a list of absolute filenames.
        """
        expr = path.join(basedir, expr)
        for filename in glob.iglob(expr):
            if path.isdir(filename):
                continue
            yield filename

    def consider_single_directory(self, directory, item):
        """Searches for ``item`` within ``directory``. Is able to
        resolve glob instructions.

        Subclasses can call this when they have narrowed done the
        location of a bundle item to a single directory.
        """
        expr = path.join(directory, item)
        if has_magic(expr):
            # Note: No error if glob returns an empty list
            return list(self.glob(directory, item))
        else:
            if path.exists(expr):
                return expr
            raise IOError("'%s' does not exist" % expr)

    def search_env_directory(self, ctx, item):
        """This is called by :meth:`search_for_source` when no
        :attr:`Environment.load_path` is set.
        """
        return self.consider_single_directory(ctx.directory, item)

    def search_load_path(self, ctx, item):
        """This is called by :meth:`search_for_source` when a
        :attr:`Environment.load_path` is set.

        If you want to change how the load path is processed,
        overwrite this method.
        """
        if has_magic(item):
            # We glob all paths.
            result = []
            for path in ctx.load_path:
                result.extend(list(self.glob(path, item)))
            return result
        else:
            # Single file, stop when we find the first match, or error
            # out otherwise. We still use glob() because then the load_path
            # itself can contain globs. Neat!
            for path in ctx.load_path:
                result = list(self.glob(path, item))
                if result:
                    return result
            raise IOError("'%s' not found in load path: %s" % (
                item, ctx.load_path))

    def search_for_source(self, ctx, item):
        """Called by :meth:`resolve_source` after determining that
        ``item`` is a relative filesystem path.

        You should always overwrite this method, and let
        :meth:`resolve_source` deal with absolute paths, urls and
        other types of items that a bundle may contain.
        """
        if ctx.load_path:
            return self.search_load_path(ctx, item)
        else:
            return self.search_env_directory(ctx, item)

    def query_url_mapping(self, ctx, filepath):
        """Searches the environment-wide url mapping (based on the
        urls assigned to each directory in the load path). Returns
        the correct url for ``filepath``.

        Subclasses should be sure that they really want to call this
        method, instead of simply falling back to ``super()``.
        """
        # Build a list of dir -> url mappings
        mapping = list(ctx.url_mapping.items())
        try:
            mapping.append((ctx.directory, ctx.url))
        except EnvironmentError:
            # Rarely, directory/url may not be set. That's ok.
            pass

        # Make sure paths are absolute, normalized, and sorted by length
        mapping = list(map(
            lambda p_u: (path.normpath(path.abspath(p_u[0])), p_u[1]),
            mapping))
        mapping.sort(key=lambda i: len(i[0]), reverse=True)

        needle = path.normpath(filepath)
        for candidate, url in mapping:
            if needle.startswith(candidate):
                # Found it!
                rel_path = needle[len(candidate)+1:]
                # If there are any subdirs in rel_path, ensure
                # they use HTML-style path separators, in case
                # the local OS (Windows!) has a different scheme
                rel_path = rel_path.replace(os.sep, "/")
                return url_prefix_join(url, rel_path)
        raise ValueError('Cannot determine url for %s' % filepath)

    def resolve_source(self, ctx, item):
        """Given ``item`` from a Bundle's contents, this has to
        return the final value to use, usually an absolute
        filesystem path.

        .. note::
            It is also allowed to return urls and bundle instances
            (or generally anything else the calling :class:`Bundle`
            instance may be able to handle). Indeed this is the
            reason why the name of this method does not imply a
            return type.

        The incoming item is usually a relative path, but may also be
        an absolute path, or a url. These you will commonly want to
        return unmodified.

        This method is also allowed to resolve ``item`` to multiple
        values, in which case a list should be returned. This is
        commonly used if ``item`` includes glob instructions
        (wildcards).

        .. note::
            Instead of this, subclasses should consider implementing
            :meth:`search_for_source` instead.
        """

        # Pass through some things unscathed
        if not isinstance(item, six.string_types):
            # Don't stand in the way of custom values.
            return item
        if is_url(item) or path.isabs(item):
            return item

        return self.search_for_source(ctx, item)

    def resolve_output_to_path(self, ctx, target, bundle):
        """Given ``target``, this has to return the absolute
        filesystem path to which the output file of ``bundle``
        should be written.

        ``target`` may be a relative or absolute path, and is
        usually taking from the :attr:`Bundle.output` property.

        If a version-placeholder is used (``%(version)s``, it is
        still unresolved at this point.
        """
        return path.join(ctx.directory, target)

    def resolve_source_to_url(self, ctx, filepath, item):
        """Given the absolute filesystem path in ``filepath``, as
        well as the original value from :attr:`Bundle.contents` which
        resolved to this path, this must return the absolute url
        through which the file is to be referenced.

        Depending on the use case, either the ``filepath`` or the
        ``item`` argument will be more helpful in generating the url.

        This method should raise a ``ValueError`` if the url cannot
        be determined.
        """
        return self.query_url_mapping(ctx, filepath)

    def resolve_output_to_url(self, ctx, target):
        """Given ``target``, this has to return the url through
        which the output file can be referenced.

        ``target`` may be a relative or absolute path, and is
        usually taking from the :attr:`Bundle.output` property.

        This is different from :meth:`resolve_source_to_url` in
        that you do not passed along the result of
        :meth:`resolve_output_to_path`. This is because in many
        use cases, the filesystem is not available at the point
        where the output url is needed (the media server may on
        a different machine).
        """
        if not path.isabs(target):
            # If relative, output files are written to env.directory,
            # thus we can simply base all values off of env.url.
            return url_prefix_join(ctx.url, target)
        else:
            # If an absolute output path was specified, then search
            # the url mappings.
            return self.query_url_mapping(ctx, target)


class BundleRegistry(object):

    def __init__(self):
        self._named_bundles = {}
        self._anon_bundles = []

    def __iter__(self):
        return chain(six.itervalues(self._named_bundles), self._anon_bundles)

    def __getitem__(self, name):
        return self._named_bundles[name]

    def __contains__(self, name):
        return name in self._named_bundles

    def __len__(self):
        return len(self._named_bundles) + len(self._anon_bundles)

    def __bool__(self):
        return True
    __nonzero__ = __bool__   # For Python 2

    def register(self, name, *args, **kwargs):
        """Register a :class:`Bundle` with the given ``name``.

        This can be called in multiple ways:

        - With a single :class:`Bundle` instance::

              env.register('jquery', jquery_bundle)

        - With a dictionary, registering multiple bundles at once:

              bundles = {'js': js_bundle, 'css': css_bundle}
              env.register(bundles)

          .. note::
              This is a convenient way to use a :doc:`loader <loaders>`:

                   env.register(YAMLLoader('assets.yaml').load_bundles())

        - With many arguments, creating a new bundle on the fly::

              env.register('all_js', jquery_bundle, 'common.js',
                           filters='rjsmin', output='packed.js')
        """

        from .bundle import Bundle

        # Register a dict
        if isinstance(name, dict) and not args and not kwargs:
            for name, bundle in name.items():
                self.register(name, bundle)
            return

        if len(args) == 0:
            raise TypeError('at least two arguments are required')
        else:
            if len(args) == 1 and not kwargs and isinstance(args[0], Bundle):
                bundle = args[0]
            else:
                bundle = Bundle(*args, **kwargs)

            if name in self._named_bundles:
                if self._named_bundles[name] == bundle:
                    pass  # ignore
                else:
                    raise RegisterError('Another bundle is already registered '+
                                        'as "%s": %s' % (name, self._named_bundles[name]))
            else:
                self._named_bundles[name] = bundle
                bundle.env = self   # take ownership

            return bundle

    def add(self, *bundles):
        """Register a list of bundles with the environment, without
        naming them.

        This isn't terribly useful in most cases. It exists primarily
        because in some cases, like when loading bundles by searching
        in templates for the use of an "assets" tag, no name is available.
        """
        for bundle in bundles:
            self._anon_bundles.append(bundle)
            bundle.env = self    # take ownership


# Those are config keys used by the environment. Framework-wrappers may
# find this list useful if they desire to prefix those settings. For example,
# in Django, it would be ASSETS_DEBUG. Other config keys are encouraged to use
# their own namespacing, so they don't need to be prefixed. For example, a
# filter setting might be CSSMIN_BIN.
env_options = [
    'directory', 'url', 'debug', 'cache', 'updater', 'auto_build',
    'url_expire', 'versions', 'manifest', 'load_path', 'url_mapping']


class ConfigurationContext(object):
    """Interface to the webassets configuration key-value store.

    This wraps the :class:`ConfigStorage`` interface and adds some
    helpers. It allows attribute-access to the most important
    settings, and transparently instantiates objects, such that
    ``env.manifest`` gives you an object, even though the configuration
    contains the string "json".
    """

    def __init__(self, storage):
        self._storage = storage

    def append_path(self, path, url=None):
        """Appends ``path`` to :attr:`load_path`, and adds a
        corresponding entry to :attr:`url_mapping`.
        """
        self.load_path.append(path)
        if url:
            self.url_mapping[path] = url

    def _set_debug(self, debug):
        self._storage['debug'] = debug
    def _get_debug(self):
        return self._storage['debug']
    debug = property(_get_debug, _set_debug, doc=
    """Enable/disable debug mode. Possible values are:

        ``False``
            Production mode. Bundles will be merged and filters applied.
        ``True``
            Enable debug mode. Bundles will output their individual source
            files.
        *"merge"*
            Merge the source files, but do not apply filters.
    """)

    def _set_cache(self, enable):
        self._storage['cache'] = enable
    def _get_cache(self):
        cache = get_cache(self._storage['cache'], self)
        if cache != self._storage['cache']:
            self._storage['cache'] = cache
        return cache
    cache = property(_get_cache, _set_cache, doc=
    """Controls the behavior of the cache. The cache will speed up rebuilding
    of your bundles, by caching individual filter results. This can be
    particularly useful while developing, if your bundles would otherwise take
    a long time to rebuild.

    Possible values are:

      ``False``
          Do not use the cache.

      ``True`` (default)
          Cache using default location, a ``.webassets-cache`` folder inside
          :attr:`directory`.

      *custom path*
         Use the given directory as the cache directory.
    """)

    def _set_auto_build(self, value):
        self._storage['auto_build'] = value
    def _get_auto_build(self):
        return self._storage['auto_build']
    auto_build = property(_get_auto_build, _set_auto_build, doc=
    """Controls whether bundles should be automatically built, and
    rebuilt, when required (if set to ``True``), or whether they
    must be built manually be the user, for example via a management
    command.

    This is a good setting to have enabled during debugging, and can
    be very convenient for low-traffic sites in production as well.
    However, there is a cost in checking whether the source files
    have changed, so if you care about performance, or if your build
    process takes very long, then you may want to disable this.

    By default automatic building is enabled.
    """)

    def _set_manifest(self, manifest):
        self._storage['manifest'] = manifest
    def _get_manifest(self):
        manifest = get_manifest(self._storage['manifest'], env=self)
        if manifest != self._storage['manifest']:
            self._storage['manifest'] = manifest
        return manifest
    manifest = property(_get_manifest, _set_manifest, doc=
    """A manifest persists information about the versions bundles
    are at.

    The Manifest plays a role only if you insert the bundle version
    in your output filenames, or append the version as a querystring
    to the url (via the ``url_expire`` option). It serves two
    purposes:

        - Without a manifest, it may be impossible to determine the
          version at runtime. In a deployed app, the media files may
          be stored on a different server entirely, and be
          inaccessible from the application code. The manifest,
          if shipped with your application, is what still allows to
          construct the proper URLs.

        - Even if it were possible to determine the version at
          runtime without a manifest, it may be a costly process,
          and using a manifest may give you better performance. If
          you use a hash-based version for example, this hash would
          need to be recalculated every time a new process is
          started.

    Valid values are:

      ``"cache"`` (default)
          The cache is used to remember version information. This
          is useful to avoid recalculating the version hash.

      ``"file:{path}"``
          Stores version information in a file at {path}. If not
          path is given, the manifest will be stored as
          ``.webassets-manifest`` in ``Environment.directory``.

      ``"json:{path}"``
         Same as "file:{path}", but uses JSON to store the information.

      ``False``, ``None``
          No manifest is used.

      Any custom manifest implementation.
    """)

    def _set_versions(self, versions):
        self._storage['versions'] = versions
    def _get_versions(self):
        versions = get_versioner(self._storage['versions'])
        if versions != self._storage['versions']:
            self._storage['versions'] = versions
        return versions
    versions = property(_get_versions, _set_versions, doc=
    """Defines what should be used as a Bundle ``version``.

    A bundle's version is what is appended to URLs when the
    ``url_expire`` option is enabled, and the version can be part
    of a Bundle's output filename by use of the ``%(version)s``
    placeholder.

    Valid values are:

      ``timestamp``
          The version is determined by looking at the mtime of a
          bundle's output file.

      ``hash`` (default)
          The version is a hash over the output file's content.

      ``False``, ``None``
          Functionality that requires a version is disabled. This
          includes the ``url_expire`` option, the ``auto_build``
          option, and support for the %(version)s placeholder.

      Any custom version implementation.

    """)

    def set_updater(self, updater):
        self._storage['updater'] = updater
    def get_updater(self):
        updater = get_updater(self._storage['updater'])
        if updater != self._storage['updater']:
            self._storage['updater'] = updater
        return updater
    updater = property(get_updater, set_updater, doc=
    """Controls how the ``auto_build`` option should determine
    whether a bundle needs to be rebuilt.

      ``"timestamp"`` (default)
          Rebuild bundles if the source file timestamp exceeds the existing
          output file's timestamp.

      ``"always"``
          Always rebuild bundles (avoid in production environments).

      Any custom version implementation.
    """)

    def _set_url_expire(self, url_expire):
        self._storage['url_expire'] = url_expire
    def _get_url_expire(self):
        return self._storage['url_expire']
    url_expire = property(_get_url_expire, _set_url_expire, doc=
    """If you send your assets to the client using a
    *far future expires* header (to minimize the 304 responses
    your server has to send), you need to make sure that assets
    will be reloaded by the browser when they change.

    If this is set to ``True``, then the Bundle URLs generated by
    webassets will have their version (see ``Environment.versions``)
    appended as a querystring.

    An alternative approach would be to use the ``%(version)s``
    placeholder in the bundle output file.

    The default behavior (indicated by a ``None`` value) is to add
    an expiry querystring if the bundle does not use a version
    placeholder.
    """)

    def _set_directory(self, directory):
        self._storage['directory'] = directory
    def _get_directory(self):
        try:
            return path.abspath(self._storage['directory'])
        except KeyError:
            raise EnvironmentError(
                'The environment has no "directory" configured')
    directory = property(_get_directory, _set_directory, doc=
    """The base directory to which all paths will be relative to,
    unless :attr:`load_paths` are given, in which case this will
    only serve as the output directory.

    In the url space, it is mapped to :attr:`urls`.
    """)

    def _set_url(self, url):
        self._storage['url'] = url
    def _get_url(self):
        try:
            return self._storage['url']
        except KeyError:
            raise EnvironmentError(
                'The environment has no "url" configured')
    url = property(_get_url, _set_url, doc=
    """The url prefix used to construct urls for files in
    :attr:`directory`.

    To define url spaces for other directories, see
    :attr:`url_mapping`.
    """)

    def _set_load_path(self, load_path):
        self._storage['load_path'] = load_path
    def _get_load_path(self):
        return self._storage['load_path']
    load_path = property(_get_load_path, _set_load_path, doc=
    """An list of directories that will be searched for source files.

    If this is set, source files will only be looked for in these
    directories, and :attr:`directory` is used as a location for
    output files only.

    .. note:
        You are free to add :attr:`directory` to your load path as
        well.

    .. note:
        Items on the load path are allowed to contain globs.

    To modify this list, you should use :meth:`append_path`, since
    it makes it easy to add the corresponding url prefix to
    :attr:`url_mapping`.
    """)

    def _set_url_mapping(self, url_mapping):
        self._storage['url_mapping'] = url_mapping
    def _get_url_mapping(self):
        return self._storage['url_mapping']
    url_mapping = property(_get_url_mapping, _set_url_mapping, doc=
    """A dictionary of directory -> url prefix mappings that will
    be considered when generating urls, in addition to the pair of
    :attr:`directory` and :attr:`url`, which is always active.

    You should use :meth:`append_path` to add directories to the
    load path along with their respective url spaces, instead of
    modifying this setting directly.
    """)

    def _set_resolver(self, resolver):
        self._storage['resolver'] = resolver
    def _get_resolver(self):
        return self._storage['resolver']
    resolver = property(_get_resolver, _set_resolver)


class BaseEnvironment(BundleRegistry, ConfigurationContext):
    """Abstract base class for :class:`Environment` with slightly more
    generic assumptions, to ease subclassing.
    """

    config_storage_class = None
    resolver_class = Resolver

    def __init__(self, **config):
        BundleRegistry.__init__(self)
        self._config = self.config_storage_class(self)
        ConfigurationContext.__init__(self, self._config)

        # directory, url currently do not have default values
        #
        # some thought went into these defaults:
        #   - enable url_expire, because we want to encourage the right thing
        #   - default to hash versions, for the same reason: they're better
        #   - manifest=cache because hash versions are slow
        self.config.setdefault('debug', False)
        self.config.setdefault('cache', True)
        self.config.setdefault('url_expire', None)
        self.config.setdefault('auto_build', True)
        self.config.setdefault('manifest', 'cache')
        self.config.setdefault('versions', 'hash')
        self.config.setdefault('updater', 'timestamp')
        self.config.setdefault('load_path', [])
        self.config.setdefault('url_mapping', {})
        self.config.setdefault('resolver', self.resolver_class())

        self.config.update(config)

    @property
    def config(self):
        """Key-value configuration. Keys are case-insensitive.
        """
        # This is a property so that user are not tempted to assign
        # a custom dictionary which won't uphold our caseless semantics.
        return self._config


class DictConfigStorage(ConfigStorage):
    """Using a lower-case dict for configuration values.
    """
    def __init__(self, *a, **kw):
        self._dict = {}
        ConfigStorage.__init__(self, *a, **kw)
    def __contains__(self, key):
        return self._dict.__contains__(key.lower())
    def __getitem__(self, key):
        key = key.lower()
        value = self._get_deprecated(key)
        if not value is None:
            return value
        return self._dict.__getitem__(key)
    def __setitem__(self, key, value):
        key = key.lower()
        if not self._set_deprecated(key, value):
            self._dict.__setitem__(key.lower(), value)
    def __delitem__(self, key):
        self._dict.__delitem__(key.lower())


class Environment(BaseEnvironment):
    """Owns a collection of bundles, and a set of configuration values which
    will be used when processing these bundles.
    """

    config_storage_class = DictConfigStorage

    def __init__(self, directory=None, url=None, **more_config):
        super(Environment, self).__init__(**more_config)
        if directory is not None:
            self.directory = directory
        if url is not None:
            self.url = url


def parse_debug_value(value):
    """Resolve the given string value to a debug option.

    Can be used to deal with os environment variables, for example.
    """
    if value is None:
        return value
    value = value.lower()
    if value in ('true', '1'):
        return True
    elif value in ('false', '0'):
        return False
    elif value in ('merge',):
        return 'merge'
    else:
        raise ValueError()

