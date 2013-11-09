# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

from sockjs.tornado import SockJSRouter
from flask import Flask, render_template, send_from_directory
from flask.ext.login import LoginManager
from flask.ext.principal import Principal, Permission, RoleNeed, identity_loaded, UserNeed

import os
import logging
import logging.config

SUCCESS = {}

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


from octoprint.server.util import LargeResponseHandler, ReverseProxied, restricted_access, PrinterStateConnection
from octoprint.printer import Printer, getConnectionOptions
from octoprint.settings import settings
import octoprint.gcodefiles as gcodefiles
import octoprint.util as util
import octoprint.users as users
import octoprint.events as events
import octoprint.timelapse


@app.route("/")
def index():
	branch = None
	commit = None
	try:
		branch, commit = util.getGitInfo()
	except:
		pass

	return render_template(
		"index.jinja2",
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

		global printer
		global gcodeManager
		global userManager
		global eventManager
		global loginManager
		global debug

		from tornado.wsgi import WSGIContainer
		from tornado.httpserver import HTTPServer
		from tornado.ioloop import IOLoop
		from tornado.web import Application, FallbackHandler

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
		octoprint.timelapse.configureTimelapse()

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

		app.wsgi_app = ReverseProxied(app.wsgi_app)

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

		from octoprint.server.ajax import ajax
		from octoprint.server.api import api

		app.register_blueprint(ajax, url_prefix="/ajax")
		app.register_blueprint(api, url_prefix="/api")

		self._router = SockJSRouter(self._createSocketConnection, "/sockjs")

		self._tornado_app = Application(self._router.urls + [
			(r"/downloads/timelapse/([^/]*\.mpg)", LargeResponseHandler, {"path": settings().getBaseFolder("timelapse"), "as_attachment": True}),
			(r"/downloads/gcode/([^/]*\.(gco|gcode))", LargeResponseHandler, {"path": settings().getBaseFolder("uploads"), "as_attachment": True}),
			(r".*", FallbackHandler, {"fallback": WSGIContainer(app.wsgi_app)})
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
		settings(init=True, basedir=basedir, configfile=configfile)

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
