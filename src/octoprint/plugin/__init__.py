# coding=utf-8
"""
This module represents OctoPrint's plugin subsystem. This includes management and helper methods as well as the
registered plugin types.

.. autofunction:: plugin_manager

.. autofunction:: plugin_settings

.. autofunction:: call_plugin

.. autoclass:: PluginSettings
   :members:
"""

from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import os
import logging

from octoprint.settings import settings as s
from octoprint.plugin.core import (PluginInfo, PluginManager, Plugin)
from octoprint.plugin.types import *

from octoprint.util import deprecated

# singleton
_instance = None

def _validate_plugin(phase, plugin_info):
	if phase == "after_load":
		if plugin_info.implementation is not None and isinstance(plugin_info.implementation, AppPlugin):
			# transform app plugin into hook
			import warnings
			warnings.warn("{name} uses deprecated plugin mixin AppPlugin, use octoprint.accesscontrol.appkey hook instead".format(name=plugin_info.key), DeprecationWarning)

			hooks = plugin_info.hooks
			if not "octoprint.accesscontrol.appkey" in hooks:
				hooks["octoprint.accesscontrol.appkey"] = plugin_info.implementation.get_additional_apps
			setattr(plugin_info.instance, PluginInfo.attr_hooks, hooks)

def plugin_manager(init=False, plugin_folders=None, plugin_types=None, plugin_entry_points=None, plugin_disabled_list=None,
                   plugin_restart_needing_hooks=None, plugin_obsolete_hooks=None, plugin_validators=None, settings=None):
	"""
	Factory method for initially constructing and consecutively retrieving the :class:`~octoprint.plugin.core.PluginManager`
	singleton.

	Arguments:
	    init (boolean): A flag indicating whether this is the initial call to construct the singleton (True) or not
	        (False, default). If this is set to True and the plugin manager has already been initialized, a :class:`ValueError`
	        will be raised. The same will happen if the plugin manager has not yet been initialized and this is set to
	        False.
	    plugin_folders (list): A list of folders (as strings containing the absolute path to them) in which to look for
	        potential plugin modules. If not provided this defaults to the configured ``plugins`` base folder and
	        ``src/plugins`` within OctoPrint's code base.
	    plugin_types (list): A list of recognized plugin types for which to look for provided implementations. If not
	        provided this defaults to the plugin types found in :mod:`octoprint.plugin.types` without
	        :class:`~octoprint.plugin.OctoPrintPlugin`.
	    plugin_entry_points (list): A list of entry points pointing to modules which to load as plugins. If not provided
	        this defaults to the entry point ``octoprint.plugin``.
	    plugin_disabled_list (list): A list of plugin identifiers that are currently disabled. If not provided this
	        defaults to all plugins for which ``enabled`` is set to ``False`` in the settings.
	    plugin_restart_needing_hooks (list): A list of hook namespaces which cause a plugin to need a restart in order
	        be enabled/disabled. Does not have to contain full hook identifiers, will be matched with startswith similar
	        to logging handlers
	    plugin_obsolete_hooks (list): A list of hooks that have been declared obsolete. Plugins implementing them will
	        not be enabled since they might depend on functionality that is no longer available.
	    plugin_validators (list): A list of additional plugin validators through which to process each plugin.

	Returns:
	    PluginManager: A fully initialized :class:`~octoprint.plugin.core.PluginManager` instance to be used for plugin
	        management tasks.

	Raises:
	    ValueError: ``init`` was True although the plugin manager was already initialized, or it was False although
	        the plugin manager was not yet initialized.
	"""

	global _instance
	if _instance is not None:
		if init:
			raise ValueError("Plugin Manager already initialized")

	else:
		if init:
			if settings is None:
				settings = s()

			if plugin_folders is None:
				plugin_folders = (
					settings.getBaseFolder("plugins"),
					(os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "plugins")), True)
				)
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
				                ProgressPlugin,
				                WizardPlugin,
				                UiPlugin]
			if plugin_entry_points is None:
				plugin_entry_points = "octoprint.plugin"
			if plugin_disabled_list is None:
				plugin_disabled_list = settings.get(["plugins", "_disabled"])
			if plugin_restart_needing_hooks is None:
				plugin_restart_needing_hooks = [
					"octoprint.server.http"
				]
			if plugin_obsolete_hooks is None:
				plugin_obsolete_hooks = [
					"octoprint.comm.protocol.gcode"
				]
			if plugin_validators is None:
				plugin_validators = [
					_validate_plugin
				]

			_instance = PluginManager(plugin_folders,
			                          plugin_types,
			                          plugin_entry_points,
			                          logging_prefix="octoprint.plugins.",
			                          plugin_disabled_list=plugin_disabled_list,
			                          plugin_restart_needing_hooks=plugin_restart_needing_hooks,
			                          plugin_obsolete_hooks=plugin_obsolete_hooks,
			                          plugin_validators=plugin_validators)
		else:
			raise ValueError("Plugin Manager not initialized yet")
	return _instance


