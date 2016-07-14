# coding=utf-8
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

from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import sys
import os
import yaml
import yaml.parser
import logging
import re
import uuid
import copy

try:
	from collections import ChainMap
except ImportError:
	from chainmap import ChainMap

from octoprint.util import atomic_write, is_hidden_path, dict_merge

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
		"autoconnect": False,
		"log": False,
		"timeout": {
			"detection": 0.5,
			"connection": 10,
			"communication": 30,
			"heatup": 2,
			"temperature": 5,
			"temperatureTargetSet": 2,
			"sdStatus": 1
		},
		"additionalPorts": [],
		"additionalBaudrates": [],
		"longRunningCommands": ["G4", "G28", "G29", "G30", "G32", "M400", "M226"],
		"checksumRequiringCommands": ["M110"],
		"helloCommand": "M110 N0",
		"disconnectOnErrors": True,
		"ignoreErrorsFromFirmware": False,
		"logResends": True,
		"supportResendsWithoutOk": False,

		# command specific flags
		"triggerOkForM29": True
	},
	"server": {
		"host": "0.0.0.0",
		"port": 5000,
		"firstRun": True,
		"seenWizards": {},
		"secretKey": None,
		"reverseProxy": {
			"prefixHeader": "X-Script-Name",
			"schemeHeader": "X-Scheme",
			"hostHeader": "X-Forwarded-Host",
			"prefixFallback": "",
			"schemeFallback": "",
			"hostFallback": ""
		},
		"uploads": {
			"maxSize":  1 * 1024 * 1024 * 1024, # 1GB
			"nameSuffix": "name",
			"pathSuffix": "path"
		},
		"maxSize": 100 * 1024, # 100 KB
		"commands": {
			"systemShutdownCommand": None,
			"systemRestartCommand": None,
			"serverRestartCommand": None
		},
		"diskspace": {
			"warning": 500 * 1024 * 1024, # 500 MB
			"critical": 200 * 1024 * 1024, # 200 MB
		},
		"preemptiveCache": {
			"exceptions": [],
			"until": 7
		}
	},
	"webcam": {
		"stream": None,
		"snapshot": None,
		"ffmpeg": None,
		"ffmpegThreads": 1,
		"bitrate": "5000k",
		"watermark": True,
		"flipH": False,
		"flipV": False,
		"rotate90" : False,
		"timelapse": {
			"type": "off",
			"options": {},
			"postRoll": 0,
			"fps": 25
		},
		"cleanTmpAfterDays": 7
	},
	"gcodeViewer": {
		"enabled": True,
		"mobileSizeThreshold": 2 * 1024 * 1024, # 2MB
		"sizeThreshold": 20 * 1024 * 1024, # 20MB
	},
	"gcodeAnalysis": {
		"maxExtruders": 10
	},
	"feature": {
		"temperatureGraph": True,
		"waitForStartOnConnect": False,
		"alwaysSendChecksum": False,
		"neverSendChecksum": False,
		"sendChecksumWithUnknownCommands": False,
		"unknownCommandsNeedAck": False,
		"sdSupport": True,
		"sdRelativePath": False,
		"sdAlwaysAvailable": False,
		"swallowOkAfterResend": True,
		"repetierTargetTemp": False,
		"externalHeatupDetection": True,
		"supportWait": True,
		"keyboardControl": True,
		"pollWatched": False,
		"ignoreIdenticalResends": False,
		"identicalResendsCountdown": 7,
		"supportFAsCommand": False,
		"modelSizeDetection": True
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
		"data": None
	},
	"temperature": {
		"profiles": [
			{"name": "ABS", "extruder" : 210, "bed" : 100 },
			{"name": "PLA", "extruder" : 180, "bed" : 60 }
		],
		"cutoff": 30
	},
	"printerProfiles": {
		"default": None,
		"defaultProfile": {}
	},
	"printerParameters": {
		"pauseTriggers": [],
		"defaultExtrusionLength": 5
	},
	"appearance": {
		"name": "",
		"color": "default",
		"colorTransparent": False,
		"defaultLanguage": "_default",
		"showFahrenheitAlso": False,
		"components": {
			"order": {
				"navbar": ["settings", "systemmenu", "login", "plugin_announcements"],
				"sidebar": ["connection", "state", "files"],
				"tab": ["temperature", "control", "gcodeviewer", "terminal", "timelapse"],
				"settings": [
					"section_printer", "serial", "printerprofiles", "temperatures", "terminalfilters", "gcodescripts",
					"section_features", "features", "webcam", "accesscontrol", "gcodevisualizer", "api",
					"section_octoprint", "server", "folders", "appearance", "logs", "plugin_pluginmanager", "plugin_softwareupdate", "plugin_announcements"
				],
				"usersettings": ["access", "interface"],
				"wizard": ["access"],
				"about": ["about", "supporters", "authors", "changelog", "license", "thirdparty", "plugin_pluginmanager"],
				"generic": []
			},
			"disabled": {
				"navbar": [],
				"sidebar": [],
				"tab": [],
				"settings": [],
				"usersettings": [],
				"generic": []
			}
		}
	},
	"controls": [],
	"system": {
		"actions": []
	},
	"accessControl": {
		"enabled": True,
		"salt": None,
		"userManager": "octoprint.users.FilebasedUserManager",
		"userfile": None,
		"autologinLocal": False,
		"localNetworks": ["127.0.0.0/8"],
		"autologinAs": None
	},
	"slicing": {
		"enabled": True,
		"defaultSlicer": "cura",
		"defaultProfiles": None
	},
	"events": {
		"enabled": True,
		"subscriptions": []
	},
	"api": {
		"enabled": True,
		"key": None,
		"allowCrossOrigin": False,
		"apps": {}
	},
	"terminalFilters": [
		{ "name": "Suppress M105 requests/responses", "regex": "(Send: M105)|(Recv: ok (B|T\d*):)" },
		{ "name": "Suppress M27 requests/responses", "regex": "(Send: M27)|(Recv: SD printing byte)" }
	],
	"plugins": {
		"_disabled": []
	},
	"scripts": {
		"gcode": {
			"afterPrintCancelled": "; disable motors\nM84\n\n;disable all heaters\n{% snippet 'disable_hotends' %}\n{% snippet 'disable_bed' %}\n;disable fan\nM106 S0",
			"snippets": {
				"disable_hotends": "{% for tool in range(printer_profile.extruder.count) %}M104 T{{ tool }} S0\n{% endfor %}",
				"disable_bed": "{% if printer_profile.heatedBed %}M140 S0\n{% endif %}"
			}
		}
	},
	"devel": {
		"stylesheet": "css",
		"cache": {
			"enabled": True,
			"preemptive": True
		},
		"webassets": {
			"minify": False,
			"bundle": True,
			"clean_on_startup": True
		},
		"virtualPrinter": {
			"enabled": False,
			"okAfterResend": False,
			"forceChecksum": False,
			"okWithLinenumber": False,
			"numExtruders": 1,
			"includeCurrentToolInTemps": True,
			"includeFilenameInOpened": True,
			"movementSpeed": {
				"x": 6000,
				"y": 6000,
				"z": 200,
				"e": 300
			},
			"hasBed": True,
			"repetierStyleTargetTemperature": False,
			"repetierStyleResends": False,
			"okBeforeCommandOutput": False,
			"smoothieTemperatureReporting": False,
			"extendedSdFileList": False,
			"throttle": 0.01,
			"waitOnLongMoves": False,
			"rxBuffer": 64,
			"txBuffer": 40,
			"commandBuffer": 4,
			"sendWait": True,
			"waitInterval": 1.0,
			"supportM112": True,
			"echoOnM117": True,
			"brokenM29": True,
			"supportF": False
		}
	}
}
"""The default settings of the core application."""

