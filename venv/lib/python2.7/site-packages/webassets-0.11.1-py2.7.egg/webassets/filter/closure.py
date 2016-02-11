"""Minify Javascript with `Google Closure Compiler
<https://code.google.com/p/closure-compiler/>`_.

Google Closure Compiler is an external tool written in Java, which needs
to be available. One way to get it is to install the
`closure <http://pypi.python.org/pypi/closure>`_ package::

    pip install closure

No configuration is necessary in this case.

You can also define a ``CLOSURE_COMPRESSOR_PATH`` setting that
points to the ``.jar`` file. Otherwise, an environment variable by
the same name is tried. The filter will also look for a ``JAVA_HOME``
environment variable to run the ``.jar`` file, or will otherwise
assume that ``java`` is on the system path.

Supported configuration options:

CLOSURE_COMPRESSOR_OPTIMIZATION
    Corresponds to Google Closure's `compilation level parameter
    <https://code.google.com/closure/compiler/docs/compilation_levels.html>`_.

CLOSURE_EXTRA_ARGS
    A list of further options to be passed to the Closure compiler.
    There are a lot of them.

    For options which take values you want to use two items in the list::

        ['--output_wrapper', 'foo: %output%']
"""

from __future__ import absolute_import
from webassets.filter import JavaTool


__all__ = ('ClosureJS',)


class ClosureJS(JavaTool):

    name = 'closure_js'
    options = {
        'opt': 'CLOSURE_COMPRESSOR_OPTIMIZATION',
        'extra_args': 'CLOSURE_EXTRA_ARGS',
    }

    def setup(self):
        super(ClosureJS, self).setup()

        try:
            self.jar = self.get_config('CLOSURE_COMPRESSOR_PATH',
                                       what='Google Closure Compiler')
        except EnvironmentError:
            try:
                import closure
                self.jar = closure.get_jar_filename()
            except ImportError:
                raise EnvironmentError(
                    "\nClosure Compiler jar can't be found."
                    "\nPlease either install the closure package:"
                    "\n\n    pip install closure\n"
                    "\nor provide a CLOSURE_COMPRESSOR_PATH setting "
                    "or an environment variable with the full path to "
                    "the Closure compiler jar."
                )

    def output(self, _in, out, **kw):
        args = ['--charset', 'UTF-8',
                '--compilation_level', self.opt or 'WHITESPACE_ONLY']
        if self.extra_args:
            args.extend(self.extra_args)
        self.subprocess(args, out, _in)
