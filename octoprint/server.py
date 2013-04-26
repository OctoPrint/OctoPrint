# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

from werkzeug.utils import secure_filename
import tornadio2
from flask import Flask, request, render_template, jsonify, send_from_directory, url_for, current_app, session, abort
from flask.ext.login import LoginManager, login_user, logout_user, login_required, current_user
from flask.ext.principal import Principal, Permission, RoleNeed, Identity, identity_changed, AnonymousIdentity, identity_loaded, UserNeed

import os
import threading
import logging, logging.config
import subprocess

from octoprint.printer import Printer, getConnectionOptions
from octoprint.settings import settings, valid_boolean_trues
import octoprint.timelapse as timelapse
import octoprint.gcodefiles as gcodefiles
import octoprint.util as util
import octoprint.users as users

SUCCESS = {}
BASEURL = "/ajax/"

app = Flask("octoprint")
# Only instantiated by the Server().run() method
# In order that threads don't start too early when running as a Daemon
printer = None 
gcodeManager = None
userManager = None

principals = Principal(app)
admin_permission = Permission(RoleNeed("admin"))
user_permission = Permission(RoleNeed("user"))

#~~ Printer state

class PrinterStateConnection(tornadio2.SocketConnection):
	def __init__(self, printer, gcodeManager, userManager, session, endpoint=None):
		tornadio2.SocketConnection.__init__(self, session, endpoint)

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

	def on_open(self, info):
		self._logger.info("New connection from client")
		# Use of global here is smelly
		printer.registerCallback(self)
		gcodeManager.registerCallback(self)

	def on_close(self):
		self._logger.info("Closed client connection")
		# Use of global here is smelly
		printer.unregisterCallback(self)
		gcodeManager.unregisterCallback(self)

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
		self.emit("current", data)

	def sendHistoryData(self, data):
		self.emit("history", data)

	def sendUpdateTrigger(self, type):
		self.emit("updateTrigger", type)

	def addLog(self, data):
		with self._logBacklogMutex:
			self._logBacklog.append(data)

	def addMessage(self, data):
		with self._messageBacklogMutex:
			self._messageBacklog.append(data)

	def addTemperature(self, data):
		with self._temperatureBacklogMutex:
			self._temperatureBacklog.append(data)

# Did attempt to make webserver an encapsulated class but ended up with __call__ failures

@app.route("/")
def index():
	return render_template(
		"index.jinja2",
		ajaxBaseUrl=BASEURL,
		webcamStream=settings().get(["webcam", "stream"]),
		enableTimelapse=(settings().get(["webcam", "snapshot"]) is not None and settings().get(["webcam", "ffmpeg"]) is not None),
		enableGCodeVisualizer=settings().get(["feature", "gCodeVisualizer"]),
		enableSystemMenu=settings().get(["system"]) is not None and settings().get(["system", "actions"]) is not None and len(settings().get(["system", "actions"])) > 0,
		enableAccessControl=userManager is not None
	)

#~~ Printer control

@app.route(BASEURL + "control/connection/options", methods=["GET"])
def connectionOptions():
	return jsonify(getConnectionOptions())

@app.route(BASEURL + "control/connection", methods=["POST"])
@login_required
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
		printer.connect(port=port, baudrate=baudrate)
	elif "command" in request.values.keys() and request.values["command"] == "disconnect":
		printer.disconnect()

	return jsonify(SUCCESS)

@app.route(BASEURL + "control/command", methods=["POST"])
@login_required
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
@login_required
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
@login_required
def setTargetTemperature():
	if "temp" in request.values.keys():
		# set target temperature
		temp = request.values["temp"]
		printer.command("M104 S" + temp)

	if "bedTemp" in request.values.keys():
		# set target bed temperature
		bedTemp = request.values["bedTemp"]
		printer.command("M140 S" + bedTemp)

	return jsonify(SUCCESS)

@app.route(BASEURL + "control/jog", methods=["POST"])
@login_required
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

@app.route(BASEURL + "control/speed", methods=["GET"])
def getSpeedValues():
	return jsonify(feedrate=printer.feedrateState())

@app.route(BASEURL + "control/speed", methods=["POST"])
@login_required
def speed():
	if not printer.isOperational():
		return jsonify(SUCCESS)

	for key in ["outerWall", "innerWall", "fill", "support"]:
		if key in request.values.keys():
			value = int(request.values[key])
			printer.setFeedrateModifier(key, value)

	return getSpeedValues()

