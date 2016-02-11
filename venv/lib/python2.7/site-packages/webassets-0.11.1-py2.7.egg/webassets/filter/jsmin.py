from __future__ import absolute_import
import warnings

from webassets.filter import Filter


__all__ = ('JSMin',)


class JSMin(Filter):
    """Minifies Javascript by removing whitespace, comments, etc.

    This filter uses a Python port of Douglas Crockford's `JSMin
    <http://www.crockford.com/javascript/jsmin.html>`_, which needs
    to be installed separately.

    There are actually multiple implementations available, for
    example one by Baruch Even. Easiest to install via PyPI is
    the one by Dave St. Germain::

        $ pip install jsmin

    The filter is tested with this ``jsmin`` package from PyPI,
    but will work with any module that exposes a
    ``JavascriptMinify`` object with a ``minify`` method.

    If you want to avoid installing another dependency, use the
    :class:`webassets.filter.rjsmin.RJSMin` filter instead.
    """

    name = 'jsmin'

    def setup(self):
        import jsmin
        self.jsmin = jsmin

    def output(self, _in, out, **kw):
        if hasattr(self.jsmin, 'JavaScriptMinifier'):
            # jsmin.py from v8
            minifier = self.jsmin.JavaScriptMinifier()
            minified = minifier.JSMinify(_in.read())
            out.write(minified)
        else:
            self.jsmin.JavascriptMinify().minify(_in, out)
