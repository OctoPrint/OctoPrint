# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

import ConfigParser
import sys
import os

APPNAME="PrinterWebUI"

instance = None

def settings():
	global instance
	if instance is None:
		instance = Settings()
	return instance

default_settings = {
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
		"ffmpeg": None
	},
	"folder": {
		"uploads": None,
		"timelapse": None
	}
}

class Settings(object):

	def __init__(self):
		self.settings_dir = None

		self._config = None
		self._changes = None

		self.init_settings_dir()
		self.load()

	def init_settings_dir(self):
		# taken from http://stackoverflow.com/questions/1084697/how-do-i-store-desktop-application-data-in-a-cross-platform-way-for-python
		if sys.platform == "darwin":
			from AppKit import NSSearchPathForDirectoriesInDomains
			# http://developer.apple.com/DOCUMENTATION/Cocoa/Reference/Foundation/Miscellaneous/Foundation_Functions/Reference/reference.html#//apple_ref/c/func/NSSearchPathForDirectoriesInDomains
			# NSApplicationSupportDirectory = 14
			# NSUserDomainMask = 1
			# True for expanding the tilde into a fully qualified path
			self.settings_dir = os.path.join(NSSearchPathForDirectoriesInDomains(14, 1, True)[0], APPNAME)
		elif sys.platform == "win32":
			self.settings_dir = os.path.join(os.environ["APPDATA"], APPNAME)
		else:
			self.settings_dir = os.path.expanduser(os.path.join("~", "." + APPNAME.lower()))

	def load(self):
		self._config = ConfigParser.ConfigParser(allow_no_value=True)
		self._config.read(os.path.join(self.settings_dir, "config.ini"))

	def save(self, force=False):
		if self._changes is None and not force:
			return

		for section in default_settings.keys():
			if self._changes.has_key(section):
				for key in self._changes[section].keys():
					value = self._changes[section][key]
					if not self._config.has_section(section):
						self._config.add_section(section)
					self._config.set(section, key, value)

		with open(os.path.join(self.settings_dir, "config.ini"), "wb") as configFile:
			self._config.write(configFile)
			self._changes = None
		self.load()

	def get(self, section, key):
		if section not in default_settings.keys():
			return None

		value = None
		if self._config.has_option(section, key):
			value = self._config.get(section, key)
		if value is None:
			if default_settings.has_key(section) and default_settings[section].has_key(key):
				return default_settings[section][key]
			else:
				return None
		else:
			return value

	def getInt(self, section, key):
		value = self.get(section, key)
		if value is None:
			return None

		try:
			return int(value)
		except ValueError:
			return None

	def getBaseFolder(self, type):
		if type not in default_settings["folder"].keys():
			return None

		folder = self.get("folder", type)
		if folder is None:
			folder = os.path.join(self.settings_dir, type)

		if not os.path.isdir(folder):
			os.makedirs(folder)

		return folder

	def set(self, section, key, value):
		if section not in default_settings.keys():
			return None

		if self._changes is None:
			self._changes = {}

		if self._changes.has_key(section):
			sectionConfig = self._changes[section]
		else:
			sectionConfig = {}

		sectionConfig[key] = value
		self._changes[section] = sectionConfig

