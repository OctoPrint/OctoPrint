# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

import os

from flask import request, jsonify, url_for
from werkzeug.utils import secure_filename

import octoprint.timelapse
import octoprint.util as util
from octoprint.settings import settings, valid_boolean_trues

from octoprint.server import restricted_access, admin_permission
from octoprint.server.util import redirectToTornado
from octoprint.server.api import api


#~~ timelapse handling


@api.route("/timelapse", methods=["GET"])
def getTimelapseData():
	timelapse = octoprint.timelapse.current

	config = {"type": "off"}
	if timelapse is not None and isinstance(timelapse, octoprint.timelapse.ZTimelapse):
		config["type"] = "zchange"
		config["postRoll"] = timelapse.postRoll()
	elif timelapse is not None and isinstance(timelapse, octoprint.timelapse.TimedTimelapse):
		config["type"] = "timed"
		config["postRoll"] = timelapse.postRoll()
		config.update({
			"interval": timelapse.interval()
		})

	files = octoprint.timelapse.getFinishedTimelapses()
	for file in files:
		file["url"] = url_for("index") + "downloads/timelapse/" + file["name"]

	return jsonify({
		"config": config,
		"files": files
	})


@api.route("/timelapse/<filename>", methods=["GET"])
def downloadTimelapse(filename):
	return redirectToTornado(request, url_for("index") + "downloads/timelapse/" + filename)


@api.route("/timelapse/<filename>", methods=["DELETE"])
@restricted_access
def deleteTimelapse(filename):
	if util.isAllowedFile(filename, {"mpg"}):
		secure = os.path.join(settings().getBaseFolder("timelapse"), secure_filename(filename))
		if os.path.exists(secure):
			os.remove(secure)
	return getTimelapseData()


@api.route("/timelapse", methods=["POST"])
@restricted_access
def setTimelapseConfig():
	if "type" in request.values:
		config = {
			"type": request.values["type"],
			"postRoll": 0,
			"options": {}
		}


		if "postRoll" in request.values:
			try:
				config["postRoll"] = int(request.values["postRoll"])
			except ValueError:
				pass

		if "interval" in request.values:
			interval = 10
			try:
				interval = int(request.values["interval"])
			except ValueError:
				pass

			config["options"] = {
				"interval": interval
			}

		if admin_permission.can() and "save" in request.values and request.values["save"] in valid_boolean_trues:
			octoprint.timelapse.configureTimelapse(config, True)
		else:
			octoprint.timelapse.configureTimelapse(config)

	return getTimelapseData()