def plugin_settings(plugin_key, defaults=None, get_preprocessors=None, set_preprocessors=None, settings=None):
	"""
	Factory method for creating a :class:`PluginSettings` instance.

	Arguments:
	    plugin_key (string): The plugin identifier for which to create the settings instance.
	    defaults (dict): The default settings for the plugin.
	    get_preprocessors (dict): The getter preprocessors for the plugin.
	    set_preprocessors (dict): The setter preprocessors for the plugin.
	    settings (octoprint.settings.Settings): The settings instance to use.

	Returns:
	    PluginSettings: A fully initialized :class:`PluginSettings` instance to be used to access the plugin's
	        settings
	"""
	if settings is None:
		settings = s()
	return PluginSettings(settings, plugin_key, defaults=defaults,
	                      get_preprocessors=get_preprocessors,
	                      set_preprocessors=set_preprocessors)


def plugin_settings_for_settings_plugin(plugin_key, instance, settings=None):
	"""
	Factory method for creating a :class:`PluginSettings` instance for a given :class:`SettingsPlugin` instance.

	Will return `None` if the provided `instance` is not a :class:`SettingsPlugin` instance.

	Arguments:
	    plugin_key (string): The plugin identifier for which to create the settings instance.
	    implementation (octoprint.plugin.SettingsPlugin): The :class:`SettingsPlugin` instance.
	    settings (octoprint.settings.Settings): The settings instance to use. Defaults to the global OctoPrint settings.

	Returns:
	    PluginSettings or None: A fully initialized :class:`PluginSettings` instance to be used to access the plugin's
	        settings, or `None` if the provided `instance` was not a class:`SettingsPlugin`
	"""
	if not isinstance(instance, SettingsPlugin):
		return None

	try:
		defaults = instance.get_settings_defaults()
		get_preprocessors, set_preprocessors = instance.get_settings_preprocessors()
	except:
		logging.getLogger(__name__).exception("Error while retrieving defaults or preprocessors for plugin {}".format(plugin_key))
		return None

	return plugin_settings(plugin_key, defaults=defaults, get_preprocessors=get_preprocessors, set_preprocessors=set_preprocessors, settings=settings)


def call_plugin(types, method, args=None, kwargs=None, callback=None, error_callback=None, sorting_context=None):
	"""
	Helper method to invoke the indicated ``method`` on all registered plugin implementations implementing the
	indicated ``types``. Allows providing method arguments and registering callbacks to call in case of success
	and/or failure of each call which can be used to return individual results to the calling code.

	Example:

	.. sourcecode:: python

	   def my_success_callback(name, plugin, result):
	       print("{name} was called successfully and returned {result!r}".format(**locals()))

	   def my_error_callback(name, plugin, exc):
	       print("{name} raised an exception: {exc!s}".format(**locals()))

	   octoprint.plugin.call_plugin(
	       [octoprint.plugin.StartupPlugin],
	       "on_startup",
	       args=(my_host, my_port),
	       callback=my_success_callback,
	       error_callback=my_error_callback
	   )

	Arguments:
	    types (list): A list of plugin implementation types to match against.
	    method (string): Name of the method to call on all matching implementations.
	    args (tuple): A tuple containing the arguments to supply to the called ``method``. Optional.
	    kwargs (dict): A dictionary containing the keyword arguments to supply to the called ``method``. Optional.
	    callback (function): A callback to invoke after an implementation has been called successfully. Will be called
	        with the three arguments ``name``, ``plugin`` and ``result``. ``name`` will be the plugin identifier,
	        ``plugin`` the plugin implementation instance itself and ``result`` the result returned from the
	        ``method`` invocation.
	    error_callback (function): A callback to invoke after the call of an implementation resulted in an exception.
	        Will be called with the three arguments ``name``, ``plugin`` and ``exc``. ``name`` will be the plugin
	        identifier, ``plugin`` the plugin implementation instance itself and ``exc`` the caught exception.

	"""

	if not isinstance(types, (list, tuple)):
		types = [types]
	if args is None:
		args = []
	if kwargs is None:
		kwargs = dict()

	plugins = plugin_manager().get_implementations(*types, sorting_context=sorting_context)
	for plugin in plugins:
		if hasattr(plugin, method):
			try:
				result = getattr(plugin, method)(*args, **kwargs)
				if callback:
					callback(plugin._identifier, plugin, result)
			except Exception as exc:
				logging.getLogger(__name__).exception("Error while calling plugin %s" % plugin._identifier)
				if error_callback:
					error_callback(plugin._identifier, plugin, exc)


