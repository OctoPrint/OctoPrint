from __future__ import with_statement

import os

from webassets.filter import ExternalTool
from webassets.utils import working_directory


class Less(ExternalTool):
    """Converts `less <http://lesscss.org/>`_ markup to real CSS.

    This depends on the NodeJS implementation of less, installable via npm.
    To use the old Ruby-based version (implemented in the 1.x Ruby gem), see
    :class:`~.less_ruby.Less`.

    *Supported configuration options*:

    LESS_BIN (binary)
        Path to the less executable used to compile source files. By default,
        the filter will attempt to run ``lessc`` via the system path.

    LESS_LINE_NUMBERS (line_numbers)
        Outputs filename and line numbers. Can be either 'comments', which
        will output the debug info within comments, 'mediaquery' that will
        output the information within a fake media query which is compatible
        with the SASSPath to the less executable used to compile source files.

    LESS_RUN_IN_DEBUG (run_in_debug)
        By default, the filter will compile in debug mode. Since the less
        compiler is written in Javascript and capable of running in the
        browser, you can set this to ``False`` to have your original less
        source files served (see below).

    LESS_PATHS (paths)
        Add include paths for less command line.
        It should be a list of paths relatives to Environment.directory or absolute paths.
        Order matters as less will pick the first file found in path order.

    LESS_AS_OUTPUT (boolean)
        By default, this works as an "input filter", meaning ``less`` is
        called for each source file in the bundle. This is because the
        path of the source file is required so that @import directives
        within the Less file can be correctly resolved.

        However, it is possible to use this filter as an "output filter",
        meaning the source files will first be concatenated, and then the
        Less filter is applied in one go. This can provide a speedup for
        bigger projects.

    .. admonition:: Compiling less in the browser

        less is an interesting case because it is written in Javascript and
        capable of running in the browser. While for performance reason you
        should prebuild your stylesheets in production, while developing you
        may be interested in serving the original less files to the client,
        and have less compile them in the browser.

        To do so, you first need to make sure the less filter is not applied
        when :attr:`Environment.debug` is ``True``. You can do so via an
        option::

            env.config['less_run_in_debug'] = False

        Second, in order for the less to identify the  less source files as
        needing to be compiled, they have to be referenced with a
        ``rel="stylesheet/less"`` attribute. One way to do this is to use the
        :attr:`Bundle.extra` dictionary, which works well with the template
        tags that webassets provides for some template languages::

            less_bundle = Bundle(
                '**/*.less',
                filters='less',
                extra={'rel': 'stylesheet/less' if env.debug else 'stylesheet'}
            )

        Then, for example in a Jinja2 template, you would write::

            {% assets less_bundle %}
                <link rel="{{ EXTRA.rel }}" type="text/css" href="{{ ASSET_URL }}">
            {% endassets %}

        With this, the ``<link>`` tag will sport the correct ``rel`` value both
        in development and in production.

        Finally, you need to include the less compiler::

            if env.debug:
                js_bundle.contents += 'http://lesscss.googlecode.com/files/less-1.3.0.min.js'
    """

    name = 'less'
    options = {
        'less': ('binary', 'LESS_BIN'),
        'run_in_debug': 'LESS_RUN_IN_DEBUG',
        'line_numbers': 'LESS_LINE_NUMBERS',
        'extra_args': 'LESS_EXTRA_ARGS',
        'paths': 'LESS_PATHS',
        'as_output': 'LESS_AS_OUTPUT'
    }
    max_debug_level = None

    def setup(self):
        super(Less, self).setup()
        if self.run_in_debug is False:
            # Disable running in debug mode for this instance.
            self.max_debug_level = False

    def resolve_source(self, path):
        return self.ctx.resolver.resolve_source(self.ctx, path)

    def _apply_less(self, in_, out, source_path=None, **kw):
        # Set working directory to the source file so that includes are found
        args = [self.less or 'lessc']
        if self.line_numbers:
            args.append('--line-numbers=%s' % self.line_numbers)

        if self.paths:
            paths = [
                path if os.path.isabs(path) else self.resolve_source(path)
                for path in self.paths
            ]
            args.append('--include-path={0}'.format(os.pathsep.join(paths)))

        if self.extra_args:
            args.extend(self.extra_args)

        args.append('-')

        if source_path:
            with working_directory(filename=source_path):
                self.subprocess(args, out, in_)
        else:
            self.subprocess(args, out, in_)

    def input(self, _in, out, source_path, output_path, **kw):
        if self.as_output:
            out.write(_in.read())
        else:
            self._apply_less(_in, out, source_path)

    def output(self, _in, out, **kwargs):
        if not self.as_output:
            out.write(_in.read())
        else:
            self._apply_less(_in, out)
