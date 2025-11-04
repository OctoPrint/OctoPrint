__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging
import re
from typing import Any

from flask import abort, jsonify, request
from flask_login import current_user

import octoprint.plugin
import octoprint.util
from octoprint.access.permissions import Permissions
from octoprint.schema.config.controls import CustomControl, CustomControlContainer
from octoprint.server import pluginManager, userManager
from octoprint.server.api import NO_CONTENT, api
from octoprint.server.util.flask import (
    api_version_matches,
    credentials_checked_recently,
    ensure_credentials_checked_recently,
    no_firstrun_access,
    require_credentials_checked_recently,
    with_revalidation_checking,
)
from octoprint.settings import settings, valid_boolean_trues
from octoprint.timelapse import configure_timelapse
from octoprint.webcams import (
    get_default_webcam,
    get_snapshot_webcam,
    get_webcams_as_dicts,
)

# ~~ settings

FOLDER_TYPES = ("uploads", "timelapse", "watched")
TIMELAPSE_BITRATE_PATTERN = re.compile(r"\d+[KMGTPEZY]?i?B?", flags=re.IGNORECASE)
DEPRECATED_WEBCAM_KEYS = (
    "streamUrl",
    "streamRatio",
    "streamTimeout",
    "streamWebrtcIceServers",
    "snapshotUrl",
    "snapshotTimeout",
    "snapshotSslValidation",
    "cacheBuster",
    "flipH",
    "flipV",
    "rotate90",
)

REAUTHED_SETTINGS = {
    "server": {"commands": True},
    "webcam": {
        "ffmpegPath": True,
        "ffmpegCommandline": True,
        "ffmpegThumbnailCommandline": True,
    },
    "system": {"actions": True},
}


def _lastmodified():
    return settings().last_modified


def _etag(lm=None):
    if lm is None:
        lm = _lastmodified()

    plugins = sorted(octoprint.plugin.plugin_manager().enabled_plugins)
    plugin_settings = _get_plugin_settings()

    from collections import OrderedDict

    sorted_plugin_settings = OrderedDict()
    for key in sorted(plugin_settings.keys()):
        sorted_plugin_settings[key] = plugin_settings.get(key, {})

    if current_user is not None and not current_user.is_anonymous:
        roles = sorted(current_user.permissions, key=lambda x: x.key)
    else:
        roles = []

    import hashlib

    hash = hashlib.sha1()

    def hash_update(value):
        value = value.encode("utf-8")
        hash.update(value)

    # last modified timestamp
    hash_update(str(lm))

    # effective config from config.yaml + overlays
    hash_update(repr(settings().effective))

    # might duplicate settings().effective, but plugins might also inject additional keys into the settings
    # output that are not stored in config.yaml
    hash_update(repr(sorted_plugin_settings))

    # if the list of plugins changes, the settings structure changes too
    hash_update(repr(plugins))

    # and likewise if the role of the user changes
    hash_update(repr(roles))

    # or if the user reauthenticates
    hash_update(repr(credentials_checked_recently()))

    return hash.hexdigest()


