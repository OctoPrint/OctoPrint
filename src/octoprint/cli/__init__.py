# coding=utf-8
from __future__ import absolute_import

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"

import click
import octoprint


# ~~ click context

class OctoPrintContext(object):
    """Custom context wrapping the standard options."""

    def __init__(self, configfile=None, basedir=None, verbosity=0):
        self.configfile = configfile
        self.basedir = basedir
        self.verbosity = verbosity


pass_octoprint_ctx = click.make_pass_decorator(OctoPrintContext, ensure=True)
"""Decorator to pass in the :class:`OctoPrintContext` instance."""


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
        if 'help' in attrs:
            attrs['help'] = inspect.cleandoc(attrs['help'])
        _param_memo(f, HiddenOption(param_decls, **attrs))
        return f

    return decorator


# ~~ helper for settings context options

def set_ctx_obj_option(ctx, param, value):
    """Helper for setting eager options on the context."""
    if ctx.obj is None:
        ctx.obj = OctoPrintContext()

    if hasattr(ctx.obj, param.name):
        setattr(ctx.obj, param.name, value)


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
        factory("--basedir", "-b", type=click.Path(), callback=set_ctx_obj_option, is_eager=True, expose_value=False,
                help="Specify the basedir to use for uploads, timelapses etc."),
        factory("--config", "-c", "configfile", type=click.Path(), callback=set_ctx_obj_option, is_eager=True,
                expose_value=False,
                help="Specify the config file to use."),
        factory("--verbose", "-v", "verbosity", count=True, callback=set_ctx_obj_option, is_eager=True,
                expose_value=False,
                help="Increase logging verbosity"),
    ]

    return bulk_options(options)


# ~~ helper for settings legacy options we still have to support on "octoprint"

legacy_options = bulk_options([
    hidden_option("--host", type=click.STRING),
    hidden_option("--port", type=click.INT),
    hidden_option("--logging", type=click.Path()),
    hidden_option("--debug", "-d", is_flag=True),
    hidden_option("--daemon", type=click.Choice(["start", "stop", "restart"])),
    hidden_option("--pid", type=click.Path(), default="/tmp/octoprint.pid"),
    hidden_option("--iknowwhatimdoing", "allow_root", is_flag=True),
])
"""Legacy options available directly on the "octoprint" command in earlier versions.
   Kept available for reasons of backwards compatibility, but hidden from the
   generated help pages."""

# ~~ "octoprint" command, merges server_commands and plugin_commands groups

from .server import server_commands
from .plugins import plugin_commands
from .dev import dev_commands
from .client import client_commands


@click.group(name="octoprint", invoke_without_command=True, cls=click.CommandCollection,
             sources=[server_commands, plugin_commands, dev_commands, client_commands])
@standard_options()
@legacy_options
@click.version_option(version=octoprint.__version__)
@click.pass_context
def octo(ctx, debug, host, port, logging, daemon, pid, allow_root):
    if ctx.invoked_subcommand is None:
        # We have to support calling the octoprint command without any
        # sub commands to remain backwards compatible.
        #
        # But better print a message to inform people that they should
        # use the sub commands instead.

        if daemon:
            click.echo("Daemon operation via \"octoprint --daemon "
                       "start|stop|restart\" is deprecated, please use "
                       "\"octoprint daemon start|stop|restart\" from now on")

            from octoprint.cli.server import daemon_command
            ctx.invoke(daemon_command, debug=debug, pid=pid, daemon=daemon, allow_root=allow_root)
        else:
            click.echo("Starting the server via \"octoprint\" is deprecated, "
                       "please use \"octoprint serve\" from now on.")

            from octoprint.cli.server import serve_command
            ctx.invoke(serve_command, debug=debug, host=host, port=port, logging=logging, allow_root=allow_root)
