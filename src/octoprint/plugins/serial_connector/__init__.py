from flask_babel import gettext

import octoprint.plugin

from .connector import ConnectedSerialPrinter  # noqa: F401


class SerialConnectorPlugin(
    octoprint.plugin.AssetPlugin, octoprint.plugin.TemplatePlugin
):
    ##~~ TemplatePlugin mixin

    def get_template_configs(self):
        return [
            {
                "type": "connection_options",
                "name": gettext("Serial Connection"),
                "connector": "serial",
                "template": "serial_connector_connection_option.jinja2",
                "custom_bindings": True,
            }
        ]


__plugin_name__ = "Serial Connector"
__plugin_author__ = "Gina Häußge"
__plugin_description__ = (
    "A printer connector plugin to support serial communication (e.g. Marlin, Prusa, ...)"
)
__plugin_license__ = "AGPLv3"
__plugin_pythoncompat__ = ">=3.9,<4"
__plugin_disabling_discouraged__ = gettext(
    "Without this plugin you will no longer be able to connect "
    "to printers based on serial communication."
)
__plugin_implementation__ = SerialConnectorPlugin()
