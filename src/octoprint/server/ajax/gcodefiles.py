# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

from flask import request, jsonify, make_response, url_for

import octoprint.gcodefiles as gcodefiles
import octoprint.util as util
from octoprint.filemanager.destinations import FileDestinations
from octoprint.settings import settings, valid_boolean_trues
from octoprint.server import printer, gcodeManager, eventManager, restricted_access, SUCCESS
from octoprint.server.util import redirectToTornado
from octoprint.server.ajax import ajax


#~~ GCODE file handling


@ajax.route("/gcodefiles", methods=["GET"])
def readGcodeFiles():
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


@ajax.route("/gcodefiles/<path:filename>", methods=["GET"])
def readGcodeFile(filename):
	return redirectToTornado(request, url_for("index") + "downloads/gcode/" + filename)


@ajax.route("/gcodefiles/upload", methods=["POST"])
@restricted_access
def uploadGcodeFile():
	if "gcode_file" in request.files.keys():
		file = request.files["gcode_file"]
		sd = "target" in request.values.keys() and request.values["target"] == "sd";

		currentFilename = None
		currentSd = None
		currentJob = printer.getCurrentJob()
		if currentJob is not None and "filename" in currentJob.keys() and "sd" in currentJob.keys():
			currentFilename = currentJob["filename"]
			currentSd = currentJob["sd"]

		futureFilename = gcodeManager.getFutureFilename(file)
		if futureFilename is None or (not settings().getBoolean(["cura", "enabled"]) and not gcodefiles.isGcodeFileName(futureFilename)):
			return make_response("Can not upload file %s, wrong format?" % file.filename, 400)

		if futureFilename == currentFilename and sd == currentSd and printer.isPrinting() or printer.isPaused():
			# trying to overwrite currently selected file, but it is being printed
			return make_response("Trying to overwrite file that is currently being printed: %s" % currentFilename, 403)

		destination = FileDestinations.SDCARD if sd else FileDestinations.LOCAL

		filename, done = gcodeManager.addFile(file, destination)

		if filename is None:
			return make_response("Could not upload the file %s" % file.filename, 500)

		absFilename = gcodeManager.getAbsolutePath(filename)
		if sd:
			printer.addSdFile(filename, absFilename)

		if currentFilename == filename and currentSd == sd:
			# reload file as it was updated
			if sd:
				printer.selectFile(filename, sd, False)
			else:
				printer.selectFile(absFilename, sd, False)

		eventManager.fire("Upload", filename)
	return jsonify(files=gcodeManager.getAllFileData(), filename=filename, done=done)


@ajax.route("/gcodefiles/load", methods=["POST"])
@restricted_access
def loadGcodeFile():
	if "filename" in request.values.keys():
		printAfterLoading = False
		if "print" in request.values.keys() and request.values["print"] in valid_boolean_trues:
			printAfterLoading = True

		sd = False
		if "target" in request.values.keys() and request.values["target"] == "sd":
			filename = request.values["filename"]
			sd = True
		else:
			filename = gcodeManager.getAbsolutePath(request.values["filename"])
		printer.selectFile(filename, sd, printAfterLoading)
	return jsonify(SUCCESS)


@ajax.route("/gcodefiles/delete", methods=["POST"])
@restricted_access
def deleteGcodeFile():
	if "filename" in request.values.keys():
		filename = request.values["filename"]
		sd = "target" in request.values.keys() and request.values["target"] == "sd"

		currentJob = printer.getCurrentJob()
		currentFilename = None
		currentSd = None
		if currentJob is not None and "filename" in currentJob.keys() and "sd" in currentJob.keys():
			currentFilename = currentJob["filename"]
			currentSd = currentJob["sd"]

		if currentFilename is not None and filename == currentFilename and not (printer.isPrinting() or printer.isPaused()):
			printer.unselectFile()

		if not (currentFilename == filename and currentSd == sd and (printer.isPrinting() or printer.isPaused())):
			if sd:
				printer.deleteSdFile(filename)
			else:
				gcodeManager.removeFile(filename)
	return readGcodeFiles()


@ajax.route("/gcodefiles/refresh", methods=["POST"])
@restricted_access
def refreshFiles():
	printer.updateSdFiles()
	return jsonify(SUCCESS)

