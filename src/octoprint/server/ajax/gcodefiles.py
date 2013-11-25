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
	files = _getFileList(FileDestinations.LOCAL)
	files.extend(_getFileList(FileDestinations.SDCARD))
	return jsonify(files=files, free=util.getFormattedSize(util.getFreeBytes(settings().getBaseFolder("uploads"))))


@ajax.route("/gcodefiles/<string:target>", methods=["GET"])
def readGcodeFilesForTarget(target):
	if target not in [FileDestinations.LOCAL, FileDestinations.SDCARD]:
		return make_response("Invalid target: %s" % target, 400)

	return jsonify(files=_getFileList(target), free=util.getFormattedSize(util.getFreeBytes(settings().getBaseFolder("uploads"))))


def _getFileList(target):
	if target == FileDestinations.SDCARD:
		sdFileList = printer.getSdFiles()

		files = []
		if sdFileList is not None:
			for sdFile in sdFileList:
				files.append({
					"name": sdFile,
					"size": "n/a",
					"bytes": 0,
					"date": "n/a",
					"origin": FileDestinations.SDCARD
				})
	else:
		files = gcodeManager.getAllFileData()
	return files


@ajax.route("/gcodefiles/<string:target>", methods=["POST"])
@restricted_access
def uploadGcodeFile(target):
	if not target in [FileDestinations.LOCAL, FileDestinations.SDCARD]:
		return make_response("Invalid target: %s" % target, 400)

	if "gcode_file" in request.files.keys():
		file = request.files["gcode_file"]
		sd = target == FileDestinations.SDCARD
		selectAfterUpload = "select" in request.values.keys() and request.values["select"] in valid_boolean_trues
		printAfterSelect = "print" in request.values.keys() and request.values["print"] in valid_boolean_trues

		# determine current job
		currentFilename = None
		currentSd = None
		currentJob = printer.getCurrentJob()
		if currentJob is not None and "filename" in currentJob.keys() and "sd" in currentJob.keys():
			currentFilename = currentJob["filename"]
			currentSd = currentJob["sd"]

		# determine future filename of file to be uploaded, abort if it can't be uploaded
		futureFilename = gcodeManager.getFutureFilename(file)
		if futureFilename is None or (not settings().getBoolean(["cura", "enabled"]) and not gcodefiles.isGcodeFileName(futureFilename)):
			return make_response("Can not upload file %s, wrong format?" % file.filename, 400)

		# prohibit overwriting currently selected file while it's being printed
		if futureFilename == currentFilename and sd == currentSd and printer.isPrinting() or printer.isPaused():
			return make_response("Trying to overwrite file that is currently being printed: %s" % currentFilename, 403)

		filename = None

		def fileProcessingFinished(filename, absFilename, destination):
			"""
			Callback for when the file processing (upload, optional slicing, addition to analysis queue) has
			finished.

			Depending on the file's destination triggers either streaming to SD card or directly calls selectOrPrint.
			"""
			sd = destination == FileDestinations.SDCARD
			if sd:
				printer.addSdFile(filename, absFilename, selectAndOrPrint)
			else:
				selectAndOrPrint(absFilename, destination)

		def selectAndOrPrint(nameToSelect, destination):
			"""
			Callback for when the file is ready to be selected and optionally printed. For SD file uploads this only
			the case after they have finished streaming to the printer, which is why this callback is also used
			for the corresponding call to addSdFile.

			Selects the just uploaded file if either selectAfterUpload or printAfterSelect are True, or if the
			exact file is already selected, such reloading it.
			"""
			sd = destination == FileDestinations.SDCARD
			if selectAfterUpload or printAfterSelect or (currentFilename == filename and currentSd == sd):
				printer.selectFile(nameToSelect, sd, printAfterSelect)

		destination = FileDestinations.SDCARD if sd else FileDestinations.LOCAL
		filename, done = gcodeManager.addFile(file, destination, fileProcessingFinished)
		if filename is None:
			return make_response("Could not upload the file %s" % file.filename, 500)

		eventManager.fire("Upload", filename)
		return jsonify(files=gcodeManager.getAllFileData(), filename=filename, done=done)
	else:
		return make_response("No gcode_file included", 400)


@ajax.route("/gcodefiles/local/<path:filename>", methods=["GET"])
def readGcodeFile(filename):
	return redirectToTornado(request, url_for("index") + "downloads/gcode/" + filename)


@ajax.route("/gcodefiles/<string:target>/<path:filename>", methods=["POST"])
@restricted_access
def gcodeFileCommand(filename, target):
	if not target in [FileDestinations.LOCAL, FileDestinations.SDCARD]:
		return make_response("Invalid target: %s" % target, 400)

	# valid file commands, dict mapping command name to mandatory parameters
	valid_commands = {
		"load": []
	}

	command, data, response = util.getJsonCommandFromRequest(request, valid_commands)
	if response is not None:
		return response

	if command == "load":
		# selects/loads a file
		printAfterLoading = False
		if "print" in data.keys() and data["print"]:
			printAfterLoading = True

		sd = False
		if target == FileDestinations.SDCARD:
			filenameToSelect = filename
			sd = True
		else:
			filenameToSelect = gcodeManager.getAbsolutePath(filename)
		printer.selectFile(filenameToSelect, sd, printAfterLoading)
		return jsonify(SUCCESS)

	return make_response("Command %s is currently not implemented" % command, 400)


@ajax.route("/gcodefiles/<string:target>/<path:filename>", methods=["DELETE"])
@restricted_access
def deleteGcodeFile(filename, target):
	if not target in [FileDestinations.LOCAL, FileDestinations.SDCARD]:
		return make_response("Invalid target: %s" % target, 400)

	sd = target == FileDestinations.SDCARD

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


@ajax.route("/gcodefiles/<string:target>/refresh", methods=["POST"])
@restricted_access
def refreshFiles(target):
	if not target in [FileDestinations.LOCAL, FileDestinations.SDCARD]:
		return make_response("Invalid target: %s" % target, 400)

	if target == FileDestinations.SDCARD:
		printer.updateSdFiles()

	return jsonify(SUCCESS)

