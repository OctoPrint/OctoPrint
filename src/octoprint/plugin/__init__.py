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

from octoprint.settings import settings
from octoprint.plugin.core import (PluginInfo, PluginManager, Plugin)
from octoprint.plugin.types import *

from octoprint.util import deprecated

# singleton
_instance = None

def plugin_manager(init=False, plugin_folders=None, plugin_types=None, plugin_entry_points=None, plugin_disabled_list=None):
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

	Returns:
	    PluginManager: A fully initialized :class:`~octoprint.plugin.core.PluginManager` instance to be used for plugin
	        management tasks.

	Raises:
	    ValueError: ``init`` was True although the plugin manager was already initialized, or it was False although
	        the plugin manager was not yet initialized.
	"""

	global _instance
	if _instance is None:
		if init:
			if _instance is not None:
				raise ValueError("Plugin Manager already initialized")

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
	"""
	Factory method for creating a :class:`PluginSettings` instance.

	Arguments:
	    plugin_key (string): The plugin identifier for which to create the settings instance.
	    defaults (dict): The default settings for the plugin.

	Returns:
	    PluginSettings: A fully initialized :class:`PluginSettings` instance to be used to access the plugin's
	        settings
	"""
	return PluginSettings(settings(), plugin_key, defaults=defaults)


def call_plugin(types, method, args=None, kwargs=None, callback=None, error_callback=None):
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

	plugins = plugin_manager().get_implementations(*types)
	for name, plugin in plugins.items():
		if hasattr(plugin, method):
			try:
				result = getattr(plugin, method)(*args, **kwargs)
				if callback:
					callback(name, plugin, result)
			except Exception as exc:
				logging.getLogger(__name__).exception("Error while calling plugin %s" % name)
				if error_callback:
					error_callback(name, plugin, exc)


class PluginSettings(object):
	"""
	The :class:`PluginSettings` class is the interface for plugins to their own or globally defined settings.

	It provides a couple of convenience methods for directly accessing plugin settings via the regular
	:class:`octoprint.settings.Settings` interfaces as well as means to access plugin specific folder locations.

	.. method:: get(path, merged=False, asdict=False)

	   Retrieves a raw key from the settings for ``path``, optionally merging the raw value with the default settings
	   if ``merged`` is set to True.

	   :param list path:      a list of path elements to navigate to the settings value
	   :param boolean merged: whether to merge the returned result with the default settings (True) or not (False, default)
	   :return: the retrieved settings value

	.. method:: get_int(path)

	.. method:: get_float(path)

	.. method:: get_boolean(path)

	.. method:: set(path, value, force=False)

	.. method:: set_int(path, value, force=False)

	.. method:: set_float(path, value, force=False)

	.. method:: set_boolean(path, value, force=False)
	"""

	def __init__(self, settings, plugin_key, defaults=None):
		"""
		Initializes the object with the provided :class:`octoprint.settings.Settings` manager as ``settings``, using
		the ``plugin_key`` and optional ``defaults``.

		:param settings:
		:param plugin_key:
		:param defaults:
		:return:
		"""
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

	def global_get(self, path, **kwargs):
		return self.settings.get(path, **kwargs)

	def global_get_int(self, path, **kwargs):
		return self.settings.getInt(path, **kwargs)

	def global_get_float(self, path, **kwargs):
		return self.settings.getFloat(path, **kwargs)

	def global_get_boolean(self, path, **kwargs):
		return self.settings.getBoolean(path, **kwargs)

	def global_set(self, path, value, **kwargs):
		self.settings.set(path, value, **kwargs)

	def global_set_int(self, path, value, **kwargs):
		self.settings.setInt(path, value, **kwargs)

	def global_set_float(self, path, value, **kwargs):
		self.settings.setFloat(path, value, **kwargs)

	def global_set_boolean(self, path, value, **kwargs):
		self.settings.setBoolean(path, value, **kwargs)

	def global_get_basefolder(self, folder_type, **kwargs):
		return self.settings.getBaseFolder(folder_type, **kwargs)

	def get_plugin_logfile_path(self, postfix=None):
		filename = "plugin_" + self.plugin_key
		if postfix is not None:
			filename += "_" + postfix
		filename += ".log"
		return os.path.join(self.settings.getBaseFolder("logs"), filename)

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

	# TODO: Remove with release of 1.2.0

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
