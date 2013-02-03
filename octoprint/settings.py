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
	},
}

default_settings = old_default_settings.copy()
default_settings.update({
	"controls": []
})

class Settings(object):

	def __init__(self):
		self.settings_dir = None

		self._config = None
		self._dirty = False

		self.init_settings_dir()
		self.load()

	def init_settings_dir(self):
		self.settings_dir = _resolveSettingsDir(APPNAME)

		# migration due to rename
		old_settings_dir = _resolveSettingsDir(OLD_APPNAME)
		if os.path.exists(old_settings_dir) and os.path.isdir(old_settings_dir) and not os.path.exists(self.settings_dir):
			os.rename(old_settings_dir, self.settings_dir)

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

	def getObject(self, key):
		if key not in default_settings.keys():
			return None

		if key in self._config.keys():
			return self._config[key]

		return default_settings[key]

	def get(self, section, key):
		if section not in default_settings.keys():
			return None

		if self._config.has_key(section) and self._config[section].has_key(key):
			return self._config[section][key]

		if default_settings.has_key(section) and default_settings[section].has_key(key):
			return default_settings[section][key]

		return None

	def getInt(self, section, key):
		value = self.get(section, key)
		if value is None:
			return None

		try:
			return int(value)
		except ValueError:
			return None

	def getBoolean(self, section, key):
		value = self.get(section, key)
		if value is None:
			return None
		if isinstance(value, bool):
			return value
		return value.lower() in ["true", "yes", "y", "1"]

	def getBaseFolder(self, type):
		if type not in old_default_settings["folder"].keys():
			return None

		folder = self.get("folder", type)
		if folder is None:
			folder = os.path.join(self.settings_dir, type.replace("_", os.path.sep))

		if not os.path.isdir(folder):
			os.makedirs(folder)

		return folder

	def set(self, section, key, value):
		if section not in default_settings.keys():
			return

		if self._config.has_key(section):
			sectionConfig = self._config[section]
		else:
			sectionConfig = {}

		sectionConfig[key] = value
		self._config[section] = sectionConfig
		self._dirty = True

	def setObject(self, key, value):
		if key not in default_settings.keys():
			return

		self._config[key] = value
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