@app.route(BASEURL + "control/custom", methods=["GET"])
def getCustomControls():
	customControls = settings().get(["controls"])
	return jsonify(controls=customControls)

#~~ GCODE file handling

@app.route(BASEURL + "gcodefiles", methods=["GET"])
def readGcodeFiles():
	return jsonify(files=gcodeManager.getAllFileData())

@app.route(BASEURL + "gcodefiles/<path:filename>", methods=["GET"])
def readGcodeFile(filename):
	return send_from_directory(settings().getBaseFolder("uploads"), filename, as_attachment=True)

@app.route(BASEURL + "gcodefiles/upload", methods=["POST"])
@login_required
def uploadGcodeFile():
	filename = None
	if "gcode_file" in request.files.keys():
		file = request.files["gcode_file"]
		filename = gcodeManager.addFile(file)
	return jsonify(files=gcodeManager.getAllFileData(), filename=filename)

@app.route(BASEURL + "gcodefiles/load", methods=["POST"])
@login_required
def loadGcodeFile():
	if "filename" in request.values.keys():
		printAfterLoading = False
		if "print" in request.values.keys() and request.values["print"] in valid_boolean_trues:
			printAfterLoading = True
		filename = gcodeManager.getAbsolutePath(request.values["filename"])
		if filename is not None:
			printer.loadGcode(filename, printAfterLoading)
	return jsonify(SUCCESS)

@app.route(BASEURL + "gcodefiles/delete", methods=["POST"])
@login_required
def deleteGcodeFile():
	if "filename" in request.values.keys():
		filename = request.values["filename"]
		gcodeManager.removeFile(filename)
	return readGcodeFiles()

#~~ timelapse handling

@app.route(BASEURL + "timelapse", methods=["GET"])
def getTimelapseData():
	lapse = printer.getTimelapse()

	type = "off"
	additionalConfig = {}
	if lapse is not None and isinstance(lapse, timelapse.ZTimelapse):
		type = "zchange"
	elif lapse is not None and isinstance(lapse, timelapse.TimedTimelapse):
		type = "timed"
		additionalConfig = {
			"interval": lapse.interval()
		}

	files = timelapse.getFinishedTimelapses()
	for file in files:
		file["url"] = url_for("downloadTimelapse", filename=file["name"])

	return jsonify({
	"type": type,
	"config": additionalConfig,
	"files": files
	})

@app.route(BASEURL + "timelapse/<filename>", methods=["GET"])
def downloadTimelapse(filename):
	if util.isAllowedFile(filename, set(["mpg"])):
		return send_from_directory(settings().getBaseFolder("timelapse"), filename, as_attachment=True)

@app.route(BASEURL + "timelapse/<filename>", methods=["DELETE"])
@login_required
def deleteTimelapse(filename):
	if util.isAllowedFile(filename, set(["mpg"])):
		secure = os.path.join(settings().getBaseFolder("timelapse"), secure_filename(filename))
		if os.path.exists(secure):
			os.remove(secure)
	return getTimelapseData()

@app.route(BASEURL + "timelapse", methods=["POST"])
@login_required
def setTimelapseConfig():
	if request.values.has_key("type"):
		type = request.values["type"]
		lapse = None
		if "zchange" == type:
			lapse = timelapse.ZTimelapse()
		elif "timed" == type:
			interval = 10
			if request.values.has_key("interval"):
				try:
					interval = int(request.values["interval"])
				except ValueError:
					pass
			lapse = timelapse.TimedTimelapse(interval)
		printer.setTimelapse(lapse)

	return getTimelapseData()

#~~ settings

@app.route(BASEURL + "settings", methods=["GET"])
def getSettings():
	s = settings()

	[movementSpeedX, movementSpeedY, movementSpeedZ, movementSpeedE] = s.get(["printerParameters", "movementSpeed", ["x", "y", "z", "e"]])

	return jsonify({
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
			"watermark": s.getBoolean(["webcam", "watermark"])
		},
		"feature": {
			"gcodeViewer": s.getBoolean(["feature", "gCodeVisualizer"]),
			"waitForStart": s.getBoolean(["feature", "waitForStartOnConnect"])
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
			"actions": s.get(["system", "actions"])
		}
	})

