# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

from flask import request, jsonify, make_response, url_for

import octoprint.util as util
from octoprint.filemanager.destinations import FileDestinations
from octoprint.settings import settings, valid_boolean_trues
from octoprint.server import printer, fileManager, slicingManager, eventManager, NO_CONTENT
from octoprint.server.util.flask import restricted_access
from octoprint.server.api import api
from octoprint.events import Events
import octoprint.filemanager


#~~ GCODE file handling


@api.route("/files", methods=["GET"])
def readGcodeFiles():
	filter = None
	if "filter" in request.values:
		filter = request.values["filter"]
	files = _getFileList(FileDestinations.LOCAL, filter=filter)
	files.extend(_getFileList(FileDestinations.SDCARD))
	return jsonify(files=files, free=util.getFreeBytes(settings().getBaseFolder("uploads")))


@api.route("/files/<string:origin>", methods=["GET"])
def readGcodeFilesForOrigin(origin):
	if origin not in [FileDestinations.LOCAL, FileDestinations.SDCARD]:
		return make_response("Unknown origin: %s" % origin, 404)

	files = _getFileList(origin)

	if origin == FileDestinations.LOCAL:
		return jsonify(files=files, free=util.getFreeBytes(settings().getBaseFolder("uploads")))
	else:
		return jsonify(files=files)


def _getFileDetails(origin, filename):
	files = _getFileList(origin)
	for file in files:
		if file["name"] == filename:
			return file
	return None


def _getFileList(origin, filter=None):
	if origin == FileDestinations.SDCARD:
		sdFileList = printer.getSdFiles()

		files = []
		if sdFileList is not None:
			for sdFile, sdSize in sdFileList:
				file = {
					"type": "machinecode",
					"name": sdFile,
					"origin": FileDestinations.SDCARD,
					"refs": {
						"resource": url_for(".readGcodeFile", target=FileDestinations.SDCARD, filename=sdFile, _external=True)
					}
				}
				if sdSize is not None:
					file.update({"size": sdSize})
				files.append(file)
	else:
		filter_func = None
		if filter:
			filter_func = lambda entry, entry_data: octoprint.filemanager.valid_file_type(entry, type=filter)
		files = fileManager.list_files(origin, filter=filter_func, recursive=False)[origin].values()
		for file in files:
			file["origin"] = FileDestinations.LOCAL

			if "analysis" in file and octoprint.filemanager.valid_file_type(file["name"], type="gcode"):
				file["gcodeAnalysis"] = file["analysis"]
				del file["analysis"]

			if "history" in file and octoprint.filemanager.valid_file_type(file["name"], type="gcode"):
				# convert print log
				history = file["history"]
				del file["history"]
				success = 0
				failure = 0
				last = None
				for entry in history:
					success += 1 if entry["success"] else 0
					failure += 1 if not entry["success"] else 0
					if not last or entry["timestamp"] > last["timestamp"]:
						last = entry
				if last:
					prints = dict(
						success=success,
						failure=failure,
						last=dict(
							success=last["success"],
							date=last["timestamp"],
							printTime=last["printTime"]
						)
					)
					file["prints"] = prints

			file.update({
				"refs": {
					"resource": url_for(".readGcodeFile", target=FileDestinations.LOCAL, filename=file["name"], _external=True),
					"download": url_for("index", _external=True) + "downloads/files/" + FileDestinations.LOCAL + "/" + file["name"]
				}
			})
	return files


def _verifyFileExists(origin, filename):
	if origin == FileDestinations.SDCARD:
		return filename in map(lambda x: x[0], printer.getSdFiles())
	else:
		return fileManager.file_exists(origin, filename)


