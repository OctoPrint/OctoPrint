# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


import logging
import sys

import click

from octoprint.cli import (
    bulk_options,
    get_ctx_obj_option,
    set_ctx_obj_option,
    standard_options,
)

click.disable_unicode_literals_warning = True


def run_server(
    basedir,
    configfile,
    host,
    port,
    v6_only,
    debug,
    allow_root,
    logging_config,
    verbosity,
    safe_mode,
    ignore_blacklist,
    octoprint_daemon=None,
):
    """Initializes the environment and starts up the server."""

    from octoprint import FatalStartupError, __display_version__, init_platform

    def log_startup(recorder=None, safe_mode=None, **kwargs):
        from octoprint.logging import get_divider_line
        from octoprint.logging.handlers import PluginTimingsLogHandler

        logger = logging.getLogger("octoprint.startup")
        PluginTimingsLogHandler.arm_rollover()

        logger.info(get_divider_line("*"))
        logger.info("Starting OctoPrint {}".format(__display_version__))
        if safe_mode:
            logger.info("Starting in SAFE MODE. Third party plugins will be disabled!")
            if safe_mode == "flag":
                reason = "command line flag"
            elif safe_mode == "settings":
                reason = "setting in config.yaml"
            elif safe_mode == "incomplete_startup":
                reason = "problem during last startup"
            else:
                reason = "unknown"
            logger.info("Reason for safe mode: {}".format(reason))

        if recorder and len(recorder):
            logger.info(get_divider_line("-", "Logged during platform initialization:"))

            from octoprint.logging.handlers import CombinedLogHandler

            handler = CombinedLogHandler(*logging.getLogger().handlers)
            recorder.setTarget(handler)
            recorder.flush()

            logger.info(get_divider_line("-"))

        from octoprint import urllib3_ssl

        if not urllib3_ssl:
            logging.getLogger("octoprint.server").warning(
                "requests/urllib3 will run in an insecure SSL environment. "
                "You might see corresponding warnings logged later "
                '("InsecurePlatformWarning"). It is recommended to either '
                "update to a Python version >= 2.7.9 or alternatively "
                "install PyOpenSSL plus its dependencies. For details see "
                "https://urllib3.readthedocs.org/en/latest/security.html#openssl-pyopenssl"
            )
        logger.info(get_divider_line("*"))

    def log_register_rollover(
        safe_mode=None, plugin_manager=None, environment_detector=None, **kwargs
    ):
        from octoprint.logging import get_divider_line, get_handler, log_to_handler
        from octoprint.logging.handlers import OctoPrintLogHandler

        def rollover_callback():
            handler = get_handler("file")
            if handler is None:
                return

            logger = logging.getLogger("octoprint.server")

            def _log(message, level=logging.INFO):
                log_to_handler(logger, handler, level, message)

            _log(get_divider_line("-", "Log roll over detected"))
            _log("OctoPrint {}".format(__display_version__))
            if safe_mode:
                _log("SAFE MODE is active. Third party plugins are disabled!")
            plugin_manager.log_all_plugins(only_to_handler=handler)
            environment_detector.log_detected_environment(only_to_handler=handler)
            _log(get_divider_line("-"))

        OctoPrintLogHandler.registerRolloverCallback(rollover_callback)

    try:
        components = init_platform(
            basedir,
            configfile,
            logging_file=logging_config,
            debug=debug,
            verbosity=verbosity,
            uncaught_logger=__name__,
            safe_mode=safe_mode,
            ignore_blacklist=ignore_blacklist,
            after_safe_mode=log_startup,
            after_environment_detector=log_register_rollover,
        )
        (
            settings,
            _,
            safe_mode,
            event_manager,
            connectivity_checker,
            plugin_manager,
            environment_detector,
        ) = components

    except FatalStartupError as e:
        logger = logging.getLogger("octoprint.startup").fatal
        echo = lambda x: click.echo(x, err=True)

        for method in logger, echo:
            method(str(e))
            method("There was a fatal error starting up OctoPrint.")

    else:
        from octoprint.server import Server

        octoprint_server = Server(
            settings=settings,
            plugin_manager=plugin_manager,
            event_manager=event_manager,
            connectivity_checker=connectivity_checker,
            environment_detector=environment_detector,
            host=host,
            port=port,
            v6_only=v6_only,
            debug=debug,
            safe_mode=safe_mode,
            allow_root=allow_root,
            octoprint_daemon=octoprint_daemon,
        )
        octoprint_server.run()


# ~~ server options

server_options = bulk_options(
    [
        click.option(
            "--host",
            type=click.STRING,
            callback=set_ctx_obj_option,
            help="Specify the host address on which to bind the server.",
        ),
        click.option(
            "--port",
            type=click.INT,
            callback=set_ctx_obj_option,
            help="Specify the port on which to bind the server.",
        ),
        click.option(
            "-4",
            "--ipv4",
            "v4",
            is_flag=True,
            callback=set_ctx_obj_option,
            help="Bind to IPv4 addresses only. Implies '--host 0.0.0.0'. Silently ignored if -6 is present.",
        ),
        click.option(
            "-6",
            "--ipv6",
            "v6",
            is_flag=True,
            callback=set_ctx_obj_option,
            help="Bind to IPv6 addresses only. Disables dual stack when binding to any v6 addresses. Silently ignored if -4 is present.",
        ),
        click.option(
            "--logging",
            type=click.Path(),
            callback=set_ctx_obj_option,
            help="Specify the config file to use for configuring logging.",
        ),
        click.option(
            "--iknowwhatimdoing",
            "allow_root",
            is_flag=True,
            callback=set_ctx_obj_option,
            help="Allow OctoPrint to run as user root.",
        ),
        click.option(
            "--debug",
            is_flag=True,
            callback=set_ctx_obj_option,
            help="Enable debug mode.",
        ),
        click.option(
            "--ignore-blacklist",
            "ignore_blacklist",
            is_flag=True,
            callback=set_ctx_obj_option,
            help="Disable processing of the plugin blacklist.",
        ),
    ]
)
"""Decorator to add the options shared among the server commands: ``--host``, ``--port``, ``-4``, ``-6``
   ``--logging``, ``--iknowwhatimdoing`` and ``--debug``."""

