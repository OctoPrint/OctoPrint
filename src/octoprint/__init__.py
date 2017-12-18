#!/usr/bin/env python2
# coding=utf-8
from __future__ import absolute_import, division, print_function

import sys
import logging as log

#~~ version

from ._version import get_versions
versions = get_versions()

__version__ = versions['version']
__branch__ = versions.get('branch', None)
__display_version__ = __version__
__revision__ = versions.get('full-revisionid', versions.get('full', None))

del versions
del get_versions

#~~ try to ensure a sound SSL environment

urllib3_ssl = True
"""Whether requests/urllib3 and urllib3 (if installed) should be able to establish
   a sound SSL environment or not."""

version_info = sys.version_info
if version_info.major == 2 and version_info.minor <= 7 and version_info.micro < 9:
	try:
		# make sure our requests version of urllib3 is properly patched (if possible)
		import requests.packages.urllib3.contrib.pyopenssl
		requests.packages.urllib3.contrib.pyopenssl.inject_into_urllib3()
	except ImportError:
		urllib3_ssl = False

	try:
		import urllib3

		# only proceed if urllib3 is even installed on its own
		try:
			# urllib3 is there, let's patch that too
			import urllib3.contrib.pyopenssl
			urllib3.contrib.pyopenssl.inject_into_urllib3()
		except ImportError:
			urllib3_ssl = False
	except ImportError:
		pass

del version_info

#~~ custom exceptions

class FatalStartupError(BaseException):
	pass

#~~ init methods to bring up platform

def init_platform(basedir, configfile, use_logging_file=True, logging_file=None,
                  logging_config=None, debug=False, verbosity=0, uncaught_logger=None,
                  uncaught_handler=None, safe_mode=False, ignore_blacklist=False, after_preinit_logging=None,
                  after_settings=None, after_logging=None, after_safe_mode=None,
                  after_event_manager=None, after_connectivity_checker=None,
                  after_plugin_manager=None, after_environment_detector=None):
	kwargs = dict()

	logger, recorder = preinit_logging(debug, verbosity, uncaught_logger, uncaught_handler)
	kwargs["logger"] = logger
	kwargs["recorder"] = recorder

	if callable(after_preinit_logging):
		after_preinit_logging(**kwargs)

	settings = init_settings(basedir, configfile)
	kwargs["settings"] = settings
	if callable(after_settings):
		after_settings(**kwargs)

	logger = init_logging(settings,
	                      use_logging_file=use_logging_file,
	                      logging_file=logging_file,
	                      default_config=logging_config,
	                      debug=debug,
	                      verbosity=verbosity,
	                      uncaught_logger=uncaught_logger,
	                      uncaught_handler=uncaught_handler)
	kwargs["logger"] = logger

	if callable(after_logging):
		after_logging(**kwargs)

	settings_safe_mode = settings.getBoolean(["server", "startOnceInSafeMode"])
	safe_mode = safe_mode or settings_safe_mode
	kwargs["safe_mode"] = safe_mode

	if callable(after_safe_mode):
		after_safe_mode(**kwargs)

	event_manager = init_event_manager(settings)

	kwargs["event_manager"] = event_manager
	if callable(after_event_manager):
		after_event_manager(**kwargs)

	connectivity_checker = init_connectivity_checker(settings, event_manager)

	kwargs["connectivity_checker"] = connectivity_checker
	if callable(after_connectivity_checker):
		after_connectivity_checker(**kwargs)

	plugin_manager = init_pluginsystem(settings,
	                                   safe_mode=safe_mode,
	                                   ignore_blacklist=ignore_blacklist,
	                                   connectivity_checker=connectivity_checker)
	kwargs["plugin_manager"] = plugin_manager

	if callable(after_plugin_manager):
		after_plugin_manager(**kwargs)

	environment_detector = init_environment_detector(plugin_manager)
	kwargs["environment_detector"] = environment_detector

	if callable(after_environment_detector):
		after_environment_detector(**kwargs)

	return settings, logger, safe_mode, event_manager, connectivity_checker, plugin_manager, environment_detector


def init_settings(basedir, configfile):
	"""Inits the settings instance based on basedir and configfile to use."""

	from octoprint.settings import settings, InvalidSettings
	try:
		return settings(init=True, basedir=basedir, configfile=configfile)
	except InvalidSettings as e:
		message = "Error parsing the configuration file, it appears to be invalid YAML."
		if e.line is not None and e.column is not None:
			message += " The parser reported an error on line {}, column {}.".format(e.line, e.column)
		raise FatalStartupError(message)


