# coding=utf-8
__author__ = "Marc Hannappel Salandora"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

import os

from flask import request, jsonify, make_response, url_for
from werkzeug.utils import secure_filename

from octoprint.settings import settings

from octoprint.server import restricted_access
from octoprint.server.util import redirectToTornado
from octoprint.server.api import api


@api.route("/logs", methods=["GET"])
def getLogData():
	files = _getLogFiles()
	return jsonify(files=files)


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
			"size": statResult.st_size,
			"bytes": statResult.st_size,
			"date": int(statResult.st_mtime),
			"url": url_for("index") + "downloads/logs/" + osFile
		})

	return files

