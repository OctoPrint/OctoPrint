# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging

from flask import request, jsonify, make_response
from werkzeug.exceptions import BadRequest

from octoprint.events import eventManager, Events
from octoprint.settings import settings
from octoprint.printer import get_connection_options

from octoprint.server import admin_permission
from octoprint.server.api import api
from octoprint.server.util.flask import restricted_access

import octoprint.plugin
import octoprint.util

#~~ settings


@api.route("/settings", methods=["GET"])
def getSettings():
	logger = logging.getLogger(__name__)

	s = settings()

	connectionOptions = get_connection_options()

	data = {
		"api": {
			"enabled": s.getBoolean(["api", "enabled"]),
			"key": s.get(["api", "key"]) if admin_permission.can() else "n/a",
			"allowCrossOrigin": s.get(["api", "allowCrossOrigin"])
		},
		"appearance": {
			"name": s.get(["appearance", "name"]),
			"color": s.get(["appearance", "color"]),
			"colorTransparent": s.getBoolean(["appearance", "colorTransparent"]),
			"defaultLanguage": s.get(["appearance", "defaultLanguage"])
		},
		"printer": {
			"defaultExtrusionLength": s.getInt(["printerParameters", "defaultExtrusionLength"])
		},
		"webcam": {
			"streamUrl": s.get(["webcam", "stream"]),
			"snapshotUrl": s.get(["webcam", "snapshot"]),
			"ffmpegPath": s.get(["webcam", "ffmpeg"]),
			"bitrate": s.get(["webcam", "bitrate"]),
			"ffmpegThreads": s.get(["webcam", "ffmpegThreads"]),
			"watermark": s.getBoolean(["webcam", "watermark"]),
			"flipH": s.getBoolean(["webcam", "flipH"]),
			"flipV": s.getBoolean(["webcam", "flipV"]),
			"rotate90": s.getBoolean(["webcam", "rotate90"])
		},
		"feature": {
			"gcodeViewer": s.getBoolean(["gcodeViewer", "enabled"]),
			"temperatureGraph": s.getBoolean(["feature", "temperatureGraph"]),
			"waitForStart": s.getBoolean(["feature", "waitForStartOnConnect"]),
			"alwaysSendChecksum": s.getBoolean(["feature", "alwaysSendChecksum"]),
			"sdSupport": s.getBoolean(["feature", "sdSupport"]),
			"sdAlwaysAvailable": s.getBoolean(["feature", "sdAlwaysAvailable"]),
			"swallowOkAfterResend": s.getBoolean(["feature", "swallowOkAfterResend"]),
			"repetierTargetTemp": s.getBoolean(["feature", "repetierTargetTemp"]),
			"externalHeatupDetection": s.getBoolean(["feature", "externalHeatupDetection"]),
			"keyboardControl": s.getBoolean(["feature", "keyboardControl"]),
			"pollWatched": s.getBoolean(["feature", "pollWatched"]),
			"ignoreIdenticalResends": s.getBoolean(["feature", "ignoreIdenticalResends"])
		},
		"serial": {
			"port": connectionOptions["portPreference"],
			"baudrate": connectionOptions["baudratePreference"],
			"portOptions": connectionOptions["ports"],
			"baudrateOptions": connectionOptions["baudrates"],
			"autoconnect": s.getBoolean(["serial", "autoconnect"]),
			"timeoutConnection": s.getFloat(["serial", "timeout", "connection"]),
			"timeoutDetection": s.getFloat(["serial", "timeout", "detection"]),
			"timeoutCommunication": s.getFloat(["serial", "timeout", "communication"]),
			"timeoutTemperature": s.getFloat(["serial", "timeout", "temperature"]),
			"timeoutSdStatus": s.getFloat(["serial", "timeout", "sdStatus"]),
			"log": s.getBoolean(["serial", "log"]),
			"additionalPorts": s.get(["serial", "additionalPorts"]),
			"longRunningCommands": s.get(["serial", "longRunningCommands"]),
			"checksumRequiringCommands": s.get(["serial", "checksumRequiringCommands"]),
			"helloCommand": s.get(["serial", "helloCommand"]),
			"ignoreErrorsFromFirmware": s.getBoolean(["serial", "ignoreErrorsFromFirmware"]),
			"disconnectOnErrors": s.getBoolean(["serial", "disconnectOnErrors"]),
			"triggerOkForM29": s.getBoolean(["serial", "triggerOkForM29"]),
			"supportResendsWithoutOk": s.getBoolean(["serial", "supportResendsWithoutOk"])
		},
		"folder": {
			"uploads": s.getBaseFolder("uploads"),
			"timelapse": s.getBaseFolder("timelapse"),
			"timelapseTmp": s.getBaseFolder("timelapse_tmp"),
			"logs": s.getBaseFolder("logs"),
			"watched": s.getBaseFolder("watched")
		},
		"temperature": {
			"profiles": s.get(["temperature", "profiles"]),
			"cutoff": s.getInt(["temperature", "cutoff"])
		},
		"system": {
			"actions": s.get(["system", "actions"]),
			"events": s.get(["system", "events"])
		},
		"terminalFilters": s.get(["terminalFilters"]),
		"scripts": {
			"gcode": {
				"afterPrinterConnected": None,
				"beforePrintStarted": None,
				"afterPrintCancelled": None,
				"afterPrintDone": None,
				"beforePrintPaused": None,
				"afterPrintResumed": None,
				"snippets": dict()
			}
		},
		"server": {
			"commands": {
				"systemShutdownCommand": s.get(["server", "commands", "systemShutdownCommand"]),
				"systemRestartCommand": s.get(["server", "commands", "systemRestartCommand"]),
				"serverRestartCommand": s.get(["server", "commands", "serverRestartCommand"])
			},
			"diskspace": {
				"warning": s.getInt(["server", "diskspace", "warning"]),
				"critical": s.getInt(["server", "diskspace", "critical"])
			}
		}
	}

	gcode_scripts = s.listScripts("gcode")
	if gcode_scripts:
		data["scripts"] = dict(gcode=dict())
		for name in gcode_scripts:
			data["scripts"]["gcode"][name] = s.loadScript("gcode", name, source=True)

	def process_plugin_result(name, result):
		if result:
			try:
				jsonify(test=result)
			except:
				logger.exception("Error while jsonifying settings from plugin {}, please contact the plugin author about this".format(name))

			if not "plugins" in data:
				data["plugins"] = dict()
			if "__enabled" in result:
				del result["__enabled"]
			data["plugins"][name] = result

	for plugin in octoprint.plugin.plugin_manager().get_implementations(octoprint.plugin.SettingsPlugin):
		try:
			result = plugin.on_settings_load()
			process_plugin_result(plugin._identifier, result)
		except TypeError:
			logger.warn("Could not load settings for plugin {name} ({version}) since it called super(...)".format(name=plugin._plugin_name, version=plugin._plugin_version))
			logger.warn("in a way which has issues due to OctoPrint's dynamic reloading after plugin operations.")
			logger.warn("Please contact the plugin's author and ask to update the plugin to use a direct call like")
			logger.warn("octoprint.plugin.SettingsPlugin.on_settings_load(self) instead.")
		except:
			logger.exception("Could not load settings for plugin {name} ({version})".format(version=plugin._plugin_version, name=plugin._plugin_name))

	return jsonify(data)


