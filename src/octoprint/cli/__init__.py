# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


import sys

import click

import octoprint

click.disable_unicode_literals_warning = True


# ~~ click context


class OctoPrintContext(object):
    """Custom context wrapping the standard options."""

    def __init__(self, configfile=None, basedir=None, verbosity=0, safe_mode=False):
        self.configfile = configfile
        self.basedir = basedir
        self.verbosity = verbosity
        self.safe_mode = safe_mode


pass_octoprint_ctx = click.make_pass_decorator(OctoPrintContext, ensure=True)
"""Decorator to pass in the :class:`OctoPrintContext` instance."""

# ~~ Basic CLI initialization for plugins


def init_platform_for_cli(ctx):
    """
    Performs a basic platform initialization for the CLI.

    Plugin implementations will be initialized, but only with a subset of the usual
    property injections:

       * _identifier and everything else parsed from metadata
       * _logger
       * _connectivity_checker
       * _environment_detector
       * _event_bus
       * _plugin_manager
       * _settings

    Returns: the same list of components as returned by ``init_platform``
    """

    from octoprint import (
        init_custom_events,
        init_platform,
        init_settings_plugin_config_migration_and_cleanup,
    )
    from octoprint import octoprint_plugin_inject_factory as opif
    from octoprint import settings_plugin_inject_factory as spif

    components = init_platform(
        get_ctx_obj_option(ctx, "basedir", None),
        get_ctx_obj_option(ctx, "configfile", None),
        safe_mode=True,
    )

    (
        settings,
        logger,
        safe_mode,
        event_manager,
        connectivity_checker,
        plugin_manager,
        environment_detector,
    ) = components

    init_custom_events(plugin_manager)
    octoprint_plugin_inject_factory = opif(
        settings,
        {
            "plugin_manager": plugin_manager,
            "event_bus": event_manager,
            "connectivity_checker": connectivity_checker,
            "environment_detector": environment_detector,
        },
    )
    settings_plugin_inject_factory = spif(settings)

    plugin_manager.implementation_inject_factories = [
        octoprint_plugin_inject_factory,
        settings_plugin_inject_factory,
    ]
    plugin_manager.initialize_implementations()

    init_settings_plugin_config_migration_and_cleanup(plugin_manager)

    return components


# ~~ Custom click option to hide from help


class HiddenOption(click.Option):
    """Custom option sub class with empty help."""

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
        if "help" in attrs:
            attrs["help"] = inspect.cleandoc(attrs["help"])
        _param_memo(f, HiddenOption(param_decls, **attrs))
        return f

    return decorator


# ~~ helper for setting context options


def set_ctx_obj_option(ctx, param, value):
    """Helper for setting eager options on the context."""
    if ctx.obj is None:
        ctx.obj = OctoPrintContext()
    if value != param.default:
        setattr(ctx.obj, param.name, value)
    elif param.default is not None:
        setattr(ctx.obj, param.name, param.default)


# ~~ helper for retrieving context options


def get_ctx_obj_option(ctx, key, default, include_parents=True):
    if include_parents and hasattr(ctx, "parent") and ctx.parent:
        fallback = get_ctx_obj_option(ctx.parent, key, default)
    else:
        fallback = default
    return getattr(ctx.obj, key, fallback)


# ~~ helper for setting a lot of bulk options


def bulk_options(options):
    """
    Utility decorator to decorate a function with a list of click decorators.

    The provided list of ``options`` will be reversed to ensure correct
    processing order (inverse from what would be intuitive).
    """

    def decorator(f):
        options.reverse()
        for option in options:
            option(f)
        return f

    return decorator


# ~~ helper for setting --basedir, --config and --verbose options


