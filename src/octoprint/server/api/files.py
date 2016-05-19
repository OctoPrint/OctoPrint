# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

from flask import request, jsonify, make_response, url_for

from octoprint.filemanager.destinations import FileDestinations
from octoprint.settings import settings, valid_boolean_trues
from octoprint.server import printer, fileManager, slicingManager, eventManager, NO_CONTENT
from octoprint.server.util.flask import restricted_access, get_json_command_from_request
from octoprint.server.api import api
from octoprint.events import Events
import octoprint.filemanager
import octoprint.filemanager.util
import octoprint.filemanager.storage
import octoprint.slicing

import psutil


#~~ GCODE file handling


@api.route("/files", methods=["GET"])
def readGcodeFiles():
	filter = "filter" in request.values and request.values["recursive"] in valid_boolean_trues
	recursive = "recursive" in request.values and request.values["recursive"] in valid_boolean_trues

	files = _getFileList(FileDestinations.LOCAL, filter=filter, recursive=recursive)
	files.extend(_getFileList(FileDestinations.SDCARD))

	usage = psutil.disk_usage(settings().getBaseFolder("uploads"))
	return jsonify(files=files, free=usage.free, total=usage.total)


@api.route("/files/<string:origin>", methods=["GET"])
def readGcodeFilesForOrigin(origin):
	if origin not in [FileDestinations.LOCAL, FileDestinations.SDCARD]:
		return make_response("Unknown origin: %s" % origin, 404)

	recursive = False
	if "recursive" in request.values:
		recursive = request.values["recursive"] == 'true'

	files = _getFileList(origin, recursive=recursive)

	if origin == FileDestinations.LOCAL:
		usage = psutil.disk_usage(settings().getBaseFolder("uploads"))
		return jsonify(files=files, free=usage.free, total=usage.total)
	else:
		return jsonify(files=files)


def _getFileDetails(origin, path):
	files = _getFileList(origin, recursive=True)
	path = path.split('/')

	if len(path) == 1:
		# shortcut for files in the root folder
		name = path[0]
		for f in files:
			if f["name"] == name:
				return f

		return None

	node = files
	while path:
		segment = path.pop(0)
		for f in node:
			if not f["name"] == segment:
				# wrong name => next!
				continue

			if not path:
				# no path left and name matches => found it!
				return f

			if not f["type"] == "folder":
				# path left but not a folder => that doesn't work
				return None

			# we'll use this folder's children as the next iteration
			node = f["children"]
			break
		else:
			# nothing matched the name, we can't find it
			return None

	# nothing returned until now => not found
	return None


def _getFileList(origin, filter=None, recursive=False):
	if origin == FileDestinations.SDCARD:
		sdFileList = printer.get_sd_files()

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

		files = fileManager.list_files(origin, filter=filter_func, recursive=recursive)[origin].values()

		def analyse_recursively(files, path=None):
			if path is None:
				path = ""

			for file in files:
				file["origin"] = FileDestinations.LOCAL

				if file["type"] == "folder":
					file["children"] = analyse_recursively(file["children"].values(), path + file["name"] + "/")
				else:
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
							success += 1 if "success" in entry and entry["success"] else 0
							failure += 1 if "success" in entry and not entry["success"] else 0
							if not last or ("timestamp" in entry and "timestamp" in last and entry["timestamp"] > last["timestamp"]):
								last = entry
						if last:
							prints = dict(
								success=success,
								failure=failure,
								last=dict(
									success=last["success"],
									date=last["timestamp"]
								)
							)
							if "printTime" in last:
								prints["last"]["printTime"] = last["printTime"]
							file["prints"] = prints

					file.update({
						"refs": {
							"resource": url_for(".readGcodeFile", target=FileDestinations.LOCAL, filename=path + file["name"], _external=True),
							"download": url_for("index", _external=True) + "downloads/files/" + FileDestinations.LOCAL + "/" + path + file["name"]
						}
					})

			return files

		analyse_recursively(files)

	return files


