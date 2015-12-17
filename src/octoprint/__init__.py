#!/usr/bin/env python2
# coding=utf-8
from __future__ import absolute_import, print_function

import sys
import logging

#~~ version

from ._version import get_versions
versions = get_versions()

__version__ = versions['version']
__branch__ = versions.get('branch', None)
__display_version__ = "{} ({} branch)".format(__version__, __branch__) if __branch__ else __version__
__revision__ = versions.get('full-revisionid', versions.get('full', None))

del versions
del get_versions

#~~ sane logging defaults

logging.basicConfig()

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

#~~ init methods to bring up platform

def init_platform(basedir, configfile, use_logging_file=True, logging_file=None,
                  logging_config=None, debug=False, verbosity=0, uncaught_logger=None,
                  uncaught_handler=None, after_settings=None, after_logging=None):
	settings = init_settings(basedir, configfile)
	if callable(after_settings):
		after_settings(settings)

	logger = init_logging(settings,
	                      use_logging_file=use_logging_file,
	                      logging_file=logging_file,
	                      default_config=logging_config,
	                      debug=debug,
	                      verbosity=verbosity,
	                      uncaught_logger=uncaught_logger,
	                      uncaught_handler=uncaught_handler)
	if callable(after_logging):
		after_logging(logger)

	plugin_manager = init_pluginsystem(settings)
	return settings, logger, plugin_manager


def init_settings(basedir, configfile):
	"""Inits the settings instance based on basedir and configfile to use."""

	from octoprint.settings import settings
	return settings(init=True, basedir=basedir, configfile=configfile)


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
					"filename": os.path.join(settings.getBaseFolder("logs"), "octoprint.log")
				},
				"serialFile": {
					"class": "logging.handlers.RotatingFileHandler",
					"level": "DEBUG",
					"formatter": "simple",
					"maxBytes": 2 * 1024 * 1024, # let's limit the serial log to 2MB in size
					"filename": os.path.join(settings.getBaseFolder("logs"), "serial.log")
				}
			},
			"loggers": {
				"SERIAL": {
					"level": "CRITICAL",
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
		config = dict_merge(default_config, config_from_file)
	else:
		config = default_config

	# configure logging globally
	import logging.config
	logging.config.dictConfig(config)

	# make sure we log any warnings
	logging.captureWarnings(True)

	import warnings

	categories = (DeprecationWarning, PendingDeprecationWarning)
	if verbosity > 2:
		warnings.simplefilter("always")
	elif debug or verbosity > 0:
		for category in categories:
			warnings.simplefilter("always", category=category)

	# make sure we also log any uncaught exceptions
	if uncaught_logger is None:
		logger = logging.getLogger(__name__)
	else:
		logger = logging.getLogger(uncaught_logger)

	if uncaught_handler is None:
		def exception_logger(exc_type, exc_value, exc_tb):
			logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))
		uncaught_handler = exception_logger
	sys.excepthook = uncaught_handler

	return logger


def init_pluginsystem(settings):
	"""Initializes the plugin manager based on the settings."""
	from octoprint.plugin import plugin_manager
	return plugin_manager(init=True, settings=settings)

#~~ server main method

def main():
	from octoprint.cli import octo
	octo(prog_name="octoprint", auto_envvar_prefix="OCTOPRINT")


if __name__ == "__main__":
	main()
