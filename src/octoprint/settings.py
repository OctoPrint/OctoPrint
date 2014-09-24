# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

import sys
import os
import copy
import yaml
import logging
import re
import uuid

from octoprint.collectionUtils import dict_merge, eachDeep

APPNAME = "OctoPrint"
instance = None
valid_boolean_trues = [True, "true", "yes", "y"]
valid_boolean_falses = [False, "false", "no", "n"]

# converts stringified primatives to their primitives, or returns the
# value unchanged
def coercePrimative(value):
	if value is None or value == "null":
		return None
	if value in valid_boolean_trues:
		return True
	if value in valid_boolean_falses:
		return False
	try:
		intVal = int(value)
		floatVal = float(value)
		if (intVal - floatVal == 0):
			return intVal
		return floatVal
	except:
		pass
	return value

def settings(init=False, configfile=None, basedir=None):
	global instance
	if instance is None:
		if init:
			instance = Settings(configfile, basedir)
		else:
			raise ValueError("Settings not initialized yet")
	return instance

default_settings_client_public = {
	"appearance": {
		"color": "default",
		"name": ""
	},
	"api": {
		"enabled": False,
		"key": ''.join('%02X' % ord(z) for z in uuid.uuid4().bytes)
	},
	"cura": {
		"config": "/default/path/to/your/cura/config.ini",
		"enabled": False,
		"path": "/default/path/to/cura"
	},
	"feature": {
		"alwaysSendChecksum": False,
		"repetierTargetTemp": False,
		"sdAlwaysAvailable": False,
		"sdSupport": True,
		"swallowOkAfterResend": True,
		"temperatureGraph": True,
		"waitForStartOnConnect": False
	},
	"folder": {
		"logs": None,
		"timelapse": None,
		"timelapse_tmp": None,
		"uploads": None,
		"virtualSd": None
	},
	"gcodeViewer": {
		"enabled": True,
		"mobileSizeThreshold": 2 * 1024 * 1024, # 2MB
		"sizeThreshold": 20 * 1024 * 1024, # 20MB
	},
	"notifications": {
		"email": {
			"enabled": False,
			"sendgridId": None,
			"sendgridKey": None
		},
		"enabled": False,
		"textMessage": {
			"countryPrefix": None,
			"enabled": False,
			"toNumber": None,
			"fromNumber": None,
			"twilioAcctId": None,
			"twilioAcctKey": None
		},
		"cloud": {
			"enabled": False,
			"orchestrateId": None,
			"orchestrateKey": None
		}
	},
	"printerParameters": {
		"bedDimensions": {
			"x": 200.0, "y": 200.0
		},
		"extruderOffsets": [
			{"x": 0.0, "y": 0.0}
		],
		"invertAxes": [],
		"pauseTriggers": [],
		"movementSpeed": {
			"x": 6000,
			"y": 6000,
			"z": 200,
			"e": 300
		},
		"numExtruders": 1
	},
	"serial": {
		"additionalPorts": [], # TODO appears unused.  Ref'd in comm.py Scrap?
		"autoconnect": False,
		"baudrate": None,
		"log": False,
		"port": None,
		"timeout": {
			"communication": 5,
			"connection": 2,
			"detection": 0.5,
			"sdStatus": 1,
			"temperature": 5
		}
	},
	"system": {
		"actions": []
	},
	"temperature": {
		"profiles":
			[
				{"name": "ABS", "extruder": 210, "bed": 100 },
				{"name": "PLA", "extruder": 180, "bed": 60 }
			]
	},
	"terminalFilters": [
		{ "name": "Suppress M27 requests/responses", "regex": "(Send: M27)|(Recv: SD printing byte)" },
		{ "name": "Suppress M105 requests/responses", "regex": "(Send: M105)|(Recv: ok T\d*:)" }
	],
	"webcam": {
		"bitrate": "5000k",
		"ffmpeg": None,
		"flipH": False,
		"flipV": False,
		"snapshot": None,
		"stream": None,
		"timelapse": {
			"options": {},
			"postRoll": 0,
			"type": "off"
		},
		"watermark": True
	}
}

default_settings_client_private = {
	"accessControl": {
		"autologinLocal": False,
		"autXologinAs": None,
		"enabled": True,
		"localNetworks": ["127.0.0.0/8"],
		"userfile": None,
		"userManager": "octoprint.users.FilebasedUserManager"
	},
	"controls": [],
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
			"repetierStyleTargetTemperature": False
		}
	},
	"events": {
		"enabled": False,
		"subscriptions": []
	},
	"server": {
		"baseUrl": "",
		"firstRun": True,
		"host": "0.0.0.0",
		"port": 5000,
		"scheme": ""
	}
}

default_settings = dict_merge(default_settings_client_public, default_settings_client_private)

