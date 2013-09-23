# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

from werkzeug.utils import secure_filename, redirect
from sockjs.tornado import SockJSRouter, SockJSConnection
from flask import Flask, request, render_template, jsonify, send_from_directory, url_for, current_app, session, abort, make_response
from flask.ext.login import LoginManager, login_user, logout_user, login_required, current_user
from flask.ext.principal import Principal, Permission, RoleNeed, Identity, identity_changed, AnonymousIdentity, identity_loaded, UserNeed

from functools import wraps

import os
import threading
import logging, logging.config
import subprocess
import netaddr

from octoprint.printer import Printer, getConnectionOptions
from octoprint.settings import settings, valid_boolean_trues
import octoprint.timelapse
import octoprint.gcodefiles as gcodefiles
import octoprint.util as util
import octoprint.users as users
from octoprint.filemanager.destinations import FileDestinations


import octoprint.events as events

SUCCESS = {}
BASEURL = "/ajax/"
APIBASEURL = "/api/"

app = Flask("octoprint")
# Only instantiated by the Server().run() method
# In order that threads don't start too early when running as a Daemon
printer = None
timelapse = None
debug = False

gcodeManager = None
userManager = None
eventManager = None
loginManager = None

principals = Principal(app)
admin_permission = Permission(RoleNeed("admin"))
user_permission = Permission(RoleNeed("user"))

#~~ Printer state

class PrinterStateConnection(SockJSConnection):
	def __init__(self, printer, gcodeManager, userManager, eventManager, session):
		SockJSConnection.__init__(self, session)

		self._logger = logging.getLogger(__name__)

		self._temperatureBacklog = []
		self._temperatureBacklogMutex = threading.Lock()
		self._logBacklog = []
		self._logBacklogMutex = threading.Lock()
		self._messageBacklog = []
		self._messageBacklogMutex = threading.Lock()

		self._printer = printer
		self._gcodeManager = gcodeManager
		self._userManager = userManager
		self._eventManager = eventManager

	def _getRemoteAddress(self, info):
		forwardedFor = info.headers.get("X-Forwarded-For")
		if forwardedFor is not None:
			return forwardedFor.split(",")[0]
		return info.ip

	def on_open(self, info):
		self._logger.info("New connection from client: %s" % self._getRemoteAddress(info))
		self._printer.registerCallback(self)
		self._gcodeManager.registerCallback(self)
		octoprint.timelapse.registerCallback(self)

		self._eventManager.fire("ClientOpened")
		self._eventManager.subscribe("MovieDone", self._onMovieDone)
		self._eventManager.subscribe("SlicingStarted", self._onSlicingStarted)
		self._eventManager.subscribe("SlicingDone", self._onSlicingDone)
		self._eventManager.subscribe("SlicingFailed", self._onSlicingFailed)

		global timelapse
		octoprint.timelapse.notifyCallbacks(timelapse)

	def on_close(self):
		self._logger.info("Closed client connection")
		self._printer.unregisterCallback(self)
		self._gcodeManager.unregisterCallback(self)
		octoprint.timelapse.unregisterCallback(self)

		self._eventManager.fire("ClientClosed")
		self._eventManager.unsubscribe("MovieDone", self._onMovieDone)
		self._eventManager.unsubscribe("SlicingStarted", self._onSlicingStarted)
		self._eventManager.unsubscribe("SlicingDone", self._onSlicingDone)
		self._eventManager.unsubscribe("SlicingFailed", self._onSlicingFailed)

	def on_message(self, message):
		pass

	def sendCurrentData(self, data):
		# add current temperature, log and message backlogs to sent data
		with self._temperatureBacklogMutex:
			temperatures = self._temperatureBacklog
			self._temperatureBacklog = []

		with self._logBacklogMutex:
			logs = self._logBacklog
			self._logBacklog = []

		with self._messageBacklogMutex:
			messages = self._messageBacklog
			self._messageBacklog = []

		data.update({
			"temperatures": temperatures,
			"logs": logs,
			"messages": messages
		})
		self._emit("current", data)

	def sendHistoryData(self, data):
		self._emit("history", data)

	def sendUpdateTrigger(self, type, payload=None):
		self._emit("updateTrigger", {"type": type, "payload": payload})

	def sendFeedbackCommandOutput(self, name, output):
		self._emit("feedbackCommandOutput", {"name": name, "output": output})

	def sendTimelapseConfig(self, timelapseConfig):
		self._emit("timelapse", timelapseConfig)

	def addLog(self, data):
		with self._logBacklogMutex:
			self._logBacklog.append(data)

	def addMessage(self, data):
		with self._messageBacklogMutex:
			self._messageBacklog.append(data)

	def addTemperature(self, data):
		with self._temperatureBacklogMutex:
			self._temperatureBacklog.append(data)

	def _onMovieDone(self, event, payload):
		self.sendUpdateTrigger("timelapseFiles")

	def _onSlicingStarted(self, event, payload):
		self.sendUpdateTrigger("slicingStarted", payload)

	def _onSlicingDone(self, event, payload):
		self.sendUpdateTrigger("slicingDone", payload)

	def _onSlicingFailed(self, event, payload):
		self.sendUpdateTrigger("slicingFailed", payload)

	def _emit(self, type, payload):
		self.send({type: payload})

