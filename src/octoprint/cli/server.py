# coding=utf-8
from __future__ import absolute_import, division, print_function

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


import click
import logging
import sys

from octoprint.cli import bulk_options, standard_options, set_ctx_obj_option, get_ctx_obj_option

def run_server(basedir, configfile, host, port, debug, allow_root, logging_config, verbosity, safe_mode, octoprint_daemon=None):
	"""Initializes the environment and starts up the server."""

	from octoprint import init_platform, __display_version__, FatalStartupError

	def log_startup(recorder=None, safe_mode=None, **kwargs):
		logger = logging.getLogger("octoprint.server")
		logger.info("Starting OctoPrint {}".format(__display_version__))
		if safe_mode:
			logger.info("Starting in SAFE MODE. Third party plugins will be disabled!")

		if recorder and len(recorder):
			logger.info("--- Logged during platform initialization: ---")

			from octoprint.logging.handlers import CombinedLogHandler
			handler = CombinedLogHandler(*logging.getLogger().handlers)
			recorder.setTarget(handler)
			recorder.flush()

			logger.info("----------------------------------------------")

		from octoprint import urllib3_ssl
		if not urllib3_ssl:
			logging.getLogger("octoprint.server")\
				.warn("requests/urllib3 will run in an insecure SSL environment. "
			          "You might see corresponding warnings logged later "
			          "(\"InsecurePlatformWarning\"). It is recommended to either "
			          "update to a Python version >= 2.7.9 or alternatively "
			          "install PyOpenSSL plus its dependencies. For details see "
			          "https://urllib3.readthedocs.org/en/latest/security.html#openssl-pyopenssl")

	try:
		settings, _, safe_mode, plugin_manager = init_platform(basedir,
		                                                       configfile,
		                                                       logging_file=logging_config,
		                                                       debug=debug,
		                                                       verbosity=verbosity,
		                                                       uncaught_logger=__name__,
		                                                       safe_mode=safe_mode,
		                                                       after_safe_mode=log_startup)
	except FatalStartupError as e:
		click.echo(e.message, err=True)
		click.echo("There was a fatal error starting up OctoPrint.", err=True)
	else:
		from octoprint.server import Server
		octoprint_server = Server(settings=settings,
		                          plugin_manager=plugin_manager,
		                          host=host,
		                          port=port,
		                          debug=debug,
		                          safe_mode=safe_mode,
		                          allow_root=allow_root,
		                          octoprint_daemon=octoprint_daemon)
		octoprint_server.run()

#~~ server options

server_options = bulk_options([
	click.option("--host", type=click.STRING, callback=set_ctx_obj_option,
	             help="Specify the host on which to bind the server."),
	click.option("--port", type=click.INT, callback=set_ctx_obj_option,
	             help="Specify the port on which to bind the server."),
	click.option("--logging", type=click.Path(), callback=set_ctx_obj_option,
	             help="Specify the config file to use for configuring logging."),
	click.option("--iknowwhatimdoing", "allow_root", is_flag=True, callback=set_ctx_obj_option,
	             help="Allow OctoPrint to run as user root."),
	click.option("--debug", is_flag=True, callback=set_ctx_obj_option,
	             help="Enable debug mode.")
])
"""Decorator to add the options shared among the server commands: ``--host``, ``--port``,
   ``--logging``, ``--iknowwhatimdoing`` and ``--debug``."""

daemon_options = bulk_options([
	click.option("--pid", type=click.Path(), default="/tmp/octoprint.pid", callback=set_ctx_obj_option,
	             help="Pidfile to use for daemonizing.")
])
"""Decorator to add the options for the daemon subcommand: ``--pid``."""

#~~ "octoprint serve" and "octoprint daemon" commands

@click.group()
def server_commands():
	pass


@server_commands.command(name="serve")
@server_options
@standard_options(hidden=True)
@click.pass_context
def serve_command(ctx, **kwargs):
	"""Starts the OctoPrint server."""

	def get_value(key):
		return get_ctx_obj_option(ctx, key, kwargs.get(key))

	host = get_value("host")
	port = get_value("port")
	logging = get_value("logging")
	allow_root = get_value("allow_root")
	debug = get_value("debug")

	basedir = get_value("basedir")
	configfile = get_value("configfile")
	verbosity = get_value("verbosity")
	safe_mode = get_value("safe_mode")

	run_server(basedir, configfile, host, port, debug,
	           allow_root, logging, verbosity, safe_mode)


if sys.platform == "linux2":
	# we only support daemon mode under Linux

	@server_commands.command(name="daemon")
	@server_options
	@daemon_options
	@standard_options(hidden=True)
	@click.argument("command", type=click.Choice(["start", "stop", "restart", "status"]),
	                metavar="start|stop|restart|status")
	@click.pass_context
	def daemon_command(ctx, command, **kwargs):
		"""
		Starts, stops or restarts in daemon mode.

		Please note that daemon mode is only supported under Linux right now.
		"""

		def get_value(key):
			return get_ctx_obj_option(ctx, key, kwargs.get(key))

		host = get_value("host")
		port = get_value("port")
		logging = get_value("logging")
		allow_root = get_value("allow_root")
		debug = get_value("debug")
		pid = get_value("pid")

		basedir = get_value("basedir")
		configfile = get_value("configfile")
		verbosity = get_value("verbosity")
		safe_mode = get_value("safe_mode")

		if pid is None:
			click.echo("No path to a pidfile set",
			           file=sys.stderr)
			sys.exit(1)

		from octoprint.daemon import Daemon
		class OctoPrintDaemon(Daemon):
			def __init__(self, pidfile, basedir, configfile, host, port, debug, allow_root, logging_config, verbosity, safe_mode):
				Daemon.__init__(self, pidfile)

				self._basedir = basedir
				self._configfile = configfile
				self._host = host
				self._port = port
				self._debug = debug
				self._allow_root = allow_root
				self._logging_config = logging_config
				self._verbosity = verbosity
				self._safe_mode = safe_mode

			def run(self):
				run_server(self._basedir, self._configfile, self._host, self._port, self._debug,
				           self._allow_root, self._logging_config, self._verbosity, self._safe_mode,
				           octoprint_daemon=self)

		octoprint_daemon = OctoPrintDaemon(pid, basedir, configfile, host, port, debug, allow_root, logging, verbosity,
		                                   safe_mode)

		if command == "start":
			octoprint_daemon.start()
		elif command == "stop":
			octoprint_daemon.stop()
		elif command == "restart":
			octoprint_daemon.restart()
		elif command == "status":
			octoprint_daemon.status()


