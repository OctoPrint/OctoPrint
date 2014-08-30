# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

from flask import request, jsonify, make_response

from octoprint.settings import settings
from octoprint.printer import getConnectionOptions
from octoprint.server import printer, NO_CONTENT
from octoprint.server.api import api
from octoprint.server.util.flask import restricted_access
import octoprint.util as util


@api.route("/connection", methods=["GET"])
def connectionState():
	state, port, baudrate = printer.getCurrentConnection()
	current = {
		"state": state,
		"port": port,
		"baudrate": baudrate
	}
	return jsonify({"current": current, "options": getConnectionOptions()})


@api.route("/connection", methods=["POST"])
@restricted_access
def connectionCommand():
	valid_commands = {
		"connect": ["autoconnect"],
		"disconnect": []
	}

	command, data, response = util.getJsonCommandFromRequest(request, valid_commands)
	if response is not None:
		return response

	if command == "connect":
		options = getConnectionOptions()

		port = None
		baudrate = None
		if "port" in data.keys():
			port = data["port"]
			if port not in options["ports"]:
				return make_response("Invalid port: %s" % port, 400)
		if "baudrate" in data.keys():
			baudrate = data["baudrate"]
			if baudrate not in options["baudrates"]:
				return make_response("Invalid baudrate: %d" % baudrate, 400)
		if "save" in data.keys() and data["save"]:
			settings().set(["serial", "port"], port)
			settings().setInt(["serial", "baudrate"], baudrate)
		if "autoconnect" in data.keys():
			settings().setBoolean(["serial", "autoconnect"], data["autoconnect"])
		settings().save()
		printer.connect(port=port, baudrate=baudrate)
	elif command == "disconnect":
		printer.disconnect()

	return NO_CONTENT


