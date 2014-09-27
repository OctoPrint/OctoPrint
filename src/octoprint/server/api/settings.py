# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging

from flask import request, jsonify

from octoprint.settings import settings

from octoprint.server import admin_permission
from octoprint.server.api import api
from octoprint.server.util.flask import restricted_access

import octoprint.plugin

# Setting helpers
def setCura(data):
	s = settings()
	cura = data.get("cura", None)
	if cura:
		path = cura.get("path")
		if path:
			s.set(["cura", "path"], path)

		config = cura.get("config")
		if config:
			s.set(["cura", "config"], config)

		# Enabled is a boolean so we cannot check that we have a result
		enabled = cura.get("enabled")
		s.setBoolean(["cura", "enabled"], enabled)

def setLog(data):
	s = settings()
	oldLog = s.get(["serial", "log"])
	if "log" in data["serial"].keys():
		s.set(["serial", "log"], data["serial"]["log"])
	if oldLog and not s.get(["serial", "log"]):
		# disable debug logging to serial.log
		logging.getLogger("SERIAL").debug("Disabling serial logging")
		logging.getLogger("SERIAL").setLevel(logging.CRITICAL)
	elif not oldLog and s.get(["serial", "log"]):
		# enable debug logging to serial.log
		logging.getLogger("SERIAL").setLevel(logging.DEBUG)
		logging.getLogger("SERIAL").debug("Enabling serial logging")

@api.route("/settings", methods=["GET"])
def getSettings():
	data = settings().clientSettings()

	def process_plugin_result(name, plugin, result):
		if result:
			if not "plugins" in data:
				data["plugins"] = dict()
			if "__enabled" in result:
				del result["__enabled"]
			data["plugins"][name] = result

	octoprint.plugin.call_plugin(octoprint.plugin.SettingsPlugin, "on_settings_load", callback=process_plugin_result)
	return jsonify(data)

@api.route("/settings", methods=["POST"])
@restricted_access
@admin_permission.require(403)
def setSettings():
	if "application/json" in request.headers["Content-Type"]:
		data = request.json
		s = settings()
		setLog(data) # call before bulk setting op to compare old vs new
		s.clientSettings(data)
		setCura(data)
		s.setUserDirs()
		if "plugins" in data:
			for name, plugin in octoprint.plugin.plugin_manager().get_implementations(octoprint.plugin.SettingsPlugin).items():
				if name in data["plugins"]:
					plugin.on_settings_save(data["plugins"][name])
		s.save()
	return getSettings()