def preinit_logging(debug=False, verbosity=0, uncaught_logger=None, uncaught_handler=None):
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
			}
		},
		"loggers": {
			"octoprint": {
				"level": "DEBUG" if debug else "INFO"
			},
			"octoprint.util": {
				"level": "INFO"
			}
		},
		"root": {
			"level": "WARN",
			"handlers": ["console"]
		}
	}

	logger = set_logging_config(config, debug, verbosity, uncaught_logger, uncaught_handler)

	from octoprint.logging.handlers import RecordingLogHandler
	recorder = RecordingLogHandler(level=log.DEBUG)
	log.getLogger().addHandler(recorder)

	return logger, recorder


def init_logging(settings, use_logging_file=True, logging_file=None, default_config=None, debug=False, verbosity=0, uncaught_logger=None, uncaught_handler=None):
	"""Sets up logging."""

	import os

	from octoprint.util import dict_merge

	# default logging configuration
	if default_config is None:
		default_config = {
			"version": 1,
			"formatters": {
				"simple": {
					"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
				},
				"serial": {
					"format": "%(asctime)s - %(message)s"
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
					"class": "octoprint.logging.handlers.OctoPrintLogHandler",
					"level": "DEBUG",
					"formatter": "simple",
					"when": "D",
					"backupCount": 6,
					"filename": os.path.join(settings.getBaseFolder("logs"), "octoprint.log")
				},
				"serialFile": {
					"class": "octoprint.logging.handlers.SerialLogHandler",
					"level": "DEBUG",
					"formatter": "serial",
					"backupCount": 3,
					"filename": os.path.join(settings.getBaseFolder("logs"), "serial.log"),
					"delay": True
				}
			},
			"loggers": {
				"SERIAL": {
					"level": "INFO",
					"handlers": ["serialFile"],
					"propagate": False
				},
				"octoprint": {
					"level": "INFO"
				},
				"octoprint.util": {
					"level": "INFO"
				},
				"octoprint.plugins": {
					"level": "INFO"
				}
			},
			"root": {
				"level": "WARN",
				"handlers": ["console", "file"]
			}
		}

	if debug or verbosity > 0:
		default_config["loggers"]["octoprint"]["level"] = "DEBUG"
		default_config["root"]["level"] = "INFO"
	if verbosity > 1:
		default_config["loggers"]["octoprint.plugins"]["level"] = "DEBUG"
	if verbosity > 2:
		default_config["root"]["level"] = "DEBUG"

	config = default_config
	if use_logging_file:
		# further logging configuration from file...
		if logging_file is None:
			logging_file = os.path.join(settings.getBaseFolder("base"), "logging.yaml")

		config_from_file = {}
		if os.path.exists(logging_file) and os.path.isfile(logging_file):
			import yaml
			with open(logging_file, "r") as f:
				config_from_file = yaml.safe_load(f)

		# we merge that with the default config
		if config_from_file is not None and isinstance(config_from_file, dict):
			config = dict_merge(default_config, config_from_file)

	# configure logging globally
	return set_logging_config(config, debug, verbosity, uncaught_logger, uncaught_handler)


def set_logging_config(config, debug, verbosity, uncaught_logger, uncaught_handler):
	# configure logging globally
	import logging.config as logconfig
	logconfig.dictConfig(config)

	# make sure we log any warnings
	log.captureWarnings(True)

	import warnings

	categories = (DeprecationWarning, PendingDeprecationWarning)
	if verbosity > 2:
		warnings.simplefilter("always")
	elif debug or verbosity > 0:
		for category in categories:
			warnings.simplefilter("always", category=category)

	# make sure we also log any uncaught exceptions
	if uncaught_logger is None:
		logger = log.getLogger(__name__)
	else:
		logger = log.getLogger(uncaught_logger)

	if uncaught_handler is None:
		def exception_logger(exc_type, exc_value, exc_tb):
			logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))

		uncaught_handler = exception_logger
	sys.excepthook = uncaught_handler

	return logger


