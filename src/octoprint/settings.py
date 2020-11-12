# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

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

import copy
import io
import logging
import os
import re
import sys
import time

import yaml
import yaml.parser

# noinspection PyCompatibility
from past.builtins import basestring

try:
    from collections import ChainMap
except ImportError:
    from chainmap import ChainMap

try:
    from collections.abc import KeysView
except ImportError:
    from collections import KeysView

from octoprint.util import (
    CaseInsensitiveSet,
    atomic_write,
    dict_merge,
    generate_api_key,
    is_hidden_path,
)

_APPNAME = "OctoPrint"

_instance = None


def settings(init=False, basedir=None, configfile=None):
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
            _instance = Settings(configfile=configfile, basedir=basedir)
        else:
            raise ValueError("Settings not initialized yet")

    return _instance


default_settings = {
    "serial": {
        "port": None,
        "baudrate": None,
        "exclusive": True,
        "autoconnect": False,
        "log": False,
        "timeout": {
            "detectionFirst": 10,
            "detectionConsecutive": 2,
            "connection": 10,
            "communication": 30,
            "communicationBusy": 3,
            "temperature": 5,
            "temperatureTargetSet": 2,
            "temperatureAutoreport": 2,
            "sdStatus": 1,
            "sdStatusAutoreport": 1,
            "resendOk": 0.5,
            "baudrateDetectionPause": 1.0,
            "positionLogWait": 10.0,
        },
        "maxCommunicationTimeouts": {"idle": 2, "printing": 5, "long": 5},
        "maxWritePasses": 5,
        "additionalPorts": [],
        "additionalBaudrates": [],
        "blacklistedPorts": [],
        "blacklistedBaudrates": [],
        "longRunningCommands": ["G4", "G28", "G29", "G30", "G32", "M400", "M226", "M600"],
        "blockedCommands": ["M0", "M1"],
        "pausingCommands": ["M0", "M1", "M25"],
        "emergencyCommands": ["M112", "M108", "M410"],
        "checksumRequiringCommands": ["M110"],
        "helloCommand": "M110 N0",
        "disconnectOnErrors": True,
        "ignoreErrorsFromFirmware": False,
        "terminalLogSize": 20,
        "logResends": True,
        "supportResendsWithoutOk": "detect",
        "logPositionOnPause": True,
        "logPositionOnCancel": False,
        "abortHeatupOnCancel": True,
        "waitForStartOnConnect": False,
        "alwaysSendChecksum": False,
        "neverSendChecksum": False,
        "sendChecksumWithUnknownCommands": False,
        "unknownCommandsNeedAck": False,
        "sdRelativePath": False,
        "sdAlwaysAvailable": False,
        "maxNotSdPrinting": 2,
        "swallowOkAfterResend": True,
        "repetierTargetTemp": False,
        "externalHeatupDetection": True,
        "supportWait": True,
        "ignoreIdenticalResends": False,
        "identicalResendsCountdown": 7,
        "supportFAsCommand": False,
        "firmwareDetection": True,
        "blockWhileDwelling": False,
        "useParityWorkaround": "detect",
        "maxConsecutiveResends": 10,
        "sendM112OnError": True,
        "disableSdPrintingDetection": False,
        "ackMax": 1,
        "sanityCheckTools": True,
        "notifySuppressedCommands": "warn",
        "capabilities": {
            "autoreport_temp": True,
            "autoreport_sdstatus": True,
            "busy_protocol": True,
            "emergency_parser": True,
        },
        "resendRatioThreshold": 10,
        "resendRatioStart": 100,
        # command specific flags
        "triggerOkForM29": True,
    },
    "server": {
        "host": None,
        "port": 5000,
        "firstRun": True,
        "startOnceInSafeMode": False,
        "ignoreIncompleteStartup": False,
        "incompleteStartup": False,
        "seenWizards": {},
        "secretKey": None,
        "heartbeat": 15 * 60,  # 15 min
        "reverseProxy": {
            "prefixHeader": None,
            "schemeHeader": None,
            "hostHeader": None,
            "serverHeader": None,
            "portHeader": None,
            "prefixFallback": None,
            "schemeFallback": None,
            "hostFallback": None,
            "serverFallback": None,
            "portFallback": None,
            "trustedDownstream": [],
        },
        "uploads": {
            "maxSize": 1 * 1024 * 1024 * 1024,  # 1GB
            "nameSuffix": "name",
            "pathSuffix": "path",
        },
        "maxSize": 100 * 1024,  # 100 KB
        "commands": {
            "systemShutdownCommand": None,
            "systemRestartCommand": None,
            "serverRestartCommand": None,
            "localPipCommand": None,
        },
        "onlineCheck": {
            "enabled": None,
            "interval": 15 * 60,  # 15 min
            "host": "8.8.8.8",
            "port": 53,
            "name": "octoprint.org",
        },
        "pluginBlacklist": {
            "enabled": None,
            "url": "https://plugins.octoprint.org/blacklist.json",
            "ttl": 15 * 60,  # 15 min
        },
        "diskspace": {
            "warning": 500 * 1024 * 1024,  # 500 MB
            "critical": 200 * 1024 * 1024,  # 200 MB
        },
        "preemptiveCache": {"exceptions": [], "until": 7},
        "ipCheck": {"enabled": True, "trustedSubnets": []},
        "allowFraming": False,
        "cookies": {"secure": False, "samesite": None},
    },
    "webcam": {
        "webcamEnabled": True,
        "timelapseEnabled": True,
        "stream": None,
        "streamRatio": "16:9",
        "streamTimeout": 5,
        "snapshot": None,
        "snapshotTimeout": 5,
        "snapshotSslValidation": True,
        "ffmpeg": None,
        "ffmpegThreads": 1,
        "ffmpegVideoCodec": "libx264",
        "bitrate": "10000k",
        "watermark": True,
        "flipH": False,
        "flipV": False,
        "rotate90": False,
        "timelapse": {
            "type": "off",
            "options": {},
            "postRoll": 0,
            "fps": 25,
        },
        "cleanTmpAfterDays": 7,
    },
    "gcodeAnalysis": {
        "maxExtruders": 10,
        "throttle_normalprio": 0.01,
        "throttle_highprio": 0.0,
        "throttle_lines": 100,
        "runAt": "idle",  # 'never', 'idle', 'always'
    },
    "feature": {
        "temperatureGraph": True,
        "sdSupport": True,
        "keyboardControl": True,
        "pollWatched": False,
        "modelSizeDetection": True,
        "printStartConfirmation": False,
        "printCancelConfirmation": True,
        "autoUppercaseBlacklist": ["M117", "M118"],
        "g90InfluencesExtruder": False,
    },
    "folder": {
        "uploads": None,
        "timelapse": None,
        "timelapse_tmp": None,
        "logs": None,
        "virtualSd": None,
        "watched": None,
        "plugins": None,
        "slicingProfiles": None,
        "printerProfiles": None,
        "scripts": None,
        "translations": None,
        "generated": None,
        "data": None,
    },
    "temperature": {
        "profiles": [
            {"name": "ABS", "extruder": 210, "bed": 100},
            {"name": "PLA", "extruder": 180, "bed": 60},
        ],
        "cutoff": 30,
        "sendAutomatically": False,
        "sendAutomaticallyAfter": 1,
    },
    "printerProfiles": {"default": None},
    "printerParameters": {"pauseTriggers": [], "defaultExtrusionLength": 5},
    "appearance": {
        "name": "",
        "color": "default",
        "colorTransparent": False,
        "colorIcon": True,
        "defaultLanguage": "_default",
        "showFahrenheitAlso": False,
        "fuzzyTimes": True,
        "closeModalsWithClick": True,
        "showInternalFilename": True,
        "components": {
            "order": {
                "navbar": [
                    "settings",
                    "systemmenu",
                    "plugin_announcements",
                    "plugin_logging_seriallog",
                    "plugin_logging_plugintimingslog",
                    "plugin_pi_support",
                    "login",
                ],
                "sidebar": ["plugin_firmware_check", "connection", "state", "files"],
                "tab": [
                    "temperature",
                    "control",
                    "plugin_gcodeviewer",
                    "terminal",
                    "timelapse",
                ],
                "settings": [
                    "section_printer",
                    "serial",
                    "printerprofiles",
                    "temperatures",
                    "terminalfilters",
                    "gcodescripts",
                    "section_features",
                    "features",
                    "webcam",
                    "accesscontrol",
                    "plugin_gcodeviewer",
                    "api",
                    "plugin_appkeys",
                    "section_octoprint",
                    "server",
                    "folders",
                    "appearance",
                    "plugin_logging",
                    "plugin_pluginmanager",
                    "plugin_softwareupdate",
                    "plugin_announcements",
                    "plugin_backup",
                    "plugin_tracking",
                    "plugin_errortracking",
                    "plugin_pi_support",
                ],
                "usersettings": ["access", "interface"],
                "wizard": ["plugin_backup", "plugin_corewizard_acl"],
                "about": [
                    "about",
                    "plugin_pi_support",
                    "supporters",
                    "authors",
                    "changelog",
                    "license",
                    "thirdparty",
                    "plugin_pluginmanager",
                ],
                "generic": [],
            },
            "disabled": {
                "navbar": [],
                "sidebar": [],
                "tab": [],
                "settings": [],
                "usersettings": [],
                "generic": [],
            },
        },
    },
    "controls": [],
    "system": {"actions": []},
    "accessControl": {
        "salt": None,
        "userManager": "octoprint.access.users.FilebasedUserManager",
        "groupManager": "octoprint.access.groups.FilebasedGroupManager",
        "permissionManager": "octoprint.access.permissions.PermissionManager",
        "userfile": None,
        "groupfile": None,
        "autologinLocal": False,
        "localNetworks": ["127.0.0.0/8", "::1/128"],
        "autologinAs": None,
        "trustBasicAuthentication": False,
        "checkBasicAuthenticationPassword": True,
        "trustRemoteUser": False,
        "remoteUserHeader": "REMOTE_USER",
        "addRemoteUsers": False,
    },
    "slicing": {"enabled": True, "defaultSlicer": None, "defaultProfiles": None},
    "events": {"enabled": True, "subscriptions": []},
    "api": {"key": None, "allowCrossOrigin": False, "apps": {}},
    "terminalFilters": [
        {
            "name": "Suppress temperature messages",
            "regex": r"(Send: (N\d+\s+)?M105)|(Recv:\s+(ok\s+((P|B|N)\d+\s+)*)?(B|T\d*):\d+)",
        },
        {
            "name": "Suppress SD status messages",
            "regex": r"(Send: (N\d+\s+)?M27)|(Recv: SD printing byte)|(Recv: Not SD printing)",
        },
        {"name": "Suppress wait responses", "regex": r"Recv: wait"},
        {
            "name": "Suppress processing responses",
            "regex": r"Recv: (echo:\s*)?busy:\s*processing",
        },
    ],
    "plugins": {"_disabled": [], "_forcedCompatible": []},
    "scripts": {
        "gcode": {
            "afterPrintCancelled": "; disable motors\nM84\n\n;disable all heaters\n{% snippet 'disable_hotends' %}\n{% snippet 'disable_bed' %}\n;disable fan\nM106 S0",
            "snippets": {
                "disable_hotends": "{% if printer_profile.extruder.sharedNozzle %}M104 T0 S0\n{% else %}{% for tool in range(printer_profile.extruder.count) %}M104 T{{ tool }} S0\n{% endfor %}{% endif %}",
                "disable_bed": "{% if printer_profile.heatedBed %}M140 S0\n{% endif %}",
            },
        }
    },
    "estimation": {
        "printTime": {
            "statsWeighingUntil": 0.5,
            "validityRange": 0.15,
            "forceDumbFromPercent": 0.3,
            "forceDumbAfterMin": 30,
            "stableThreshold": 60,
        }
    },
    "devel": {
        "stylesheet": "css",
        "cache": {"enabled": True, "preemptive": True},
        "webassets": {
            "bundle": True,
            "clean_on_startup": True,
            "minify": True,
            "minify_plugins": False,
        },
        "useFrozenDictForPrinterState": True,
        "showLoadingAnimation": True,
        "sockJsConnectTimeout": 30,
        "pluginTimings": False,
    },
}
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


