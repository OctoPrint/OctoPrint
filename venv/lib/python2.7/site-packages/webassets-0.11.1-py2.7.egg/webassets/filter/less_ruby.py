import time
import os, subprocess
import tempfile

from webassets.filter import Filter
from webassets.exceptions import FilterError


__all__ = ('Less',)


class Less(Filter):
    """Converts `Less <http://lesscss.org/>`_ markup to real CSS.

    This uses the old Ruby implementation available in the 1.x versions of the
    less gem. All 2.x versions of the gem are wrappers around the newer
    NodeJS/Javascript implementation, which you are generally encouraged to
    use, and which is available in webassets via the :class:`~.filter.less.Less`
    filter.

    This filter for the Ruby version is being kept around for
    backwards-compatibility.

    *Supported configuration options*:

    LESS_RUBY_PATH (binary)
        Path to the less executable used to compile source files. By default,
        the filter will attempt to run ``lessc`` via the system path.
    """

    # XXX Deprecate this one.
    """
    XXX: Depending on how less is actually used in practice, it might actually
    be a valid use case to NOT have this be a source filter, so that one can
    split the css files into various less files, referencing variables in other
    files' - without using @include, instead having them merged together by
    django-assets. This will currently not work because we compile each
    file separately, and the compiler would fail at undefined variables.
    """

    name = 'less_ruby'
    options = {
        'less': ('binary', 'LESS_RUBY_PATH')
    }
    max_debug_level = None

    def open(self, out, sourcePath, **kw):
        """Less currently doesn't take data from stdin, and doesn't allow
        us from stdout either. Neither does it return a proper non-0 error
        code when an error occurs, or even write to stderr (stdout instead)!

        Hopefully this will improve in the future:

        http://groups.google.com/group/lesscss/browse_thread/thread/3aed033a44c51b4c/b713148afde87e81
        """
        # TODO: Use NamedTemporaryFile.
        outtemp_name = os.path.join(tempfile.gettempdir(),
                                    'assets_temp_%d.css' % int(time.time()))

        proc = subprocess.Popen(
            [self.less or 'lessc', sourcePath, outtemp_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            # shell: necessary on windows to execute
            # ruby files, but doesn't work on linux.
            shell=(os.name == 'nt'))
        stdout, stderr = proc.communicate()

        # less only writes to stdout, as noted in the method doc, but
        # check everything anyway.
        if stdout or stderr or proc.returncode != 0:
            if os.path.exists(outtemp_name):
                os.unlink(outtemp_name)
            raise FilterError(('less: subprocess had error: stderr=%s, '+
                               'stdout=%s, returncode=%s') % (
                                            stderr, stdout, proc.returncode))

        outtemp = open(outtemp_name)
        try:
            out.write(outtemp.read())
        finally:
            outtemp.close()

            os.unlink(outtemp_name)
