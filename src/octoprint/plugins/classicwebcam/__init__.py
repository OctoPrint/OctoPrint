__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2020 The OctoPrint Project - Released under terms of the AGPLv3 License"

from flask_babel import gettext

import octoprint.plugin
from octoprint.schema.config.webcam import RatioEnum, Webcam, WebcamCompatibility


class MjpegWebcamPlugin(
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.WebcamPlugin,
):
    def get_assets(self):
        return {
            "js": ["js/classicwebcam.js", "js/classicwebcam_settings.js"],
            "less": ["less/classicwebcam.less"],
            "css": ["css/classicwebcam.css"],
        }

    def get_template_configs(self):
        return [
            {
                "type": "settings",
                "template": "classicwebcam_settings.jinja2",
                "custom_bindings": True,
            },
            {
                "type": "webcam",
                "name": "Classic Webcam",
                "template": "classicwebcam_webcam.jinja2",
                "custom_bindings": True,
                "suffix": "_real",
            },
        ]

    def get_webcam_configurations(self):
        streamRatio = self._settings.get(["streamRatio"])
        if streamRatio == "4:3":
            streamRatio = RatioEnum.four_three
        else:
            streamRatio = RatioEnum.sixteen_nine
        webRtcServers = self._settings.get(["streamWebrtcIceServers"])
        cacheBuster = self._settings.get(["cacheBuster"]) is True
        stream = self._settings.get(["stream"])
        snapshot = self._settings.get(["snapshot"])
        flipH = self._settings.get(["flipH"]) is True
        flipV = self._settings.get(["flipH"]) is True
        rotate90 = self._settings.get(["flipH"]) is True

        try:
            streamTimeout = int(self._settings.get(["streamTimeout"]))
        except ValueError:
            streamTimeout = 5

        return [
            Webcam(
                name="classic",
                displayName="Classic Webcam",
                snapshot=snapshot,
                flipH=flipH,
                flipV=flipV,
                rotate90=rotate90,
                compat=WebcamCompatibility(
                    stream=stream,
                    streamTimeout=streamTimeout,
                    streamRatio=streamRatio,
                    cacheBuster=cacheBuster,
                    streamWebrtcIceServers=webRtcServers,
                ),
                extras=dict(
                    stream=stream,
                    streamTimeout=streamTimeout,
                    streamRatio=streamRatio,
                    streamWebrtcIceServers=webRtcServers,
                    cacheBuster=cacheBuster,
                ),
            ),
        ]

    def get_settings_defaults(self):
        return dict(
            flipH=False,
            flipV=False,
            rotate90=False,
            stream="",
            streamTimeout=5,
            streamRatio="16:9",
            streamWebrtcIceServers="stun:stun.l.google.com:19302",
            snapshot="",
            cacheBuster=False,
        )

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
                    ["streamTimeout"], config.get("streamTimeout", 5), force=True
                )
                self._settings.global_remove(["webcam", "streamTimeout"])

                self._settings.set(
                    ["streamRatio"], config.get("streamRatio", ""), force=True
                )
                self._settings.global_remove(["webcam", "streamRatio"])

                self._settings.set(
                    ["streamWebrtcIceServers"],
                    ",".join(
                        config.get(
                            "streamWebrtcIceServers", ["stun:stun.l.google.com:19302"]
                        )
                    ),
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
