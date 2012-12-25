#!/usr/bin/env python
# coding=utf-8
__author__ = 'Gina Häußge <osd@foosel.net>'

from flask import Flask, request, render_template, jsonify

from printer import Printer

import tempfile

app = Flask("Cura.webui")
printer = Printer()
printer.connect()

@app.route('/')
def index():
	return render_template('index.html')

@app.route('/api/printer/connect', methods=['POST'])
def connect():
	printer.connect()
	return jsonify(state='Connecting')

@app.route('/api/printer/disconnect', methods=['POST'])
def disconnect():
	printer.disconnect()
	return jsonify(state='Offline')

@app.route('/api/printer', methods=['GET'])
def printerState():
	temp = printer.currentTemp
	bedTemp = printer.currentBedTemp
	jobData = printer.jobData()

	if jobData != None:
		return jsonify(state=printer.getStateString(),
			operational=printer.isOperational(),
			closedOrError=printer.isClosedOrError(),
			temp=temp,
			bedTemp=bedTemp,
			job=jobData)
	else:
		return jsonify(state=printer.getStateString(),
			temperature=temp,
			bedTemperature=bedTemp)

@app.route('/api/printer/messages', methods=['GET'])
def printerMessages():
	return jsonify(messages=printer.messages)

@app.route('/api/printer/log', methods=['GET'])
def printerMessages():
	return jsonify(log=printer.log)

@app.route('/api/printer/command', methods=['POST'])
def printerCommand():
	command = request.form['command']
	printer.command(command)
	return jsonify(state=printer.getStateString())

@app.route('/api/printer/temperatures', methods=['GET'])
def printerTemperatures():
	return jsonify(temperatures = printer.temps)

@app.route('/api/printer/gcode', methods=['POST'])
def uploadGcodeFile():
	file = request.files['gcode_file']
	if file != None:
		(handle, filename) = tempfile.mkstemp(suffix='.gcode', prefix='tmp_', text=True)
		file.save(filename)
		printer.loadGcode(filename)
	return jsonify(state=printer.getStateString())

@app.route('/api/printer/print', methods=['POST'])
def printGcode():
	printer.startPrint()
	return jsonify(state=printer.getStateString())

@app.route('/api/printer/pause', methods=['POST'])
def pausePrint():
	printer.togglePausePrint()
	return jsonify(state=printer.getStateString())

@app.route('/api/printer/cancel', methods=['POST'])
def cancelPrint():
	printer.cancelPrint()
	return jsonify(state=printer.getStateString())

def run():
	app.debug = True
	app.run()
