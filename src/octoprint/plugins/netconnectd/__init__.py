# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import os
import logging
from flask import jsonify

import octoprint.plugin


default_settings = {
	"socket": "/var/run/netconnectd.sock"
}


s = octoprint.plugin.plugin_settings("netconnectd", defaults=default_settings)


class NetconnectdSettingsPlugin(octoprint.plugin.SettingsPlugin, octoprint.plugin.SimpleApiPlugin, octoprint.plugin.AssetPlugin):

	def __init__(self):
		self.logger = logging.getLogger(__name__)

	##~~ SettingsPlugin

	def on_settings_load(self):
		return {
			"socket": s.get(["socket"])
		}

	def on_settings_save(self, data):
		if "socket" in data and data["socket"]:
			s.set(["socket"], data["socket"])

	##~~ TemplatePlugin API (part of SettingsPlugin)

	def get_template_vars(self):
		return dict(
			_settings_menu_entry="Network connection"
		)

	def get_template_folder(self):
		return os.path.join(os.path.dirname(os.path.realpath(__file__)), "templates")

	##~~ SimpleApiPlugin API

	def get_api_commands(self):
		return {
			"start_ap": [],
			"stop_ap": [],
			"refresh_wifi": [],
			"configure_wifi": ["ssid", "psk"],
		}

	def on_api_get(self, request):
		try:
			wifis = self._get_wifi_list()
			status = self._get_status()
		except Exception as e:
			return jsonify(dict(error=e.message))

		return jsonify({
			"wifis": wifis,
			"status": status
		})

	def on_api_command(self, command, data):
		if command == "refresh_wifi":
			return jsonify(self._get_wifi_list(force=True))

		elif command == "configure_wifi":
			if data["psk"]:
				self.logger.info("Configuring wifi {ssid} and psk...".format(**data))
			else:
				self.logger.info("Configuring wifi {ssid}...".format(**data))

		elif command == "start_ap":
			self.logger.info("Starting ap...")

		elif command == "stop_ap":
			self.logger.info("Stopping ap...")

	##~~ AssetPlugin API

	def get_asset_folder(self):
		return os.path.join(os.path.dirname(os.path.realpath(__file__)), "static")

	def get_assets(self):
		return {
			"js": ["js/netconnectd.js"],
			"css": ["css/netconnectd.css"],
			"less": ["less/netconnectd.less"]
		}

	##~~ Private helpers

	def _get_wifi_list(self, force=False):
		if force:
			self.logger.info("Forcing wifi refresh...")
		return [
			{"name": "A Test Wifi", "quality": 59, "encrypted": True},
			{"name": "TyrionDiesOnPage24", "quality": 90, "encrypted": True},
			{"name": "Giraffenhaus", "quality": 78, "encrypted": False},
		]

	def _get_status(self):
		return {
			"ap": False,
			"connectedToWifi": True
		}


__plugin_name__ = "netconnectd client"
__plugin_version__ = "0.1"
__plugin_description__ = "Client for netconnectd that allows configuration of netconnectd through OctoPrint's settings dialog"
__plugin_implementations__ = []

def __plugin_check__():
	import sys
	# TODO arm the check
	#if not sys.platform == 'linux2':
	#	return False

	global __plugin_implementations__
	__plugin_implementations__ = [NetconnectdSettingsPlugin()]
	return True