def restricted_access(func):
	"""
	If you decorate a view with this, it will ensure that first setup has been
	done for OctoPrint's Access Control plus that any conditions of the
	login_required decorator are met.

	If OctoPrint's Access Control has not been setup yet (indicated by the "firstRun"
	flag from the settings being set to True and the userManager not indicating
	that it's user database has been customized from default), the decorator
	will cause a HTTP 403 status code to be returned by the decorated resource.

	Otherwise the result of calling login_required will be returned.
	"""
	@wraps(func)
	def decorated_view(*args, **kwargs):
		if settings().getBoolean(["server", "firstRun"]) and (userManager is None or not userManager.hasBeenCustomized()):
			return make_response("OctoPrint isn't setup yet", 403)
		return login_required(func)(*args, **kwargs)
	return decorated_view

# Did attempt to make webserver an encapsulated class but ended up with __call__ failures

@app.route("/")
def index():
	branch = None
	commit = None
	try:
		branch, commit = util.getGitInfo()
	except:
		pass

	global debug

	return render_template(
		"index.jinja2",
		ajaxBaseUrl=BASEURL,
		webcamStream=settings().get(["webcam", "stream"]),
		enableTimelapse=(settings().get(["webcam", "snapshot"]) is not None and settings().get(["webcam", "ffmpeg"]) is not None),
		enableGCodeVisualizer=settings().get(["feature", "gCodeVisualizer"]),
		enableTemperatureGraph=settings().get(["feature", "temperatureGraph"]),
		enableSystemMenu=settings().get(["system"]) is not None and settings().get(["system", "actions"]) is not None and len(settings().get(["system", "actions"])) > 0,
		enableAccessControl=userManager is not None,
		enableSdSupport=settings().get(["feature", "sdSupport"]),
		firstRun=settings().getBoolean(["server", "firstRun"]) and (userManager is None or not userManager.hasBeenCustomized()),
		debug=debug,
		gitBranch=branch,
		gitCommit=commit
	)

@app.route("/robots.txt")
def robotsTxt():
	return send_from_directory(app.static_folder, "robots.txt")

#~~ Printer control

@app.route(BASEURL + "control/connection/options", methods=["GET"])
def connectionOptions():
	return jsonify(getConnectionOptions())

@app.route(BASEURL + "control/connection", methods=["POST"])
@restricted_access
def connect():
	if "command" in request.values.keys() and request.values["command"] == "connect":
		port = None
		baudrate = None
		if "port" in request.values.keys():
			port = request.values["port"]
		if "baudrate" in request.values.keys():
			baudrate = request.values["baudrate"]
		if "save" in request.values.keys():
			settings().set(["serial", "port"], port)
			settings().setInt(["serial", "baudrate"], baudrate)
			settings().save()
		if "autoconnect" in request.values.keys():
			settings().setBoolean(["serial", "autoconnect"], True)
			settings().save()
		printer.connect(port=port, baudrate=baudrate)
	elif "command" in request.values.keys() and request.values["command"] == "disconnect":
		printer.disconnect()

	return jsonify(SUCCESS)

@app.route(BASEURL + "control/command", methods=["POST"])
@restricted_access
def printerCommand():
	if "application/json" in request.headers["Content-Type"]:
		data = request.json

		parameters = {}
		if "parameters" in data.keys(): parameters = data["parameters"]

		commands = []
		if "command" in data.keys(): commands = [data["command"]]
		elif "commands" in data.keys(): commands = data["commands"]

		commandsToSend = []
		for command in commands:
			commandToSend = command
			if len(parameters) > 0:
				commandToSend = command % parameters
			commandsToSend.append(commandToSend)

		printer.commands(commandsToSend)

	return jsonify(SUCCESS)

@app.route(BASEURL + "control/job", methods=["POST"])
@restricted_access
def printJobControl():
	if "command" in request.values.keys():
		if request.values["command"] == "start":
			printer.startPrint()
		elif request.values["command"] == "pause":
			printer.togglePausePrint()
		elif request.values["command"] == "cancel":
			printer.cancelPrint()
	return jsonify(SUCCESS)

@app.route(BASEURL + "control/temperature", methods=["POST"])
@restricted_access
def setTargetTemperature():
	if "temp" in request.values.keys():
		# set target temperature
		temp = request.values["temp"]
		printer.command("M104 S" + temp)

	if "bedTemp" in request.values.keys():
		# set target bed temperature
		bedTemp = request.values["bedTemp"]
		printer.command("M140 S" + bedTemp)

	if "tempOffset" in request.values.keys():
		# set target temperature offset
		try:
			tempOffset = float(request.values["tempOffset"])
			if tempOffset >= -50 and tempOffset <= 50:
				printer.setTemperatureOffset(tempOffset, None)
		except:
			pass

	if "bedTempOffset" in request.values.keys():
		# set target bed temperature offset
		try:
			bedTempOffset = float(request.values["bedTempOffset"])
			if bedTempOffset >= -50 and bedTempOffset <= 50:
				printer.setTemperatureOffset(None, bedTempOffset)
		except:
			pass

	return jsonify(SUCCESS)

@app.route(BASEURL + "control/jog", methods=["POST"])
@restricted_access
def jog():
	if not printer.isOperational() or printer.isPrinting():
		# do not jog when a print job is running or we don't have a connection
		return jsonify(SUCCESS)

	(movementSpeedX, movementSpeedY, movementSpeedZ, movementSpeedE) = settings().get(["printerParameters", "movementSpeed", ["x", "y", "z", "e"]])
	if "x" in request.values.keys():
		# jog x
		x = request.values["x"]
		printer.commands(["G91", "G1 X%s F%d" % (x, movementSpeedX), "G90"])
	if "y" in request.values.keys():
		# jog y
		y = request.values["y"]
		printer.commands(["G91", "G1 Y%s F%d" % (y, movementSpeedY), "G90"])
	if "z" in request.values.keys():
		# jog z
		z = request.values["z"]
		printer.commands(["G91", "G1 Z%s F%d" % (z, movementSpeedZ), "G90"])
	if "homeXY" in request.values.keys():
		# home x/y
		printer.command("G28 X0 Y0")
	if "homeZ" in request.values.keys():
		# home z
		printer.command("G28 Z0")
	if "extrude" in request.values.keys():
		# extrude/retract
		length = request.values["extrude"]
		printer.commands(["G91", "G1 E%s F%d" % (length, movementSpeedE), "G90"])

	return jsonify(SUCCESS)

