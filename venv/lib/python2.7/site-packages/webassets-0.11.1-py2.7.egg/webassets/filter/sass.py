from __future__ import print_function
import os, subprocess

from webassets.filter import Filter
from webassets.exceptions import FilterError, ImminentDeprecationWarning
from webassets.cache import FilesystemCache


__all__ = ('Sass', 'SCSS')


class Sass(Filter):
    """Converts `Sass <http://sass-lang.com/>`_ markup to real CSS.

    Requires the Sass executable to be available externally. To install
    it, you might be able to do::

         $ sudo gem install sass

    By default, this works as an "input filter", meaning ``sass`` is
    called for each source file in the bundle. This is because the
    path of the source file is required so that @import directives
    within the Sass file can be correctly resolved.

    However, it is possible to use this filter as an "output filter",
    meaning the source files will first be concatenated, and then the
    Sass filter is applied in one go. This can provide a speedup for
    bigger projects.

    To use Sass as an output filter::

        from webassets.filter import get_filter
        sass = get_filter('sass', as_output=True)
        Bundle(...., filters=(sass,))

    However, if you want to use the output filter mode and still also
    use the @import directive in your Sass files, you will need to
    pass along the ``load_paths`` argument, which specifies the path
    to which the imports are relative to (this is implemented by
    changing the working directory before calling the ``sass``
    executable)::

        sass = get_filter('sass', as_output=True, load_paths='/tmp')

    With ``as_output=True``, the resulting concatenation of the Sass
    files is piped to Sass via stdin (``cat ... | sass --stdin ...``)
    and may cause applications to not compile if import statements are
    given as relative paths.

    For example, if a file ``foo/bar/baz.scss`` imports file
    ``foo/bar/bat.scss`` (same directory) and the import is defined as
    ``@import "bat";`` then Sass will fail compiling because Sass
    has naturally no information on where ``baz.scss`` is located on
    disk (since the data was passed via stdin) in order for Sass to
    resolve the location of ``bat.scss``::

        Traceback (most recent call last):
        ...
        webassets.exceptions.FilterError: sass: subprocess had error: stderr=(sass):1: File to import not found or unreadable: bat. (Sass::SyntaxError)
               Load paths:
                 /path/to/project-foo
                on line 1 of standard input
          Use --trace for backtrace.
        , stdout=, returncode=65

    To overcome this issue, the full path must be provided in the
    import statement, ``@import "foo/bar/bat"``, then webassets
    will pass the ``load_paths`` argument (e.g.,
    ``/path/to/project-foo``) to Sass via its ``-I`` flags so Sass can
    resolve the full path to the file to be imported:
    ``/path/to/project-foo/foo/bar/bat``

    Support configuration options:

    SASS_BIN
        The path to the Sass binary. If not set, the filter will
        try to run ``sass`` as if it's in the system path.

    SASS_STYLE
        The style for the output CSS. Can be one of ``expanded`` (default),
        ``nested``, ``compact`` or ``compressed``.

    SASS_DEBUG_INFO
        If set to ``True``, will cause Sass to output debug information
        to be used by the FireSass Firebug plugin. Corresponds to the
        ``--debug-info`` command line option of Sass.

        Note that for this, Sass uses ``@media`` rules, which are
        not removed by a CSS compressor. You will thus want to make
        sure that this option is disabled in production.

        By default, the value of this option will depend on the
        environment ``DEBUG`` setting.

    SASS_LINE_COMMENTS
        Passes ``--line-comments`` flag to sass which emit comments in the
        generated CSS indicating the corresponding source line.

	Note that this option is disabled by Sass if ``--style compressed`` or
        ``--debug-info`` options are provided.

        Enabled by default. To disable, set empty environment variable
        ``SASS_LINE_COMMENTS=`` or pass ``line_comments=False`` to this filter.
    """
    # TODO: If an output filter could be passed the list of all input
    # files, the filter might be able to do something interesting with
    # it (for example, determine that all source files are in the same
    # directory).

    name = 'sass'
    options = {
        'binary': 'SASS_BIN',
        'use_scss': ('scss', 'SASS_USE_SCSS'),
        'use_compass': ('use_compass', 'SASS_COMPASS'),
        'debug_info': 'SASS_DEBUG_INFO',
        'as_output': 'SASS_AS_OUTPUT',
        'load_paths': 'SASS_LOAD_PATHS',
        'libs': 'SASS_LIBS',
        'style': 'SASS_STYLE',
        'line_comments': 'SASS_LINE_COMMENTS',
    }
    max_debug_level = None

    def _apply_sass(self, _in, out, cd=None):
        # Switch to source file directory if asked, so that this directory
        # is by default on the load path. We could pass it via -I, but then
        # files in the (undefined) wd could shadow the correct files.
        orig_cwd = os.getcwd()
        child_cwd = orig_cwd
        if cd:
            child_cwd = cd

        args = [self.binary or 'sass',
                '--stdin',
                '--style', self.style or 'expanded']
        if self.line_comments is None or self.line_comments:
            args.append('--line-comments')
        if isinstance(self.ctx.cache, FilesystemCache):
            args.extend(['--cache-location',
                         os.path.join(orig_cwd, self.ctx.cache.directory, 'sass')])
        elif not cd:
            # Without a fixed working directory, the location of the cache
            # is basically undefined, so prefer not to use one at all.
            args.extend(['--no-cache'])
        if (self.ctx.environment.debug if self.debug_info is None else self.debug_info):
            args.append('--debug-info')
        if self.use_scss:
            args.append('--scss')
        if self.use_compass:
            args.append('--compass')
        for path in self.load_paths or []:
            args.extend(['-I', path])
        for lib in self.libs or []:
            args.extend(['-r', lib])

        proc = subprocess.Popen(args,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                # shell: necessary on windows to execute
                                # ruby files, but doesn't work on linux.
                                shell=(os.name == 'nt'),
                                cwd=child_cwd)
        stdout, stderr = proc.communicate(_in.read().encode('utf-8'))

        if proc.returncode != 0:
            raise FilterError(('sass: subprocess had error: stderr=%s, '+
                               'stdout=%s, returncode=%s') % (
                                            stderr, stdout, proc.returncode))
        elif stderr:
            print("sass filter has warnings:", stderr)

        out.write(stdout.decode('utf-8'))

    def input(self, _in, out, source_path, output_path, **kw):
        if self.as_output:
            out.write(_in.read())
        else:
            self._apply_sass(_in, out, os.path.dirname(source_path))

    def output(self, _in, out, **kwargs):
        if not self.as_output:
            out.write(_in.read())
        else:
            self._apply_sass(_in, out)


class SCSS(Sass):
    """Version of the ``sass`` filter that uses the SCSS syntax.
    """

    name = 'scss'

    def __init__(self, *a, **kw):
        assert not 'scss' in kw
        kw['scss'] = True
        super(SCSS, self).__init__(*a, **kw)