@api.route("/settings", methods=["GET"])
@with_revalidation_checking(
    etag_factory=_etag,
    lastmodified_factory=_lastmodified,
    unless=lambda: request.values.get("force", "false") in valid_boolean_trues
    or settings().getBoolean(["server", "firstRun"])
    or not userManager.has_been_customized(),
)
def getSettings():
    if not Permissions.SETTINGS_READ.can() and not (
        settings().getBoolean(["server", "firstRun"])
        or not userManager.has_been_customized()
    ):
        abort(403)

    s = settings()

    # NOTE: Remember to adjust the docs of the data model on the Settings API if anything
    # is changed, added or removed here

    data = {
        "api": {
            "key": (
                s.get(["api", "key"])
                if Permissions.ADMIN.can() and credentials_checked_recently()
                else None
            ),
            "allowCrossOrigin": s.get(["api", "allowCrossOrigin"]),
        },
        "appearance": {
            "name": s.get(["appearance", "name"]),
            "color": s.get(["appearance", "color"]),
            "colorTransparent": s.getBoolean(["appearance", "colorTransparent"]),
            "colorIcon": s.getBoolean(["appearance", "colorIcon"]),
            "defaultLanguage": s.get(["appearance", "defaultLanguage"]),
            "showFahrenheitAlso": s.getBoolean(["appearance", "showFahrenheitAlso"]),
            "fuzzyTimes": s.getBoolean(["appearance", "fuzzyTimes"]),
            "closeModalsWithClick": s.getBoolean(["appearance", "closeModalsWithClick"]),
            "showInternalFilename": s.getBoolean(["appearance", "showInternalFilename"]),
            "thumbnails": {
                "filelistEnabled": s.getBoolean(
                    ["appearance", "thumbnails", "filelistEnabled"]
                ),
                "filelistScale": s.getInt(["appearance", "thumbnails", "filelistScale"]),
                "filelistAlignment": s.get(
                    ["appearance", "thumbnails", "filelistAlignment"]
                ),
                "filelistPreview": s.getBoolean(
                    ["appearance", "thumbnails", "filelistPreview"]
                ),
                "stateEnabled": s.getBoolean(
                    ["appearance", "thumbnails", "stateEnabled"]
                ),
                "stateScale": s.getInt(["appearance", "thumbnails", "stateScale"]),
            },
        },
        "feature": {
            "temperatureGraph": s.getBoolean(["feature", "temperatureGraph"]),
            "sdSupport": s.getBoolean(["feature", "sdSupport"]),
            "keyboardControl": s.getBoolean(["feature", "keyboardControl"]),
            "pollWatched": s.getBoolean(["feature", "pollWatched"]),
            "modelSizeDetection": s.getBoolean(["feature", "modelSizeDetection"]),
            "rememberFileFolder": s.getBoolean(["feature", "rememberFileFolder"]),
            "printStartConfirmation": s.getBoolean(["feature", "printStartConfirmation"]),
            "printCancelConfirmation": s.getBoolean(
                ["feature", "printCancelConfirmation"]
            ),
            "uploadOverwriteConfirmation": s.getBoolean(
                ["feature", "uploadOverwriteConfirmation"]
            ),
            "fileDeleteConfirmation": s.getBoolean(["feature", "fileDeleteConfirmation"]),
            "g90InfluencesExtruder": s.getBoolean(["feature", "g90InfluencesExtruder"]),
            "autoUppercaseBlacklist": s.get(["feature", "autoUppercaseBlacklist"]),
            "enableDragDropUpload": s.getBoolean(["feature", "enableDragDropUpload"]),
        },
        "gcodeAnalysis": {
            "runAt": s.get(["gcodeAnalysis", "runAt"]),
            "bedZ": s.getFloat(["gcodeAnalysis", "bedZ"]),
        },
        "folder": {
            "uploads": s.getBaseFolder("uploads"),
            "timelapse": s.getBaseFolder("timelapse"),
            "watched": s.getBaseFolder("watched"),
        },
        "temperature": {
            "profiles": s.get(["temperature", "profiles"]),
            "cutoff": s.getInt(["temperature", "cutoff"]),
            "sendAutomatically": s.getBoolean(["temperature", "sendAutomatically"]),
            "sendAutomaticallyAfter": s.getInt(
                ["temperature", "sendAutomaticallyAfter"], min=0, max=30
            ),
        },
        "system": {
            "actions": s.get(["system", "actions"]),
        },
        "terminalFilters": s.get(["terminalFilters"]),
        "scripts": {
            "gcode": {
                "afterPrinterConnected": None,
                "beforePrinterDisconnected": None,
                "beforePrintStarted": None,
                "afterPrintCancelled": None,
                "afterPrintDone": None,
                "beforePrintPaused": None,
                "afterPrintResumed": None,
                "beforeToolChange": None,
                "afterToolChange": None,
                "snippets": {},
            }
        },
        "server": {
            "commands": {
                "systemShutdownCommand": s.get(
                    ["server", "commands", "systemShutdownCommand"]
                ),
                "systemRestartCommand": s.get(
                    ["server", "commands", "systemRestartCommand"]
                ),
                "serverRestartCommand": s.get(
                    ["server", "commands", "serverRestartCommand"]
                ),
            },
            "diskspace": {
                "warning": s.getInt(["server", "diskspace", "warning"]),
                "critical": s.getInt(["server", "diskspace", "critical"]),
            },
            "onlineCheck": {
                "enabled": s.getBoolean(["server", "onlineCheck", "enabled"]),
                "interval": int(s.getInt(["server", "onlineCheck", "interval"]) / 60),
                "host": s.get(["server", "onlineCheck", "host"]),
                "port": s.getInt(["server", "onlineCheck", "port"]),
                "name": s.get(["server", "onlineCheck", "name"]),
            },
            "pluginBlacklist": {
                "enabled": s.getBoolean(["server", "pluginBlacklist", "enabled"]),
                "url": s.get(["server", "pluginBlacklist", "url"]),
                "ttl": int(s.getInt(["server", "pluginBlacklist", "ttl"]) / 60),
            },
            "allowFraming": s.getBoolean(["server", "allowFraming"]),
        },
        "devel": {"pluginTimings": s.getBoolean(["devel", "pluginTimings"])},
        "slicing": {"defaultSlicer": s.get(["slicing", "defaultSlicer"])},
    }

    gcode_scripts = s.listScripts("gcode")
    if gcode_scripts:
        data["scripts"] = {"gcode": {}}
        for name in gcode_scripts:
            data["scripts"]["gcode"][name] = s.loadScript("gcode", name, source=True)

    plugin_settings = _get_plugin_settings()
    if len(plugin_settings):
        data["plugins"] = plugin_settings

    if not api_version_matches(">=1.12.0"):
        data["serial"] = _get_serial_settings()

    if Permissions.WEBCAM.can() or (
        settings().getBoolean(["server", "firstRun"])
        and not userManager.has_been_customized()
    ):
        webcamsDict = get_webcams_as_dicts()
        data["webcam"] = {
            "webcamEnabled": s.getBoolean(["webcam", "webcamEnabled"]),
            "timelapseEnabled": s.getBoolean(["webcam", "timelapseEnabled"]),
            "ffmpegPath": s.get(["webcam", "ffmpeg"]),
            "ffmpegCommandline": s.get(["webcam", "ffmpegCommandline"]),
            "bitrate": s.get(["webcam", "bitrate"]),
            "ffmpegThreads": s.get(["webcam", "ffmpegThreads"]),
            "ffmpegVideoCodec": s.get(["webcam", "ffmpegVideoCodec"]),
            "watermark": s.getBoolean(["webcam", "watermark"]),
            "renderAfterPrintDelay": s.getInt(["webcam", "renderAfterPrintDelay"]),
            # webcams & defaults
            "webcams": webcamsDict,
            "defaultWebcam": None,
            "snapshotWebcam": None,
        }

        for key in DEPRECATED_WEBCAM_KEYS:
            data["webcam"][key] = None

        defaultWebcam = get_default_webcam()
        if defaultWebcam:
            data["webcam"].update(
                {
                    "flipH": defaultWebcam.config.flipH,
                    "flipV": defaultWebcam.config.flipV,
                    "rotate90": defaultWebcam.config.rotate90,
                    "defaultWebcam": defaultWebcam.config.name,
                }
            )

        compatWebcam = defaultWebcam.config.compat if defaultWebcam is not None else None
        if compatWebcam:
            data["webcam"].update(
                {
                    "streamUrl": compatWebcam.stream,
                    "streamRatio": compatWebcam.streamRatio,
                    "streamTimeout": compatWebcam.streamTimeout,
                    "streamWebrtcIceServers": compatWebcam.streamWebrtcIceServers,
                    "snapshotUrl": compatWebcam.snapshot,
                    "snapshotTimeout": compatWebcam.snapshotTimeout,
                    "snapshotSslValidation": compatWebcam.snapshotSslValidation,
                    "cacheBuster": compatWebcam.cacheBuster,
                }
            )

        snapshotWebcam = get_snapshot_webcam()
        if snapshotWebcam:
            data["webcam"].update(
                {
                    "snapshotWebcam": snapshotWebcam.config.name,
                }
            )
    else:
        data["webcam"] = {}

    if Permissions.CONTROL.can():
        data["controls"] = s.get(["controls"])
    else:
        data["controls"] = []

    if Permissions.ADMIN.can():
        data["accessControl"] = {
            "autologinLocal": s.getBoolean(["accessControl", "autologinLocal"]),
            "autologinHeadsupAcknowledged": s.getBoolean(
                ["accessControl", "autologinHeadsupAcknowledged"]
            ),
        }

    return jsonify(data)


def _get_plugin_settings():
    logger = logging.getLogger(__name__)

    data = {}

    def process_plugin_result(name, result):
        if result:
            try:
                jsonify(test=result)
            except Exception:
                logger.exception(
                    "Error while jsonifying settings from plugin {}, please contact the plugin author about this".format(
                        name
                    )
                )
                raise
            else:
                if "__enabled" in result:
                    del result["__enabled"]
                data[name] = result

    for plugin in octoprint.plugin.plugin_manager().get_implementations(
        octoprint.plugin.SettingsPlugin
    ):
        try:
            result = plugin.on_settings_load()
            process_plugin_result(plugin._identifier, result)
        except Exception:
            logger.exception(
                "Could not load settings for plugin {name} ({version})".format(
                    version=plugin._plugin_version, name=plugin._plugin_name
                ),
                extra={"plugin": plugin._identifier},
            )

    return data


@api.route("/settings", methods=["POST"])
@no_firstrun_access
@Permissions.SETTINGS.require(403)
def setSettings():
    data = request.get_json()
    if not isinstance(data, dict):
        abort(400, description="Malformed JSON body in request")

    response = _saveSettings(data)
    if response:
        return response
    return getSettings()


@api.route("/settings/apikey", methods=["POST"])
@no_firstrun_access
@Permissions.ADMIN.require(403)
@require_credentials_checked_recently
def generateApiKey():
    apikey = settings().generateApiKey()
    return jsonify(apikey=apikey)


@api.route("/settings/apikey", methods=["DELETE"])
@no_firstrun_access
@Permissions.ADMIN.require(403)
@require_credentials_checked_recently
def deleteApiKey():
    settings().deleteApiKey()
    return NO_CONTENT