@app.route(BASEURL + "control/custom", methods=["GET"])
def getCustomControls():
	customControls = settings().get(["controls"])
	return jsonify(controls=customControls)

@app.route(BASEURL + "control/sd", methods=["POST"])
@restricted_access
def sdCommand():
	if not settings().getBoolean(["feature", "sdSupport"]) or not printer.isOperational() or printer.isPrinting():
		return jsonify(SUCCESS)

	if "command" in request.values.keys():
		command = request.values["command"]
		if command == "init":
			printer.initSdCard()
		elif command == "refresh":
			printer.refreshSdFiles()
		elif command == "release":
			printer.releaseSdCard()

	return jsonify(SUCCESS)

#~~ GCODE file handling

@app.route(BASEURL + "gcodefiles", methods=["GET"])
def readGcodeFiles():
	files = gcodeManager.getAllFileData()

	sdFileList = printer.getSdFiles()
	if sdFileList is not None:
		for sdFile in sdFileList:
			files.append({
				"name": sdFile,
				"size": "n/a",
				"bytes": 0,
				"date": "n/a",
				"origin": "sd"
			})
	return jsonify(files=files, free=util.getFormattedSize(util.getFreeBytes(settings().getBaseFolder("uploads"))))

@app.route(BASEURL + "gcodefiles/<path:filename>", methods=["GET"])
def readGcodeFile(filename):
	return redirectToTornado(request, "/downloads/gcode/" + filename)

@app.route(BASEURL + "gcodefiles/upload", methods=["POST"])
@restricted_access
def uploadGcodeFile():
	if "gcode_file" in request.files.keys():
		file = request.files["gcode_file"]
		sd = "target" in request.values.keys() and request.values["target"] == "sd";

		currentFilename = None
		currentSd = None
		currentJob = printer.getCurrentJob()
		if currentJob is not None and "filename" in currentJob.keys() and "sd" in currentJob.keys():
			currentFilename = currentJob["filename"]
			currentSd = currentJob["sd"]

		futureFilename = gcodeManager.getFutureFilename(file)
		if futureFilename is None or (not settings().getBoolean(["cura", "enabled"]) and not gcodefiles.isGcodeFileName(futureFilename)):
			return make_response("Can not upload file %s, wrong format?" % file.filename, 400)

		if futureFilename == currentFilename and sd == currentSd and printer.isPrinting() or printer.isPaused():
			# trying to overwrite currently selected file, but it is being printed
			return make_response("Trying to overwrite file that is currently being printed: %s" % currentFilename, 403)

		destination = FileDestinations.SDCARD if sd else FileDestinations.LOCAL

		filename, done = gcodeManager.addFile(file, destination)

		if filename is None:
			return make_response("Could not upload the file %s" % file.filename, 500)

		absFilename = gcodeManager.getAbsolutePath(filename)
		if sd:
			printer.addSdFile(filename, absFilename)

		if currentFilename == filename and currentSd == sd:
			# reload file as it was updated
			if sd:
				printer.selectFile(filename, sd, False)
			else:
				printer.selectFile(absFilename, sd, False)

		global eventManager
		eventManager.fire("Upload", filename)
	return jsonify(files=gcodeManager.getAllFileData(), filename=filename, done=done)


@app.route(BASEURL + "gcodefiles/load", methods=["POST"])
@restricted_access
def loadGcodeFile():
	if "filename" in request.values.keys():
		printAfterLoading = False
		if "print" in request.values.keys() and request.values["print"] in valid_boolean_trues:
			printAfterLoading = True

		sd = False
		if "target" in request.values.keys() and request.values["target"] == "sd":
			filename = request.values["filename"]
			sd = True
		else:
			filename = gcodeManager.getAbsolutePath(request.values["filename"])
		printer.selectFile(filename, sd, printAfterLoading)
	return jsonify(SUCCESS)

@app.route(BASEURL + "gcodefiles/delete", methods=["POST"])
@restricted_access
def deleteGcodeFile():
	if "filename" in request.values.keys():
		filename = request.values["filename"]
		sd = "target" in request.values.keys() and request.values["target"] == "sd"

		currentJob = printer.getCurrentJob()
		currentFilename = None
		currentSd = None
		if currentJob is not None and "filename" in currentJob.keys() and "sd" in currentJob.keys():
			currentFilename = currentJob["filename"]
			currentSd = currentJob["sd"]

		if currentFilename is not None and filename == currentFilename and not (printer.isPrinting() or printer.isPaused()):
			printer.unselectFile()

		if not (currentFilename == filename and currentSd == sd and (printer.isPrinting() or printer.isPaused())):
			if sd:
				printer.deleteSdFile(filename)
			else:
				gcodeManager.removeFile(filename)
	return readGcodeFiles()

@app.route(BASEURL + "gcodefiles/refresh", methods=["POST"])
@restricted_access
def refreshFiles():
	printer.updateSdFiles()
	return jsonify(SUCCESS)

