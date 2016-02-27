from __future__ import with_statement

import shlex
from os import path, getcwd

from webassets.filter import ExternalTool


class RequireJSFilter(ExternalTool):
    '''
    Optimizes AMD-style modularized JavaScript into a single asset
    using `RequireJS <http://requirejs.org/>`_.

    This depends on the NodeJS executable ``r.js``; install via npm::

        $ npm install -g requirejs

    Details on configuring r.js can be found at
    http://requirejs.org/docs/optimization.html#basics.

    *Supported configuration options*:

    executable (env: REQUIREJS_BIN)

        Path to the RequireJS executable used to compile source
        files. By default, the filter will attempt to run ``r.js`` via
        the system path.

    config (env: REQUIREJS_CONFIG)

        The RequireJS options file. The path is taken to be relative
        to the Enviroment.directory (by defualt is /static).


    baseUrl (env: REQUIREJS_BASEURL)

        The ``baseUrl`` parameter to r.js; this is the directory that
        AMD modules will be loaded from. The path is taken relative
        to the Enviroment.directory (by defualt is /static).
        Typically, this is used in
        conjunction with a ``baseUrl`` parameter set in the `config`
        options file, where the baseUrl value in the config file is
        used for client-side processing, and the value here is for
        server-side processing.

    optimize (env: REQUIREJS_OPTIMIZE)

        The ``optimize`` parameter to r.js; controls whether or not
        r.js minifies the output. By default, it is enabled, but can
        be set to ``none`` to disable minification. The typical
        scenario to disable minification is if you do some additional
        processing of the JavaScript (such as removing
        ``console.log()`` lines) before minification by the ``rjsmin``
        filter.

    extras (env: REQUIREJS_EXTRAS)

        Any other command-line parameters to be passed to r.js. The
        string is expected to be in unix shell-style format, meaning
        that quotes can be used to escape spaces, etc.

    run_in_debug (env: REQUIREJS_RUN_IN_DEBUG)

        Boolean which controls if the AMD requirejs is evaluated
        client-side or server-side in debug mode. If set to a truthy
        value (e.g. 'yes'), then server-side compilation is done, even
        in debug mode. The default is false.

    .. admonition:: Client-side AMD evaluation

        AMD modules can be loaded client-side without any processing
        done on the server-side. The advantage to this is that
        debugging is easier because the browser can tell you which
        source file is responsible for a particular line of code. The
        disadvantage is that it means that each loaded AMD module is a
        separate HTTP request. When running client-side, the client
        needs access to the `config` -- for this reason, when running
        in client-side mode, the webassets environment must be
        adjusted to include a reference to this
        configuration. Typically, this is done by adding something
        similar to the following during webassets initialization:

        .. code-block:: python

            if env.debug and not env.config.get('requirejs_run_in_debug', True):
                env['requirejs'].contents += ('requirejs-browser-config.js',)

        And the file ``requirejs-browser-config.js`` will look
        something like:

        .. code-block:: js

            require.config({baseUrl: '/static/script/'});

        Set the `run_in_debug` option to control client-side or
        server-side compilation in debug.
    '''

    name    = 'requirejs'
    method  = 'open'
    options = {
      'executable'    : ('executable',    'REQUIREJS_BIN'),
      'config'        : ('config',        'REQUIREJS_CONFIG'),
      'baseUrl'       : ('baseUrl',       'REQUIREJS_BASEURL'),
      'optimize'      : ('optimize',      'REQUIREJS_OPTIMIZE'),
      'extras'        : ('extras',        'REQUIREJS_EXTRAS'),
      'run_in_debug'  : ('run_in_debug',  'REQUIREJS_RUN_IN_DEBUG'),
    }

    max_debug_level = None

    def setup(self):
        super(RequireJSFilter, self).setup()
        # todo: detect if `r.js` is installed...
        if not self.run_in_debug:
            # Disable running in debug mode for this instance.
            self.max_debug_level = False

        if self.executable:
            self.argv = shlex.split(self.executable)
        else:
            self.argv = ['r.js']

        if self.config:
            rel_config = path.join(
                path.relpath(
                    self.ctx.directory,
                    getcwd()
                ),
                self.config
            )
        if not self.baseUrl:
            self.baseUrl = path.relpath(
                self.ctx.directory,
                getcwd()
            )

        self.argv.extend(
            filter(
                None,
                ['-o',
                 rel_config if self.config else None,
                 'name={modname}',
                 'out={{output}}',
                 'baseUrl=' + self.baseUrl if self.baseUrl else None,
                 'optimize=' + self.optimize if self.optimize else None,
             ])
        )
        if self.extras:
            self.argv.extend(shlex.split(self.extras))

    def open(self, out, source_path, **kw):
        if self.ctx.debug and not self.run_in_debug:
            with open(source_path, 'rb') as fp:
                out.write(fp.read())
            return
        # extract the AMD module name
        name = kw.get('source')
        if not name:
            base = path.abspath(self.baseUrl)
            name = path.abspath(source_path)
            if not name.startswith(base):
                raise ValueError(
                    'requested AMD script "%s" does not exist in baseUrl "%s"'
                    % (source_path, self.baseUrl))
            name = name[len(base) + 1:]
        kw['modname'] = path.splitext(name)[0]
        return super(RequireJSFilter, self).open(out, source_path, **kw)
