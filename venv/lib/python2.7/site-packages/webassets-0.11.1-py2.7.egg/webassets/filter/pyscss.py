import os

from webassets.filter import Filter
from webassets.utils import working_directory


__all__ = ('PyScss',)


class PyScss(Filter):
    """Converts `Scss <http://sass-lang.com/>`_ markup to real CSS.

    This uses `PyScss <https://github.com/Kronuz/pyScss>`_, a native
    Python implementation of the Scss language. The PyScss module needs
    to be installed. It's API has been changing; currently, version
    1.1.5 is known to be supported.

    This is an alternative to using the ``sass`` or ``scss`` filters,
    which are based on the original, external tools.

    .. note::
        The Sass syntax is not supported by PyScss. You need to use
        the ``sass`` filter based on the original Ruby implementation
        instead.

    *Supported configuration options:*

    PYSCSS_DEBUG_INFO (debug_info)
        Include debug information in the output for use with FireSass.

        If unset, the default value will depend on your
        :attr:`Environment.debug` setting.

    PYSCSS_LOAD_PATHS (load_paths)
        Additional load paths that PyScss should use.

        .. warning::
            The filter currently does not automatically use
            :attr:`Environment.load_path` for this.

    PYSCSS_STATIC_ROOT (static_root)
        The directory PyScss should look in when searching for include
        files that you have referenced. Will use
        :attr:`Environment.directory` by default.

    PYSCSS_STATIC_URL (static_url)
        The url PyScss should use when generating urls to files in
        ``PYSCSS_STATIC_ROOT``. Will use :attr:`Environment.url` by
        default.

    PYSCSS_ASSETS_ROOT (assets_root)
        The directory PyScss should look in when searching for things
        like images that you have referenced. Will use
        ``PYSCSS_STATIC_ROOT`` by default.

    PYSCSS_ASSETS_URL (assets_url)
        The url PyScss should use when generating urls to files in
        ``PYSCSS_ASSETS_ROOT``. Will use ``PYSCSS_STATIC_URL`` by
        default.

    PYSCSS_STYLE (style)
        The style of the output CSS. Can be one of ``nested`` (default),
        ``compact``, ``compressed``, or ``expanded``.
    """

    # TODO: PyScss now allows STATIC_ROOT to be a callable, though
    # none of the other pertitent values are allowed to be, so this
    # is probably not good enough for us.

    name = 'pyscss'
    options = {
        'debug_info': 'PYSCSS_DEBUG_INFO',
        'load_paths': 'PYSCSS_LOAD_PATHS',
        'static_root': 'PYSCSS_STATIC_ROOT',
        'static_url': 'PYSCSS_STATIC_URL',
        'assets_root': 'PYSCSS_ASSETS_ROOT',
        'assets_url': 'PYSCSS_ASSETS_URL',
        'style': 'PYSCSS_STYLE',
    }
    max_debug_level = None

    def setup(self):
        super(PyScss, self).setup()

        import scss
        self.scss = scss

        if self.style:
            try:
                from packaging.version import Version
            except ImportError:
                from distutils.version import LooseVersion as Version
            assert Version(scss.__version__) >= Version('1.2.0'), \
                'PYSCSS_STYLE only supported in pyScss>=1.2.0'

        # Initialize various settings:
        # Why are these module-level, not instance-level ?!
        # TODO: It appears that in the current dev version, the
        # settings can finally passed to a constructor. We'll need
        # to support this.

        # Only the dev version appears to support a list
        if self.load_paths:
            scss.config.LOAD_PATHS = ','.join(self.load_paths)

        # These are needed for various helpers (working with images
        # etc.). Similar to the compass filter, we require the user
        # to specify such paths relative to the media directory.
        try:
            scss.config.STATIC_ROOT = self.static_root or self.ctx.directory
            scss.config.STATIC_URL = self.static_url or self.ctx.url
        except EnvironmentError:
            raise EnvironmentError('Because Environment.url and/or '
                'Environment.directory are not set, you need to '
                'provide values for the PYSCSS_STATIC_URL and/or '
                'PYSCSS_STATIC_ROOT settings.')

        # This directory PyScss will use when generating new files,
        # like a spritemap. Maybe we should REQUIRE this to be set.
        scss.config.ASSETS_ROOT = self.assets_root or scss.config.STATIC_ROOT
        scss.config.ASSETS_URL = self.assets_url or scss.config.STATIC_URL

    def input(self, _in, out, **kw):
        """Like the original sass filter, this also needs to work as
        an input filter, so that relative @imports can be properly
        resolved.
        """

        source_path = kw['source_path']

        # Because PyScss always puts the current working dir at first
        # place of the load path, this is what we need to use to make
        # relative references work.
        with working_directory(os.path.dirname(source_path)):

            scss_opts = {
                'debug_info': (
                    self.ctx.environment.debug if self.debug_info is None else self.debug_info),
            }
            if self.style:
                scss_opts['style'] = self.style
            else:
                scss_opts['compress'] = False

            scss = self.scss.Scss(
                scss_opts=scss_opts,
                # This is rather nice. We can pass along the filename,
                # but also give it already preprocessed content.
                scss_files={source_path: _in.read()})

            # Compile
            # Note: This will not throw an error when certain things
            # are wrong, like an include file missing. It merely outputs
            # to stdout, via logging. We might have to do something about
            # this, and evaluate such problems to an exception.
            out.write(scss.compile())
