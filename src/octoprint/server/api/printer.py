# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

from flask import request, jsonify, make_response, Response
from werkzeug.exceptions import BadRequest
import re

from octoprint.settings import settings, valid_boolean_trues
from octoprint.server import printer, printerProfileManager, NO_CONTENT
from octoprint.server.api import api
from octoprint.server.util.flask import restricted_access, get_json_command_from_request

from octoprint.printer import UnknownScript

#~~ Printer


@api.route("/printer", methods=["GET"])
def printerState():
	if not printer.is_operational():
		return make_response("Printer is not operational", 409)

	# process excludes
	excludes = []
	if "exclude" in request.values:
		excludeStr = request.values["exclude"]
		if len(excludeStr.strip()) > 0:
			excludes = filter(lambda x: x in ["temperature", "sd", "state"], map(lambda x: x.strip(), excludeStr.split(",")))

	result = {}

	processor = lambda x: x
	if not printerProfileManager.get_current_or_default()["heatedBed"]:
		processor = _delete_bed

	# add temperature information
	if not "temperature" in excludes:
		result.update({"temperature": _get_temperature_data(processor)})

	# add sd information
	if not "sd" in excludes and settings().getBoolean(["feature", "sdSupport"]):
		result.update({"sd": {"ready": printer.is_sd_ready()}})

	# add state information
	if not "state" in excludes:
		state = printer.get_current_data()["state"]
		result.update({"state": state})

	return jsonify(result)


#~~ Tool


@api.route("/printer/tool", methods=["POST"])
@restricted_access
def printerToolCommand():
	if not printer.is_operational():
		return make_response("Printer is not operational", 409)

	valid_commands = {
		"select": ["tool"],
		"target": ["targets"],
		"offset": ["offsets"],
		"extrude": ["amount"],
		"flowrate": ["factor"]
	}
	command, data, response = get_json_command_from_request(request, valid_commands)
	if response is not None:
		return response

	validation_regex = re.compile("tool\d+")

	##~~ tool selection
	if command == "select":
		tool = data["tool"]
		if re.match(validation_regex, tool) is None:
			return make_response("Invalid tool: %s" % tool, 400)
		if not tool.startswith("tool"):
			return make_response("Invalid tool for selection: %s" % tool, 400)

		printer.change_tool(tool)

	##~~ temperature
	elif command == "target":
		targets = data["targets"]

		# make sure the targets are valid and the values are numbers
		validated_values = {}
		for tool, value in targets.items():
			if re.match(validation_regex, tool) is None:
				return make_response("Invalid target for setting temperature: %s" % tool, 400)
			if not isinstance(value, (int, long, float)):
				return make_response("Not a number for %s: %r" % (tool, value), 400)
			validated_values[tool] = value

		# perform the actual temperature commands
		for tool in validated_values.keys():
			printer.set_temperature(tool, validated_values[tool])

	##~~ temperature offset
	elif command == "offset":
		offsets = data["offsets"]

		# make sure the targets are valid, the values are numbers and in the range [-50, 50]
		validated_values = {}
		for tool, value in offsets.items():
			if re.match(validation_regex, tool) is None:
				return make_response("Invalid target for setting temperature: %s" % tool, 400)
			if not isinstance(value, (int, long, float)):
				return make_response("Not a number for %s: %r" % (tool, value), 400)
			if not -50 <= value <= 50:
				return make_response("Offset %s not in range [-50, 50]: %f" % (tool, value), 400)
			validated_values[tool] = value

		# set the offsets
		printer.set_temperature_offset(validated_values)

	##~~ extrusion
	elif command == "extrude":
		if printer.is_printing():
			# do not extrude when a print job is running
			return make_response("Printer is currently printing", 409)

		amount = data["amount"]
		if not isinstance(amount, (int, long, float)):
			return make_response("Not a number for extrusion amount: %r" % amount, 400)
		printer.extrude(amount)

	elif command == "flowrate":
		factor = data["factor"]
		if not isinstance(factor, (int, long, float)):
			return make_response("Not a number for flow rate: %r" % factor, 400)
		try:
			printer.flow_rate(factor)
		except ValueError as e:
			return make_response("Invalid value for flow rate: %s" % str(e), 400)

	return NO_CONTENT


@api.route("/printer/tool", methods=["GET"])
def printerToolState():
	if not printer.is_operational():
		return make_response("Printer is not operational", 409)

	return jsonify(_get_temperature_data(_delete_bed))


##~~ Heated bed


@api.route("/printer/bed", methods=["POST"])
@restricted_access
def printerBedCommand():
	if not printer.is_operational():
		return make_response("Printer is not operational", 409)

	if not printerProfileManager.get_current_or_default()["heatedBed"]:
		return make_response("Printer does not have a heated bed", 409)

	valid_commands = {
		"target": ["target"],
		"offset": ["offset"]
	}
	command, data, response = get_json_command_from_request(request, valid_commands)
	if response is not None:
		return response

	##~~ temperature
	if command == "target":
		target = data["target"]

		# make sure the target is a number
		if not isinstance(target, (int, long, float)):
			return make_response("Not a number: %r" % target, 400)

		# perform the actual temperature command
		printer.set_temperature("bed", target)

	##~~ temperature offset
	elif command == "offset":
		offset = data["offset"]

		# make sure the offset is valid
		if not isinstance(offset, (int, long, float)):
			return make_response("Not a number: %r" % offset, 400)
		if not -50 <= offset <= 50:
			return make_response("Offset not in range [-50, 50]: %f" % offset, 400)

		# set the offsets
		printer.set_temperature_offset({"bed": offset})

	return NO_CONTENT


