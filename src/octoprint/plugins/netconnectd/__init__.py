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


class NetconnectdSettingsPlugin(octoprint.plugin.SettingsPlugin,
                                octoprint.plugin.TemplatePlugin,
                                octoprint.plugin.SimpleApiPlugin,
                                octoprint.plugin.AssetPlugin):

	def __init__(self):
		self.logger = logging.getLogger("plugins.netconnectd." + __name__)
		self.address = s.get(["socket"])

	##~~ SettingsPlugin

	def on_settings_load(self):
		return {
			"socket": s.get(["socket"])
		}

	def on_settings_save(self, data):
		if "socket" in data and data["socket"]:
			s.set(["socket"], data["socket"])

		self.address = s.get(["socket"])

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

			self._configure_and_select_wifi(data["ssid"], data["psk"], force=data["force"] if "force" in data else False)

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
		payload = dict()
		if force:
			self.logger.info("Forcing wifi refresh...")
			payload["force"] = True

		flag, content = self._send_message("list_wifi", payload)
		if not flag:
			raise RuntimeError("Error while listing wifi: " + content)

		result = []
		for wifi in content:
			result.append(dict(ssid=wifi["ssid"], address=wifi["address"], quality=wifi["signal"], encrypted=wifi["encrypted"]))
		return result

	def _get_status(self):
		payload = dict()

		flag, content = self._send_message("status", payload)
		if not flag:
			raise RuntimeError("Error while querying status: " + content)

		return content

	def _configure_and_select_wifi(self, ssid, psk, force=False):
		payload = dict(
			ssid=ssid,
			psk=psk,
			force=force
		)

		flag, content = self._send_message("config_wifi", payload)
		if not flag:
			raise RuntimeError("Error while configuring wifi: " + content)

		flag, content = self._send_message("start_wifi", dict())
		if not flag:
			raise RuntimeError("Error while selecting wifi: " + content)

	def _send_message(self, message, data):
		obj = dict()
		obj[message] = data

		import json
		js = json.dumps(obj, encoding="utf8", separators=(",", ":"))

		import socket
		sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		try:
			sock.connect(self.address)
			sock.sendall(js + '\x00')

			buffer = []
			while True:
				chunk = sock.recv(16)
				if chunk:
					buffer.append(chunk)
					if chunk.endswith('\x00'):
						break

			data = ''.join(buffer).strip()[:-1]

			response = json.loads(data.strip())
			if "result" in response:
				return True, response["result"]

			elif "error" in response:
				# something went wrong
				self.logger.warn("Request to netconnectd went wrong: " + response["error"])
				return False, response["error"]

			else:
				output = "Unknown response from netconnectd: {response!r}".format(response=response)
				self.logger.warn(output)
				return False, output

		except Exception as e:
			output = "Error while talking to netconnectd: {}".format(e.message)
			self.logger.warn(output)
			return False, output

		finally:
			sock.close()

__plugin_name__ = "netconnectd client"
__plugin_version__ = "0.1"
__plugin_description__ = "Client for netconnectd that allows configuration of netconnectd through OctoPrint's settings dialog"
__plugin_implementations__ = []

def __plugin_check__():
	import sys
	if not sys.platform == 'linux2':
		return False

	global __plugin_implementations__
	__plugin_implementations__ = [NetconnectdSettingsPlugin()]
	return True



