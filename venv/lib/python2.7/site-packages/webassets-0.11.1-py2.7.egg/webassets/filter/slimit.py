from __future__ import absolute_import
from webassets.filter import Filter


__all__ = ('Slimit',)


class Slimit(Filter):
    """Minifies JS.

    Requires the ``slimit`` package (https://github.com/rspivak/slimit),
    which is a JavaScript minifier written in Python. It compiles JavaScript
    into more compact code so that it downloads and runs faster.

    Right now it does not use the mangle options to its minifier.
    """

    name = 'slimit'

    def setup(self):
        try:
            import slimit
        except ImportError:
            raise EnvironmentError('The "slimit" package is not installed.')
        else:
            self.slimit = slimit

    def output(self, _in, out, **kw):
        out.write(self.slimit.minify(_in.read()))