#-- very simple api routines
@app.route(APIBASEURL + "load", methods=["POST"])
def apiLoad():
	logger = logging.getLogger(__name__)

	if not settings().get(["api", "enabled"]):
		abort(401)

	if not "apikey" in request.values.keys():
		abort(401)

	if request.values["apikey"] != settings().get(["api", "key"]):
		abort(403)

	if not "file" in request.files.keys():
		abort(400)

	# Perform an upload
	file = request.files["file"]
	if not gcodefiles.isGcodeFileName(file.filename):
		abort(400)

	filename, done = gcodeManager.addFile(file)
	if filename is None:
		logger.warn("Upload via API failed")
		abort(500)

	# Immediately perform a file select and possibly print too
	printAfterSelect = False
	if "print" in request.values.keys() and request.values["print"] in valid_boolean_trues:
		printAfterSelect = True
	filepath = gcodeManager.getAbsolutePath(filename)
	if filepath is not None:
		printer.selectFile(filepath, False, printAfterSelect)
	return jsonify(SUCCESS)

@app.route(APIBASEURL + "state", methods=["GET"])
def apiPrinterState():
	if not settings().get(["api", "enabled"]):
		abort(401)

	if not "apikey" in request.values.keys():
		abort(401)

	if request.values["apikey"] != settings().get(["api", "key"]):
		abort(403)

	currentData = printer.getCurrentData()
	currentData.update({
		"temperatures": printer.getCurrentTemperatures()
	})
	return jsonify(currentData)

#~~ timelapse handling

@app.route(BASEURL + "timelapse", methods=["GET"])
def getTimelapseData():
	global timelapse

	type = "off"
	additionalConfig = {}
	if timelapse is not None and isinstance(timelapse, octoprint.timelapse.ZTimelapse):
		type = "zchange"
	elif timelapse is not None and isinstance(timelapse, octoprint.timelapse.TimedTimelapse):
		type = "timed"
		additionalConfig = {
			"interval": timelapse.interval()
		}

	files = octoprint.timelapse.getFinishedTimelapses()
	for file in files:
		file["url"] = "/downloads/timelapse/" + file["name"]

	return jsonify({
		"type": type,
		"config": additionalConfig,
		"files": files
	})

@app.route(BASEURL + "timelapse/<filename>", methods=["GET"])
def downloadTimelapse(filename):
	return redirectToTornado(request, "/downloads/timelapse/" + filename)

@app.route(BASEURL + "timelapse/<filename>", methods=["DELETE"])
@restricted_access
def deleteTimelapse(filename):
	if util.isAllowedFile(filename, set(["mpg"])):
		secure = os.path.join(settings().getBaseFolder("timelapse"), secure_filename(filename))
		if os.path.exists(secure):
			os.remove(secure)
	return getTimelapseData()

@app.route(BASEURL + "timelapse", methods=["POST"])
@restricted_access
def setTimelapseConfig():
	if request.values.has_key("type"):
		config = {
			"type": request.values["type"],
			"options": {}
		}

		if request.values.has_key("interval"):
			interval = 10
			try:
				interval = int(request.values["interval"])
			except ValueError:
				pass

			config["options"] = {
				"interval": interval
			}

		if admin_permission.can() and request.values.has_key("save") and request.values["save"] in valid_boolean_trues:
			_configureTimelapse(config, True)
		else:
			_configureTimelapse(config)

	return getTimelapseData()

def _configureTimelapse(config=None, persist=False):
	global timelapse

	if config is None:
		config = settings().get(["webcam", "timelapse"])

	if timelapse is not None:
		timelapse.unload()

	type = config["type"]
	if type is None or "off" == type:
		timelapse = None
	elif "zchange" == type:
		timelapse = octoprint.timelapse.ZTimelapse()
	elif "timed" == type:
		interval = 10
		if "options" in config and "interval" in config["options"]:
			interval = config["options"]["interval"]
		timelapse = octoprint.timelapse.TimedTimelapse(interval)

	octoprint.timelapse.notifyCallbacks(timelapse)

	if persist:
		settings().set(["webcam", "timelapse"], config)
		settings().save()

#~~ settings

@app.route(BASEURL + "settings", methods=["GET"])
def getSettings():
	s = settings()

	[movementSpeedX, movementSpeedY, movementSpeedZ, movementSpeedE] = s.get(["printerParameters", "movementSpeed", ["x", "y", "z", "e"]])

	connectionOptions = getConnectionOptions()

	return jsonify({
		"api": {
			"enabled": s.getBoolean(["api", "enabled"]),
			"key": s.get(["api", "key"])
		},
		"appearance": {
			"name": s.get(["appearance", "name"]),
			"color": s.get(["appearance", "color"])
		},
		"printer": {
			"movementSpeedX": movementSpeedX,
			"movementSpeedY": movementSpeedY,
			"movementSpeedZ": movementSpeedZ,
			"movementSpeedE": movementSpeedE,
		},
		"webcam": {
			"streamUrl": s.get(["webcam", "stream"]),
			"snapshotUrl": s.get(["webcam", "snapshot"]),
			"ffmpegPath": s.get(["webcam", "ffmpeg"]),
			"bitrate": s.get(["webcam", "bitrate"]),
			"watermark": s.getBoolean(["webcam", "watermark"]),
			"flipH": s.getBoolean(["webcam", "flipH"]),
			"flipV": s.getBoolean(["webcam", "flipV"])
		},
		"feature": {
			"gcodeViewer": s.getBoolean(["feature", "gCodeVisualizer"]),
			"temperatureGraph": s.getBoolean(["feature", "temperatureGraph"]),
			"invertZ": s.getBoolean(["feature", "invertZ"]),
			"waitForStart": s.getBoolean(["feature", "waitForStartOnConnect"]),
			"alwaysSendChecksum": s.getBoolean(["feature", "alwaysSendChecksum"]),
			"sdSupport": s.getBoolean(["feature", "sdSupport"]),
			"swallowOkAfterResend": s.getBoolean(["feature", "swallowOkAfterResend"])
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
			"log": s.getBoolean(["serial", "log"])
		},
		"folder": {
			"uploads": s.getBaseFolder("uploads"),
			"timelapse": s.getBaseFolder("timelapse"),
			"timelapseTmp": s.getBaseFolder("timelapse_tmp"),
			"logs": s.getBaseFolder("logs")
		},
		"temperature": {
			"profiles": s.get(["temperature", "profiles"])
		},
		"system": {
			"actions": s.get(["system", "actions"]),
			"events": s.get(["system", "events"])
		},
		"terminalFilters": s.get(["terminalFilters"]),
		"cura": {
			"enabled": s.getBoolean(["cura", "enabled"]),
			"path": s.get(["cura", "path"]),
			"config": s.get(["cura", "config"])
		}
	})