@api.route("/settings/templates", methods=["GET"])
@no_firstrun_access
@Permissions.SETTINGS.require(403)
def fetchTemplateData():
    from octoprint.server.views import fetch_template_data

    refresh = request.values.get("refresh", "false") in valid_boolean_trues
    templates, _, _ = fetch_template_data(refresh=refresh)

    result = {}
    for tt in templates:
        result[tt] = []
        for key in templates[tt]["order"]:
            entry = templates[tt]["entries"].get(key)
            if not entry:
                continue

            if isinstance(entry, dict):
                name = key
            else:
                name, entry = entry

            data = {"id": key, "name": name}

            if entry and "_plugin" in entry:
                plugin = pluginManager.get_plugin_info(
                    entry["_plugin"], require_enabled=False
                )
                data["plugin_id"] = plugin.key
                data["plugin_name"] = plugin.name

            result[tt].append(data)

    return jsonify(order=result)


@api.route("/settings/reauthReq", methods=["GET"])
@no_firstrun_access
@Permissions.SETTINGS.require(403)
def fetchReauthRequirements():
    return jsonify({"requirements": _reauth_requirements()})


def _reauth_requirements():
    logger = logging.getLogger(__name__)
    require_reauth = {}
    for plugin in octoprint.plugin.plugin_manager().get_implementations(
        octoprint.plugin.SettingsPlugin
    ):
        plugin_id = plugin._identifier
        try:
            additional = plugin.get_settings_reauth_requirements()
            if additional:
                octoprint.util.dict_merge(
                    require_reauth,
                    {"plugins": {plugin_id: additional}},
                    in_place=True,
                )
        except Exception:
            logger.exception(
                f"Could not determine reauth information for plugin {plugin._plugin_name}",
                extra={"plugin": plugin_id},
            )
            abort(500)

    octoprint.util.dict_merge(require_reauth, REAUTHED_SETTINGS, in_place=True)
    return require_reauth


