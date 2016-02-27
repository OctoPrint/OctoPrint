""" Compile and Minify CSS with `Google Closure Stylesheets
<http://code.google.com/p/closure-stylesheets/>`_.

Google Closure Templates is an external tool written in Java, which needs
to be obtained separately.

You must define a ``CLOSURE_STYLESHEETS_PATH`` setting that
points to the ``.jar`` file. Otherwise, an environment variable by
the same name is tried. The filter will also look for a ``JAVA_HOME``
environment variable to run the ``.jar`` file, or will otherwise
assume that ``java`` is on the system path.
"""

from webassets.filter import JavaTool


__all__ = ['ClosureStylesheetsCompiler', 'ClosureStylesheetsMinifier']


class ClosureStylesheetsBase(JavaTool):

    def setup(self):
        super(ClosureStylesheetsBase, self).setup()
        try:
            self.jar = self.get_config('CLOSURE_STYLESHEETS_PATH',
                    what='Google Closure Stylesheets tool')
        except EnvironmentError:
            raise EnvironmentError(
                "\nGoogle Closure Stylesheets jar can't be found."
                "\nPlease provide a CLOSURE_STYLESHEETS_PATH setting "
                "or an environment variable with the full path to "
                "the Google Closure Stylesheets jar."
            )

    def output(self, _in, out, **kw):
        params = []
        if self.mode != 'minify':
            params.append('--pretty-print')
        self.subprocess(
            params + ['{input}'], out, _in)


class ClosureStylesheetsCompiler(ClosureStylesheetsBase):
    name = 'closure_stylesheets_compiler'
    mode = 'compile'


class ClosureStylesheetsMinifier(ClosureStylesheetsBase):
    name = 'closure_stylesheets_minifier'
    mode = 'minify'
