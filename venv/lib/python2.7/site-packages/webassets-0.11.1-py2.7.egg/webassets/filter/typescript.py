import os
import subprocess
import tempfile
from io import open   # Give 2 and 3 use same newline behaviour.

from webassets.filter import Filter
from webassets.exceptions import FilterError


__all__ = ('TypeScript',)



class TypeScript(Filter):
    """Compile  `TypeScript <http://www.typescriptlang.org>`_ to JavaScript.

    TypeScript is an external tool written for NodeJS.
    This filter assumes that the ``tsc`` executable is in the path. Otherwise, you
    may define the ``TYPESCRIPT_BIN`` setting.
    """

    name = 'typescript'
    max_debug_level = None
    options = {
        'binary': 'TYPESCRIPT_BIN',
    }

    def output(self, _in, out, **kw):
        # The typescript compiler cannot read a file which does not have
        # the .ts extension. The output file needs to have an extension,
        # or the compiler will want to create a directory in its place.
        input_filename = tempfile.mktemp() + ".ts"
        output_filename = tempfile.mktemp() + ".js"

        with open(input_filename, 'w') as f:
            f.write(_in.read())

        args = [self.binary or 'tsc', '--out', output_filename, input_filename]
        proc = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=(os.name == 'nt'))
        stdout, stderr = proc.communicate()
        if proc.returncode != 0:
            raise FilterError("typescript: subprocess had error: stderr=%s," % stderr +
                "stdout=%s, returncode=%s" % (stdout, proc.returncode))

        with open(output_filename, 'r') as f:
            out.write(f.read())

        os.unlink(input_filename)
        os.unlink(output_filename)
