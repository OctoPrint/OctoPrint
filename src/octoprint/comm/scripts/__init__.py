__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"


class Script(object):
    def __init__(self, name, renderer, context=None):
        if context is None:
            context = {}

        self.name = name
        self.renderer = renderer
        self.context = context

    def render(self, context=None):
        if context is None:
            context = {}

        render_context = dict(self.context)
        render_context.update(context)

        content = self.renderer(render_context)
        if content is None:
            return None

        return content.split("\n")


class UnknownScript(Exception):
    def __init__(self, name, *args, **kwargs):
        self.name = name


class InvalidScript(Exception):
    pass
