# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

from flask import Flask, request, render_template, jsonify, send_file, abort
from werkzeug import secure_filename

from printer_webui.printer import Printer, getConnectionOptions
from printer_webui.settings import settings

import sys
import os
import fnmatch
import StringIO

BASEURL="/ajax/"
SUCCESS={}

UPLOAD_FOLDER = os.path.join(settings().settings_dir, "uploads")
if not os.path.isdir(UPLOAD_FOLDER):
	os.makedirs(UPLOAD_FOLDER)
ALLOWED_EXTENSIONS = set(["gcode"])

WEBCAM_FOLDER = os.path.join(settings().settings_dir, "webcam")
if not os.path.isdir(WEBCAM_FOLDER):
	os.makedirs(WEBCAM_FOLDER)

app = Flask("printer_webui")
printer = Printer()

@app.route("/")
def index():
	return render_template("index.html", webcamStream = settings().get("webcam", "stream"))

#~~ Printer state

@app.route(BASEURL + "state", methods=["GET"])
def printerState():
	temp = printer.currentTemp
	bedTemp = printer.currentBedTemp
	targetTemp = printer.currentTargetTemp
	bedTargetTemp = printer.currentBedTargetTemp
	jobData = printer.jobData()
	gcodeState = printer.gcodeState()
	feedrateState = printer.feedrateState()

	result = {
		"state": printer.getStateString(),
		"temp": temp,
		"bedTemp": bedTemp,
		"targetTemp": targetTemp,
		"targetBedTemp": bedTargetTemp,
		"operational": printer.isOperational(),
		"closedOrError": printer.isClosedOrError(),
		"error": printer.isError(),
		"printing": printer.isPrinting(),
		"paused": printer.isPaused(),
		"ready": printer.isReady(),
		"loading": printer.isLoading()
	}

	if jobData is not None:
		jobData["filename"] = jobData["filename"].replace(UPLOAD_FOLDER + os.sep, "")
		result["job"] = jobData

	if gcodeState is not None:
		gcodeState["filename"] = gcodeState["filename"].replace(UPLOAD_FOLDER + os.sep, "")
		result["gcode"] = gcodeState

	if feedrateState is not None:
		result["feedrate"] = feedrateState

	if request.values.has_key("temperatures"):
		result["temperatures"] = printer.temps

	if request.values.has_key("log"):
		result["log"] = printer.log

	if request.values.has_key("messages"):
		result["messages"] = printer.messages

	return jsonify(result)

@app.route(BASEURL + "state/messages", methods=["GET"])
def printerMessages():
	return jsonify(messages=printer.messages)

@app.route(BASEURL + "state/log", methods=["GET"])
def printerLogs():
	return jsonify(log=printer.log)

@app.route(BASEURL + "state/temperatures", methods=["GET"])
def printerTemperatures():
	return jsonify(temperatures = printer.temps)

#~~ Printer control

@app.route(BASEURL + "control/connectionOptions", methods=["GET"])
def connectionOptions():
	return jsonify(getConnectionOptions())

@app.route(BASEURL + "control/connect", methods=["POST"])
def connect():
	port = None
	baudrate = None
	if request.values.has_key("port"):
		port = request.values["port"]
	if request.values.has_key("baudrate"):
		baudrate = request.values["baudrate"]
	if request.values.has_key("save"):
		settings().set("serial", "port", port)
		settings().set("serial", "baudrate", baudrate)
		settings().save()
	printer.connect(port=port, baudrate=baudrate)
	return jsonify(state="Connecting")

@app.route(BASEURL + "control/disconnect", methods=["POST"])
def disconnect():
	printer.disconnect()
	return jsonify(state="Offline")

@app.route(BASEURL + "control/command", methods=["POST"])
def printerCommand():
	command = request.form["command"]
	printer.command(command)
	return jsonify(SUCCESS)

@app.route(BASEURL + "control/print", methods=["POST"])
def printGcode():
	printer.startPrint()
	return jsonify(SUCCESS)

@app.route(BASEURL + "control/pause", methods=["POST"])
def pausePrint():
	printer.togglePausePrint()
	return jsonify(SUCCESS)

@app.route(BASEURL + "control/cancel", methods=["POST"])
def cancelPrint():
	printer.cancelPrint()
	return jsonify(SUCCESS)

@app.route(BASEURL + "control/temperature", methods=["POST"])
def setTargetTemperature():
	if not printer.isOperational():
		return jsonify(SUCCESS)

	if request.values.has_key("temp"):
		# set target temperature
		temp = request.values["temp"];
		printer.command("M104 S" + temp)

	if request.values.has_key("bedTemp"):
		# set target bed temperature
		bedTemp = request.values["bedTemp"]
		printer.command("M140 S" + bedTemp)

	return jsonify(SUCCESS)

