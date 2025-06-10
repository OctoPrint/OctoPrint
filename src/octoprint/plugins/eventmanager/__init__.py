import copy

from flask_babel import gettext

import octoprint.events
import octoprint.plugin
from octoprint.access.permissions import Permissions


class EventManagerPlugin(
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.TemplatePlugin,
):
    # ~~ SettingsPlugin mixin

    def on_settings_load(self):
        if not Permissions.SETTINGS.can():
            return {"availableEvents": [], "subscriptions": []}

        my_settings = {
            "availableEvents": octoprint.events.all_events(),
            "subscriptions": [],
        }

        events = self._settings.global_get(["events"])
        if events and events.get("subscriptions", []):
            subs = events.get("subscriptions", [])
            setting_subs = []
            for sub in subs:
                data = copy.deepcopy(sub)

                if "name" not in data:
                    # ensure name is set
                    data["name"] = data["command"]

                if not isinstance(data["event"], list):
                    # ensure event list is a list
                    data["event"] = [data["event"]]

                setting_subs.append(data)

            # sort by name
            my_settings["subscriptions"] = sorted(setting_subs, key=(lambda x: x["name"]))

        return my_settings

    def on_settings_save(self, data):
        if isinstance(data.get("subscriptions"), list):
            self._settings.global_set(
                ["events", "subscriptions"], data.get("subscriptions", [])
            )

    def get_settings_reauth_requirements(self):
        return {"subscriptions": True}

    # ~~ AssetPlugin mixin

    def get_assets(self):
        return {"js": ["js/events.js"]}

    # ~~ TemplatePlugin mixin

    def get_template_configs(self):
        return [
            {
                "type": "settings",
                "custom_bindings": True,
                "name": gettext("Event Manager"),
            }
        ]


__plugin_name__ = gettext("Event Manager")
__plugin_pythoncompat__ = ">=3.9,<4"
__plugin_author__ = "jneilliii"
__plugin_license__ = "AGPLv3"
__plugin_description__ = gettext(
    "Plugin to configure event subscriptions available in config.yaml."
)
__plugin_implementation__ = EventManagerPlugin()