@app.route(BASEURL + "settings", methods=["POST"])
@restricted_access
@admin_permission.require(403)
def setSettings():
	if "application/json" in request.headers["Content-Type"]:
		data = request.json
		s = settings()

		if "api" in data.keys():
			if "enabled" in data["api"].keys(): s.set(["api", "enabled"], data["api"]["enabled"])
			if "key" in data["api"].keys(): s.set(["api", "key"], data["api"]["key"], True)

		if "appearance" in data.keys():
			if "name" in data["appearance"].keys(): s.set(["appearance", "name"], data["appearance"]["name"])
			if "color" in data["appearance"].keys(): s.set(["appearance", "color"], data["appearance"]["color"])

		if "printer" in data.keys():
			if "movementSpeedX" in data["printer"].keys(): s.setInt(["printerParameters", "movementSpeed", "x"], data["printer"]["movementSpeedX"])
			if "movementSpeedY" in data["printer"].keys(): s.setInt(["printerParameters", "movementSpeed", "y"], data["printer"]["movementSpeedY"])
			if "movementSpeedZ" in data["printer"].keys(): s.setInt(["printerParameters", "movementSpeed", "z"], data["printer"]["movementSpeedZ"])
			if "movementSpeedE" in data["printer"].keys(): s.setInt(["printerParameters", "movementSpeed", "e"], data["printer"]["movementSpeedE"])

		if "webcam" in data.keys():
			if "streamUrl" in data["webcam"].keys(): s.set(["webcam", "stream"], data["webcam"]["streamUrl"])
			if "snapshotUrl" in data["webcam"].keys(): s.set(["webcam", "snapshot"], data["webcam"]["snapshotUrl"])
			if "ffmpegPath" in data["webcam"].keys(): s.set(["webcam", "ffmpeg"], data["webcam"]["ffmpegPath"])
			if "bitrate" in data["webcam"].keys(): s.set(["webcam", "bitrate"], data["webcam"]["bitrate"])
			if "watermark" in data["webcam"].keys(): s.setBoolean(["webcam", "watermark"], data["webcam"]["watermark"])
			if "flipH" in data["webcam"].keys(): s.setBoolean(["webcam", "flipH"], data["webcam"]["flipH"])
			if "flipV" in data["webcam"].keys(): s.setBoolean(["webcam", "flipV"], data["webcam"]["flipV"])

		if "feature" in data.keys():
			if "gcodeViewer" in data["feature"].keys(): s.setBoolean(["feature", "gCodeVisualizer"], data["feature"]["gcodeViewer"])
			if "temperatureGraph" in data["feature"].keys(): s.setBoolean(["feature", "temperatureGraph"], data["feature"]["temperatureGraph"])
			if "invertZ" in data["feature"].keys(): s.setBoolean(["feature", "invertZ"], data["feature"]["invertZ"])
			if "waitForStart" in data["feature"].keys(): s.setBoolean(["feature", "waitForStartOnConnect"], data["feature"]["waitForStart"])
			if "alwaysSendChecksum" in data["feature"].keys(): s.setBoolean(["feature", "alwaysSendChecksum"], data["feature"]["alwaysSendChecksum"])
			if "sdSupport" in data["feature"].keys(): s.setBoolean(["feature", "sdSupport"], data["feature"]["sdSupport"])
			if "swallowOkAfterResend" in data["feature"].keys(): s.setBoolean(["feature", "swallowOkAfterResend"], data["feature"]["swallowOkAfterResend"])

		if "serial" in data.keys():
			if "autoconnect" in data["serial"].keys(): s.setBoolean(["serial", "autoconnect"], data["serial"]["autoconnect"])
			if "port" in data["serial"].keys(): s.set(["serial", "port"], data["serial"]["port"])
			if "baudrate" in data["serial"].keys(): s.setInt(["serial", "baudrate"], data["serial"]["baudrate"])
			if "timeoutConnection" in data["serial"].keys(): s.setFloat(["serial", "timeout", "connection"], data["serial"]["timeoutConnection"])
			if "timeoutDetection" in data["serial"].keys(): s.setFloat(["serial", "timeout", "detection"], data["serial"]["timeoutDetection"])
			if "timeoutCommunication" in data["serial"].keys(): s.setFloat(["serial", "timeout", "communication"], data["serial"]["timeoutCommunication"])

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

		if "temperature" in data.keys():
			if "profiles" in data["temperature"].keys(): s.set(["temperature", "profiles"], data["temperature"]["profiles"])

		if "terminalFilters" in data.keys():
			s.set(["terminalFilters"], data["terminalFilters"])

		if "system" in data.keys():
			if "actions" in data["system"].keys(): s.set(["system", "actions"], data["system"]["actions"])
			if "events" in data["system"].keys(): s.set(["system", "events"], data["system"]["events"])

		cura = data.get("cura", None)
		if cura:
			path = cura.get("path")
			if path:
				s.set(["cura", "path"], path)

			config = cura.get("config")
			if config:
				s.set(["cura", "config"], config)

			# Enabled is a boolean so we cannot check that we have a result
			enabled = cura.get("enabled")
			s.setBoolean(["cura", "enabled"], enabled)

		s.save()

	return getSettings()

