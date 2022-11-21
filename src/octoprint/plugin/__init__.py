"""
This module represents OctoPrint's plugin subsystem. This includes management and helper methods as well as the
registered plugin types.

.. autofunction:: plugin_manager

.. autofunction:: plugin_settings

.. autofunction:: call_plugin

.. autoclass:: PluginSettings
   :members:
"""

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging
import os

from octoprint.plugin.core import Plugin, PluginInfo, PluginManager  # noqa: F401
from octoprint.plugin.types import *  # noqa: F401,F403 ## used by multiple other modules
from octoprint.plugin.types import OctoPrintPlugin, SettingsPlugin
from octoprint.settings import settings as s
from octoprint.util import deprecated

# singleton
_instance = None


def _validate_plugin(phase, plugin_info):
    return True


def plugin_manager(
    init=False,
    plugin_folders=None,
    plugin_bases=None,
    plugin_entry_points=None,
    plugin_disabled_list=None,
    plugin_sorting_order=None,
    plugin_blacklist=None,
    plugin_restart_needing_hooks=None,
    plugin_obsolete_hooks=None,
    plugin_considered_bundled=None,
    plugin_validators=None,
    compatibility_ignored_list=None,
):
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
        plugin_bases (list): A list of recognized plugin base classes for which to look for provided implementations. If not
            provided this defaults to :class:`~octoprint.plugin.OctoPrintPlugin`.
        plugin_entry_points (list): A list of entry points pointing to modules which to load as plugins. If not provided
            this defaults to the entry point ``octoprint.plugin``.
        plugin_disabled_list (list): A list of plugin identifiers that are currently disabled. If not provided this
            defaults to all plugins for which ``enabled`` is set to ``False`` in the settings.
        plugin_sorting_order (dict): A dict containing a custom sorting orders for plugins. The keys are plugin identifiers,
            mapped to dictionaries containing the sorting contexts as key and the custom sorting value as value.
        plugin_blacklist (list): A list of plugin identifiers/identifier-requirement tuples
            that are currently blacklisted.
        plugin_restart_needing_hooks (list): A list of hook namespaces which cause a plugin to need a restart in order
            be enabled/disabled. Does not have to contain full hook identifiers, will be matched with startswith similar
            to logging handlers
        plugin_obsolete_hooks (list): A list of hooks that have been declared obsolete. Plugins implementing them will
            not be enabled since they might depend on functionality that is no longer available.
        plugin_considered_bundled (list): A list of plugin identifiers that are considered bundled plugins even if
            installed separately.
        plugin_validators (list): A list of additional plugin validators through which to process each plugin.
        compatibility_ignored_list (list): A list of plugin keys for which it will be ignored if they are flagged as
            incompatible. This is for development purposes only and should not be used in production.

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
            if plugin_bases is None:
                plugin_bases = [OctoPrintPlugin]

            if plugin_restart_needing_hooks is None:
                plugin_restart_needing_hooks = [
                    "octoprint.server.http.*",
                    "octoprint.printer.factory",
                    "octoprint.access.permissions",
                    "octoprint.timelapse.extensions",
                ]

            if plugin_obsolete_hooks is None:
                plugin_obsolete_hooks = ["octoprint.comm.protocol.gcode"]

            if plugin_considered_bundled is None:
                plugin_considered_bundled = ["firmware_check", "file_check", "pi_support"]

            if plugin_validators is None:
                plugin_validators = [_validate_plugin]
            else:
                plugin_validators.append(_validate_plugin)

            _instance = PluginManager(
                plugin_folders,
                plugin_bases,
                plugin_entry_points,
                logging_prefix="octoprint.plugins.",
                plugin_disabled_list=plugin_disabled_list,
                plugin_sorting_order=plugin_sorting_order,
                plugin_blacklist=plugin_blacklist,
                plugin_restart_needing_hooks=plugin_restart_needing_hooks,
                plugin_obsolete_hooks=plugin_obsolete_hooks,
                plugin_considered_bundled=plugin_considered_bundled,
                plugin_validators=plugin_validators,
                compatibility_ignored_list=compatibility_ignored_list,
            )
        else:
            raise ValueError("Plugin Manager not initialized yet")
    return _instance


def plugin_settings(
    plugin_key,
    defaults=None,
    get_preprocessors=None,
    set_preprocessors=None,
    settings=None,
):
    """
    Factory method for creating a :class:`PluginSettings` instance.

    Arguments:
        plugin_key (string): The plugin identifier for which to create the settings instance.
        defaults (dict): The default settings for the plugin, if different from get_settings_defaults.
        get_preprocessors (dict): The getter preprocessors for the plugin.
        set_preprocessors (dict): The setter preprocessors for the plugin.
        settings (octoprint.settings.Settings): The settings instance to use.

    Returns:
        PluginSettings: A fully initialized :class:`PluginSettings` instance to be used to access the plugin's
            settings
    """
    if settings is None:
        settings = s()
    return PluginSettings(
        settings,
        plugin_key,
        defaults=defaults,
        get_preprocessors=get_preprocessors,
        set_preprocessors=set_preprocessors,
    )


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
        get_preprocessors, set_preprocessors = instance.get_settings_preprocessors()
    except Exception:
        logging.getLogger(__name__).exception(
            f"Error while retrieving preprocessors for plugin {plugin_key}"
        )
        return None

    return plugin_settings(
        plugin_key,
        get_preprocessors=get_preprocessors,
        set_preprocessors=set_preprocessors,
        settings=settings,
    )


