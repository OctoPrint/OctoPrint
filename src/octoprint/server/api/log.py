# coding=utf-8
__author__ = "Marc Hannappel Salandora"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

import os
import datetime

from flask import request, jsonify, make_response, url_for
from werkzeug.utils import secure_filename

import octoprint.util as util
from octoprint.settings import settings, valid_boolean_trues

from octoprint.server import restricted_access, admin_permission
from octoprint.server.util import redirectToTornado
from octoprint.server.api import api

@api.route("/logs", methods=["GET"])
def getLogData():
	files = _getLogFiles()
	return jsonify(files=files)

@api.route("/logs/online/<filename>", methods=["GET"])
def onlineLog(filename):
	secure = os.path.join(settings().getBaseFolder("logs"), secure_filename(filename))
	if not os.path.exists(secure):
		return make_response("Unknown filename: %s" % filename, 404)
	
	file = open(secure, 'r')
	return jsonify(data=file.read())

@api.route("/logs/<filename>", methods=["GET"])
def downloadLog(filename):
	return redirectToTornado(request, url_for("index") + "downloads/logs/" + filename)


@api.route("/logs/<filename>", methods=["DELETE"])
@restricted_access
def deleteLog(filename):
	secure = os.path.join(settings().getBaseFolder("logs"), secure_filename(filename))
	if os.path.exists(secure):
			os.remove(secure)

	return getLogData()

def _getLogFiles():
	files = []
	basedir = settings().getBaseFolder("logs")
	for osFile in os.listdir(basedir):
		statResult = os.stat(os.path.join(basedir, osFile))
		files.append({
			"name": osFile,
			"size": util.getFormattedSize(statResult.st_size),
			"bytes": statResult.st_size,
			"date": util.getFormattedDateTime(datetime.datetime.fromtimestamp(statResult.st_ctime))
		})

	for file in files:
		file["url"] = url_for("index") + "downloads/logs/" + file["name"]

	return files