@app.route(BASEURL + "setup", methods=["POST"])
def firstRunSetup():
	global userManager

	if not settings().getBoolean(["server", "firstRun"]):
		abort(403)

	if "ac" in request.values.keys() and request.values["ac"] in valid_boolean_trues and \
					"user" in request.values.keys() and "pass1" in request.values.keys() and \
					"pass2" in request.values.keys() and request.values["pass1"] == request.values["pass2"]:
		# configure access control
		settings().setBoolean(["accessControl", "enabled"], True)
		userManager.addUser(request.values["user"], request.values["pass1"], True, ["user", "admin"])
		settings().setBoolean(["server", "firstRun"], False)
	elif "ac" in request.values.keys() and not request.values["ac"] in valid_boolean_trues:
		# disable access control
		settings().setBoolean(["accessControl", "enabled"], False)
		settings().setBoolean(["server", "firstRun"], False)

		userManager = None
		loginManager.anonymous_user = users.DummyUser
		principals.identity_loaders.appendleft(users.dummy_identity_loader)

	settings().save()
	return jsonify(SUCCESS)

#~~ user settings

@app.route(BASEURL + "users", methods=["GET"])
@restricted_access
@admin_permission.require(403)
def getUsers():
	if userManager is None:
		return jsonify(SUCCESS)

	return jsonify({"users": userManager.getAllUsers()})

@app.route(BASEURL + "users", methods=["POST"])
@restricted_access
@admin_permission.require(403)
def addUser():
	if userManager is None:
		return jsonify(SUCCESS)

	if "application/json" in request.headers["Content-Type"]:
		data = request.json

		name = data["name"]
		password = data["password"]
		active = data["active"]

		roles = ["user"]
		if "admin" in data.keys() and data["admin"]:
			roles.append("admin")

		try:
			userManager.addUser(name, password, active, roles)
		except users.UserAlreadyExists:
			abort(409)
	return getUsers()

@app.route(BASEURL + "users/<username>", methods=["GET"])
@restricted_access
def getUser(username):
	if userManager is None:
		return jsonify(SUCCESS)

	if current_user is not None and not current_user.is_anonymous() and (current_user.get_name() == username or current_user.is_admin()):
		user = userManager.findUser(username)
		if user is not None:
			return jsonify(user.asDict())
		else:
			abort(404)
	else:
		abort(403)

@app.route(BASEURL + "users/<username>", methods=["PUT"])
@restricted_access
@admin_permission.require(403)
def updateUser(username):
	if userManager is None:
		return jsonify(SUCCESS)

	user = userManager.findUser(username)
	if user is not None:
		if "application/json" in request.headers["Content-Type"]:
			data = request.json

			# change roles
			roles = ["user"]
			if "admin" in data.keys() and data["admin"]:
				roles.append("admin")
			userManager.changeUserRoles(username, roles)

			# change activation
			if "active" in data.keys():
				userManager.changeUserActivation(username, data["active"])
		return getUsers()
	else:
		abort(404)

@app.route(BASEURL + "users/<username>", methods=["DELETE"])
@restricted_access
@admin_permission.require(http_exception=403)
def removeUser(username):
	if userManager is None:
		return jsonify(SUCCESS)

	try:
		userManager.removeUser(username)
		return getUsers()
	except users.UnknownUser:
		abort(404)

@app.route(BASEURL + "users/<username>/password", methods=["PUT"])
@restricted_access
def changePasswordForUser(username):
	if userManager is None:
		return jsonify(SUCCESS)

	if current_user is not None and not current_user.is_anonymous() and (current_user.get_name() == username or current_user.is_admin()):
		if "application/json" in request.headers["Content-Type"]:
			data = request.json
			if "password" in data.keys() and data["password"]:
				try:
					userManager.changeUserPassword(username, data["password"])
				except users.UnknownUser:
					return app.make_response(("Unknown user: %s" % username, 404, []))
		return jsonify(SUCCESS)
	else:
		return app.make_response(("Forbidden", 403, []))

#~~ system control

@app.route(BASEURL + "system", methods=["POST"])
@restricted_access
@admin_permission.require(403)
def performSystemAction():
	logger = logging.getLogger(__name__)
	if request.values.has_key("action"):
		action = request.values["action"]
		availableActions = settings().get(["system", "actions"])
		for availableAction in availableActions:
			if availableAction["action"] == action:
				logger.info("Performing command: %s" % availableAction["command"])
				try:
					subprocess.check_output(availableAction["command"], shell=True)
				except subprocess.CalledProcessError, e:
					logger.warn("Command failed with return code %i: %s" % (e.returncode, e.message))
					return app.make_response(("Command failed with return code %i: %s" % (e.returncode, e.message), 500, []))
				except Exception, ex:
					logger.exception("Command failed")
					return app.make_response(("Command failed: %r" % ex, 500, []))
	return jsonify(SUCCESS)

#~~ Login/user handling

