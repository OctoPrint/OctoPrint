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

	attr_author = '__plugin_author__'

	attr_url = '__plugin_url__'

	attr_license = '__plugin_license__'

	attr_hooks = '__plugin_hooks__'

	attr_implementations = '__plugin_implementations__'

	attr_helpers = '__plugin_helpers__'

	attr_check = '__plugin_check__'

	attr_init = '__plugin_init__'

	def __init__(self, key, location, instance, name=None, version=None, description=None, author=None, url=None, license=None):
		self.key = key
		self.location = location
		self.instance = instance
		self.origin = None
		self.enabled = True
		self.bundled = False

		self._name = name
		self._version = version
		self._description = description
		self._author = author
		self._url = url
		self._license = license

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
		return self._get_instance_attribute(self.__class__.attr_name, default=self._name)

	@property
	def description(self):
		return self._get_instance_attribute(self.__class__.attr_description, default=self._description)

	@property
	def version(self):
		return self._version if self._version is not None else self._get_instance_attribute(self.__class__.attr_version, default=self._version)

	@property
	def author(self):
		return self._get_instance_attribute(self.__class__.attr_author, default=self._author)

	@property
	def url(self):
		return self._get_instance_attribute(self.__class__.attr_url, default=self._url)

	@property
	def license(self):
		return self._get_instance_attribute(self.__class__.attr_license, default=self._license)

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
		self.plugin_implementations = defaultdict(set)
		self.plugin_implementations_by_type = defaultdict(list)

		self.disabled_plugins = dict()

		self.registered_clients = []

		self.reload_plugins()

	def _find_plugins(self):
		plugins = dict()
		disabled_plugins = dict()
		if self.plugin_folders:
			self._add_plugins_from_folders(self.plugin_folders, plugins, disabled_plugins)
		if self.plugin_entry_points:
			self._add_plugins_from_entry_points(self.plugin_entry_points, plugins, disabled_plugins)
		return plugins, disabled_plugins

	def _add_plugins_from_folders(self, folders, plugins, disabled_plugins):
		for folder in folders:
			readonly = False
			if isinstance(folder, (list, tuple)):
				if len(folder) == 2:
					folder, readonly = folder
				else:
					continue

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

				if key in plugins:
					# plugin is already defined, ignore it
					continue

				plugin = self._load_plugin_from_module(key, folder=folder)
				if plugin:
					plugin.origin = ("folder", folder)
					if readonly:
						plugin.bundled = True

					if self._is_plugin_disabled(key):
						plugin.enabled = False
						disabled_plugins[key] = plugin
					else:
						plugins[key] = plugin

		return plugins, disabled_plugins

	def _add_plugins_from_entry_points(self, groups, plugins, disabled_plugins):
		import pkg_resources
		import pkginfo

		if not isinstance(groups, (list, tuple)):
			groups = [groups]

		for group in groups:
			for entry_point in pkg_resources.iter_entry_points(group=group, name=None):
				key = entry_point.name
				module_name = entry_point.module_name
				version = entry_point.dist.version

				if key in plugins:
					# plugin is already defined, ignore it
					continue

				kwargs = dict(module_name=module_name, version=version)
				try:
					module_pkginfo = pkginfo.Installed(module_name)
				except:
					self.logger.exception("Something went wrong while retrieving package info data for module %s" % module_name)
				else:
					kwargs.update(dict(
						name=module_pkginfo.name,
						summary=module_pkginfo.summary,
						author=module_pkginfo.author,
						url=module_pkginfo.home_page,
						license=module_pkginfo.license
					))

				plugin = self._load_plugin_from_module(key, **kwargs)
				if plugin:
					plugin.origin = ("entry_point", group, module_name)

					if self._is_plugin_disabled(key):
						plugin.enabled = False
						disabled_plugins[key] = plugin
					else:
						plugins[key] = plugin

		return plugins, disabled_plugins

	def _load_plugin_from_module(self, key, folder=None, module_name=None, name=None, version=None, summary=None, author=None, url=None, license=None):
		# TODO error handling
		try:
			if folder:
				module = imp.find_module(key, [folder])
			elif module_name:
				module = imp.find_module(module_name)
			else:
				return None
		except:
			self.logger.warn("Could not locate plugin {key}")
			return None

		plugin = self._load_plugin(key, *module, name=name, version=version, summary=summary, author=author, url=url, license=license)
		if plugin:
			if plugin.check():
				return plugin
			else:
				self.logger.warn("Plugin \"{plugin}\" did not pass check".format(plugin=str(plugin)))
				return None


	def _load_plugin(self, key, f, filename, description, name=None, version=None, summary=None, author=None, url=None, license=None):
		try:
			instance = imp.load_module(key, f, filename, description)
			return PluginInfo(key, filename, instance, name=name, version=version, description=summary, author=author, url=url, license=license)
		except:
			self.logger.exception("Error loading plugin {key}, disabling it".format(key=key))
			return None

	def _is_plugin_disabled(self, key):
		return key in self.plugin_disabled_list or key.endswith('disabled')

	def reload_plugins(self):
		self.logger.info("Loading plugins from {folders} and installed plugin packages...".format(folders=", ".join(self.plugin_folders)))
		self.plugins, self.disabled_plugins = self._find_plugins()

		for name, plugin in self.plugins.items():
			# initialize the plugin
			plugin.init()

			# evaluate registered hooks
			for hook, callback in plugin.hooks.items():
				self.plugin_hooks[hook].append((name, callback))

			# evaluate registered implementations
			for plugin_type in self.plugin_types:
				implementations = plugin.get_implementations(plugin_type)
				self.plugin_implementations_by_type[plugin_type] += ( (name, implementation) for implementation in implementations )
			self.plugin_implementations[name].update(plugin.get_implementations())

		self.log_registered_plugins()

	def initialize_implementations(self, additional_injects=None):
		if additional_injects is None:
			additional_injects = dict()

		for name, implementations in self.plugin_implementations.items():
			plugin = self.plugins[name]
			for implementation in implementations:
				kwargs = dict(additional_injects)
				kwargs.update(dict(
					identifier=name,
					plugin_name=plugin.name,
					plugin_version=plugin.version,
					basefolder=os.path.realpath(plugin.location),
					logger=logging.getLogger("octoprint.plugins." + name),
				))
				try:
					implementation.pre_initialize(**kwargs)
				except:
					self.logger.exception("Exception while initializing plugin")

		self.logger.info("Initialized {count} plugin(s)".format(count=len(self.plugin_implementations)))

	def log_registered_plugins(self):
		if len(self.plugins) <= 0:
			self.logger.info("No plugins found")
		else:
			self.logger.info("Found {count} plugin(s): {plugins}".format(count=len(self.plugins), plugins=", ".join(map(lambda x: str(x), self.plugins.values()))))

		if len(self.disabled_plugins) > 0:
			self.logger.info("{count} plugin(s) currently disabled: {plugins}".format(count=len(self.disabled_plugins), plugins=", ".join(map(lambda x: str(x), self.disabled_plugins.values()))))

	def get_plugin(self, name):
		if not name in self.plugins:
			return None
		return self.plugins[name].instance

	def get_hooks(self, hook):
		if not hook in self.plugin_hooks:
			return dict()
		return {hook[0]: hook[1] for hook in self.plugin_hooks[hook]}

	def get_implementations(self, *types):
		result = None

		for t in types:
			implementations = self.plugin_implementations_by_type[t]
			if result is None:
				result = set(implementations)
			else:
				result = result.intersection(implementations)

		if result is None:
			return dict()
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

	def register_client(self, client):
		if client is None:
			return
		self.registered_clients.append(client)

	def unregister_client(self, client):
		self.registered_clients.remove(client)

	def send_plugin_message(self, plugin, data):
		for client in self.registered_clients:
			try: client.sendPluginMessage(plugin, data)
			except: self.logger.exception("Exception while sending plugin data to client")


class Plugin(object):
	def pre_initialize(self, **kwargs):
		for arg, value in kwargs.items():
			setattr(self, "_" + arg, value)
		self.initialize()

	def initialize(self):
		pass
