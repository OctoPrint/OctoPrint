#!/usr/bin/env python
# coding=utf-8
__author__ = 'Gina Häußge <osd@foosel.net>'

from flask import Flask, request, render_template, jsonify

from printer import Printer

import os
import fnmatch

BASEURL='/ajax/'
SUCCESS={}
UPLOAD_FOLDER="uploads"

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
def printerMessages():
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
	if file != None:
		filename = UPLOAD_FOLDER + os.sep + file.filename
		file.save(filename)
	return readGcodeFiles()

@app.route(BASEURL + 'gcodefiles/load', methods=['POST'])
def loadGcodeFile():
	filename = request.values["filename"]
	printer.loadGcode(UPLOAD_FOLDER + os.sep + filename)
	return jsonify(SUCCESS)

@app.route(BASEURL + 'gcodefiles/delete', methods=['POST'])
def deleteGcodeFile():
	filename = request.values["filename"]
	os.remove(UPLOAD_FOLDER + os.sep + filename)
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

def run():
	app.debug = True
	app.run(host="0.0.0.0")