@app.route(BASEURL + "login", methods=["POST"])
def login():
	if userManager is not None and "user" in request.values.keys() and "pass" in request.values.keys():
		username = request.values["user"]
		password = request.values["pass"]

		if "remember" in request.values.keys() and request.values["remember"] == "true":
			remember = True
		else:
			remember = False

		user = userManager.findUser(username)
		if user is not None:
			if user.check_password(users.UserManager.createPasswordHash(password)):
				login_user(user, remember=remember)
				identity_changed.send(current_app._get_current_object(), identity=Identity(user.get_id()))
				return jsonify(user.asDict())
		return app.make_response(("User unknown or password incorrect", 401, []))
	elif "passive" in request.values.keys():
		user = current_user
		if user is not None and not user.is_anonymous():
			identity_changed.send(current_app._get_current_object(), identity=Identity(user.get_id()))
			return jsonify(user.asDict())
		elif settings().getBoolean(["accessControl", "autologinLocal"]) \
				and settings().get(["accessControl", "autologinAs"]) is not None \
				and settings().get(["accessControl", "localNetworks"]) is not None:

			autologinAs = settings().get(["accessControl", "autologinAs"])
			localNetworks = netaddr.IPSet([])
			for ip in settings().get(["accessControl", "localNetworks"]):
				localNetworks.add(ip)

			try:
				remoteAddr = util.getRemoteAddress(request)
				if netaddr.IPAddress(remoteAddr) in localNetworks:
					user = userManager.findUser(autologinAs)
					if user is not None:
						login_user(user)
						identity_changed.send(current_app._get_current_object(), identity=Identity(user.get_id()))
						return jsonify(user.asDict())
			except:
				logger = logging.getLogger(__name__)
				logger.exception("Could not autologin user %s for networks %r" % (autologinAs, localNetworks))
	return jsonify(SUCCESS)

@app.route(BASEURL + "logout", methods=["POST"])
@restricted_access
def logout():
	# Remove session keys set by Flask-Principal
	for key in ('identity.id', 'identity.auth_type'):
		del session[key]
	identity_changed.send(current_app._get_current_object(), identity=AnonymousIdentity())

	logout_user()

	return jsonify(SUCCESS)

@identity_loaded.connect_via(app)
def on_identity_loaded(sender, identity):
	user = load_user(identity.id)
	if user is None:
		return

	identity.provides.add(UserNeed(user.get_name()))
	if user.is_user():
		identity.provides.add(RoleNeed("user"))
	if user.is_admin():
		identity.provides.add(RoleNeed("admin"))

def load_user(id):
	if userManager is not None:
		return userManager.findUser(id)
	return users.DummyUser()

def redirectToTornado(request, target):
	requestUrl = request.url
	appBaseUrl = requestUrl[:requestUrl.find(BASEURL)]

	redirectUrl = appBaseUrl + target
	if "?" in requestUrl:
		fragment = requestUrl[requestUrl.rfind("?"):]
		redirectUrl += fragment
	return redirect(redirectUrl)

#~~ customized large response handler

from tornado.web import StaticFileHandler, HTTPError
import datetime, stat, mimetypes, email, time

class LargeResponseHandler(StaticFileHandler):

	CHUNK_SIZE = 16 * 1024

	def initialize(self, path, default_filename=None, as_attachment=False):
		StaticFileHandler.initialize(self, path, default_filename)
		self._as_attachment = as_attachment

	def get(self, path, include_body=True):
		path = self.parse_url_path(path)
		abspath = os.path.abspath(os.path.join(self.root, path))
		# os.path.abspath strips a trailing /
		# it needs to be temporarily added back for requests to root/
		if not (abspath + os.path.sep).startswith(self.root):
			raise HTTPError(403, "%s is not in root static directory", path)
		if os.path.isdir(abspath) and self.default_filename is not None:
			# need to look at the request.path here for when path is empty
			# but there is some prefix to the path that was already
			# trimmed by the routing
			if not self.request.path.endswith("/"):
				self.redirect(self.request.path + "/")
				return
			abspath = os.path.join(abspath, self.default_filename)
		if not os.path.exists(abspath):
			raise HTTPError(404)
		if not os.path.isfile(abspath):
			raise HTTPError(403, "%s is not a file", path)

		stat_result = os.stat(abspath)
		modified = datetime.datetime.fromtimestamp(stat_result[stat.ST_MTIME])

		self.set_header("Last-Modified", modified)

		mime_type, encoding = mimetypes.guess_type(abspath)
		if mime_type:
			self.set_header("Content-Type", mime_type)

		cache_time = self.get_cache_time(path, modified, mime_type)

		if cache_time > 0:
			self.set_header("Expires", datetime.datetime.utcnow() +
									   datetime.timedelta(seconds=cache_time))
			self.set_header("Cache-Control", "max-age=" + str(cache_time))

		self.set_extra_headers(path)

		# Check the If-Modified-Since, and don't send the result if the
		# content has not been modified
		ims_value = self.request.headers.get("If-Modified-Since")
		if ims_value is not None:
			date_tuple = email.utils.parsedate(ims_value)
			if_since = datetime.datetime.fromtimestamp(time.mktime(date_tuple))
			if if_since >= modified:
				self.set_status(304)
				return

		if not include_body:
			assert self.request.method == "HEAD"
			self.set_header("Content-Length", stat_result[stat.ST_SIZE])
		else:
			with open(abspath, "rb") as file:
				while True:
					data = file.read(LargeResponseHandler.CHUNK_SIZE)
					if not data:
						break
					self.write(data)
					self.flush()

	def set_extra_headers(self, path):
		if self._as_attachment:
			self.set_header("Content-Disposition", "attachment")