@api.route("/files/<string:target>", methods=["POST"])
@restricted_access
def uploadGcodeFile(target):
	if not target in [FileDestinations.LOCAL, FileDestinations.SDCARD]:
		return make_response("Unknown target: %s" % target, 404)

	input_name = "file"
	input_upload_name = input_name + "." + settings().get(["server", "uploads", "nameSuffix"])
	input_upload_path = input_name + "." + settings().get(["server", "uploads", "pathSuffix"])
	if input_upload_name in request.values and input_upload_path in request.values:
		import shutil
		upload = util.Object()
		upload.filename = request.values[input_upload_name]
		upload.save = lambda new_path: shutil.move(request.values[input_upload_path], new_path)
	elif input_name in request.files:
		upload = request.files[input_name]
	else:
		return make_response("No file included", 400)

	if target == FileDestinations.SDCARD and not settings().getBoolean(["feature", "sdSupport"]):
		return make_response("SD card support is disabled", 404)

	sd = target == FileDestinations.SDCARD
	selectAfterUpload = "select" in request.values.keys() and request.values["select"] in valid_boolean_trues
	printAfterSelect = "print" in request.values.keys() and request.values["print"] in valid_boolean_trues

	if sd:
		# validate that all preconditions for SD upload are met before attempting it
		if not (printer.isOperational() and not (printer.isPrinting() or printer.isPaused())):
			return make_response("Can not upload to SD card, printer is either not operational or already busy", 409)
		if not printer.isSdReady():
			return make_response("Can not upload to SD card, not yet initialized", 409)

	# determine current job
	currentFilename = None
	currentOrigin = None
	currentJob = printer.getCurrentJob()
	if currentJob is not None and "file" in currentJob.keys():
		currentJobFile = currentJob["file"]
		if "name" in currentJobFile.keys() and "origin" in currentJobFile.keys():
			currentFilename = currentJobFile["name"]
			currentOrigin = currentJobFile["origin"]

	# determine future filename of file to be uploaded, abort if it can't be uploaded
	try:
		futureFilename = fileManager.sanitize_name(FileDestinations.LOCAL, upload.filename)
	except:
		futureFilename = None
	if futureFilename is None or not (slicingManager.slicing_enabled or octoprint.filemanager.valid_file_type(futureFilename, type="gcode")):
		return make_response("Can not upload file %s, wrong format?" % upload.filename, 415)

	# prohibit overwriting currently selected file while it's being printed
	if futureFilename == currentFilename and target == currentOrigin and printer.isPrinting() or printer.isPaused():
		return make_response("Trying to overwrite file that is currently being printed: %s" % currentFilename, 409)

	def fileProcessingFinished(filename, absFilename, destination):
		"""
		Callback for when the file processing (upload, optional slicing, addition to analysis queue) has
		finished.

		Depending on the file's destination triggers either streaming to SD card or directly calls selectAndOrPrint.
		"""

		if destination == FileDestinations.SDCARD and octoprint.filemanager.valid_file_type(filename, "gcode"):
			return filename, printer.addSdFile(filename, absFilename, selectAndOrPrint)
		else:
			selectAndOrPrint(filename, absFilename, destination)
			return filename

	def selectAndOrPrint(filename, absFilename, destination):
		"""
		Callback for when the file is ready to be selected and optionally printed. For SD file uploads this is only
		the case after they have finished streaming to the printer, which is why this callback is also used
		for the corresponding call to addSdFile.

		Selects the just uploaded file if either selectAfterUpload or printAfterSelect are True, or if the
		exact file is already selected, such reloading it.
		"""
		if octoprint.filemanager.valid_file_type(added_file, "gcode") and (selectAfterUpload or printAfterSelect or (currentFilename == filename and currentOrigin == destination)):
			printer.selectFile(absFilename, destination == FileDestinations.SDCARD, printAfterSelect)

	added_file = fileManager.add_file(FileDestinations.LOCAL, upload.filename, upload, allow_overwrite=True)
	if added_file is None:
		return make_response("Could not upload the file %s" % upload.filename, 500)
	if octoprint.filemanager.valid_file_type(added_file, "stl"):
		filename = added_file
		done = True
	else:
		filename = fileProcessingFinished(added_file, fileManager.get_absolute_path(FileDestinations.LOCAL, added_file), target)
		done = True

	sdFilename = None
	if isinstance(filename, tuple):
		filename, sdFilename = filename

	eventManager.fire(Events.UPLOAD, {"file": filename, "target": target})

	files = {}
	location = url_for(".readGcodeFile", target=FileDestinations.LOCAL, filename=filename, _external=True)
	files.update({
		FileDestinations.LOCAL: {
			"name": filename,
			"origin": FileDestinations.LOCAL,
			"refs": {
				"resource": location,
				"download": url_for("index", _external=True) + "downloads/files/" + FileDestinations.LOCAL + "/" + filename
			}
		}
	})

	if sd and sdFilename:
		location = url_for(".readGcodeFile", target=FileDestinations.SDCARD, filename=sdFilename, _external=True)
		files.update({
			FileDestinations.SDCARD: {
				"name": sdFilename,
				"origin": FileDestinations.SDCARD,
				"refs": {
					"resource": location
				}
			}
		})

	r = make_response(jsonify(files=files, done=done), 201)
	r.headers["Location"] = location
	return r