def init_pluginsystem(settings, safe_mode=False, ignore_blacklist=True, connectivity_checker=None):
	"""Initializes the plugin manager based on the settings."""

	import os

	logger = log.getLogger(__name__ + ".startup")

	plugin_folders = [(os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "plugins")), True),
	                  settings.getBaseFolder("plugins")]
	plugin_entry_points = ["octoprint.plugin"]
	plugin_disabled_list = settings.get(["plugins", "_disabled"])

	plugin_blacklist = []
	if not ignore_blacklist and settings.getBoolean(["server", "pluginBlacklist", "enabled"]):
		plugin_blacklist = get_plugin_blacklist(settings, connectivity_checker=connectivity_checker)

	plugin_validators = []
	if safe_mode:
		def validator(phase, plugin_info):
			if phase == "after_load":
				setattr(plugin_info, "safe_mode_victim", not plugin_info.bundled)
				setattr(plugin_info, "safe_mode_enabled", False)
			elif phase == "before_enable":
				if not plugin_info.bundled:
					setattr(plugin_info, "safe_mode_enabled", True)
					return False
			return True
		plugin_validators.append(validator)

	from octoprint.plugin import plugin_manager
	pm = plugin_manager(init=True,
	                    plugin_folders=plugin_folders,
	                    plugin_entry_points=plugin_entry_points,
	                    plugin_disabled_list=plugin_disabled_list,
	                    plugin_blacklist=plugin_blacklist,
	                    plugin_validators=plugin_validators)

	settings_overlays = dict()
	disabled_from_overlays = dict()

	def handle_plugin_loaded(name, plugin):
		if plugin.instance and hasattr(plugin.instance, "__plugin_settings_overlay__"):
			plugin.needs_restart = True

			# plugin has a settings overlay, inject it
			overlay_definition = getattr(plugin.instance, "__plugin_settings_overlay__")
			if isinstance(overlay_definition, (tuple, list)):
				overlay_definition, order = overlay_definition
			else:
				order = None

			overlay = settings.load_overlay(overlay_definition)

			if "plugins" in overlay and "_disabled" in overlay["plugins"]:
				disabled_plugins = overlay["plugins"]["_disabled"]
				del overlay["plugins"]["_disabled"]
				disabled_from_overlays[name] = (disabled_plugins, order)

			settings_overlays[name] = overlay
			logger.debug("Found settings overlay on plugin {}".format(name))

	def handle_plugins_loaded(startup=False, initialize_implementations=True, force_reload=None):
		if not startup:
			return

		sorted_disabled_from_overlays = sorted([(key, value[0], value[1]) for key, value in disabled_from_overlays.items()], key=lambda x: (x[2] is None, x[2], x[0]))

		disabled_list = pm.plugin_disabled_list
		already_processed = []
		for name, addons, _ in sorted_disabled_from_overlays:
			if not name in disabled_list and not name.endswith("disabled"):
				for addon in addons:
					if addon in disabled_list:
						continue

					if addon in already_processed:
						logger.info("Plugin {} wants to disable plugin {}, but that was already processed".format(name, addon))

					if not addon in already_processed and not addon in disabled_list:
						disabled_list.append(addon)
						logger.info("Disabling plugin {} as defined by plugin {}".format(addon, name))
				already_processed.append(name)

	def handle_plugin_enabled(name, plugin):
		if name in settings_overlays:
			settings.add_overlay(settings_overlays[name])
			logger.info("Added settings overlay from plugin {}".format(name))

	pm.on_plugin_loaded = handle_plugin_loaded
	pm.on_plugins_loaded = handle_plugins_loaded
	pm.on_plugin_enabled = handle_plugin_enabled
	pm.reload_plugins(startup=True, initialize_implementations=False)
	return pm