class HierarchicalChainMap(ChainMap):
    def deep_dict(self, root=None):
        if root is None:
            root = self

        result = {}
        for key, value in root.items():
            if isinstance(value, dict):
                result[key] = self.deep_dict(root=self.__class__._get_next(key, root))
            else:
                result[key] = value
        return result

    def has_path(self, path, only_local=False, only_defaults=False):
        if only_defaults:
            current = self.parents
        elif only_local:
            current = self.__class__(self.maps[0])
        else:
            current = self

        try:
            for key in path[:-1]:
                value = current[key]
                if isinstance(value, dict):
                    current = self.__class__._get_next(
                        key, current, only_local=only_local
                    )
                else:
                    return False
            return path[-1] in current
        except KeyError:
            return False

    def get_by_path(self, path, only_local=False, only_defaults=False, merged=False):
        if only_defaults:
            current = self.parents
        elif only_local:
            current = self.__class__(self.maps[0])
        else:
            current = self

        for key in path[:-1]:
            value = current[key]
            if isinstance(value, dict):
                current = self.__class__._get_next(key, current, only_local=only_local)
            else:
                raise KeyError(key)

        if merged:
            current = current.deep_dict()
        return current[path[-1]]

    def set_by_path(self, path, value):
        current = self

        for key in path[:-1]:
            if key not in current.maps[0]:
                current.maps[0][key] = {}
            if not isinstance(current[key], dict):
                raise KeyError(key)
            current = self.__class__._hierarchy_for_key(key, current)

        current[path[-1]] = value

    def del_by_path(self, path):
        if not path:
            raise ValueError("Invalid path")

        current = self

        for key in path[:-1]:
            if not isinstance(current[key], dict):
                raise KeyError(key)
            current = self.__class__._hierarchy_for_key(key, current)

        del current[path[-1]]

    @classmethod
    def _hierarchy_for_key(cls, key, chain):
        wrapped_mappings = list()
        for mapping in chain.maps:
            if key in mapping and mapping[key] is not None:
                wrapped_mappings.append(mapping[key])
            else:
                wrapped_mappings.append({})
        return HierarchicalChainMap(*wrapped_mappings)

    @classmethod
    def _get_next(cls, key, node, only_local=False):
        if isinstance(node, dict):
            return node[key]
        elif only_local and key not in node.maps[0]:
            raise KeyError(key)
        else:
            return cls._hierarchy_for_key(key, node)