@api.route("/files/<string:target>/<path:filename>", methods=["GET"])
def readGcodeFile(target, filename):
	if not target in [FileDestinations.LOCAL, FileDestinations.SDCARD]:
		return make_response("Unknown target: %s" % target, 404)

	file = _getFileDetails(target, filename)
	if not file:
		return make_response("File not found on '%s': %s" % (target, filename), 404)

	return jsonify(file)


@api.route("/files/<string:target>/<path:filename>", methods=["POST"])
@restricted_access
def gcodeFileCommand(filename, target):
	if not target in [FileDestinations.LOCAL, FileDestinations.SDCARD]:
		return make_response("Unknown target: %s" % target, 404)

	if not _verifyFileExists(target, filename):
		return make_response("File not found on '%s': %s" % (target, filename), 404)

	# valid file commands, dict mapping command name to mandatory parameters
	valid_commands = {
		"select": [],
		"slice": []
	}

	command, data, response = util.getJsonCommandFromRequest(request, valid_commands)
	if response is not None:
		return response

	if command == "select":
		# selects/loads a file
		printAfterLoading = False
		if "print" in data.keys() and data["print"]:
			if not printer.isOperational():
				return make_response("Printer is not operational, cannot directly start printing", 409)
			printAfterLoading = True

		sd = False
		if target == FileDestinations.SDCARD:
			filenameToSelect = filename
			sd = True
		else:
			filenameToSelect = fileManager.get_absolute_path(target, filename)
		printer.selectFile(filenameToSelect, sd, printAfterLoading)

	elif command == "slice":
		if "slicer" in data.keys():
			slicer = data["slicer"]
			del data["slicer"]
			if not slicer in slicingManager.registered_slicers:
				return make_response("Slicer {slicer} is not available".format(**locals()), 400)
		elif "cura" in slicingManager.registered_slicers:
			slicer = "cura"
		else:
			return make_response("Cannot slice {filename}, no slicer available".format(**locals()), 415)

		if not octoprint.filemanager.valid_file_type(filename, type="stl"):
			return make_response("Cannot slice {filename}, not an STL file".format(**locals()), 415)

		if "gcode" in data.keys() and data["gcode"]:
			gcode_name = data["gcode"]
			del data["gcode"]
		else:
			import os
			name, _ = os.path.splitext(filename)
			gcode_name = name + ".gco"

		if "profile" in data.keys() and data["profile"]:
			profile = data["profile"]
			del data["profile"]
		else:
			profile = None

		override_keys = [k for k in data if k.startswith("profile.") and data[k] is not None]
		overrides = dict()
		for key in override_keys:
			overrides[key[len("profile."):]] = data[key]

		ok, result = fileManager.slice(slicer, target, filename, target, gcode_name, profile=profile, overrides=overrides)
		if ok:
			files = {}
			location = url_for(".readGcodeFile", target=target, filename=gcode_name, _external=True)
			result = {
				"name": gcode_name,
				"origin": FileDestinations.LOCAL,
				"refs": {
					"resource": location,
					"download": url_for("index", _external=True) + "downloads/files/" + target + "/" + gcode_name
				}
			}

			r = make_response(jsonify(result), 202)
			r.headers["Location"] = location
			return r
		else:
			return make_response("Could not slice: {result}".format(result=result), 500)

	return NO_CONTENT


@api.route("/files/<string:target>/<path:filename>", methods=["DELETE"])
@restricted_access
def deleteGcodeFile(filename, target):
	if not target in [FileDestinations.LOCAL, FileDestinations.SDCARD]:
		return make_response("Unknown target: %s" % target, 404)

	if not _verifyFileExists(target, filename):
		return make_response("File not found on '%s': %s" % (target, filename), 404)

	currentJob = printer.getCurrentJob()
	currentFilename = None
	currentOrigin = None
	if currentJob is not None and "file" in currentJob.keys() and "name" in currentJob["file"] and "origin" in currentJob["file"]:
		currentFilename = currentJob["file"]["name"]
		currentOrigin = currentJob["file"]["origin"]

	# prohibit deleting the file that is currently being printed
	if currentFilename == filename and currentOrigin == target and (printer.isPrinting() or printer.isPaused()):
		make_response("Trying to delete file that is currently being printed: %s" % filename, 409)

	# deselect the file if it's currently selected
	if currentFilename is not None and filename == currentFilename:
		printer.unselectFile()

	# delete it
	if target == FileDestinations.SDCARD:
		printer.deleteSdFile(filename)
	else:
		fileManager.remove_file(target, filename)

	return NO_CONTENT

