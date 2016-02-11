from __future__ import absolute_import
from webassets.filter import Filter


__all__ = ('Jinja2',)


class Jinja2(Filter):
    """Process a file through the Jinja2 templating engine.

    Requires the ``jinja2`` package (https://github.com/mitsuhiko/jinja2).

    The Jinja2 context can be specified with the `JINJA2_CONTEXT` configuration
    option or directly with `context={...}`. Example:

    .. code-block:: python

        Bundle('input.css', filters=Jinja2(context={'foo': 'bar'}))
    
    Additionally to enable template loading mechanics from your project you can provide
    `JINJA2_ENV` or `jinja2_env` arg to make use of already created environment.
    """

    name = 'jinja2'
    max_debug_level = None
    options = {
        'context': 'JINJA2_CONTEXT',
        'jinja2_env': 'JINJA2_ENV'
    }

    def setup(self):
        try:
            import jinja2
        except ImportError:
            raise EnvironmentError('The "jinja2" package is not installed.')
        else:
            self.jinja2 = jinja2
        super(Jinja2, self).setup()

    def input(self, _in, out, **kw):
        tpl_factory = self.jinja2_env.from_string if self.jinja2_env else self.jinja2.Template
        out.write(tpl_factory(_in.read()).render(self.context or {}))
