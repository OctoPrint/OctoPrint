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
			"""
			Allows overriding cookiecutter's user config with a custom dict
			with fallback to the original data.
			"""
			from octoprint.util import fallback_dict

			original_get_user_config = cookiecutter.main.get_user_config
			original_config = original_get_user_config()
			try:
				cookiecutter.main.get_user_config = lambda: fallback_dict(config, original_config)
				yield
			finally:
				cookiecutter.main.get_user_config = original_get_user_config

		@contextlib.contextmanager
		def custom_cookiecutter_prompt(options):
			"""
			Custom cookiecutter prompter for the template config.

			If a setting is available in the provided options (read from the CLI)
			that will be used, otherwise the user will be prompted for a value
			via click.
			"""
			original_prompt_for_config = cookiecutter.main.prompt_for_config

			def custom_prompt_for_config(context, no_input=False):
				import cookiecutter.prompt

				cookiecutter_dict = {}
				env = cookiecutter.prompt.Environment()

				for key, raw in context['cookiecutter'].items():
					if key in options:
						val = options[key]
					else:
						raw = raw if isinstance(raw, basestring) else str(raw)
						val = env.from_string(raw).render(cookiecutter=cookiecutter_dict)

						if not no_input:
							val = click.prompt(key, default=val)

					cookiecutter_dict[key] = val
				return cookiecutter_dict

			try:
				cookiecutter.main.prompt_for_config = custom_prompt_for_config
				yield
			finally:
				cookiecutter.main.prompt_for_config = original_prompt_for_config

		@click.command("newplugin")
		@click.option("--name", "-n", help="The name of the plugin")
		@click.option("--package", "-p", help="The plugin package")
		@click.option("--author", "-a", help="The plugin author's name")
		@click.option("--email", "-e", help="The plugin author's mail address")
		@click.option("--license", "-l", help="The plugin's license")
		@click.option("--description", "-d", help="The plugin's description")
		@click.option("--homepage", help="The plugin's homepage URL")
		@click.option("--source", "-s", help="The URL to the plugin's source")
		@click.option("--installurl", "-i", help="The plugin's install URL")
		@click.argument("identifier", required=False)
		def command(name, package, author, email, description, license, homepage, source, installurl, identifier):
			"""Creates a new plugin based on the OctoPrint Plugin cookiecutter template."""
			from octoprint.util import tempdir

			# deleting a git checkout folder might run into access errors due
			# to write-protected sub folders, so we use a custom onerror handler
			# that tries to fix such permissions
			def onerror(func, path, exc_info):
				"""Originally from http://stackoverflow.com/a/2656405/2028598"""
				import stat
				import os

				if not os.access(path, os.W_OK):
					os.chmod(path, stat.S_IWUSR)
					func(path)
				else:
					raise

			with tempdir(onerror=onerror) as path:
				custom = dict(cookiecutters_dir=path)
				with custom_cookiecutter_config(custom):
					raw_options = dict(
						plugin_identifier=identifier,
						plugin_package=package,
						plugin_name=name,
						full_name=author,
						email=email,
						plugin_description=description,
						plugin_license=license,
						plugin_homepage=homepage,
						plugin_source=source,
						plugin_installurl=installurl
					)
					options = dict((k, v) for k, v in raw_options.items() if v is not None)

					with custom_cookiecutter_prompt(options):
						cookiecutter.main.cookiecutter("gh:OctoPrint/cookiecutter-octoprint-plugin")

		return command

@click.group(cls=OctoPrintDevelCommands)
def devel_commands():
	pass
