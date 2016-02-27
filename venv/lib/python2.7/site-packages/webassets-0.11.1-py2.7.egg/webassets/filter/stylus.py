import os
from webassets.filter import ExternalTool, option


__all__ = ('Stylus',)


class Stylus(ExternalTool):
    """Converts `Stylus <http://learnboost.github.com/stylus/>`_ markup to CSS.

    Requires the Stylus executable to be available externally. You can install
    it using the `Node Package Manager <http://npmjs.org/>`_::

        $ npm install -g stylus

    Supported configuration options:

    STYLUS_BIN
        The path to the Stylus binary. If not set, assumes ``stylus`` is in the
        system path.

    STYLUS_PLUGINS
        A Python list of Stylus plugins to use. Each plugin will be included
        via Stylus's command-line ``--use`` argument.

    STYLUS_EXTRA_ARGS
        A Python list of any additional command-line arguments.
        
    STYLUS_EXTRA_PATHS
        A Python list of any additional import paths.
    """

    name = 'stylus'
    options = {
        'stylus': 'STYLUS_BIN',
        'plugins': option('STYLUS_PLUGINS', type=list),
        'extra_args': option('STYLUS_EXTRA_ARGS', type=list),
        'extra_paths': option('STYLUS_EXTRA_PATHS', type=list),
    }
    max_debug_level = None

    def input(self, _in, out, **kwargs):
        args = [self.stylus or 'stylus']
        source_dir = os.path.dirname(kwargs['source_path'])
        paths = [source_dir] + (self.extra_paths or [])
        for path in paths:
            args.extend(('--include', path))
        for plugin in self.plugins or []:
            args.extend(('--use', plugin))
        if self.extra_args:
            args.extend(self.extra_args)
        self.subprocess(args, out, _in)
