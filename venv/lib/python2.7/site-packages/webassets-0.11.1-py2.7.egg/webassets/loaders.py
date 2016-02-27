"""Loaders are helper classes which will read environments and/or
bundles from a source, like a configuration file.

This can be used as an alternative to an imperative setup.
"""

import os, sys
from os import path
import glob, fnmatch
import types
from webassets import six
try:
    import yaml
except ImportError:
    pass

from webassets import six
from webassets import Environment
from webassets.bundle import Bundle
from webassets.importlib import import_module


__all__ = ('Loader', 'LoaderError', 'PythonLoader', 'YAMLLoader',
           'GlobLoader',)



class LoaderError(Exception):
    """Loaders should raise this when they can't deal with a given file.
    """


class YAMLLoader(object):
    """Will load an environment or a set of bundles from
    `YAML <http://en.wikipedia.org/wiki/YAML>`_ files.
    """

    def __init__(self, file_or_filename):
        try:
            yaml
        except NameError:
            raise EnvironmentError('PyYAML is not installed')
        else:
            self.yaml = yaml
        self.file_or_filename = file_or_filename

    def _yield_bundle_contents(self, data):
        """Yield bundle contents from the given dict.

        Each item yielded will be either a string representing a file path
        or a bundle."""
        contents = data.get('contents', [])
        if isinstance(contents, six.string_types):
            contents = contents,
        for content in contents:
            if isinstance(content, dict):
                content = self._get_bundle(content)
            yield content

    def _get_bundle(self, data):
        """Return a bundle initialised by the given dict."""
        kwargs = dict(
            filters=data.get('filters', None),
            output=data.get('output', None),
            debug=data.get('debug', None),
            extra=data.get('extra', {}),
            config=data.get('config', {}),
            depends=data.get('depends', None))
        return Bundle(*list(self._yield_bundle_contents(data)), **kwargs)

    def _get_bundles(self, obj, known_bundles=None):
        """Return a dict that keys bundle names to bundles."""
        bundles = {}
        for key, data in six.iteritems(obj):
            if data is None:
                data = {}
            bundles[key] = self._get_bundle(data)

        # now we need to recurse through the bundles and get any that
        # are included in each other.
        for bundle_name, bundle in bundles.items():
            # copy contents
            contents = list(bundle.contents)
            for i, item in enumerate(bundle.contents):
                if item in bundles:
                    contents[i] = bundles[item]
                elif known_bundles and item in known_bundles:
                    contents[i] = known_bundles[item]
            # cast back to a tuple
            contents = tuple(contents)
            if contents != bundle.contents:
                bundle.contents = contents
        return bundles

    def _open(self):
        """Returns a (fileobj, filename) tuple.

        The filename can be False if it is unknown.
        """
        if isinstance(self.file_or_filename, six.string_types):
            return open(self.file_or_filename), self.file_or_filename

        file = self.file_or_filename
        return file, getattr(file, 'name', False)

    def load_bundles(self, environment=None):
        """Load a list of :class:`Bundle` instances defined in the YAML file.

        Expects the following format:

        .. code-block:: yaml

            bundle-name:
                filters: sass,cssutils
                output: cache/default.css
                contents:
                    - css/jquery.ui.calendar.css
                    - css/jquery.ui.slider.css
            another-bundle:
                # ...

        Bundles may reference each other:

        .. code-block:: yaml

            js-all:
                contents:
                    - jquery.js
                    - jquery-ui    # This is a bundle reference
            jquery-ui:
                contents: jqueryui/*.js

        If an ``environment`` argument is given, it's bundles
        may be referenced as well. Note that you may pass any
        compatibly dict-like object.

        Finally, you may also use nesting:

        .. code-block:: yaml

            js-all:
                contents:
                    - jquery.js
                    # This is a nested bundle
                    - contents: "*.coffee"
                      filters: coffeescript

        """
        # TODO: Support a "consider paths relative to YAML location, return
        # as absolute paths" option?
        f, _ = self._open()
        try:
            obj = self.yaml.load(f) or {}
            return self._get_bundles(obj, environment)
        finally:
            f.close()

    def load_environment(self):
        """Load an :class:`Environment` instance defined in the YAML file.

        Expects the following format:

        .. code-block:: yaml

            directory: ../static
            url: /media
            debug: True
            updater: timestamp
            config:
                compass_bin: /opt/compass
                another_custom_config_value: foo

            bundles:
                # ...

        All values, including ``directory`` and ``url`` are optional. The
        syntax for defining bundles is the same as for
        :meth:`~.YAMLLoader.load_bundles`.

        Sample usage::

            from webassets.loaders import YAMLLoader
            loader = YAMLLoader('asset.yml')
            env = loader.load_environment()

            env['some-bundle'].urls()
        """
        f, filename = self._open()
        try:
            obj = self.yaml.load(f) or {}

            env = Environment()

            # Load environment settings
            for setting in ('debug', 'cache', 'versions', 'url_expire',
                            'auto_build', 'url', 'directory', 'manifest', 'load_path',
                            # TODO: The deprecated values; remove at some point
                            'expire', 'updater'):
                if setting in obj:
                    setattr(env, setting, obj[setting])

            # Treat the 'directory' option special, make it relative to the
            # path of the YAML file, if we know it.
            if filename and 'directory' in env.config:
                env.directory = path.normpath(
                    path.join(path.dirname(filename),
                              env.config['directory']))

            # Load custom config options
            if 'config' in obj:
                env.config.update(obj['config'])

            # Load bundles
            bundles = self._get_bundles(obj.get('bundles', {}))
            for name, bundle in six.iteritems(bundles):
                env.register(name, bundle)

            return env
        finally:
            f.close()