@app.route(BASEURL + "settings", methods=["POST"])
@login_required
@admin_permission.require(403)
def setSettings():
	if "application/json" in request.headers["Content-Type"]:
		data = request.json
		s = settings()

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

		if "feature" in data.keys():
			if "gcodeViewer" in data["feature"].keys(): s.setBoolean(["feature", "gCodeVisualizer"], data["feature"]["gcodeViewer"])
			if "waitForStart" in data["feature"].keys(): s.setBoolean(["feature", "waitForStartOnConnect"], data["feature"]["waitForStart"])

		if "folder" in data.keys():
			if "uploads" in data["folder"].keys(): s.setBaseFolder("uploads", data["folder"]["uploads"])
			if "timelapse" in data["folder"].keys(): s.setBaseFolder("timelapse", data["folder"]["timelapse"])
			if "timelapseTmp" in data["folder"].keys(): s.setBaseFolder("timelapse_tmp", data["folder"]["timelapseTmp"])
			if "logs" in data["folder"].keys(): s.setBaseFolder("logs", data["folder"]["logs"])

		if "temperature" in data.keys():
			if "profiles" in data["temperature"].keys(): s.set(["temperature", "profiles"], data["temperature"]["profiles"])

		if "system" in data.keys():
			if "actions" in data["system"].keys(): s.set(["system", "actions"], data["system"]["actions"])

		s.save()

	return getSettings()

#~~ user settings

@app.route(BASEURL + "users", methods=["GET"])
@login_required
@admin_permission.require(403)
def getUsers():
	if userManager is None:
		return jsonify(SUCCESS)

	return jsonify({"users": userManager.getAllUsers()})

@app.route(BASEURL + "users", methods=["POST"])
@login_required
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
@login_required
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
@login_required
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
@login_required
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
@login_required
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
@login_required
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

		if "remember" in request.values.keys() and request.values["remember"]:
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
			return jsonify(user.asDict())
	return jsonify(SUCCESS)

@app.route(BASEURL + "logout", methods=["POST"])
@login_required
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

#~~ startup code
class Server():
	def __init__(self, configfile=None, basedir=None, host="0.0.0.0", port=5000, debug=False):
		self._configfile = configfile
		self._basedir = basedir
		self._host = host
		self._port = port
		self._debug = debug

	def run(self):
		# Global as I can't work out a way to get it into PrinterStateConnection
		global printer
		global gcodeManager
		global userManager

		from tornado.wsgi import WSGIContainer
		from tornado.httpserver import HTTPServer
		from tornado.ioloop import IOLoop
		from tornado.web import Application, FallbackHandler

		# first initialize the settings singleton and make sure it uses given configfile and basedir if available
		self._initSettings(self._configfile, self._basedir)

		# then initialize logging
		self._initLogging(self._debug)
		logger = logging.getLogger(__name__)

		gcodeManager = gcodefiles.GcodeManager()
		printer = Printer(gcodeManager)

		if settings().getBoolean(["accessControl", "enabled"]):
			userManagerName = settings().get(["accessControl", "userManager"])
			try:
				clazz = util.getClass(userManagerName)
				userManager = clazz()
			except AttributeError, e:
				logger.exception("Could not instantiate user manager %s, will run with accessControl disabled!" % userManagerName)

		app.secret_key = "k3PuVYgtxNm8DXKKTw2nWmFQQun9qceV"
		login_manager = LoginManager()
		login_manager.session_protection = "strong"
		login_manager.user_callback = load_user
		if userManager is None:
			login_manager.anonymous_user = users.DummyUser
			principals.identity_loaders.appendleft(users.dummy_identity_loader)
		login_manager.init_app(app)

		if self._host is None:
			self._host = settings().get(["server", "host"])
		if self._port is None:
			self._port = settings().getInt(["server", "port"])

		logger.info("Listening on http://%s:%d" % (self._host, self._port))
		app.debug = self._debug

		self._router = tornadio2.TornadioRouter(self._createSocketConnection)

		self._tornado_app = Application(self._router.urls + [
			(".*", FallbackHandler, {"fallback": WSGIContainer(app)})
		])
		self._server = HTTPServer(self._tornado_app)
		self._server.listen(self._port, address=self._host)
		IOLoop.instance().start()

	def _createSocketConnection(self, session, endpoint=None):
		global printer, gcodeManager, userManager
		return PrinterStateConnection(printer, gcodeManager, userManager, session, endpoint)

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
			},
			"root": {
				"level": "INFO",
				"handlers": ["console", "file"]
			}
		}

		if debug:
			config["loggers"]["SERIAL"] = {
				"level": "DEBUG",
				"handlers": ["serialFile"],
				"propagate": False
			}

		logging.config.dictConfig(config)

if __name__ == "__main__":
	octoprint = Server()
	octoprint.run()
