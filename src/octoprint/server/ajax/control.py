# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

from flask import request, jsonify, make_response

from octoprint.settings import settings, valid_boolean_trues
from octoprint.printer import getConnectionOptions
from octoprint.server import printer, restricted_access, SUCCESS
from octoprint.server.ajax import ajax
import octoprint.util as util

#~~ Printer control


@ajax.route("/control/connection", methods=["GET"])
def connectionOptions():
	state, port, baudrate = printer.getCurrentConnection()
	current = {
		"state": state,
		"port": port,
		"baudrate": baudrate
	}
	return jsonify({"current": current, "options": getConnectionOptions()})


@ajax.route("/control/connection", methods=["POST"])
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
		settings().setBoolean(["serial", "autoconnect"], data["autoconnect"])
		settings().save()
		printer.connect(port=port, baudrate=baudrate)
	elif command == "disconnect":
		printer.disconnect()

	return jsonify(SUCCESS)


@ajax.route("/control/printer/command", methods=["POST"])
@restricted_access
def printerCommand():
	if not printer.isOperational():
		return make_response("Printer is not operational", 403)

	if not "application/json" in request.headers["Content-Type"]:
		return make_response("Expected content type JSON", 400)

	data = request.json

	parameters = {}
	if "parameters" in data.keys(): parameters = data["parameters"]

	commands = []
	if "command" in data.keys(): commands = [data["command"]]
	elif "commands" in data.keys(): commands = data["commands"]

	commandsToSend = []
	for command in commands:
		commandToSend = command
		if len(parameters) > 0:
			commandToSend = command % parameters
		commandsToSend.append(commandToSend)

	printer.commands(commandsToSend)

	return jsonify(SUCCESS)


@ajax.route("/control/job", methods=["POST"])
@restricted_access
def controlJob():
	if not printer.isOperational():
		return make_response("Printer is not operational", 403)

	valid_commands = {
		"start": [],
		"pause": [],
		"cancel": []
	}

	command, data, response = util.getJsonCommandFromRequest(request, valid_commands)
	if response is not None:
		return response

	if command == "start":
		printer.startPrint()
	elif command == "pause":
		printer.togglePausePrint()
	elif command == "cancel":
		printer.cancelPrint()
	return jsonify(SUCCESS)


@ajax.route("/control/printer/hotend", methods=["POST"])
@restricted_access
def controlPrinterHotend():
	if not printer.isOperational():
		return make_response("Printer is not operational", 403)

	valid_commands = {
		"temp": ["temps"],
		"offset": ["offsets"]
	}
	command, data, response = util.getJsonCommandFromRequest(request, valid_commands)
	if response is not None:
		return response

	valid_targets = ["hotend", "bed"]

	##~~ temperature
	if command == "temp":
		temps = data["temps"]

		# make sure the targets are valid and the values are numbers
		validated_values = {}
		for type, value in temps.iteritems():
			if not type in valid_targets:
				return make_response("Invalid target for setting temperature: %s" % type, 400)
			if not isinstance(value, (int, long, float)):
				return make_response("Not a number for %s: %r" % (type, value), 400)
			validated_values[type] = value

		# perform the actual temperature commands
		# TODO make this a generic method call (printer.setTemperature(type, value)) to get rid of gcode here
		if "hotend" in validated_values:
			printer.command("M104 S%f" % validated_values["hotend"])
		if "bed" in validated_values:
			printer.command("M140 S%f" % validated_values["bed"])

	##~~ temperature offset
	elif command == "offset":
		offsets = data["offsets"]

		# make sure the targets are valid, the values are numbers and in the range [-50, 50]
		validated_values = {}
		for type, value in offsets.iteritems():
			if not type in valid_targets:
				return make_response("Invalid target for setting temperature: %s" % type, 400)
			if not isinstance(value, (int, long, float)):
				return make_response("Not a number for %s: %r" % (type, value), 400)
			if not -50 <= value <= 50:
				return make_response("Offset %s not in range [-50, 50]: %f" % (type, value), 400)
			validated_values[type] = value

		# set the offsets
		if "hotend" in validated_values and "bed" in validated_values:
			printer.setTemperatureOffset(validated_values["hotend"], validated_values["bed"])
		elif "hotend" in validated_values:
			printer.setTemperatureOffset(validated_values["hotend"], None)
		elif "bed" in validated_values:
			printer.setTemperatureOffset(None, validated_values["bed"])

	return jsonify(SUCCESS)


@ajax.route("/control/printer/printhead", methods=["POST"])
@restricted_access
def controlPrinterPrinthead():
	if not printer.isOperational() or printer.isPrinting():
		# do not jog when a print job is running or we don't have a connection
		return make_response("Printer is not operational or currently printing", 403)

	valid_commands = {
		"jog": [],
		"home": ["axes"]
	}
	command, data, response = util.getJsonCommandFromRequest(request, valid_commands)
	if response is not None:
		return response

	movementSpeed = settings().get(["printerParameters", "movementSpeed", ["x", "y", "z"]], asdict=True)

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

		# execute the jog commands
		for axis, value in validated_values.iteritems():
			# TODO make this a generic method call (printer.jog(axis, value)) to get rid of gcode here
			printer.commands(["G91", "G1 %s%.4f F%d" % (axis.upper(), value, movementSpeed[axis]), "G90"])

	##~~ home command
	elif command == "home":
		validated_values = []
		axes = data["axes"]
		for axis in axes:
			if not axis in valid_axes:
				return make_response("Invalid axis: %s" % axis, 400)
			validated_values.append(axis)

		# execute the home command
		# TODO make this a generic method call (printer.home(axis, ...)) to get rid of gcode here
		printer.commands(["G91", "G28 %s" % " ".join(map(lambda x: "%s0" % x.upper(), validated_values)), "G90"])

	return jsonify(SUCCESS)


@ajax.route("/control/printer/feeder", methods=["POST"])
@restricted_access
def controlPrinterFeeder():
	if not printer.isOperational() or printer.isPrinting():
		# do not jog when a print job is running or we don't have a connection
		return make_response("Printer is not operational or currently printing", 403)

	valid_commands = {
		"extrude": ["amount"]
	}
	command, data, response = util.getJsonCommandFromRequest(request, valid_commands)
	if response is not None:
		return response

	extrusionSpeed = settings().get(["printerParameters", "movementSpeed", "e"])

	if command == "extrude":
		amount = data["amount"]
		if not isinstance(amount, (int, long, float)):
			return make_response("Not a number for extrusion amount: %r" % amount, 400)

		# TODO make this a generic method call (printer.extruder([hotend,] amount)) to get rid of gcode here
		printer.commands(["G91", "G1 E%s F%d" % (data["amount"], extrusionSpeed), "G90"])

	return jsonify(SUCCESS)


@ajax.route("/control/custom", methods=["GET"])
def getCustomControls():
	customControls = settings().get(["controls"])
	return jsonify(controls=customControls)


@ajax.route("/control/sd", methods=["POST"])
@restricted_access
def sdCommand():
	if not settings().getBoolean(["feature", "sdSupport"]) or not printer.isOperational() or printer.isPrinting():
		return make_response("SD support is disabled", 403)

	valid_commands = {
		"init": [],
		"refresh": [],
		"release": []
	}
	command, data, response = util.getJsonCommandFromRequest(request, valid_commands)
	if response is not None:
		return response

	if command == "init":
		printer.initSdCard()
	elif command == "refresh":
		printer.refreshSdFiles()
	elif command == "release":
		printer.releaseSdCard()

	return jsonify(SUCCESS)