def _saveSettings(data):
    logger = logging.getLogger(__name__)

    if octoprint.util.dict_contains_any_keys(_reauth_requirements(), data):
        ensure_credentials_checked_recently()

    s = settings()

    # NOTE: Remember to adjust the docs of the data model on the Settings API if anything
    # is changed, added or removed here

    if "folder" in data:
        try:
            folders = data["folder"]
            future = {}
            for folder in FOLDER_TYPES:
                future[folder] = s.getBaseFolder(folder)
                if folder in folders:
                    future[folder] = folders[folder]

            for folder in folders:
                if folder not in FOLDER_TYPES:
                    continue
                for other_folder in FOLDER_TYPES:
                    if folder == other_folder:
                        continue
                    if future[folder] == future[other_folder]:
                        # duplicate detected, raise
                        raise ValueError(
                            "Duplicate folder path for {} and {}".format(
                                folder, other_folder
                            )
                        )

                s.setBaseFolder(folder, future[folder])
        except Exception:
            logger.exception("Something went wrong while saving a folder path")
            abort(400, description="At least one of the configured folders is invalid")

    if "api" in data:
        if "allowCrossOrigin" in data["api"]:
            s.setBoolean(["api", "allowCrossOrigin"], data["api"]["allowCrossOrigin"])

    if "accessControl" in data:
        if "autologinHeadsupAcknowledged" in data["accessControl"]:
            s.setBoolean(
                ["accessControl", "autologinHeadsupAcknowledged"],
                data["accessControl"]["autologinHeadsupAcknowledged"],
            )

    if "appearance" in data:
        if "name" in data["appearance"]:
            s.set(["appearance", "name"], data["appearance"]["name"])
        if "color" in data["appearance"]:
            s.set(["appearance", "color"], data["appearance"]["color"])
        if "colorTransparent" in data["appearance"]:
            s.setBoolean(
                ["appearance", "colorTransparent"],
                data["appearance"]["colorTransparent"],
            )
        if "colorIcon" in data["appearance"]:
            s.setBoolean(["appearance", "colorIcon"], data["appearance"]["colorIcon"])
        if "defaultLanguage" in data["appearance"]:
            s.set(
                ["appearance", "defaultLanguage"], data["appearance"]["defaultLanguage"]
            )
        if "showFahrenheitAlso" in data["appearance"]:
            s.setBoolean(
                ["appearance", "showFahrenheitAlso"],
                data["appearance"]["showFahrenheitAlso"],
            )
        if "fuzzyTimes" in data["appearance"]:
            s.setBoolean(["appearance", "fuzzyTimes"], data["appearance"]["fuzzyTimes"])
        if "closeModalsWithClick" in data["appearance"]:
            s.setBoolean(
                ["appearance", "closeModalsWithClick"],
                data["appearance"]["closeModalsWithClick"],
            )
        if "showInternalFilename" in data["appearance"]:
            s.setBoolean(
                ["appearance", "showInternalFilename"],
                data["appearance"]["showInternalFilename"],
            )

        if "thumbnails" in data["appearance"]:
            thumbnails = data["appearance"]["thumbnails"]
            if "filelistEnabled" in thumbnails:
                s.setBoolean(
                    ["appearance", "thumbnails", "filelistEnabled"],
                    thumbnails["filelistEnabled"],
                )
            if "filelistScale" in thumbnails:
                s.setInt(
                    ["appearance", "thumbnails", "filelistScale"],
                    thumbnails["filelistScale"],
                )
            if "filelistAlignment" in thumbnails and thumbnails["filelistAlignment"] in (
                "left",
                "right",
                "center",
            ):
                s.set(
                    ["appearance", "thumbnails", "filelistAlignment"],
                    thumbnails["filelistAlignment"],
                )
            if "filelistPreview" in thumbnails:
                s.setBoolean(
                    ["appearance", "thumbnails", "filelistPreview"],
                    thumbnails["filelistPreview"],
                )
            if "stateEnabled" in thumbnails:
                s.setBoolean(
                    ["appearance", "thumbnails", "stateEnabled"],
                    thumbnails["stateEnabled"],
                )
            if "stateScale" in thumbnails:
                s.setInt(
                    ["appearance", "thumbnails", "stateScale"], thumbnails["stateScale"]
                )

    if "printer" in data:
        if "defaultExtrusionLength" in data["printer"]:
            s.setInt(
                ["printerParameters", "defaultExtrusionLength"],
                data["printer"]["defaultExtrusionLength"],
            )

    if "webcam" in data:
        for key in DEPRECATED_WEBCAM_KEYS:
            if key in data["webcam"]:
                logger.warning(
                    f"Setting webcam.{key} via the API is no longer supported, please use the individual settings of the default webcam instead."
                )

        if "webcamEnabled" in data["webcam"]:
            s.setBoolean(["webcam", "webcamEnabled"], data["webcam"]["webcamEnabled"])
        if "timelapseEnabled" in data["webcam"]:
            s.setBoolean(
                ["webcam", "timelapseEnabled"], data["webcam"]["timelapseEnabled"]
            )
        if "snapshotTimeout" in data["webcam"]:
            s.setInt(["webcam", "snapshotTimeout"], data["webcam"]["snapshotTimeout"])
        if "snapshotSslValidation" in data["webcam"]:
            s.setBoolean(
                ["webcam", "snapshotSslValidation"],
                data["webcam"]["snapshotSslValidation"],
            )
        if "ffmpegPath" in data["webcam"]:
            s.set(["webcam", "ffmpeg"], data["webcam"]["ffmpegPath"])
        if "ffmpegCommandline" in data["webcam"]:
            commandline = data["webcam"]["ffmpegCommandline"]
            if not all(
                "{" + x + "}" in commandline for x in ("ffmpeg", "input", "output")
            ):
                abort(
                    400,
                    description="Invalid webcam.ffmpegCommandline setting, lacks mandatory {ffmpeg}, {input} or {output}",
                )
            try:
                commandline.format(
                    ffmpeg="ffmpeg",
                    fps="fps",
                    bitrate="bitrate",
                    threads="threads",
                    input="input",
                    output="output",
                    videocodec="videocodec",
                    containerformat="containerformat",
                    filters="filters",
                )
            except Exception:
                # some invalid data we'll refuse to set
                logger.exception("Invalid webcam.ffmpegCommandline setting")
                abort(400, description="Invalid webcam.ffmpegCommandline setting")
            else:
                s.set(["webcam", "ffmpegCommandline"], commandline)
        if "bitrate" in data["webcam"] and data["webcam"]["bitrate"]:
            bitrate = str(data["webcam"]["bitrate"])
            if not TIMELAPSE_BITRATE_PATTERN.match(bitrate):
                abort(
                    400,
                    description="Invalid webcam.bitrate setting, needs to be a valid ffmpeg bitrate",
                )
            s.set(["webcam", "bitrate"], bitrate)
        if "ffmpegThreads" in data["webcam"]:
            s.setInt(["webcam", "ffmpegThreads"], data["webcam"]["ffmpegThreads"])
        if "ffmpegVideoCodec" in data["webcam"] and data["webcam"][
            "ffmpegVideoCodec"
        ] in ("mpeg2video", "libx264"):
            s.set(["webcam", "ffmpegVideoCodec"], data["webcam"]["ffmpegVideoCodec"])
        if "watermark" in data["webcam"]:
            s.setBoolean(["webcam", "watermark"], data["webcam"]["watermark"])
        if "renderAfterPrintDelay" in data["webcam"]:
            s.setInt(
                ["webcam", "renderAfterPrintDelay"],
                data["webcam"]["renderAfterPrintDelay"],
            )
        if "defaultWebcam" in data["webcam"]:
            s.set(["webcam", "defaultWebcam"], data["webcam"]["defaultWebcam"])
        if "snapshotWebcam" in data["webcam"]:
            s.set(["webcam", "snapshotWebcam"], data["webcam"]["snapshotWebcam"])

            # timelapse needs to be reconfigured now since it depends on the current snapshot webcam
            configure_timelapse()

    if "feature" in data:
        if "temperatureGraph" in data["feature"]:
            s.setBoolean(
                ["feature", "temperatureGraph"], data["feature"]["temperatureGraph"]
            )
        if "sdSupport" in data["feature"]:
            s.setBoolean(["feature", "sdSupport"], data["feature"]["sdSupport"])
        if "keyboardControl" in data["feature"]:
            s.setBoolean(
                ["feature", "keyboardControl"], data["feature"]["keyboardControl"]
            )
        if "pollWatched" in data["feature"]:
            s.setBoolean(["feature", "pollWatched"], data["feature"]["pollWatched"])
        if "modelSizeDetection" in data["feature"]:
            s.setBoolean(
                ["feature", "modelSizeDetection"], data["feature"]["modelSizeDetection"]
            )
        if "rememberFileFolder" in data["feature"]:
            s.setBoolean(
                ["feature", "rememberFileFolder"],
                data["feature"]["rememberFileFolder"],
            )
        if "printStartConfirmation" in data["feature"]:
            s.setBoolean(
                ["feature", "printStartConfirmation"],
                data["feature"]["printStartConfirmation"],
            )
        if "printCancelConfirmation" in data["feature"]:
            s.setBoolean(
                ["feature", "printCancelConfirmation"],
                data["feature"]["printCancelConfirmation"],
            )
        if "uploadOverwriteConfirmation" in data["feature"]:
            s.setBoolean(
                ["feature", "uploadOverwriteConfirmation"],
                data["feature"]["uploadOverwriteConfirmation"],
            )
        if "fileDeleteConfirmation" in data["feature"]:
            s.setBoolean(
                ["feature", "fileDeleteConfirmation"],
                data["feature"]["fileDeleteConfirmation"],
            )
        if "g90InfluencesExtruder" in data["feature"]:
            s.setBoolean(
                ["feature", "g90InfluencesExtruder"],
                data["feature"]["g90InfluencesExtruder"],
            )
        if "autoUppercaseBlacklist" in data["feature"] and isinstance(
            data["feature"]["autoUppercaseBlacklist"], (list, tuple)
        ):
            s.set(
                ["feature", "autoUppercaseBlacklist"],
                data["feature"]["autoUppercaseBlacklist"],
            )
        if "enableDragDropUpload" in data["feature"]:
            s.setBoolean(
                ["feature", "enableDragDropUpload"],
                data["feature"]["enableDragDropUpload"],
            )

    if "gcodeAnalysis" in data:
        if "runAt" in data["gcodeAnalysis"]:
            s.set(["gcodeAnalysis", "runAt"], data["gcodeAnalysis"]["runAt"])
        if "bedZ" in data["gcodeAnalysis"]:
            s.setFloat(["gcodeAnalysis", "bedZ"], data["gcodeAnalysis"]["bedZ"])

    if "serial" in data and not api_version_matches(">=1.12.0"):
        _set_serial_settings(data["serial"])

    if "temperature" in data:
        if "profiles" in data["temperature"]:
            result = []
            for profile in data["temperature"]["profiles"]:
                try:
                    profile["bed"] = int(profile["bed"])
                    profile["extruder"] = int(profile["extruder"])
                except ValueError:
                    pass
                result.append(profile)
            s.set(["temperature", "profiles"], result)
        if "cutoff" in data["temperature"]:
            try:
                cutoff = int(data["temperature"]["cutoff"])
                if cutoff > 1:
                    s.setInt(["temperature", "cutoff"], cutoff)
            except ValueError:
                pass
        if "sendAutomatically" in data["temperature"]:
            s.setBoolean(
                ["temperature", "sendAutomatically"],
                data["temperature"]["sendAutomatically"],
            )
        if "sendAutomaticallyAfter" in data["temperature"]:
            s.setInt(
                ["temperature", "sendAutomaticallyAfter"],
                data["temperature"]["sendAutomaticallyAfter"],
                min=0,
                max=30,
            )

    if "terminalFilters" in data:
        s.set(["terminalFilters"], data["terminalFilters"])

    if "system" in data:
        if "actions" in data["system"]:
            s.set(["system", "actions"], data["system"]["actions"])

    if "scripts" in data:
        if "gcode" in data["scripts"] and isinstance(data["scripts"]["gcode"], dict):
            for name, script in data["scripts"]["gcode"].items():
                if name == "snippets":
                    continue
                if not isinstance(script, str):
                    continue
                s.saveScript(
                    "gcode", name, script.replace("\r\n", "\n").replace("\r", "\n")
                )

    if "controls" in data and isinstance(data["controls"], list):

        def sanitize_control(control):
            if not isinstance(control, dict):
                return None

            try:
                if "children" in control:
                    return CustomControlContainer(**control)
                else:
                    return CustomControl(**control)
            except Exception:
                logger.exception("Error validating custom control")

            return None

        sanitized = [sanitize_control(item) for item in data["controls"]]
        if any(x is None for x in sanitized):
            logging.getLogger(
                "There were invalid custom controls provided, not saving..."
            )
        else:
            s.set(["controls"], data["controls"])

    if "server" in data:
        if "commands" in data["server"]:
            if "systemShutdownCommand" in data["server"]["commands"]:
                s.set(
                    ["server", "commands", "systemShutdownCommand"],
                    data["server"]["commands"]["systemShutdownCommand"],
                )
            if "systemRestartCommand" in data["server"]["commands"]:
                s.set(
                    ["server", "commands", "systemRestartCommand"],
                    data["server"]["commands"]["systemRestartCommand"],
                )
            if "serverRestartCommand" in data["server"]["commands"]:
                s.set(
                    ["server", "commands", "serverRestartCommand"],
                    data["server"]["commands"]["serverRestartCommand"],
                )
        if "diskspace" in data["server"]:
            if "warning" in data["server"]["diskspace"]:
                s.setInt(
                    ["server", "diskspace", "warning"],
                    data["server"]["diskspace"]["warning"],
                )
            if "critical" in data["server"]["diskspace"]:
                s.setInt(
                    ["server", "diskspace", "critical"],
                    data["server"]["diskspace"]["critical"],
                )
        if "onlineCheck" in data["server"]:
            if "enabled" in data["server"]["onlineCheck"]:
                s.setBoolean(
                    ["server", "onlineCheck", "enabled"],
                    data["server"]["onlineCheck"]["enabled"],
                )
            if "interval" in data["server"]["onlineCheck"]:
                try:
                    interval = int(data["server"]["onlineCheck"]["interval"])
                    s.setInt(["server", "onlineCheck", "interval"], interval * 60)
                except ValueError:
                    pass
            if "host" in data["server"]["onlineCheck"]:
                s.set(
                    ["server", "onlineCheck", "host"],
                    data["server"]["onlineCheck"]["host"],
                )
            if "port" in data["server"]["onlineCheck"]:
                s.setInt(
                    ["server", "onlineCheck", "port"],
                    data["server"]["onlineCheck"]["port"],
                )
            if "name" in data["server"]["onlineCheck"]:
                s.set(
                    ["server", "onlineCheck", "name"],
                    data["server"]["onlineCheck"]["name"],
                )
        if "pluginBlacklist" in data["server"]:
            if "enabled" in data["server"]["pluginBlacklist"]:
                s.setBoolean(
                    ["server", "pluginBlacklist", "enabled"],
                    data["server"]["pluginBlacklist"]["enabled"],
                )
            if "url" in data["server"]["pluginBlacklist"]:
                s.set(
                    ["server", "pluginBlacklist", "url"],
                    data["server"]["pluginBlacklist"]["url"],
                )
            if "ttl" in data["server"]["pluginBlacklist"]:
                try:
                    ttl = int(data["server"]["pluginBlacklist"]["ttl"])
                    s.setInt(["server", "pluginBlacklist", "ttl"], ttl * 60)
                except ValueError:
                    pass
        if "allowFraming" in data["server"]:
            s.setBoolean(["server", "allowFraming"], data["server"]["allowFraming"])

    if "devel" in data:
        oldLog = s.getBoolean(["devel", "pluginTimings"])
        if "pluginTimings" in data["devel"]:
            s.setBoolean(["devel", "pluginTimings"], data["devel"]["pluginTimings"])
        if oldLog and not s.getBoolean(["devel", "pluginTimings"]):
            # disable plugin timing logging to plugintimings.log
            logging.getLogger("PLUGIN_TIMINGS").debug("Disabling plugin timings logging")
            logging.getLogger("PLUGIN_TIMINGS").setLevel(logging.INFO)
        elif not oldLog and s.getBoolean(["devel", "pluginTimings"]):
            # enable plugin timing logging to plugintimings.log
            logging.getLogger("PLUGIN_TIMINGS").setLevel(logging.DEBUG)
            logging.getLogger("PLUGIN_TIMINGS").debug("Enabling plugin timings logging")

    if "slicing" in data:
        if "defaultSlicer" in data["slicing"]:
            s.set(["slicing", "defaultSlicer"], data["slicing"]["defaultSlicer"])

    if "plugins" in data:
        for plugin in octoprint.plugin.plugin_manager().get_implementations(
            octoprint.plugin.SettingsPlugin
        ):
            plugin_id = plugin._identifier
            if plugin_id in data["plugins"]:
                try:
                    plugin.on_settings_save(data["plugins"][plugin_id])
                except TypeError:
                    logger.warning(
                        "Could not save settings for plugin {name} ({version}). It may have called super(...)".format(
                            name=plugin._plugin_name, version=plugin._plugin_version
                        )
                    )
                    logger.warning(
                        "in a way which has issues due to OctoPrint's dynamic reloading after plugin operations."
                    )
                    logger.warning(
                        "Please contact the plugin's author and ask to update the plugin to use a direct call like"
                    )
                    logger.warning(
                        "octoprint.plugin.SettingsPlugin.on_settings_save(self, data) instead.",
                        exc_info=True,
                    )
                except Exception:
                    logger.exception(
                        "Could not save settings for plugin {name} ({version})".format(
                            version=plugin._plugin_version, name=plugin._plugin_name
                        ),
                        extra={"plugin": plugin._identifier},
                    )

    s.save(trigger_event=True)


