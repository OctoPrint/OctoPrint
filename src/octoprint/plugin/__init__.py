# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import os
import logging

from octoprint.settings import settings
from octoprint.plugin.core import (PluginInfo, PluginManager, Plugin)
from octoprint.plugin.types import *

from octoprint.util import deprecated

# singleton
_instance = None

def plugin_manager(init=False, plugin_folders=None, plugin_types=None, plugin_entry_points=None, plugin_disabled_list=None):
	global _instance
	if _instance is None:
		if init:
			if plugin_folders is None:
				plugin_folders = (settings().getBaseFolder("plugins"), os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "plugins")))
			if plugin_types is None:
				plugin_types = [StartupPlugin,
				                ShutdownPlugin,
				                TemplatePlugin,
				                SettingsPlugin,
				                SimpleApiPlugin,
				                AssetPlugin,
				                BlueprintPlugin,
				                EventHandlerPlugin,
				                SlicerPlugin,
				                AppPlugin,
				                ProgressPlugin]
			if plugin_entry_points is None:
				plugin_entry_points = "octoprint.plugin"
			if plugin_disabled_list is None:
				all_plugin_settings = settings().get(["plugins"])
				plugin_disabled_list = []
				for key in all_plugin_settings:
					if "enabled" in all_plugin_settings[key] and not all_plugin_settings[key]:
						plugin_disabled_list.append(key)

			_instance = PluginManager(plugin_folders, plugin_types, plugin_entry_points, logging_prefix="octoprint.plugins.", plugin_disabled_list=plugin_disabled_list)
		else:
			raise ValueError("Plugin Manager not initialized yet")
	return _instance


def plugin_settings(plugin_key, defaults=None):
	return PluginSettings(settings(), plugin_key, defaults=defaults)


def call_plugin(types, method, args=None, kwargs=None, callback=None, error_callback=None):
	if not isinstance(types, (list, tuple)):
		types = [types]
	if args is None:
		args = []
	if kwargs is None:
		kwargs = dict()

	plugins = plugin_manager().get_implementations(*types)
	for name, plugin in plugins.items():
		if hasattr(plugin, method):
			try:
				result = getattr(plugin, method)(*args, **kwargs)
				if callback:
					callback(name, plugin, result)
			except Exception as e:
				logging.getLogger(__name__).exception("Error while calling plugin %s" % name)
				if error_callback:
					error_callback(name, plugin, e)


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

		self.access_methods = dict(
			get=("get", lambda args: prefix_path_in_args(args), lambda kwargs: add_defaults_to_kwargs(kwargs)),
			get_int=("getInt", lambda args,: prefix_path_in_args(args), lambda kwargs: add_defaults_to_kwargs(kwargs)),
			get_float=("getFloat", lambda args,: prefix_path_in_args(args), lambda kwargs: add_defaults_to_kwargs(kwargs)),
			get_boolean=("getBoolean", lambda args,: prefix_path_in_args(args), lambda kwargs: add_defaults_to_kwargs(kwargs)),
			set=("set", lambda args: prefix_path_in_args(args), lambda kwargs: add_defaults_to_kwargs(kwargs)),
			set_int=("setInt", lambda args: prefix_path_in_args(args), lambda kwargs: add_defaults_to_kwargs(kwargs)),
			set_float=("setFloat", lambda args: prefix_path_in_args(args), lambda kwargs: add_defaults_to_kwargs(kwargs)),
			set_boolean=("setBoolean", lambda args: prefix_path_in_args(args), lambda kwargs: add_defaults_to_kwargs(kwargs))
		)
		self.deprecated_access_methods = dict(getInt="get_int", getFloat="get_float", getBoolean="get_boolean", setInt="set_int", setFloat="set_float", setBoolean="set_boolean")

	def global_get(self, path):
		return self.settings.get(path)
	globalGet = deprecated("globalGet has been renamed to global_get")(global_get)

	def global_get_int(self, path):
		return self.settings.getInt(path)
	globalGetInt = deprecated("globalGetInt has been renamed to global_get_int")(global_get_int)

	def global_get_float(self, path):
		return self.settings.getFloat(path)
	globalGetFloat = deprecated("globalGetFloat has been renamed to global_get_float")(global_get_float)

	def global_get_boolean(self, path):
		return self.settings.getBoolean(path)
	globalGetBoolean = deprecated("globalGetBoolean has been renamed to global_get_boolean")(global_get_boolean)

	def global_set(self, path, value):
		self.settings.set(path, value)
	globalSet = deprecated("globalSet has been renamed to global_set")(global_set)

	def global_set_int(self, path, value):
		self.settings.setInt(path, value)
	globalSetInt = deprecated("globalSetInt has been renamed to global_set_int")(global_set_int)

	def global_set_float(self, path, value):
		self.settings.setFloat(path, value)
	globalSetFloat = deprecated("globalSetFloat has been renamed to global_set_float")(global_set_float)

	def global_set_boolean(self, path, value):
		self.settings.setBoolean(path, value)
	globalSetBoolean = deprecated("globalSetBoolean has been renamed to global_set_boolean")(global_set_boolean)

	def global_get_basefolder(self, folder_type):
		return self.settings.getBaseFolder(folder_type)
	globalGetBaseFolder = deprecated("globalGetBaseFolder has been renamed to global_get_basefolder")(global_get_basefolder)

	def get_plugin_logfile_path(self, postfix=None):
		filename = "plugin_" + self.plugin_key
		if postfix is not None:
			filename += "_" + postfix
		filename += ".log"
		return os.path.join(self.settings.getBaseFolder("logs"), filename)
	getPluginLogfilePath = deprecated("getPluginLogfilePath has been renamed to get_plugin_logfile_path")(get_plugin_logfile_path)

	def __getattr__(self, item):
		all_access_methods = self.access_methods.keys() + self.deprecated_access_methods.keys()
		if item in all_access_methods:
			decorator = None
			if item in self.deprecated_access_methods:
				new = self.deprecated_access_methods[item]
				decorator = deprecated("{old} has been renamed to {new}".format(old=item, new=new), stacklevel=2)
				item = new

			settings_name, args_mapper, kwargs_mapper = self.access_methods[item]
			if hasattr(self.settings, settings_name) and callable(getattr(self.settings, settings_name)):
				orig_func = getattr(self.settings, settings_name)
				if decorator is not None:
					orig_func = decorator(orig_func)

				return lambda *args, **kwargs: orig_func(*args_mapper(args), **kwargs_mapper(kwargs))

		return getattr(self.settings, item)
