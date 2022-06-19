__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2020 The OctoPrint Project - Released under terms of the AGPLv3 License"

from flask_babel import gettext

import octoprint.plugin


class MjpegWebcamPlugin(
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.WebcamPlugin,
):
    def get_assets(self):
        return {
            "js": ["js/classicwebcam.js"],
            "less": ["less/classicwebcam.less"],
            "css": ["css/classicwebcam.css"],
        }

    def get_template_configs(self):
        return [
            {
                "type": "settings",
                "template": "classicwebcam_settings.jinja2",
                "custom_bindings": False,
            },
            {
                "type": "webcam",
                "name": "Classic Webcam",
                "template": "classicwebcam_webcam.jinja2",
                "custom_bindings": True,
                "suffix": "_real",
            },
            {
                "type": "webcam",
                "name": "Dummy Webcam",
                "template": "classicwebcam_webcam_2.jinja2",
                "custom_bindings": False,
                "suffix": "_dummy",
            },
        ]

    def get_settings_version(self):
        return 1

    def on_settings_migrate(self, target, current):
        if current is None:
            config = self._settings.global_get(["webcam"])
            if config:
                self._logger.info(
                    "Migrating settings from webcam to plugins.classicwebcam..."
                )

                self._settings.set_boolean(
                    ["flipH"], config.get("flipH", False), force=True
                )
                self._settings.global_remove(["webcam", "flipH"])

                self._settings.set_boolean(
                    ["flipV"], config.get("flipV", False), force=True
                )
                self._settings.global_remove(["webcam", "flipV"])

                self._settings.set_boolean(
                    ["rotate90"], config.get("rotate90", False), force=True
                )
                self._settings.global_remove(["webcam", "rotate90"])

                self._settings.set(["stream"], config.get("stream", ""), force=True)
                self._settings.global_remove(["webcam", "stream"])

                self._settings.set_int(
                    ["streamTimeout"], config.get("streamTimeout", ""), force=True
                )
                self._settings.global_remove(["webcam", "streamTimeout"])

                self._settings.set(
                    ["streamRatio"], config.get("streamRatio", ""), force=True
                )
                self._settings.global_remove(["webcam", "streamRatio"])

                self._settings.set(
                    ["streamWebrtcIceServers"],
                    config.get("streamWebrtcIceServers", []),
                    force=True,
                )
                self._settings.global_remove(["webcam", "streamWebrtcIceServers"])

                self._settings.set(["snapshot"], config.get("snapshot", ""), force=True)
                self._settings.global_remove(["webcam", "snapshot"])

                self._settings.set_boolean(
                    ["cacheBuster"], config.get("cacheBuster", ""), force=True
                )
                self._settings.global_remove(["webcam", "cacheBuster"])


__plugin_name__ = gettext("Classic Webcam")
__plugin_author__ = "Christian Würthner"
__plugin_description__ = "Provides a simple webcam viewer in OctoPrint's UI, images provided by an MJPEG webcam."
__plugin_disabling_discouraged__ = gettext(
    "Without this plugin the basic Webcam in the control tab"
    " will no longer be available."
)
__plugin_license__ = "AGPLv3"
__plugin_pythoncompat__ = ">=3.7,<4"
__plugin_implementation__ = MjpegWebcamPlugin()
# __plugin_hooks__ = {
# 	"octoprint.access.permissions": __plugin_implementation__.get_additional_permissions
# }
