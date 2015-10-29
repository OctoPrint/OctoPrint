# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


import click
import logging

class OctoPrintDevelCommands(click.MultiCommand):
	"""
	Custom `click.MultiCommand <http://click.pocoo.org/5/api/#click.MultiCommand>`_
	implementation that provides commands relevant for (plugin) development
	based on availability of development dependencies.
	"""

	sep = ":"

	def list_commands(self, ctx):
		result = [name for name in self._get_commands()]
		result.sort()
		return result

	def get_command(self, ctx, cmd_name):
		commands = self._get_commands()
		return commands.get(cmd_name, None)

	def _get_commands(self):
		commands = dict()

		for name in [x for x in dir(self) if x.startswith("command_")]:
			method = getattr(self, name)

			try:
				result = method()
				if result is not None:
					commands["devel" + self.sep + result.name] = result
			except:
				logging.getLogger(__name__).exception("There was an error registering one of the devel commands ({})".format(name))

		return commands

	def command_newplugin(self):
		try:
			import cookiecutter.main
		except ImportError:
			return None

		import contextlib

		@contextlib.contextmanager
		def custom_cookiecutter_config(config):
			from octoprint.util import fallback_dict

			original_get_user_config = cookiecutter.main.get_user_config
			original_config = original_get_user_config()
			try:
				cookiecutter.main.get_user_config = lambda: fallback_dict(config, original_config)
				yield
			finally:
				cookiecutter.main.get_user_config = original_get_user_config

		@click.command("newplugin")
		def command():
			"""Creates a new plugin based on the OctoPrint Plugin cookiecutter template."""
			from octoprint.util import tempdir

			with tempdir() as path:
				custom = dict(cookiecutters_dir=path)
				with custom_cookiecutter_config(custom):
					cookiecutter.main.cookiecutter("gh:OctoPrint/cookiecutter-octoprint-plugin")

		return command

@click.group(cls=OctoPrintDevelCommands)
def devel_commands():
	pass