daemon_options = bulk_options(
    [
        click.option(
            "--pid",
            type=click.Path(),
            default="/tmp/octoprint.pid",
            callback=set_ctx_obj_option,
            help="Pidfile to use for daemonizing.",
        )
    ]
)
"""Decorator to add the options for the daemon subcommand: ``--pid``."""

# ~~ "octoprint serve" and "octoprint daemon" commands


@click.group()
def server_commands():
    pass


@server_commands.command(name="safemode")
@standard_options()
@click.pass_context
def enable_safemode(ctx, **kwargs):
    """Sets the safe mode flag for the next start."""
    from octoprint import FatalStartupError, init_settings

    logging.basicConfig(
        level=logging.DEBUG
        if get_ctx_obj_option(ctx, "verbosity", 0) > 0
        else logging.WARN
    )
    try:
        settings = init_settings(
            get_ctx_obj_option(ctx, "basedir", None),
            get_ctx_obj_option(ctx, "configfile", None),
        )
    except FatalStartupError as e:
        click.echo(str(e), err=True)
        click.echo("There was a fatal error initializing the settings manager.", err=True)
        ctx.exit(-1)
    else:
        settings.setBoolean(["server", "startOnceInSafeMode"], True)
        settings.save()

        click.echo(
            "Safe mode flag set, OctoPrint will start in safe mode on next restart."
        )


@server_commands.command(name="serve")
@standard_options()
@server_options
@click.pass_context
def serve_command(ctx, **kwargs):
    """Starts the OctoPrint server."""

    def get_value(key):
        return get_ctx_obj_option(ctx, key, kwargs.get(key))

    host = get_value("host")
    port = get_value("port")
    v4 = get_value("v4")
    v6 = get_value("v6")
    logging = get_value("logging")
    allow_root = get_value("allow_root")
    debug = get_value("debug")

    basedir = get_value("basedir")
    configfile = get_value("configfile")
    verbosity = get_value("verbosity")
    safe_mode = "flag" if get_value("safe_mode") else None
    ignore_blacklist = get_value("ignore_blacklist")

    if v4 and not host:
        host = "0.0.0.0"

    run_server(
        basedir,
        configfile,
        host,
        port,
        v6,
        debug,
        allow_root,
        logging,
        verbosity,
        safe_mode,
        ignore_blacklist,
    )


if sys.platform != "win32" and sys.platform != "darwin":
    # we do not support daemon mode under windows or macosx

    @server_commands.command(name="daemon")
    @standard_options()
    @server_options
    @daemon_options
    @click.argument(
        "command",
        type=click.Choice(["start", "stop", "restart", "status"]),
        metavar="start|stop|restart|status",
    )
    @click.pass_context
    def daemon_command(ctx, command, **kwargs):
        """
        Starts, stops or restarts in daemon mode.

        Please note that daemon mode is not supported under Windows and MacOSX right now.
        """

        def get_value(key):
            return get_ctx_obj_option(ctx, key, kwargs.get(key))

        host = get_value("host")
        port = get_value("port")
        v4 = get_value("v4")
        v6 = get_value("v6")
        logging = get_value("logging")
        allow_root = get_value("allow_root")
        debug = get_value("debug")
        pid = get_value("pid")

        basedir = get_value("basedir")
        configfile = get_value("configfile")
        verbosity = get_value("verbosity")
        safe_mode = "flag" if get_value("safe_mode") else None
        ignore_blacklist = get_value("ignore_blacklist")

        if v4 and not host:
            host = "0.0.0.0"

        if pid is None:
            click.echo("No path to a pidfile set", file=sys.stderr)
            sys.exit(1)

        from octoprint.daemon import Daemon

        class OctoPrintDaemon(Daemon):
            def __init__(
                self,
                pidfile,
                basedir,
                configfile,
                host,
                port,
                v6_only,
                debug,
                allow_root,
                logging_config,
                verbosity,
                safe_mode,
                ignore_blacklist,
            ):
                Daemon.__init__(self, pidfile)

                self._basedir = basedir
                self._configfile = configfile
                self._host = host
                self._port = port
                self._v6_only = v6_only
                self._debug = debug
                self._allow_root = allow_root
                self._logging_config = logging_config
                self._verbosity = verbosity
                self._safe_mode = safe_mode
                self._ignore_blacklist = ignore_blacklist

            def run(self):
                run_server(
                    self._basedir,
                    self._configfile,
                    self._host,
                    self._port,
                    self._v6_only,
                    self._debug,
                    self._allow_root,
                    self._logging_config,
                    self._verbosity,
                    self._safe_mode,
                    self._ignore_blacklist,
                    octoprint_daemon=self,
                )

        octoprint_daemon = OctoPrintDaemon(
            pid,
            basedir,
            configfile,
            host,
            port,
            v6,
            debug,
            allow_root,
            logging,
            verbosity,
            safe_mode,
            ignore_blacklist,
        )

        if command == "start":
            octoprint_daemon.start()
        elif command == "stop":
            octoprint_daemon.stop()
        elif command == "restart":
            octoprint_daemon.restart()
        elif command == "status":
            octoprint_daemon.status()
