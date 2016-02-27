from __future__ import with_statement

from webassets.filter import ExternalTool
from webassets.utils import working_directory


class AutoprefixerFilter(ExternalTool):
    """Prefixes vendor-prefixes using `autoprefixer
    <https://github.com/ai/autoprefixer>`, which uses the `Can I Use?
    <http://www.caniuse.com>` database to know which prefixes need to be
    inserted.

    This depends on the `autoprefixer <https://github.com/ai/autoprefixer>`
    command line tool being installed (use ``npm install autoprefixer``).

    *Supported configuration options*:

    AUTOPREFIXER_BIN
        Path to the autoprefixer executable used to compile source files. By
        default, the filter will attempt to run ``autoprefixer`` via the
        system path.

    AUTOPREFIXER_BROWSERS
        The browser expressions to use.  This corresponds to the ``--browsers
        <value>`` flag, see the `--browsers documentation
        <https://github.com/ai/autoprefixer#browsers>`.  By default, this flag
        won't be passed, and autoprefixer's default will be used.

        Example::

            AUTOPREFIXER_BROWSERS = ['> 1%', 'last 2 versions', 'firefox 24', 'opera 12.1']

    AUTOPREFIXER_EXTRA_ARGS
        Additional options may be passed to ``autoprefixer`` using this
        setting, which expects a list of strings.

    """
    name = 'autoprefixer'
    options = {
        'autoprefixer': 'AUTOPREFIXER_BIN',
        'browsers': 'AUTOPREFIXER_BROWSERS',
        'extra_args': 'AUTOPREFIXER_EXTRA_ARGS',
    }

    def input(self, in_, out, source_path, **kw):
        # Set working directory to the source file so that includes are found
        args = [self.autoprefixer or 'autoprefixer']
        if self.browsers:
            if isinstance(self.browsers, (list, tuple)):
                self.browsers = u','.join(self.browsers)
            args.extend(['--browsers', self.browsers])
        if self.extra_args:
            args.extend(self.extra_args)
        with working_directory(filename=source_path):
            self.subprocess(args, out, in_)