class PluginSettings(object):
	"""
	The :class:`PluginSettings` class is the interface for plugins to their own or globally defined settings.

	It provides a couple of convenience methods for directly accessing plugin settings via the regular
	:class:`octoprint.settings.Settings` interfaces as well as means to access plugin specific folder locations.

	All getter and setter methods will ensure that plugin settings are stored in their correct location within the
	settings structure by modifying the supplied paths accordingly.

	Arguments:
	    settings (Settings): The :class:`~octoprint.settings.Settings` instance on which to operate.
	    plugin_key (str): The plugin identifier of the plugin for which to create this instance.
	    defaults (dict): The plugin's defaults settings, will be used to determine valid paths within the plugin's
	        settings structure

	.. method:: get(path, merged=False, asdict=False)

	   Retrieves a raw value from the settings for ``path``, optionally merging the raw value with the default settings
	   if ``merged`` is set to True.

	   :param path: The path for which to retrieve the value.
	   :type path: list, tuple
	   :param boolean merged: Whether to merge the returned result with the default settings (True) or not (False,
	       default).
	   :returns: The retrieved settings value.
	   :rtype: object

	.. method:: get_int(path)

	   Like :func:`get` but tries to convert the retrieved value to ``int``.

	.. method:: get_float(path)

	   Like :func:`get` but tries to convert the retrieved value to ``float``.

	.. method:: get_boolean(path)

	   Like :func:`get` but tries to convert the retrieved value to ``boolean``.

	.. method:: set(path, value, force=False)

	   Sets the raw value on the settings for ``path``.

	   :param path: The path for which to retrieve the value.
	   :type path: list, tuple
	   :param object value: The value to set.
	   :param boolean force: If set to True, the modified configuration will even be written back to disk if
	       the value didn't change.

	.. method:: set_int(path, value, force=False)

	   Like :func:`set` but ensures the value is an ``int`` through attempted conversion before setting it.

	.. method:: set_float(path, value, force=False)

	   Like :func:`set` but ensures the value is an ``float`` through attempted conversion before setting it.

	.. method:: set_boolean(path, value, force=False)

	   Like :func:`set` but ensures the value is an ``boolean`` through attempted conversion before setting it.
	"""

	def __init__(self, settings, plugin_key, defaults=None, get_preprocessors=None, set_preprocessors=None):
		self.settings = settings
		self.plugin_key = plugin_key

		if defaults is None:
			defaults = dict()
		self.defaults = dict(plugins=dict())
		self.defaults["plugins"][plugin_key] = defaults
		self.defaults["plugins"][plugin_key]["_config_version"] = None

		if get_preprocessors is None:
			get_preprocessors = dict()
		self.get_preprocessors = dict(plugins=dict())
		self.get_preprocessors["plugins"][plugin_key] = get_preprocessors

		if set_preprocessors is None:
			set_preprocessors = dict()
		self.set_preprocessors = dict(plugins=dict())
		self.set_preprocessors["plugins"][plugin_key] = set_preprocessors

		def prefix_path_in_args(args, index=0):
			result = []
			if index == 0:
				result.append(self._prefix_path(args[0]))
				result.extend(args[1:])
			else:
				args_before = args[:index - 1]
				args_after = args[index + 1:]
				result.extend(args_before)
				result.append(self._prefix_path(args[index]))
				result.extend(args_after)
			return result

		def add_getter_kwargs(kwargs):
			if not "defaults" in kwargs:
				kwargs.update(defaults=self.defaults)
			if not "preprocessors" in kwargs:
				kwargs.update(preprocessors=self.get_preprocessors)
			return kwargs

		def add_setter_kwargs(kwargs):
			if not "defaults" in kwargs:
				kwargs.update(defaults=self.defaults)
			if not "preprocessors" in kwargs:
				kwargs.update(preprocessors=self.set_preprocessors)
			return kwargs

		self.access_methods = dict(
			has        =("has",        prefix_path_in_args, add_getter_kwargs),
			get        =("get",        prefix_path_in_args, add_getter_kwargs),
			get_int    =("getInt",     prefix_path_in_args, add_getter_kwargs),
			get_float  =("getFloat",   prefix_path_in_args, add_getter_kwargs),
			get_boolean=("getBoolean", prefix_path_in_args, add_getter_kwargs),
			set        =("set",        prefix_path_in_args, add_setter_kwargs),
			set_int    =("setInt",     prefix_path_in_args, add_setter_kwargs),
			set_float  =("setFloat",   prefix_path_in_args, add_setter_kwargs),
			set_boolean=("setBoolean", prefix_path_in_args, add_setter_kwargs),
			remove     =("remove",     prefix_path_in_args, lambda x: x)
		)
		self.deprecated_access_methods = dict(
			getInt    ="get_int",
			getFloat  ="get_float",
			getBoolean="get_boolean",
			setInt    ="set_int",
			setFloat  ="set_float",
			setBoolean="set_boolean"
		)

	def _prefix_path(self, path=None):
		if path is None:
			path = list()
		return ['plugins', self.plugin_key] + path

	def global_has(self, path, **kwargs):
		return self.settings.has(path, **kwargs)

	def global_remove(self, path, **kwargs):
		return self.settings.remove(path, **kwargs)

	def global_get(self, path, **kwargs):
		"""
		Getter for retrieving settings not managed by the plugin itself from the core settings structure. Use this
		to access global settings outside of your plugin.

		Directly forwards to :func:`octoprint.settings.Settings.get`.
		"""
		return self.settings.get(path, **kwargs)

	def global_get_int(self, path, **kwargs):
		"""
		Like :func:`global_get` but directly forwards to :func:`octoprint.settings.Settings.getInt`.
		"""
		return self.settings.getInt(path, **kwargs)

	def global_get_float(self, path, **kwargs):
		"""
		Like :func:`global_get` but directly forwards to :func:`octoprint.settings.Settings.getFloat`.
		"""
		return self.settings.getFloat(path, **kwargs)

	def global_get_boolean(self, path, **kwargs):
		"""
		Like :func:`global_get` but directly orwards to :func:`octoprint.settings.Settings.getBoolean`.
		"""
		return self.settings.getBoolean(path, **kwargs)

	def global_set(self, path, value, **kwargs):
		"""
		Setter for modifying settings not managed by the plugin itself on the core settings structure. Use this
		to modify global settings outside of your plugin.

		Directly forwards to :func:`octoprint.settings.Settings.set`.
		"""
		self.settings.set(path, value, **kwargs)

	def global_set_int(self, path, value, **kwargs):
		"""
		Like :func:`global_set` but directly forwards to :func:`octoprint.settings.Settings.setInt`.
		"""
		self.settings.setInt(path, value, **kwargs)

	def global_set_float(self, path, value, **kwargs):
		"""
		Like :func:`global_set` but directly forwards to :func:`octoprint.settings.Settings.setFloat`.
		"""
		self.settings.setFloat(path, value, **kwargs)

	def global_set_boolean(self, path, value, **kwargs):
		"""
		Like :func:`global_set` but directly forwards to :func:`octoprint.settings.Settings.setBoolean`.
		"""
		self.settings.setBoolean(path, value, **kwargs)

	def global_get_basefolder(self, folder_type, **kwargs):
		"""
		Retrieves a globally defined basefolder of the given ``folder_type``. Directly forwards to
		:func:`octoprint.settings.Settings.getBaseFolder`.
		"""
		return self.settings.getBaseFolder(folder_type, **kwargs)

	def get_plugin_logfile_path(self, postfix=None):
		"""
		Retrieves the path to a logfile specifically for the plugin. If ``postfix`` is not supplied, the logfile
		will be named ``plugin_<plugin identifier>.log`` and located within the configured ``logs`` folder. If a
		postfix is supplied, the name will be ``plugin_<plugin identifier>_<postfix>.log`` at the same location.

		Plugins may use this for specific logging tasks. For example, a :class:`~octoprint.plugin.SlicingPlugin` might
		want to create a log file for logging the output of the slicing engine itself if some debug flag is set.

		Arguments:
		    postfix (str): Postfix of the logfile for which to create the path. If set, the file name of the log file
		        will be ``plugin_<plugin identifier>_<postfix>.log``, if not it will be
		        ``plugin_<plugin identifier>.log``.

		Returns:
		    str: Absolute path to the log file, directly usable by the plugin.
		"""
		filename = "plugin_" + self.plugin_key
		if postfix is not None:
			filename += "_" + postfix
		filename += ".log"
		return os.path.join(self.settings.getBaseFolder("logs"), filename)

	@deprecated("PluginSettings.get_plugin_data_folder has been replaced by OctoPrintPlugin.get_plugin_data_folder",
	            includedoc="Replaced by :func:`~octoprint.plugin.types.OctoPrintPlugin.get_plugin_data_folder`",
	            since="1.2.0")
	def get_plugin_data_folder(self):
		path = os.path.join(self.settings.getBaseFolder("data"), self.plugin_key)
		if not os.path.isdir(path):
			os.makedirs(path)
		return path

	def get_all_data(self, **kwargs):
		merged = kwargs.get("merged", True)
		asdict = kwargs.get("asdict", True)
		defaults = kwargs.get("defaults", self.defaults)
		preprocessors = kwargs.get("preprocessors", self.get_preprocessors)

		kwargs.update(dict(
			merged=merged,
			asdict=asdict,
			defaults=defaults,
			preprocessors=preprocessors
		))

		return self.settings.get(self._prefix_path(), **kwargs)

	def clean_all_data(self):
		self.settings.remove(self._prefix_path())

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

				def _func(*args, **kwargs):
					return orig_func(*args_mapper(args), **kwargs_mapper(kwargs))
				_func.__name__ = item
				_func.__doc__ = orig_func.__doc__ if "__doc__" in dir(orig_func) else None

				return _func

		return getattr(self.settings, item)

	##~~ deprecated methods follow

	# TODO: Remove with release of 1.3.0

	globalGet            = deprecated("globalGet has been renamed to global_get",
	                                  includedoc="Replaced by :func:`global_get`",
	                                  since="1.2.0-dev-546")(global_get)
	globalGetInt         = deprecated("globalGetInt has been renamed to global_get_int",
	                                  includedoc="Replaced by :func:`global_get_int`",
	                                  since="1.2.0-dev-546")(global_get_int)
	globalGetFloat       = deprecated("globalGetFloat has been renamed to global_get_float",
	                                  includedoc="Replaced by :func:`global_get_float`",
	                                  since="1.2.0-dev-546")(global_get_float)
	globalGetBoolean     = deprecated("globalGetBoolean has been renamed to global_get_boolean",
	                                  includedoc="Replaced by :func:`global_get_boolean`",
	                                  since="1.2.0-dev-546")(global_get_boolean)
	globalSet            = deprecated("globalSet has been renamed to global_set",
	                                  includedoc="Replaced by :func:`global_set`",
	                                  since="1.2.0-dev-546")(global_set)
	globalSetInt         = deprecated("globalSetInt has been renamed to global_set_int",
	                                  includedoc="Replaced by :func:`global_set_int`",
	                                  since="1.2.0-dev-546")(global_set_int)
	globalSetFloat       = deprecated("globalSetFloat has been renamed to global_set_float",
	                                  includedoc="Replaced by :func:`global_set_float`",
	                                  since="1.2.0-dev-546")(global_set_float)
	globalSetBoolean     = deprecated("globalSetBoolean has been renamed to global_set_boolean",
	                                  includedoc="Replaced by :func:`global_set_boolean`",
	                                  since="1.2.0-dev-546")(global_set_boolean)
	globalGetBaseFolder  = deprecated("globalGetBaseFolder has been renamed to global_get_basefolder",
	                                  includedoc="Replaced by :func:`global_get_basefolder`",
	                                  since="1.2.0-dev-546")(global_get_basefolder)
	getPluginLogfilePath = deprecated("getPluginLogfilePath has been renamed to get_plugin_logfile_path",
	                                  includedoc="Replaced by :func:`get_plugin_logfile_path`",
	                                  since="1.2.0-dev-546")(get_plugin_logfile_path)
