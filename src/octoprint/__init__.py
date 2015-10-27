#!/usr/bin/env python2
# coding=utf-8
from __future__ import absolute_import, print_function

import sys
import logging

#~~ version

from ._version import get_versions
versions = get_versions()

__version__ = versions['version']
__branch__ = versions['branch'] if 'branch' in versions else None
__display_version__ = "{} ({} branch)".format(__version__, __branch__) if __branch__ else __version__

del versions
del get_versions

#~~ sane logging defaults

logging.basicConfig()

#~~ init methods to bring up platform

def init_platform(basedir, configfile, use_logging_file=True, logging_file=None,
                  logging_config=None, debug=False, uncaught_logger=None,
                  uncaught_handler=None, after_settings=None, after_logging=None):
	settings = init_settings(basedir, configfile)
	if callable(after_settings):
		after_settings(settings)

	logger = init_logging(settings,
	                      use_logging_file=use_logging_file,
	                      logging_file=logging_file,
	                      default_config=logging_config,
	                      debug=debug,
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


def init_logging(settings, use_logging_file=True, logging_file=None, default_config=None, debug=False, uncaught_logger=None, uncaught_handler=None):
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
				"tornado.application": {
					"level": "INFO"
				},
				"tornado.general": {
					"level": "INFO"
				}
			},
			"root": {
				"level": "INFO",
				"handlers": ["console", "file"]
			}
		}

	if debug:
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
	warnings.simplefilter("always")

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
