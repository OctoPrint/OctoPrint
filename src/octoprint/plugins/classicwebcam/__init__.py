__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

import threading

import requests
from flask_babel import gettext

import octoprint.plugin
from octoprint.schema.webcam import RatioEnum, Webcam, WebcamCompatibility
from octoprint.webcams import WebcamNotAbleToTakeSnapshotException


class ClassicWebcamPlugin(
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.WebcamProviderPlugin,
    octoprint.plugin.WizardPlugin,
):
    def __init__(self):
        self._capture_mutex = threading.Lock()
        self._webcam_name = "classic"

    # ~~ TemplatePlugin API

    def get_assets(self):
        return {
            "js": [
                "js/classicwebcam.js",
                "js/classicwebcam_settings.js",
                "js/classicwebcam_wizard.js",
            ],
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
            {
                "type": "wizard",
                "name": "Classic Webcam Wizard",
                "template": "classicwebcam_wizard.jinja2",
                "suffix": "_wizard",
            },
        ]

    # ~~ WebcamProviderPlugin API

    def get_webcam_configurations(self):
        streamRatio = self._settings.get(["streamRatio"])
        if streamRatio == "4:3":
            streamRatio = RatioEnum.four_three
        else:
            streamRatio = RatioEnum.sixteen_nine
        webRtcServers = self._settings.get(["streamWebrtcIceServers"])
        cacheBuster = self._settings.get_boolean(["cacheBuster"])
        stream = self._get_stream_url()
        snapshot = self._get_snapshot_url()
        flipH = self._settings.get_boolean(["flipH"])
        flipV = self._settings.get_boolean(["flipV"])
        rotate90 = self._settings.get_boolean(["rotate90"])
        snapshotSslValidation = self._settings.get_boolean(["snapshotSslValidation"])

        try:
            streamTimeout = int(self._settings.get(["streamTimeout"]))
        except Exception:
            streamTimeout = 5

        try:
            snapshotTimeout = int(self._settings.get(["snapshotTimeout"]))
        except Exception:
            snapshotTimeout = 5

        return [
            Webcam(
                name=self._webcam_name,
                displayName="Classic Webcam",
                flipH=flipH,
                flipV=flipV,
                rotate90=rotate90,
                snapshotDisplay=snapshot,
                canSnapshot=self._can_snapshot(),
                compat=WebcamCompatibility(
                    stream=stream,
                    streamTimeout=streamTimeout,
                    streamRatio=streamRatio,
                    cacheBuster=cacheBuster,
                    streamWebrtcIceServers=webRtcServers,
                    snapshot=snapshot,
                    snapshotTimeout=snapshotTimeout,
                    snapshotSslValidation=snapshotSslValidation,
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

    def _get_snapshot_url(self):
        return self._settings.get(["snapshot"])

    def _get_stream_url(self):
        return self._settings.get(["stream"])

    def _can_snapshot(self):
        snapshot = self._get_snapshot_url()
        return snapshot is not None and snapshot.strip() != ""

    def take_webcam_snapshot(self, _):
        snapshot_url = self._get_snapshot_url()
        if not self._can_snapshot():
            raise WebcamNotAbleToTakeSnapshotException(self._webcam_name)

        with self._capture_mutex:
            self._logger.debug(f"Capturing image from {snapshot_url}")
            r = requests.get(
                snapshot_url,
                stream=True,
                timeout=self._settings.get_int(["snapshotTimeout"]),
                verify=self._settings.get_boolean(["snapshotSslValidation"]),
            )
            r.raise_for_status()
            return r.iter_content(chunk_size=1024)

    # ~~ SettingsPlugin API

    def get_settings_defaults(self):
        return dict(
            flipH=False,
            flipV=False,
            rotate90=False,
            stream="",
            streamTimeout=5,
            streamRatio="16:9",
            streamWebrtcIceServers=["stun:stun.l.google.com:19302"],
            snapshot="",
            cacheBuster=False,
            snapshotSslValidation=True,
            snapshotTimeout=5,
        )

    def get_settings_version(self):
        return 1

    def on_settings_save(self, data):
        dirty = False
        if "streamTimeout" in data:
            self._settings.set_int(["streamTimeout"], data.pop("streamTimeout"))
            dirty = True
        if "snapshotTimeout" in data:
            self._settings.set_int(["snapshotTimeout"], data.pop("snapshotTimeout"))
            dirty = True
        if dirty:
            self._settings.save()

        return super().on_settings_save(data)

    def on_settings_migrate(self, target, current):
        if current is None:
            config = self._settings.global_get(["webcam"])
            if config:
                self._logger.info(
                    "Migrating settings from webcam to plugins.classicwebcam..."
                )

                # flipH
                self._settings.set_boolean(["flipH"], config.get("flipH", False))
                self._settings.global_remove(["webcam", "flipH"])

                # flipV
                self._settings.set_boolean(["flipV"], config.get("flipV", False))
                self._settings.global_remove(["webcam", "flipV"])

                # rotate90
                self._settings.set_boolean(["rotate90"], config.get("rotate90", False))
                self._settings.global_remove(["webcam", "rotate90"])

                # stream
                self._settings.set(["stream"], config.get("stream", ""))
                self._settings.global_remove(["webcam", "stream"])

                # streamTimeout
                self._settings.set_int(["streamTimeout"], config.get("streamTimeout", 5))
                self._settings.global_remove(["webcam", "streamTimeout"])

                # streamRatio
                self._settings.set(["streamRatio"], config.get("streamRatio", "16:9"))
                self._settings.global_remove(["webcam", "streamRatio"])

                # streamWebrtcIceServers
                self._settings.set(
                    ["streamWebrtcIceServers"],
                    config.get(
                        "streamWebrtcIceServers", ["stun:stun.l.google.com:19302"]
                    ),
                )
                self._settings.global_remove(["webcam", "streamWebrtcIceServers"])

                # snapshot
                self._settings.set(["snapshot"], config.get("snapshot", ""))
                self._settings.global_remove(["webcam", "snapshot"])

                # cacheBuster
                self._settings.set_boolean(
                    ["cacheBuster"], config.get("cacheBuster", False)
                )
                self._settings.global_remove(["webcam", "cacheBuster"])

                # snapshotTimeout
                self._settings.set_int(
                    ["snapshotTimeout"], config.get("snapshotTimeout", 5)
                )
                self._settings.global_remove(["webcam", "snapshotTimeout"])

                # snapshotSslValidation
                self._settings.set_boolean(
                    ["snapshotSslValidation"], config.get("snapshotSslValidation", True)
                )
                self._settings.global_remove(["webcam", "snapshotSslValidation"])

    # ~~ WizardPlugin API

    def is_wizard_required(self):
        required = (
            not self._get_stream_url()
            or not self._get_snapshot_url()
            or not self._settings.global_get(["webcam", "ffmpegPath"])
        )
        firstrun = self._settings.global_get(["server", "firstRun"])
        return required and firstrun

    def get_wizard_version(self):
        return 1


__plugin_name__ = gettext("Classic Webcam")
__plugin_author__ = "Christian Würthner"
__plugin_description__ = "Provides a simple webcam viewer in OctoPrint's UI, images provided by an MJPEG webcam."
__plugin_disabling_discouraged__ = gettext(
    "This plugin provides the standard webcam in OctoPrint. If you do not have any other plugin providing a webcam set up, the webcam section in the control tab will no longer be visible."
)
__plugin_license__ = "AGPLv3"
__plugin_pythoncompat__ = ">=3.7,<4"
__plugin_implementation__ = ClassicWebcamPlugin()
