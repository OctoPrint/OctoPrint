__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging
import re

from flask import abort, jsonify, request
from flask_login import current_user

import octoprint.plugin
import octoprint.util
from octoprint.access.permissions import Permissions
from octoprint.server import pluginManager, printer, userManager
from octoprint.server.api import NO_CONTENT, api
from octoprint.server.util.flask import no_firstrun_access, with_revalidation_checking
from octoprint.settings import settings, valid_boolean_trues

# ~~ settings

FOLDER_TYPES = ("uploads", "timelapse", "watched")
TIMELAPSE_BITRATE_PATTERN = re.compile(r"\d+[KMGTPEZY]?i?B?", flags=re.IGNORECASE)


def _lastmodified():
    return settings().last_modified


def _etag(lm=None):
    if lm is None:
        lm = _lastmodified()

    connection_options = printer.__class__.get_connection_options()
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

    # connection options are also part of the settings
    hash_update(repr(connection_options))

    # if the list of plugins changes, the settings structure changes too
    hash_update(repr(plugins))

    # and likewise if the role of the user changes
    hash_update(repr(roles))

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

    connectionOptions = printer.__class__.get_connection_options()

    # NOTE: Remember to adjust the docs of the data model on the Settings API if anything
    # is changed, added or removed here

    data = {
        "api": {
            "key": s.get(["api", "key"]) if Permissions.ADMIN.can() else None,
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
        },
        "webcam": {
            "webcamEnabled": s.getBoolean(["webcam", "webcamEnabled"]),
            "timelapseEnabled": s.getBoolean(["webcam", "timelapseEnabled"]),
            "streamUrl": s.get(["webcam", "stream"]),
            "streamRatio": s.get(["webcam", "streamRatio"]),
            "streamTimeout": s.getInt(["webcam", "streamTimeout"]),
            "streamWebrtcIceServers": s.get(["webcam", "streamWebrtcIceServers"]),
            "snapshotUrl": s.get(["webcam", "snapshot"]),
            "snapshotTimeout": s.getInt(["webcam", "snapshotTimeout"]),
            "snapshotSslValidation": s.getBoolean(["webcam", "snapshotSslValidation"]),
            "ffmpegPath": s.get(["webcam", "ffmpeg"]),
            "ffmpegCommandline": s.get(["webcam", "ffmpegCommandline"]),
            "bitrate": s.get(["webcam", "bitrate"]),
            "ffmpegThreads": s.get(["webcam", "ffmpegThreads"]),
            "ffmpegVideoCodec": s.get(["webcam", "ffmpegVideoCodec"]),
            "watermark": s.getBoolean(["webcam", "watermark"]),
            "flipH": s.getBoolean(["webcam", "flipH"]),
            "flipV": s.getBoolean(["webcam", "flipV"]),
            "rotate90": s.getBoolean(["webcam", "rotate90"]),
            "cacheBuster": s.getBoolean(["webcam", "cacheBuster"]),
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
            "g90InfluencesExtruder": s.getBoolean(["feature", "g90InfluencesExtruder"]),
            "autoUppercaseBlacklist": s.get(["feature", "autoUppercaseBlacklist"]),
        },
        "gcodeAnalysis": {
            "runAt": s.get(["gcodeAnalysis", "runAt"]),
            "bedZ": s.getFloat(["gcodeAnalysis", "bedZ"]),
        },
        "serial": {
            "port": connectionOptions["portPreference"],
            "baudrate": connectionOptions["baudratePreference"],
            "exclusive": s.getBoolean(["serial", "exclusive"]),
            "lowLatency": s.getBoolean(["serial", "lowLatency"]),
            "portOptions": connectionOptions["ports"],
            "baudrateOptions": connectionOptions["baudrates"],
            "autoconnect": s.getBoolean(["serial", "autoconnect"]),
            "timeoutConnection": s.getFloat(["serial", "timeout", "connection"]),
            "timeoutDetectionFirst": s.getFloat(["serial", "timeout", "detectionFirst"]),
            "timeoutDetectionConsecutive": s.getFloat(
                ["serial", "timeout", "detectionConsecutive"]
            ),
            "timeoutCommunication": s.getFloat(["serial", "timeout", "communication"]),
            "timeoutCommunicationBusy": s.getFloat(
                ["serial", "timeout", "communicationBusy"]
            ),
            "timeoutTemperature": s.getFloat(["serial", "timeout", "temperature"]),
            "timeoutTemperatureTargetSet": s.getFloat(
                ["serial", "timeout", "temperatureTargetSet"]
            ),
            "timeoutTemperatureAutoreport": s.getFloat(
                ["serial", "timeout", "temperatureAutoreport"]
            ),
            "timeoutSdStatus": s.getFloat(["serial", "timeout", "sdStatus"]),
            "timeoutSdStatusAutoreport": s.getFloat(
                ["serial", "timeout", "sdStatusAutoreport"]
            ),
            "timeoutPosAutoreport": s.getFloat(["serial", "timeout", "posAutoreport"]),
            "timeoutBaudrateDetectionPause": s.getFloat(
                ["serial", "timeout", "baudrateDetectionPause"]
            ),
            "timeoutPositionLogWait": s.getFloat(
                ["serial", "timeout", "positionLogWait"]
            ),
            "log": s.getBoolean(["serial", "log"]),
            "additionalPorts": s.get(["serial", "additionalPorts"]),
            "additionalBaudrates": s.get(["serial", "additionalBaudrates"]),
            "blacklistedPorts": s.get(["serial", "blacklistedPorts"]),
            "blacklistedBaudrates": s.get(["serial", "blacklistedBaudrates"]),
            "longRunningCommands": s.get(["serial", "longRunningCommands"]),
            "checksumRequiringCommands": s.get(["serial", "checksumRequiringCommands"]),
            "blockedCommands": s.get(["serial", "blockedCommands"]),
            "ignoredCommands": s.get(["serial", "ignoredCommands"]),
            "pausingCommands": s.get(["serial", "pausingCommands"]),
            "sdCancelCommand": s.get(["serial", "sdCancelCommand"]),
            "emergencyCommands": s.get(["serial", "emergencyCommands"]),
            "helloCommand": s.get(["serial", "helloCommand"]),
            "ignoreErrorsFromFirmware": s.getBoolean(
                ["serial", "ignoreErrorsFromFirmware"]
            ),
            "disconnectOnErrors": s.getBoolean(["serial", "disconnectOnErrors"]),
            "triggerOkForM29": s.getBoolean(["serial", "triggerOkForM29"]),
            "logPositionOnPause": s.getBoolean(["serial", "logPositionOnPause"]),
            "logPositionOnCancel": s.getBoolean(["serial", "logPositionOnCancel"]),
            "abortHeatupOnCancel": s.getBoolean(["serial", "abortHeatupOnCancel"]),
            "supportResendsWithoutOk": s.get(["serial", "supportResendsWithoutOk"]),
            "waitForStart": s.getBoolean(["serial", "waitForStartOnConnect"]),
            "alwaysSendChecksum": s.getBoolean(["serial", "alwaysSendChecksum"]),
            "neverSendChecksum": s.getBoolean(["serial", "neverSendChecksum"]),
            "sendChecksumWithUnknownCommands": s.getBoolean(
                ["serial", "sendChecksumWithUnknownCommands"]
            ),
            "unknownCommandsNeedAck": s.getBoolean(["serial", "unknownCommandsNeedAck"]),
            "sdRelativePath": s.getBoolean(["serial", "sdRelativePath"]),
            "sdAlwaysAvailable": s.getBoolean(["serial", "sdAlwaysAvailable"]),
            "sdLowerCase": s.getBoolean(["serial", "sdLowerCase"]),
            "swallowOkAfterResend": s.getBoolean(["serial", "swallowOkAfterResend"]),
            "repetierTargetTemp": s.getBoolean(["serial", "repetierTargetTemp"]),
            "externalHeatupDetection": s.getBoolean(
                ["serial", "externalHeatupDetection"]
            ),
            "ignoreIdenticalResends": s.getBoolean(["serial", "ignoreIdenticalResends"]),
            "firmwareDetection": s.getBoolean(["serial", "firmwareDetection"]),
            "blockWhileDwelling": s.getBoolean(["serial", "blockWhileDwelling"]),
            "useParityWorkaround": s.get(["serial", "useParityWorkaround"]),
            "sanityCheckTools": s.getBoolean(["serial", "sanityCheckTools"]),
            "notifySuppressedCommands": s.get(["serial", "notifySuppressedCommands"]),
            "sendM112OnError": s.getBoolean(["serial", "sendM112OnError"]),
            "disableSdPrintingDetection": s.getBoolean(
                ["serial", "disableSdPrintingDetection"]
            ),
            "ackMax": s.getInt(["serial", "ackMax"]),
            "maxTimeoutsIdle": s.getInt(["serial", "maxCommunicationTimeouts", "idle"]),
            "maxTimeoutsPrinting": s.getInt(
                ["serial", "maxCommunicationTimeouts", "printing"]
            ),
            "maxTimeoutsLong": s.getInt(["serial", "maxCommunicationTimeouts", "long"]),
            "capAutoreportTemp": s.getBoolean(
                ["serial", "capabilities", "autoreport_temp"]
            ),
            "capAutoreportSdStatus": s.getBoolean(
                ["serial", "capabilities", "autoreport_sdstatus"]
            ),
            "capAutoreportPos": s.getBoolean(
                ["serial", "capabilities", "autoreport_pos"]
            ),
            "capBusyProtocol": s.getBoolean(["serial", "capabilities", "busy_protocol"]),
            "capEmergencyParser": s.getBoolean(
                ["serial", "capabilities", "emergency_parser"]
            ),
            "capExtendedM20": s.getBoolean(["serial", "capabilities", "extended_m20"]),
            "resendRatioThreshold": s.getInt(["serial", "resendRatioThreshold"]),
            "resendRatioStart": s.getInt(["serial", "resendRatioStart"]),
            "ignoreEmptyPorts": s.getBoolean(["serial", "ignoreEmptyPorts"]),
            "encoding": s.get(["serial", "encoding"]),
            "enableShutdownActionCommand": s.get(
                ["serial", "enableShutdownActionCommand"]
            ),
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
            "events": s.get(["system", "events"]),
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
    if "application/json" not in request.headers["Content-Type"]:
        abort(400, description="Expected content-type JSON")

    data = request.get_json()
    if data is None or not isinstance(data, dict):
        abort(400, description="Malformed JSON body in request")

    response = _saveSettings(data)
    if response:
        return response
    return getSettings()


@api.route("/settings/apikey", methods=["POST"])
@no_firstrun_access
@Permissions.SETTINGS.require(403)
def generateApiKey():
    apikey = settings().generateApiKey()
    return jsonify(apikey=apikey)


@api.route("/settings/apikey", methods=["DELETE"])
@no_firstrun_access
@Permissions.SETTINGS.require(403)
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


def _saveSettings(data):
    logger = logging.getLogger(__name__)

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

    if "appearance" in data:
        if "name" in data["appearance"]:
            s.set(["appearance", "name"], data["appearance"]["name"])
        if "color" in data["appearance"]:
            s.set(["appearance", "color"], data["appearance"]["color"])
        if "colorTransparent" in data["appearance"]:
            s.setBoolean(
                ["appearance", "colorTransparent"], data["appearance"]["colorTransparent"]
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

    if "printer" in data:
        if "defaultExtrusionLength" in data["printer"]:
            s.setInt(
                ["printerParameters", "defaultExtrusionLength"],
                data["printer"]["defaultExtrusionLength"],
            )

    if "webcam" in data:
        if "webcamEnabled" in data["webcam"]:
            s.setBoolean(["webcam", "webcamEnabled"], data["webcam"]["webcamEnabled"])
        if "timelapseEnabled" in data["webcam"]:
            s.setBoolean(
                ["webcam", "timelapseEnabled"], data["webcam"]["timelapseEnabled"]
            )
        if "streamUrl" in data["webcam"]:
            s.set(["webcam", "stream"], data["webcam"]["streamUrl"])
        if "streamRatio" in data["webcam"] and data["webcam"]["streamRatio"] in (
            "16:9",
            "4:3",
        ):
            s.set(["webcam", "streamRatio"], data["webcam"]["streamRatio"])
        if "streamTimeout" in data["webcam"]:
            s.setInt(["webcam", "streamTimeout"], data["webcam"]["streamTimeout"])
        if "streamWebrtcIceServers" in data["webcam"] and isinstance(
            data["webcam"]["streamWebrtcIceServers"], (list, tuple)
        ):
            s.set(
                ["webcam", "streamWebrtcIceServers"],
                data["webcam"]["streamWebrtcIceServers"],
            )
        if "snapshotUrl" in data["webcam"]:
            s.set(["webcam", "snapshot"], data["webcam"]["snapshotUrl"])
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
                map(lambda x: "{" + x + "}" in commandline, ("ffmpeg", "input", "output"))
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
        if "flipH" in data["webcam"]:
            s.setBoolean(["webcam", "flipH"], data["webcam"]["flipH"])
        if "flipV" in data["webcam"]:
            s.setBoolean(["webcam", "flipV"], data["webcam"]["flipV"])
        if "rotate90" in data["webcam"]:
            s.setBoolean(["webcam", "rotate90"], data["webcam"]["rotate90"])
        if "cacheBuster" in data["webcam"]:
            s.setBoolean(["webcam", "cacheBuster"], data["webcam"]["cacheBuster"])

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

    if "gcodeAnalysis" in data:
        if "runAt" in data["gcodeAnalysis"]:
            s.set(["gcodeAnalysis", "runAt"], data["gcodeAnalysis"]["runAt"])
        if "bedZ" in data["gcodeAnalysis"]:
            s.setFloat(["gcodeAnalysis", "bedZ"], data["gcodeAnalysis"]["bedZ"])

    if "serial" in data:
        if "autoconnect" in data["serial"]:
            s.setBoolean(["serial", "autoconnect"], data["serial"]["autoconnect"])
        if "port" in data["serial"]:
            s.set(["serial", "port"], data["serial"]["port"])
        if "baudrate" in data["serial"]:
            s.setInt(["serial", "baudrate"], data["serial"]["baudrate"])
        if "exclusive" in data["serial"]:
            s.setBoolean(["serial", "exclusive"], data["serial"]["exclusive"])
        if "lowLatency" in data["serial"]:
            s.setBoolean(["serial", "lowLatency"], data["serial"]["lowLatency"])
        if "timeoutConnection" in data["serial"]:
            s.setFloat(
                ["serial", "timeout", "connection"],
                data["serial"]["timeoutConnection"],
                min=1.0,
            )
        if "timeoutDetectionFirst" in data["serial"]:
            s.setFloat(
                ["serial", "timeout", "detectionFirst"],
                data["serial"]["timeoutDetectionFirst"],
                min=1.0,
            )
        if "timeoutDetectionConsecutive" in data["serial"]:
            s.setFloat(
                ["serial", "timeout", "detectionConsecutive"],
                data["serial"]["timeoutDetectionConsecutive"],
                min=1.0,
            )
        if "timeoutCommunication" in data["serial"]:
            s.setFloat(
                ["serial", "timeout", "communication"],
                data["serial"]["timeoutCommunication"],
                min=1.0,
            )
        if "timeoutCommunicationBusy" in data["serial"]:
            s.setFloat(
                ["serial", "timeout", "communicationBusy"],
                data["serial"]["timeoutCommunicationBusy"],
                min=1.0,
            )
        if "timeoutTemperature" in data["serial"]:
            s.setFloat(
                ["serial", "timeout", "temperature"],
                data["serial"]["timeoutTemperature"],
                min=1.0,
            )
        if "timeoutTemperatureTargetSet" in data["serial"]:
            s.setFloat(
                ["serial", "timeout", "temperatureTargetSet"],
                data["serial"]["timeoutTemperatureTargetSet"],
                min=1.0,
            )
        if "timeoutTemperatureAutoreport" in data["serial"]:
            s.setFloat(
                ["serial", "timeout", "temperatureAutoreport"],
                data["serial"]["timeoutTemperatureAutoreport"],
                min=0.0,
            )
        if "timeoutSdStatus" in data["serial"]:
            s.setFloat(
                ["serial", "timeout", "sdStatus"],
                data["serial"]["timeoutSdStatus"],
                min=1.0,
            )
        if "timeoutSdStatusAutoreport" in data["serial"]:
            s.setFloat(
                ["serial", "timeout", "sdStatusAutoreport"],
                data["serial"]["timeoutSdStatusAutoreport"],
                min=0.0,
            )
        if "timeoutPosAutoreport" in data["serial"]:
            s.setFloat(
                ["serial", "timeout", "posAutoreport"],
                data["serial"]["timeoutPosAutoreport"],
                min=0.0,
            )
        if "timeoutBaudrateDetectionPause" in data["serial"]:
            s.setFloat(
                ["serial", "timeout", "baudrateDetectionPause"],
                data["serial"]["timeoutBaudrateDetectionPause"],
                min=0.0,
            )
        if "timeoutPositionLogWait" in data["serial"]:
            s.setFloat(
                ["serial", "timeout", "positionLogWait"],
                data["serial"]["timeoutPositionLogWait"],
                min=1.0,
            )
        if "additionalPorts" in data["serial"] and isinstance(
            data["serial"]["additionalPorts"], (list, tuple)
        ):
            s.set(["serial", "additionalPorts"], data["serial"]["additionalPorts"])
        if "additionalBaudrates" in data["serial"] and isinstance(
            data["serial"]["additionalBaudrates"], (list, tuple)
        ):
            s.set(
                ["serial", "additionalBaudrates"], data["serial"]["additionalBaudrates"]
            )
        if "blacklistedPorts" in data["serial"] and isinstance(
            data["serial"]["blacklistedPorts"], (list, tuple)
        ):
            s.set(["serial", "blacklistedPorts"], data["serial"]["blacklistedPorts"])
        if "blacklistedBaudrates" in data["serial"] and isinstance(
            data["serial"]["blacklistedBaudrates"], (list, tuple)
        ):
            s.set(
                ["serial", "blacklistedBaudrates"], data["serial"]["blacklistedBaudrates"]
            )
        if "longRunningCommands" in data["serial"] and isinstance(
            data["serial"]["longRunningCommands"], (list, tuple)
        ):
            s.set(
                ["serial", "longRunningCommands"], data["serial"]["longRunningCommands"]
            )
        if "checksumRequiringCommands" in data["serial"] and isinstance(
            data["serial"]["checksumRequiringCommands"], (list, tuple)
        ):
            s.set(
                ["serial", "checksumRequiringCommands"],
                data["serial"]["checksumRequiringCommands"],
            )
        if "blockedCommands" in data["serial"] and isinstance(
            data["serial"]["blockedCommands"], (list, tuple)
        ):
            s.set(["serial", "blockedCommands"], data["serial"]["blockedCommands"])
        if "ignoredCommands" in data["serial"] and isinstance(
            data["serial"]["ignoredCommands"], (list, tuple)
        ):
            s.set(["serial", "ignoredCommands"], data["serial"]["ignoredCommands"])
        if "pausingCommands" in data["serial"] and isinstance(
            data["serial"]["pausingCommands"], (list, tuple)
        ):
            s.set(["serial", "pausingCommands"], data["serial"]["pausingCommands"])
        if "sdCancelCommand" in data["serial"]:
            s.set(["serial", "sdCancelCommand"], data["serial"]["sdCancelCommand"])
        if "emergencyCommands" in data["serial"] and isinstance(
            data["serial"]["emergencyCommands"], (list, tuple)
        ):
            s.set(["serial", "emergencyCommands"], data["serial"]["emergencyCommands"])
        if "helloCommand" in data["serial"]:
            s.set(["serial", "helloCommand"], data["serial"]["helloCommand"])
        if "ignoreErrorsFromFirmware" in data["serial"]:
            s.setBoolean(
                ["serial", "ignoreErrorsFromFirmware"],
                data["serial"]["ignoreErrorsFromFirmware"],
            )
        if "disconnectOnErrors" in data["serial"]:
            s.setBoolean(
                ["serial", "disconnectOnErrors"], data["serial"]["disconnectOnErrors"]
            )
        if "triggerOkForM29" in data["serial"]:
            s.setBoolean(["serial", "triggerOkForM29"], data["serial"]["triggerOkForM29"])
        if "supportResendsWithoutOk" in data["serial"]:
            value = data["serial"]["supportResendsWithoutOk"]
            if value in ("always", "detect", "never"):
                s.set(["serial", "supportResendsWithoutOk"], value)
        if "waitForStart" in data["serial"]:
            s.setBoolean(
                ["serial", "waitForStartOnConnect"], data["serial"]["waitForStart"]
            )
        if "alwaysSendChecksum" in data["serial"]:
            s.setBoolean(
                ["serial", "alwaysSendChecksum"], data["serial"]["alwaysSendChecksum"]
            )
        if "neverSendChecksum" in data["serial"]:
            s.setBoolean(
                ["serial", "neverSendChecksum"], data["serial"]["neverSendChecksum"]
            )
        if "sdRelativePath" in data["serial"]:
            s.setBoolean(["serial", "sdRelativePath"], data["serial"]["sdRelativePath"])
        if "sdAlwaysAvailable" in data["serial"]:
            s.setBoolean(
                ["serial", "sdAlwaysAvailable"], data["serial"]["sdAlwaysAvailable"]
            )
        if "sdLowerCase" in data["serial"]:
            s.setBoolean(["serial", "sdLowerCase"], data["serial"]["sdLowerCase"])
        if "swallowOkAfterResend" in data["serial"]:
            s.setBoolean(
                ["serial", "swallowOkAfterResend"], data["serial"]["swallowOkAfterResend"]
            )
        if "repetierTargetTemp" in data["serial"]:
            s.setBoolean(
                ["serial", "repetierTargetTemp"], data["serial"]["repetierTargetTemp"]
            )
        if "externalHeatupDetection" in data["serial"]:
            s.setBoolean(
                ["serial", "externalHeatupDetection"],
                data["serial"]["externalHeatupDetection"],
            )
        if "ignoreIdenticalResends" in data["serial"]:
            s.setBoolean(
                ["serial", "ignoreIdenticalResends"],
                data["serial"]["ignoreIdenticalResends"],
            )
        if "firmwareDetection" in data["serial"]:
            s.setBoolean(
                ["serial", "firmwareDetection"], data["serial"]["firmwareDetection"]
            )
        if "blockWhileDwelling" in data["serial"]:
            s.setBoolean(
                ["serial", "blockWhileDwelling"], data["serial"]["blockWhileDwelling"]
            )
        if "useParityWorkaround" in data["serial"]:
            value = data["serial"]["useParityWorkaround"]
            if value in ("always", "detect", "never"):
                s.set(["serial", "useParityWorkaround"], value)
        if "sanityCheckTools" in data["serial"]:
            s.setBoolean(
                ["serial", "sanityCheckTools"], data["serial"]["sanityCheckTools"]
            )
        if "notifySuppressedCommands" in data["serial"]:
            value = data["serial"]["notifySuppressedCommands"]
            if value in ("info", "warn", "never"):
                s.set(["serial", "notifySuppressedCommands"], value)
        if "sendM112OnError" in data["serial"]:
            s.setBoolean(["serial", "sendM112OnError"], data["serial"]["sendM112OnError"])
        if "disableSdPrintingDetection" in data["serial"]:
            s.setBoolean(
                ["serial", "disableSdPrintingDetection"],
                data["serial"]["disableSdPrintingDetection"],
            )
        if "ackMax" in data["serial"]:
            s.setInt(["serial", "ackMax"], data["serial"]["ackMax"])
        if "logPositionOnPause" in data["serial"]:
            s.setBoolean(
                ["serial", "logPositionOnPause"], data["serial"]["logPositionOnPause"]
            )
        if "logPositionOnCancel" in data["serial"]:
            s.setBoolean(
                ["serial", "logPositionOnCancel"], data["serial"]["logPositionOnCancel"]
            )
        if "abortHeatupOnCancel" in data["serial"]:
            s.setBoolean(
                ["serial", "abortHeatupOnCancel"], data["serial"]["abortHeatupOnCancel"]
            )
        if "maxTimeoutsIdle" in data["serial"]:
            s.setInt(
                ["serial", "maxCommunicationTimeouts", "idle"],
                data["serial"]["maxTimeoutsIdle"],
            )
        if "maxTimeoutsPrinting" in data["serial"]:
            s.setInt(
                ["serial", "maxCommunicationTimeouts", "printing"],
                data["serial"]["maxTimeoutsPrinting"],
            )
        if "maxTimeoutsLong" in data["serial"]:
            s.setInt(
                ["serial", "maxCommunicationTimeouts", "long"],
                data["serial"]["maxTimeoutsLong"],
            )
        if "capAutoreportTemp" in data["serial"]:
            s.setBoolean(
                ["serial", "capabilities", "autoreport_temp"],
                data["serial"]["capAutoreportTemp"],
            )
        if "capAutoreportSdStatus" in data["serial"]:
            s.setBoolean(
                ["serial", "capabilities", "autoreport_sdstatus"],
                data["serial"]["capAutoreportSdStatus"],
            )
        if "capAutoreportPos" in data["serial"]:
            s.setBoolean(
                ["serial", "capabilities", "autoreport_pos"],
                data["serial"]["capAutoreportPos"],
            )
        if "capBusyProtocol" in data["serial"]:
            s.setBoolean(
                ["serial", "capabilities", "busy_protocol"],
                data["serial"]["capBusyProtocol"],
            )
        if "capEmergencyParser" in data["serial"]:
            s.setBoolean(
                ["serial", "capabilities", "emergency_parser"],
                data["serial"]["capEmergencyParser"],
            )
        if "capExtendedM20" in data["serial"]:
            s.setBoolean(
                ["serial", "capabilities", "extended_m20"],
                data["serial"]["capExtendedM20"],
            ),
        if "resendRatioThreshold" in data["serial"]:
            s.setInt(
                ["serial", "resendRatioThreshold"], data["serial"]["resendRatioThreshold"]
            )
        if "resendRatioStart" in data["serial"]:
            s.setInt(["serial", "resendRatioStart"], data["serial"]["resendRatioStart"])
        if "ignoreEmptyPorts" in data["serial"]:
            s.setBoolean(
                ["serial", "ignoreEmptyPorts"], data["serial"]["ignoreEmptyPorts"]
            )

        if "encoding" in data["serial"]:
            s.set(["serial", "encoding"], data["serial"]["encoding"])

        if "enableShutdownActionCommand" in data["serial"]:
            s.setBoolean(
                ["serial", "enableShutdownActionCommand"],
                data["serial"]["enableShutdownActionCommand"],
            )

        oldLog = s.getBoolean(["serial", "log"])
        if "log" in data["serial"]:
            s.setBoolean(["serial", "log"], data["serial"]["log"])
        if oldLog and not s.getBoolean(["serial", "log"]):
            # disable debug logging to serial.log
            logging.getLogger("SERIAL").debug("Disabling serial logging")
            logging.getLogger("SERIAL").setLevel(logging.CRITICAL)
        elif not oldLog and s.getBoolean(["serial", "log"]):
            # enable debug logging to serial.log
            logging.getLogger("SERIAL").setLevel(logging.DEBUG)
            logging.getLogger("SERIAL").debug("Enabling serial logging")

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
        if "events" in data["system"]:
            s.set(["system", "events"], data["system"]["events"])

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