valid_boolean_trues = [True, "true", "yes", "y", "1"]
""" Values that are considered to be equivalent to the boolean ``True`` value, used for type conversion in various places."""


class NoSuchSettingsPath(BaseException):
	pass


class InvalidSettings(BaseException):
	def __init__(self, message, line=None, column=None, details=None):
		self.message = message
		self.line = line
		self.column = column
		self.details = details


class HierarchicalChainMap(ChainMap):

	def deep_dict(self, root=None):
		if root is None:
			root = self

		result = dict()
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
					current = self.__class__._get_next(key, current, only_local=only_local)
				else:
					return False
			return path[-1] in current
		except KeyError:
			return False

	def get_by_path(self, path, only_local=False, only_defaults=False):
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

		return current[path[-1]]

	def set_by_path(self, path, value):
		current = self

		for key in path[:-1]:
			if key not in current.maps[0]:
				current.maps[0][key] = dict()
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
				wrapped_mappings.append(dict())
		return HierarchicalChainMap(*wrapped_mappings)

	@classmethod
	def _get_next(cls, key, node, only_local=False):
		if isinstance(node, dict):
			return node[key]
		elif only_local and not key in node.maps[0]:
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

	def __init__(self, configfile=None, basedir=None):
		self._logger = logging.getLogger(__name__)

		self._basedir = None

		self._map = HierarchicalChainMap(dict(), default_settings)

		self._config = None
		self._dirty = False
		self._mtime = None

		self._get_preprocessors = dict(
			controls=self._process_custom_controls
		)
		self._set_preprocessors = dict()

		self._init_basedir(basedir)

		if configfile is not None:
			self._configfile = configfile
		else:
			self._configfile = os.path.join(self._basedir, "config.yaml")
		self.load(migrate=True)

		if self.get(["api", "key"]) is None:
			self.set(["api", "key"], ''.join('%02X' % ord(z) for z in uuid.uuid4().bytes))
			self.save(force=True)

		self._script_env = self._init_script_templating()

	def _init_basedir(self, basedir):
		if basedir is not None:
			self._basedir = basedir
		else:
			self._basedir = _default_basedir(_APPNAME)

		if not os.path.isdir(self._basedir):
			os.makedirs(self._basedir)

	def _get_default_folder(self, type):
		folder = default_settings["folder"][type]
		if folder is None:
			folder = os.path.join(self._basedir, type.replace("_", os.path.sep))
		return folder

	def _init_script_templating(self):
		from jinja2 import Environment, BaseLoader, ChoiceLoader, TemplateNotFound
		from jinja2.nodes import Include
		from jinja2.ext import Extension

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
						templates += map(lambda x: key + "/" + x, self._get_templates(scripts[key]))
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
					if not prefix in self._mapping:
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
		file_system_loader = FilteredFileSystemLoader(self.getBaseFolder("scripts"),
		                                              path_filter=path_filter)
		settings_loader = SettingsScriptLoader(self)
		choice_loader = ChoiceLoader([file_system_loader, settings_loader])
		select_loader = SelectLoader(choice_loader,
		                             dict(bundled=settings_loader,
		                                  file=file_system_loader))
		return RelEnvironment(loader=select_loader, extensions=[SnippetExtension])

	def _get_script_template(self, script_type, name, source=False):
		from jinja2 import TemplateNotFound

		template_name = script_type + "/" + name
		try:
			if source:
				template_name, _, _ = self._script_env.loader.get_source(self._script_env, template_name)
				return template_name
			else:
				return self._script_env.get_template(template_name)
		except TemplateNotFound:
			return None
		except:
			self._logger.exception("Exception while trying to resolve template {template_name}".format(**locals()))
			return None

	def _get_scripts(self, script_type):
		return self._script_env.list_templates(filter_func=lambda x: x.startswith(script_type+"/"))

	def _process_custom_controls(self, controls):
		def process_control(c):
			# shallow copy
			result = dict(c)

			if "regex" in result and "template" in result:
				# if it's a template matcher, we need to add a key to associate with the matcher output
				import hashlib
				key_hash = hashlib.md5()
				key_hash.update(result["regex"])
				result["key"] = key_hash.hexdigest()

				template_key_hash = hashlib.md5()
				template_key_hash.update(result["template"])
				result["template_key"] = template_key_hash.hexdigest()

			elif "children" in result:
				# if it has children we need to process them recursively
				result["children"] = map(process_control, [child for child in result["children"] if child is not None])

			return result

		return map(process_control, controls)

	@property
	def effective(self):
		return self._map.deep_dict()

	@property
	def effective_yaml(self):
		import yaml
		return yaml.safe_dump(self.effective)

	@property
	def effective_hash(self):
		import hashlib
		hash = hashlib.md5()
		hash.update(self.effective_yaml)
		return hash.hexdigest()

	@property
	def config_yaml(self):
		import yaml
		return yaml.safe_dump(self._config)

	@property
	def config_hash(self):
		import hashlib
		hash = hashlib.md5()
		hash.update(self.config_yaml)
		return hash.hexdigest()

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
		    int: The last modification time of the configuration file.
		"""
		stat = os.stat(self._configfile)
		return stat.st_mtime

	#~~ load and save

	def load(self, migrate=False):
		if os.path.exists(self._configfile) and os.path.isfile(self._configfile):
			with open(self._configfile, "r") as f:
				try:
					self._config = yaml.safe_load(f)
					self._mtime = self.last_modified
				except yaml.YAMLError as e:
					details = e.message

					if hasattr(e, "problem_mark"):
						line = e.problem_mark.line
						column = e.problem_mark.column
					else:
						line = None
						column = None

					raise InvalidSettings("Invalid YAML file: {}".format(self._configfile),
					                      details=details,
					                      line=line,
					                      column=column)
				except:
					raise
		# changed from else to handle cases where the file exists, but is empty / 0 bytes
		if not self._config:
			self._config = dict()

		if migrate:
			self._migrate_config()

	def load_overlay(self, overlay, migrate=True):
		config = None

		if callable(overlay):
			try:
				overlay = overlay(self)
			except:
				self._logger.exception("Error loading overlay from callable")
				return

		if isinstance(overlay, basestring):
			if os.path.exists(overlay) and os.path.isfile(overlay):
				with open(overlay, "r") as f:
					config = yaml.safe_load(f)
		elif isinstance(overlay, dict):
			config = overlay
		else:
			raise ValueError("Overlay must be either a path to a yaml file or a dictionary")

		if not isinstance(config, dict):
			raise ValueError("Configuration data must be a dict but is a {}".format(config.__class__))

		if migrate:
			self._migrate_config(config)
		return config

	def add_overlay(self, overlay):
		self._map.maps.insert(1, overlay)

	def _migrate_config(self, config=None):
		if config is None:
			config = self._config

		dirty = False

		migrators = (
			self._migrate_event_config,
			self._migrate_reverse_proxy_config,
			self._migrate_printer_parameters,
			self._migrate_gcode_scripts
		)

		for migrate in migrators:
			dirty = migrate(config) or dirty
		if dirty:
			self.save(force=True)

	def _migrate_gcode_scripts(self, config):
		"""
		Migrates an old development version of gcode scripts to the new template based format.
		"""

		dirty = False
		if "scripts" in config:
			if "gcode" in config["scripts"]:
				if "templates" in config["scripts"]["gcode"]:
					del config["scripts"]["gcode"]["templates"]

				replacements = dict(
					disable_steppers="M84",
					disable_hotends="{% snippet 'disable_hotends' %}",
					disable_bed="M140 S0",
					disable_fan="M106 S0"
				)

				for name, script in config["scripts"]["gcode"].items():
					self.saveScript("gcode", name, script.format(**replacements))
			del config["scripts"]
			dirty = True
		return dirty

	def _migrate_printer_parameters(self, config):
		"""
		Migrates the old "printer > parameters" data structure to the new printer profile mechanism.
		"""
		default_profile = config["printerProfiles"]["defaultProfile"] if "printerProfiles" in config and "defaultProfile" in config["printerProfiles"] else dict()
		dirty = False

		if "printerParameters" in config:
			printer_parameters = config["printerParameters"]

			if "movementSpeed" in printer_parameters or "invertAxes" in printer_parameters:
				default_profile["axes"] = dict(x=dict(), y=dict(), z=dict(), e=dict())
				if "movementSpeed" in printer_parameters:
					for axis in ("x", "y", "z", "e"):
						if axis in printer_parameters["movementSpeed"]:
							default_profile["axes"][axis]["speed"] = printer_parameters["movementSpeed"][axis]
					del config["printerParameters"]["movementSpeed"]
				if "invertedAxes" in printer_parameters:
					for axis in ("x", "y", "z", "e"):
						if axis in printer_parameters["invertedAxes"]:
							default_profile["axes"][axis]["inverted"] = True
					del config["printerParameters"]["invertedAxes"]

			if "numExtruders" in printer_parameters or "extruderOffsets" in printer_parameters:
				if not "extruder" in default_profile:
					default_profile["extruder"] = dict()

				if "numExtruders" in printer_parameters:
					default_profile["extruder"]["count"] = printer_parameters["numExtruders"]
					del config["printerParameters"]["numExtruders"]
				if "extruderOffsets" in printer_parameters:
					extruder_offsets = []
					for offset in printer_parameters["extruderOffsets"]:
						if "x" in offset and "y" in offset:
							extruder_offsets.append((offset["x"], offset["y"]))
					default_profile["extruder"]["offsets"] = extruder_offsets
					del config["printerParameters"]["extruderOffsets"]

			if "bedDimensions" in printer_parameters:
				bed_dimensions = printer_parameters["bedDimensions"]
				if not "volume" in default_profile:
					default_profile["volume"] = dict()

				if "circular" in bed_dimensions and "r" in bed_dimensions and bed_dimensions["circular"]:
					default_profile["volume"]["formFactor"] = "circular"
					default_profile["volume"]["width"] = 2 * bed_dimensions["r"]
					default_profile["volume"]["depth"] = default_profile["volume"]["width"]
				elif "x" in bed_dimensions or "y" in bed_dimensions:
					default_profile["volume"]["formFactor"] = "rectangular"
					if "x" in bed_dimensions:
						default_profile["volume"]["width"] = bed_dimensions["x"]
					if "y" in bed_dimensions:
						default_profile["volume"]["depth"] = bed_dimensions["y"]
				del config["printerParameters"]["bedDimensions"]

			dirty = True

		if dirty:
			if not "printerProfiles" in config:
				config["printerProfiles"] = dict()
			config["printerProfiles"]["defaultProfile"] = default_profile
		return dirty

	def _migrate_reverse_proxy_config(self, config):
		"""
		Migrates the old "server > baseUrl" and "server > scheme" configuration entries to
		"server > reverseProxy > prefixFallback" and "server > reverseProxy > schemeFallback".
		"""
		if "server" in config.keys() and ("baseUrl" in config["server"] or "scheme" in config["server"]):
			prefix = ""
			if "baseUrl" in config["server"]:
				prefix = config["server"]["baseUrl"]
				del config["server"]["baseUrl"]

			scheme = ""
			if "scheme" in config["server"]:
				scheme = config["server"]["scheme"]
				del config["server"]["scheme"]

			if not "reverseProxy" in config["server"] or not isinstance(config["server"]["reverseProxy"], dict):
				config["server"]["reverseProxy"] = dict()
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
		"""
		if "events" in config.keys() and ("gcodeCommandTrigger" in config["events"] or "systemCommandTrigger" in config["events"]):
			self._logger.info("Migrating config (event subscriptions)...")

			# migrate event hooks to new format
			placeholderRe = re.compile("%\((.*?)\)s")

			eventNameReplacements = {
				"ClientOpen": "ClientOpened",
				"TransferStart": "TransferStarted"
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
						command = command.replace("{__%s}" % key, payloadDataReplacements[event][key])

				# return processed tuple
				return event, command

			disableSystemCommands = False
			if "systemCommandTrigger" in config["events"] and "enabled" in config["events"]["systemCommandTrigger"]:
				disableSystemCommands = not config["events"]["systemCommandTrigger"]["enabled"]

			disableGcodeCommands = False
			if "gcodeCommandTrigger" in config["events"] and "enabled" in config["events"]["gcodeCommandTrigger"]:
				disableGcodeCommands = not config["events"]["gcodeCommandTrigger"]["enabled"]

			disableAllCommands = disableSystemCommands and disableGcodeCommands
			newEvents = {
				"enabled": not disableAllCommands,
				"subscriptions": []
			}

			if "systemCommandTrigger" in config["events"] and "subscriptions" in config["events"]["systemCommandTrigger"]:
				for trigger in config["events"]["systemCommandTrigger"]["subscriptions"]:
					if not ("event" in trigger and "command" in trigger):
						continue

					newTrigger = {"type": "system"}
					if disableSystemCommands and not disableAllCommands:
						newTrigger["enabled"] = False

					newTrigger["event"], newTrigger["command"] = migrateEventHook(trigger["event"], trigger["command"])
					newEvents["subscriptions"].append(newTrigger)

			if "gcodeCommandTrigger" in config["events"] and "subscriptions" in config["events"]["gcodeCommandTrigger"]:
				for trigger in config["events"]["gcodeCommandTrigger"]["subscriptions"]:
					if not ("event" in trigger and "command" in trigger):
						continue

					newTrigger = {"type": "gcode"}
					if disableGcodeCommands and not disableAllCommands:
						newTrigger["enabled"] = False

					newTrigger["event"], newTrigger["command"] = migrateEventHook(trigger["event"], trigger["command"])
					newTrigger["command"] = newTrigger["command"].split(",")
					newEvents["subscriptions"].append(newTrigger)

			config["events"] = newEvents
			self._logger.info("Migrated %d event subscriptions to new format and structure" % len(newEvents["subscriptions"]))
			return True
		else:
			return False

	def save(self, force=False):
		if not self._dirty and not force:
			return False

		from octoprint.util import atomic_write
		try:
			with atomic_write(self._configfile, "wb", prefix="octoprint-config-", suffix=".yaml") as configFile:
				yaml.safe_dump(self._config, configFile, default_flow_style=False, indent="    ", allow_unicode=True)
				self._dirty = False
		except:
			self._logger.exception("Error while saving config.yaml!")
			raise
		else:
			self.load()
			return True

	##~~ Internal getter

	def _get_by_path(self, path, config):
		current = config
		for key in path:
			if key not in current:
				raise NoSuchSettingsPath()
			current = current[key]
		return current

	def _get_value(self, path, asdict=False, config=None, defaults=None, preprocessors=None, merged=False, incl_defaults=True, do_copy=True):
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

		preprocessor = None
		if preprocessors is not None:
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
			results = dict()
		else:
			results = list()

		for key in keys:
			try:
				value = chain.get_by_path(parent_path + [key], only_local=not incl_defaults)
			except KeyError:
				raise NoSuchSettingsPath()

			if isinstance(value, dict) and merged:
				try:
					default_value = chain.get_by_path(parent_path + [key], only_defaults=True)
					if default_value is not None:
						value = dict_merge(default_value, value)
				except KeyError:
					raise NoSuchSettingsPath()

			if preprocessors is not None:
				try:
					preprocessor = self._get_by_path(path, preprocessors)
				except:
					pass

				if callable(preprocessor):
					value = preprocessor(value)

			if do_copy:
				value = copy.deepcopy(value)

			if asdict:
				results[key] = value
			else:
				results.append(value)

		if not isinstance(last, (list, tuple)):
			if asdict:
				return results.values().pop()
			else:
				return results.pop()
		else:
			return results

	#~~ has

	def has(self, path, **kwargs):
		try:
			self._get_value(path, **kwargs)
		except NoSuchSettingsPath:
			return False
		else:
			return True

	#~~ getter

	def get(self, path, **kwargs):
		error_on_path = kwargs.get("error_on_path", False)
		new_kwargs = dict(kwargs)
		if "error_on_path" in new_kwargs:
			del new_kwargs["error_on_path"]

		try:
			return self._get_value(path, **new_kwargs)
		except NoSuchSettingsPath:
			if error_on_path:
				raise
			return None

	def getInt(self, path, **kwargs):
		value = self.get(path, **kwargs)
		if value is None:
			return None

		try:
			return int(value)
		except ValueError:
			self._logger.warn("Could not convert %r to a valid integer when getting option %r" % (value, path))
			return None

	def getFloat(self, path, **kwargs):
		value = self.get(path, **kwargs)
		if value is None:
			return None

		try:
			return float(value)
		except ValueError:
			self._logger.warn("Could not convert %r to a valid integer when getting option %r" % (value, path))
			return None

	def getBoolean(self, path, **kwargs):
		value = self.get(path, **kwargs)
		if value is None:
			return None
		if isinstance(value, bool):
			return value
		if isinstance(value, (int, float)):
			return value != 0
		if isinstance(value, (str, unicode)):
			return value.lower() in valid_boolean_trues
		return value is not None

	def getBaseFolder(self, type, create=True):
		if type not in default_settings["folder"].keys() + ["base"]:
			return None

		if type == "base":
			return self._basedir

		folder = self.get(["folder", type])
		if folder is None:
			folder = self._get_default_folder(type)

		if not os.path.isdir(folder):
			if create:
				os.makedirs(folder)
			else:
				raise IOError("No such folder: {folder}".format(folder=folder))

		return folder

	def listScripts(self, script_type):
		return map(lambda x: x[len(script_type + "/"):], filter(lambda x: x.startswith(script_type + "/"), self._get_scripts(script_type)))

	def loadScript(self, script_type, name, context=None, source=False):
		if context is None:
			context = dict()
		context.update(dict(script=dict(type=script_type, name=name)))

		template = self._get_script_template(script_type, name, source=source)
		if template is None:
			return None

		if source:
			script = template
		else:
			try:
				script = template.render(**context)
			except:
				self._logger.exception("Exception while trying to render script {script_type}:{name}".format(**locals()))
				return None

		return script

	#~~ remove

	def remove(self, path, config=None, error_on_path=False):
		if not path:
			if error_on_path:
				raise NoSuchSettingsPath()
			return

		if config is not None:
			mappings = [config] + self._overlay_maps + [self._default_map]
			chain = HierarchicalChainMap(*mappings)
		else:
			chain = self._map

		try:
			chain.del_by_path(path)
			self._dirty = True
		except KeyError:
			if error_on_path:
				raise NoSuchSettingsPath()
			pass

	#~~ setter

	def set(self, path, value, force=False, defaults=None, config=None, preprocessors=None, error_on_path=False):
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

		preprocessor = None
		if preprocessors is not None:
			try:
				preprocessor = self._get_by_path(path, preprocessors)
			except NoSuchSettingsPath:
				pass

			if callable(preprocessor):
				value = preprocessor(value)

		try:
			current = chain.get_by_path(path)
			default_value = chain.get_by_path(path, only_defaults=True)
			in_local = chain.has_path(path, only_local=True)
			in_defaults = chain.has_path(path, only_defaults=True)
		except KeyError:
			if error_on_path:
				raise NoSuchSettingsPath()
			return

		if not force and in_defaults and in_local and default_value == value:
			try:
				chain.del_by_path(path)
				self._dirty = True
			except KeyError:
				if error_on_path:
					raise NoSuchSettingsPath()
				pass
		elif force or (not in_local and in_defaults and default_value != value) or (in_local and current != value):
			if value is None and in_local:
				chain.del_by_path(path)
			else:
				chain.set_by_path(path, value)
			self._dirty = True

	def setInt(self, path, value, **kwargs):
		if value is None:
			self.set(path, None, **kwargs)
			return

		try:
			intValue = int(value)
		except ValueError:
			self._logger.warn("Could not convert %r to a valid integer when setting option %r" % (value, path))
			return

		self.set(path, intValue, **kwargs)

	def setFloat(self, path, value, **kwargs):
		if value is None:
			self.set(path, None, **kwargs)
			return

		try:
			floatValue = float(value)
		except ValueError:
			self._logger.warn("Could not convert %r to a valid integer when setting option %r" % (value, path))
			return

		self.set(path, floatValue, **kwargs)

	def setBoolean(self, path, value, **kwargs):
		if value is None or isinstance(value, bool):
			self.set(path, value, **kwargs)
		elif isinstance(value, basestring) and value.lower() in valid_boolean_trues:
			self.set(path, True, **kwargs)
		else:
			self.set(path, False, **kwargs)

	def setBaseFolder(self, type, path, force=False):
		if type not in default_settings["folder"].keys():
			return None

		currentPath = self.getBaseFolder(type)
		defaultPath = self._get_default_folder(type)
		if (path is None or path == defaultPath) and "folder" in self._config.keys() and type in self._config["folder"].keys():
			del self._config["folder"][type]
			if not self._config["folder"]:
				del self._config["folder"]
			self._dirty = True
		elif (path != currentPath and path != defaultPath) or force:
			if not "folder" in self._config.keys():
				self._config["folder"] = {}
			self._config["folder"][type] = path
			self._dirty = True

	def saveScript(self, script_type, name, script):
		script_folder = self.getBaseFolder("scripts")
		filename = os.path.realpath(os.path.join(script_folder, script_type, name))
		if not filename.startswith(os.path.realpath(script_folder)):
			# oops, jail break, that shouldn't happen
			raise ValueError("Invalid script path to save to: {filename} (from {script_type}:{name})".format(**locals()))

		path, _ = os.path.split(filename)
		if not os.path.exists(path):
			os.makedirs(path)
		with atomic_write(filename, "wb") as f:
			f.write(script)

def _default_basedir(applicationName):
	# taken from http://stackoverflow.com/questions/1084697/how-do-i-store-desktop-application-data-in-a-cross-platform-way-for-python
	if sys.platform == "darwin":
		from AppKit import NSSearchPathForDirectoriesInDomains
		# http://developer.apple.com/DOCUMENTATION/Cocoa/Reference/Foundation/Miscellaneous/Foundation_Functions/Reference/reference.html#//apple_ref/c/func/NSSearchPathForDirectoriesInDomains
		# NSApplicationSupportDirectory = 14
		# NSUserDomainMask = 1
		# True for expanding the tilde into a fully qualified path
		return os.path.join(NSSearchPathForDirectoriesInDomains(14, 1, True)[0], applicationName)
	elif sys.platform == "win32":
		return os.path.join(os.environ["APPDATA"], applicationName)
	else:
		return os.path.expanduser(os.path.join("~", "." + applicationName.lower()))
