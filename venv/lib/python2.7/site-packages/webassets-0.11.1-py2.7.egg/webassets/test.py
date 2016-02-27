"""Helpers for testing webassets.

This is included in the webassets package because it is useful for testing
external libraries that use webassets (like the flask-assets wrapper).
"""
from __future__ import print_function

import tempfile
import shutil
import os
from os import path
import time

from webassets import Environment, Bundle
from webassets.six.moves import map
from webassets.six.moves import zip


__all__ = ('TempDirHelper', 'TempEnvironmentHelper',)


class TempDirHelper(object):
    """Base-class for tests which provides a temporary directory
    (which is properly deleted after the test is done), and various
    helper methods to do filesystem operations within that directory.
    """

    default_files = {}

    def setup(self):
        self._tempdir_created = tempfile.mkdtemp()
        self.create_files(self.default_files)

    def teardown(self):
        shutil.rmtree(self._tempdir_created)

    def __enter__(self):
        self.setup()
        return self

    def __exit__(self, type, value, traceback):
        self.teardown()

    @property
    def tempdir(self):
        # Use a read-only property here, so the user is
        # less likely to modify the attribute, and have
        # his data deleted on teardown.
        return self._tempdir_created

    def create_files(self, files):
        """Helper that allows to quickly create a bunch of files in
        the media directory of the current test run.
        """
        import codecs
        # Allow passing a list of filenames to create empty files
        if not hasattr(files, 'items'):
            files = dict(map(lambda n: (n, ''), files))
        for name, data in files.items():
            dirs = path.dirname(self.path(name))
            if not path.exists(dirs):
                os.makedirs(dirs)
            f = codecs.open(self.path(name), 'w', 'utf-8')
            f.write(data)
            f.close()

    def create_directories(self, *dirs):
        """Helper to create directories within the media directory
        of the current test's environment.
        """
        result = []
        for dir in dirs:
            full_path = self.path(dir)
            result.append(full_path)
            os.makedirs(full_path)
        return result

    def exists(self, name):
        """Ensure the given file exists within the current test run's
        media directory.
        """
        return path.exists(self.path(name))

    def get(self, name):
        """Return the given file's contents.
        """
        with open(self.path(name)) as f:
            r = f.read()
            print(repr(r))
            return r

    def unlink(self, name):
        os.unlink(self.path(name))

    def path(self, name):
        """Return the given file's full path."""
        return path.join(self._tempdir_created, name)

    def setmtime(self, *files, **kwargs):
        """Set the mtime of the given files. Useful helper when
        needing to test things like the timestamp updater.

        Specify ``mtime`` as a keyword argument, or time.time()
        will automatically be used. Returns the mtime used.

        Specify ``mod`` as a keyword argument, and the modifier
        will be added to the ``mtime`` used.
        """
        mtime = kwargs.pop('mtime', time.time())
        mtime += kwargs.pop('mod', 0)
        assert not kwargs, "Unsupported kwargs: %s" %  ', '.join(kwargs.keys())
        for f in files:
            os.utime(self.path(f), (mtime, mtime))
        return mtime

    def p(self, *files):
        """Print the contents of the given files to stdout; useful
        for some quick debugging.
        """
        if not files:
            files = ['out']   # This is a often used output filename
        for f in files:
            content = self.get(f)
            print(f)
            print("-" * len(f))
            print(repr(content))
            print(content)
            print()


class TempEnvironmentHelper(TempDirHelper):
    """Base-class for tests which provides a pre-created
    environment, based in a temporary directory, and utility
    methods to do filesystem operations within that directory.
    """

    default_files = {'in1': 'A', 'in2': 'B', 'in3': 'C', 'in4': 'D'}

    def setup(self):
        TempDirHelper.setup(self)

        self.env = self._create_environment()
        # Unless we explicitly test it, we don't want to use the cache
        # during testing.
        self.env.cache = False
        self.env.manifest = False

    def _create_environment(self):
        return Environment(self._tempdir_created, '')

    def mkbundle(self, *a, **kw):
        b = Bundle(*a, **kw)
        b.env = self.env
        return b
