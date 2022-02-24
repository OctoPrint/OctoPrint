from flask_babel import gettext

import octoprint.events
import octoprint.plugin
from octoprint.access import ADMIN_GROUP


class EventManagerPlugin(
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.TemplatePlugin,
):
    def on_settings_load(self):
        my_settings = {
            "availableEvents": octoprint.events.all_events(),
            "subscriptions": [],
        }
        events = self._settings.global_get(["events"])
        if events:
            my_settings["subscriptions"] = events.get("subscriptions", [])
        return my_settings

    def on_settings_save(self, data):
        if type(data.get("subscriptions")) == list:
            self._settings.global_set(
                ["events", "subscriptions"], data.get("subscriptions", [])
            )

    def get_assets(self):
        return {"js": ["js/events.js"]}

    def get_template_configs(self):
        return [
            {
                "type": "settings",
                "custom_bindings": True,
                "name": gettext("Event Manager"),
            }
        ]

    def get_additional_permissions(self):
        return [
            {
                "key": "MANAGE",
                "name": "Event management",
                "description": gettext(
                    "Allows for the management of event subscriptions."
                ),
                "default_groups": [ADMIN_GROUP],
                "roles": ["manage"],
            }
        ]


__plugin_name__ = gettext("Event Manager")
__plugin_pythoncompat__ = ">=3.7,<4"
__plugin_author__ = "jneilliii"
__plugin_license__ = "AGPLv3"
__plugin_description__ = gettext(
    "Plugin to configure event subscriptions available in config.yaml."
)
__plugin_implementation__ = EventManagerPlugin()
