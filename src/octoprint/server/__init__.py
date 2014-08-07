# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import uuid
from sockjs.tornado import SockJSRouter
from flask import Flask, render_template, send_from_directory
from flask.ext.login import LoginManager
from flask.ext.principal import Principal, Permission, RoleNeed, identity_loaded, UserNeed
from watchdog.observers import Observer

import os
import logging
import logging.config

SUCCESS = {}
NO_CONTENT = ("", 204)

app = Flask("octoprint")
debug = False

printer = None
gcodeManager = None
userManager = None
eventManager = None
loginManager = None

principals = Principal(app)
admin_permission = Permission(RoleNeed("admin"))
user_permission = Permission(RoleNeed("user"))

# only import the octoprint stuff down here, as it might depend on things defined above to be initialized already
from octoprint.printer import Printer, getConnectionOptions
from octoprint.settings import settings
import octoprint.gcodefiles as gcodefiles
import octoprint.users as users
import octoprint.events as events
import octoprint.timelapse
import octoprint._version
import octoprint.util

from . import util


UI_API_KEY = ''.join('%02X' % ord(z) for z in uuid.uuid4().bytes)
VERSION = octoprint._version.get_versions()['version']


@app.route("/")
def index():
	return render_template(
		"index.jinja2",
		webcamStream=settings().get(["webcam", "stream"]),
		enableTimelapse=(settings().get(["webcam", "snapshot"]) is not None and settings().get(["webcam", "ffmpeg"]) is not None),
		enableGCodeVisualizer=settings().get(["gcodeViewer", "enabled"]),
		enableTemperatureGraph=settings().get(["feature", "temperatureGraph"]),
		enableSystemMenu=settings().get(["system"]) is not None and settings().get(["system", "actions"]) is not None and len(settings().get(["system", "actions"])) > 0,
		enableAccessControl=userManager is not None,
		enableSdSupport=settings().get(["feature", "sdSupport"]),
		firstRun=settings().getBoolean(["server", "firstRun"]) and (userManager is None or not userManager.hasBeenCustomized()),
		debug=debug,
		version=VERSION,
		stylesheet=settings().get(["devel", "stylesheet"]),
		gcodeMobileThreshold=settings().get(["gcodeViewer", "mobileSizeThreshold"]),
		gcodeThreshold=settings().get(["gcodeViewer", "sizeThreshold"]),
		uiApiKey=UI_API_KEY
	)


