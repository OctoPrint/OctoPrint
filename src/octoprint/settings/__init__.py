"""
This module represents OctoPrint's settings management. Within this module the default settings for the core
application are defined and the instance of the :class:`Settings` is held, which offers getter and setter
methods for the raw configuration values as well as various convenience methods to access the paths to base folders
of various types and the configuration file itself.

.. autodata:: default_settings
   :annotation: = dict(...)

.. autodata:: valid_boolean_trues

.. autofunction:: settings

.. autoclass:: Settings
   :members:
   :undoc-members:
"""

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import fnmatch
import logging
import os
import re
import sys
import threading
import time
from collections import ChainMap, defaultdict
from collections.abc import KeysView
from typing import Any, Dict, List

from yaml import YAMLError

from octoprint.schema.config import Config
from octoprint.util import (
    CaseInsensitiveSet,
    atomic_write,
    deprecated,
    dict_merge,
    fast_deepcopy,
    generate_api_key,
    is_hidden_path,
    time_this,
    yaml,
)

_APPNAME = "OctoPrint"

_instance = None


def settings(init=False, basedir=None, configfile=None, overlays=None):
    """
    Factory method for initially constructing and consecutively retrieving the :class:`~octoprint.settings.Settings`
    singleton.

    Arguments:
        init (boolean): A flag indicating whether this is the initial call to construct the singleton (True) or not
            (False, default). If this is set to True and the plugin manager has already been initialized, a :class:`ValueError`
            will be raised. The same will happen if the plugin manager has not yet been initialized and this is set to
            False.
        basedir (str): Path of the base directory for all of OctoPrint's settings, log files, uploads etc. If not set
            the default will be used: ``~/.octoprint`` on Linux, ``%APPDATA%/OctoPrint`` on Windows and
            ``~/Library/Application Support/OctoPrint`` on MacOS.
        configfile (str): Path of the configuration file (``config.yaml``) to work on. If not set the default will
            be used: ``<basedir>/config.yaml`` for ``basedir`` as defined above.
        overlays (list): List of paths to config overlays to put between default settings and config.yaml

    Returns:
        Settings: The fully initialized :class:`Settings` instance.

    Raises:
        ValueError: ``init`` is True but settings are already initialized or vice versa.
    """
    global _instance
    if _instance is not None:
        if init:
            raise ValueError("Settings Manager already initialized")

    else:
        if init:
            _instance = Settings(
                configfile=configfile, basedir=basedir, overlays=overlays
            )
        else:
            raise ValueError("Settings not initialized yet")

    return _instance


# TODO: This is a temporary solution to get the default settings from the pydantic model.
_config = Config()
default_settings = _config.dict(by_alias=True)
"""The default settings of the core application."""

valid_boolean_trues = CaseInsensitiveSet(True, "true", "yes", "y", "1", 1)
""" Values that are considered to be equivalent to the boolean ``True`` value, used for type conversion in various places."""


class NoSuchSettingsPath(Exception):
    pass


class InvalidSettings(Exception):
    pass


class InvalidYaml(InvalidSettings):
    def __init__(self, file, line=None, column=None, details=None):
        self.file = file
        self.line = line
        self.column = column
        self.details = details

    def __str__(self):
        message = (
            "Error parsing the configuration file {}, "
            "it is invalid YAML.".format(self.file)
        )
        if self.line and self.column:
            message += " The parser reported an error on line {}, column {}.".format(
                self.line, self.column
            )
        return message


class DuplicateFolderPaths(InvalidSettings):
    def __init__(self, folders):
        self.folders = folders

        self.duplicates = {}
        for folder, path in folders.items():
            duplicates = []
            for other_folder, other_path in folders.items():
                if other_folder == folder:
                    continue
                if other_path == path:
                    duplicates.append(other_folder)
            if len(duplicates):
                self.duplicates[folder] = duplicates

    def __str__(self):
        duplicates = [
            "{} (duplicates: {})".format(folder, ", ".join(dupes))
            for folder, dupes in self.duplicates.items()
        ]
        return "There are duplicate folder paths configured: {}".format(
            ", ".join(duplicates)
        )


_CHAINMAP_SEP = "\x1f"


