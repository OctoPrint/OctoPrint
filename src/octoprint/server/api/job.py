# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

from flask import request, make_response, jsonify

from octoprint.server import printer, NO_CONTENT
from octoprint.server.util.flask import restricted_access, get_json_command_from_request
from octoprint.server.api import api
import octoprint.util as util


@api.route("/job", methods=["POST"])
@restricted_access
def controlJob():
	if not printer.is_operational():
		return make_response("Printer is not operational", 409)

	valid_commands = {
		"start": [],
		"restart": [],
		"pause": [],
		"cancel": []
	}

	command, data, response = get_json_command_from_request(request, valid_commands)
	if response is not None:
		return response

	activePrintjob = printer.is_printing() or printer.is_paused()

	if command == "start":
		if activePrintjob:
			return make_response("Printer already has an active print job, did you mean 'restart'?", 409)
		printer.start_print()
	elif command == "restart":
		if not printer.is_paused():
			return make_response("Printer does not have an active print job or is not paused", 409)
		printer.start_print()
	elif command == "pause":
		if not activePrintjob:
			return make_response("Printer is neither printing nor paused, 'pause' command cannot be performed", 409)
		action = data.get("action", "toggle")
		if action == "toggle":
			printer.toggle_pause_print()
		elif action == "pause":
			printer.pause_print()
		elif action == "resume":
			printer.resume_print()
		else:
			return make_response("Unknown action '{}', allowed values for action parameter are 'pause', 'resume' and 'toggle'".format(action), 400)
	elif command == "cancel":
		if not activePrintjob:
			return make_response("Printer is neither printing nor paused, 'cancel' command cannot be performed", 409)
		printer.cancel_print()
	return NO_CONTENT


@api.route("/job", methods=["GET"])
def jobState():
	currentData = printer.get_current_data()
	return jsonify({
		"job": currentData["job"],
		"progress": currentData["progress"],
		"state": currentData["state"]["text"]
	})