#~~ startup code
class Server():
	def __init__(self, configfile=None, basedir=None, host="0.0.0.0", port=5000, debug=False, allowRoot=False):
		self._configfile = configfile
		self._basedir = basedir
		self._host = host
		self._port = port
		self._debug = debug
		self._allowRoot = allowRoot

		  
	def run(self):
		if not self._allowRoot:
			self._checkForRoot()

		# Global as I can't work out a way to get it into PrinterStateConnection
		global printer
		global gcodeManager
		global userManager
		global eventManager
		global loginManager
		global debug
		
		from tornado.wsgi import WSGIContainer
		from tornado.httpserver import HTTPServer
		from tornado.ioloop import IOLoop
		from tornado.web import Application, FallbackHandler, StaticFileHandler

		debug = self._debug

		# first initialize the settings singleton and make sure it uses given configfile and basedir if available
		self._initSettings(self._configfile, self._basedir)

		# then initialize logging
		self._initLogging(self._debug)
		logger = logging.getLogger(__name__)

		eventManager = events.eventManager()
		gcodeManager = gcodefiles.GcodeManager()
		printer = Printer(gcodeManager)

		# configure timelapse
		_configureTimelapse()

		# setup system and gcode command triggers
		events.SystemCommandTrigger(printer)
		events.GcodeCommandTrigger(printer)
		if self._debug:
			events.DebugEventListener()

		if settings().getBoolean(["accessControl", "enabled"]):
			userManagerName = settings().get(["accessControl", "userManager"])
			try:
				clazz = util.getClass(userManagerName)
				userManager = clazz()
			except AttributeError, e:
				logger.exception("Could not instantiate user manager %s, will run with accessControl disabled!" % userManagerName)

		app.secret_key = "k3PuVYgtxNm8DXKKTw2nWmFQQun9qceV"
		loginManager = LoginManager()
		loginManager.session_protection = "strong"
		loginManager.user_callback = load_user
		if userManager is None:
			loginManager.anonymous_user = users.DummyUser
			principals.identity_loaders.appendleft(users.dummy_identity_loader)
		loginManager.init_app(app)

		if self._host is None:
			self._host = settings().get(["server", "host"])
		if self._port is None:
			self._port = settings().getInt(["server", "port"])

		logger.info("Listening on http://%s:%d" % (self._host, self._port))
		app.debug = self._debug

		self._router = SockJSRouter(self._createSocketConnection, "/sockjs")

		self._tornado_app = Application(self._router.urls + [
			(r"/downloads/timelapse/([^/]*\.mpg)", LargeResponseHandler, {"path": settings().getBaseFolder("timelapse"), "as_attachment": True}),
			(r"/downloads/gcode/([^/]*\.(gco|gcode))", LargeResponseHandler, {"path": settings().getBaseFolder("uploads"), "as_attachment": True}),
			(r".*", FallbackHandler, {"fallback": WSGIContainer(app)})
		])
		self._server = HTTPServer(self._tornado_app)
		self._server.listen(self._port, address=self._host)

		eventManager.fire("Startup")
		if settings().getBoolean(["serial", "autoconnect"]):
			(port, baudrate) = settings().get(["serial", "port"]), settings().getInt(["serial", "baudrate"])
			connectionOptions = getConnectionOptions()
			if port in connectionOptions["ports"]:
				printer.connect(port, baudrate)
		try:
			IOLoop.instance().start()
		except:
			logger.fatal("Now that is embarrassing... Something really really went wrong here. Please report this including the stacktrace below in OctoPrint's bugtracker. Thanks!")
			logger.exception("Stacktrace follows:")

	def _createSocketConnection(self, session):
		global printer, gcodeManager, userManager, eventManager
		return PrinterStateConnection(printer, gcodeManager, userManager, eventManager, session)

	def _checkForRoot(self):
		if "geteuid" in dir(os) and os.geteuid() == 0:
			exit("You should not run OctoPrint as root!")

	def _initSettings(self, configfile, basedir):
		s = settings(init=True, basedir=basedir, configfile=configfile)

	def _initLogging(self, debug):
		config = {
			"version": 1,
			"formatters": {
				"simple": {
					"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
				}
			},
			"handlers": {
				"console": {
					"class": "logging.StreamHandler",
					"level": "DEBUG",
					"formatter": "simple",
					"stream": "ext://sys.stdout"
				},
				"file": {
					"class": "logging.handlers.TimedRotatingFileHandler",
					"level": "DEBUG",
					"formatter": "simple",
					"when": "D",
					"backupCount": "1",
					"filename": os.path.join(settings().getBaseFolder("logs"), "octoprint.log")
				},
				"serialFile": {
					"class": "logging.handlers.RotatingFileHandler",
					"level": "DEBUG",
					"formatter": "simple",
					"maxBytes": 2 * 1024 * 1024, # let's limit the serial log to 2MB in size
					"filename": os.path.join(settings().getBaseFolder("logs"), "serial.log")
				}
			},
			"loggers": {
				#"octoprint.timelapse": {
				#	"level": "DEBUG"
				#},
				#"octoprint.events": {
				#	"level": "DEBUG"
				#},
				"SERIAL": {
					"level": "CRITICAL",
					"handlers": ["serialFile"],
					"propagate": False
				}
			},
			"root": {
				"level": "INFO",
				"handlers": ["console", "file"]
			}
		}

		if debug:
			config["root"]["level"] = "DEBUG"

		logging.config.dictConfig(config)

		if settings().getBoolean(["serial", "log"]):
			# enable debug logging to serial.log
			logging.getLogger("SERIAL").setLevel(logging.DEBUG)
			logging.getLogger("SERIAL").debug("Enabling serial logging")

if __name__ == "__main__":
	octoprint = Server()
	octoprint.run()