@api.route("/settings", methods=["POST"])
@restricted_access
@admin_permission.require(403)
def setSettings():
	logger = logging.getLogger(__name__)

	if not "application/json" in request.headers["Content-Type"]:
		return make_response("Expected content-type JSON", 400)

	try:
		data = request.json
	except BadRequest:
		return make_response("Malformed JSON body in request", 400)
	s = settings()

	if "api" in data.keys():
		if "enabled" in data["api"].keys(): s.setBoolean(["api", "enabled"], data["api"]["enabled"])
		if "key" in data["api"].keys(): s.set(["api", "key"], data["api"]["key"], True)
		if "allowCrossOrigin" in data["api"].keys(): s.setBoolean(["api", "allowCrossOrigin"], data["api"]["allowCrossOrigin"])

	if "appearance" in data.keys():
		if "name" in data["appearance"].keys(): s.set(["appearance", "name"], data["appearance"]["name"])
		if "color" in data["appearance"].keys(): s.set(["appearance", "color"], data["appearance"]["color"])
		if "colorTransparent" in data["appearance"].keys(): s.setBoolean(["appearance", "colorTransparent"], data["appearance"]["colorTransparent"])
		if "defaultLanguage" in data["appearance"]: s.set(["appearance", "defaultLanguage"], data["appearance"]["defaultLanguage"])

	if "printer" in data.keys():
		if "defaultExtrusionLength" in data["printer"]: s.setInt(["printerParameters", "defaultExtrusionLength"], data["printer"]["defaultExtrusionLength"])

	if "webcam" in data.keys():
		if "streamUrl" in data["webcam"].keys(): s.set(["webcam", "stream"], data["webcam"]["streamUrl"])
		if "snapshotUrl" in data["webcam"].keys(): s.set(["webcam", "snapshot"], data["webcam"]["snapshotUrl"])
		if "ffmpegPath" in data["webcam"].keys(): s.set(["webcam", "ffmpeg"], data["webcam"]["ffmpegPath"])
		if "bitrate" in data["webcam"].keys(): s.set(["webcam", "bitrate"], data["webcam"]["bitrate"])
		if "ffmpegThreads" in data["webcam"].keys(): s.setInt(["webcam", "ffmpegThreads"], data["webcam"]["ffmpegThreads"])
		if "watermark" in data["webcam"].keys(): s.setBoolean(["webcam", "watermark"], data["webcam"]["watermark"])
		if "flipH" in data["webcam"].keys(): s.setBoolean(["webcam", "flipH"], data["webcam"]["flipH"])
		if "flipV" in data["webcam"].keys(): s.setBoolean(["webcam", "flipV"], data["webcam"]["flipV"])
		if "rotate90" in data["webcam"].keys(): s.setBoolean(["webcam", "rotate90"], data["webcam"]["rotate90"])

	if "feature" in data.keys():
		if "gcodeViewer" in data["feature"].keys(): s.setBoolean(["gcodeViewer", "enabled"], data["feature"]["gcodeViewer"])
		if "temperatureGraph" in data["feature"].keys(): s.setBoolean(["feature", "temperatureGraph"], data["feature"]["temperatureGraph"])
		if "waitForStart" in data["feature"].keys(): s.setBoolean(["feature", "waitForStartOnConnect"], data["feature"]["waitForStart"])
		if "alwaysSendChecksum" in data["feature"].keys(): s.setBoolean(["feature", "alwaysSendChecksum"], data["feature"]["alwaysSendChecksum"])
		if "sdSupport" in data["feature"].keys(): s.setBoolean(["feature", "sdSupport"], data["feature"]["sdSupport"])
		if "sdAlwaysAvailable" in data["feature"].keys(): s.setBoolean(["feature", "sdAlwaysAvailable"], data["feature"]["sdAlwaysAvailable"])
		if "swallowOkAfterResend" in data["feature"].keys(): s.setBoolean(["feature", "swallowOkAfterResend"], data["feature"]["swallowOkAfterResend"])
		if "repetierTargetTemp" in data["feature"].keys(): s.setBoolean(["feature", "repetierTargetTemp"], data["feature"]["repetierTargetTemp"])
		if "externalHeatupDetection" in data["feature"].keys(): s.setBoolean(["feature", "externalHeatupDetection"], data["feature"]["externalHeatupDetection"])
		if "keyboardControl" in data["feature"].keys(): s.setBoolean(["feature", "keyboardControl"], data["feature"]["keyboardControl"])
		if "pollWatched" in data["feature"]: s.setBoolean(["feature", "pollWatched"], data["feature"]["pollWatched"])
		if "ignoreIdenticalResends" in data["feature"]: s.setBoolean(["feature", "ignoreIdenticalResends"], data["feature"]["ignoreIdenticalResends"])

	if "serial" in data.keys():
		if "autoconnect" in data["serial"].keys(): s.setBoolean(["serial", "autoconnect"], data["serial"]["autoconnect"])
		if "port" in data["serial"].keys(): s.set(["serial", "port"], data["serial"]["port"])
		if "baudrate" in data["serial"].keys(): s.setInt(["serial", "baudrate"], data["serial"]["baudrate"])
		if "timeoutConnection" in data["serial"].keys(): s.setFloat(["serial", "timeout", "connection"], data["serial"]["timeoutConnection"])
		if "timeoutDetection" in data["serial"].keys(): s.setFloat(["serial", "timeout", "detection"], data["serial"]["timeoutDetection"])
		if "timeoutCommunication" in data["serial"].keys(): s.setFloat(["serial", "timeout", "communication"], data["serial"]["timeoutCommunication"])
		if "timeoutTemperature" in data["serial"].keys(): s.setFloat(["serial", "timeout", "temperature"], data["serial"]["timeoutTemperature"])
		if "timeoutSdStatus" in data["serial"].keys(): s.setFloat(["serial", "timeout", "sdStatus"], data["serial"]["timeoutSdStatus"])
		if "additionalPorts" in data["serial"] and isinstance(data["serial"]["additionalPorts"], (list, tuple)): s.set(["serial", "additionalPorts"], data["serial"]["additionalPorts"])
		if "longRunningCommands" in data["serial"] and isinstance(data["serial"]["longRunningCommands"], (list, tuple)): s.set(["serial", "longRunningCommands"], data["serial"]["longRunningCommands"])
		if "checksumRequiringCommands" in data["serial"] and isinstance(data["serial"]["checksumRequiringCommands"], (list, tuple)): s.set(["serial", "checksumRequiringCommands"], data["serial"]["checksumRequiringCommands"])
		if "helloCommand" in data["serial"]: s.set(["serial", "helloCommand"], data["serial"]["helloCommand"])
		if "ignoreErrorsFromFirmware" in data["serial"]: s.setBoolean(["serial", "ignoreErrorsFromFirmware"], data["serial"]["ignoreErrorsFromFirmware"])
		if "disconnectOnErrors" in data["serial"]: s.setBoolean(["serial", "disconnectOnErrors"], data["serial"]["disconnectOnErrors"])
		if "triggerOkForM29" in data["serial"]: s.setBoolean(["serial", "triggerOkForM29"], data["serial"]["triggerOkForM29"])
		if "supportResendsWithoutOk" in data["serial"]: s.setBoolean(["serial", "supportResendsWithoutOk"], data["serial"]["supportResendsWithoutOk"])

		oldLog = s.getBoolean(["serial", "log"])
		if "log" in data["serial"].keys(): s.setBoolean(["serial", "log"], data["serial"]["log"])
		if oldLog and not s.getBoolean(["serial", "log"]):
			# disable debug logging to serial.log
			logging.getLogger("SERIAL").debug("Disabling serial logging")
			logging.getLogger("SERIAL").setLevel(logging.CRITICAL)
		elif not oldLog and s.getBoolean(["serial", "log"]):
			# enable debug logging to serial.log
			logging.getLogger("SERIAL").setLevel(logging.DEBUG)
			logging.getLogger("SERIAL").debug("Enabling serial logging")

	if "folder" in data.keys():
		if "uploads" in data["folder"].keys(): s.setBaseFolder("uploads", data["folder"]["uploads"])
		if "timelapse" in data["folder"].keys(): s.setBaseFolder("timelapse", data["folder"]["timelapse"])
		if "timelapseTmp" in data["folder"].keys(): s.setBaseFolder("timelapse_tmp", data["folder"]["timelapseTmp"])
		if "logs" in data["folder"].keys(): s.setBaseFolder("logs", data["folder"]["logs"])
		if "watched" in data["folder"].keys(): s.setBaseFolder("watched", data["folder"]["watched"])

	if "temperature" in data.keys():
		if "profiles" in data["temperature"].keys(): s.set(["temperature", "profiles"], data["temperature"]["profiles"])
		if "cutoff" in data["temperature"].keys(): s.setInt(["temperature", "cutoff"], data["temperature"]["cutoff"])

	if "terminalFilters" in data.keys():
		s.set(["terminalFilters"], data["terminalFilters"])

	if "system" in data.keys():
		if "actions" in data["system"].keys(): s.set(["system", "actions"], data["system"]["actions"])
		if "events" in data["system"].keys(): s.set(["system", "events"], data["system"]["events"])

	if "scripts" in data:
		if "gcode" in data["scripts"] and isinstance(data["scripts"]["gcode"], dict):
			for name, script in data["scripts"]["gcode"].items():
				if name == "snippets":
					continue
				s.saveScript("gcode", name, script.replace("\r\n", "\n").replace("\r", "\n"))

	if "server" in data:
		if "commands" in data["server"]:
			if "systemShutdownCommand" in data["server"]["commands"].keys(): s.set(["server", "commands", "systemShutdownCommand"], data["server"]["commands"]["systemShutdownCommand"])
			if "systemRestartCommand" in data["server"]["commands"].keys(): s.set(["server", "commands", "systemRestartCommand"], data["server"]["commands"]["systemRestartCommand"])
			if "serverRestartCommand" in data["server"]["commands"].keys(): s.set(["server", "commands", "serverRestartCommand"], data["server"]["commands"]["serverRestartCommand"])
		if "diskspace" in data["server"]:
			if "warning" in data["server"]["diskspace"]: s.setInt(["server", "diskspace", "warning"], data["server"]["diskspace"]["warning"])
			if "critical" in data["server"]["diskspace"]: s.setInt(["server", "diskspace", "critical"], data["server"]["diskspace"]["critical"])

	if "plugins" in data:
		for plugin in octoprint.plugin.plugin_manager().get_implementations(octoprint.plugin.SettingsPlugin):
			plugin_id = plugin._identifier
			if plugin_id in data["plugins"]:
				try:
					plugin.on_settings_save(data["plugins"][plugin_id])
				except TypeError:
					logger.warn("Could not save settings for plugin {name} ({version}) since it called super(...)".format(name=plugin._plugin_name, version=plugin._plugin_version))
					logger.warn("in a way which has issues due to OctoPrint's dynamic reloading after plugin operations.")
					logger.warn("Please contact the plugin's author and ask to update the plugin to use a direct call like")
					logger.warn("octoprint.plugin.SettingsPlugin.on_settings_save(self, data) instead.")
				except:
					logger.exception("Could not save settings for plugin {name} ({version})".format(version=plugin._plugin_version, name=plugin._plugin_name))

	if s.save():
		eventManager().fire(Events.SETTINGS_UPDATED)

	return getSettings()