def _verifyFileExists(origin, filename):
	if origin == FileDestinations.SDCARD:
		return filename in map(lambda x: x[0], printer.get_sd_files())
	else:
		return fileManager.file_exists(origin, filename)


def _verifyFolderExists(origin, foldername):
	if origin == FileDestinations.SDCARD:
		return False
	else:
		return fileManager.folder_exists(origin, foldername)


def _isBusy(target, path):
	currentOrigin, currentFilename = _getCurrentFile()
	if currentFilename is not None and currentOrigin == target and fileManager.file_in_path(FileDestinations.LOCAL, path, currentFilename) and (printer.is_printing() or printer.is_paused()):
		return True

	return any(target == x[0] and fileManager.file_in_path(FileDestinations.LOCAL, path, x[1]) for x in fileManager.get_busy_files())

@api.route("/files/<string:target>", methods=["POST"])
@restricted_access
def uploadGcodeFile(target):
	input_name = "file"
	input_upload_name = input_name + "." + settings().get(["server", "uploads", "nameSuffix"])
	input_upload_path = input_name + "." + settings().get(["server", "uploads", "pathSuffix"])
	if input_upload_name in request.values and input_upload_path in request.values:
		if not target in [FileDestinations.LOCAL, FileDestinations.SDCARD]:
			return make_response("Unknown target: %s" % target, 404)

		upload = octoprint.filemanager.util.DiskFileWrapper(request.values[input_upload_name], request.values[input_upload_path])

		# Store any additional user data the caller may have passed.
		userdata = None
		if "userdata" in request.values:
			import json
			try:
				userdata = json.loads(request.values["userdata"])
			except:
				return make_response("userdata contains invalid JSON", 400)

		if target == FileDestinations.SDCARD and not settings().getBoolean(["feature", "sdSupport"]):
			return make_response("SD card support is disabled", 404)

		sd = target == FileDestinations.SDCARD
		selectAfterUpload = "select" in request.values.keys() and request.values["select"] in valid_boolean_trues
		printAfterSelect = "print" in request.values.keys() and request.values["print"] in valid_boolean_trues

		if sd:
			# validate that all preconditions for SD upload are met before attempting it
			if not (printer.is_operational() and not (printer.is_printing() or printer.is_paused())):
				return make_response("Can not upload to SD card, printer is either not operational or already busy", 409)
			if not printer.is_sd_ready():
				return make_response("Can not upload to SD card, not yet initialized", 409)

		# determine current job
		currentPath = None
		currentFilename = None
		currentOrigin = None
		currentJob = printer.get_current_job()
		if currentJob is not None and "file" in currentJob.keys():
			currentJobFile = currentJob["file"]
			if currentJobFile is not None and "name" in currentJobFile.keys() and "origin" in currentJobFile.keys() and currentJobFile["name"] is not None and currentJobFile["origin"] is not None:
				currentPath, currentFilename = fileManager.sanitize(FileDestinations.LOCAL, currentJobFile["name"])
				currentOrigin = currentJobFile["origin"]

		# determine future filename of file to be uploaded, abort if it can't be uploaded
		try:
			# FileDestinations.LOCAL = should normally be target, but can't because SDCard handling isn't implemented yet
			futurePath, futureFilename = fileManager.sanitize(FileDestinations.LOCAL, upload.filename)
		except:
			futurePath = None
			futureFilename = None

		if futureFilename is None:
			return make_response("Can not upload file %s, wrong format?" % upload.filename, 415)

		if "path" in request.values and request.values["path"]:
			# FileDestinations.LOCAL = should normally be target, but can't because SDCard handling isn't implemented yet
			futurePath = fileManager.sanitize_path(FileDestinations.LOCAL, request.values["path"])

		# prohibit overwriting currently selected file while it's being printed
		if futurePath == currentPath and futureFilename == currentFilename and target == currentOrigin and (printer.is_printing() or printer.is_paused()):
			return make_response("Trying to overwrite file that is currently being printed: %s" % currentFilename, 409)

		def fileProcessingFinished(filename, absFilename, destination):
			"""
			Callback for when the file processing (upload, optional slicing, addition to analysis queue) has
			finished.

			Depending on the file's destination triggers either streaming to SD card or directly calls selectAndOrPrint.
			"""

			if destination == FileDestinations.SDCARD and octoprint.filemanager.valid_file_type(filename, "gcode"):
				return filename, printer.add_sd_file(filename, absFilename, selectAndOrPrint)
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
				printer.select_file(absFilename, destination == FileDestinations.SDCARD, printAfterSelect)

		# FileDestinations.LOCAL = should normally be target, but can't because SDCard handling isn't implemented yet
		futureFullPath = fileManager.join_path(FileDestinations.LOCAL, futurePath, futureFilename)

		try:
			added_file = fileManager.add_file(FileDestinations.LOCAL, futureFullPath, upload, allow_overwrite=True)
		except octoprint.filemanager.storage.StorageError as e:
			if e.code == octoprint.filemanager.storage.StorageError.INVALID_FILE:
				return make_response("Could not upload the file \"{}\", invalid type".format(upload.filename), 400)
			else:
				return make_response("Could not upload the file \"{}\"".format(upload.filename), 500)

		if octoprint.filemanager.valid_file_type(added_file, "stl"):
			filename = added_file
			done = True
		else:
			filename = fileProcessingFinished(added_file, fileManager.path_on_disk(FileDestinations.LOCAL, added_file), target)
			done = True

		if userdata is not None:
			# upload included userdata, add this now to the metadata
			fileManager.set_additional_metadata(FileDestinations.LOCAL, added_file, "userdata", userdata)

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
	elif "foldername" in request.values:
		foldername = request.values["foldername"]

		if not target in [FileDestinations.LOCAL]:
			return make_response("Unknown target: %s" % target, 400)

		futurePath, futureName = fileManager.sanitize(target, foldername)
		if not futureName or not futurePath:
			return make_response("Can't create a folder with an empty name", 400)

		futureFullPath = fileManager.join_path(target, futurePath, futureName)
		if octoprint.filemanager.valid_file_type(futureName):
			return make_response("Can't create a folder named %s, please try another name" % futureName, 409)

		try:
			fileManager.add_folder(target, futureFullPath)
		except octoprint.filemanager.storage.StorageError as e:
			if e.code == octoprint.filemanager.storage.StorageError.INVALID_DIRECTORY:
				return make_response("Could not create folder {}, invalid directory".format(futureName))
			else:
				return make_response("Could not create folder {}".format(futureName))
	else:
		return make_response("No file to upload and no folder to create", 400)

	return NO_CONTENT


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

	# valid file commands, dict mapping command name to mandatory parameters
	valid_commands = {
		"select": [],
		"slice": [],
		"copy": ["destination"],
		"move": ["destination"]
	}

	command, data, response = get_json_command_from_request(request, valid_commands)
	if response is not None:
		return response

	if command == "select":
		if not _verifyFileExists(target, filename):
			return make_response("File not found on '%s': %s" % (target, filename), 404)

		# selects/loads a file
		if not octoprint.filemanager.valid_file_type(filename, type="machinecode"):
			return make_response("Cannot select {filename} for printing, not a machinecode file".format(**locals()), 415)

		printAfterLoading = False
		if "print" in data.keys() and data["print"] in valid_boolean_trues:
			if not printer.is_operational():
				return make_response("Printer is not operational, cannot directly start printing", 409)
			printAfterLoading = True

		sd = False
		if target == FileDestinations.SDCARD:
			filenameToSelect = filename
			sd = True
		else:
			filenameToSelect = fileManager.path_on_disk(target, filename)
		printer.select_file(filenameToSelect, sd, printAfterLoading)

	elif command == "slice":
		if not _verifyFileExists(target, filename):
			return make_response("File not found on '%s': %s" % (target, filename), 404)

		try:
			if "slicer" in data:
				slicer = data["slicer"]
				del data["slicer"]
				slicer_instance = slicingManager.get_slicer(slicer)

			elif "cura" in slicingManager.registered_slicers:
				slicer = "cura"
				slicer_instance = slicingManager.get_slicer("cura")

			else:
				return make_response("Cannot slice {filename}, no slicer available".format(**locals()), 415)
		except octoprint.slicing.UnknownSlicer as e:
			return make_response("Slicer {slicer} is not available".format(slicer=e.slicer), 400)

		if not octoprint.filemanager.valid_file_type(filename, type="stl"):
			return make_response("Cannot slice {filename}, not an STL file".format(**locals()), 415)

		if slicer_instance.get_slicer_properties()["same_device"] and (printer.is_printing() or printer.is_paused()):
			# slicer runs on same device as OctoPrint, slicing while printing is hence disabled
			return make_response("Cannot slice on {slicer} while printing due to performance reasons".format(**locals()), 409)

		if "gcode" in data and data["gcode"]:
			gcode_name = data["gcode"]
			del data["gcode"]
		else:
			import os
			name, _ = os.path.splitext(filename)
			gcode_name = name + ".gco"

		if "path" in data and data["path"]:
			gcode_name = fileManager.join_path(target, data["path"], gcode_name)
		else:
			path, _ = fileManager.split_path(target, filename)
			if path:
				gcode_name = fileManager.join_path(target, path, gcode_name)

		# prohibit overwriting the file that is currently being printed
		currentOrigin, currentFilename = _getCurrentFile()
		if currentFilename == gcode_name and currentOrigin == target and (printer.is_printing() or printer.is_paused()):
			make_response("Trying to slice into file that is currently being printed: %s" % gcode_name, 409)

		if "profile" in data.keys() and data["profile"]:
			profile = data["profile"]
			del data["profile"]
		else:
			profile = None

		if "printerProfile" in data.keys() and data["printerProfile"]:
			printerProfile = data["printerProfile"]
			del data["printerProfile"]
		else:
			printerProfile = None

		if "position" in data.keys() and data["position"] and isinstance(data["position"], dict) and "x" in data["position"] and "y" in data["position"]:
			position = data["position"]
			del data["position"]
		else:
			position = None

		select_after_slicing = False
		if "select" in data.keys() and data["select"] in valid_boolean_trues:
			if not printer.is_operational():
				return make_response("Printer is not operational, cannot directly select for printing", 409)
			select_after_slicing = True

		print_after_slicing = False
		if "print" in data.keys() and data["print"] in valid_boolean_trues:
			if not printer.is_operational():
				return make_response("Printer is not operational, cannot directly start printing", 409)
			select_after_slicing = print_after_slicing = True

		override_keys = [k for k in data if k.startswith("profile.") and data[k] is not None]
		overrides = dict()
		for key in override_keys:
			overrides[key[len("profile."):]] = data[key]

		def slicing_done(target, gcode_name, select_after_slicing, print_after_slicing):
			if select_after_slicing or print_after_slicing:
				sd = False
				if target == FileDestinations.SDCARD:
					filenameToSelect = gcode_name
					sd = True
				else:
					filenameToSelect = fileManager.path_on_disk(target, gcode_name)
				printer.select_file(filenameToSelect, sd, print_after_slicing)

		try:
			fileManager.slice(slicer, target, filename, target, gcode_name,
			                  profile=profile,
			                  printer_profile_id=printerProfile,
			                  position=position,
			                  overrides=overrides,
			                  callback=slicing_done,
			                  callback_args=(target, gcode_name, select_after_slicing, print_after_slicing))
		except octoprint.slicing.UnknownProfile:
			return make_response("Profile {profile} doesn't exist".format(**locals()), 400)

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

	elif command == "copy" or command == "move":
		# Copy and move are only possible on local storage
		if not target in [FileDestinations.LOCAL]:
			return make_response("Unsupported target for {}: {}".format(command, target), 400)

		if not _verifyFileExists(target, filename) and not _verifyFolderExists(target, filename):
			return make_response("File/Folder not found on '%s': %s" % (target, filename), 404)

		destination = data["destination"]
		if _verifyFolderExists(target, destination):
			path, name = fileManager.split_path(target, filename)
			destination = fileManager.join_path(target, destination, name)

		if _verifyFileExists(target, destination) or _verifyFolderExists(target, destination):
			return make_response("File/Folder already exists: %s" % filename, 409)

		if command == "copy":
			if fileManager.file_exists(target, filename):
				fileManager.copy_file(target, filename, destination)
			elif fileManager.folder_exists(target, filename):
				fileManager.copy_folder(target, filename, destination)
		elif command == "move":
			if _isBusy(target, filename):
				return make_response("Trying to move a file/folder that is currently in use: %s" % filename, 409)

			# deselect the file if it's currently selected
			currentOrigin, currentFilename = _getCurrentFile()
			if currentFilename is not None and filename == currentFilename:
				printer.unselect_file()

			if fileManager.file_exists(target, filename):
				fileManager.move_file(target, filename, destination)
			elif fileManager.folder_exists(target, filename):
				fileManager.move_folder(target, filename, destination)

	return NO_CONTENT