# pre 1.12.0 settings API still contains serial settings, backwards compatibility layer starts here


def _get_serial_settings():
    from octoprint.printer.connection import ConnectedPrinter

    s = settings()

    serial_connector = ConnectedPrinter.find("serial")
    if serial_connector:
        connection_options = serial_connector.connection_options()
    else:
        connection_options = {}

    preferred_connection_connector = s.get(
        ["printerConnection", "preferred", "connector"]
    )
    preferred_connection_params = {}
    if preferred_connection_connector == "serial":
        preferred_connection_params = s.get(
            ["printerConnection", "preferred", "parameters"]
        )

    return {
        "port": preferred_connection_params.get("port"),
        "baudrate": preferred_connection_params.get("baudrate"),
        "exclusive": s.getBoolean(["plugins", "serial_connector", "exclusive"]),
        "lowLatency": s.getBoolean(["plugins", "serial_connector", "lowLatency"]),
        "portOptions": connection_options.get("ports", []),
        "baudrateOptions": connection_options.get("baudrates", []),
        "autoconnect": s.getBoolean(["plugins", "serial_connector", "autoconnect"]),
        "timeoutConnection": s.getFloat(
            ["plugins", "serial_connector", "timeout", "connection"]
        ),
        "timeoutDetectionFirst": s.getFloat(
            ["plugins", "serial_connector", "timeout", "detectionFirst"]
        ),
        "timeoutDetectionConsecutive": s.getFloat(
            ["plugins", "serial_connector", "timeout", "detectionConsecutive"]
        ),
        "timeoutCommunication": s.getFloat(
            ["plugins", "serial_connector", "timeout", "communication"]
        ),
        "timeoutCommunicationBusy": s.getFloat(
            ["plugins", "serial_connector", "timeout", "communicationBusy"]
        ),
        "timeoutTemperature": s.getFloat(
            ["plugins", "serial_connector", "timeout", "temperature"]
        ),
        "timeoutTemperatureTargetSet": s.getFloat(
            ["plugins", "serial_connector", "timeout", "temperatureTargetSet"]
        ),
        "timeoutTemperatureAutoreport": s.getFloat(
            ["plugins", "serial_connector", "timeout", "temperatureAutoreport"]
        ),
        "timeoutSdStatus": s.getFloat(
            ["plugins", "serial_connector", "timeout", "sdStatus"]
        ),
        "timeoutSdStatusAutoreport": s.getFloat(
            ["plugins", "serial_connector", "timeout", "sdStatusAutoreport"]
        ),
        "timeoutPosAutoreport": s.getFloat(
            ["plugins", "serial_connector", "timeout", "posAutoreport"]
        ),
        "timeoutBaudrateDetectionPause": s.getFloat(
            ["plugins", "serial_connector", "timeout", "baudrateDetectionPause"]
        ),
        "timeoutPositionLogWait": s.getFloat(
            ["plugins", "serial_connector", "timeout", "positionLogWait"]
        ),
        "log": s.getBoolean(["plugins", "serial_connector", "log"]),
        "additionalPorts": s.get(["plugins", "serial_connector", "additionalPorts"]),
        "additionalBaudrates": s.get(
            ["plugins", "serial_connector", "additionalBaudrates"]
        ),
        "blacklistedPorts": s.get(["plugins", "serial_connector", "blacklistedPorts"]),
        "blacklistedBaudrates": s.get(
            ["plugins", "serial_connector", "blacklistedBaudrates"]
        ),
        "longRunningCommands": s.get(
            ["plugins", "serial_connector", "longRunningCommands"]
        ),
        "checksumRequiringCommands": s.get(
            ["plugins", "serial_connector", "checksumRequiringCommands"]
        ),
        "blockedCommands": s.get(["plugins", "serial_connector", "blockedCommands"]),
        "ignoredCommands": s.get(["plugins", "serial_connector", "ignoredCommands"]),
        "pausingCommands": s.get(["plugins", "serial_connector", "pausingCommands"]),
        "sdCancelCommand": s.get(["plugins", "serial_connector", "sdCancelCommand"]),
        "emergencyCommands": s.get(["plugins", "serial_connector", "emergencyCommands"]),
        "helloCommand": s.get(["plugins", "serial_connector", "helloCommand"]),
        "ignoreErrorsFromFirmware": s.get(
            ["plugins", "serial_connector", "errorHandling"]
        )
        == "ignore",
        "disconnectOnErrors": s.get(["plugins", "serial_connector", "errorHandling"])
        == "disconnect",
        "triggerOkForM29": s.getBoolean(
            ["plugins", "serial_connector", "triggerOkForM29"]
        ),
        "logPositionOnPause": s.getBoolean(
            ["plugins", "serial_connector", "logPositionOnPause"]
        ),
        "logPositionOnCancel": s.getBoolean(
            ["plugins", "serial_connector", "logPositionOnCancel"]
        ),
        "abortHeatupOnCancel": s.getBoolean(
            ["plugins", "serial_connector", "abortHeatupOnCancel"]
        ),
        "supportResendsWithoutOk": s.get(
            ["plugins", "serial_connector", "supportResendsWithoutOk"]
        ),
        "waitForStart": s.getBoolean(
            ["plugins", "serial_connector", "waitForStartOnConnect"]
        ),
        "waitToLoadSdFileList": s.getBoolean(
            ["plugins", "serial_connector", "waitToLoadSdFileList"]
        ),
        "alwaysSendChecksum": s.get(["plugins", "serial_connector", "sendChecksum"])
        == "always",
        "neverSendChecksum": s.getBoolean(["plugins", "serial_connector", "sendChecksum"])
        == "never",
        "sendChecksumWithUnknownCommands": s.getBoolean(
            ["plugins", "serial_connector", "sendChecksumWithUnknownCommands"]
        ),
        "unknownCommandsNeedAck": s.getBoolean(
            ["plugins", "serial_connector", "unknownCommandsNeedAck"]
        ),
        "sdRelativePath": s.getBoolean(["plugins", "serial_connector", "sdRelativePath"]),
        "sdAlwaysAvailable": s.getBoolean(
            ["plugins", "serial_connector", "sdAlwaysAvailable"]
        ),
        "sdLowerCase": s.getBoolean(["plugins", "serial_connector", "sdLowerCase"]),
        "swallowOkAfterResend": s.getBoolean(
            ["plugins", "serial_connector", "swallowOkAfterResend"]
        ),
        "repetierTargetTemp": s.getBoolean(
            ["plugins", "serial_connector", "repetierTargetTemp"]
        ),
        "externalHeatupDetection": s.getBoolean(
            ["plugins", "serial_connector", "externalHeatupDetection"]
        ),
        "ignoreIdenticalResends": s.getBoolean(
            ["plugins", "serial_connector", "ignoreIdenticalResends"]
        ),
        "firmwareDetection": s.getBoolean(
            ["plugins", "serial_connector", "firmwareDetection"]
        ),
        "blockWhileDwelling": s.getBoolean(
            ["plugins", "serial_connector", "blockWhileDwelling"]
        ),
        "useParityWorkaround": s.get(
            ["plugins", "serial_connector", "useParityWorkaround"]
        ),
        "sanityCheckTools": s.getBoolean(
            ["plugins", "serial_connector", "sanityCheckTools"]
        ),
        "notifySuppressedCommands": s.get(
            ["plugins", "serial_connector", "notifySuppressedCommands"]
        ),
        "sendM112OnError": s.getBoolean(
            ["plugins", "serial_connector", "sendM112OnError"]
        ),
        "disableSdPrintingDetection": s.getBoolean(
            ["plugins", "serial_connector", "disableSdPrintingDetection"]
        ),
        "ackMax": s.getInt(["plugins", "serial_connector", "ackMax"]),
        "maxTimeoutsIdle": s.getInt(
            ["plugins", "serial_connector", "maxCommunicationTimeouts", "idle"]
        ),
        "maxTimeoutsPrinting": s.getInt(
            ["plugins", "serial_connector", "maxCommunicationTimeouts", "printing"]
        ),
        "maxTimeoutsLong": s.getInt(
            ["plugins", "serial_connector", "maxCommunicationTimeouts", "long"]
        ),
        "capAutoreportTemp": s.getBoolean(
            ["plugins", "serial_connector", "capabilities", "autoreport_temp"]
        ),
        "capAutoreportSdStatus": s.getBoolean(
            ["plugins", "serial_connector", "capabilities", "autoreport_sdstatus"]
        ),
        "capAutoreportPos": s.getBoolean(
            ["plugins", "serial_connector", "capabilities", "autoreport_pos"]
        ),
        "capBusyProtocol": s.getBoolean(
            ["plugins", "serial_connector", "capabilities", "busy_protocol"]
        ),
        "capEmergencyParser": s.getBoolean(
            ["plugins", "serial_connector", "capabilities", "emergency_parser"]
        ),
        "capExtendedM20": s.getBoolean(
            ["plugins", "serial_connector", "capabilities", "extended_m20"]
        ),
        "capLfnWrite": s.getBoolean(
            ["plugins", "serial_connector", "capabilities", "lfn_write"]
        ),
        "resendRatioThreshold": s.getInt(
            ["plugins", "serial_connector", "resendRatioThreshold"]
        ),
        "resendRatioStart": s.getInt(["plugins", "serial_connector", "resendRatioStart"]),
        "ignoreEmptyPorts": s.getBoolean(
            ["plugins", "serial_connector", "ignoreEmptyPorts"]
        ),
        "encoding": s.get(["plugins", "serial_connector", "encoding"]),
        "enableShutdownActionCommand": s.get(
            ["plugins", "serial_connector", "enableShutdownActionCommand"]
        ),
    }


