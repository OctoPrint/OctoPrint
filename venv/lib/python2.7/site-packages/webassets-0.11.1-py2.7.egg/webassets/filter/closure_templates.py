"""Client Side Templating with `Google Closure Templates
<https://code.google.com/p/closure-templates/>`_.

Google Closure Templates is an external tool written in Java, which needs
to be available. One way to get it is to install the
`closure-soy <http://pypi.python.org/pypi/closure-soy>`_ package::

    pip install closure-soy

No configuration is necessary in this case.

You can also define a ``CLOSURE_TEMPLATES_PATH`` setting that
points to the ``.jar`` file. Otherwise, an environment variable by
the same name is tried. The filter will also look for a ``JAVA_HOME``
environment variable to run the ``.jar`` file, or will otherwise
assume that ``java`` is on the system path.

Supported configuration options:

CLOSURE_EXTRA_ARGS
    A list of further options to be passed to the Closure compiler.
    There are a lot of them.

    For options which take values you want to use two items in the list::

        ['--inputPrefix', 'prefix']
"""

import subprocess
import os
import tempfile

from webassets.exceptions import FilterError
from webassets.filter.jst import JSTemplateFilter


__all__ = ('ClosureTemplateFilter',)


class ClosureTemplateFilter(JSTemplateFilter):
    name = 'closure_tmpl'
    options = {
        'extra_args': 'CLOSURE_EXTRA_ARGS',
    }

    def process_templates(self, out,  hunks, **kw):
        templates = [info['source_path'] for _, info in hunks]

        temp = tempfile.NamedTemporaryFile(dir='.', delete=True)
        args = ["--outputPathFormat", temp.name, '--srcs']
        args.extend(templates)
        if self.extra_args:
            args.extend(self.extra_args)
        self.java_run(args)
        out.write(open(temp.name).read())

    def setup(self):
        super(ClosureTemplateFilter, self).setup()
        try:
            self.jar = self.get_config('CLOSURE_TEMPLATES_PATH',
                    what='Google Closure Soy Templates Compiler')
        except EnvironmentError:
            try:
                import closure_soy
                self.jar = closure_soy.get_jar_filename()
            except ImportError:
                raise EnvironmentError(
                    "\nClosure Templates jar can't be found."
                    "\nPlease either install the closure package:"
                    "\n\n    pip install closure-soy\n"
                    "\nor provide a CLOSURE_TEMPLATES_PATH setting "
                    "or an environment variable with the full path to "
                    "the Closure compiler jar."
                )
        self.java_setup()
        super(ClosureTemplateFilter, self).setup()

    def java_setup(self):
        # We can reasonably expect that java is just on the path, so
        # don't require it, but hope for the best.
        path = self.get_config(env='JAVA_HOME', require=False)
        if path is not None:
            self.java = os.path.join(path, 'bin/java')
        else:
            self.java = 'java'

    def java_run(self, args):
        proc = subprocess.Popen(
            [self.java, '-jar', self.jar] + args,
            # we cannot use the in/out streams directly, as they might be
            # StringIO objects (which are not supported by subprocess)
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=(os.name == 'nt'))
        stdout, stderr = proc.communicate()
        if proc.returncode:
            raise FilterError('%s: subprocess returned a '
                'non-success result code: %s, stdout=%s, stderr=%s' % (
                     self.name, proc.returncode, stdout, stderr))
