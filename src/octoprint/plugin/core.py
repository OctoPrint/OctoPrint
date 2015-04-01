# coding=utf-8
"""
In this module resides the core data structures and logic of the plugin system. It is implemented in an OctoPrint-agnostic
way and could be extracted into a separate Python module in the future.

.. autoclass:: PluginManager
   :members:

.. autoclass:: PluginInfo
   :members:

.. autoclass:: Plugin
   :members:

"""

from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import os
import imp
from collections import defaultdict
import logging


class PluginInfo(object):
	"""
	The :class:`PluginInfo` class wraps all available information about a registered plugin.

	This includes its meta data (like name, description, version, etc) as well as the actual plugin extensions like
	implementations, hooks and helpers.

	It works on Python module objects and extracts the relevant data from those via accessing the
	:ref:`control properties <sec-plugin-concepts-controlproperties>`.

	Arguments:
	    key (str): Identifier of the plugin
	    location (str): Installation folder of the plugin
	    instance (module): Plugin module instance
	    name (str): Human readable name of the plugin
	    version (str): Version of the plugin
	    description (str): Description of the plugin
	    author (str): Author of the plugin
	    url (str): URL of the website of the plugin
	    license (str): License of the plugin
	"""

	attr_name = '__plugin_name__'
	""" Module attribute from which to retrieve the plugin's human readable name. """

	attr_description = '__plugin_description__'
	""" Module attribute from which to retrieve the plugin's description. """

	attr_version = '__plugin_version__'
	""" Module attribute from which to retrieve the plugin's version. """

	attr_author = '__plugin_author__'
	""" Module attribute from which to retrieve the plugin's author. """

	attr_url = '__plugin_url__'
	""" Module attribute from which to retrieve the plugin's website URL. """

	attr_license = '__plugin_license__'
	""" Module attribute from which to retrieve the plugin's license. """

	attr_hooks = '__plugin_hooks__'
	""" Module attribute from which to retrieve the plugin's provided hooks. """

	attr_implementation = '__plugin_implementation__'
	""" Module attribute from which to retrieve the plugin's provided mixin implementation. """

	attr_implementations = '__plugin_implementations__'
	"""
	Module attribute from which to retrieve the plugin's provided implementations.

	This deprecated attribute will only be used if a plugin does not yet offer :attr:`attr_implementation`. Only the
	first entry will be evaluated.

	.. deprecated:: 1.2.0-dev-694

	   Use :attr:`attr_implementation` instead.
	"""

	attr_helpers = '__plugin_helpers__'
	""" Module attribute from which to retrieve the plugin's provided helpers. """

	attr_check = '__plugin_check__'
	""" Module attribute which to call to determine if the plugin can be loaded. """

	attr_init = '__plugin_init__'
	""" Module attribute which to call when loading the plugin. """

	attr_load = '__plugin_load__'

	attr_unload = '__plugin_unload__'

	attr_enable = '__plugin_enable__'

	attr_disable = '__plugin_disable__'

	attr_activate = '__plugin_activate__'

	attr_deactivate = '__plugin_deactivate__'

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

		self._validate()

	def _validate(self):
		# if the plugin still uses __plugin_implementations__, log a deprecation warning and put the first
		# item into __plugin_implementation__
		if hasattr(self.instance, self.__class__.attr_implementations):
			if not hasattr(self.instance, self.__class__.attr_implementation):
				# deprecation warning
				import warnings
				warnings.warn("{name} uses deprecated control property __plugin_implementations__, use __plugin_implementation__ instead - only the first implementation of {name} will be recognized".format(name=self.key), DeprecationWarning)

				# put first item into __plugin_implementation__
				implementations = getattr(self.instance, self.__class__.attr_implementations)
				if len(implementations) > 0:
					setattr(self.instance, self.__class__.attr_implementation, implementations[0])

			# delete __plugin_implementations__
			delattr(self.instance, self.__class__.attr_implementations)

	def __str__(self):
		if self.version:
			return "{name} ({version})".format(name=self.name, version=self.version)
		else:
			return self.name

	def long_str(self, show_bundled=False, bundled_str=(" [B]", ""),
	             show_location=False, location_str=" - {location}",
	             show_enabled=False, enabled_str=("* ", "  ")):
		if show_enabled:
			ret = enabled_str[0] if self.enabled else enabled_str[1]
		else:
			ret = ""

		ret += str(self)

		if show_bundled:
			ret += bundled_str[0] if self.bundled else bundled_str[1]

		if show_location and self.location:
			ret += location_str.format(location=self.location)

		return ret

	def get_hook(self, hook):
		"""
		Arguments:
		    hook (str): Hook to return.

		Returns:
		    callable or None: Handler for the requested ``hook`` or None if no handler is registered.
		"""

		if not hook in self.hooks:
			return None
		return self.hooks[hook]

	def get_implementation(self, *types):
		"""
		Arguments:
		    types (list): List of :class:`Plugin` sub classes all returned implementations need to implement.

		Returns:
		    object: The plugin's implementation if it matches all of the requested ``types``, None otherwise.
		"""

		if not self.implementation:
			return None

		for t in types:
			if not isinstance(self.implementation, t):
				return None

		return self.implementation

	@property
	def name(self):
		"""
		Human readable name of the plugin. Will be taken from name attribute of the plugin module if available,
		otherwise from the ``name`` supplied during construction with a fallback to ``key``.

		Returns:
		    str: Name of the plugin, fallback is the plugin's identifier.
		"""
		return self._get_instance_attribute(self.__class__.attr_name, defaults=(self._name, self.key))

	@property
	def description(self):
		"""
		Description of the plugin. Will be taken from the description attribute of the plugin module as defined in
		:attr:`attr_description` if available, otherwise from the ``description`` supplied during construction.
		May be None.

		Returns:
		    str or None: Description of the plugin.
		"""
		return self._get_instance_attribute(self.__class__.attr_description, default=self._description)

	@property
	def version(self):
		"""
		Version of the plugin. Will be taken from the version attribute of the plugin module as defined in
		:attr:`attr_version` if available, otherwise from the ``version`` supplied during construction. May be None.

		Returns:
		    str or None: Version of the plugin.
		"""
		return self._version if self._version is not None else self._get_instance_attribute(self.__class__.attr_version, default=self._version)

	@property
	def author(self):
		"""
		Author of the plugin. Will be taken from the author attribute of the plugin module as defined in
		:attr:`attr_author` if available, otherwise from the ``author`` supplied during construction. May be None.

		Returns:
		    str or None: Author of the plugin.
		"""
		return self._get_instance_attribute(self.__class__.attr_author, default=self._author)

	@property
	def url(self):
		"""
		Website URL for the plugin. Will be taken from the url attribute of the plugin module as defined in
		:attr:`attr_url` if available, otherwise from the ``url`` supplied during construction. May be None.

		Returns:
		    str or None: Website URL for the plugin.
		"""
		return self._get_instance_attribute(self.__class__.attr_url, default=self._url)

	@property
	def license(self):
		"""
		License of the plugin. Will be taken from the license attribute of the plugin module as defined in
		:attr:`attr_license` if available, otherwise from the ``license`` supplied during construction. May be None.

		Returns:
		    str or None: License of the plugin.
		"""
		return self._get_instance_attribute(self.__class__.attr_license, default=self._license)

	@property
	def hooks(self):
		"""
		Hooks provided by the plugin. Will be taken from the hooks attribute of the plugin module as defiend in
		:attr:`attr_hooks` if available, otherwise an empty dictionary is returned.

		Returns:
		    dict: Hooks provided by the plugin.
		"""
		return self._get_instance_attribute(self.__class__.attr_hooks, default={})

	@property
	def implementation(self):
		"""
		Implementation provided by the plugin. Will be taken from the implementation attribute of the plugin module
		as defined in :attr:`attr_implementation` if available, otherwise None is returned.

		Returns:
		    object: Implementation provided by the plugin.
		"""
		return self._get_instance_attribute(self.__class__.attr_implementation, default=None)

	@property
	def helpers(self):
		"""
		Helpers provided by the plugin. Will be taken from the helpers attribute of the plugin module as defined in
		:attr:`attr_helpers` if available, otherwise an empty list is returned.

		Returns:
		    dict: Helpers provided by the plugin.
		"""
		return self._get_instance_attribute(self.__class__.attr_helpers, default={})

	@property
	def check(self):
		"""
		Method for pre-load check of plugin. Will be taken from the check attribute of the plugin module as defined in
		:attr:`attr_check` if available, otherwise a lambda always returning True is returned.

		Returns:
		    callable: Check method for the plugin module which should return True if the plugin can be loaded, False
		        otherwise.
		"""
		return self._get_instance_attribute(self.__class__.attr_check, default=lambda: True)

	@property
	def load(self):
		"""
		Method for loading the plugin module. Will be taken from the load attribute of the plugin module as defined
		in :attr:`attr_load` if available, otherwise a no-operation lambda will be returned.

		Returns:
		    callable: Init method for the plugin module.
		"""
		load = self._get_instance_attribute(self.__class__.attr_load, default=None)
		if load is None:
			load = self._get_instance_attribute(self.__class__.attr_init, default=lambda:True)
		return load

	@property
	def unload(self):
		return self._get_instance_attribute(self.__class__.attr_unload, default=lambda: True)

	@property
	def activate(self):
		return self._get_instance_attribute(self.__class__.attr_activate, default=lambda: True)

	@property
	def deactivate(self):
		return self._get_instance_attribute(self.__class__.attr_deactivate, default=lambda: True)

	@property
	def enable(self):
		self.enabled = True
		return self._get_instance_attribute(self.__class__.attr_enable, default=lambda: True)

	@property
	def disable(self):
		self.enabled = False
		return self._get_instance_attribute(self.__class__.attr_disable, default=lambda: True)

	def _get_instance_attribute(self, attr, default=None, defaults=None):
		if not hasattr(self.instance, attr):
			if defaults is not None:
				for value in defaults:
					if value is not None:
						return value
			return default
		return getattr(self.instance, attr)


