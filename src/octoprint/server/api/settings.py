# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

import logging

from flask import request, jsonify

from octoprint.settings import settings

from octoprint.server import restricted_access, admin_permission
from octoprint.server.api import api

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
	return jsonify(settings().clientSettings())


@api.route("/settings", methods=["POST"])
@restricted_access
@admin_permission.require(403)
def setSettings():
	if "application/json" in request.headers["Content-Type"]:
		data = request.json
		s = settings()
		setLog(data) # call before bulk setting op to compare old vs new
		clientSettings = s.clientSettings(data)
		setCura(data)
		s.setUserDirs()
		s.save()
	return getSettings()