class HierarchicalChainMap:
    """
    Stores a bunch of nested dictionaries in chain map, allowing queries of nested values
    work on lower directories. For example:

    Example:
        >>> example_dict = {"a": "a", "b": {"c": "c"}}
        >>> hcm = HierarchicalChainMap({"b": {"d": "d"}}, example_dict)
        >>> cm = ChainMap({"b": {"d": "d"}}, example_dict)
        >>> cm["b"]["d"]
        'd'
        >>> cm["b"]["c"]
        Traceback (most recent call last):
            ...
        KeyError: 'c'
        >>> hcm.get_by_path(["b", "d"])
        'd'
        >>> hcm.get_by_path(["b", "c"])
        'c'

    Internally, the chainmap is flattened, without any contained dictionaries. Combined with
    a prefix cache, this allows for fast lookups of nested values. The chainmap is also
    unflattened when needed, for example when returning sub trees or the full dictionary.

    For flattening, the path to each value is joined with a special separator character
    that is unlikely to appear in a normal key, ``\x1f``. Unflattening is then done
    by splitting the keys on this character and recreating the nested structure.
    """

    @staticmethod
    def _flatten(d: Dict[str, Any], parent_key: str = "") -> Dict[str, Any]:
        """
        Recursively flattens a hierarchical dictionary.

        Args:
            d (dict): The hierarchical dictionary to flatten.
            parent_key (str): The parent key to use for the current level.

        Returns:
            dict: The flattened dictionary.
        """

        if d is None:
            return {}

        items = []
        for k, v in d.items():
            new_key = parent_key + _CHAINMAP_SEP + str(k) if parent_key else str(k)
            if v and isinstance(v, dict):
                items.extend(HierarchicalChainMap._flatten(v, new_key).items())
            else:
                items.append((new_key, v))
        return dict(items)

    @staticmethod
    def _unflatten(d: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """
        Unflattens a flattened dictionary.

        Args:
            d (dict): The flattened dictionary.
            prefix (str): The prefix to use for the top level keys. If provided, only keys
                starting with this prefix will be unflattened and part of the result.

        Returns:
            dict: The unflattened dictionary.
        """

        if d is None:
            return {}

        result = {}
        for key, value in d.items():
            if not key.startswith(prefix):
                continue
            subkeys = key[len(prefix) :].split(_CHAINMAP_SEP)
            current = result

            path = []
            for subkey in subkeys[:-1]:
                # we only need that for logging in case of data weirdness below
                path.append(subkey)

                # make sure the subkey is in the current dict, and that it is a dict
                if subkey not in current:
                    current[subkey] = {}
                elif not isinstance(current[subkey], dict):
                    logging.getLogger(__name__).warning(
                        f"There is a non-dict value on the path to {key} at {path!r}, ignoring."
                    )
                    current[subkey] = {}

                # go down a level
                current = current[subkey]

            current[subkeys[-1]] = value

        return result

    @staticmethod
    def _path_to_key(path: List[str]) -> str:
        """Converts a path to a key."""
        return _CHAINMAP_SEP.join(path)

    @staticmethod
    def from_layers(*layers: Dict[str, Any]) -> "HierarchicalChainMap":
        """Generates a new chain map from the provided layers."""
        result = HierarchicalChainMap()
        result._chainmap.maps = layers
        return result

    def __init__(self, *maps: Dict[str, Any]):
        self._chainmap = ChainMap(*map(self._flatten, maps))
        self._prefixed_keys = {}

    def _has_prefix(self, prefix: str, current: ChainMap = None) -> bool:
        """
        Check if the given prefix is in the current map. This utilizes the cached
        prefix keys to avoid recomputing the list every time.
        """
        if current is None:
            current = self._chainmap
        return any(map(lambda x: x in current, self._cached_prefixed_keys(prefix)))

    def _with_prefix(self, prefix: str, current: ChainMap = None) -> Dict[str, Any]:
        """
        Get a dict with all keys that start with the given prefix. This utilizes the
        cached prefix keys to avoid recomputing the list every time.
        """
        if current is None:
            current = self._chainmap
        return {k: current[k] for k in self._cached_prefixed_keys(prefix) if k in current}

    def _cached_prefixed_keys(self, prefix: str) -> List[str]:
        """
        Get a list of keys that start with the given prefix. This is cached to avoid
        recomputing the list every time.
        """
        if prefix not in self._prefixed_keys:
            keys = [k for k in self._chainmap.keys() if k.startswith(prefix)]
            if keys:
                self._prefixed_keys[prefix] = keys
        return self._prefixed_keys.get(prefix, [])

    def _invalidate_prefixed_keys(self, prefix: str) -> None:
        """
        Invalidate the cache of prefixed keys for the given prefix.

        This is done the following way:

        - Iterate backwards through all prefixes of the given prefix
          and delete any cached keys for them.
        - Delete all keys that start with the given prefix.
        """
        seps = []
        for i, c in enumerate(prefix):
            if c == _CHAINMAP_SEP:
                seps.append(i)

        for sep in reversed(seps):
            try:
                del self._prefixed_keys[prefix[: sep + 1]]
            except KeyError:
                pass

        to_delete = [key for key in self._prefixed_keys.keys() if key.startswith(prefix)]
        for prefix in to_delete:
            del self._prefixed_keys[prefix]

    def deep_dict(self) -> Dict[str, Any]:
        """Returns an unflattened copy of the current chainmap."""
        return self._unflatten(self._chainmap)

    def has_path(
        self, path: List[str], only_local: bool = False, only_defaults: bool = False
    ) -> bool:
        """
        Checks if the given path exists in the current map.

        Args:
            only_local (bool): Only check the top most map.
            only_defaults (bool): Only check everything but the top most map.

        Returns:
            bool: True if the path exists, False otherwise.
        """
        if only_defaults:
            current = self._chainmap.parents
        elif only_local:
            current = self._chainmap.maps[0]
        else:
            current = self._chainmap

        key = self._path_to_key(path)
        prefix = key + _CHAINMAP_SEP
        return key in current or self._has_prefix(prefix, current)

    @time_this(
        logtarget="octoprint.settings.timings.HierarchicalChainMap.get_by_path",
        message="{func}({func_args}) took {timing:.6f}ms",
        incl_func_args=True,
    )
    def get_by_path(
        self,
        path: List[str],
        only_local: bool = False,
        only_defaults: bool = False,
        merged: bool = False,
    ) -> Any:
        """
        Retrieves the value at the given path. If the path is not found, a KeyError is raised.

        Makes heavy use of the prefix cache to avoid recomputing the list of keys every time.

        Args:
            path (list): The path to the value to retrieve.
            only_local (bool): Only check the top most map.
            only_defaults (bool): Only check everything but the top most map.
            merged (bool): If true and the value is a dict, merge all values from all layers.

        Returns:
            The value at the given path.
        """
        if only_defaults:
            current = self._chainmap.parents
        elif only_local:
            current = self._chainmap.maps[0]
        else:
            current = self._chainmap

        key = self._path_to_key(path)
        prefix = key + _CHAINMAP_SEP

        if key in current and not self._has_prefix(prefix, current):
            # found it, return
            return current[key]

        # if we arrived here we might be trying to grab a dict, look for children

        # TODO 2.0.0 remove this & make 'merged' the default
        if not merged and hasattr(current, "maps"):
            # we do something a bit odd here: if merged is not true, we don't include the
            # full contents of the key. Instead, we only include the contents of the key
            # on the first level where we find the value.
            for layer in current.maps:
                if self._has_prefix(prefix, layer):
                    current = layer
                    break

        result = self._unflatten(self._with_prefix(prefix, current), prefix=prefix)
        if not result:
            raise KeyError("Could not find entry for " + str(path))
        return result

    def set_by_path(self, path: List[str], value: Any) -> None:
        """
        Sets the value at the given path.

        Only the top most map is written to.

        Takes care of invalidating the prefix cache as needed.

        Args:
            path (list): The path to the value to set.
            value: The value to set.
        """
        current = self._chainmap.maps[0]  # config only
        key = self._path_to_key(path)
        prefix = key + _CHAINMAP_SEP

        # path might have had subkeys before, clean them up
        self._del_prefix(current, prefix)

        if isinstance(value, dict):
            current.update(self._flatten(value, key))
            self._invalidate_prefixed_keys(prefix)

        else:
            # make sure to clear anything below the path (e.g. switching from dict
            # to something else, for whatever reason)
            self._clean_upward_path(current, path)

            # finally set the new value
            current[key] = value

    def del_by_path(self, path: List[str]) -> None:
        """
        Deletes the value at the given path.

        Only the top most map is written to.

        Takes care of invalidating the prefix cache as needed.

        Args:
            path (list): The path to the value to delete.

        Raises:
            KeyError: If the path does not exist.
        """
        if not path:
            raise ValueError("Invalid path")

        current = self._chainmap.maps[0]  # config only
        key = self._path_to_key(path)
        prefix = key + _CHAINMAP_SEP
        deleted = False

        # delete any subkeys
        deleted = self._del_prefix(current, prefix)

        # delete the key itself if it's there
        try:
            del current[key]
            deleted = True
        except KeyError:
            pass

        if not deleted:
            raise KeyError("Could not find entry for " + str(path))

        # clean anything that's now empty and above our path
        self._clean_upward_path(current, path)

    def _del_prefix(self, current: ChainMap, prefix: str) -> bool:
        """
        Deletes all keys that start with the given prefix.

        Takes care of invalidating the prefix cache as needed.

        Args:
            current (ChainMap): The map to delete from.
            prefix (str): The prefix to delete.

        Returns:
            bool: True if any keys were deleted, False otherwise.
        """
        to_delete = self._with_prefix(prefix, current).keys()
        for k in to_delete:
            del current[k]

        if len(to_delete) > 0:
            self._invalidate_prefixed_keys(prefix)

        return len(to_delete) > 0

    def _clean_upward_path(self, current: ChainMap, path: List[str]) -> None:
        """
        Cleans up the path upwards from the given path, getting rid of any empty dicts.

        Args:
            current (ChainMap): The map to clean up.
            path (list): The path to clean up from.
        """
        working_path = path
        while len(working_path):
            working_path = working_path[:-1]
            if not working_path:
                break

            key = self._path_to_key(working_path)
            prefix = key + _CHAINMAP_SEP
            if self._has_prefix(prefix, current):
                # there's at least one subkey here, we're done
                break

            # delete the key itself if it's there
            try:
                del current[key]
            except KeyError:
                # key itself wasn't in there
                pass

    def with_config_defaults(
        self, config: Dict[str, Any] = None, defaults: Dict[str, Any] = None
    ) -> "HierarchicalChainMap":
        """
        Builds a new map with the following layers: provided config + any intermediary
        parents + provided defaults + regular defaults.

        Args:
            config (dict): The config to use as the top layer. May be None in which case
                it will be set to the current config. May be unflattened.
            defaults (dict): The defaults to use above the bottom layer. May be None in
                which case it will be set to an empty layer. May be unflattened.

        Returns:
            HierarchicalChainMap: A new chain map with the provided layers.
        """
        if config is None and defaults is None:
            return self

        if config is not None:
            config = self._flatten(config)
        else:
            config = self._chainmap.maps[0]

        if defaults is not None:
            defaults = [self._flatten(defaults)]
        else:
            defaults = []

        layers = [config] + self._middle_layers() + defaults + [self._chainmap.maps[-1]]
        return self.with_layers(*layers)

    def with_layers(self, *layers: Dict[str, Any]) -> "HierarchicalChainMap":
        """
        Builds a new map with the provided layers. Makes sure to copy the current prefix cache
        to the new map.

        Args:
            layers: The layers to use in the new map. May be unflattened.

        Returns:
            HierarchicalChainMap: A new chain map with the provided layers.
        """

        chain = HierarchicalChainMap.from_layers(*layers)
        chain._prefixed_keys = (
            self._prefixed_keys
        )  # be sure to copy the cache or it will lose sync
        return chain

    @property
    def top_map(self) -> Dict[str, Any]:
        """This is the layer that is written to, unflattened"""
        return self._unflatten(self._chainmap.maps[0])

    @top_map.setter
    def top_map(self, value):
        self._chainmap.maps[0] = self._flatten(value)

    @property
    def bottom_map(self) -> Dict[str, Any]:
        """The very bottom layer is the default layer, unflattened"""
        return self._unflatten(self._chainmap.maps[-1])

    def insert_map(self, pos: int, d: Dict[str, Any]) -> None:
        """
        Inserts a new map at the given position into the chainmap.

        The map is flattened before being inserted.

        Takes care of invalidating the prefix cache as needed.

        Args:
            pos (int): The position to insert the map at.
            d (dict): The unflattened map to insert. May be unflattened.
        """

        flattened = self._flatten(d)
        for k in flattened:
            self._invalidate_prefixed_keys(k + _CHAINMAP_SEP)
        self._chainmap.maps.insert(pos, flattened)

    def delete_map(self, pos: int) -> None:
        """
        Deletes the map at the given position from the chainmap.

        Takes care of invalidating the prefix cache as needed.

        Args:
            pos (int): The position to delete the map from.
        """

        flattened = self._chainmap.maps[pos]
        for k in flattened:
            self._invalidate_prefixed_keys(k + _CHAINMAP_SEP)
        del self._chainmap.maps[pos]

    @property
    def all_layers(self) -> List[Dict[str, Any]]:
        """A list of all layers in this map, flattened."""
        return self._chainmap.maps

    def _middle_layers(self) -> List[dict]:
        """Returns all layers between the top and bottom layer, flattened."""
        if len(self._chainmap.maps) > 2:
            return self._chainmap.maps[1:-1]
        else:
            return []


class Settings:
    """
    The :class:`Settings` class allows managing all of OctoPrint's settings. It takes care of initializing the settings
    directory, loading the configuration from ``config.yaml``, persisting changes to disk etc and provides access
    methods for getting and setting specific values from the overall settings structure via paths.

    A general word on the concept of paths, since they play an important role in OctoPrint's settings management. A
    path is basically a list or tuple consisting of keys to follow down into the settings (which are basically like
    a ``dict``) in order to set or retrieve a specific value (or more than one). For example, for a settings
    structure like the following::

        serial:
            port: "/dev/ttyACM0"
            baudrate: 250000
            timeout:
                communication: 20.0
                temperature: 5.0
                sdStatus: 1.0
                connection: 10.0
        server:
            host: "0.0.0.0"
            port: 5000

    the following paths could be used:

    ========================================== ============================================================================
    Path                                       Value
    ========================================== ============================================================================
    ``["serial", "port"]``                     ::

                                                   "/dev/ttyACM0"

    ``["serial", "timeout"]``                  ::

                                                   communication: 20.0
                                                   temperature: 5.0
                                                   sdStatus: 1.0
                                                   connection: 10.0

    ``["serial", "timeout", "temperature"]``   ::

                                                   5.0

    ``["server", "port"]``                     ::

                                                   5000

    ========================================== ============================================================================

    However, these would be invalid paths: ``["key"]``, ``["serial", "port", "value"]``, ``["server", "host", 3]``.
    """

    OVERLAY_KEY = "__overlay__"

    def __init__(self, configfile=None, basedir=None, overlays=None):
        self._logger = logging.getLogger(__name__)

        self._basedir = None

        if overlays is None:
            overlays = []

        assert isinstance(default_settings, dict)

        self._map = HierarchicalChainMap({}, default_settings)
        self.load_overlays(overlays)

        self._dirty = False
        self._dirty_time = 0
        self._last_config_hash = None
        self._last_effective_hash = None
        self._mtime = None

        self._lock = threading.RLock()

        self._get_preprocessors = {"controls": self._process_custom_controls}
        self._set_preprocessors = {}
        self._path_update_callbacks = defaultdict(list)
        self._deprecated_paths = defaultdict(dict)

        self.flagged_basefolders = {}

        self._init_basedir(basedir)

        if configfile is not None:
            self._configfile = configfile
        else:
            self._configfile = os.path.join(self._basedir, "config.yaml")
        self.load(migrate=True)

        apikey = self.get(["api", "key"])
        if not apikey or apikey == "n/a":
            self.generateApiKey()

        self._script_env = self._init_script_templating()

        self.sanity_check_folders(
            folders=[
                "logs",
            ]
        )
        self.warn_about_risky_settings()

    def _init_basedir(self, basedir):
        if basedir is not None:
            self._basedir = basedir
        else:
            self._basedir = _default_basedir(_APPNAME)

        if not os.path.isdir(self._basedir):
            try:
                os.makedirs(self._basedir)
            except Exception:
                self._logger.fatal(
                    "Could not create basefolder at {}. This is a fatal error, OctoPrint "
                    "can't run without a writable base folder.".format(self._basedir),
                    exc_info=1,
                )
                raise

    def sanity_check_folders(self, folders=None):
        if folders is None:
            folders = default_settings["folder"].keys()

        folder_map = {}
        for folder in folders:
            folder_map[folder] = self.getBaseFolder(
                folder, check_writable=True, deep_check_writable=True
            )

        # validate uniqueness of folder paths
        if len(folder_map.values()) != len(set(folder_map.values())):
            raise DuplicateFolderPaths(folders)

    def warn_about_risky_settings(self):
        if not self.getBoolean(["devel", "enableRateLimiter"]):
            self._logger.warning(
                "Rate limiting is disabled, this is a security risk. Do not run this in production."
            )
        if not self.getBoolean(["devel", "enableCsrfProtection"]):
            self._logger.warning(
                "CSRF Protection is disabled, this is a security risk. Do not run this in production."
            )

    def _is_deprecated_path(self, path):
        if path and isinstance(path[-1], (list, tuple)):
            prefix = path[:-1]
            return any(
                map(lambda x: bool(self._deprecated_paths[tuple(prefix + [x])]), path[-1])
            )

        if (
            tuple(path) not in self._deprecated_paths
            or not self._deprecated_paths[tuple(path)]
        ):
            return False

        try:
            return list(self._deprecated_paths[tuple(path)].values())[-1]
        except StopIteration:
            return False

    def _path_modified(self, path, current_value, new_value):
        callbacks = self._path_update_callbacks.get(tuple(path))
        if callbacks:
            for callback in callbacks:
                try:
                    if callable(callback):
                        callback(path, current_value, new_value)
                except Exception:
                    self._logger.exception(
                        f"Error while executing callback {callback} for path {path}"
                    )

    def _get_default_folder(self, type):
        folder = default_settings["folder"][type]
        if folder is None:
            folder = os.path.join(self._basedir, type.replace("_", os.path.sep))
        return folder

    def _init_script_templating(self):
        from jinja2 import BaseLoader, ChoiceLoader, TemplateNotFound
        from jinja2.ext import Extension
        from jinja2.nodes import Include
        from jinja2.sandbox import SandboxedEnvironment

        from octoprint.util.jinja import FilteredFileSystemLoader

        class SnippetExtension(Extension):
            tags = {"snippet"}
            fields = Include.fields

            def parse(self, parser):
                node = parser.parse_include()
                if not node.template.value.startswith("/"):
                    node.template.value = "snippets/" + node.template.value
                return node

        class SettingsScriptLoader(BaseLoader):
            def __init__(self, s):
                self._settings = s

            def get_source(self, environment, template):
                parts = template.split("/")
                if not len(parts):
                    raise TemplateNotFound(template)

                script = self._settings.get(["scripts"], merged=True)
                for part in parts:
                    if isinstance(script, dict) and part in script:
                        script = script[part]
                    else:
                        raise TemplateNotFound(template)
                source = script
                if source is None:
                    raise TemplateNotFound(template)
                mtime = self._settings._mtime
                return source, None, lambda: mtime == self._settings.last_modified

            def list_templates(self):
                scripts = self._settings.get(["scripts"], merged=True)
                return self._get_templates(scripts)

            def _get_templates(self, scripts):
                templates = []
                for key in scripts:
                    if isinstance(scripts[key], dict):
                        templates += list(
                            map(
                                lambda x: key + "/" + x, self._get_templates(scripts[key])
                            )
                        )
                    elif isinstance(scripts[key], str):
                        templates.append(key)
                return templates

        class SelectLoader(BaseLoader):
            def __init__(self, default, mapping, sep=":"):
                self._default = default
                self._mapping = mapping
                self._sep = sep

            def get_source(self, environment, template):
                if self._sep in template:
                    prefix, name = template.split(self._sep, 1)
                    if prefix not in self._mapping:
                        raise TemplateNotFound(template)
                    return self._mapping[prefix].get_source(environment, name)
                return self._default.get_source(environment, template)

            def list_templates(self):
                return self._default.list_templates()

        class RelEnvironment(SandboxedEnvironment):
            def __init__(self, prefix_sep=":", *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._prefix_sep = prefix_sep

            def join_path(self, template, parent):
                prefix, name = self._split_prefix(template)

                if name.startswith("/"):
                    return self._join_prefix(prefix, name[1:])
                else:
                    _, parent_name = self._split_prefix(parent)
                    parent_base = parent_name.split("/")[:-1]
                    return self._join_prefix(prefix, "/".join(parent_base) + "/" + name)

            def _split_prefix(self, template):
                if self._prefix_sep in template:
                    return template.split(self._prefix_sep, 1)
                else:
                    return "", template

            def _join_prefix(self, prefix, template):
                if len(prefix):
                    return prefix + self._prefix_sep + template
                else:
                    return template

        path_filter = lambda path: not is_hidden_path(path)
        file_system_loader = FilteredFileSystemLoader(
            self.getBaseFolder("scripts"), path_filter=path_filter
        )
        settings_loader = SettingsScriptLoader(self)
        choice_loader = ChoiceLoader([file_system_loader, settings_loader])
        select_loader = SelectLoader(
            choice_loader, {"bundled": settings_loader, "file": file_system_loader}
        )
        return RelEnvironment(loader=select_loader, extensions=[SnippetExtension])

    def _get_script_template(self, script_type, name, source=False):
        from jinja2 import TemplateNotFound

        template_name = script_type + "/" + name
        try:
            if source:
                template_name, _, _ = self._script_env.loader.get_source(
                    self._script_env, template_name
                )
                return template_name
            else:
                return self._script_env.get_template(template_name)
        except TemplateNotFound:
            return None
        except Exception:
            self._logger.exception(
                f"Exception while trying to resolve template {template_name}"
            )
            return None

    def _get_scripts(self, script_type):
        return self._script_env.list_templates(
            filter_func=lambda x: x.startswith(script_type + "/")
        )

    def _process_custom_controls(self, controls):
        def process_control(c):
            # shallow copy
            result = dict(c)

            if "regex" in result and "template" in result:
                # if it's a template matcher, we need to add a key to associate with the matcher output
                import hashlib

                key_hash = hashlib.md5()
                key_hash.update(result["regex"].encode("utf-8"))
                result["key"] = key_hash.hexdigest()

                template_key_hash = hashlib.md5()
                template_key_hash.update(result["template"].encode("utf-8"))
                result["template_key"] = template_key_hash.hexdigest()

            elif "children" in result:
                # if it has children we need to process them recursively
                result["children"] = list(
                    map(
                        process_control,
                        [child for child in result["children"] if child is not None],
                    )
                )

            return result

        return list(map(process_control, controls))

    def _forget_hashes(self):
        self._last_config_hash = None
        self._last_effective_hash = None

    def _mark_dirty(self):
        with self._lock:
            self._dirty = True
            self._dirty_time = time.time()
            self._forget_hashes()

    @property
    def effective(self):
        return self._map.deep_dict()

    @property
    def effective_yaml(self):
        return yaml.dump(self.effective)

    @property
    def effective_hash(self):
        if self._last_effective_hash is not None:
            return self._last_effective_hash

        import hashlib

        hash = hashlib.md5()
        hash.update(self.effective_yaml.encode("utf-8"))
        self._last_effective_hash = hash.hexdigest()
        return self._last_effective_hash

    @property
    def config_yaml(self):
        return yaml.dump(self.config)

    @property
    def config_hash(self):
        if self._last_config_hash:
            return self._last_config_hash

        import hashlib

        hash = hashlib.md5()
        hash.update(self.config_yaml.encode("utf-8"))
        self._last_config_hash = hash.hexdigest()
        return self._last_config_hash

    @property
    def config(self):
        """
        A view of the local config as stored in config.yaml

        Does not support modifications, they will be thrown away silently. If you need to
        modify anything in the settings, utilize the provided set and remove methods.
        """
        return self._map.top_map

    @property
    @deprecated(
        "Settings._config has been deprecated and is a read-only view. Please use Settings.config or the set & remove methods instead.",
        since="1.8.0",
    )
    def _config(self):
        return self.config

    @_config.setter
    @deprecated(
        "Setting of Settings._config has been deprecated. Please use the set & remove methods instead and get in touch if you have a usecase they don't cover.",
        since="1.8.0",
    )
    def _config(self, value):
        self._map.top_map = value

    @property
    def _overlay_layers(self):
        if len(self._map.all_layers) > 2:
            return self._map.all_layers[1:-1]
        else:
            return []

    @property
    def _default_map(self):
        return self._map.bottom_map

    @property
    def last_modified(self):
        """
        Returns:
            (int) The last modification time of the configuration file.
        """
        stat = os.stat(self._configfile)
        return stat.st_mtime

    @property
    def last_modified_or_made_dirty(self):
        return max(self.last_modified, self._dirty_time)

    # ~~ load and save

    def load(self, migrate=False):
        config = None
        mtime = None

        if os.path.exists(self._configfile) and os.path.isfile(self._configfile):
            with open(self._configfile, encoding="utf-8", errors="replace") as f:
                try:
                    config = yaml.load_from_file(file=f)
                    mtime = self.last_modified

                except YAMLError as e:
                    details = str(e)

                    if hasattr(e, "problem_mark"):
                        line = e.problem_mark.line
                        column = e.problem_mark.column
                    else:
                        line = None
                        column = None

                    raise InvalidYaml(
                        self._configfile,
                        details=details,
                        line=line,
                        column=column,
                    )

        # changed from else to handle cases where the file exists, but is empty / 0 bytes
        if not config or not isinstance(config, dict):
            config = {}

        self._map.top_map = config
        self._mtime = mtime

        if migrate:
            self._migrate_config()

        self._forget_hashes()

    def load_overlays(self, overlays, migrate=True):
        for overlay in overlays:
            if not os.path.exists(overlay):
                continue

            def process(path):
                try:
                    overlay_config = self.load_overlay(path, migrate=migrate)
                    self.add_overlay(overlay_config)
                    self._logger.info(f"Added config overlay from {path}")
                except Exception:
                    self._logger.exception(f"Could not add config overlay from {path}")

            if os.path.isfile(overlay):
                process(overlay)

            elif os.path.isdir(overlay):
                for entry in os.scandir(overlay):
                    name = entry.name
                    path = entry.path

                    if is_hidden_path(path) or not fnmatch.fnmatch(name, "*.yaml"):
                        continue

                    process(path)

    def load_overlay(self, overlay, migrate=True):
        config = None

        if callable(overlay):
            try:
                overlay = overlay(self)
            except Exception:
                self._logger.exception("Error loading overlay from callable")
                return

        if isinstance(overlay, str):
            if os.path.exists(overlay) and os.path.isfile(overlay):
                config = yaml.load_from_file(path=overlay)
        elif isinstance(overlay, dict):
            config = overlay
        else:
            raise ValueError(
                "Overlay must be either a path to a yaml file or a dictionary"
            )

        if not isinstance(config, dict):
            raise ValueError(
                f"Configuration data must be a dict but is a {config.__class__}"
            )

        if migrate:
            self._migrate_config(config)
        return config

    def add_overlay(
        self, overlay, at_end=False, key=None, deprecated=None, replace=False
    ):
        assert isinstance(overlay, dict)

        if key is None:
            overlay_yaml = yaml.dump(overlay)
            import hashlib

            hash = hashlib.md5()
            hash.update(overlay_yaml.encode("utf-8"))
            key = hash.hexdigest()

        if replace:
            self.remove_overlay(key)

        if deprecated is not None:
            self._logger.debug(
                f"Marking all (recursive) paths in this overlay as deprecated: {overlay}"
            )
            for path in _paths([], overlay):
                self._deprecated_paths[tuple(path)][key] = deprecated

        overlay[self.OVERLAY_KEY] = key
        if at_end:
            self._map.insert_map(-1, overlay)
        else:
            self._map.insert_map(1, overlay)

        return key

    def remove_overlay(self, key):
        index = -1
        for i, overlay in enumerate(self._overlay_layers):
            if key == overlay.get(self.OVERLAY_KEY):
                index = i
                overlay = self._map._unflatten(overlay)
                break

        if index > -1:
            self._map.delete_map(index + 1)

            self._logger.debug(
                f"Removing all deprecation marks for (recursive) paths in this overlay: {overlay}"
            )
            for path in _paths([], overlay):
                try:
                    del self._deprecated_paths[tuple(path)][key]
                except KeyError:
                    # key not in dict
                    pass

            return True
        return False

    def add_path_update_callback(self, path, callback):
        callbacks = self._path_update_callbacks[tuple(path)]
        if callback not in callbacks:
            callbacks.append(callback)

    def remove_path_update_callback(self, path, callback):
        try:
            self._path_update_callbacks[tuple(path)].remove(callback)
        except ValueError:
            # callback not in list
            pass

    def _migrate_config(self, config=None, persist=False):
        if config is None:
            config = self._map.top_map
            persist = True

        dirty = False

        migrators = (
            self._migrate_event_config,
            self._migrate_reverse_proxy_config,
            self._migrate_printer_parameters,
            self._migrate_gcode_scripts,
            self._migrate_core_system_commands,
            self._migrate_serial_features,
            self._migrate_resend_without_ok,
            self._migrate_string_temperature_profile_values,
            self._migrate_blocked_commands,
            self._migrate_gcodeviewer_enabled,
        )

        for migrate in migrators:
            dirty = migrate(config) or dirty

        if dirty and persist:
            self._map.top_map = (
                config  # we need to write it back here or the changes will be lost
            )
            self.save(force=True)

    def _migrate_gcode_scripts(self, config):
        """
        Migrates an old development version of gcode scripts to the new template based format.

        Added in 1.2.0
        """

        dirty = False
        if "scripts" in config:
            if "gcode" in config["scripts"]:
                if "templates" in config["scripts"]["gcode"]:
                    del config["scripts"]["gcode"]["templates"]

                replacements = {
                    "disable_steppers": "M84",
                    "disable_hotends": "{% snippet 'disable_hotends' %}",
                    "disable_bed": "M140 S0",
                    "disable_fan": "M106 S0",
                }

                for name, script in config["scripts"]["gcode"].items():
                    self.saveScript("gcode", name, script.format(**replacements))
            del config["scripts"]
            dirty = True
        return dirty

    def _migrate_printer_parameters(self, config):
        """
        Migrates the old "printer > parameters" data structure to the new printer profile mechanism.

        Added in 1.2.0
        """
        default_profile = (
            config["printerProfiles"]["defaultProfile"]
            if "printerProfiles" in config
            and "defaultProfile" in config["printerProfiles"]
            else {}
        )
        dirty = False

        if "printerParameters" in config:
            printer_parameters = config["printerParameters"]

            if (
                "movementSpeed" in printer_parameters
                or "invertAxes" in printer_parameters
            ):
                dirty = True
                default_profile["axes"] = {"x": {}, "y": {}, "z": {}, "e": {}}
                if "movementSpeed" in printer_parameters:
                    for axis in ("x", "y", "z", "e"):
                        if axis in printer_parameters["movementSpeed"]:
                            default_profile["axes"][axis]["speed"] = printer_parameters[
                                "movementSpeed"
                            ][axis]
                    del config["printerParameters"]["movementSpeed"]
                if "invertedAxes" in printer_parameters:
                    for axis in ("x", "y", "z", "e"):
                        if axis in printer_parameters["invertedAxes"]:
                            default_profile["axes"][axis]["inverted"] = True
                    del config["printerParameters"]["invertedAxes"]

            if (
                "numExtruders" in printer_parameters
                or "extruderOffsets" in printer_parameters
            ):
                dirty = True
                if "extruder" not in default_profile:
                    default_profile["extruder"] = {}

                if "numExtruders" in printer_parameters:
                    default_profile["extruder"]["count"] = printer_parameters[
                        "numExtruders"
                    ]
                    del config["printerParameters"]["numExtruders"]
                if "extruderOffsets" in printer_parameters:
                    extruder_offsets = []
                    for offset in printer_parameters["extruderOffsets"]:
                        if "x" in offset and "y" in offset:
                            extruder_offsets.append((offset["x"], offset["y"]))
                    default_profile["extruder"]["offsets"] = extruder_offsets
                    del config["printerParameters"]["extruderOffsets"]

            if "bedDimensions" in printer_parameters:
                dirty = True
                bed_dimensions = printer_parameters["bedDimensions"]
                if "volume" not in default_profile:
                    default_profile["volume"] = {}

                if (
                    "circular" in bed_dimensions
                    and "r" in bed_dimensions
                    and bed_dimensions["circular"]
                ):
                    default_profile["volume"]["formFactor"] = "circular"
                    default_profile["volume"]["width"] = 2 * bed_dimensions["r"]
                    default_profile["volume"]["depth"] = default_profile["volume"][
                        "width"
                    ]
                elif "x" in bed_dimensions or "y" in bed_dimensions:
                    default_profile["volume"]["formFactor"] = "rectangular"
                    if "x" in bed_dimensions:
                        default_profile["volume"]["width"] = bed_dimensions["x"]
                    if "y" in bed_dimensions:
                        default_profile["volume"]["depth"] = bed_dimensions["y"]
                del config["printerParameters"]["bedDimensions"]

        if dirty:
            if "printerProfiles" not in config:
                config["printerProfiles"] = {}
            config["printerProfiles"]["defaultProfile"] = default_profile
        return dirty

    def _migrate_reverse_proxy_config(self, config):
        """
        Migrates the old "server > baseUrl" and "server > scheme" configuration entries to
        "server > reverseProxy > prefixFallback" and "server > reverseProxy > schemeFallback".

        Added in 1.2.0
        """
        if "server" in config and (
            "baseUrl" in config["server"] or "scheme" in config["server"]
        ):
            prefix = ""
            if "baseUrl" in config["server"]:
                prefix = config["server"]["baseUrl"]
                del config["server"]["baseUrl"]

            scheme = ""
            if "scheme" in config["server"]:
                scheme = config["server"]["scheme"]
                del config["server"]["scheme"]

            if "reverseProxy" not in config["server"] or not isinstance(
                config["server"]["reverseProxy"], dict
            ):
                config["server"]["reverseProxy"] = {}
            if prefix:
                config["server"]["reverseProxy"]["prefixFallback"] = prefix
            if scheme:
                config["server"]["reverseProxy"]["schemeFallback"] = scheme
            self._logger.info("Migrated reverse proxy configuration to new structure")
            return True
        else:
            return False

    def _migrate_event_config(self, config):
        """
        Migrates the old event configuration format of type "events > gcodeCommandTrigger" and
        "event > systemCommandTrigger" to the new events format.

        Added in 1.2.0
        """
        if "events" in config and (
            "gcodeCommandTrigger" in config["events"]
            or "systemCommandTrigger" in config["events"]
        ):
            self._logger.info("Migrating config (event subscriptions)...")

            # migrate event hooks to new format
            placeholderRe = re.compile(r"%\((.*?)\)s")

            eventNameReplacements = {
                "ClientOpen": "ClientOpened",
                "TransferStart": "TransferStarted",
            }
            payloadDataReplacements = {
                "Upload": {"data": "{file}", "filename": "{file}"},
                "Connected": {"data": "{port} at {baudrate} baud"},
                "FileSelected": {"data": "{file}", "filename": "{file}"},
                "TransferStarted": {"data": "{remote}", "filename": "{remote}"},
                "TransferDone": {"data": "{remote}", "filename": "{remote}"},
                "ZChange": {"data": "{new}"},
                "CaptureStart": {"data": "{file}"},
                "CaptureDone": {"data": "{file}"},
                "MovieDone": {"data": "{movie}", "filename": "{gcode}"},
                "Error": {"data": "{error}"},
                "PrintStarted": {"data": "{file}", "filename": "{file}"},
                "PrintDone": {"data": "{file}", "filename": "{file}"},
            }

            def migrateEventHook(event, command):
                # migrate placeholders
                command = placeholderRe.sub("{__\\1}", command)

                # migrate event names
                if event in eventNameReplacements:
                    event = eventNameReplacements["event"]

                # migrate payloads to more specific placeholders
                if event in payloadDataReplacements:
                    for key in payloadDataReplacements[event]:
                        command = command.replace(
                            "{__%s}" % key, payloadDataReplacements[event][key]
                        )

                # return processed tuple
                return event, command

            disableSystemCommands = False
            if (
                "systemCommandTrigger" in config["events"]
                and "enabled" in config["events"]["systemCommandTrigger"]
            ):
                disableSystemCommands = not config["events"]["systemCommandTrigger"][
                    "enabled"
                ]

            disableGcodeCommands = False
            if (
                "gcodeCommandTrigger" in config["events"]
                and "enabled" in config["events"]["gcodeCommandTrigger"]
            ):
                disableGcodeCommands = not config["events"]["gcodeCommandTrigger"][
                    "enabled"
                ]

            disableAllCommands = disableSystemCommands and disableGcodeCommands
            newEvents = {"enabled": not disableAllCommands, "subscriptions": []}

            if (
                "systemCommandTrigger" in config["events"]
                and "subscriptions" in config["events"]["systemCommandTrigger"]
            ):
                for trigger in config["events"]["systemCommandTrigger"]["subscriptions"]:
                    if not ("event" in trigger and "command" in trigger):
                        continue

                    newTrigger = {"type": "system"}
                    if disableSystemCommands and not disableAllCommands:
                        newTrigger["enabled"] = False

                    newTrigger["event"], newTrigger["command"] = migrateEventHook(
                        trigger["event"], trigger["command"]
                    )
                    newEvents["subscriptions"].append(newTrigger)

            if (
                "gcodeCommandTrigger" in config["events"]
                and "subscriptions" in config["events"]["gcodeCommandTrigger"]
            ):
                for trigger in config["events"]["gcodeCommandTrigger"]["subscriptions"]:
                    if not ("event" in trigger and "command" in trigger):
                        continue

                    newTrigger = {"type": "gcode"}
                    if disableGcodeCommands and not disableAllCommands:
                        newTrigger["enabled"] = False

                    newTrigger["event"], newTrigger["command"] = migrateEventHook(
                        trigger["event"], trigger["command"]
                    )
                    newTrigger["command"] = newTrigger["command"].split(",")
                    newEvents["subscriptions"].append(newTrigger)

            config["events"] = newEvents
            self._logger.info(
                "Migrated %d event subscriptions to new format and structure"
                % len(newEvents["subscriptions"])
            )
            return True
        else:
            return False

    def _migrate_core_system_commands(self, config):
        """
        Migrates system commands for restart, reboot and shutdown as defined on OctoPi or
        according to the official setup guide to new core system commands to remove
        duplication.

        If server commands for action is not yet set, migrates command. Otherwise only
        deletes definition from custom system commands.

        Added in 1.3.0
        """
        changed = False

        migration_map = {
            "shutdown": "systemShutdownCommand",
            "reboot": "systemRestartCommand",
            "restart": "serverRestartCommand",
        }

        if (
            "system" in config
            and "actions" in config["system"]
            and isinstance(config["system"]["actions"], (list, tuple))
        ):
            actions = config["system"]["actions"]
            to_delete = []
            for index, spec in enumerate(actions):
                action = spec.get("action")
                command = spec.get("command")
                if action is None or command is None:
                    continue

                migrate_to = migration_map.get(action)
                if migrate_to is not None:
                    if (
                        "server" not in config
                        or "commands" not in config["server"]
                        or migrate_to not in config["server"]["commands"]
                    ):
                        if "server" not in config:
                            config["server"] = {}
                        if "commands" not in config["server"]:
                            config["server"]["commands"] = {}
                        config["server"]["commands"][migrate_to] = command
                        self._logger.info(
                            "Migrated {} action to server.commands.{}".format(
                                action, migrate_to
                            )
                        )

                    to_delete.append(index)
                    self._logger.info(
                        "Deleting {} action from configured system commands, superseded by server.commands.{}".format(
                            action, migrate_to
                        )
                    )

            for index in reversed(to_delete):
                actions.pop(index)
                changed = True

        if changed:
            # let's make a backup of our current config, in case someone wants to roll back to an
            # earlier version and needs to recover the former system commands for that
            backup_path = self.backup("system_command_migration")
            self._logger.info(
                "Made a copy of the current config at {} to allow recovery of manual system command configuration".format(
                    backup_path
                )
            )

        return changed

    def _migrate_serial_features(self, config):
        """
        Migrates feature flags identified as serial specific from the feature to the serial config tree and vice versa.

        If a flag already exists in the target tree, only deletes the copy in the source tree.

        Added in 1.3.7
        """
        changed = False

        FEATURE_TO_SERIAL = (
            "waitForStartOnConnect",
            "alwaysSendChecksum",
            "neverSendChecksum",
            "sendChecksumWithUnknownCommands",
            "unknownCommandsNeedAck",
            "sdRelativePath",
            "sdAlwaysAvailable",
            "swallowOkAfterResend",
            "repetierTargetTemp",
            "externalHeatupDetection",
            "supportWait",
            "ignoreIdenticalResends",
            "identicalResendsCountdown",
            "supportFAsCommand",
            "firmwareDetection",
            "blockWhileDwelling",
        )
        SERIAL_TO_FEATURE = ("autoUppercaseBlacklist",)

        def migrate_key(key, source, target):
            if source in config and key in config[source]:
                if config.get(target) is None:
                    # make sure we have a serial tree
                    config[target] = {}
                if key not in config[target]:
                    # only copy over if it's not there yet
                    config[target][key] = config[source][key]
                # delete feature flag
                del config[source][key]
                return True
            return False

        for key in FEATURE_TO_SERIAL:
            changed = migrate_key(key, "feature", "serial") or changed

        for key in SERIAL_TO_FEATURE:
            changed = migrate_key(key, "serial", "feature") or changed

        if changed:
            # let's make a backup of our current config, in case someone wants to roll back to an
            # earlier version and needs a backup of their flags
            backup_path = self.backup("serial_feature_migration")
            self._logger.info(
                "Made a copy of the current config at {} to allow recovery of serial feature flags".format(
                    backup_path
                )
            )

        return changed

    def _migrate_resend_without_ok(self, config):
        """
        Migrates supportResendsWithoutOk flag from boolean to ("always", "detect", "never") value range.

        True gets migrated to "always", False to "detect" (which is the new default).

        Added in 1.3.7
        """
        if (
            "serial" in config
            and "supportResendsWithoutOk" in config["serial"]
            and config["serial"]["supportResendsWithoutOk"]
            not in ("always", "detect", "never")
        ):
            value = config["serial"]["supportResendsWithoutOk"]
            if value:
                config["serial"]["supportResendsWithoutOk"] = "always"
            else:
                config["serial"]["supportResendsWithoutOk"] = "detect"
            return True
        return False

    def _migrate_string_temperature_profile_values(self, config):
        """
        Migrates/fixes temperature profile wrongly saved with strings instead of ints as temperature values.

        Added in 1.3.8
        """
        if "temperature" in config and "profiles" in config["temperature"]:
            profiles = config["temperature"]["profiles"]
            if any(
                map(
                    lambda x: not isinstance(x.get("extruder", 0), int)
                    or not isinstance(x.get("bed", 0), int),
                    profiles,
                )
            ):
                result = []
                for profile in profiles:
                    try:
                        profile["extruder"] = int(profile["extruder"])
                        profile["bed"] = int(profile["bed"])
                    except ValueError:
                        pass
                    result.append(profile)
                config["temperature"]["profiles"] = result
                return True
        return False

    def _migrate_blocked_commands(self, config):
        if "serial" in config and "blockM0M1" in config["serial"]:
            blockM0M1 = config["serial"]["blockM0M1"]
            blockedCommands = config["serial"].get("blockedCommands", [])
            if blockM0M1:
                blockedCommands = set(blockedCommands)
                blockedCommands.add("M0")
                blockedCommands.add("M1")
                config["serial"]["blockedCommands"] = sorted(blockedCommands)
            else:
                config["serial"]["blockedCommands"] = sorted(
                    v for v in blockedCommands if v not in ("M0", "M1")
                )
            del config["serial"]["blockM0M1"]
            return True
        return False

    def _migrate_gcodeviewer_enabled(self, config):
        if (
            "gcodeViewer" in config
            and "enabled" in config["gcodeViewer"]
            and not config["gcodeViewer"]["enabled"]
        ):
            if "plugins" not in config:
                config["plugins"] = {}
            if "_disabled" not in config["plugins"]:
                config["plugins"]["_disabled"] = []
            config["plugins"]["_disabled"].append("gcodeviewer")
            del config["gcodeViewer"]["enabled"]
            return True
        return False

    def backup(self, suffix=None, path=None, ext=None, hidden=False):
        import shutil

        if path is None:
            path = os.path.dirname(self._configfile)

        basename = os.path.basename(self._configfile)
        name, default_ext = os.path.splitext(basename)

        if ext is None:
            ext = default_ext

        if suffix is None and ext == default_ext:
            raise ValueError("Need a suffix or a different extension")

        if suffix is None:
            suffix = ""

        backup = os.path.join(
            path, "{}{}.{}{}".format("." if hidden else "", name, suffix, ext)
        )
        shutil.copy(self._configfile, backup)
        return backup

    def save(self, force=False, trigger_event=False):
        with self._lock:
            if not self._dirty and not force:
                return False

            try:
                with atomic_write(
                    self._configfile,
                    mode="wt",
                    prefix="octoprint-config-",
                    suffix=".yaml",
                    permissions=0o600,
                    max_permissions=0o666,
                ) as configFile:
                    yaml.save_to_file(self._map.top_map, file=configFile)
                    self._dirty = False
            except Exception:
                self._logger.exception("Error while saving config.yaml!")
                raise
            else:
                from octoprint.events import Events, eventManager

                self.load()

                if trigger_event:
                    payload = {
                        "config_hash": self.config_hash,
                        "effective_hash": self.effective_hash,
                    }
                    eventManager().fire(Events.SETTINGS_UPDATED, payload=payload)

                return True

    ##~~ Internal getter

    def _get_by_path(self, path, config):
        current = config
        for key in path:
            if key not in current:
                raise NoSuchSettingsPath()
            current = current[key]
        return current

    def _get_value(
        self,
        path,
        asdict=False,
        config=None,
        defaults=None,
        preprocessors=None,
        merged=False,
        incl_defaults=True,
        do_copy=True,
    ):
        if not path:
            raise NoSuchSettingsPath()

        is_deprecated = self._is_deprecated_path(path)
        if is_deprecated:
            self._logger.warning(
                f"DeprecationWarning: Detected access to deprecated settings path {path}, returned value is derived from compatibility overlay. {is_deprecated if isinstance(is_deprecated, str) else ''}"
            )
            config = {}

        chain = self._map.with_config_defaults(config=config, defaults=defaults)

        if preprocessors is None:
            preprocessors = self._get_preprocessors

        preprocessor = None
        try:
            preprocessor = self._get_by_path(path, preprocessors)
        except NoSuchSettingsPath:
            pass

        parent_path = path[:-1]
        last = path[-1]

        if not isinstance(last, (list, tuple)):
            keys = [last]
        else:
            keys = last

        if asdict:
            results = {}
        else:
            results = list()

        for key in keys:
            try:
                value = chain.get_by_path(
                    parent_path + [key], only_local=not incl_defaults, merged=merged
                )
            except KeyError:
                raise NoSuchSettingsPath()

            if isinstance(value, dict) and merged:
                try:
                    default_value = chain.get_by_path(
                        parent_path + [key], only_defaults=True, merged=True
                    )
                    if default_value is not None:
                        value = dict_merge(default_value, value)
                except KeyError:
                    # no default value, so nothing to merge
                    pass

            if callable(preprocessor):
                value = preprocessor(value)

            if do_copy:
                if isinstance(value, KeysView):
                    value = list(value)
                value = fast_deepcopy(value)

            if asdict:
                results[key] = value
            else:
                results.append(value)

        if not isinstance(last, (list, tuple)):
            if asdict:
                return list(results.values()).pop()
            else:
                return results.pop()
        else:
            return results

    # ~~ has

    def has(self, path, **kwargs):
        try:
            self._get_value(path, **kwargs)
        except NoSuchSettingsPath:
            return False
        else:
            return True

    # ~~ getter

    def get(self, path, **kwargs):
        error_on_path = kwargs.pop("error_on_path", False)
        validator = kwargs.pop("validator", None)
        fallback = kwargs.pop("fallback", None)

        def process():
            try:
                return self._get_value(path, **kwargs)
            except NoSuchSettingsPath:
                if error_on_path:
                    raise
                return None

        result = process()
        if callable(validator) and not validator(result):
            result = fallback
        return result

    def getInt(self, path, **kwargs):
        minimum = kwargs.pop("min", None)
        maximum = kwargs.pop("max", None)

        value = self.get(path, **kwargs)
        if value is None:
            return None

        try:
            intValue = int(value)

            if minimum is not None and intValue < minimum:
                return minimum
            elif maximum is not None and intValue > maximum:
                return maximum
            else:
                return intValue
        except ValueError:
            self._logger.warning(
                "Could not convert %r to a valid integer when getting option %r"
                % (value, path)
            )
            return None

    def getFloat(self, path, **kwargs):
        minimum = kwargs.pop("min", None)
        maximum = kwargs.pop("max", None)

        value = self.get(path, **kwargs)
        if value is None:
            return None

        try:
            floatValue = float(value)

            if minimum is not None and floatValue < minimum:
                return minimum
            elif maximum is not None and floatValue > maximum:
                return maximum
            else:
                return floatValue
        except ValueError:
            self._logger.warning(
                "Could not convert %r to a valid integer when getting option %r"
                % (value, path)
            )
            return None

    def getBoolean(self, path, **kwargs):
        value = self.get(path, **kwargs)
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return value.lower() in valid_boolean_trues
        return value is not None

    def checkBaseFolder(self, type):
        if type != "base" and type not in default_settings["folder"]:
            return False

        if type == "base":
            return os.path.exists(self._basedir)

        folder = self.get(["folder", type])
        default_folder = self._get_default_folder(type)
        if folder is None:
            folder = default_folder
        return os.path.exists(folder)

    def getBaseFolder(
        self,
        type,
        create=True,
        allow_fallback=True,
        check_writable=True,
        deep_check_writable=False,
    ):
        if type != "base" and type not in default_settings["folder"]:
            return None

        if type == "base":
            return self._basedir

        folder = self.get(["folder", type])
        default_folder = self._get_default_folder(type)
        if folder is None:
            folder = default_folder

        try:
            _validate_folder(
                folder,
                create=create,
                check_writable=check_writable,
                deep_check_writable=deep_check_writable,
            )
        except Exception as exc:
            if folder != default_folder and allow_fallback:
                self._logger.exception(
                    "Invalid configured {} folder at {}, attempting to "
                    "fall back on default folder at {}".format(
                        type, folder, default_folder
                    )
                )
                _validate_folder(
                    default_folder,
                    create=create,
                    check_writable=check_writable,
                    deep_check_writable=deep_check_writable,
                )
                folder = default_folder
                self.flagged_basefolders[type] = str(exc)

                try:
                    self.remove(["folder", type])
                    self.save()
                except KeyError:
                    pass
            else:
                raise

        return folder

    def listScripts(self, script_type):
        return list(
            map(
                lambda x: x[len(script_type + "/") :],
                filter(
                    lambda x: x.startswith(script_type + "/"),
                    self._get_scripts(script_type),
                ),
            )
        )

    def loadScript(self, script_type, name, context=None, source=False):
        if context is None:
            context = {}
        context.update({"script": {"type": script_type, "name": name}})

        template = self._get_script_template(script_type, name, source=source)
        if template is None:
            return None

        if source:
            script = template
        else:
            try:
                script = template.render(**context)
            except Exception:
                self._logger.exception(
                    f"Exception while trying to render script {script_type}:{name}"
                )
                return None

        return script

    # ~~ remove

    def remove(self, path, config=None, error_on_path=False, defaults=None):
        if not path:
            if error_on_path:
                raise NoSuchSettingsPath()
            return

        chain = self._map.with_config_defaults(config=config, defaults=defaults)

        try:
            with self._lock:
                chain.del_by_path(path)
                self._mark_dirty()
        except KeyError:
            if error_on_path:
                raise NoSuchSettingsPath()
            pass

    # ~~ setter

    def set(
        self,
        path,
        value,
        force=False,
        defaults=None,
        config=None,
        preprocessors=None,
        error_on_path=False,
        *args,
        **kwargs,
    ):
        if not path:
            if error_on_path:
                raise NoSuchSettingsPath()
            return

        is_deprecated = self._is_deprecated_path(path)
        if is_deprecated:
            self._logger.warning(
                f"[Deprecation] Prevented write of `{value}` to deprecated settings path {path}. {is_deprecated if isinstance(is_deprecated, str) else ''}"
            )
            return

        if self._mtime is not None and self.last_modified != self._mtime:
            self.load()

        chain = self._map.with_config_defaults(config=config, defaults=defaults)

        if preprocessors is None:
            preprocessors = self._set_preprocessors

        preprocessor = None
        try:
            preprocessor = self._get_by_path(path, preprocessors)
        except NoSuchSettingsPath:
            pass

        if callable(preprocessor):
            value = preprocessor(value)

        try:
            current = chain.get_by_path(path)
        except KeyError:
            current = None

        try:
            default_value = chain.get_by_path(path, only_defaults=True)
        except KeyError:
            if error_on_path:
                raise NoSuchSettingsPath()
            default_value = None

        with self._lock:
            in_local = chain.has_path(path, only_local=True)
            in_defaults = chain.has_path(path, only_defaults=True)

            if not force and in_defaults and in_local and default_value == value:
                try:
                    chain.del_by_path(path)
                    self._mark_dirty()
                    self._path_modified(path, current, value)
                except KeyError:
                    if error_on_path:
                        raise NoSuchSettingsPath()
                    pass
            elif (
                force
                or (not in_local and in_defaults and default_value != value)
                or (in_local and current != value)
            ):
                chain.set_by_path(path, value)
                self._mark_dirty()
                self._path_modified(path, current, value)

        # we've changed the interface to no longer mutate the passed in config, so we
        # must manually do that here
        if config is not None:
            config.clear()
            config.update(chain.top_map)

    def setInt(self, path, value, **kwargs):
        if value is None:
            self.set(path, None, **kwargs)
            return

        minimum = kwargs.pop("min", None)
        maximum = kwargs.pop("max", None)

        try:
            intValue = int(value)

            if minimum is not None and intValue < minimum:
                intValue = minimum
            if maximum is not None and intValue > maximum:
                intValue = maximum
        except ValueError:
            self._logger.warning(
                "Could not convert %r to a valid integer when setting option %r"
                % (value, path)
            )
            return

        self.set(path, intValue, **kwargs)

    def setFloat(self, path, value, **kwargs):
        if value is None:
            self.set(path, None, **kwargs)
            return

        minimum = kwargs.pop("min", None)
        maximum = kwargs.pop("max", None)

        try:
            floatValue = float(value)

            if minimum is not None and floatValue < minimum:
                floatValue = minimum
            if maximum is not None and floatValue > maximum:
                floatValue = maximum
        except ValueError:
            self._logger.warning(
                "Could not convert %r to a valid integer when setting option %r"
                % (value, path)
            )
            return

        self.set(path, floatValue, **kwargs)

    def setBoolean(self, path, value, **kwargs):
        if value is None or isinstance(value, bool):
            self.set(path, value, **kwargs)
        elif isinstance(value, str) and value.lower() in valid_boolean_trues:
            self.set(path, True, **kwargs)
        else:
            self.set(path, False, **kwargs)

    def setBaseFolder(self, type, path, force=False, validate=True):
        if type not in default_settings["folder"]:
            return None

        currentPath = self.getBaseFolder(type)
        defaultPath = self._get_default_folder(type)
        if path is None or path == defaultPath:
            self.remove(["folder", type])
        elif (path != currentPath and path != defaultPath) or force:
            if validate:
                _validate_folder(path, check_writable=True, deep_check_writable=True)
            self.set(["folder", type], path, force=force)

    def saveScript(self, script_type, name, script):
        script_folder = self.getBaseFolder("scripts")
        filename = os.path.realpath(os.path.join(script_folder, script_type, name))
        if not filename.startswith(os.path.realpath(script_folder)):
            # oops, jail break, that shouldn't happen
            raise ValueError(
                f"Invalid script path to save to: {filename} (from {script_type}:{name})"
            )

        path, _ = os.path.split(filename)
        if not os.path.exists(path):
            os.makedirs(path)
        with atomic_write(filename, mode="wt", max_permissions=0o666) as f:
            f.write(script)

    def generateApiKey(self):
        apikey = generate_api_key()
        self.set(["api", "key"], apikey)
        self.save(force=True)
        return apikey

    def deleteApiKey(self):
        self.set(["api", "key"], None)
        self.save(force=True)


def _default_basedir(applicationName):
    # taken from http://stackoverflow.com/questions/1084697/how-do-i-store-desktop-application-data-in-a-cross-platform-way-for-python
    if sys.platform == "darwin":
        import appdirs

        return appdirs.user_data_dir(applicationName, "")
    elif sys.platform == "win32":
        return os.path.join(os.environ["APPDATA"], applicationName)
    else:
        return os.path.expanduser(os.path.join("~", "." + applicationName.lower()))


def _validate_folder(folder, create=True, check_writable=True, deep_check_writable=False):
    logger = logging.getLogger(__name__)

    if not os.path.exists(folder):
        if os.path.islink(folder):
            # broken symlink, see #2644
            raise OSError(f"Folder at {folder} appears to be a broken symlink")

        elif create:
            # non existing, but we are allowed to create it
            try:
                os.makedirs(folder)
            except Exception:
                logger.exception(f"Could not create {folder}")
                raise OSError(
                    "Folder for type {} at {} does not exist and creation failed".format(
                        type, folder
                    )
                )

        else:
            # not extisting, not allowed to create it
            raise OSError(f"No such folder: {folder}")

    elif os.path.isfile(folder):
        # hardening against misconfiguration, see #1953
        raise OSError(f"Expected a folder at {folder} but found a file instead")

    elif check_writable:
        # make sure we can also write into the folder
        error = "Folder at {} doesn't appear to be writable, please fix its permissions".format(
            folder
        )
        if not os.access(folder, os.W_OK):
            raise OSError(error)

        elif deep_check_writable:
            # try to write a file to the folder - on network shares that might be the only reliable way
            # to determine whether things are *actually* writable
            testfile = os.path.join(folder, ".testballoon.txt")
            try:
                with open(testfile, "w", encoding="utf-8") as f:
                    f.write("test")
                os.remove(testfile)
            except Exception:
                logger.exception(f"Could not write test file to {testfile}")
                raise OSError(error)


def _paths(prefix, data):
    if isinstance(data, dict):
        for k, v in data.items():
            yield from _paths(prefix + [k], v)
    else:
        yield prefix