def _set_serial_settings(data: dict[str, Any]):
    s = settings()

    # if we see autoconnect, port or baudrate coming in, set the related settings on
    # the printerConnection subtree
    if "autoconnect" in data:
        s.setBoolean(["printerConnection", "autoconnect"], data["autoconnect"])
    if "port" in data or "baudrate" in data:
        s.set(["printerConnection", "preferred", "connector"], "serial")
        s.set(
            ["printerConnection", "preferred", "parameters"],
            {"port": data.get("port", "AUTO"), "baudrate": data.get("baudrate")},
        )

    # handle the other serial settings
    if "exclusive" in data:
        s.setBoolean(["plugins", "serial_connector", "exclusive"], data["exclusive"])
    if "lowLatency" in data:
        s.setBoolean(["plugins", "serial_connector", "lowLatency"], data["lowLatency"])
    if "timeoutConnection" in data:
        s.setFloat(
            ["plugins", "serial_connector", "timeout", "connection"],
            data["timeoutConnection"],
            min=1.0,
        )
    if "timeoutDetectionFirst" in data:
        s.setFloat(
            ["plugins", "serial_connector", "timeout", "detectionFirst"],
            data["timeoutDetectionFirst"],
            min=1.0,
        )
    if "timeoutDetectionConsecutive" in data:
        s.setFloat(
            ["plugins", "serial_connector", "timeout", "detectionConsecutive"],
            data["timeoutDetectionConsecutive"],
            min=1.0,
        )
    if "timeoutCommunication" in data:
        s.setFloat(
            ["plugins", "serial_connector", "timeout", "communication"],
            data["timeoutCommunication"],
            min=1.0,
        )
    if "timeoutCommunicationBusy" in data:
        s.setFloat(
            ["plugins", "serial_connector", "timeout", "communicationBusy"],
            data["timeoutCommunicationBusy"],
            min=1.0,
        )
    if "timeoutTemperature" in data:
        s.setFloat(
            ["plugins", "serial_connector", "timeout", "temperature"],
            data["timeoutTemperature"],
            min=1.0,
        )
    if "timeoutTemperatureTargetSet" in data:
        s.setFloat(
            ["plugins", "serial_connector", "timeout", "temperatureTargetSet"],
            data["timeoutTemperatureTargetSet"],
            min=1.0,
        )
    if "timeoutTemperatureAutoreport" in data:
        s.setFloat(
            ["plugins", "serial_connector", "timeout", "temperatureAutoreport"],
            data["timeoutTemperatureAutoreport"],
            min=0.0,
        )
    if "timeoutSdStatus" in data:
        s.setFloat(
            ["plugins", "serial_connector", "timeout", "sdStatus"],
            data["timeoutSdStatus"],
            min=1.0,
        )
    if "timeoutSdStatusAutoreport" in data:
        s.setFloat(
            ["plugins", "serial_connector", "timeout", "sdStatusAutoreport"],
            data["timeoutSdStatusAutoreport"],
            min=0.0,
        )
    if "timeoutPosAutoreport" in data:
        s.setFloat(
            ["plugins", "serial_connector", "timeout", "posAutoreport"],
            data["timeoutPosAutoreport"],
            min=0.0,
        )
    if "timeoutBaudrateDetectionPause" in data:
        s.setFloat(
            ["plugins", "serial_connector", "timeout", "baudrateDetectionPause"],
            data["timeoutBaudrateDetectionPause"],
            min=0.0,
        )
    if "timeoutPositionLogWait" in data:
        s.setFloat(
            ["plugins", "serial_connector", "timeout", "positionLogWait"],
            data["timeoutPositionLogWait"],
            min=1.0,
        )
    if "additionalPorts" in data and isinstance(data["additionalPorts"], (list, tuple)):
        s.set(["plugins", "serial_connector", "additionalPorts"], data["additionalPorts"])
    if "additionalBaudrates" in data and isinstance(
        data["additionalBaudrates"], (list, tuple)
    ):
        s.set(
            ["plugins", "serial_connector", "additionalBaudrates"],
            data["additionalBaudrates"],
        )
    if "blacklistedPorts" in data and isinstance(data["blacklistedPorts"], (list, tuple)):
        s.set(
            ["plugins", "serial_connector", "blacklistedPorts"], data["blacklistedPorts"]
        )
    if "blacklistedBaudrates" in data and isinstance(
        data["blacklistedBaudrates"], (list, tuple)
    ):
        s.set(
            ["plugins", "serial_connector", "blacklistedBaudrates"],
            data["blacklistedBaudrates"],
        )
    if "longRunningCommands" in data and isinstance(
        data["longRunningCommands"], (list, tuple)
    ):
        s.set(
            ["plugins", "serial_connector", "longRunningCommands"],
            data["longRunningCommands"],
        )
    if "checksumRequiringCommands" in data and isinstance(
        data["checksumRequiringCommands"], (list, tuple)
    ):
        s.set(
            ["plugins", "serial_connector", "checksumRequiringCommands"],
            data["checksumRequiringCommands"],
        )
    if "blockedCommands" in data and isinstance(data["blockedCommands"], (list, tuple)):
        s.set(["plugins", "serial_connector", "blockedCommands"], data["blockedCommands"])
    if "ignoredCommands" in data and isinstance(data["ignoredCommands"], (list, tuple)):
        s.set(["plugins", "serial_connector", "ignoredCommands"], data["ignoredCommands"])
    if "pausingCommands" in data and isinstance(data["pausingCommands"], (list, tuple)):
        s.set(["plugins", "serial_connector", "pausingCommands"], data["pausingCommands"])
    if "sdCancelCommand" in data:
        s.set(["plugins", "serial_connector", "sdCancelCommand"], data["sdCancelCommand"])
    if "emergencyCommands" in data and isinstance(
        data["emergencyCommands"], (list, tuple)
    ):
        s.set(
            ["plugins", "serial_connector", "emergencyCommands"],
            data["emergencyCommands"],
        )
    if "helloCommand" in data:
        s.set(["plugins", "serial_connector", "helloCommand"], data["helloCommand"])
    if "disconnectOnErrors" in data or "ignoreErrorsFromFirmware" in data:
        if data.get("disconnectOnErrors", False):
            value = "disconnect"
        elif data.get("ignoreErrorsFromFirmware", False):
            value = "ignore"
        else:
            value = "cancel"
        s.set(["plugins", "serial_connecetor", "errorHandling"], value)
    if "triggerOkForM29" in data:
        s.setBoolean(
            ["plugins", "serial_connector", "triggerOkForM29"], data["triggerOkForM29"]
        )
    if "supportResendsWithoutOk" in data:
        value = data["supportResendsWithoutOk"]
        if value in ("always", "detect", "never"):
            s.set(["plugins", "serial_connector", "supportResendsWithoutOk"], value)
    if "waitForStart" in data:
        s.setBoolean(
            ["plugins", "serial_connector", "waitForStartOnConnect"], data["waitForStart"]
        )
    if "waitToLoadSdFileList" in data:
        s.setBoolean(
            ["plugins", "serial_connector", "waitToLoadSdFileList"],
            data["waitToLoadSdFileList"],
        )
    if "alwaysSendChecksum" in data or "neverSendChecksum" in data:
        if data.get("alwaysSendChecksum", False):
            value = "always"
        elif data.get("neverSendChecksum", False):
            value = "never"
        else:
            value = "print"
        s.set(["plugins", "serial_connector", "sendChecksum"], value)
    if "sendChecksumWithUnknownCommands" in data:
        s.setBoolean(
            ["plugins", "serial_connector", "sendChecksumWithUnknownCommands"],
            data["sendChecksumWithUnknownCommands"],
        )
    if "unknownCommandsNeedAck" in data:
        s.setBoolean(
            ["plugins", "serial_connector", "unknownCommandsNeedAck"],
            data["unknownCommandsNeedAck"],
        )
    if "sdRelativePath" in data:
        s.setBoolean(
            ["plugins", "serial_connector", "sdRelativePath"], data["sdRelativePath"]
        )
    if "sdAlwaysAvailable" in data:
        s.setBoolean(
            ["plugins", "serial_connector", "sdAlwaysAvailable"],
            data["sdAlwaysAvailable"],
        )
    if "sdLowerCase" in data:
        s.setBoolean(["plugins", "serial_connector", "sdLowerCase"], data["sdLowerCase"])
    if "swallowOkAfterResend" in data:
        s.setBoolean(
            ["plugins", "serial_connector", "swallowOkAfterResend"],
            data["swallowOkAfterResend"],
        )
    if "repetierTargetTemp" in data:
        s.setBoolean(
            ["plugins", "serial_connector", "repetierTargetTemp"],
            data["repetierTargetTemp"],
        )
    if "externalHeatupDetection" in data:
        s.setBoolean(
            ["plugins", "serial_connector", "externalHeatupDetection"],
            data["externalHeatupDetection"],
        )
    if "ignoreIdenticalResends" in data:
        s.setBoolean(
            ["plugins", "serial_connector", "ignoreIdenticalResends"],
            data["ignoreIdenticalResends"],
        )
    if "firmwareDetection" in data:
        s.setBoolean(
            ["plugins", "serial_connector", "firmwareDetection"],
            data["firmwareDetection"],
        )
    if "blockWhileDwelling" in data:
        s.setBoolean(
            ["plugins", "serial_connector", "blockWhileDwelling"],
            data["blockWhileDwelling"],
        )
    if "useParityWorkaround" in data:
        value = data["useParityWorkaround"]
        if value in ("always", "detect", "never"):
            s.set(["plugins", "serial_connector", "useParityWorkaround"], value)
    if "sanityCheckTools" in data:
        s.setBoolean(
            ["plugins", "serial_connector", "sanityCheckTools"], data["sanityCheckTools"]
        )
    if "notifySuppressedCommands" in data:
        value = data["notifySuppressedCommands"]
        if value in ("info", "warn", "never"):
            s.set(["plugins", "serial_connector", "notifySuppressedCommands"], value)
    if "sendM112OnError" in data:
        s.setBoolean(
            ["plugins", "serial_connector", "sendM112OnError"], data["sendM112OnError"]
        )
    if "disableSdPrintingDetection" in data:
        s.setBoolean(
            ["plugins", "serial_connector", "disableSdPrintingDetection"],
            data["disableSdPrintingDetection"],
        )
    if "ackMax" in data:
        s.setInt(["plugins", "serial_connector", "ackMax"], data["ackMax"])
    if "logPositionOnPause" in data:
        s.setBoolean(
            ["plugins", "serial_connector", "logPositionOnPause"],
            data["logPositionOnPause"],
        )
    if "logPositionOnCancel" in data:
        s.setBoolean(
            ["plugins", "serial_connector", "logPositionOnCancel"],
            data["logPositionOnCancel"],
        )
    if "abortHeatupOnCancel" in data:
        s.setBoolean(
            ["plugins", "serial_connector", "abortHeatupOnCancel"],
            data["abortHeatupOnCancel"],
        )
    if "maxTimeoutsIdle" in data:
        s.setInt(
            ["plugins", "serial_connector", "maxCommunicationTimeouts", "idle"],
            data["maxTimeoutsIdle"],
        )
    if "maxTimeoutsPrinting" in data:
        s.setInt(
            ["plugins", "serial_connector", "maxCommunicationTimeouts", "printing"],
            data["maxTimeoutsPrinting"],
        )
    if "maxTimeoutsLong" in data:
        s.setInt(
            ["plugins", "serial_connector", "maxCommunicationTimeouts", "long"],
            data["maxTimeoutsLong"],
        )
    if "capAutoreportTemp" in data:
        s.setBoolean(
            ["plugins", "serial_connector", "capabilities", "autoreport_temp"],
            data["capAutoreportTemp"],
        )
    if "capAutoreportSdStatus" in data:
        s.setBoolean(
            ["plugins", "serial_connector", "capabilities", "autoreport_sdstatus"],
            data["capAutoreportSdStatus"],
        )
    if "capAutoreportPos" in data:
        s.setBoolean(
            ["plugins", "serial_connector", "capabilities", "autoreport_pos"],
            data["capAutoreportPos"],
        )
    if "capBusyProtocol" in data:
        s.setBoolean(
            ["plugins", "serial_connector", "capabilities", "busy_protocol"],
            data["capBusyProtocol"],
        )
    if "capEmergencyParser" in data:
        s.setBoolean(
            ["plugins", "serial_connector", "capabilities", "emergency_parser"],
            data["capEmergencyParser"],
        )
    if "capExtendedM20" in data:
        s.setBoolean(
            ["plugins", "serial_connector", "capabilities", "extended_m20"],
            data["capExtendedM20"],
        )
    if "capLfnWrite" in data:
        s.setBoolean(
            ["plugins", "serial_connector", "capabilities", "lfn_write"],
            data["capLfnWrite"],
        )
    if "resendRatioThreshold" in data:
        s.setInt(
            ["plugins", "serial_connector", "resendRatioThreshold"],
            data["resendRatioThreshold"],
        )
    if "resendRatioStart" in data:
        s.setInt(
            ["plugins", "serial_connector", "resendRatioStart"], data["resendRatioStart"]
        )
    if "ignoreEmptyPorts" in data:
        s.setBoolean(
            ["plugins", "serial_connector", "ignoreEmptyPorts"], data["ignoreEmptyPorts"]
        )

    if "encoding" in data:
        s.set(["plugins", "serial_connector", "encoding"], data["encoding"])

    if "enableShutdownActionCommand" in data:
        s.setBoolean(
            ["plugins", "serial_connector", "enableShutdownActionCommand"],
            data["enableShutdownActionCommand"],
        )

    oldLog = s.getBoolean(["plugins", "serial_connector", "log"])
    if "log" in data:
        s.setBoolean(["plugins", "serial_connector", "log"], data["log"])
    if oldLog and not s.getBoolean(["plugins", "serial_connector", "log"]):
        # disable debug logging to serial.log
        logging.getLogger("SERIAL").debug("Disabling serial logging")
        logging.getLogger("SERIAL").setLevel(logging.CRITICAL)
    elif not oldLog and s.getBoolean(["plugins", "serial_connector", "log"]):
        # enable debug logging to serial.log
        logging.getLogger("SERIAL").setLevel(logging.DEBUG)
        logging.getLogger("SERIAL").debug("Enabling serial logging")
