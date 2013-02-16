# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

import ConfigParser
import sys
import os
import yaml

APPNAME="OctoPrint"
OLD_APPNAME="PrinterWebUI"

instance = None

def settings():
	global instance
	if instance is None:
		instance = Settings()
	return instance

old_default_settings = {
	"serial": {
		"port": None,
		"baudrate": None
	},
	"server": {
		"host": "0.0.0.0",
		"port": 5000
	},
	"webcam": {
		"stream": None,
		"snapshot": None,
		"ffmpeg": None,
		"bitrate": "5000k"
	},
	"folder": {
		"uploads": None,
		"timelapse": None,
		"timelapse_tmp": None
	},
	"feature": {
    	"gCodeVisualizer": True
	},
}

default_settings = old_default_settings.copy()
default_settings.update({
	"controls": [],
	"printerParameters": {
		"movementSpeed": {
			"x": 6000,
			"y": 6000,
			"z": 200,
			"e": 300
		}
	}
})

valid_boolean_trues = ["true", "yes", "y", "1"]

class Settings(object):

	def __init__(self):
		self.settings_dir = None

		self._config = None
		self._dirty = False

		self._init_settings_dir()
		self.load()

	def _init_settings_dir(self):
		self.settings_dir = _resolveSettingsDir(APPNAME)

		# migration due to rename
		old_settings_dir = _resolveSettingsDir(OLD_APPNAME)
		if os.path.exists(old_settings_dir) and os.path.isdir(old_settings_dir) and not os.path.exists(self.settings_dir):
			os.rename(old_settings_dir, self.settings_dir)

	#~~ load and save

	def load(self):
		filename = os.path.join(self.settings_dir, "config.yaml")
		oldFilename = os.path.join(self.settings_dir, "config.ini")
		if os.path.exists(filename) and os.path.isfile(filename):
			with open(filename, "r") as f:
				self._config = yaml.safe_load(f)
		elif os.path.exists(oldFilename) and os.path.isfile(oldFilename):
			config = ConfigParser.ConfigParser(allow_no_value=True)
			config.read(oldFilename)
			self._config = {}
			for section in old_default_settings.keys():
				if not config.has_section(section):
					continue

				self._config[section] = {}
				for option in old_default_settings[section].keys():
					if not config.has_option(section, option):
						continue

					self._config[section][option] = config.get(section, option)
					self._dirty = True
			self.save(force=True)
			os.rename(oldFilename, oldFilename + ".bck")
		else:
			self._config = {}

	def save(self, force=False):
		if not self._dirty and not force:
			return

		with open(os.path.join(self.settings_dir, "config.yaml"), "wb") as configFile:
			yaml.safe_dump(self._config, configFile, default_flow_style=False, indent="    ", allow_unicode=True)
			self._dirty = False
		self.load()

	#~~ getter

	def get(self, path):
		if len(path) == 0:
			return None

		config = self._config
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

		results = []
		for key in keys:
			if key in config.keys():
				results.append(config[key])
			elif key in defaults:
				results.append(defaults[key])
			else:
				results.append(None)

		if not isinstance(k, (list, tuple)):
			return results.pop()
		else:
			return results

	def getInt(self, path):
		value = self.get(path)
		if value is None:
			return None

		try:
			return int(value)
		except ValueError:
			return None

	def getBoolean(self, path):
		value = self.get(path)
		if value is None:
			return None
		if isinstance(value, bool):
			return value
		return value.lower() in valid_boolean_trues

	def getBaseFolder(self, type):
		if type not in old_default_settings["folder"].keys():
			return None

		folder = self.get(["folder", type])
		if folder is None:
			folder = os.path.join(self.settings_dir, type.replace("_", os.path.sep))

		if not os.path.isdir(folder):
			os.makedirs(folder)

		return folder

	#~~ setter

	def set(self, path, value):
		if len(path) == 0:
			return

		config = self._config
		defaults = default_settings

		while len(path) > 1:
			key = path.pop(0)
			if key in config.keys():
				config = config[key]
			elif key in defaults.keys():
				config[key] = {}
				config = config[key]
			else:
				return

		key = path.pop(0)
		config[key] = value
		self._dirty = True

	def setInt(self, path, value):
		if value is None:
			return

		try:
			intValue = int(value)
		except ValueError:
			return

		self.set(path, intValue)

	def setBoolean(self, path, value):
		if value is None:
			return
		elif isinstance(value, bool):
			self.set(path, value)
		elif value.lower() in valid_boolean_trues:
			self.set(path, True)
		else:
			self.set(path, False)

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