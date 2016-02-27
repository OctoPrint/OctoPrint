from __future__ import absolute_import
import logging
import logging.handlers

from webassets.filter import Filter


__all__ = ('CSSUtils',)


class CSSUtils(Filter):
    """Minifies CSS by removing whitespace, comments etc., using the Python
    `cssutils <http://cthedot.de/cssutils/>`_ library.

    Note that since this works as a parser on the syntax level, so invalid
    CSS input could potentially result in data loss.
    """

    name = 'cssutils'

    def setup(self):
        import cssutils
        self.cssutils = cssutils

        try:
            # cssutils is unaware of so many new CSS3 properties,
            # vendor-prefixes etc., that it's diagnostic messages are rather
            # useless. Disable them.
            log = logging.getLogger('assets.cssutils')
            log.addHandler(logging.handlers.MemoryHandler(10))

            # Newer versions of cssutils print a deprecation warning
            # for 'setlog'.
            if hasattr(cssutils.log, 'setLog'):
                func = cssutils.log.setLog
            else:
                func = cssutils.log.setlog
            func(log)
        except ImportError:
            # During doc generation, Django is not going to be setup and will
            # fail when the settings object is accessed. That's ok though.
            pass

    def output(self, _in, out, **kw):
        sheet = self.cssutils.parseString(_in.read())
        self.cssutils.ser.prefs.useMinified()
        out.write(sheet.cssText.decode('utf-8'))