def get_plugin_blacklist(settings, connectivity_checker=None):
	import requests
	import os
	import time
	import yaml

	from octoprint.util import bom_aware_open
	from octoprint.util.version import is_octoprint_compatible

	logger = log.getLogger(__name__ + ".startup")

	if connectivity_checker is not None and not connectivity_checker.online:
		logger.info("We don't appear to be online, not fetching plugin blacklist")
		return []

	def format_blacklist(entries):
		format_entry = lambda x: "{} ({})".format(x[0], x[1]) if isinstance(x, (list, tuple)) and len(x) == 2 \
			else "{} (any)".format(x)
		return ", ".join(map(format_entry, entries))

	def process_blacklist(entries):
		result = []

		if not isinstance(entries, list):
			return result

		for entry in entries:
			if not "plugin" in entry:
				continue

			if "octoversions" in entry and not is_octoprint_compatible(*entry["octoversions"]):
				continue

			if "version" in entry:
				logger.debug("Blacklisted plugin: {}, version: {}".format(entry["plugin"], entry["version"]))
				result.append((entry["plugin"], entry["version"]))
			elif "versions" in entry:
				logger.debug("Blacklisted plugin: {}, versions: {}".format(entry["plugin"], ", ".join(entry["versions"])))
				for version in entry["versions"]:
					result.append((entry["plugin"], version))
			else:
				logger.debug("Blacklisted plugin: {}".format(entry["plugin"]))
				result.append(entry["key"])

		return result

	def fetch_blacklist_from_cache(path, ttl):
		if not os.path.isfile(path):
			return None

		if os.stat(path).st_mtime + ttl < time.time():
			return None

		with bom_aware_open(path, encoding="utf-8", mode="r") as f:
			result = yaml.safe_load(f)

		if isinstance(result, list):
			return result

	def fetch_blacklist_from_url(url, timeout=3, cache=None):
		result = []
		try:
			r = requests.get(url, timeout=timeout)
			result = process_blacklist(r.json())

			if cache is not None:
				try:
					with bom_aware_open(cache, encoding="utf-8", mode="w") as f:
						yaml.safe_dump(result, f)
				except:
					logger.info("Fetched plugin blacklist but couldn't write it to its cache file.")
		except:
			logger.info("Unable to fetch plugin blacklist from {}, proceeding without it.".format(url))
		return result

	try:
		# first attempt to fetch from cache
		cache_path = os.path.join(settings.getBaseFolder("data"), "plugin_blacklist.yaml")
		ttl = settings.getInt(["server", "pluginBlacklist", "ttl"])
		blacklist = fetch_blacklist_from_cache(cache_path, ttl)

		if blacklist is None:
			# no result from the cache, let's fetch it fresh
			url = settings.get(["server", "pluginBlacklist", "url"])
			timeout = settings.getFloat(["server", "pluginBlacklist", "timeout"])
			blacklist = fetch_blacklist_from_url(url, timeout=timeout, cache=cache_path)

		if blacklist is None:
			# still now result, so no blacklist
			blacklist = []

		if blacklist:
			logger.info("Blacklist processing done, "
			            "adding {} blacklisted plugin versions: {}".format(len(blacklist),
			                                                               format_blacklist(blacklist)))
		else:
			logger.info("Blacklist processing done")

		return blacklist
	except:
		logger.exception("Something went wrong while processing the plugin blacklist. Proceeding without it.")


def init_event_manager(settings):
	from octoprint.events import eventManager
	return eventManager()


def init_connectivity_checker(settings, event_manager):
	from octoprint.events import Events
	from octoprint.util import ConnectivityChecker

	# start regular check if we are connected to the internet
	connectivityEnabled = settings.getBoolean(["server", "onlineCheck", "enabled"])
	connectivityInterval = settings.getInt(["server", "onlineCheck", "interval"])
	connectivityHost = settings.get(["server", "onlineCheck", "host"])
	connectivityPort = settings.getInt(["server", "onlineCheck", "port"])

	def on_connectivity_change(old_value, new_value):
		event_manager.fire(Events.CONNECTIVITY_CHANGED, payload=dict(old=old_value, new=new_value))

	connectivityChecker = ConnectivityChecker(connectivityInterval,
	                                          connectivityHost,
	                                          port=connectivityPort,
	                                          enabled=connectivityEnabled,
	                                          on_change=on_connectivity_change)

	return connectivityChecker


def init_environment_detector(plugin_manager):
	from octoprint.environment import EnvironmentDetector
	return EnvironmentDetector(plugin_manager)

#~~ server main method

def main():
	import sys

	# os args are gained differently on win32
	try:
		from click.utils import get_os_args
		args = get_os_args()
	except ImportError:
		# for whatever reason we are running an older Click version?
		args = sys.argv[1:]

	if len(args) >= len(sys.argv):
		# Now some ugly preprocessing of our arguments starts. We have a somewhat difficult situation on our hands
		# here if we are running under Windows and want to be able to handle utf-8 command line parameters (think
		# plugin parameters such as names or something, e.g. for the "dev plugin:new" command) while at the same
		# time also supporting sys.argv rewriting for debuggers etc (e.g. PyCharm).
		#
		# So what we try to do here is solve this... Generally speaking, sys.argv and whatever Windows returns
		# for its CommandLineToArgvW win32 function should have the same length. If it doesn't however and
		# sys.argv is shorter than the win32 specific command line arguments, obviously stuff was cut off from
		# sys.argv which also needs to be cut off of the win32 command line arguments.
		#
		# So this is what we do here.

		# -1 because first entry is the script that was called
		sys_args_length = len(sys.argv) - 1

		# cut off stuff from the beginning
		args = args[-1 * sys_args_length:] if sys_args_length else []

	from octoprint.cli import octo
	octo(args=args, prog_name="octoprint", auto_envvar_prefix="OCTOPRINT")


if __name__ == "__main__":
	main()