class Settings(object):
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
            timeouts:
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

    def __init__(self, configfile=None, basedir=None):
        self._logger = logging.getLogger(__name__)

        self._basedir = None

        assert isinstance(default_settings, dict)

        self._map = HierarchicalChainMap({}, default_settings)

        self._config = None
        self._dirty = False
        self._dirty_time = 0
        self._last_config_hash = None
        self._last_effective_hash = None
        self._mtime = None

        self._get_preprocessors = {"controls": self._process_custom_controls}
        self._set_preprocessors = {}

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
        for folder in folders:
            self.getBaseFolder(
                folder, check_writable=True, deep_check_writable=True, log_error=True
            )

    def _get_default_folder(self, type):
        folder = default_settings["folder"][type]
        if folder is None:
            folder = os.path.join(self._basedir, type.replace("_", os.path.sep))
        return folder

    def _init_script_templating(self):
        from jinja2 import BaseLoader, ChoiceLoader, Environment, TemplateNotFound
        from jinja2.ext import Extension
        from jinja2.nodes import Include

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
                    elif isinstance(scripts[key], basestring):
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

        class RelEnvironment(Environment):
            def __init__(self, prefix_sep=":", *args, **kwargs):
                Environment.__init__(self, *args, **kwargs)
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
                "Exception while trying to resolve template {template_name}".format(
                    **locals()
                )
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
        self._dirty = True
        self._dirty_time = time.time()
        self._forget_hashes()

    @property
    def effective(self):
        return self._map.deep_dict()

    @property
    def effective_yaml(self):
        import yaml

        return yaml.safe_dump(self.effective)

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
        import yaml

        return yaml.safe_dump(self._config)

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
    def _config(self):
        return self._map.maps[0]

    @_config.setter
    def _config(self, value):
        self._map.maps[0] = value

    @property
    def _overlay_maps(self):
        if len(self._map.maps) > 2:
            return self._map.maps[1:-1]
        else:
            return []

    @property
    def _default_map(self):
        return self._map.maps[-1]

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
        if os.path.exists(self._configfile) and os.path.isfile(self._configfile):
            with io.open(self._configfile, "rt", encoding="utf-8", errors="replace") as f:
                try:
                    self._config = yaml.safe_load(f)
                    self._mtime = self.last_modified

                except yaml.YAMLError as e:
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
        if not self._config or not isinstance(self._config, dict):
            self._config = {}

        if migrate:
            self._migrate_config()
        self._validate_config()

        self._forget_hashes()

    def load_overlay(self, overlay, migrate=True):
        config = None

        if callable(overlay):
            try:
                overlay = overlay(self)
            except Exception:
                self._logger.exception("Error loading overlay from callable")
                return

        if isinstance(overlay, basestring):
            if os.path.exists(overlay) and os.path.isfile(overlay):
                with io.open(overlay, "rt", encoding="utf-8", errors="replace") as f:
                    config = yaml.safe_load(f)
        elif isinstance(overlay, dict):
            config = overlay
        else:
            raise ValueError(
                "Overlay must be either a path to a yaml file or a dictionary"
            )

        if not isinstance(config, dict):
            raise ValueError(
                "Configuration data must be a dict but is a {}".format(config.__class__)
            )

        if migrate:
            self._migrate_config(config)
        return config

    def add_overlay(self, overlay, at_end=False, key=None):
        assert isinstance(overlay, dict)

        if key is None:
            overlay_yaml = yaml.safe_dump(overlay)
            import hashlib

            hash = hashlib.md5()
            hash.update(overlay_yaml.encode("utf-8"))
            key = hash.hexdigest()

        overlay[self.OVERLAY_KEY] = key
        if at_end:
            pos = len(self._map.maps) - 1
            self._map.maps.insert(pos, overlay)
        else:
            self._map.maps.insert(1, overlay)

        return key

    def remove_overlay(self, key):
        index = -1
        for i, overlay in enumerate(self._overlay_maps):
            if key == overlay.get(self.OVERLAY_KEY):
                index = i

        if index > -1:
            del self._map.maps[index + 1]
            return True
        return False

    def _migrate_config(self, config=None, persist=False):
        if config is None:
            config = self._config
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
                    [v for v in blockedCommands if v not in ("M0", "M1")]
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

    def _validate_config(self):
        # validate uniqueness of folder paths
        folder_keys = self.get(["folder"], merged=True).keys()
        folders = dict(
            (folder_key, self.getBaseFolder(folder_key)) for folder_key in folder_keys
        )
        if len(folders.values()) != len(set(folders.values())):
            raise DuplicateFolderPaths(folders)

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
                yaml.safe_dump(
                    self._config,
                    configFile,
                    default_flow_style=False,
                    indent=4,
                    allow_unicode=True,
                )
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

        if config is not None or defaults is not None:
            if config is None:
                config = self._config

            if defaults is None:
                defaults = dict(self._map.parents)

            # mappings: provided config + any intermediary parents + provided defaults + regular defaults
            mappings = [config] + self._overlay_maps + [defaults, self._default_map]
            chain = HierarchicalChainMap(*mappings)
        else:
            chain = self._map

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
                    parent_path + [key], only_local=not incl_defaults
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
                    raise NoSuchSettingsPath()

            if preprocessors is not None:
                try:
                    preprocessor = self._get_by_path(path, preprocessors)
                except Exception:
                    pass

                if callable(preprocessor):
                    value = preprocessor(value)

            if do_copy:
                if isinstance(value, KeysView):
                    value = list(value)
                value = copy.deepcopy(value)

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
        if isinstance(value, basestring):
            return value.lower() in valid_boolean_trues
        return value is not None

    def getBaseFolder(
        self,
        type,
        create=True,
        allow_fallback=True,
        log_error=False,
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
                log_error=log_error,
            )
        except Exception:
            if folder != default_folder and allow_fallback:
                if log_error:
                    self._logger.error(
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
                    log_error=log_error,
                )
                folder = default_folder

                try:
                    del self._config["folder"][type]
                    if not len(self._config["folder"]):
                        del self._config["folder"]
                    self._mark_dirty()
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
                    "Exception while trying to render script {script_type}:{name}".format(
                        **locals()
                    )
                )
                return None

        return script

    # ~~ remove

    def remove(self, path, config=None, error_on_path=False, defaults=None):
        if not path:
            if error_on_path:
                raise NoSuchSettingsPath()
            return

        if config is not None or defaults is not None:
            if config is None:
                config = self._config

            if defaults is None:
                defaults = dict(self._map.parents)

            chain = HierarchicalChainMap(config, defaults)
        else:
            chain = self._map

        try:
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
        **kwargs
    ):
        if not path:
            if error_on_path:
                raise NoSuchSettingsPath()
            return

        if self._mtime is not None and self.last_modified != self._mtime:
            self.load()

        if config is not None or defaults is not None:
            if config is None:
                config = self._config

            if defaults is None:
                defaults = dict(self._map.parents)

            chain = HierarchicalChainMap(config, defaults)
        else:
            chain = self._map

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

        in_local = chain.has_path(path, only_local=True)
        in_defaults = chain.has_path(path, only_defaults=True)

        if not force and in_defaults and in_local and default_value == value:
            try:
                chain.del_by_path(path)
                self._mark_dirty()
            except KeyError:
                if error_on_path:
                    raise NoSuchSettingsPath()
                pass
        elif (
            force
            or (not in_local and in_defaults and default_value != value)
            or (in_local and current != value)
        ):
            if value is None and in_local:
                chain.del_by_path(path)
            else:
                chain.set_by_path(path, value)
            self._mark_dirty()

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
        elif isinstance(value, basestring) and value.lower() in valid_boolean_trues:
            self.set(path, True, **kwargs)
        else:
            self.set(path, False, **kwargs)

    def setBaseFolder(self, type, path, force=False, validate=True):
        if type not in default_settings["folder"]:
            return None

        currentPath = self.getBaseFolder(type)
        defaultPath = self._get_default_folder(type)
        if (
            (path is None or path == defaultPath)
            and "folder" in self._config
            and type in self._config["folder"]
        ):
            del self._config["folder"][type]
            if not self._config["folder"]:
                del self._config["folder"]
            self._mark_dirty()
        elif (path != currentPath and path != defaultPath) or force:
            if validate:
                _validate_folder(path, check_writable=True, deep_check_writable=True)

            if "folder" not in self._config:
                self._config["folder"] = {}
            self._config["folder"][type] = path
            self._mark_dirty()

    def saveScript(self, script_type, name, script):
        script_folder = self.getBaseFolder("scripts")
        filename = os.path.realpath(os.path.join(script_folder, script_type, name))
        if not filename.startswith(os.path.realpath(script_folder)):
            # oops, jail break, that shouldn't happen
            raise ValueError(
                "Invalid script path to save to: {filename} (from {script_type}:{name})".format(
                    **locals()
                )
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


def _validate_folder(
    folder, create=True, check_writable=True, deep_check_writable=False, log_error=False
):
    logger = logging.getLogger(__name__)

    if not os.path.exists(folder):
        if os.path.islink(folder):
            # broken symlink, see #2644
            raise IOError("Folder at {} appears to be a broken symlink".format(folder))

        elif create:
            # non existing, but we are allowed to create it
            try:
                os.makedirs(folder)
            except Exception:
                if log_error:
                    logger.exception("Could not create {}".format(folder))
                raise IOError(
                    "Folder for type {} at {} does not exist and creation failed".format(
                        type, folder
                    )
                )

        else:
            # not extisting, not allowed to create it
            raise IOError("No such folder: {}".format(folder))

    elif os.path.isfile(folder):
        # hardening against misconfiguration, see #1953
        raise IOError("Expected a folder at {} but found a file instead".format(folder))

    elif check_writable:
        # make sure we can also write into the folder
        error = "Folder at {} doesn't appear to be writable, please fix its permissions".format(
            folder
        )
        if not os.access(folder, os.W_OK):
            raise IOError(error)

        elif deep_check_writable:
            # try to write a file to the folder - on network shares that might be the only reliable way
            # to determine whether things are *actually* writable
            testfile = os.path.join(folder, ".testballoon.txt")
            try:
                with io.open(testfile, "wt", encoding="utf-8") as f:
                    f.write("test")
                os.remove(testfile)
            except Exception:
                if log_error:
                    logger.exception("Could not write test file to {}".format(folder))
                raise IOError(error)
