# coding=utf-8
from __future__ import absolute_import

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


import click
import logging
import sys

from octoprint.cli import pass_octoprint_ctx, bulk_options, standard_options

def run_server(basedir, configfile, host, port, debug, allow_root, logging_config, verbosity):
	"""Initializes the environment and starts up the server."""

	from octoprint import init_platform, __display_version__

	def log_startup(_):
		logging.getLogger("octoprint.server").info("Starting OctoPrint {}".format(__display_version__))

		from octoprint import urllib3_ssl
		if not urllib3_ssl:
			logging.getLogger("octoprint.server")\
				.warn("requests/urllib3 will run in an insecure SSL environment. "
			          "You might see corresponding warnings logged later "
			          "(\"InsecurePlatformWarning\"). It is recommended to either "
			          "update to a Python version >= 2.7.9 or alternatively "
			          "install PyOpenSSL plus its dependencies. For details see "
			          "https://urllib3.readthedocs.org/en/latest/security.html#openssl-pyopenssl")

	settings, _, plugin_manager = init_platform(basedir,
	                                            configfile,
	                                            logging_file=logging_config,
	                                            debug=debug,
	                                            verbosity=verbosity,
	                                            uncaught_logger=__name__,
	                                            after_logging=log_startup)

	from octoprint.server import Server
	octoprint_server = Server(settings=settings, plugin_manager=plugin_manager, host=host, port=port, debug=debug, allow_root=allow_root)
	octoprint_server.run()

#~~ server options

server_options = bulk_options([
	click.option("--host", type=click.STRING,
	             help="Specify the host on which to bind the server."),
	click.option("--port", type=click.INT,
	             help="Specify the port on which to bind the server."),
	click.option("--logging", type=click.Path(),
	             help="Specify the config file to use for configuring logging."),
	click.option("--iknowwhatimdoing", "allow_root", is_flag=True,
	             help="Allow OctoPrint to run as user root."),
	click.option("--debug", is_flag=True, help="Enable debug mode"),
])
"""Decorator to add the options shared among the server commands: ``--host``, ``--port``,
   ``--logging``, ``--iknowwhatimdoing`` and ``--debug``."""

#~~ "octoprint serve" and "octoprint daemon" commands

@click.group()
@pass_octoprint_ctx
def server_commands(obj):
	pass


@server_commands.command(name="serve")
@server_options
@standard_options(hidden=True)
@pass_octoprint_ctx
def serve_command(obj, host, port, logging, allow_root, debug):
	"""Starts the OctoPrint server."""
	run_server(obj.basedir, obj.configfile, host, port, debug,
	           allow_root, logging, obj.verbosity)


@server_commands.command(name="daemon")
@click.option("--pid", type=click.Path(), default="/tmp/octoprint.pid",
              help="Pidfile to use for daemonizing.")
@server_options
@standard_options(hidden=True)
@click.argument("command", type=click.Choice(["start", "stop", "restart", "status"]),
                metavar="start|stop|restart|status")
@pass_octoprint_ctx
def daemon_command(octoprint_ctx, pid, host, port, logging, allow_root, debug, command):
	"""
	Starts, stops or restarts in daemon mode.

	Please note that daemon mode is only supported under Linux right now.
	"""
	if sys.platform == "darwin" or sys.platform == "win32":
		click.echo("Sorry, daemon mode is only supported under Linux right now",
		           file=sys.stderr)
		sys.exit(2)

	if pid is None:
		click.echo("No path to a pidfile set",
		           file=sys.stderr)
		sys.exit(1)

	from octoprint.daemon import Daemon
	class OctoPrintDaemon(Daemon):
		def __init__(self, pidfile, basedir, configfile, host, port, debug, allow_root, logging_config, verbosity):
			Daemon.__init__(self, pidfile)

			self._basedir = basedir
			self._configfile = configfile
			self._host = host
			self._port = port
			self._debug = debug
			self._allow_root = allow_root
			self._logging_config = logging_config
			self._verbosity = verbosity

		def run(self):
			run_server(self._basedir, self._configfile, self._host, self._port, self._debug, self._allow_root, self._logging_config, self._verbosity)

	octoprint_daemon = OctoPrintDaemon(pid, octoprint_ctx.basedir, octoprint_ctx.configfile,
	                                   host, port, debug, allow_root, logging, octoprint_ctx.verbosity)

	if command == "start":
		octoprint_daemon.start()
	elif command == "stop":
		octoprint_daemon.stop()
	elif command == "restart":
		octoprint_daemon.restart()
	elif command == "status":
		octoprint_daemon.status()


