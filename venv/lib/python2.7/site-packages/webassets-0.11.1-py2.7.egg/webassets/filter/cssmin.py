from __future__ import absolute_import
from webassets.filter import Filter


__all__ = ('CSSMin',)


class CSSMin(Filter):
    """Minifies CSS.

    Requires the ``cssmin`` package (http://github.com/zacharyvoase/cssmin),
    which is a port of the YUI CSS compression algorithm.
    """

    name = 'cssmin'

    def setup(self):
        try:
            import cssmin
        except ImportError:
            raise EnvironmentError('The "cssmin" package is not installed.')
        else:
            self.cssmin = cssmin

    def output(self, _in, out, **kw):
        out.write(self.cssmin.cssmin(_in.read()))
