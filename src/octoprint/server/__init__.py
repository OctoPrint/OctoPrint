# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import uuid
from sockjs.tornado import SockJSRouter
from flask import Flask, render_template, send_from_directory, g, request, make_response, session, url_for
from flask.ext.login import LoginManager, current_user
from flask.ext.principal import Principal, Permission, RoleNeed, identity_loaded, UserNeed
from flask.ext.babel import Babel, gettext, ngettext
from babel import Locale
from watchdog.observers import Observer
from collections import defaultdict

import os
import logging
import logging.config
import atexit

SUCCESS = {}
NO_CONTENT = ("", 204)

app = Flask("octoprint")
babel = Babel(app)
debug = False

printer = None
printerProfileManager = None
fileManager = None
slicingManager = None
analysisQueue = None
userManager = None
eventManager = None
loginManager = None
pluginManager = None
appSessionManager = None

principals = Principal(app)
admin_permission = Permission(RoleNeed("admin"))
user_permission = Permission(RoleNeed("user"))

# only import the octoprint stuff down here, as it might depend on things defined above to be initialized already
from octoprint.printer import get_connection_options
from octoprint.printer.profile import PrinterProfileManager
from octoprint.printer.standard import Printer
from octoprint.settings import settings
import octoprint.users as users
import octoprint.events as events
import octoprint.plugin
import octoprint.timelapse
import octoprint._version
import octoprint.util
import octoprint.filemanager.storage
import octoprint.filemanager.analysis
import octoprint.slicing

from . import util
util.tornado.fix_ioloop_scheduling()


UI_API_KEY = ''.join('%02X' % ord(z) for z in uuid.uuid4().bytes)

versions = octoprint._version.get_versions()
VERSION = versions['version']
BRANCH = versions['branch'] if 'branch' in versions else None
DISPLAY_VERSION = "%s (%s branch)" % (VERSION, BRANCH) if BRANCH else VERSION
del versions


def get_available_locale_identifiers(locales):
	result = set()

	# add available translations
	for locale in locales:
		result.add(locale.language)
		if locale.territory:
			# if a territory is specified, add that too
			result.add("%s_%s" % (locale.language, locale.territory))

	return result


LOCALES = [Locale.parse("en")] + babel.list_translations()
LANGUAGES = get_available_locale_identifiers(LOCALES)


@app.before_request
def before_request():
	g.locale = get_locale()

@app.after_request
def after_request(response):
	# send no-cache headers with all POST responses
	if request.method == "POST":
		response.cache_control.no_cache = True
	response.headers.add("X-Clacks-Overhead", "GNU Terry Pratchett")
	return response


@babel.localeselector
def get_locale():
	if "l10n" in request.values:
		return Locale.negotiate([request.values["l10n"]], LANGUAGES)

	if hasattr(g, "identity") and g.identity and userManager is not None:
		userid = g.identity.id
		try:
			user_language = userManager.getUserSetting(userid, ("interface", "language"))
			if user_language is not None and not user_language == "_default":
				return Locale.negotiate([user_language], LANGUAGES)
		except octoprint.users.UnknownUser:
			pass

	default_language = settings().get(["appearance", "defaultLanguage"])
	if default_language is not None and not default_language == "_default" and default_language in LANGUAGES:
		return Locale.negotiate([default_language], LANGUAGES)

	return request.accept_languages.best_match(LANGUAGES)


@app.route("/")
@util.flask.cached(refreshif=lambda: util.flask.cache_check_headers() or "_refresh" in request.values, key=lambda: "view/%s/%s" % (request.path, g.locale))
def index():

	#~~ a bunch of settings

	enable_gcodeviewer = settings().getBoolean(["gcodeViewer", "enabled"])
	enable_timelapse = (settings().get(["webcam", "snapshot"]) and settings().get(["webcam", "ffmpeg"]))
	enable_systemmenu = settings().get(["system"]) is not None and settings().get(["system", "actions"]) is not None and len(settings().get(["system", "actions"])) > 0
	enable_accesscontrol = userManager is not None
	preferred_stylesheet = settings().get(["devel", "stylesheet"])
	locales = dict((l.language, dict(language=l.language, display=l.display_name, english=l.english_name)) for l in LOCALES)