@api.route("/printer/bed", methods=["GET"])
def printerBedState():
	if not printer.is_operational():
		return make_response("Printer is not operational", 409)

	if not printerProfileManager.get_current_or_default()["heatedBed"]:
		return make_response("Printer does not have a heated bed", 409)

	data = _get_temperature_data(_delete_tools)
	if isinstance(data, Response):
		return data
	else:
		return jsonify(data)


##~~ Print head


@api.route("/printer/printhead", methods=["POST"])
@restricted_access
def printerPrintheadCommand():
	valid_commands = {
		"jog": [],
		"home": ["axes"],
		"feedrate": ["factor"]
	}
	command, data, response = get_json_command_from_request(request, valid_commands)
	if response is not None:
		return response

	if not printer.is_operational() or (printer.is_printing() and command != "feedrate"):
		# do not jog when a print job is running or we don't have a connection
		return make_response("Printer is not operational or currently printing", 409)

	valid_axes = ["x", "y", "z"]
	##~~ jog command
	if command == "jog":
		# validate all jog instructions, make sure that the values are numbers
		validated_values = {}
		for axis in valid_axes:
			if axis in data:
				value = data[axis]
				if not isinstance(value, (int, long, float)):
					return make_response("Not a number for axis %s: %r" % (axis, value), 400)
				validated_values[axis] = value

		absolute = "absolute" in data and data["absolute"] in valid_boolean_trues
		speed = data.get("speed", None)

		# execute the jog commands
		printer.jog(validated_values, relative=not absolute, speed=speed)

	##~~ home command
	elif command == "home":
		validated_values = []
		axes = data["axes"]
		for axis in axes:
			if not axis in valid_axes:
				return make_response("Invalid axis: %s" % axis, 400)
			validated_values.append(axis)

		# execute the home command
		printer.home(validated_values)

	elif command == "feedrate":
		factor = data["factor"]
		if not isinstance(factor, (int, long, float)):
			return make_response("Not a number for feed rate: %r" % factor, 400)
		try:
			printer.feed_rate(factor)
		except ValueError as e:
			return make_response("Invalid value for feed rate: %s" % str(e), 400)

	return NO_CONTENT


##~~ SD Card


@api.route("/printer/sd", methods=["POST"])
@restricted_access
def printerSdCommand():
	if not settings().getBoolean(["feature", "sdSupport"]):
		return make_response("SD support is disabled", 404)

	if not printer.is_operational() or printer.is_printing() or printer.is_paused():
		return make_response("Printer is not operational or currently busy", 409)

	valid_commands = {
		"init": [],
		"refresh": [],
		"release": []
	}
	command, data, response = get_json_command_from_request(request, valid_commands)
	if response is not None:
		return response

	if command == "init":
		printer.init_sd_card()
	elif command == "refresh":
		printer.refresh_sd_files()
	elif command == "release":
		printer.release_sd_card()

	return NO_CONTENT


@api.route("/printer/sd", methods=["GET"])
def printerSdState():
	if not settings().getBoolean(["feature", "sdSupport"]):
		return make_response("SD support is disabled", 404)

	return jsonify(ready=printer.is_sd_ready())


##~~ Commands


@api.route("/printer/command", methods=["POST"])
@restricted_access
def printerCommand():
	if not printer.is_operational():
		return make_response("Printer is not operational", 409)

	if not "application/json" in request.headers["Content-Type"]:
		return make_response("Expected content type JSON", 400)

	try:
		data = request.json
	except BadRequest:
		return make_response("Malformed JSON body in request", 400)

	if "command" in data and "commands" in data:
		return make_response("'command' and 'commands' are mutually exclusive", 400)
	elif ("command" in data or "commands" in data) and "script" in data:
		return make_response("'command'/'commands' and 'script' are mutually exclusive", 400)
	elif not ("command" in data or "commands" in data or "script" in data):
		return make_response("Need one of 'command', 'commands' or 'script'", 400)

	parameters = dict()
	if "parameters" in data:
		parameters = data["parameters"]

	if "command" in data or "commands" in data:
		if "command" in data:
			commands = [data["command"]]
		else:
			if not isinstance(data["commands"], (list, tuple)):
				return make_response("'commands' needs to be a list", 400)
			commands = data["commands"]

		commandsToSend = []
		for command in commands:
			commandToSend = command
			if len(parameters) > 0:
				commandToSend = command % parameters
			commandsToSend.append(commandToSend)

		printer.commands(commandsToSend)

	elif "script" in data:
		script_name = data["script"]
		context = dict(parameters=parameters)
		if "context" in data:
			context["context"] = data["context"]

		try:
			printer.script(script_name, context=context)
		except UnknownScript:
			return make_response("Unknown script: {script_name}".format(**locals()), 404)

	return NO_CONTENT

@api.route("/printer/command/custom", methods=["GET"])
def getCustomControls():
	# TODO: document me
	customControls = settings().get(["controls"])
	return jsonify(controls=customControls)


def _get_temperature_data(preprocessor):
	if not printer.is_operational():
		return make_response("Printer is not operational", 409)

	tempData = printer.get_current_temperatures()

	if "history" in request.values.keys() and request.values["history"] in valid_boolean_trues:
		tempHistory = printer.get_temperature_history()

		limit = 300
		if "limit" in request.values.keys() and unicode(request.values["limit"]).isnumeric():
			limit = int(request.values["limit"])

		history = list(tempHistory)
		limit = min(limit, len(history))

		tempData.update({
			"history": map(lambda x: preprocessor(x), history[-limit:])
		})

	return preprocessor(tempData)


def _delete_tools(x):
	return _delete_from_data(x, lambda k: k.startswith("tool"))


def _delete_bed(x):
	return _delete_from_data(x, lambda k: k == "bed")


def _delete_from_data(x, key_matcher):
	data = dict(x)
	for k in data.keys():
		if key_matcher(k):
			del data[k]
	return data
