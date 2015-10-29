# coding=utf-8
from __future__ import absolute_import

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


import click
import logging

from octoprint.cli import pass_octoprint_ctx, OctoPrintContext

#~~ "octoprint plugin:command" commands

class OctoPrintPluginCommands(click.MultiCommand):
	"""
	Custom `click.MultiCommand` implementation that collects commands from
	the plugin hook "octoprint.cli.commands".
	"""

	sep = ":"
	"""Separator for commands between plugin name and command name."""

	def __init__(self, *args, **kwargs):
		click.MultiCommand.__init__(self, *args, **kwargs)
		self._settings = None
		self._plugin_manager = None
		self._logger = logging.getLogger(__name__)

	def _initialize(self, ctx):
		if self._settings is not None:
			return

		if ctx.obj is None:
			ctx.obj = OctoPrintContext()

		# initialize settings and plugin manager based on provided
		# context (basedir and configfile)
		from octoprint import init_settings, init_pluginsystem
		self._settings = init_settings(ctx.obj.basedir, ctx.obj.configfile)
		self._plugin_manager = init_pluginsystem(self._settings)

		# fetch registered hooks
		self._hooks = self._plugin_manager.get_hooks("octoprint.cli.commands")

	def list_commands(self, ctx):
		self._initialize(ctx)
		result = [name for name in self._get_commands()]
		result.sort()
		return result

	def get_command(self, ctx, cmd_name):
		self._initialize(ctx)
		commands = self._get_commands()
		return commands.get(cmd_name, None)

	def _get_commands(self):
		"""Fetch all commands from plugins providing any."""

		import collections
		result = collections.OrderedDict()

		for name, hook in self._hooks.items():
			try:
				commands = hook(self, pass_octoprint_ctx)
				for command in commands:
					if not isinstance(command, click.Command):
						self._logger.warn("Plugin {} provided invalid CLI command, ignoring it: {!r}".format(name, command))
						continue
					result[name + self.sep + command.name] = command
			except:
				self._logger.exception("Error while retrieving cli commants for plugin {}".format(name))

		return result

@click.group(cls=OctoPrintPluginCommands)
@pass_octoprint_ctx
def plugin_commands(obj):
	"""Commands provided by plugins."""
	logging.basicConfig(level=logging.DEBUG if obj.verbosity > 0 else logging.WARN)


