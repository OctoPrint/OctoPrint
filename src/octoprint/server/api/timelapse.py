# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import os

from flask import request, jsonify, url_for, make_response
from werkzeug.utils import secure_filename

import octoprint.timelapse
import octoprint.util as util
from octoprint.settings import settings, valid_boolean_trues

from octoprint.server import admin_permission
from octoprint.server.util.flask import redirect_to_tornado, restricted_access
from octoprint.server.api import api


#~~ timelapse handling


@api.route("/timelapse", methods=["GET"])
def getTimelapseData():
	timelapse = octoprint.timelapse.current

	config = {"type": "off"}
	if timelapse is not None and isinstance(timelapse, octoprint.timelapse.ZTimelapse):
		config["type"] = "zchange"
		config["postRoll"] = timelapse.post_roll
		config["fps"] = timelapse.fps
	elif timelapse is not None and isinstance(timelapse, octoprint.timelapse.TimedTimelapse):
		config["type"] = "timed"
		config["postRoll"] = timelapse.post_roll
		config["fps"] = timelapse.fps
		config.update({
			"interval": timelapse.interval
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
	return redirect_to_tornado(request, url_for("index") + "downloads/timelapse/" + filename)


@api.route("/timelapse/<filename>", methods=["DELETE"])
@restricted_access
def deleteTimelapse(filename):
	if util.is_allowed_file(filename, {"mpg"}):
		timelapse_folder = settings().getBaseFolder("timelapse")
		full_path = os.path.realpath(os.path.join(timelapse_folder, filename))
		if full_path.startswith(timelapse_folder) and os.path.exists(full_path):
			os.remove(full_path)
	return getTimelapseData()


@api.route("/timelapse", methods=["POST"])
@restricted_access
def setTimelapseConfig():
	data = request.values
	if hasattr(request, "json") and request.json:
		data = request.json

	if "type" in data:
		config = {
			"type": data["type"],
			"postRoll": 0,
			"fps": 25,
			"options": {}
		}

		if "postRoll" in data:
			try:
				postRoll = int(data["postRoll"])
			except ValueError:
				return make_response("Invalid value for postRoll: %r" % data["postRoll"], 400)
			else:
				if postRoll >= 0:
					config["postRoll"] = postRoll
				else:
					return make_response("Invalid value for postRoll: %d" % postRoll, 400)

		if "fps" in data:
			try:
				fps = int(data["fps"])
			except ValueError:
				return make_response("Invalid value for fps: %r" % data["fps"], 400)
			else:
				if fps > 0:
					config["fps"] = fps
				else:
					return make_response("Invalid value for fps: %d" % fps, 400)

		if "interval" in data:
			config["options"] = {
				"interval": 10
			}

			try:
				interval = int(data["interval"])
			except ValueError:
				return make_response("Invalid value for interval: %r" % data["interval"])
			else:
				if interval > 0:
					config["options"]["interval"] = interval
				else:
					return make_response("Invalid value for interval: %d" % interval)

		if admin_permission.can() and "save" in data and data["save"] in valid_boolean_trues:
			octoprint.timelapse.configureTimelapse(config, True)
		else:
			octoprint.timelapse.configureTimelapse(config)

	return getTimelapseData()