@api.route("/files/<string:target>/<path:filename>", methods=["DELETE"])
@restricted_access
def deleteGcodeFile(filename, target):
	if not _verifyFileExists(target, filename) and not _verifyFolderExists(target, filename):
		return make_response("File/Folder not found on '%s': %s" % (target, filename), 404)

	if _verifyFileExists(target, filename):
		if not target in [FileDestinations.LOCAL, FileDestinations.SDCARD]:
			return make_response("Unknown target: %s" % target, 400)

		if _isBusy(target, filename):
			return make_response("Trying to delete a file that is currently in use: %s" % filename, 409)

		# deselect the file if it's currently selected
		currentOrigin, currentFilename = _getCurrentFile()
		if currentFilename is not None and currentOrigin == target and filename == currentFilename:
			printer.unselect_file()

		# delete it
		if target == FileDestinations.SDCARD:
			printer.delete_sd_file(filename)
		else:
			fileManager.remove_file(target, filename)

	elif _verifyFolderExists(target, filename):
		if not target in [FileDestinations.LOCAL]:
			return make_response("Unknown target: %s" % target, 400)

		if _isBusy(target, filename):
			return make_response("Trying to delete a folder that contains a file that is currently in use: %s" % filename, 409)

		# deselect the file if it's currently selected
		currentOrigin, currentFilename = _getCurrentFile()
		if currentFilename is not None and currentOrigin == target and fileManager.file_in_path(target, filename, currentFilename):
			printer.unselect_file()

		# delete it
		fileManager.remove_folder(target, filename)

	return NO_CONTENT