class Settings(object):

	def __init__(self, configfile=None, basedir=None):
		self._logger = logging.getLogger(__name__)

		self.settings_dir = None

		self._config = None
		self._dirty = False

		self._init_settings_dir(basedir)

		if configfile is not None:
			self._configfile = configfile
		else:
			self._configfile = os.path.join(self.settings_dir, "config.yaml")
		self.load(migrate=True)
		self.setUserDirs()

	def _init_settings_dir(self, basedir):
		if basedir is not None:
			self.settings_dir = basedir
		else:
			self.settings_dir = _resolveSettingsDir(APPNAME)

	def setUserDirs(self):
		userFolders = self.get(["folder"], True).items()
		for dirName, path in userFolders:
			self.setBaseFolder(dirName, path)

	def _getDefaultFolder(self, type):
		folder = default_settings["folder"][type]
		if folder is None:
			folder = os.path.join(self.settings_dir, type.replace("_", os.path.sep))
		return folder

	# getter/setter for settings I/O between server & client
	def clientSettings(self, data=None):
		if data is None:
			return self._getClientSettings()
		return self._setClientSettings(data)

	def _getClientSettings(self):
		# recurse over settings, generating new nested dict of kv pairs
		self._clientSettingsPayload = {}
		getClientConfig = {
			"on": self._setPropForClient
		}
		eachDeep(default_settings_client_public, getClientConfig)

		# manually append 1-way serial settings
		from octoprint.printer import getConnectionOptions
		connectionOps = getConnectionOptions()
		self._clientSettingsPayload["serial"]["ports"] = connectionOps["ports"]
		self._clientSettingsPayload["serial"]["baudrates"] = connectionOps["baudrates"]
		return self._clientSettingsPayload

	def _setClientSettings(self, data):
		setClientConfig = {
			"on": self._setPropFromClient
		}
		eachDeep(data, setClientConfig)
		return self._getClientSettings()

	# appends nested values to client payload as self.clientSettings() summoned iterator
	# fetches all client settings values
	def _setPropForClient(self, value, config):
		refObj = self._clientSettingsPayload # init to payload root then traverse
		finalKey = config["_path"][len(config["_path"]) - 1]
		for pathSeg in config["_path"]:
			if (pathSeg in refObj.keys() and not pathSeg == finalKey):
				refObj = refObj[pathSeg]
			elif not pathSeg == finalKey:
				refObj[pathSeg] = {}
				refObj = refObj[pathSeg]
		refObj[finalKey] = self.get(config["_path"])

	def _setPropFromClient(self, value, config):
		self.set(config["_path"], value)

	#~~ load and save

	def load(self, migrate=False):
		if os.path.exists(self._configfile) and os.path.isfile(self._configfile):
			with open(self._configfile, "r") as f:
				self._config = yaml.safe_load(f)
		# chamged from else to handle cases where the file exists, but is empty / 0 bytes
		if not self._config:
			self._config = {}

		if migrate:
			self._migrateConfig()

	def _migrateConfig(self):
		if not self._config:
			return

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
			self.save(force=True)
			self._logger.info("Migrated %d event subscriptions to new format and structure" % len(newEvents["subscriptions"]))

	def save(self, force=False):
		if not self._dirty and not force:
			return

		with open(self._configfile, "wb") as configFile:
			yaml.safe_dump(self._config, configFile, default_flow_style=False, indent="    ", allow_unicode=True)
			self._dirty = False
		self.load()

	#~~ getter

	def get(self, pathRef, asdict=False):
		path = copy.deepcopy(pathRef)
		if len(path) == 0:
			return None
		config = self._config
		defaults = default_settings

		# Find requested value in user config and defaults
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

		# Wrap results in collection
		if asdict:
			results = {}
		else:
			results = []
		for key in keys:
			if key in config.keys():
				value = config[key]
			elif key in defaults:
				value = defaults[key]
			else:
				value = None
			value = coercePrimative(value)
			if asdict:
				results[key] = value
			else:
				results.append(value)

		# Return in requested format
		if not isinstance(k, (list, tuple)):
			if asdict:
				return copy.deepcopy(results.values().pop())
			else:
				return results.pop()
		else:
			return copy.deepcopy(results)

	def getInt(self, path):
		return self.get(path)

	def getFloat(self, path):
		return self.get(path)

	def getBoolean(self, path):
		return self.get(path)

	# Returns the path of the folder of the specified type/name, first
	# from user settings, then falling back on app defaults. Creates
	# the folder if not present
	def getBaseFolder(self, type):
		if type not in default_settings["folder"].keys():
			return None

		folderPath = self.get(["folder", type])
		if folderPath is None:
			folderPath = self._getDefaultFolder(type)

		if not os.path.isdir(folderPath):
			try:
				os.makedirs(folderPath)
			except Exception, e:
				self._logger.warn("Could not create directory: %s" % e)

		return folderPath

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

	def set(self, pathRef, value, force=False):
		path = copy.deepcopy(pathRef)
		if len(path) == 0:
			return

		value = coercePrimative(value)

		config = self._config
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
		# Test if value is now default and has also been previously configured
		if not force and key in defaults.keys() and defaults[key] == value and key in config.keys():
			del config[key]
			self._dirty = True
		# Test if value was previously unconfigured and is now different than default, or if value was simply updated
		elif force or (not key in config.keys() and defaults[key] != value) or (key in config.keys() and config[key] != value):
			if value is None:
				del config[key]
			else:
				config[key] = value
			self._dirty = True
		else:
			# purge unused dictionary extensions from self._config
			for x in xrange(1, 2):
				config = self._config
				for p in pathRef:
					if p in config.keys():
						if not config[p]:
							del config[p]
							break
						else:
							config = config[p]
					else:
						break

	def setInt(self, path, value, force=False):
		self.set(path, value, force)

	def setFloat(self, path, value, force=False):
		self.set(path, value, force)

	def setBoolean(self, path, value, force=False):
			self.set(path, value, force)

	def setBaseFolder(self, type, path, force=False):
		if type not in default_settings["folder"].keys():
			return None

		currentPath = self.getBaseFolder(type)
		defaultPath = self._getDefaultFolder(type)
		# Remove frivolous config entry if it is the default value
		if (path is None or path == defaultPath) and "folder" in self._config.keys() and type in self._config["folder"].keys():
			del self._config["folder"][type]
			if not self._config["folder"]:
				del self._config["folder"]
			self._dirty = True
		# Else update config with newly created dir
		elif (path != currentPath and path != defaultPath and not path is None) or force:
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