#~~ prepare assets

	supported_stylesheets = ("css", "less")
	assets = dict(
		js=[],
		stylesheets=[]
	)
	assets["js"] = [
		url_for('static', filename='js/app/viewmodels/appearance.js'),
		url_for('static', filename='js/app/viewmodels/connection.js'),
		url_for('static', filename='js/app/viewmodels/control.js'),
		url_for('static', filename='js/app/viewmodels/firstrun.js'),
		url_for('static', filename='js/app/viewmodels/files.js'),
		url_for('static', filename='js/app/viewmodels/loginstate.js'),
		url_for('static', filename='js/app/viewmodels/navigation.js'),
		url_for('static', filename='js/app/viewmodels/printerstate.js'),
		url_for('static', filename='js/app/viewmodels/printerprofiles.js'),
		url_for('static', filename='js/app/viewmodels/settings.js'),
		url_for('static', filename='js/app/viewmodels/slicing.js'),
		url_for('static', filename='js/app/viewmodels/temperature.js'),
		url_for('static', filename='js/app/viewmodels/terminal.js'),
		url_for('static', filename='js/app/viewmodels/users.js'),
		url_for('static', filename='js/app/viewmodels/log.js'),
		url_for('static', filename='js/app/viewmodels/usersettings.js')
	]
	if enable_gcodeviewer:
		assets["js"] += [
			url_for('static', filename='js/app/viewmodels/gcode.js'),
			url_for('static', filename='gcodeviewer/js/ui.js'),
			url_for('static', filename='gcodeviewer/js/gCodeReader.js'),
			url_for('static', filename='gcodeviewer/js/renderer.js')
		]
	if enable_timelapse:
		assets["js"].append(url_for('static', filename='js/app/viewmodels/timelapse.js'))

	if preferred_stylesheet == "less":
		assets["stylesheets"].append(("less", url_for('static', filename='less/octoprint.less')))
	elif preferred_stylesheet == "css":
		assets["stylesheets"].append(("css", url_for('static', filename='css/octoprint.css')))

	asset_plugins = pluginManager.get_implementations(octoprint.plugin.AssetPlugin)
	for implementation in asset_plugins:
		name = implementation._identifier
		all_assets = implementation.get_assets()

		if "js" in all_assets:
			for asset in all_assets["js"]:
				assets["js"].append(url_for('plugin_assets', name=name, filename=asset))

		if preferred_stylesheet in all_assets:
			for asset in all_assets[preferred_stylesheet]:
				assets["stylesheets"].append((preferred_stylesheet, url_for('plugin_assets', name=name, filename=asset)))
		else:
			for stylesheet in supported_stylesheets:
				if not stylesheet in all_assets:
					continue

				for asset in all_assets[stylesheet]:
					assets["stylesheets"].append((stylesheet, url_for('plugin_assets', name=name, filename=asset)))
				break

	##~~ prepare templates

	templates = dict(
		navbar=dict(order=[], entries=dict()),
		sidebar=dict(order=[], entries=dict()),
		tab=dict(order=[], entries=dict()),
		settings=dict(order=[], entries=dict()),
		usersettings=dict(order=[], entries=dict()),
		generic=dict(order=[], entries=dict())
	)
	template_types = templates.keys()

	# navbar

	templates["navbar"]["entries"] = dict(
		settings=dict(template="navbar/settings.jinja2", _div="navbar_settings", styles=["display: none"], data_bind="visible: loginState.isAdmin")
	)
	if enable_accesscontrol:
		templates["navbar"]["entries"]["login"] = dict(template="navbar/login.jinja2", _div="navbar_login", classes=["dropdown"], custom_bindings=False)
	if enable_systemmenu:
		templates["navbar"]["entries"]["systemmenu"] = dict(template="navbar/systemmenu.jinja2", _div="navbar_systemmenu", styles=["display: none"], classes=["dropdown"], data_bind="visible: loginState.isAdmin", custom_bindings=False)

	# sidebar

	templates["sidebar"]["entries"]= dict(
		connection=(gettext("Connection"), dict(template="sidebar/connection.jinja2", _div="connection", icon="signal", styles_wrapper=["display: none"], data_bind="visible: loginState.isAdmin")),
		state=(gettext("State"), dict(template="sidebar/state.jinja2", _div="state", icon="info-sign")),
		files=(gettext("Files"), dict(template="sidebar/files.jinja2", _div="files", icon="list", classes_content=["overflow_visible"], template_header="sidebar/files_header.jinja2"))
	)

	# tabs

	templates["tab"]["entries"] = dict(
		temperature=(gettext("Temperature"), dict(template="tabs/temperature.jinja2", _div="temp")),
		control=(gettext("Control"), dict(template="tabs/control.jinja2", _div="control")),
		terminal=(gettext("Terminal"), dict(template="tabs/terminal.jinja2", _div="term")),
	)
	if enable_gcodeviewer:
		templates["tab"]["entries"]["gcodeviewer"] = (gettext("GCode Viewer"), dict(template="tabs/gcodeviewer.jinja2", _div="gcode"))
	if enable_timelapse:
		templates["tab"]["entries"]["timelapse"] = (gettext("Timelapse"), dict(template="tabs/timelapse.jinja2", _div="timelapse"))

	# settings dialog

	templates["settings"]["entries"] = dict(
		section_printer=(gettext("Printer"), None),

		serial=(gettext("Serial Connection"), dict(template="dialogs/settings/serialconnection.jinja2", _div="settings_serialConnection", custom_bindings=False)),
		printerprofiles=(gettext("Printer Profiles"), dict(template="dialogs/settings/printerprofiles.jinja2", _div="settings_printerProfiles", custom_bindings=False)),
		temperatures=(gettext("Temperatures"), dict(template="dialogs/settings/temperatures.jinja2", _div="settings_temperature", custom_bindings=False)),
		terminalfilters=(gettext("Terminal Filters"), dict(template="dialogs/settings/terminalfilters.jinja2", _div="settings_terminalFilters", custom_bindings=False)),
		gcodescripts=(gettext("GCODE Scripts"), dict(template="dialogs/settings/gcodescripts.jinja2", _div="settings_gcodeScripts", custom_bindings=False)),

		section_features=(gettext("Features"), None),

		features=(gettext("Features"), dict(template="dialogs/settings/features.jinja2", _div="settings_features", custom_bindings=False)),
		webcam=(gettext("Webcam"), dict(template="dialogs/settings/webcam.jinja2", _div="settings_webcam", custom_bindings=False)),
		api=(gettext("API"), dict(template="dialogs/settings/api.jinja2", _div="settings_api", custom_bindings=False)),

		section_octoprint=(gettext("OctoPrint"), None),

		folders=(gettext("Folders"), dict(template="dialogs/settings/folders.jinja2", _div="settings_folders", custom_bindings=False)),
		appearance=(gettext("Appearance"), dict(template="dialogs/settings/appearance.jinja2", _div="settings_appearance", custom_bindings=False)),
		logs=(gettext("Logs"), dict(template="dialogs/settings/logs.jinja2", _div="settings_logs")),
	)
	if enable_accesscontrol:
		templates["settings"]["entries"]["accesscontrol"] = (gettext("Access Control"), dict(template="dialogs/settings/accesscontrol.jinja2", _div="settings_users", custom_bindings=False))

	# user settings dialog

	if enable_accesscontrol:
		templates["usersettings"]["entries"] = dict(
			access=(gettext("Access"), dict(template="dialogs/usersettings/access.jinja2", _div="usersettings_access", custom_bindings=False)),
			interface=(gettext("Interface"), dict(template="dialogs/usersettings/interface.jinja2", _div="usersettings_interface", custom_bindings=False)),
		)

	# extract data from template plugins

	template_plugins = pluginManager.get_implementations(octoprint.plugin.TemplatePlugin)

	# rules for transforming template configs to template entries
	rules = dict(
		navbar=dict(div=lambda x: "navbar_plugin_" + x, template=lambda x: x + "_navbar.jinja2", to_entry=lambda data: data),
		sidebar=dict(div=lambda x: "sidebar_plugin_" + x, template=lambda x: x + "_sidebar.jinja2", to_entry=lambda data: (data["name"], data)),
		tab=dict(div=lambda x: "tab_plugin_" + x, template=lambda x: x + "_tab.jinja2", to_entry=lambda data: (data["name"], data)),
		settings=dict(div=lambda x: "settings_plugin_" + x, template=lambda x: x + "_settings.jinja2", to_entry=lambda data: (data["name"], data)),
		usersettings=dict(div=lambda x: "usersettings_plugin_" + x, template=lambda x: x + "_usersettings.jinja2", to_entry=lambda data: (data["name"], data)),
		generic=dict(template=lambda x: x + ".jinja2", to_entry=lambda data: data)
	)

	plugin_vars = dict()
	plugin_names = set()
	for implementation in template_plugins:
		name = implementation._identifier
		plugin_names.add(name)

		vars = implementation.get_template_vars()
		if not isinstance(vars, dict):
			vars = dict()

		for var_name, var_value in vars.items():
			plugin_vars["plugin_" + name + "_" + var_name] = var_value

		configs = implementation.get_template_configs()
		if not isinstance(configs, (list, tuple)):
			configs = []

		includes = _process_template_configs(name, implementation, configs, rules)

		for t in template_types:
			for include in includes[t]:
				if t == "navbar" or t == "generic":
					data = include
				else:
					data = include[1]

				key = data["_key"]
				if "replaces" in data:
					key = data["replaces"]
				templates[t]["entries"][key] = include

	#~~ order internal templates and plugins

	# make sure that
	# 1) we only have keys in our ordered list that we have entries for and
	# 2) we have all entries located somewhere within the order

	for t in template_types:
		default_order = settings().get(["appearance", "components", "order", t], merged=True, config=dict())
		configured_order = settings().get(["appearance", "components", "order", t], merged=True)
		configured_disabled = settings().get(["appearance", "components", "disabled", t])

		# first create the ordered list of all component ids according to the configured order
		templates[t]["order"] = [x for x in configured_order if x in templates[t]["entries"] and not x in configured_disabled]

		# now append the entries from the default order that are not already in there
		templates[t]["order"] += [x for x in default_order if not x in templates[t]["order"] and x in templates[t]["entries"] and not x in configured_disabled]

		all_ordered = set(templates[t]["order"])
		all_disabled = set(configured_disabled)

		# check if anything is missing, if not we are done here
		missing_in_order = set(templates[t]["entries"].keys()).difference(all_ordered).difference(all_disabled)
		if len(missing_in_order) == 0:
			continue

		# finally add anything that's not included in our order yet
		sorted_missing = list(missing_in_order)
		if not t == "navbar" and not t == "generic":
			# anything but navbar and generic components get sorted by their name
			sorted_missing = sorted(missing_in_order, key=lambda x: templates[t]["entries"][x][0])

		if t == "navbar":
			# additional navbar components are prepended
			templates[t]["order"] = sorted_missing + templates[t]["order"]
		elif t == "sidebar" or t == "tab" or t == "generic" or t == "usersettings":
			# additional sidebar, generic or usersettings components are appended
			templates[t]["order"] += sorted_missing
		elif t == "settings":
			# additional settings items are added to the plugin section
			templates[t]["entries"]["section_plugins"] = (gettext("Plugins"), None)
			templates[t]["order"] += ["section_plugins"] + sorted_missing

	#~~ prepare full set of template vars for rendering

	render_kwargs = dict(
		webcamStream=settings().get(["webcam", "stream"]),
		enableTemperatureGraph=settings().get(["feature", "temperatureGraph"]),
		enableAccessControl=userManager is not None,
		enableSdSupport=settings().get(["feature", "sdSupport"]),
		firstRun=settings().getBoolean(["server", "firstRun"]) and (userManager is None or not userManager.hasBeenCustomized()),
		debug=debug,
		version=VERSION,
		display_version=DISPLAY_VERSION,
		gcodeMobileThreshold=settings().get(["gcodeViewer", "mobileSizeThreshold"]),
		gcodeThreshold=settings().get(["gcodeViewer", "sizeThreshold"]),
		uiApiKey=UI_API_KEY,
		templates=templates,
		assets=assets,
		pluginNames=plugin_names,
		locales=locales
	)
	render_kwargs.update(plugin_vars)

	#~~ render!

	return render_template(
		"index.jinja2",
		**render_kwargs
	)


