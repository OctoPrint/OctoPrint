# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

import logging

from flask import Blueprint, request, jsonify, abort

from octoprint.server import printer, gcodeManager, SUCCESS
from octoprint.settings import settings, valid_boolean_trues
from octoprint.filemanager.destinations import FileDestinations
import octoprint.gcodefiles as gcodefiles

api = Blueprint("api", __name__)

#-- very simple api routines
@api.route("/load", methods=["POST"])
def apiLoad():
	logger = logging.getLogger(__name__)

	if not settings().get(["api", "enabled"]):
		abort(401)

	if not "apikey" in request.values.keys():
		abort(401)

	if request.values["apikey"] != settings().get(["api", "key"]):
		abort(403)

	if not "file" in request.files.keys():
		abort(400)

	# Perform an upload
	file = request.files["file"]
	if not gcodefiles.isGcodeFileName(file.filename):
		abort(400)

	destination = FileDestinations.LOCAL
	filename, done = gcodeManager.addFile(file, destination)
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

@api.route("/state", methods=["GET"])
def apiPrinterState():
	if not settings().get(["api", "enabled"]):
		abort(401)

	if not "apikey" in request.values.keys():
		abort(401)

	if request.values["apikey"] != settings().get(["api", "key"]):
		abort(403)

	currentData = printer.getCurrentData()
	currentData.update({
	"temperatures": printer.getCurrentTemperatures()
	})
	return jsonify(currentData)

