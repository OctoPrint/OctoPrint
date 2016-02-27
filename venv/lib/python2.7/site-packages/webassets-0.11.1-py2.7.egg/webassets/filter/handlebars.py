import subprocess
import os
from os import path

from webassets.exceptions import FilterError
from webassets.filter.jst import JSTemplateFilter


__all__ = ('Handlebars',)


class Handlebars(JSTemplateFilter):
    """Compile `Handlebars <http://handlebarsjs.com/>`_ templates.

    This filter assumes that the ``handlebars`` executable is in the path.
    Otherwise, you may define a ``HANDLEBARS_BIN`` setting.

    .. note::
        Use this filter if you want to precompile Handlebars templates.
        If compiling them in the browser is acceptable, you may use the
        JST filter, which needs no external dependency.

    .. warning::
        Currently, this filter is not compatible with input filters. Any
        filters that would run during the input-stage will simply be
        ignored. Input filters tend to be other compiler-style filters,
        so this is unlikely to be an issue.
    """

    # TODO: We should fix the warning above. Either, me make this filter
    # support input-processing (we'd have to work with the hunks given to
    # us, rather than the original source files), or make webassets raise
    # an error if the handlebars filter is combined with an input filter.
    # I'm unsure about the best API design. We could support open()
    # returning ``True`` to indicate "no input filters allowed" (
    # surprisingly hard to implement) Or, use an attribute to declare
    # as much.

    name = 'handlebars'
    options = {
        'binary': 'HANDLEBARS_BIN',
        'extra_args': 'HANDLEBARS_EXTRA_ARGS',
        'root': 'HANDLEBARS_ROOT',
    }
    max_debug_level = None

    def process_templates(self, out,  hunks, **kw):
        templates = [info['source_path'] for _, info in hunks]

        if self.root is True:
            root = self.get_config('directory')
        elif self.root:
            root = path.join(self.get_config('directory'), self.root)
        else:
            root = self._find_base_path(templates)

        args = [self.binary or 'handlebars']
        if root:
            args.extend(['-r', root])
        if self.extra_args:
            args.extend(self.extra_args)
        args.extend(templates)

        proc = subprocess.Popen(
            args, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=(os.name == 'nt'))
        stdout, stderr = proc.communicate()

        if proc.returncode != 0:
            raise FilterError(('handlebars: subprocess had error: stderr=%s, '+
                               'stdout=%s, returncode=%s') % (
                                    stderr, stdout, proc.returncode))
        out.write(stdout.decode('utf-8').strip() + ';')
