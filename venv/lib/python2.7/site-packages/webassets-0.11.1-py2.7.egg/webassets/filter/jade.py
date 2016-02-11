# coding=utf-8

from __future__ import print_function
import os, subprocess
from webassets.filter import Filter, register_filter
from webassets.exceptions import FilterError


class Jade(Filter):
    """Converts `Jade <http://jade-lang.com/>`_ templates to client-side
    JavaScript functions.

    Requires the Jade executable to be available externally. You can install it
    using the `Node Package Manager <http://npmjs.org/>`_::

        $ npm install jade

    Jade templates are compiled and stored in a window-level JavaScript object
    under a key corresponding to the template file's basename. For example,
    ``keyboardcat.jade`` compiles into:

        window.templates['keyboardcat'] = function() { ... };

    Supported configuration options:

    JADE_BIN
        The system path to the Jade binary. If not set assumes ``jade`` is in
        the system path.

    JADE_RUNTIME
        The system path to the Jade runtime, ``runtime.js`` which ships with
        Jade. If you installed Jade locally it can be found in:

            node_modules/jade/runtime.js

        Globally, on Ubuntu it's typically located in:

            /usr/lib/node_modules/jade/runtime.js

        Or sometimes:

            /usr/local/lib/node_modules/jade/runtime.js

        If, for some reason you can't find your Jade runtime you can download
        it from the `Jade Repository  <https://github.com/visionmedia/jade/blob/master/runtime.js>`_::
        but do take care to download the runtime version which matches the
        version of your installed Jade.

    JADE_NO_DEBUG
        Omits debugging information to output shorter functions.

    JADE_TEMPLATE_VAR
        The window-level JavaScript object where the compiled Jade objects will
        be stored. By default this defaults to ``templates`` as such:

            window['templates']
    """

    name = 'jade'
    max_debug_level = None
    options = {
        'jade': 'JADE_BIN',
        'jade_runtime': 'JADE_RUNTIME',
        'jade_no_debug': 'JADE_NO_DEBUG',
        'js_var': 'JADE_TEMPLATE_VAR'
    }
    argv = []


    def setup(self):
        """
        Check options and apply defaults if necessary
        """
        super(Jade, self).setup()

        self.argv.append(self.jade or 'jade')
        self.argv.append('--client')

        if self.jade_no_debug:
            self.argv.append('--no-debug')

        if not self.js_var:
            self.js_var = 'templates'


    def input(self, _in, out, **kwargs):
        """
        Compile individual Jade templates
        """
        proc = subprocess.Popen(self.argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=(os.name == 'nt'))
        stdout, stderr = proc.communicate(_in.read())

        if proc.returncode != 0:
            raise FilterError(('jade: subprocess returned a non-success ' +
                'result code: %s, stdout=%s, stderr=%s')
                 % (proc.returncode, stdout, stderr))
        elif stderr:
            print('jade filter has warnings:', stderr)

        # Add a bit of JavaScript that will place our compiled Jade function
        # into an object on the `window` object. Jade files are keyed by their
        # basename.
        key = os.path.splitext(os.path.basename(kwargs['source_path']))[0]
        preamble = "window['%s']['%s'] = " % (self.js_var, key)

        out.write('%s%s' % (preamble, stdout.strip()))


    def output(self, _in, out, **kwargs):
        """
        Prepend Jade runtime and initialize template variable.
        """
        if self.jade_runtime:
            with open(self.jade_runtime) as file:
                runtime = ''.join(file.readlines())

        # JavaScript code to initialize the window-level object that will hold
        # our compiled Jade templates as functions
        init = "if(!window['%s']) { window['%s'] = {}; }" % (self.js_var, self.js_var)

        out.write('%s\n%s\n%s' % (runtime, init, _in.read()))


register_filter(Jade)
