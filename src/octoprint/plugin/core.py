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

	attr_helpers = '__plugin_helpers__'

	attr_check = '__plugin_check__'

	attr_init = '__plugin_init__'

	def __init__(self, key, location, instance, version=None):
		self.key = key
		self.location = location
		self.instance = instance

		self._version = version

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
		return self._version if self._version is not None else self._get_instance_attribute(self.__class__.attr_version, default=None)

	@property
	def hooks(self):
		return self._get_instance_attribute(self.__class__.attr_hooks, default={})

	@property
	def implementations(self):
		return self._get_instance_attribute(self.__class__.attr_implementations, default=[])

	@property
	def helpers(self):
		return self._get_instance_attribute(self.__class__.attr_helpers, default={})

	@property
	def check(self):
		return self._get_instance_attribute(self.__class__.attr_check, default=lambda: True)

	@property
	def init(self):
		return self._get_instance_attribute(self.__class__.attr_init, default=lambda: True)

	def _get_instance_attribute(self, attr, default=None):
		if not hasattr(self.instance, attr):
			return default
		return getattr(self.instance, attr)


class PluginManager(object):

	def __init__(self, plugin_folders, plugin_types, plugin_entry_points, plugin_disabled_list=None):
		self.logger = logging.getLogger(__name__)

		if plugin_disabled_list is None:
			plugin_disabled_list = []

		self.plugin_folders = plugin_folders
		self.plugin_types = plugin_types
		self.plugin_entry_points = plugin_entry_points
		self.plugin_disabled_list = plugin_disabled_list

		self.plugins = dict()
		self.plugin_hooks = defaultdict(list)
		self.plugin_implementations = defaultdict(list)

		self.reload_plugins()

	def _find_plugins(self):
		plugins = dict()
		if self.plugin_folders:
			self._add_plugins_from_folders(self.plugin_folders, plugins)
		if self.plugin_entry_points:
			self._add_plugins_from_entry_points(self.plugin_entry_points, plugins)
		return plugins

	def _add_plugins_from_folders(self, folders, plugins):
		for folder in folders:
			if not os.path.exists(folder):
				self.logger.warn("Plugin folder {folder} could not be found, skipping it".format(folder=folder))
				continue

			entries = os.listdir(folder)
			for entry in entries:
				path = os.path.join(folder, entry)
				if os.path.isdir(path) and os.path.isfile(os.path.join(path, "__init__.py")):
					key = entry
				elif os.path.isfile(path) and entry.endswith(".py"):
					key = entry[:-3] # strip off the .py extension
				else:
					continue

				if self._is_plugin_disabled(key):
					# plugin is disabled, ignore it
					continue

				if key in plugins:
					# plugin is already defined, ignore it
					continue

				plugin = self._load_plugin_from_module(key, folder=folder)
				if plugin:
					plugins[key] = plugin

		return plugins

	def _add_plugins_from_entry_points(self, groups, plugins):
		import pkg_resources

		if not isinstance(groups, (list, tuple)):
			groups = [groups]

		for group in groups:
			for entry_point in pkg_resources.iter_entry_points(group=group, name=None):
				key = entry_point.name
				module_name = entry_point.module_name
				version = entry_point.dist.version

				if self._is_plugin_disabled(key):
					# plugin is disabled, ignore it
					continue

				if key in plugins:
					# plugin is already defined, ignore it
					continue

				plugin = self._load_plugin_from_module(key, module_name=module_name, version=version)
				if plugin:
					plugins[key] = plugin

		return plugins

	def _load_plugin_from_module(self, key, folder=None, module_name=None, version=None):
		# TODO error handling
		if folder:
			module = imp.find_module(key, [folder])
		elif module_name:
			module = imp.find_module(module_name)
		else:
			return None

		plugin = self._load_plugin(key, *module, version=version)
		if plugin:
			if plugin.check():
				return plugin
			else:
				self.logger.warn("Plugin \"{plugin}\" did not pass check, disabling it".format(plugin=str(plugin)))
				return None
            

	def _load_plugin(self, key, f, filename, description, version=None):
		try:
			instance = imp.load_module(key, f, filename, description)
			return PluginInfo(key, filename, instance, version=version)
		except:
			self.logger.exception("Error loading plugin {key}, disabling it".format(key=key))
			return None

	def _is_plugin_disabled(self, key):
		return key in self.plugin_disabled_list or key.endswith('disabled')

	def reload_plugins(self):
		self.logger.info("Loading plugins from {folders} and installed plugin packages...".format(folders=", ".join(self.plugin_folders)))
		self.plugins = self._find_plugins()

		for name, plugin in self.plugins.items():
			# initialize the plugin
			plugin.init()

			# evaluate registered hooks
			for hook, callback in plugin.hooks.items():
				self.plugin_hooks[hook].append((name, callback))

			# evaluate registered implementations
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

	def get_helpers(self, name, *helpers):
		if not name in self.plugins:
			return None
		plugin = self.plugins[name]

		all_helpers = plugin.helpers
		if len(helpers):
			return dict((k, v) for (k, v) in all_helpers.items() if k in helpers)
		else:
			return all_helpers


class Plugin(object):
	pass
