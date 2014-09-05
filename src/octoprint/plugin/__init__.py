# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import os

from octoprint.settings import settings
from octoprint.plugin.core import (PluginInfo, PluginManager, Plugin)
from octoprint.plugin.types import *

# singleton
_instance = None

def plugin_manager(init=False, plugin_folders=None, plugin_types=None):
	global _instance
	if _instance is None:
		if init:
			if plugin_folders is None:
				plugin_folders = (settings().getBaseFolder("plugins"), os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "plugins")))
			if plugin_types is None:
				plugin_types = [StartupPlugin, TemplatePlugin, SettingsPlugin, SimpleApiPlugin, AssetPlugin]

			_instance = PluginManager(plugin_folders, plugin_types)
		else:
			raise ValueError("Plugin Manager not initialized yet")
	return _instance


def plugin_settings(plugin_key, defaults=None):
	return PluginSettings(settings(), plugin_key, defaults=defaults)


class PluginSettings(object):
	def __init__(self, settings, plugin_key, defaults=None):
		self.settings = settings
		self.plugin_key = plugin_key

		if defaults is None:
			defaults = dict()
		self.defaults = dict(plugins=dict())
		self.defaults["plugins"][plugin_key] = defaults

		def prefix_path(path):
			return ['plugins', self.plugin_key] + path

		def prefix_path_in_args(args, index=0):
			result = []
			if index == 0:
				result.append(prefix_path(args[0]))
				result.extend(args[1:])
			else:
				args_before = args[:index - 1]
				args_after = args[index + 1:]
				result.extend(args_before)
				result.append(prefix_path(args[index]))
				result.extend(args_after)
			return result

		def add_defaults_to_kwargs(kwargs):
			kwargs.update(dict(defaults=self.defaults))
			return kwargs

		self.access_methods = {
			'get': (lambda args: prefix_path_in_args(args), lambda kwargs: add_defaults_to_kwargs(kwargs)),
			'getInt': (lambda args,: prefix_path_in_args(args), lambda kwargs: add_defaults_to_kwargs(kwargs)),
			'getFloat': (lambda args,: prefix_path_in_args(args), lambda kwargs: add_defaults_to_kwargs(kwargs)),
			'getBoolean': (lambda args,: prefix_path_in_args(args), lambda kwargs: add_defaults_to_kwargs(kwargs)),
			'set': (lambda args: prefix_path_in_args(args), lambda kwargs: add_defaults_to_kwargs(kwargs)),
			'setInt': (lambda args: prefix_path_in_args(args), lambda kwargs: add_defaults_to_kwargs(kwargs)),
			'setFloat': (lambda args: prefix_path_in_args(args), lambda kwargs: add_defaults_to_kwargs(kwargs)),
			'setBoolean': (lambda args: prefix_path_in_args(args), lambda kwargs: add_defaults_to_kwargs(kwargs))
		}

	def globalGet(self, path):
		return self.settings.get(path)

	def globalGetInt(self, path):
		return self.settings.getInt(path)

	def globalGetFloat(self, path):
		return self.settings.getFloat(path)

	def globalGetBoolean(self, path):
		return self.settings.getBoolean(path)

	def __getattr__(self, item):
		if item in self.access_methods and hasattr(self.settings, item) and callable(getattr(self.settings, item)):
			orig_item = getattr(self.settings, item)
			args_mapper, kwargs_mapper = self.access_methods[item]

			return lambda *args, **kwargs: orig_item(*args_mapper(args), **kwargs_mapper(kwargs))
		else:
			return getattr(self.settings, item)