def _process_template_configs(name, implementation, configs, rules):
	from jinja2.exceptions import TemplateNotFound

	counters = dict(
		navbar=1,
		sidebar=1,
		tab=1,
		settings=1,
		generic=1
	)
	includes = defaultdict(list)

	for config in configs:
		if not isinstance(config, dict):
			continue
		if not "type" in config:
			continue

		template_type = config["type"]
		del config["type"]

		if not template_type in rules:
			continue
		rule = rules[template_type]

		data = _process_template_config(name, implementation, rule, config=config, counter=counters[template_type])
		if data is None:
			continue

		includes[template_type].append(rule["to_entry"](data))
		counters[template_type] += 1

	for template_type in rules:
		if len(includes[template_type]) == 0:
			# if no template of that type was added by the config, we'll try to use the default template name
			rule = rules[template_type]
			data = _process_template_config(name, implementation, rule)
			if data is not None:
				try:
					app.jinja_env.get_or_select_template(data["template"])
				except TemplateNotFound:
					pass
				else:
					includes[template_type].append(rule["to_entry"](data))

	return includes

def _process_template_config(name, implementation, rule, config=None, counter=1):
	if "mandatory" in rule:
		for mandatory in rule["mandatory"]:
			if not mandatory in config:
				return None

	if config is None:
		config = dict()
	data = dict(config)

	if not "suffix" in data and counter > 1:
		data["suffix"] = "_%d" % counter

	if "div" in data:
		data["_div"] = data["div"]
	elif "div" in rule:
		data["_div"] = rule["div"](name)
		if "suffix" in data:
			data["_div"] = data["_div"] + data["suffix"]

	if not "template" in data:
		data["template"] = rule["template"](name)

	if not "name" in data:
		data["name"] = implementation._plugin_name

	if not "custom_bindings" in data or data["custom_bindings"]:
		data_bind = "allowBindings: true"
		if "data_bind" in data:
			data_bind = data_bind + ", " + data["data_bind"]
		data["data_bind"] = data_bind

	data["_key"] = "plugin_" + name
	if "suffix" in data:
		data["_key"] += data["suffix"]

	return data

