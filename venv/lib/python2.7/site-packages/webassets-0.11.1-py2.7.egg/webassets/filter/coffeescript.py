from __future__ import print_function
import os, subprocess

from webassets.filter import Filter
from webassets.exceptions import FilterError, ImminentDeprecationWarning


__all__ = ('CoffeeScript',)


class CoffeeScript(Filter):
    """Converts `CoffeeScript <http://jashkenas.github.com/coffee-script/>`_
    to real JavaScript.

    If you want to combine it with other JavaScript filters, make sure this
    one runs first.

    Supported configuration options:

    COFFEE_NO_BARE
        Set to ``True`` to compile with the top-level function
        wrapper (suppresses the --bare option to ``coffee``, which
        is used by default).
    """

    name = 'coffeescript'
    max_debug_level = None
    options = {
        'coffee_deprecated': (False, 'COFFEE_PATH'),
        'coffee_bin': ('binary', 'COFFEE_BIN'),
        'no_bare': 'COFFEE_NO_BARE',
    }

    def output(self, _in, out, **kw):
        binary = self.coffee_bin or self.coffee_deprecated or 'coffee'
        if self.coffee_deprecated:
            import warnings
            warnings.warn(
                'The COFFEE_PATH option of the "coffeescript" '
                +'filter has been deprecated and will be removed.'
                +'Use COFFEE_BIN instead.', ImminentDeprecationWarning)

        args = "-sp" + ("" if self.no_bare else 'b')
        try:
            proc = subprocess.Popen([binary, args],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=(os.name == 'nt'))
        except OSError as e:
            if e.errno == 2:
                raise Exception("coffeescript not installed or in system path for webassets")
            raise
        stdout, stderr = proc.communicate(_in.read().encode('utf-8'))
        if proc.returncode != 0:
            raise FilterError(('coffeescript: subprocess had error: stderr=%s, '+
                               'stdout=%s, returncode=%s') % (
                stderr, stdout, proc.returncode))
        elif stderr:
            print("coffeescript filter has warnings:", stderr)
        out.write(stdout.decode('utf-8'))