def call_plugin(
    types,
    method,
    args=None,
    kwargs=None,
    callback=None,
    error_callback=None,
    sorting_context=None,
    initialized=True,
    manager=None,
):
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
        initialized (boolean): Ignored.
        manager (PluginManager or None): The plugin manager to use. If not provided, the global plugin manager
    """

    if not isinstance(types, (list, tuple)):
        types = [types]
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}
    if manager is None:
        manager = plugin_manager()

    logger = logging.getLogger(__name__)

    plugins = manager.get_implementations(*types, sorting_context=sorting_context)
    for plugin in plugins:
        if not hasattr(plugin, "_identifier"):
            continue

        if hasattr(plugin, method):
            logger.debug(f"Calling {method} on {plugin._identifier}")
            try:
                result = getattr(plugin, method)(*args, **kwargs)
                if callback:
                    callback(plugin._identifier, plugin, result)
            except Exception as exc:
                logger.exception(
                    "Error while calling plugin %s" % plugin._identifier,
                    extra={"plugin": plugin._identifier},
                )
                if error_callback:
                    error_callback(plugin._identifier, plugin, exc)


class PluginSettings:
    """
    The :class:`PluginSettings` class is the interface for plugins to their own or globally defined settings.

    It provides some convenience methods for directly accessing plugin settings via the regular
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

    .. method:: get_int(path, min=None, max=None)

       Like :func:`get` but tries to convert the retrieved value to ``int``. If ``min`` is provided and the retrieved
       value is less than it, it will be returned instead of the value. Likewise for ``max`` - it will be returned if
       the value is greater than it.

    .. method:: get_float(path, min=None, max=None)

       Like :func:`get` but tries to convert the retrieved value to ``float``. If ``min`` is provided and the retrieved
       value is less than it, it will be returned instead of the value. Likewise for ``max`` - it will be returned if
       the value is greater than it.

    .. method:: get_boolean(path)

       Like :func:`get` but tries to convert the retrieved value to ``boolean``.

    .. method:: set(path, value, force=False)

       Sets the raw value on the settings for ``path``.

       :param path: The path for which to retrieve the value.
       :type path: list, tuple
       :param object value: The value to set.
       :param boolean force: If set to True, the modified configuration will even be written back to disk if
           the value didn't change.

    .. method:: set_int(path, value, force=False, min=None, max=None)

       Like :func:`set` but ensures the value is an ``int`` through attempted conversion before setting it.
       If ``min`` and/or ``max`` are provided, it will also be ensured that the value is greater than or equal
       to ``min`` and less than or equal to ``max``. If that is not the case, the limit value (``min`` if less than
       that, ``max`` if greater than that) will be set instead.

    .. method:: set_float(path, value, force=False, min=None, max=None)

       Like :func:`set` but ensures the value is an ``float`` through attempted conversion before setting it.
       If ``min`` and/or ``max`` are provided, it will also be ensured that the value is greater than or equal
       to ``min`` and less than or equal to ``max``. If that is not the case, the limit value (``min`` if less than
       that, ``max`` if greater than that) will be set instead.

    .. method:: set_boolean(path, value, force=False)

       Like :func:`set` but ensures the value is an ``boolean`` through attempted conversion before setting it.

    .. method:: save(force=False, trigger_event=False)

       Saves the settings to ``config.yaml`` if there are active changes. If ``force`` is set to ``True`` the settings
       will be saved even if there are no changes. Settings ``trigger_event`` to ``True`` will cause a ``SettingsUpdated``
       :ref:`event <sec-events-available_events-settings>` to get triggered.

       :param force: Force saving to ``config.yaml`` even if there are no changes.
       :type force: boolean
       :param trigger_event: Trigger the ``SettingsUpdated`` :ref:`event <sec-events-available_events-settings>` on save.
       :type trigger_event: boolean

    .. method:: add_overlay(overlay, at_end=False, key=None)

       Adds a new config overlay for the plugin's settings. Will return the overlay's key in the map.

       :param overlay: Overlay dict to add
       :type overlay: dict
       :param at_end: Whether to add overlay at end or start (default) of config hierarchy
       :type at_end: boolean
       :param key: Key to use to identify overlay. If not set one will be built based on the overlay's hash
       :type key: str
       :rtype: str

    .. method:: remove_overlay(key)

       Removes an overlay from the settings based on its key. Return ``True`` if the overlay could be found and was
       removed, ``False`` otherwise.

       :param key: The key of the overlay to remove
       :type key: str
       :rtype: boolean
    """

    def __init__(
        self,
        settings,
        plugin_key,
        defaults=None,
        get_preprocessors=None,
        set_preprocessors=None,
    ):
        self.settings = settings
        self.plugin_key = plugin_key

        if defaults is not None:
            self.defaults = {"plugins": {}}
            self.defaults["plugins"][plugin_key] = defaults
            self.defaults["plugins"][plugin_key]["_config_version"] = None
        else:
            self.defaults = None

        if get_preprocessors is None:
            get_preprocessors = {}
        self.get_preprocessors = {"plugins": {}}
        self.get_preprocessors["plugins"][plugin_key] = get_preprocessors

        if set_preprocessors is None:
            set_preprocessors = {}
        self.set_preprocessors = {"plugins": {}}
        self.set_preprocessors["plugins"][plugin_key] = set_preprocessors

        def prefix_path_in_args(args, index=0):
            result = []
            if index == 0:
                result.append(self._prefix_path(args[0]))
                result.extend(args[1:])
            else:
                args_before = args[: index - 1]
                args_after = args[index + 1 :]
                result.extend(args_before)
                result.append(self._prefix_path(args[index]))
                result.extend(args_after)
            return result

        def add_getter_kwargs(kwargs):
            if "defaults" not in kwargs and self.defaults is not None:
                kwargs.update(defaults=self.defaults)
            if "preprocessors" not in kwargs:
                kwargs.update(preprocessors=self.get_preprocessors)
            return kwargs

        def add_setter_kwargs(kwargs):
            if "defaults" not in kwargs and self.defaults is not None:
                kwargs.update(defaults=self.defaults)
            if "preprocessors" not in kwargs:
                kwargs.update(preprocessors=self.set_preprocessors)
            return kwargs

        def wrap_overlay(args):
            result = list(args)
            overlay = result[0]
            result[0] = {"plugins": {plugin_key: overlay}}
            return result

        self.access_methods = {
            "has": ("has", prefix_path_in_args, add_getter_kwargs),
            "get": ("get", prefix_path_in_args, add_getter_kwargs),
            "get_int": ("getInt", prefix_path_in_args, add_getter_kwargs),
            "get_float": ("getFloat", prefix_path_in_args, add_getter_kwargs),
            "get_boolean": ("getBoolean", prefix_path_in_args, add_getter_kwargs),
            "set": ("set", prefix_path_in_args, add_setter_kwargs),
            "set_int": ("setInt", prefix_path_in_args, add_setter_kwargs),
            "set_float": ("setFloat", prefix_path_in_args, add_setter_kwargs),
            "set_boolean": ("setBoolean", prefix_path_in_args, add_setter_kwargs),
            "remove": ("remove", prefix_path_in_args, lambda x: x),
            "add_overlay": ("add_overlay", wrap_overlay, lambda x: x),
            "remove_overlay": ("remove_overlay", lambda x: x, lambda x: x),
        }
        self.deprecated_access_methods = {
            "getInt": "get_int",
            "getFloat": "get_float",
            "getBoolean": "get_boolean",
            "setInt": "set_int",
            "setFloat": "set_float",
            "setBoolean": "set_boolean",
        }

    def _prefix_path(self, path=None):
        if path is None:
            path = list()
        return ["plugins", self.plugin_key] + path

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

    @deprecated(
        "PluginSettings.get_plugin_data_folder has been replaced by OctoPrintPlugin.get_plugin_data_folder",
        includedoc="Replaced by :func:`~octoprint.plugin.types.OctoPrintPlugin.get_plugin_data_folder`",
        since="1.2.0",
    )
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

        kwargs.update(
            {
                "merged": merged,
                "asdict": asdict,
                "defaults": defaults,
                "preprocessors": preprocessors,
            }
        )

        return self.settings.get(self._prefix_path(), **kwargs)

    def clean_all_data(self):
        self.settings.remove(self._prefix_path())

    def __getattr__(self, item):
        all_access_methods = list(self.access_methods.keys()) + list(
            self.deprecated_access_methods.keys()
        )
        if item in all_access_methods:
            decorator = None
            if item in self.deprecated_access_methods:
                new = self.deprecated_access_methods[item]
                decorator = deprecated(
                    f"{item} has been renamed to {new}",
                    stacklevel=2,
                )
                item = new

            settings_name, args_mapper, kwargs_mapper = self.access_methods[item]
            if hasattr(self.settings, settings_name) and callable(
                getattr(self.settings, settings_name)
            ):
                orig_func = getattr(self.settings, settings_name)
                if decorator is not None:
                    orig_func = decorator(orig_func)

                def _func(*args, **kwargs):
                    return orig_func(*args_mapper(args), **kwargs_mapper(kwargs))

                _func.__name__ = item
                _func.__doc__ = orig_func.__doc__ if "__doc__" in dir(orig_func) else None

                return _func

        return getattr(self.settings, item)
