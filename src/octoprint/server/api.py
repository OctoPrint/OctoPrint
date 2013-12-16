# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

import logging

from flask import Blueprint, request, jsonify, abort

from octoprint.server import printer, gcodeManager, SUCCESS
from octoprint.server.util import api_access
from octoprint.settings import valid_boolean_trues
from octoprint.filemanager.destinations import FileDestinations
import octoprint.gcodefiles as gcodefiles
import octoprint.util as util
from octoprint.printer import Printer, getConnectionOptions
from octoprint.settings import settings, valid_boolean_trues

api = Blueprint("api", __name__)

@api.route("/load", methods=["POST"])
@api_access
def apiLoad():
	logger = logging.getLogger(__name__)

	if not "file" in request.files.keys():
		abort(400)

	# Perform an upload
	f = request.files["file"]
	if not gcodefiles.isGcodeFileName(f.filename):
		abort(400)

	destination = FileDestinations.LOCAL
	filename, done = gcodeManager.addFile(f, destination)
	if filename is None:
		logger.warn("Upload via API failed")
		abort(500)

	# Immediately perform a file select and possibly print too
	printAfterSelect = False
	if "print" in request.values.keys() and request.values["print"] in valid_boolean_trues:
		printAfterSelect = True
	filepath = gcodeManager.getAbsolutePath(filename)
	if filepath is not None:
		printer.selectFile(filepath, False, printAfterSelect)
	return jsonify(SUCCESS)

@api.route("/state", methods=["POST"])
@api_access
def apiPrinterState():	
	currentData = printer.getCurrentData()
	currentData.update({
		"temperatures": printer.getCurrentTemperatures()
	})
	return jsonify(currentData)


#- Retrieve the list of files already in the printer
@api.route("/files", methods=["POST"])
@api_access
def apiFiles():
	files = gcodeManager.getAllFileData()

	sdFileList = printer.getSdFiles()
	if sdFileList is not None:
		for sdFile in sdFileList:
			files.append({
				"name": sdFile,
				"size": "n/a",
				"bytes": 0,
				"date": "n/a",
				"origin": "sd"
			})
	return jsonify(files=files, free=util.getFormattedSize(util.getFreeBytes(settings().getBaseFolder("uploads"))))


#- Select a file to load/print
# {"filename" : "escher_day_night.gcode", "startprint": false}
@api.route("/files/select", methods=["POST"])
@api_access
def apiSelectFiles():
	if not request.json:
		return jsonify(error="no json data provided")	

	if not printer.isOperational() or printer.isPrinting():
		return jsonify(error="printer is busy or not conected")
		
	data = request.json
		
	filename = data["filename"]
	
	printAfterSelect = False
	if data["startprint"] in valid_boolean_trues:
		printAfterSelect = True
	filepath = gcodeManager.getAbsolutePath(filename)
	if filepath is not None:
		printer.selectFile(filepath, False, printAfterSelect)
	return jsonify(SUCCESS)


#- Control the printer (move/extrude)
# { "axis" : "x", "length": 100 }
@api.route("/control/move", methods=["POST"] )
@api_access
def apiControl():
	if not request.json:
		return jsonify(error="no json data provided")	

	if not printer.isOperational() or printer.isPrinting():
		return jsonify(error="printer is busy or not conected")
				
	data = request.json
			
	axis = data["axis"]
	length = data["length"]
	
	return doJog(axis, length)
	
#- Control motors and fan
#  parameter fanspeed has to be the fan speed between 0 (off) and 255 (max)
# { "motors" : "off", "fanspeed" : 255 }
@api.route("/control/general", methods=["POST"] )
@api_access
def apiControlGeneral():
	if not request.json:
		return jsonify(error="no json data provided")	

	if not printer.isOperational() or printer.isPrinting():
		return jsonify(error="printer is busy or not conected")
		
	data = request.json	
	if "motors" in data:
		printer.commands(["M18"])
	
	if "fanspeed" in data:
		fanspeed = data["fanspeed"]
		printer.commands(["M106 S%d" % (fanspeed)])
	
	return jsonify(SUCCESS)


# -- Utility methods
	
# axis can be x, y, z, e (for extruder)
# if length == 0 -> home
def doJog(axis, length):

	if length != 0:
	    movementSpeed = settings().get(["printerParameters", "movementSpeed", [axis]])
	    printer.commands(["G91", "G1 %s%d F%d" % (axis.upper(), length, movementSpeed[0]), "G90"])
	else: 
	    #home
	    if axis == "Z":
	    	printer.command("G28 Z0")
	    else:
	    	printer.command("G28 X0 Y0")
			 
	return jsonify(SUCCESS)
	



	
