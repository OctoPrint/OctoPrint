# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

from flask import request, jsonify

from octoprint.settings import settings
from octoprint.printer import getConnectionOptions
from octoprint.server import printer, restricted_access, SUCCESS
from octoprint.server.ajax import ajax


#~~ Printer control


@ajax.route("/control/connection/options", methods=["GET"])
def connectionOptions():
	return jsonify(getConnectionOptions())


@ajax.route("/control/connection", methods=["POST"])
@restricted_access
def connect():
	if "command" in request.values.keys() and request.values["command"] == "connect":
		port = None
		baudrate = None
		if "port" in request.values.keys():
			port = request.values["port"]
		if "baudrate" in request.values.keys():
			baudrate = request.values["baudrate"]
		if "save" in request.values.keys():
			settings().set(["serial", "port"], port)
			settings().setInt(["serial", "baudrate"], baudrate)
			settings().save()
		if "autoconnect" in request.values.keys():
			settings().setBoolean(["serial", "autoconnect"], True)
			settings().save()
		printer.connect(port=port, baudrate=baudrate)
	elif "command" in request.values.keys() and request.values["command"] == "disconnect":
		printer.disconnect()

	return jsonify(SUCCESS)


@ajax.route("/control/command", methods=["POST"])
@restricted_access
def printerCommand():
	if "application/json" in request.headers["Content-Type"]:
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
def printJobControl():
	if "command" in request.values.keys():
		if request.values["command"] == "start":
			printer.startPrint()
		elif request.values["command"] == "pause":
			printer.togglePausePrint()
		elif request.values["command"] == "cancel":
			printer.cancelPrint()
	return jsonify(SUCCESS)


@ajax.route("/control/temperature", methods=["POST"])
@restricted_access
def setTargetTemperature():
	if "temp" in request.values.keys():
		# set target temperature
		temp = request.values["temp"]
		printer.command("M104 S" + temp)

	if "bedTemp" in request.values.keys():
		# set target bed temperature
		bedTemp = request.values["bedTemp"]
		printer.command("M140 S" + bedTemp)

	if "tempOffset" in request.values.keys():
		# set target temperature offset
		try:
			tempOffset = float(request.values["tempOffset"])
			if tempOffset >= -50 and tempOffset <= 50:
				printer.setTemperatureOffset(tempOffset, None)
		except:
			pass

	if "bedTempOffset" in request.values.keys():
		# set target bed temperature offset
		try:
			bedTempOffset = float(request.values["bedTempOffset"])
			if bedTempOffset >= -50 and bedTempOffset <= 50:
				printer.setTemperatureOffset(None, bedTempOffset)
		except:
			pass

	return jsonify(SUCCESS)


@ajax.route("/control/jog", methods=["POST"])
@restricted_access
def jog():
	if not printer.isOperational() or printer.isPrinting():
		# do not jog when a print job is running or we don't have a connection
		return jsonify(SUCCESS)

	(movementSpeedX, movementSpeedY, movementSpeedZ, movementSpeedE) = settings().get(["printerParameters", "movementSpeed", ["x", "y", "z", "e"]])
	if "x" in request.values.keys():
		# jog x
		x = request.values["x"]
		printer.commands(["G91", "G1 X%s F%d" % (x, movementSpeedX), "G90"])
	if "y" in request.values.keys():
		# jog y
		y = request.values["y"]
		printer.commands(["G91", "G1 Y%s F%d" % (y, movementSpeedY), "G90"])
	if "z" in request.values.keys():
		# jog z
		z = request.values["z"]
		printer.commands(["G91", "G1 Z%s F%d" % (z, movementSpeedZ), "G90"])
	if "homeXY" in request.values.keys():
		# home x/y
		printer.command("G28 X0 Y0")
	if "homeZ" in request.values.keys():
		# home z
		printer.command("G28 Z0")
	if "extrude" in request.values.keys():
		# extrude/retract
		length = request.values["extrude"]
		printer.commands(["G91", "G1 E%s F%d" % (length, movementSpeedE), "G90"])

	return jsonify(SUCCESS)


@ajax.route("/control/custom", methods=["GET"])
def getCustomControls():
	customControls = settings().get(["controls"])
	return jsonify(controls=customControls)


@ajax.route("/control/sd", methods=["POST"])
@restricted_access
def sdCommand():
	if not settings().getBoolean(["feature", "sdSupport"]) or not printer.isOperational() or printer.isPrinting():
		return jsonify(SUCCESS)

	if "command" in request.values.keys():
		command = request.values["command"]
		if command == "init":
			printer.initSdCard()
		elif command == "refresh":
			printer.refreshSdFiles()
		elif command == "release":
			printer.releaseSdCard()

	return jsonify(SUCCESS)


