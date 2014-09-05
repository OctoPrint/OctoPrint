# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import os
import imp
from collections import defaultdict
import logging


class PluginInfo(object):

	attr_name = '__plugin_name__'

	attr_description = '__plugin_description__'

	attr_version = '__plugin_version__'

	attr_hooks = '__plugin_hooks__'

	attr_implementations = '__plugin_implementations__'

	attr_check = '__plugin_check__'

	def __init__(self, key, location, instance):
		self.key = key
		self.location = location
		self.instance = instance

	def __str__(self):
		return "{name} ({version})".format(name=self.name, version=self.version if self.version else "unknown")

	def get_hook(self, hook):
		if not hook in self.hooks:
			return None
		return self.hooks[hook]

	def get_implementations(self, *types):
		result = set()
		for implementation in self.implementations:
			matches_all = True
			for type in types:
				if not isinstance(implementation, type):
					matches_all = False
			if matches_all:
				result.add(implementation)
		return result

	@property
	def name(self):
		return self._get_instance_attribute(self.__class__.attr_name, default=None)

	@property
	def description(self):
		return self._get_instance_attribute(self.__class__.attr_description, default=None)

	@property
	def version(self):
		return self._get_instance_attribute(self.__class__.attr_version, default=None)

	@property
	def hooks(self):
		return self._get_instance_attribute(self.__class__.attr_hooks, default={})

	@property
	def implementations(self):
		return self._get_instance_attribute(self.__class__.attr_implementations, default=[])

	@property
	def check(self):
		return self._get_instance_attribute(self.__class__.attr_check, default=lambda: True)

	def _get_instance_attribute(self, attr, default=None):
		if not hasattr(self.instance, attr):
			return default
		return getattr(self.instance, attr)


class PluginManager(object):

	def __init__(self, plugin_folders, plugin_types, plugin_disabled_list=None):
		self.logger = logging.getLogger(__name__)

		if plugin_disabled_list is None:
			plugin_disabled_list = []

		self.plugin_folders = plugin_folders
		self.plugin_types = plugin_types
		self.plugin_disabled_list = plugin_disabled_list

		self.plugins = dict()
		self.plugin_hooks = defaultdict(list)
		self.plugin_implementations = defaultdict(list)

		self.reload_plugins()

	def _find_plugins(self):
		plugins = dict()

		for folder in self.plugin_folders:
			if not os.path.exists(folder):
				self.logger.warn("Plugin folder {folder} could not be found, skipping it".format(folder=folder))
				continue

			entries = os.listdir(folder)
			for entry in entries:
				path = os.path.join(folder, entry)
				if os.path.isdir(path) and os.path.isfile(os.path.join(path, "__init__.py")):
					id = entry
				elif os.path.isfile(path) and entry.endswith(".py"):
					id = entry[:-3] # strip off the .py extension
				else:
					continue

				if self._is_plugin_disabled(id):
					# plugin is disabled, ignore it
					continue

				if id in plugins:
					# plugin is already defined, ignore it
					continue

				module = imp.find_module(id, [folder])
				plugin = self._load_plugin(id, *module)
				if plugin.check():
					plugins[id] = plugin
				else:
					self.logger.warn("Plugin \"{plugin}\" did not pass check, disabling it".format(plugin=str(plugin)))

		return plugins

	def _load_plugin(self, id, f, filename, description):
		instance = imp.load_module(id, f, filename, description)
		return PluginInfo(id, filename, instance)

	def _is_plugin_disabled(self, id):
		return id in self.plugin_disabled_list or id.endswith('disabled')

	def reload_plugins(self):
		self.logger.info("Loading plugins from {folders}...".format(folders=", ".join(self.plugin_folders)))
		self.plugins = self._find_plugins()

		for name, plugin in self.plugins.items():
			for hook, callback in plugin.hooks.items():
				self.plugin_hooks[hook].append((name, callback))
			for plugin_type in self.plugin_types:
				implementations = plugin.get_implementations(plugin_type)
				self.plugin_implementations[plugin_type] += ( (name, implementation) for implementation in implementations )

		if len(self.plugins) <= 0:
			self.logger.info("No plugins found")
		else:
			self.logger.info("Found {count} plugin(s): {plugins}".format(count=len(self.plugins), plugins=", ".join(map(lambda x: str(x), self.plugins.values()))))

	def get_plugin(self, name):
		if not name in self.plugins:
			return None
		return self.plugins[name].instance

	def get_hooks(self, hook):
		if not hook in self.plugin_hooks:
			return []
		return {hook[0]: hook[1] for hook in self.plugin_hooks[hook]}

	def get_implementations(self, *types):
		result = None

		for t in types:
			implementations = self.plugin_implementations[t]
			if result is None:
				result = set(implementations)
			else:
				result = result.intersection(implementations)

		if result is None:
			return set()
		return {impl[0]: impl[1] for impl in result}


class Plugin(object):
	pass
