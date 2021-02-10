__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

from octoprint.comm.protocol.reprap.util import process_gcode_line
from octoprint.comm.scripts import Script, UnknownScript


class GcodeScript(Script):
    def __init__(self, settings, name, context=None):
        def renderer(ctx):
            lines = settings.loadScript("gcode", name, context=ctx)
            if lines is None:
                raise UnknownScript(name)
            return lines

        super(GcodeScript, self).__init__(name, renderer, context=context)

    def render(self, context=None):
        script = super(GcodeScript, self).render(context)
        return list(
            filter(
                lambda x: x is not None and x.strip() != "",
                map(lambda x: process_gcode_line(x), script),
            )
        )
