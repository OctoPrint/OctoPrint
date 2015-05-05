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
import logging
import re
import uuid

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
	    basedir (str): Path of the base directoy for all of OctoPrint's settings, log files, uploads etc. If not set
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
			"temperature": 5,
			"sdStatus": 1
		},
		"additionalPorts": []
	},
	"server": {
		"host": "0.0.0.0",
		"port": 5000,
		"firstRun": True,
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
		"timelapse": {
			"type": "off",
			"options": {},
			"postRoll": 0,
			"fps": 25
		}
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
		"sendChecksumWithUnknownCommands": False,
		"unknownCommandsNeedAck": False,
		"sdSupport": True,
		"sdAlwaysAvailable": False,
		"swallowOkAfterResend": True,
		"repetierTargetTemp": False,
		"externalHeatupDetection": True,
		"keyboardControl": True
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
		"scripts": None
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
		"components": {
			"order": {
				"navbar": ["settings", "systemmenu", "login"],
				"sidebar": ["connection", "state", "files"],
				"tab": ["temperature", "control", "gcodeviewer", "terminal", "timelapse"],
				"settings": [
					"section_printer", "serial", "printerprofiles", "temperatures", "terminalfilters", "gcodescripts",
					"section_features", "features", "webcam", "accesscontrol", "api",
					"section_octoprint", "folders", "appearance", "logs"
				],
				"usersettings": ["access", "interface"],
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
			"afterPrintCancelled": "; disable motors\nM84\n\n;disable all heaters\n{% snippet 'disable_hotends' %}\nM140 S0\n\n;disable fan\nM106 S0",
			"snippets": {
				"disable_hotends": "{% for tool in range(printer_profile.extruder.count) %}M104 T{{ tool }} S0\n{% endfor %}"
			}
		}
	},
	"devel": {
		"stylesheet": "css",
		"cache": {
			"enabled": True
		},
		"virtualPrinter": {
			"enabled": False,
			"okAfterResend": False,
			"forceChecksum": False,
			"okWithLinenumber": False,
			"numExtruders": 1,
			"includeCurrentToolInTemps": True,
			"movementSpeed": {
				"x": 6000,
				"y": 6000,
				"z": 200,
				"e": 300
			},
			"hasBed": True,
			"repetierStyleTargetTemperature": False,
			"okBeforeCommandOutput": False,
			"smoothieTemperatureReporting": False,
			"extendedSdFileList": False,
			"throttle": 0.01,
			"waitOnLongMoves": False,
			"rxBuffer": 64,
			"txBuffer": 40,
			"commandBuffer": 4
		}
	}
}
"""The default settings of the core application."""

