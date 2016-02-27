from __future__ import absolute_import
from webassets.filter import Filter


__all__ = ('CSSPrefixer',)


class CSSPrefixer(Filter):
    """Uses `CSSPrefixer <http://github.com/myfreeweb/cssprefixer/>`_
    to add vendor prefixes to CSS files.
    """

    name = 'cssprefixer'
    max_debug_level = 'merge'

    def setup(self):
        import cssprefixer
        self.cssprefixer = cssprefixer

    def output(self, _in, out, **kw):
        output = self.cssprefixer.process(_in.read(), False, False)
        if isinstance(output, unicode):
            # cssprefixer likes to return unicode strings
            output = output.encode('utf8')
        out.write(output)