@app.route("/robots.txt")
def robotsTxt():
	return send_from_directory(app.static_folder, "robots.txt")


@app.route("/plugin_assets/<string:name>/<path:filename>")
def plugin_assets(name, filename):
	asset_plugins = pluginManager.get_filtered_implementations(lambda p: p._identifier == name, octoprint.plugin.AssetPlugin)

	if not asset_plugins:
		return make_response("Asset not found", 404)

	if len(asset_plugins) > 1:
		return make_response("More than one asset provider for {name}, can't proceed".format(name=name), 500)

	asset_plugin = asset_plugins[0]
	asset_folder = asset_plugin.get_asset_folder()
	if asset_folder is None:
		return make_response("Asset not found", 404)

	return send_from_directory(asset_folder, filename)


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
	if id == "_api":
		return users.ApiUser()

	if session and "usersession.id" in session:
		sessionid = session["usersession.id"]
	else:
		sessionid = None

	if userManager is not None:
		if sessionid:
			return userManager.findUser(username=id, session=sessionid)
		else:
			return userManager.findUser(username=id)
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

		self._logger = None

		self._lifecycle_callbacks = defaultdict(list)

		self._template_searchpaths = []

	def run(self):
		if not self._allowRoot:
			self._check_for_root()

		global printer
		global printerProfileManager
		global fileManager
		global slicingManager
		global analysisQueue
		global userManager
		global eventManager
		global loginManager
		global pluginManager
		global appSessionManager
		global debug

		from tornado.ioloop import IOLoop
		from tornado.web import Application

		import sys

		debug = self._debug

		# first initialize the settings singleton and make sure it uses given configfile and basedir if available
		settings(init=True, basedir=self._basedir, configfile=self._configfile)

		# then initialize logging
		self._setup_logging(self._debug, self._logConf)
		self._logger = logging.getLogger(__name__)
		def exception_logger(exc_type, exc_value, exc_tb):
			self._logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))
		sys.excepthook = exception_logger
		self._logger.info("Starting OctoPrint %s" % DISPLAY_VERSION)

		# then initialize the plugin manager
		pluginManager = octoprint.plugin.plugin_manager(init=True)

		printerProfileManager = PrinterProfileManager()
		eventManager = events.eventManager()
		analysisQueue = octoprint.filemanager.analysis.AnalysisQueue()
		slicingManager = octoprint.slicing.SlicingManager(settings().getBaseFolder("slicingProfiles"), printerProfileManager)
		storage_managers = dict()
		storage_managers[octoprint.filemanager.FileDestinations.LOCAL] = octoprint.filemanager.storage.LocalFileStorage(settings().getBaseFolder("uploads"))
		fileManager = octoprint.filemanager.FileManager(analysisQueue, slicingManager, printerProfileManager, initial_storage_managers=storage_managers)
		printer = Printer(fileManager, analysisQueue, printerProfileManager)
		appSessionManager = util.flask.AppSessionManager()

		def octoprint_plugin_inject_factory(name, implementation):
			if not isinstance(implementation, octoprint.plugin.OctoPrintPlugin):
				return None
			return dict(
				plugin_manager=pluginManager,
				printer_profile_manager=printerProfileManager,
				event_bus=eventManager,
				analysis_queue=analysisQueue,
				slicing_manager=slicingManager,
				file_manager=fileManager,
				printer=printer,
				app_session_manager=appSessionManager
			)

		def settings_plugin_inject_factory(name, implementation):
			if not isinstance(implementation, octoprint.plugin.SettingsPlugin):
				return None
			default_settings = implementation.get_settings_defaults()
			get_preprocessors, set_preprocessors = implementation.get_settings_preprocessors()
			plugin_settings = octoprint.plugin.plugin_settings(name,
			                                                   defaults=default_settings,
			                                                   get_preprocessors=get_preprocessors,
			                                                   set_preprocessors=set_preprocessors)
			return dict(settings=plugin_settings)

		pluginManager.implementation_inject_factories=[octoprint_plugin_inject_factory, settings_plugin_inject_factory]
		pluginManager.initialize_implementations()

		lifecycleManager = LifecycleManager(self, pluginManager)
		pluginManager.log_all_plugins()

		# initialize slicing manager and register it for changes in the registered plugins
		slicingManager.initialize()
		lifecycleManager.add_callback(["enabled", "disabled"], lambda name, plugin: slicingManager.reload_slicers())

		# setup jinja2
		self._setup_jinja2()
		def template_enabled(name, plugin):
			if plugin.implementation is None or not isinstance(plugin.implementation, octoprint.plugin.TemplatePlugin):
				return
			self._register_additional_template_plugin(plugin.implementation)
		def template_disabled(name, plugin):
			if plugin.implementation is None or not isinstance(plugin.implementation, octoprint.plugin.TemplatePlugin):
				return
			self._unregister_additional_template_plugin(plugin.implementation)
		lifecycleManager.add_callback("enabled", template_enabled)
		lifecycleManager.add_callback("disabled", template_disabled)

		# configure timelapse
		octoprint.timelapse.configureTimelapse()

		# setup command triggers
		events.CommandTrigger(printer)
		if self._debug:
			events.DebugEventListener()

		if settings().getBoolean(["accessControl", "enabled"]):
			userManagerName = settings().get(["accessControl", "userManager"])
			try:
				clazz = octoprint.util.get_class(userManagerName)
				userManager = clazz()
			except AttributeError, e:
				self._logger.exception("Could not instantiate user manager %s, will run with accessControl disabled!" % userManagerName)

		app.wsgi_app = util.ReverseProxied(
			app.wsgi_app,
			settings().get(["server", "reverseProxy", "prefixHeader"]),
			settings().get(["server", "reverseProxy", "schemeHeader"]),
			settings().get(["server", "reverseProxy", "hostHeader"]),
			settings().get(["server", "reverseProxy", "prefixFallback"]),
			settings().get(["server", "reverseProxy", "schemeFallback"]),
			settings().get(["server", "reverseProxy", "hostFallback"])
		)

		secret_key = settings().get(["server", "secretKey"])
		if not secret_key:
			import string
			from random import choice
			chars = string.ascii_lowercase + string.ascii_uppercase + string.digits
			secret_key = "".join(choice(chars) for _ in xrange(32))
			settings().set(["server", "secretKey"], secret_key)
			settings().save()
		app.secret_key = secret_key
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

		app.debug = self._debug

		# register API blueprint
		self._setup_blueprints()
		def blueprint_enabled(name, plugin):
			if plugin.implementation is None or not isinstance(plugin.implementation, octoprint.plugin.BlueprintPlugin):
				return
			self._register_blueprint_plugin(plugin.implementation)
		lifecycleManager.add_callback(["enabled"], blueprint_enabled)

		## Tornado initialization starts here

		ioloop = IOLoop()
		ioloop.install()

		self._router = SockJSRouter(self._create_socket_connection, "/sockjs")

		upload_suffixes = dict(name=settings().get(["server", "uploads", "nameSuffix"]), path=settings().get(["server", "uploads", "pathSuffix"]))
		self._tornado_app = Application(self._router.urls + [
			(r"/downloads/timelapse/([^/]*\.mpg)", util.tornado.LargeResponseHandler, dict(path=settings().getBaseFolder("timelapse"), as_attachment=True)),
			(r"/downloads/files/local/([^/]*\.(gco|gcode|g|stl))", util.tornado.LargeResponseHandler, dict(path=settings().getBaseFolder("uploads"), as_attachment=True)),
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
			printer_profile = printerProfileManager.get_default()
			connectionOptions = get_connection_options()
			if port in connectionOptions["ports"]:
				printer.connect(port=port, baudrate=baudrate, profile=printer_profile["id"] if "id" in printer_profile else "_default")

		# start up watchdogs
		observer = Observer()
		observer.schedule(util.watchdog.GcodeWatchdogHandler(fileManager, printer), settings().getBaseFolder("watched"))
		observer.start()

		# run our startup plugins
		octoprint.plugin.call_plugin(octoprint.plugin.StartupPlugin,
		                             "on_startup",
		                             args=(self._host, self._port))

		def call_on_startup(name, plugin):
			implementation = plugin.get_implementation(octoprint.plugin.StartupPlugin)
			if implementation is None:
				return
			implementation.on_startup(self._host, self._port)
		lifecycleManager.add_callback("enabled", call_on_startup)

		# prepare our after startup function
		def on_after_startup():
			self._logger.info("Listening on http://%s:%d" % (self._host, self._port))

			# now this is somewhat ugly, but the issue is the following: startup plugins might want to do things for
			# which they need the server to be already alive (e.g. for being able to resolve urls, such as favicons
			# or service xmls or the like). While they are working though the ioloop would block. Therefore we'll
			# create a single use thread in which to perform our after-startup-tasks, start that and hand back
			# control to the ioloop
			def work():
				octoprint.plugin.call_plugin(octoprint.plugin.StartupPlugin,
				                             "on_after_startup")

				def call_on_after_startup(name, plugin):
					implementation = plugin.get_implementation(octoprint.plugin.StartupPlugin)
					if implementation is None:
						return
					implementation.on_after_startup()
				lifecycleManager.add_callback("enabled", call_on_after_startup)

			import threading
			threading.Thread(target=work).start()
		ioloop.add_callback(on_after_startup)

		# prepare our shutdown function
		def on_shutdown():
			self._logger.info("Goodbye!")
			observer.stop()
			observer.join()
			octoprint.plugin.call_plugin(octoprint.plugin.ShutdownPlugin,
			                             "on_shutdown")
		atexit.register(on_shutdown)

		try:
			ioloop.start()
		except KeyboardInterrupt:
			pass
		except:
			self._logger.fatal("Now that is embarrassing... Something really really went wrong here. Please report this including the stacktrace below in OctoPrint's bugtracker. Thanks!")
			self._logger.exception("Stacktrace follows:")

	def _create_socket_connection(self, session):
		global printer, fileManager, analysisQueue, userManager, eventManager
		return util.sockjs.PrinterStateConnection(printer, fileManager, analysisQueue, userManager, eventManager, pluginManager, session)

	def _check_for_root(self):
		if "geteuid" in dir(os) and os.geteuid() == 0:
			exit("You should not run OctoPrint as root!")

	def _setup_logging(self, debug, logConf=None):
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
				},
				"tornado.application": {
					"level": "ERROR"
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
			logConf = os.path.join(settings().getBaseFolder("base"), "logging.yaml")

		configFromFile = {}
		if os.path.exists(logConf) and os.path.isfile(logConf):
			import yaml
			with open(logConf, "r") as f:
				configFromFile = yaml.safe_load(f)

		config = octoprint.util.dict_merge(defaultConfig, configFromFile)
		logging.config.dictConfig(config)
		logging.captureWarnings(True)

		import warnings
		warnings.simplefilter("always")

		if settings().getBoolean(["serial", "log"]):
			# enable debug logging to serial.log
			logging.getLogger("SERIAL").setLevel(logging.DEBUG)
			logging.getLogger("SERIAL").debug("Enabling serial logging")

	def _setup_jinja2(self):
		app.jinja_env.add_extension("jinja2.ext.do")

		# configure additional template folders for jinja2
		import jinja2
		filesystem_loader = jinja2.FileSystemLoader([])
		filesystem_loader.searchpath = self._template_searchpaths

		jinja_loader = jinja2.ChoiceLoader([
			app.jinja_loader,
			filesystem_loader
		])
		app.jinja_loader = jinja_loader
		del jinja2

		self._register_template_plugins()

	def _register_template_plugins(self):
		template_plugins = pluginManager.get_implementations(octoprint.plugin.TemplatePlugin)
		for plugin in template_plugins:
			self._register_additional_template_plugin(plugin)

	def _register_additional_template_plugin(self, plugin):
		folder = plugin.get_template_folder()
		if folder is not None and not folder in self._template_searchpaths:
			self._template_searchpaths.append(folder)

	def _unregister_additional_template_plugin(self, plugin):
		folder = plugin.get_template_folder()
		if folder is not None and folder in self._template_searchpaths:
			self._template_searchpaths.remove(folder)

	def _setup_blueprints(self):
		from octoprint.server.api import api
		from octoprint.server.apps import apps

		app.register_blueprint(api, url_prefix="/api")
		app.register_blueprint(apps, url_prefix="/apps")

		# also register any blueprints defined in BlueprintPlugins
		self._register_blueprint_plugins()

	def _register_blueprint_plugins(self):
		blueprint_plugins = octoprint.plugin.plugin_manager().get_implementations(octoprint.plugin.BlueprintPlugin)
		for plugin in blueprint_plugins:
			self._register_blueprint_plugin(plugin)

	def _register_blueprint_plugin(self, plugin):
		name = plugin._identifier
		blueprint = plugin.get_blueprint()
		if blueprint is None:
			return

		if plugin.is_blueprint_protected():
			from octoprint.server.util import apiKeyRequestHandler, corsResponseHandler
			blueprint.before_request(apiKeyRequestHandler)
			blueprint.after_request(corsResponseHandler)

		url_prefix = "/plugin/{name}".format(name=name)
		app.register_blueprint(blueprint, url_prefix=url_prefix)

		if self._logger:
			self._logger.debug("Registered API of plugin {name} under URL prefix {url_prefix}".format(name=name, url_prefix=url_prefix))

class LifecycleManager(object):
	def __init__(self, server, plugin_manager):
		self._server = server
		self._plugin_manager = plugin_manager

		self._plugin_lifecycle_callbacks = defaultdict(list)
		self._logger = logging.getLogger(__name__)

		def on_plugin_event_factory(lifecycle_event, text):
			def on_plugin_event(name, plugin):
				self.on_plugin_event(lifecycle_event, name, plugin)
				self._logger.debug(text.format(**locals()))
			return on_plugin_event

		self._plugin_manager.on_plugin_loaded = on_plugin_event_factory("loaded", "Loaded plugin {name}: {plugin}")
		self._plugin_manager.on_plugin_unloaded = on_plugin_event_factory("unloaded", "Unloaded plugin {name}: {plugin}")
		self._plugin_manager.on_plugin_activated = on_plugin_event_factory("activated", "Activated plugin {name}: {plugin}")
		self._plugin_manager.on_plugin_deactivated = on_plugin_event_factory("deactivated", "Deactivated plugin {name}: {plugin}")
		self._plugin_manager.on_plugin_enabled = on_plugin_event_factory("enabled", "Enabled plugin {name}: {plugin}")
		self._plugin_manager.on_plugin_disabled = on_plugin_event_factory("disabled", "Disabled plugin {name}: {plugin}")

	def on_plugin_event(self, event, name, plugin):
		for lifecycle_callback in self._plugin_lifecycle_callbacks[event]:
			lifecycle_callback(name, plugin)

	def add_callback(self, events, callback):
		if isinstance(events, (str, unicode)):
			events = [events]

		for event in events:
			self._plugin_lifecycle_callbacks[event].append(callback)

	def remove_callback(self, callback, events=None):
		if events is None:
			for event in self._plugin_lifecycle_callbacks:
				if callback in self._plugin_lifecycle_callbacks[event]:
					self._plugin_lifecycle_callbacks[event].remove(callback)
		else:
			if isinstance(events, (str, unicode)):
				events = [events]

			for event in events:
				if callback in self._plugin_lifecycle_callbacks[event]:
					self._plugin_lifecycle_callbacks[event].remove(callback)

if __name__ == "__main__":
	server = Server()
	server.run()
