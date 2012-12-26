#!/usr/bin/env python
# coding=utf-8
__author__ = 'Gina Häußge <osd@foosel.net>'

from flask import Flask, request, render_template, jsonify, make_response
from werkzeug import secure_filename

from printer import Printer

import sys
import os
import fnmatch

APPNAME="Cura"
BASEURL="/ajax/"
SUCCESS={}

# taken from http://stackoverflow.com/questions/1084697/how-do-i-store-desktop-application-data-in-a-cross-platform-way-for-python
if sys.platform == 'darwin':
	from AppKit import NSSearchPathForDirectoriesInDomains
	# http://developer.apple.com/DOCUMENTATION/Cocoa/Reference/Foundation/Miscellaneous/Foundation_Functions/Reference/reference.html#//apple_ref/c/func/NSSearchPathForDirectoriesInDomains
	# NSApplicationSupportDirectory = 14
	# NSUserDomainMask = 1
	# True for expanding the tilde into a fully qualified path
	appdata = os.path.join(NSSearchPathForDirectoriesInDomains(14, 1, True)[0], APPNAME)
elif sys.platform == 'win32':
	appdata = os.path.join(os.environ['APPDATA'], APPNAME)
else:
	appdata = os.path.expanduser(os.path.join("~", "." + APPNAME.lower()))

UPLOAD_FOLDER = appdata + os.sep + "uploads"
if not os.path.isdir(UPLOAD_FOLDER):
	os.makedirs(UPLOAD_FOLDER)
ALLOWED_EXTENSIONS = set(["gcode"])

app = Flask("Cura.webui")
printer = Printer()

@app.route('/')
def index():
	return render_template('index.html')

#~~ Printer state

@app.route(BASEURL + 'state', methods=['GET'])
def printerState():
	temp = printer.currentTemp
	bedTemp = printer.currentBedTemp
	targetTemp = printer.currentTargetTemp
	bedTargetTemp = printer.currentBedTargetTemp
	jobData = printer.jobData()

	result = {
		'state': printer.getStateString(),
		'temp': temp,
		'bedTemp': bedTemp,
		'targetTemp': targetTemp,
		'targetBedTemp': bedTargetTemp,
		'operational': printer.isOperational(),
		'closedOrError': printer.isClosedOrError(),
		'error': printer.isError(),
		'printing': printer.isPrinting(),
		'paused': printer.isPaused(),
		'ready': printer.isReady()
	}

	if (jobData != None):
		result['job'] = jobData

	if (request.values.has_key('temperatures')):
		result['temperatures'] = printer.temps

	if (request.values.has_key('log')):
		result['log'] = printer.log

	if (request.values.has_key('messages')):
		result['messages'] = printer.messages

	return jsonify(result)

@app.route(BASEURL + 'state/messages', methods=['GET'])
def printerMessages():
	return jsonify(messages=printer.messages)

@app.route(BASEURL + 'state/log', methods=['GET'])
def printerLogs():
	return jsonify(log=printer.log)

@app.route(BASEURL + 'state/temperatures', methods=['GET'])
def printerTemperatures():
	return jsonify(temperatures = printer.temps)

#~~ Printer control

@app.route(BASEURL + 'control/connect', methods=['POST'])
def connect():
	printer.connect()
	return jsonify(state='Connecting')

@app.route(BASEURL + 'control/disconnect', methods=['POST'])
def disconnect():
	printer.disconnect()
	return jsonify(state='Offline')

@app.route(BASEURL + 'control/command', methods=['POST'])
def printerCommand():
	command = request.form['command']
	printer.command(command)
	return jsonify(SUCCESS)

@app.route(BASEURL + 'control/print', methods=['POST'])
def printGcode():
	printer.startPrint()
	return jsonify(SUCCESS)

@app.route(BASEURL + 'control/pause', methods=['POST'])
def pausePrint():
	printer.togglePausePrint()
	return jsonify(SUCCESS)

@app.route(BASEURL + 'control/cancel', methods=['POST'])
def cancelPrint():
	printer.cancelPrint()
	return jsonify(SUCCESS)

@app.route(BASEURL + 'control/temperature', methods=['POST'])
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
		# do not jog when a print job is running or we don't have a connection
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

#~~ GCODE file handling

@app.route(BASEURL + 'gcodefiles', methods=['GET'])
def readGcodeFiles():
	files = []
	for osFile in os.listdir(UPLOAD_FOLDER):
		if not fnmatch.fnmatch(osFile, "*.gcode"):
			continue
		files.append({
			"name": osFile,
			"size": sizeof_fmt(os.stat(UPLOAD_FOLDER + os.sep + osFile).st_size)
		})
	return jsonify(files=files)

@app.route(BASEURL + 'gcodefiles/upload', methods=['POST'])
def uploadGcodeFile():
	file = request.files['gcode_file']
	if file and allowed_file(file.filename):
		secure = secure_filename(file.filename)
		filename = os.path.join(UPLOAD_FOLDER, secure)
		file.save(filename)
	return readGcodeFiles()

@app.route(BASEURL + 'gcodefiles/load', methods=['POST'])
def loadGcodeFile():
	filename = request.values["filename"]
	printer.loadGcode(UPLOAD_FOLDER + os.sep + filename)
	return jsonify(SUCCESS)

@app.route(BASEURL + 'gcodefiles/delete', methods=['POST'])
def deleteGcodeFile():
	if request.values.has_key("filename"):
		filename = request.values["filename"]
		if allowed_file(filename):
			secure = UPLOAD_FOLDER + os.sep + secure_filename(filename)
			if os.path.exists(secure):
				os.remove(secure)
	return readGcodeFiles()

def sizeof_fmt(num):
	"""
	 Taken from http://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size
	"""
	for x in ['bytes','KB','MB','GB']:
		if num < 1024.0:
			return "%3.1f%s" % (num, x)
		num /= 1024.0
	return "%3.1f%s" % (num, 'TB')

def allowed_file(filename):
	return "." in filename and filename.rsplit(".", 1)[1] in ALLOWED_EXTENSIONS

def run():
	app.run(host="0.0.0.0", port=5000)