def _getCurrentFile():
	currentJob = printer.get_current_job()
	if currentJob is not None and "file" in currentJob.keys() and "name" in currentJob["file"] and "origin" in currentJob["file"]:
		return currentJob["file"]["origin"], currentJob["file"]["name"]
	else:
		return None, None


class WerkzeugFileWrapper(octoprint.filemanager.util.AbstractFileWrapper):
	"""
	A wrapper around a Werkzeug ``FileStorage`` object.

	Arguments:
	    file_obj (werkzeug.datastructures.FileStorage): The Werkzeug ``FileStorage`` instance to wrap.

	.. seealso::

	   `werkzeug.datastructures.FileStorage <http://werkzeug.pocoo.org/docs/0.10/datastructures/#werkzeug.datastructures.FileStorage>`_
	        The documentation of Werkzeug's ``FileStorage`` class.
	"""
	def __init__(self, file_obj):
		octoprint.filemanager.util.AbstractFileWrapper.__init__(self, file_obj.filename)
		self.file_obj = file_obj

	def save(self, path):
		"""
		Delegates to ``werkzeug.datastructures.FileStorage.save``
		"""
		self.file_obj.save(path)

	def stream(self):
		"""
		Returns ``werkzeug.datastructures.FileStorage.stream``
		"""
		return self.file_obj.stream