class PythonLoader(object):
    """Basically just a simple helper to import a Python file and
    retrieve the bundles defined there.
    """

    environment = "environment"

    def __init__(self, module_name):
        if isinstance(module_name, types.ModuleType):
            self.module = module_name
        else:
            sys.path.insert(0, '')  # Ensure the current directory is on the path
            try:
                try:
                    if ":" in module_name:
                        module_name, env = module_name.split(":")
                        self.environment = env
                    self.module = import_module(module_name)
                except ImportError as e:
                    raise LoaderError(e)
            finally:
                sys.path.pop(0)

    def load_bundles(self):
        """Load ``Bundle`` objects defined in the Python module.

        Collects all bundles in the global namespace.
        """
        bundles = {}
        for name in dir(self.module):
            value = getattr(self.module, name)
            if isinstance(value, Bundle):
                bundles[name] = value
        return bundles

    def load_environment(self):
        """Load an ``Environment`` defined in the Python module.

        Expects as default a global name ``environment`` to be defined,
        or overriden by passing a string ``module:environent`` to the
        constructor.
        """
        try:
            return getattr(self.module, self.environment)
        except AttributeError as e:
            raise LoaderError(e)


def recursive_glob(treeroot, pattern):
    """
    From:
    http://stackoverflow.com/questions/2186525/2186639#2186639
    """
    results = []
    for base, dirs, files in os.walk(treeroot):
        goodfiles = fnmatch.filter(files, pattern)
        results.extend(os.path.join(base, f) for f in goodfiles)
    return results


class GlobLoader(object):
    """Base class with some helpers for loaders which need to search
    for files.
    """

    def glob_files(self, f, recursive=False):
        if isinstance(f, tuple):
            return iter(recursive_glob(f[0], f[1]))
        else:
            return iter(glob.glob(f))

    def with_file(self, filename, then_run):
        """Call ``then_run`` with the file contents.
        """
        file = open(filename, 'rb')
        try:
            contents = file.read()
            try:
                return then_run(filename, contents)
            except LoaderError:
                # We can't handle this file.
                pass
        finally:
            file.close()
