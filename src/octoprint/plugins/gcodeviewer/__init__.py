__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2020 The OctoPrint Project - Released under terms of the AGPLv3 License"

from flask_babel import gettext

import octoprint.plugin


class GcodeviewerPlugin(
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.SettingsPlugin,
):
    def get_assets(self):
        js = [
            "js/gcodeviewer.js",
            "js/viewer/ui.js",
            "js/viewer/reader.js",
            "js/viewer/renderer.js",
        ]

        return {
            "js": js,
            "less": ["less/gcodeviewer.less"],
            "css": ["css/gcodeviewer.css"],
        }

    def get_template_configs(self):
        return [
            {
                "type": "tab",
                "template": "gcodeviewer_tab.jinja2",
                "div": "gcode",
                "styles": ["display: none;"],
                "data_bind": "visible: loginState.hasAllPermissionsKo(access.permissions.GCODE_VIEWER, access.permissions.FILES_DOWNLOAD)",
            },
            {
                "type": "settings",
                "template": "gcodeviewer_settings.jinja2",
                "custom_bindings": True,
            },
            {"type": "generic", "template": "gcodeviewer_initscript.jinja2"},
        ]

    def get_settings_defaults(self):
        return {
            "mobileSizeThreshold": 2 * 1024 * 1024,  # 2MB
            "sizeThreshold": 20 * 1024 * 1024,  # 20MB
            "skipUntilThis": None,
        }

    def get_settings_version(self):
        return 1

    def on_settings_migrate(self, target, current):
        if current is None:
            config = self._settings.global_get(["gcodeViewer"])
            if config:
                self._logger.info(
                    "Migrating settings from gcodeViewer to plugins.gcodeviewer..."
                )
                if "mobileSizeThreshold" in config:
                    self._settings.set_int(
                        ["mobileSizeThreshold"], config["mobileSizeThreshold"]
                    )
                if "sizeThreshold" in config:
                    self._settings.set_int(["sizeThreshold"], config["sizeThreshold"])
                self._settings.global_remove(["gcodeViewer"])


__plugin_name__ = gettext("GCode Viewer")
__plugin_author__ = "Gina Häußge"
__plugin_description__ = "Provides a GCODE viewer in OctoPrint's UI."
__plugin_disabling_discouraged__ = gettext(
    "Without this plugin the GCode Viewer in OctoPrint will no longer be " "available."
)
__plugin_license__ = "AGPLv3"
__plugin_pythoncompat__ = ">=3.7,<4"
__plugin_implementation__ = GcodeviewerPlugin()
# __plugin_hooks__ = {
# 	"octoprint.access.permissions": __plugin_implementation__.get_additional_permissions
# }