@app.route("/robots.txt")
def robotsTxt():
	return send_from_directory(app.static_folder, "robots.txt")


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
	def __init__(self, configfile=None, basedir=None, host="0.0.0.0", port=5000, debug=False, allowRoot=False, logConf=None):
		self._configfile = configfile
		self._basedir = basedir
		self._host = host
		self._port = port
		self._debug = debug
		self._allowRoot = allowRoot
		self._logConf = logConf
		self._server = None

	def run(self):
		if not self._allowRoot:
			self._checkForRoot()

		global printer
		global gcodeManager
		global userManager
		global eventManager
		global loginManager
		global debug

		from tornado.ioloop import IOLoop
		from tornado.web import Application

		debug = self._debug

		# first initialize the settings singleton and make sure it uses given configfile and basedir if available
		self._initSettings(self._configfile, self._basedir)

		# then initialize logging
		self._initLogging(self._debug, self._logConf)
		logger = logging.getLogger(__name__)

		logger.info("Starting OctoPrint (%s)" % VERSION)

		eventManager = events.eventManager()
		gcodeManager = gcodefiles.GcodeManager()
		printer = Printer(gcodeManager)

		# configure timelapse
		octoprint.timelapse.configureTimelapse()

		# setup command triggers
		events.CommandTrigger(printer)
		if self._debug:
			events.DebugEventListener()

		if settings().getBoolean(["accessControl", "enabled"]):
			userManagerName = settings().get(["accessControl", "userManager"])
			try:
				clazz = octoprint.util.getClass(userManagerName)
				userManager = clazz()
			except AttributeError, e:
				logger.exception("Could not instantiate user manager %s, will run with accessControl disabled!" % userManagerName)

		app.wsgi_app = util.ReverseProxied(
			app.wsgi_app,
			settings().get(["server", "reverseProxy", "prefixHeader"]),
			settings().get(["server", "reverseProxy", "schemeHeader"]),
			settings().get(["server", "reverseProxy", "prefixFallback"]),
			settings().get(["server", "reverseProxy", "prefixScheme"])
		)

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

		from octoprint.server.api import api

		app.register_blueprint(api, url_prefix="/api")

		self._router = SockJSRouter(self._createSocketConnection, "/sockjs")

		upload_suffixes = dict(name=settings().get(["server", "uploads", "nameSuffix"]), path=settings().get(["server", "uploads", "pathSuffix"]))
		self._tornado_app = Application(self._router.urls + [
			(r"/downloads/timelapse/([^/]*\.mpg)", util.tornado.LargeResponseHandler, dict(path=settings().getBaseFolder("timelapse"), as_attachment=True)),
			(r"/downloads/files/local/([^/]*\.(gco|gcode))", util.tornado.LargeResponseHandler, dict(path=settings().getBaseFolder("uploads"), as_attachment=True)),
			(r"/downloads/logs/([^/]*)", util.tornado.LargeResponseHandler, dict(path=settings().getBaseFolder("logs"), as_attachment=True, access_validation=util.tornado.access_validation_factory(app, loginManager, util.flask.admin_validator))),
			(r"/downloads/camera/current", util.tornado.UrlForwardHandler, dict(url=settings().get(["webcam", "snapshot"]), as_attachment=True, access_validation=util.tornado.access_validation_factory(app, loginManager, util.flask.user_validator))),
			(r".*", util.tornado.UploadStorageFallbackHandler, dict(fallback=util.tornado.WsgiInputContainer(app.wsgi_app), file_prefix="octoprint-file-upload-", file_suffix=".tmp", suffixes=upload_suffixes))
		])
		max_body_sizes = [
			("POST", r"/api/files/([^/]*)", settings().getInt(["server", "uploads", "maxSize"]))
		]
		self._server = util.tornado.CustomHTTPServer(self._tornado_app, max_body_sizes=max_body_sizes, default_max_body_size=settings().getInt(["server", "maxSize"]))
		self._server.listen(self._port, address=self._host)

		eventManager.fire(events.Events.STARTUP)
		if settings().getBoolean(["serial", "autoconnect"]):
			(port, baudrate) = settings().get(["serial", "port"]), settings().getInt(["serial", "baudrate"])
			connectionOptions = getConnectionOptions()
			if port in connectionOptions["ports"]:
				printer.connect(port, baudrate)

		# start up watchdogs
		observer = Observer()
		observer.schedule(util.watchdog.GcodeWatchdogHandler(gcodeManager, printer), settings().getBaseFolder("watched"))
		observer.schedule(util.watchdog.UploadCleanupWatchdogHandler(gcodeManager), settings().getBaseFolder("uploads"))
		observer.start()

		try:
			IOLoop.instance().start()
		except KeyboardInterrupt:
			logger.info("Goodbye!")
		except:
			logger.fatal("Now that is embarrassing... Something really really went wrong here. Please report this including the stacktrace below in OctoPrint's bugtracker. Thanks!")
			logger.exception("Stacktrace follows:")
		finally:
			observer.stop()
		observer.join()

	def _createSocketConnection(self, session):
		global printer, gcodeManager, userManager, eventManager
		return util.sockjs.PrinterStateConnection(printer, gcodeManager, userManager, eventManager, session)

	def _checkForRoot(self):
		if "geteuid" in dir(os) and os.geteuid() == 0:
			exit("You should not run OctoPrint as root!")

	def _initSettings(self, configfile, basedir):
		settings(init=True, basedir=basedir, configfile=configfile)

	def _initLogging(self, debug, logConf=None):
		defaultConfig = {
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
			defaultConfig["root"]["level"] = "DEBUG"

		if logConf is None:
			logConf = os.path.join(settings().settings_dir, "logging.yaml")

		configFromFile = {}
		if os.path.exists(logConf) and os.path.isfile(logConf):
			import yaml
			with open(logConf, "r") as f:
				configFromFile = yaml.safe_load(f)

		config = octoprint.util.dict_merge(defaultConfig, configFromFile)
		logging.config.dictConfig(config)

		if settings().getBoolean(["serial", "log"]):
			# enable debug logging to serial.log
			logging.getLogger("SERIAL").setLevel(logging.DEBUG)
			logging.getLogger("SERIAL").debug("Enabling serial logging")

if __name__ == "__main__":
	server = Server()
	server.run()
