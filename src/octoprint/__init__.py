#!/usr/bin/env python2
# coding=utf-8
from __future__ import absolute_import, print_function

import sys
import click

from octoprint.daemon import Daemon
from octoprint.server import Server

#~~ version

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions


def init_platform(basedir, configfile, use_logging_file=True, logging_file=None,
                  logging_config=None, debug=False, uncaught_logger=None,
                  uncaught_handler=None):
	settings = init_settings(basedir, configfile)
	logger = init_logging(settings,
	                      use_logging_file=use_logging_file,
	                      logging_file=logging_file,
	                      default_config=logging_config,
	                      debug=debug,
	                      uncaught_logger=uncaught_logger,
	                      uncaught_handler=uncaught_handler)
	plugin_manager = init_pluginsystem(settings)
	return settings, logger, plugin_manager


def init_settings(basedir, configfile):
	from octoprint.settings import settings
	return settings(init=True, basedir=basedir, configfile=configfile)


def init_logging(settings, use_logging_file=True, logging_file=None, default_config=None, debug=False, uncaught_logger=None, uncaught_handler=None):
	import logging
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
		if logging_file is None:
			logging_file = os.path.join(settings.getBaseFolder("base"), "logging.yaml")

		config_from_file = {}
		if os.path.exists(logging_file) and os.path.isfile(logging_file):
			import yaml
			with open(logging_file, "r") as f:
				config_from_file = yaml.safe_load(f)

		config = dict_merge(default_config, config_from_file)
	else:
		config = default_config

	logging.config.dictConfig(config)
	logging.captureWarnings(True)

	import warnings
	warnings.simplefilter("always")

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
	from octoprint.plugin import plugin_manager
	return plugin_manager(init=True, settings=settings)

#~~ Custom click option to hide from help

class HiddenOption(click.Option):
	def get_help_record(self, ctx):
		pass

def hidden_option(*param_decls, **attrs):
	"""Attaches a hidden option to the command.  All positional arguments are
	passed as parameter declarations to :class:`Option`; all keyword
	arguments are forwarded unchanged.  This is equivalent to creating an
	:class:`Option` instance manually and attaching it to the
	:attr:`Command.params` list.
	"""

	import inspect
	from click.decorators import _param_memo

	def decorator(f):
		if 'help' in attrs:
			attrs['help'] = inspect.cleandoc(attrs['help'])
		_param_memo(f, HiddenOption(param_decls, **attrs))
		return f
	return decorator


#~~ daemon class

class OctoPrintDaemon(Daemon):
	def __init__(self, pidfile, basedir, configfile, host, port, debug, allow_root, logging_config):
		Daemon.__init__(self, pidfile)

		self._basedir = basedir
		self._configfile = configfile
		self._host = host
		self._port = port
		self._debug = debug
		self._allow_root = allow_root
		self._logging_config = logging_config

	def run(self):
		run_server(self._basedir, self._configfile, self._host, self._port, self._debug, self._allow_root, self._logging_config)

#~~ serve method

def run_server(basedir, configfile, host, port, debug, allow_root, logging_config):
	settings, _, plugin_manager = init_platform(basedir,
	                                            configfile,
	                                            logging_file=logging_config,
	                                            debug=debug,
	                                            uncaught_logger=__name__)

	octoprint = Server(settings=settings, plugin_manager=plugin_manager, host=host, port=port, debug=debug, allow_root=allow_root)
	octoprint.run()


@click.group(name="octoprint", invoke_without_command=True)
@click.option("--basedir", "-b", type=click.Path(),
              help="Specify the basedir to use for uploads, timelapses etc.")
@click.option("--config", "-c", "configfile", type=click.Path(),
              help="Specify the config file to use.")
@hidden_option("--debug", "-d", is_flag=True)
@hidden_option("--host", type=click.STRING)
@hidden_option("--port", type=click.INT)
@hidden_option("--logging", type=click.Path())
@hidden_option("--daemon", type=click.Choice(["start", "stop", "restart"]))
@hidden_option("--pid", type=click.Path())
@hidden_option("--iknowwhatimdoing", "allow_root", is_flag=True)
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx, debug, host, port, basedir, configfile, logging, daemon, pid, allow_root):
	class ContextObject(object):
		def __init__(self):
			self.debug = False
			self.configfile = None
			self.basedir = None
			self.allow_root = None

	obj = ContextObject()
	obj.debug = debug
	obj.configfile = configfile
	obj.basedir = basedir
	obj.allow_root = allow_root

	ctx.obj = obj

	if ctx.invoked_subcommand is None:
		if daemon:
			click.echo("Daemon operation via \"octoprint --daemon "
			           "(start|stop|restart)\" is deprecated, please use "
			           "\"octoprint daemon start|stop|restart\" from now on")

			ctx.invoke(daemon_command, pid=pid, daemon=daemon)
		else:
			click.echo("Starting the server via \"octoprint\" is deprecated, "
			           "please use \"octoprint serve\" from now on.")

			ctx.invoke(serve_command, host=host, port=port, logging=logging)


@cli.command(name="serve")
@click.option("--host", type=click.STRING,
              help="Specify the host on which to bind the server.")
@click.option("--port", type=click.INT,
              help="Specify the port on which to bind the server.")
@click.option("--logging", type=click.Path(),
              help="Specify the config file to use for configuring logging.")
@click.option("--debug", "-d", is_flag=True,
              help="Enable debug mode.")
@click.option("--iknowwhatimdoing", "allow_root", is_flag=True,
              help="Allow OctoPrint to run as user root.")
@click.pass_context
def serve_command(ctx, host, port, logging, debug, allow_root):
	"""Starts the OctoPrint server."""
	run_server(ctx.obj.basedir, ctx.obj.configfile, host, port, debug,
	           allow_root, logging)


@cli.command(name="daemon")
@click.option("--pid", type=click.Path(),
              help="Pidfile to use for daemonizing.")
@click.option("--host", type=click.STRING,
              help="Specify the host on which to bind the server.")
@click.option("--port", type=click.INT,
              help="Specify the port on which to bind the server.")
@click.option("--logging", type=click.Path(),
              help="Specify the config file to use for configuring logging.")
@click.option("--debug", "-d", is_flag=True,
              help="Enable debug mode")
@click.option("--iknowwhatimdoing", "allow_root", is_flag=True,
              help="Allow OctoPrint to run as user root.")
@click.argument("command", type=click.Choice(["start", "stop", "restart"]),
                metavar="start|stop|restart")
@click.pass_context
def daemon_command(ctx, pid, host, port, logging, debug, allow_root, command):
	"""
	Starts, stops or restarts in daemon mode.

	Please note that daemon mode is only supported under Linux right now.
	"""
	if sys.platform == "darwin" or sys.platform == "win32":
		click.echo("Sorry, daemon mode is only supported under Linux right now",
		           file=sys.stderr)
		sys.exit(2)

	daemon = OctoPrintDaemon(pid, ctx.obj.basedir, ctx.obj.configfile,
	              host, port, debug, allow_root, logging)

	if command == "start":
		daemon.start()
	elif command == "stop":
		daemon.stop()
	elif command == "restart":
		daemon.restart()


def main():
	cli.main(prog_name="octoprint", auto_envvar_prefix="OCTOPRINT")


if __name__ == "__main__":
	main()