valid_boolean_trues = [True, "true", "yes", "y", "1"]
""" Values that are considered to be equivalent to the boolean ``True`` value, used for type conversion in various places."""

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

	``["serial", "timeouts"]``                 ::

	                                               communication: 20.0
	                                               temperature: 5.0
	                                               sdStatus: 1.0
	                                               connection: 10.0

	``["serial", "timeouts", "temperature"]``  ::

	                                               5.0

	``["server", "port"]``                     ::

	                                               5000

	========================================== ============================================================================

	However, these would be invalid paths: ``["key"]``, ``["serial", "port", "value"]``, ``["server", "host", 3]``.
	"""

	def __init__(self, configfile=None, basedir=None):
		self._logger = logging.getLogger(__name__)

		self._basedir = None

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
		from jinja2 import Environment, BaseLoader, FileSystemLoader, ChoiceLoader, TemplateNotFound
		from jinja2.nodes import Include, Const
		from jinja2.ext import Extension

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
				return source, None, lambda: mtime == self._settings._last_modified

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

		file_system_loader = FileSystemLoader(self.getBaseFolder("scripts"))
		settings_loader = SettingsScriptLoader(self)
		choice_loader = ChoiceLoader([file_system_loader, settings_loader])
		select_loader = SelectLoader(choice_loader, dict(bundled=settings_loader, file=file_system_loader))
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

	#~~ load and save

	def load(self, migrate=False):
		if os.path.exists(self._configfile) and os.path.isfile(self._configfile):
			with open(self._configfile, "r") as f:
				self._config = yaml.safe_load(f)
				self._mtime = self._last_modified
		# changed from else to handle cases where the file exists, but is empty / 0 bytes
		if not self._config:
			self._config = {}

		if migrate:
			self._migrate_config()

	def _migrate_config(self):
		dirty = False

		migrators = (
			self._migrate_event_config,
			self._migrate_reverse_proxy_config,
			self._migrate_printer_parameters,
			self._migrate_gcode_scripts
		)

		for migrate in migrators:
			dirty = migrate() or dirty
		if dirty:
			self.save(force=True)

	def _migrate_gcode_scripts(self):
		"""
		Migrates an old development version of gcode scripts to the new template based format.
		"""

		dirty = False
		if "scripts" in self._config:
			if "gcode" in self._config["scripts"]:
				if "templates" in self._config["scripts"]["gcode"]:
					del self._config["scripts"]["gcode"]["templates"]

				replacements = dict(
					disable_steppers="M84",
					disable_hotends="{% snippet 'disable_hotends' %}",
					disable_bed="M140 S0",
					disable_fan="M106 S0"
				)

				for name, script in self._config["scripts"]["gcode"].items():
					self.saveScript("gcode", name, script.format(**replacements))
			del self._config["scripts"]
			dirty = True
		return dirty

	def _migrate_printer_parameters(self):
		"""
		Migrates the old "printer > parameters" data structure to the new printer profile mechanism.
		"""
		default_profile = self._config["printerProfiles"]["defaultProfile"] if "printerProfiles" in self._config and "defaultProfile" in self._config["printerProfiles"] else dict()
		dirty = False

		if "printerParameters" in self._config:
			printer_parameters = self._config["printerParameters"]

			if "movementSpeed" in printer_parameters or "invertAxes" in printer_parameters:
				default_profile["axes"] = dict(x=dict(), y=dict(), z=dict(), e=dict())
				if "movementSpeed" in printer_parameters:
					for axis in ("x", "y", "z", "e"):
						if axis in printer_parameters["movementSpeed"]:
							default_profile["axes"][axis]["speed"] = printer_parameters["movementSpeed"][axis]
					del self._config["printerParameters"]["movementSpeed"]
				if "invertedAxes" in printer_parameters:
					for axis in ("x", "y", "z", "e"):
						if axis in printer_parameters["invertedAxes"]:
							default_profile["axes"][axis]["inverted"] = True
					del self._config["printerParameters"]["invertedAxes"]

			if "numExtruders" in printer_parameters or "extruderOffsets" in printer_parameters:
				if not "extruder" in default_profile:
					default_profile["extruder"] = dict()

				if "numExtruders" in printer_parameters:
					default_profile["extruder"]["count"] = printer_parameters["numExtruders"]
					del self._config["printerParameters"]["numExtruders"]
				if "extruderOffsets" in printer_parameters:
					extruder_offsets = []
					for offset in printer_parameters["extruderOffsets"]:
						if "x" in offset and "y" in offset:
							extruder_offsets.append((offset["x"], offset["y"]))
					default_profile["extruder"]["offsets"] = extruder_offsets
					del self._config["printerParameters"]["extruderOffsets"]

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
				del self._config["printerParameters"]["bedDimensions"]

			dirty = True

		if dirty:
			if not "printerProfiles" in self._config:
				self._config["printerProfiles"] = dict()
			self._config["printerProfiles"]["defaultProfile"] = default_profile
		return dirty

	def _migrate_reverse_proxy_config(self):
		"""
		Migrates the old "server > baseUrl" and "server > scheme" configuration entries to
		"server > reverseProxy > prefixFallback" and "server > reverseProxy > schemeFallback".
		"""
		if "server" in self._config.keys() and ("baseUrl" in self._config["server"] or "scheme" in self._config["server"]):
			prefix = ""
			if "baseUrl" in self._config["server"]:
				prefix = self._config["server"]["baseUrl"]
				del self._config["server"]["baseUrl"]

			scheme = ""
			if "scheme" in self._config["server"]:
				scheme = self._config["server"]["scheme"]
				del self._config["server"]["scheme"]

			if not "reverseProxy" in self._config["server"] or not isinstance(self._config["server"]["reverseProxy"], dict):
				self._config["server"]["reverseProxy"] = dict()
			if prefix:
				self._config["server"]["reverseProxy"]["prefixFallback"] = prefix
			if scheme:
				self._config["server"]["reverseProxy"]["schemeFallback"] = scheme
			self._logger.info("Migrated reverse proxy configuration to new structure")
			return True
		else:
			return False

	def _migrate_event_config(self):
		"""
		Migrates the old event configuration format of type "events > gcodeCommandTrigger" and
		"event > systemCommandTrigger" to the new events format.
		"""
		if "events" in self._config.keys() and ("gcodeCommandTrigger" in self._config["events"] or "systemCommandTrigger" in self._config["events"]):
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
			if "systemCommandTrigger" in self._config["events"] and "enabled" in self._config["events"]["systemCommandTrigger"]:
				disableSystemCommands = not self._config["events"]["systemCommandTrigger"]["enabled"]

			disableGcodeCommands = False
			if "gcodeCommandTrigger" in self._config["events"] and "enabled" in self._config["events"]["gcodeCommandTrigger"]:
				disableGcodeCommands = not self._config["events"]["gcodeCommandTrigger"]["enabled"]

			disableAllCommands = disableSystemCommands and disableGcodeCommands
			newEvents = {
				"enabled": not disableAllCommands,
				"subscriptions": []
			}

			if "systemCommandTrigger" in self._config["events"] and "subscriptions" in self._config["events"]["systemCommandTrigger"]:
				for trigger in self._config["events"]["systemCommandTrigger"]["subscriptions"]:
					if not ("event" in trigger and "command" in trigger):
						continue

					newTrigger = {"type": "system"}
					if disableSystemCommands and not disableAllCommands:
						newTrigger["enabled"] = False

					newTrigger["event"], newTrigger["command"] = migrateEventHook(trigger["event"], trigger["command"])
					newEvents["subscriptions"].append(newTrigger)

			if "gcodeCommandTrigger" in self._config["events"] and "subscriptions" in self._config["events"]["gcodeCommandTrigger"]:
				for trigger in self._config["events"]["gcodeCommandTrigger"]["subscriptions"]:
					if not ("event" in trigger and "command" in trigger):
						continue

					newTrigger = {"type": "gcode"}
					if disableGcodeCommands and not disableAllCommands:
						newTrigger["enabled"] = False

					newTrigger["event"], newTrigger["command"] = migrateEventHook(trigger["event"], trigger["command"])
					newTrigger["command"] = newTrigger["command"].split(",")
					newEvents["subscriptions"].append(newTrigger)

			self._config["events"] = newEvents
			self._logger.info("Migrated %d event subscriptions to new format and structure" % len(newEvents["subscriptions"]))
			return True
		else:
			return False

	def save(self, force=False):
		if not self._dirty and not force:
			return False

		with open(self._configfile, "wb") as configFile:
			yaml.safe_dump(self._config, configFile, default_flow_style=False, indent="    ", allow_unicode=True)
			self._dirty = False
		self.load()
		return True

	@property
	def _last_modified(self):
		"""
		Returns:
		    int: The last modification time of the configuration file.
		"""
		stat = os.stat(self._configfile)
		return stat.st_mtime

	#~~ getter

	def get(self, path, asdict=False, config=None, defaults=None, preprocessors=None, merged=False):
		import octoprint.util as util

		if len(path) == 0:
			return None

		if config is None:
			config = self._config
		if defaults is None:
			defaults = default_settings
		if preprocessors is None:
			preprocessors = self._get_preprocessors

		while len(path) > 1:
			key = path.pop(0)
			if key in config and key in defaults:
				config = config[key]
				defaults = defaults[key]
			elif key in defaults:
				config = {}
				defaults = defaults[key]
			else:
				return None

			if preprocessors and isinstance(preprocessors, dict) and key in preprocessors:
				preprocessors = preprocessors[key]


		k = path.pop(0)
		if not isinstance(k, (list, tuple)):
			keys = [k]
		else:
			keys = k

		if asdict:
			results = {}
		else:
			results = []
		for key in keys:
			if key in config:
				value = config[key]
				if merged and key in defaults:
					value = util.dict_merge(defaults[key], value)
			elif key in defaults:
				value = defaults[key]
			else:
				value = None

			if preprocessors and isinstance(preprocessors, dict) and key in preprocessors and callable(preprocessors[key]):
				value = preprocessors[key](value)

			if asdict:
				results[key] = value
			else:
				results.append(value)

		if not isinstance(k, (list, tuple)):
			if asdict:
				return results.values().pop()
			else:
				return results.pop()
		else:
			return results

	def getInt(self, path, config=None, defaults=None, preprocessors=None):
		value = self.get(path, defaults=defaults, preprocessors=preprocessors)
		if value is None:
			return None

		try:
			return int(value)
		except ValueError:
			self._logger.warn("Could not convert %r to a valid integer when getting option %r" % (value, path))
			return None

	def getFloat(self, path, config=None, defaults=None, preprocessors=None):
		value = self.get(path, config=config, defaults=defaults, preprocessors=preprocessors)
		if value is None:
			return None

		try:
			return float(value)
		except ValueError:
			self._logger.warn("Could not convert %r to a valid integer when getting option %r" % (value, path))
			return None

	def getBoolean(self, path, config=None, defaults=None, preprocessors=None):
		value = self.get(path, config=config, defaults=defaults, preprocessors=preprocessors)
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

	#~~ setter

	def set(self, path, value, force=False, defaults=None, preprocessors=None):
		if len(path) == 0:
			return

		if self._mtime is not None and self._last_modified != self._mtime:
			self.load()

		config = self._config
		if defaults is None:
			defaults = default_settings
		if preprocessors is None:
			preprocessors = self._set_preprocessors

		while len(path) > 1:
			key = path.pop(0)
			if key in config.keys() and key in defaults.keys():
				config = config[key]
				defaults = defaults[key]
			elif key in defaults.keys():
				config[key] = {}
				config = config[key]
				defaults = defaults[key]
			else:
				return

			if preprocessors and isinstance(preprocessors, dict) and key in preprocessors:
				preprocessors = preprocessors[key]

		key = path.pop(0)

		if preprocessors and isinstance(preprocessors, dict) and key in preprocessors and callable(preprocessors[key]):
			value = preprocessors[key](value)

		if not force and key in defaults and key in config and defaults[key] == value:
			del config[key]
			self._dirty = True
		elif force or (not key in config and defaults[key] != value) or (key in config and config[key] != value):
			if value is None:
				del config[key]
			else:
				config[key] = value
			self._dirty = True

	def setInt(self, path, value, force=False, defaults=None, preprocessors=None):
		if value is None:
			self.set(path, None, force=force, defaults=defaults, preprocessors=preprocessors)
			return

		try:
			intValue = int(value)
		except ValueError:
			self._logger.warn("Could not convert %r to a valid integer when setting option %r" % (value, path))
			return

		self.set(path, intValue, force)

	def setFloat(self, path, value, force=False, defaults=None, preprocessors=None):
		if value is None:
			self.set(path, None, force=force, defaults=defaults, preprocessors=preprocessors)
			return

		try:
			floatValue = float(value)
		except ValueError:
			self._logger.warn("Could not convert %r to a valid integer when setting option %r" % (value, path))
			return

		self.set(path, floatValue, force)

	def setBoolean(self, path, value, force=False, defaults=None, preprocessors=None):
		if value is None or isinstance(value, bool):
			self.set(path, value, force=force, defaults=defaults, preprocessors=preprocessors)
		elif value.lower() in valid_boolean_trues:
			self.set(path, True, force=force, defaults=defaults, preprocessors=preprocessors)
		else:
			self.set(path, False, force=force, defaults=defaults, preprocessors=preprocessors)

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
		if not filename.startswith(script_folder):
			# oops, jail break, that shouldn't happen
			raise ValueError("Invalid script path to save to: {filename} (from {script_type}:{name})".format(**locals()))

		path, _ = os.path.split(filename)
		if not os.path.exists(path):
			os.makedirs(path)
		with open(filename, "w+") as f:
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
