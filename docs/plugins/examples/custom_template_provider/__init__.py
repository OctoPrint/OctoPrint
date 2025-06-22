import octoprint.plugin


class CustomTemplateTypeProvider(octoprint.plugin.TemplatePlugin):
    def add_templatetype(self, current_order, current_rules, *args, **kwargs):
        return [
            (
                "awesometemplate",
                dict(),
                dict(template=lambda x: x + "_awesometemplate.jinja2"),
            )
        ]


__plugin_name__ = "Custom Template Provider"
__plugin_pythoncompat__ = ">=2.7,<4"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = CustomTemplateTypeProvider()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.ui.web.templatetypes": __plugin_implementation__.add_templatetype
    }
