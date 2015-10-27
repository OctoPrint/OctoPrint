# coding=utf-8
from __future__ import absolute_import

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


import click
import octoprint


#~~ click context


class OctoPrintContext(object):
	def __init__(self, configfile=None, basedir=None, debug=False):
		self.configfile = configfile
		self.basedir = basedir
		self.debug = debug
pass_octoprint_ctx = click.make_pass_decorator(OctoPrintContext, ensure=True)


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

#~~ "octoprint" command, merges server_commands and plugin_commands groups

from .server import server_commands
from .plugins import plugin_commands
from .devel import devel_commands

def set_ctx_obj_option(ctx, param, value):
	"""Helper for setting eager options on the context."""
	if ctx.obj is None:
		ctx.obj = OctoPrintContext()

	if hasattr(ctx.obj, param.name):
		setattr(ctx.obj, param.name, value)


@click.group(name="octoprint", invoke_without_command=True, cls=click.CommandCollection,
             sources=[server_commands, plugin_commands, devel_commands])
@click.option("--basedir", "-b", type=click.Path(), callback=set_ctx_obj_option, is_eager=True,
              help="Specify the basedir to use for uploads, timelapses etc.")
@click.option("--config", "-c", "configfile", type=click.Path(), callback=set_ctx_obj_option, is_eager=True,
              help="Specify the config file to use.")
@click.option("--debug", "-d", is_flag=True, callback=set_ctx_obj_option, is_eager=True,
              help="Enable debug mode")
@hidden_option("--host", type=click.STRING)
@hidden_option("--port", type=click.INT)
@hidden_option("--logging", type=click.Path())
@hidden_option("--daemon", type=click.Choice(["start", "stop", "restart"]))
@hidden_option("--pid", type=click.Path())
@hidden_option("--iknowwhatimdoing", "allow_root", is_flag=True)
@click.version_option(version=octoprint.__version__)
@click.pass_context
def octo(ctx, debug, host, port, basedir, configfile, logging, daemon, pid, allow_root):

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
			ctx.invoke(daemon_command, pid=pid, daemon=daemon, allow_root=allow_root)
		else:
			click.echo("Starting the server via \"octoprint\" is deprecated, "
			           "please use \"octoprint serve\" from now on.")

			from octoprint.cli.server import serve_command
			ctx.invoke(serve_command, host=host, port=port, logging=logging, allow_root=allow_root)