def standard_options(hidden=False):
    """
    Decorator to add the standard options shared among all "octoprint" commands.

    Adds the options ``--basedir``, ``--config`` and ``--verbose``. If ``hidden``
    is set to ``True``, the options will be available on the command but not
    listed in its help page.
    """

    factory = click.option
    if hidden:
        factory = hidden_option

    options = [
        factory(
            "--basedir",
            "-b",
            type=click.Path(),
            callback=set_ctx_obj_option,
            is_eager=True,
            expose_value=False,
            help="Specify the basedir to use for configs, uploads, timelapses etc.",
        ),
        factory(
            "--config",
            "-c",
            "configfile",
            type=click.Path(),
            callback=set_ctx_obj_option,
            is_eager=True,
            expose_value=False,
            help="Specify the config file to use.",
        ),
        factory(
            "--verbose",
            "-v",
            "verbosity",
            count=True,
            callback=set_ctx_obj_option,
            is_eager=True,
            expose_value=False,
            help="Increase logging verbosity.",
        ),
        factory(
            "--safe",
            "safe_mode",
            is_flag=True,
            callback=set_ctx_obj_option,
            is_eager=True,
            expose_value=False,
            help="Enable safe mode; disables all third party plugins.",
        ),
    ]

    return bulk_options(options)


# ~~ helper for settings legacy options we still have to support on "octoprint"

legacy_options = bulk_options(
    [
        hidden_option("--host", type=click.STRING, callback=set_ctx_obj_option),
        hidden_option("--port", type=click.INT, callback=set_ctx_obj_option),
        hidden_option("--logging", type=click.Path(), callback=set_ctx_obj_option),
        hidden_option("--debug", "-d", is_flag=True, callback=set_ctx_obj_option),
        hidden_option(
            "--daemon",
            type=click.Choice(["start", "stop", "restart"]),
            callback=set_ctx_obj_option,
        ),
        hidden_option(
            "--pid",
            type=click.Path(),
            default="/tmp/octoprint.pid",
            callback=set_ctx_obj_option,
        ),
        hidden_option(
            "--iknowwhatimdoing", "allow_root", is_flag=True, callback=set_ctx_obj_option
        ),
        hidden_option(
            "--ignore-blacklist",
            "ignore_blacklist",
            is_flag=True,
            callback=set_ctx_obj_option,
        ),
    ]
)
"""Legacy options available directly on the "octoprint" command in earlier versions.
   Kept available for reasons of backwards compatibility, but hidden from the
   generated help pages."""

# ~~ "octoprint" command, merges server_commands and plugin_commands groups

from .analysis import analysis_commands  # noqa: E402
from .client import client_commands  # noqa: E402
from .config import config_commands  # noqa: E402
from .dev import dev_commands  # noqa: E402
from .plugins import plugin_commands  # noqa: E402
from .server import server_commands  # noqa: E402
from .systeminfo import systeminfo_commands  # noqa: E402
from .user import user_commands  # noqa: E402


@click.group(
    name="octoprint",
    invoke_without_command=True,
    cls=click.CommandCollection,
    sources=[
        server_commands,
        plugin_commands,
        dev_commands,
        client_commands,
        config_commands,
        analysis_commands,
        user_commands,
        systeminfo_commands,
    ],
)
@standard_options()
@legacy_options
@click.version_option(version=octoprint.__version__, allow_from_autoenv=False)
@click.pass_context
def octo(ctx, **kwargs):

    if ctx.invoked_subcommand is None:
        # We have to support calling the octoprint command without any
        # sub commands to remain backwards compatible.
        #
        # But better print a message to inform people that they should
        # use the sub commands instead.

        def get_value(key):
            return get_ctx_obj_option(ctx, key, kwargs.get(key))

        daemon = get_value("daemon")

        if daemon:
            click.echo(
                'Daemon operation via "octoprint --daemon '
                'start|stop|restart" is deprecated, please use '
                '"octoprint daemon start|stop|restart" from now on'
            )

            if sys.platform == "win32" or sys.platform == "darwin":
                click.echo(
                    "Sorry, daemon mode is not supported under your operating system right now"
                )
            else:
                from octoprint.cli.server import daemon_command

                ctx.invoke(daemon_command, command=daemon, **kwargs)
        else:
            click.echo(
                'Starting the server via "octoprint" is deprecated, '
                'please use "octoprint serve" from now on.'
            )

            from octoprint.cli.server import serve_command

            ctx.invoke(serve_command, **kwargs)