@app.route(BASEURL + "control/jog", methods=["POST"])
def jog():
	if not printer.isOperational() or printer.isPrinting():
		# do not jog when a print job is running or we don"t have a connection
		return jsonify(SUCCESS)

	if request.values.has_key("x"):
		# jog x
		x = request.values["x"]
		printer.commands(["G91", "G1 X" + x + " F6000", "G90"])
	if request.values.has_key("y"):
		# jog y
		y = request.values["y"]
		printer.commands(["G91", "G1 Y" + y + " F6000", "G90"])
	if request.values.has_key("z"):
		# jog z
		z = request.values["z"]
		printer.commands(["G91", "G1 Z" + z + " F200", "G90"])
	if request.values.has_key("homeXY"):
		# home x/y
		printer.command("G28 X0 Y0")
	if request.values.has_key("homeZ"):
		# home z
		printer.command("G28 Z0")

	return jsonify(SUCCESS)

@app.route(BASEURL + "control/speed", methods=["POST"])
def speed():
	if not printer.isOperational():
		return jsonify(SUCCESS)

	for key in ["outerWall", "innerWall", "fill", "support"]:
		if request.values.has_key(key):
			value = int(request.values[key])
			printer.setFeedrateModifier(key, value)

	return jsonify(feedrate = printer.feedrateState())

#~~ GCODE file handling

@app.route(BASEURL + "gcodefiles", methods=["GET"])
def readGcodeFiles():
	files = []
	for osFile in os.listdir(UPLOAD_FOLDER):
		if not fnmatch.fnmatch(osFile, "*.gcode"):
			continue
		files.append({
			"name": osFile,
			"size": sizeof_fmt(os.stat(os.path.join(UPLOAD_FOLDER, osFile)).st_size)
		})
	return jsonify(files=files)

@app.route(BASEURL + "gcodefiles/upload", methods=["POST"])
def uploadGcodeFile():
	file = request.files["gcode_file"]
	if file and allowed_file(file.filename):
		secure = secure_filename(file.filename)
		filename = os.path.join(UPLOAD_FOLDER, secure)
		file.save(filename)
	return readGcodeFiles()

@app.route(BASEURL + "gcodefiles/load", methods=["POST"])
def loadGcodeFile():
	filename = request.values["filename"]
	printer.loadGcode(os.path.join(UPLOAD_FOLDER, filename))
	return jsonify(SUCCESS)

@app.route(BASEURL + "gcodefiles/delete", methods=["POST"])
def deleteGcodeFile():
	if request.values.has_key("filename"):
		filename = request.values["filename"]
		if allowed_file(filename):
			secure = os.path.join(UPLOAD_FOLDER, secure_filename(filename))
			if os.path.exists(secure):
				os.remove(secure)
	return readGcodeFiles()

#~~ settings

@app.route(BASEURL + "settings", methods=["GET"])
def getSettings():
	s = settings()
	return jsonify({
		"serial_port": s.get("serial", "port"),
		"serial_baudrate": s.get("serial", "baudrate")
	})

@app.route(BASEURL + "settings", methods=["POST"])
def setSettings():
	s = settings()
	if request.values.has_key("serial_port"):
		s.set("serial", "port", request.values["serial_port"])
	if request.values.has_key("serial_baudrate"):
		s.set("serial", "baudrate", request.values["serial_baudrate"])

	s.save()
	return getSettings()

#~~ helper functions

def sizeof_fmt(num):
	"""
	 Taken from http://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size
	"""
	for x in ["bytes","KB","MB","GB"]:
		if num < 1024.0:
			return "%3.1f%s" % (num, x)
		num /= 1024.0
	return "%3.1f%s" % (num, "TB")

def allowed_file(filename):
	return "." in filename and filename.rsplit(".", 1)[1] in ALLOWED_EXTENSIONS

#~~ startup code

def run(host = "0.0.0.0", port = 5000, debug = False):
	app.debug = debug
	app.run(host=host, port=port, use_reloader=False)

def main():
	from optparse import OptionParser

	defaultHost = settings().get("server", "host")
	defaultPort = settings().get("server", "port")

	parser = OptionParser(usage="usage: %prog [options]")
	parser.add_option("-d", "--debug", action="store_true", dest="debug",
		help="Enable debug mode")
	parser.add_option("--host", action="store", type="string", default=defaultHost, dest="host",
		help="Specify the host on which to bind the server, defaults to %s if not set" % (defaultHost))
	parser.add_option("--port", action="store", type="int", default=defaultPort, dest="port",
		help="Specify the port on which to bind the server, defaults to %s if not set" % (defaultPort))
	(options, args) = parser.parse_args()

	run(host=options.host, port=options.port, debug=options.debug)

if __name__ == "__main__":
	main()