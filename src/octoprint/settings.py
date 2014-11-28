# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

import sys
import os
import yaml
import logging
import re
import uuid

APPNAME="OctoPrint"

instance = None

def settings(init=False, configfile=None, basedir=None):
	global instance
	if instance is None:
		if init:
			instance = Settings(configfile, basedir)
		else:
			raise ValueError("Settings not initialized yet")
	return instance

default_settings = {
	"serial": {
		"port": None,
		"baudrate": None,
		"autoconnect": False,
		"log": False,
		"timeout": {
			"detection": 0.5,
			"connection": 2,
			"communication": 5,
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
			"prefixFallback": "",
			"schemeFallback": ""
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
		"bitrate": "5000k",
		"watermark": True,
		"flipH": False,
		"flipV": False,
		"timelapse": {
			"type": "off",
			"options": {},
			"postRoll": 0
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
		"sdSupport": True,
		"sdAlwaysAvailable": False,
		"swallowOkAfterResend": True,
		"repetierTargetTemp": False
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
		"printerProfiles": None
	},
	"temperature": {
		"profiles": [
			{"name": "ABS", "extruder" : 210, "bed" : 100 },
			{"name": "PLA", "extruder" : 180, "bed" : 60 }
		]
	},
	"printerProfiles": {
		"default": None,
		"defaultProfile": {}
	},
	"printerParameters": {
		"movementSpeed": {
			"x": 6000,
			"y": 6000,
			"z": 200,
			"e": 300
		},
		"pauseTriggers": [],
		"invertAxes": [],
		"numExtruders": 1,
		"extruderOffsets": [
			{"x": 0.0, "y": 0.0}
		],
		"bedDimensions": {
			"x": 200.0, "y": 200.0, "r": 100, "circular": False
		},
		"defaultExtrusionLength": 5
	},
	"appearance": {
		"name": "",
		"color": "default"
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
	"cura": {
		"enabled": False,
		"path": "/default/path/to/cura",
		"config": "/default/path/to/your/cura/config.ini"
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
		{ "name": "Suppress M105 requests/responses", "regex": "(Send: M105)|(Recv: ok T\d*:)" },
		{ "name": "Suppress M27 requests/responses", "regex": "(Send: M27)|(Recv: SD printing byte)" }
	],
	"plugins": {},
	"devel": {
		"stylesheet": "css",
		"virtualPrinter": {
			"enabled": False,
			"okAfterResend": False,
			"forceChecksum": False,
			"okWithLinenumber": False,
			"numExtruders": 1,
			"includeCurrentToolInTemps": True,
			"hasBed": True,
			"repetierStyleTargetTemperature": False,
			"smoothieTemperatureReporting": False,
			"extendedSdFileList": False
		}
	}
}

valid_boolean_trues = [True, "true", "yes", "y", "1"]

class Settings(object):

	def __init__(self, configfile=None, basedir=None):
		self._logger = logging.getLogger(__name__)

		self.settings_dir = None

		self._config = None
		self._dirty = False
		self._mtime = None

		self._init_settings_dir(basedir)

		if configfile is not None:
			self._configfile = configfile
		else:
			self._configfile = os.path.join(self.settings_dir, "config.yaml")
		self.load(migrate=True)

		if self.get(["api", "key"]) is None:
			self.set(["api", "key"], ''.join('%02X' % ord(z) for z in uuid.uuid4().bytes))
			self.save(force=True)

	def _init_settings_dir(self, basedir):
		if basedir is not None:
			self.settings_dir = basedir
		else:
			self.settings_dir = _resolveSettingsDir(APPNAME)

		if not os.path.isdir(self.settings_dir):
			os.makedirs(self.settings_dir)

	def _getDefaultFolder(self, type):
		folder = default_settings["folder"][type]
		if folder is None:
			folder = os.path.join(self.settings_dir, type.replace("_", os.path.sep))
		return folder

	#~~ load and save

	def load(self, migrate=False):
		if os.path.exists(self._configfile) and os.path.isfile(self._configfile):
			with open(self._configfile, "r") as f:
				self._config = yaml.safe_load(f)
				self._mtime = self._last_modified()
		# changed from else to handle cases where the file exists, but is empty / 0 bytes
		if not self._config:
			self._config = {}

		if migrate:
			self._migrateConfig()

	def _migrateConfig(self):
		dirty = False
		for migrate in (self._migrate_event_config, self._migrate_reverse_proxy_config):
			dirty = migrate() or dirty
		if dirty:
			self.save(force=True)

	def _migrate_reverse_proxy_config(self):
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

	def _last_modified(self):
		stat = os.stat(self._configfile)
		return stat.st_mtime

	#~~ getter

	def get(self, path, asdict=False, defaults=None, merged=False):
		import octoprint.util as util

		if len(path) == 0:
			return None

		config = self._config
		if defaults is None:
			defaults = default_settings

		while len(path) > 1:
			key = path.pop(0)
			if key in config.keys() and key in defaults.keys():
				config = config[key]
				defaults = defaults[key]
			elif key in defaults.keys():
				config = {}
				defaults = defaults[key]
			else:
				return None

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
			if key in config.keys():
				value = config[key]
				if merged and key in defaults:
					value = util.dict_merge(defaults[key], value)
			elif key in defaults:
				value = defaults[key]
			else:
				value = None

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

	def getInt(self, path, defaults=None):
		value = self.get(path, defaults=defaults)
		if value is None:
			return None

		try:
			return int(value)
		except ValueError:
			self._logger.warn("Could not convert %r to a valid integer when getting option %r" % (value, path))
			return None

	def getFloat(self, path, defaults=None):
		value = self.get(path, defaults=defaults)
		if value is None:
			return None

		try:
			return float(value)
		except ValueError:
			self._logger.warn("Could not convert %r to a valid integer when getting option %r" % (value, path))
			return None

	def getBoolean(self, path, defaults=None):
		value = self.get(path, defaults=defaults)
		if value is None:
			return None
		if isinstance(value, bool):
			return value
		if isinstance(value, (int, float)):
			return value != 0
		if isinstance(value, (str, unicode)):
			return value.lower() in valid_boolean_trues
		return value is not None

	def getBaseFolder(self, type):
		if type not in default_settings["folder"].keys():
			return None

		folder = self.get(["folder", type])
		if folder is None:
			folder = self._getDefaultFolder(type)

		if not os.path.isdir(folder):
			os.makedirs(folder)

		return folder

	def getFeedbackControls(self):
		feedbackControls = []
		for control in self.get(["controls"]):
			feedbackControls.extend(self._getFeedbackControls(control))
		return feedbackControls

	def _getFeedbackControls(self, control=None):
		if control["type"] == "feedback_command" or control["type"] == "feedback":
			pattern = control["regex"]
			try:
				matcher = re.compile(pattern)
				return [(control["name"], matcher, control["template"])]
			except:
				# invalid regex or something like this, we'll just skip this entry
				pass
		elif control["type"] == "section":
			result = []
			for c in control["children"]:
				result.extend(self._getFeedbackControls(c))
			return result
		else:
			return []

	def getPauseTriggers(self):
		triggers = {
			"enable": [],
			"disable": [],
			"toggle": []
		}
		for trigger in self.get(["printerParameters", "pauseTriggers"]):
			try:
				regex = trigger["regex"]
				type = trigger["type"]
				if type in triggers.keys():
					# make sure regex is valid
					re.compile(regex)
					# add to type list
					triggers[type].append(regex)
			except:
				# invalid regex or something like this, we'll just skip this entry
				pass

		result = {}
		for type in triggers.keys():
			if len(triggers[type]) > 0:
				result[type] = re.compile("|".join(map(lambda x: "(%s)" % x, triggers[type])))
		return result

	#~~ setter

	def set(self, path, value, force=False, defaults=None):
		if len(path) == 0:
			return

		if self._mtime is not None and self._last_modified() != self._mtime:
			self.load()

		config = self._config
		if defaults is None:
			defaults = default_settings

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

		key = path.pop(0)
		if not force and key in defaults.keys() and key in config.keys() and defaults[key] == value:
			del config[key]
			self._dirty = True
		elif force or (not key in config.keys() and defaults[key] != value) or (key in config.keys() and config[key] != value):
			if value is None:
				del config[key]
			else:
				config[key] = value
			self._dirty = True

	def setInt(self, path, value, force=False, defaults=None):
		if value is None:
			self.set(path, None, force=force, defaults=defaults)
			return

		try:
			intValue = int(value)
		except ValueError:
			self._logger.warn("Could not convert %r to a valid integer when setting option %r" % (value, path))
			return

		self.set(path, intValue, force)

	def setFloat(self, path, value, force=False, defaults=None):
		if value is None:
			self.set(path, None, force=force, defaults=defaults)
			return

		try:
			floatValue = float(value)
		except ValueError:
			self._logger.warn("Could not convert %r to a valid integer when setting option %r" % (value, path))
			return

		self.set(path, floatValue, force)

	def setBoolean(self, path, value, force=False, defaults=None):
		if value is None or isinstance(value, bool):
			self.set(path, value, force=force, defaults=defaults)
		elif value.lower() in valid_boolean_trues:
			self.set(path, True, force=force, defaults=defaults)
		else:
			self.set(path, False, force=force, defaults=defaults)

	def setBaseFolder(self, type, path, force=False):
		if type not in default_settings["folder"].keys():
			return None

		currentPath = self.getBaseFolder(type)
		defaultPath = self._getDefaultFolder(type)
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

def _resolveSettingsDir(applicationName):
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