class PluginManager(object):
	"""
	The :class:`PluginManager` is the central component for finding, loading and accessing plugins provided to the
	system.

	It is able to discover plugins both through possible file system locations as well as customizable entry points.
	"""

	def __init__(self, plugin_folders, plugin_types, plugin_entry_points, logging_prefix=None, plugin_disabled_list=None):
		self.logger = logging.getLogger(__name__)

		if logging_prefix is None:
			logging_prefix = ""
		if plugin_disabled_list is None:
			plugin_disabled_list = []

		self.plugin_folders = plugin_folders
		self.plugin_types = plugin_types
		self.plugin_entry_points = plugin_entry_points
		self.plugin_disabled_list = plugin_disabled_list
		self.logging_prefix = logging_prefix

		self.plugins = dict()
		self.plugin_hooks = defaultdict(list)
		self.plugin_implementations = dict()
		self.plugin_implementations_by_type = defaultdict(list)

		self.implementation_injects = dict()
		self.implementation_inject_factories = []

		self.disabled_plugins = dict()

		self.on_plugin_loaded = lambda *args, **kwargs: None
		self.on_plugin_unloaded = lambda *args, **kwargs: None
		self.on_plugin_activated = lambda *args, **kwargs: None
		self.on_plugin_deactivated = lambda *args, **kwargs: None
		self.on_plugin_enabled = lambda *args, **kwargs: None
		self.on_plugin_disabled = lambda *args, **kwargs: None
		self.on_plugin_implementations_initialized = lambda *args, **kwargs: None

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

				plugin = self._import_plugin_from_module(key, folder=folder)
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

				plugin = self._import_plugin_from_module(key, **kwargs)
				if plugin:
					plugin.origin = ("entry_point", group, module_name)

					if self._is_plugin_disabled(key):
						plugin.enabled = False
						disabled_plugins[key] = plugin
					else:
						plugins[key] = plugin

		return plugins, disabled_plugins

	def _import_plugin_from_module(self, key, folder=None, module_name=None, name=None, version=None, summary=None, author=None, url=None, license=None):
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

		plugin = self._import_plugin(key, *module, name=name, version=version, summary=summary, author=author, url=url, license=license)
		if plugin:
			if plugin.check():
				return plugin
			else:
				self.logger.warn("Plugin \"{plugin}\" did not pass check".format(plugin=str(plugin)))
				return None


	def _import_plugin(self, key, f, filename, description, name=None, version=None, summary=None, author=None, url=None, license=None):
		try:
			instance = imp.load_module(key, f, filename, description)
			return PluginInfo(key, filename, instance, name=name, version=version, description=summary, author=author, url=url, license=license)
		except:
			self.logger.exception("Error loading plugin {key}, disabling it".format(key=key))
			return None

	def _is_plugin_disabled(self, key):
		return key in self.plugin_disabled_list or key.endswith('disabled')

	def reload_plugins(self):
		self.logger.info("Loading plugins from {folders} and installed plugin packages...".format(
			folders=", ".join(map(lambda x: x[0] if isinstance(x, tuple) else str(x), self.plugin_folders))
		))
		plugins, disabled_plugins = self._find_plugins()

		self.disabled_plugins = disabled_plugins

		for name, plugin in plugins.items():
			self.load_plugin(name, plugin)

		if len(self.plugins) <= 0:
			self.logger.info("No plugins found")
		else:
			self.logger.info("Found {count} plugin(s) providing {implementations} mixin implementations, {hooks} hook handlers".format(
				count=len(self.plugins) + len(self.disabled_plugins),
				implementations=len(self.plugin_implementations),
				hooks=sum(map(lambda x: len(x), self.plugin_hooks.values()))
			))

	@property
	def all_plugins(self):
		plugins = dict(self.plugins)
		plugins.update(self.disabled_plugins)
		return plugins

	def load_plugin(self, name, plugin):
		try:
			plugin.load()
			self._activate_plugin(name, plugin)
		except:
			self.logger.exception("There was an error loading plugin %s" % name)
			self.disabled_plugins[name] = plugin
		else:
			self.plugins[name] = plugin
			self.on_plugin_loaded(name, plugin)
			self.logger.debug("Loaded plugin {name}: {plugin}".format(**locals()))

	def unload_plugin(self, name):
		if not name in self.plugins:
			if name in self.disabled_plugins:
				plugin = self.disabled_plugins[name]
			else:
				self.logger.warn("Trying to unload unknown plugin {name}".format(**locals()))
				return
		else:
			plugin = self.plugins[name]

		try:
			self._deactivate_plugin(name, plugin)
			plugin.unload()
			if name in self.plugins:
				del self.plugins[name]
			if name in self.disabled_plugins:
				del self.disabled_plugins[name]
		except:
			self.logger.exception("There was an error unloading plugin {name}".format(**locals()))
		else:
			self.on_plugin_unloaded(name, plugin)
			self.logger.debug("Unloaded plugin {name}: {plugin}".format(**locals()))

	def enable_plugin(self, name):
		if not name in self.disabled_plugins:
			self.logger.warn("Tried to enable plugin {name}, however it is not disabled".format(**locals()))
			return

		plugin = self.disabled_plugins[name]

		try:
			del self.disabled_plugins[name]
			plugin.enable()
			self._activate_plugin(name, plugin)
			self.initialize_implementation_of_plugin(name, plugin)
			self.plugins[name] = plugin
		except:
			self.logger.exception("There was an error while enabling plugin {name}".format(**locals()))
			self.disabled_plugins[name] = plugin
		else:
			self.on_plugin_enabled(name, plugin)
			self.logger.debug("Enabled plugin {name}: {plugin}".format(**locals()))

	def disable_plugin(self, name):
		if not name in self.plugins:
			self.logger.warn("Tried to disable plugin {name}, however it is not enabled".format(**locals()))
			return

		plugin = self.plugins[name]

		try:
			del self.plugins[name]
			plugin.disable()
			self._deactivate_plugin(name, plugin)
			self.disabled_plugins[name] = plugin
		except:
			self.logger.exception("There was an error while disabling plugin {name}".format(**locals()))
			self.plugins[name] = plugin
		else:
			self.on_plugin_disabled(name, plugin)
			self.logger.debug("Disabled plugin {name}: {plugin}".format(**locals()))

	def _activate_plugin(self, name, plugin):
		plugin.activate()

		# evaluate registered hooks
		for hook, callback in plugin.hooks.items():
			self.plugin_hooks[hook].append((name, callback))

		# evaluate registered implementation
		if plugin.implementation:
			for plugin_type in self.plugin_types:
				if isinstance(plugin.implementation, plugin_type):
					self.plugin_implementations_by_type[plugin_type].append((name, plugin.implementation))

			self.plugin_implementations[name] = plugin.implementation

		self.on_plugin_activated(name, plugin)

	def _deactivate_plugin(self, name, plugin):
		plugin.deactivate()
		for hook, callback in plugin.hooks.items():
			self.plugin_hooks[hook].remove((name, callback))

		if plugin.implementation is not None:
			del self.plugin_implementations[name]
			for plugin_type in self.plugin_types:
				try:
					self.plugin_implementations_by_type[plugin_type].remove((name, plugin.implementation))
				except ValueError:
					# that's ok, the plugin was just not registered for the type
					pass

		self.on_plugin_deactivated(name, plugin)

	def initialize_implementations(self, additional_injects=None, additional_inject_factories=None):
		for name, plugin in self.plugins.items():
			self.initialize_implementation_of_plugin(name, plugin,
			                                         additional_injects=additional_injects,
			                                         additional_inject_factories=additional_inject_factories)

		self.logger.info("Initialized {count} plugin(s)".format(count=len(self.plugin_implementations)))

	def initialize_implementation_of_plugin(self, name, plugin, additional_injects=None, additional_inject_factories=None):
		if plugin.implementation is None:
			return

		self.initialize_implementation(name, plugin, plugin.implementation,
		                               additional_injects=additional_injects,
		                               additional_inject_factories=additional_inject_factories)

	def initialize_implementation(self, name, plugin, implementation, additional_injects=None, additional_inject_factories=None):
		if additional_injects is None:
			additional_injects = dict()
		if additional_inject_factories is None:
			additional_inject_factories = []

		injects = self.implementation_injects
		injects.update(additional_injects)

		inject_factories = self.implementation_inject_factories
		inject_factories += additional_inject_factories

		try:
			kwargs = dict(injects)

			kwargs.update(dict(
				identifier=name,
				plugin_name=plugin.name,
				plugin_version=plugin.version,
				basefolder=os.path.realpath(plugin.location),
				logger=logging.getLogger(self.logging_prefix + name),
				))

			# inject the additional_injects
			for arg, value in kwargs.items():
				setattr(implementation, "_" + arg, value)

			# inject any injects produced in the additional_inject_factories
			for factory in inject_factories:
				try:
					return_value = factory(name, implementation)
				except:
					self.logger.exception("Exception while executing injection factory %r" % factory)
				else:
					if return_value is not None:
						if isinstance(return_value, dict):
							for arg, value in return_value.items():
								setattr(implementation, "_" + arg, value)

			result = implementation.initialize()
			if result is not None and not result:
				self.logger.warn("Initialization of {name} returned False, disabling it".format(**locals()))
				self._deactivate_plugin(name, plugin)
				return
		except:
			self.logger.exception("Exception while initializing plugin {name}, disabling it".format(**locals()))
			self._deactivate_plugin(name, plugin)
		else:
			self.on_plugin_implementations_initialized(name, plugin)

		self.logger.debug("Initialized plugin mixin implementation for plugin {name}".format(**locals()))


	def log_all_plugins(self, show_bundled=True, bundled_str=(" (bundled)", ""), show_location=True, location_str=" = {location}", show_enabled=True, enabled_str=(" ", "!")):
		all_plugins = self.plugins.values() + self.disabled_plugins.values()

		if len(all_plugins) <= 0:
			self.logger.info("No plugins available")
		else:
			self.logger.info("{count} plugin(s) registered with the system:\n{plugins}".format(count=len(all_plugins), plugins="\n".join(
				sorted(
					map(lambda x: "| " + x.long_str(show_bundled=show_bundled,
					                                bundled_str=bundled_str,
					                                show_location=show_location,
					                                location_str=location_str,
					                                show_enabled=show_enabled,
					                                enabled_str=enabled_str),
					    self.plugins.values())
				)
			)))

	def get_plugin(self, identifier, require_enabled=True):
		"""
		Retrieves the module of the plugin identified by ``identifier``. If the plugin is not registered or disabled and
		``required_enabled`` is True (the default) None will be returned.

		Arguments:
		    identifier (str): The identifier of the plugin to retrieve.
		    require_enabled (boolean): Whether to only return the plugin if is enabled (True, default) or also if it's
		        disabled.

		Returns:
		    module: The requested plugin module or None
		"""

		plugin_info = self.get_plugin_info(identifier, require_enabled=require_enabled)
		if plugin_info is not None:
			return plugin_info.instance
		return None

	def get_plugin_info(self, identifier, require_enabled=True):
		"""
		Retrieves the :class:`PluginInfo` instance identified by ``identifier``. If the plugin is not registered or
		disabled and ``required_enabled`` is True (the default) None will be returned.

		Arguments:
		    identifier (str): The identifier of the plugin to retrieve.
		    require_enabled (boolean): Whether to only return the plugin if is enabled (True, default) or also if it's
		        disabled.

		Returns:
		    ~.PluginInfo: The requested :class:`PluginInfo` or None
		"""

		if identifier in self.plugins:
			return self.plugins[identifier]
		elif not require_enabled and identifier in self.disabled_plugins:
			return self.disabled_plugins[identifier]

		return None

	def get_hooks(self, hook):
		"""
		Retrieves all registered handlers for the specified hook.

		Arguments:
		    hook (str): The hook for which to retrieve the handlers.

		Returns:
		    dict: A dict containing all registered handlers mapped by their plugin's identifier.
		"""

		if not hook in self.plugin_hooks:
			return dict()
		return {hook[0]: hook[1] for hook in self.plugin_hooks[hook]}

	def get_implementations(self, *types):
		"""
		Get all mixin implementations that implement *all* of the provided ``types``.

		Arguments:
		    types (one or more type): The types a mixin implementation needs to implement in order to be returned.

		Returns:
		    list: A list of all found implementations
		"""

		result = None

		for t in types:
			implementations = self.plugin_implementations_by_type[t]
			if result is None:
				result = set(implementations)
			else:
				result = result.intersection(implementations)

		if result is None:
			return dict()
		return [impl[1] for impl in result]

	def get_filtered_implementations(self, f, *types):
		"""
		Get all mixin implementation that implementat *all* of the provided ``types`` and match the provided filter `f`.

		Arguments:
		    f (callable): A filter function returning True for implementations to return and False for those to exclude.
		    types (one or more type): The types a mixin implementation needs to implement in order to be returned.

		Returns:
		    list: A list of all found and matching implementations.
		"""

		assert callable(f)
		implementations = self.get_implementations(*types)
		return filter(f, implementations)

	def get_helpers(self, name, *helpers):
		"""
		Retrieves the named ``helpers`` for the plugin with identifier ``name``.

		If the plugin is not available, returns None. Otherwise returns a :class:`dict` with the requested plugin
		helper names mapped to the method - if a helper could not be resolved, it will be missing from the dict.

		Arguments:
		    name (str): Identifier of the plugin for which to look up the ``helpers``.
		    helpers (one or more str): Identifiers of the helpers of plugin ``name`` to return.

		Returns:
		    dict: A dictionary of all resolved helpers, mapped by their identifiers, or None if the plugin was not
		        registered with the system.
		"""

		if not name in self.plugins:
			return None
		plugin = self.plugins[name]

		all_helpers = plugin.helpers
		if len(helpers):
			return dict((k, v) for (k, v) in all_helpers.items() if k in helpers)
		else:
			return all_helpers

	def register_message_receiver(self, client):
		"""
		Registers a ``client`` for receiving plugin messages. The ``client`` needs to be a callable accepting two
		input arguments, ``plugin`` (the sending plugin's identifier) and ``data`` (the message itself).
		"""

		if client is None:
			return
		self.registered_clients.append(client)

	def unregister_message_receiver(self, client):
		"""
		Unregisters a ``client`` for receiving plugin messages.
		"""

		self.registered_clients.remove(client)

	def send_plugin_message(self, plugin, data):
		"""
		Sends ``data`` in the name of ``plugin`` to all currently registered message receivers by invoking them
		with the two arguments.

		Arguments:
		    plugin (str): The sending plugin's identifier.
		    data (object): The message.
		"""

		for client in self.registered_clients:
			try: client(plugin, data)
			except: self.logger.exception("Exception while sending plugin data to client")


class Plugin(object):
	"""
	The parent class of all plugin implementations.

	.. attribute:: _identifier

	   The identifier of the plugin. Injected by the plugin core system upon initialization of the implementation.

	.. attribute:: _plugin_name

	   The name of the plugin. Injected by the plugin core system upon initialization of the implementation.

	.. attribute:: _plugin_version

	   The version of the plugin. Injected by the plugin core system upon initialization of the implementation.

	.. attribute:: _basefolder

	   The base folder of the plugin. Injected by the plugin core system upon initialization of the implementation.

	.. attribute:: _logger

	   The logger instance to use, with the logging name set to the :attr:`PluginManager.logging_prefix` of the
	   :class:`PluginManager` concatenated with :attr:`_identifier`. Injected by the plugin core system upon
	   initialization of the implementation.
	"""

	def initialize(self):
		"""
		Called by the plugin core after performing all injections. Override this to initialize your implementation.
		"""
		pass
