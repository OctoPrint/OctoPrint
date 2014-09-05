# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


from .core import Plugin


class StartupPlugin(Plugin):
	def on_startup(self, host, port):
		pass


class AssetPlugin(Plugin):
	def get_asset_folder(self):
		return None

	def get_assets(self):
		return []


class TemplatePlugin(Plugin):
	def get_template_vars(self):
		return dict()

	def get_template_folder(self):
		return None


class SimpleApiPlugin(Plugin):
	def get_api_commands(self):
		return None

	def on_api_command(self, command, data):
		return None

	def on_api_get(self, request):
		return None


class SettingsPlugin(TemplatePlugin):
	def on_settings_load(self):
		return None

	def on_settings_save(self, data):
		pass



