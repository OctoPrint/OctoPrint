from __future__ import absolute_import

from webassets.filter import Filter


__all__ = ('CSSSlimmer',)


class Slimmer(Filter):

    def setup(self):
        super(Slimmer, self).setup()
        import slimmer
        self.slimmer = slimmer


class CSSSlimmer(Slimmer):
    """Minifies CSS by removing whitespace, comments etc., using the Python
    `slimmer <http://pypi.python.org/pypi/slimmer/>`_ library.
    """

    name = 'css_slimmer'

    def output(self, _in, out, **kw):
        out.write(self.slimmer.css_slimmer(_in.read()))

