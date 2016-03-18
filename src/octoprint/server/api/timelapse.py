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

from octoprint.server import admin_permission, printer
from octoprint.server.util.flask import redirect_to_tornado, restricted_access, get_json_command_from_request
from octoprint.server.api import api

from octoprint.server import NO_CONTENT


#~~ timelapse handling


@api.route("/timelapse", methods=["GET"])
def getTimelapseData():
	timelapse = octoprint.timelapse.current

	if timelapse is not None and isinstance(timelapse, octoprint.timelapse.ZTimelapse):
		config = dict(type="zchange",
		              postRoll=timelapse.post_roll,
		              fps=timelapse.fps,
		              retractionZHop=timelapse.retraction_zhop)
	elif timelapse is not None and isinstance(timelapse, octoprint.timelapse.TimedTimelapse):
		config = dict(type="timed",
		              postRoll=timelapse.post_roll,
		              fps=timelapse.fps,
		              interval=timelapse.interval)
	else:
		config = dict(type="off")

	files = octoprint.timelapse.get_finished_timelapses()
	for f in files:
		f["url"] = url_for("index") + "downloads/timelapse/" + f["name"]

	result = dict(config=config,
	              files=files)

	if "unrendered" in request.values and request.values["unrendered"] in valid_boolean_trues:
		result.update(unrendered=octoprint.timelapse.get_unrendered_timelapses())

	return jsonify(result)


@api.route("/timelapse/<filename>", methods=["GET"])
def downloadTimelapse(filename):
	return redirect_to_tornado(request, url_for("index") + "downloads/timelapse/" + filename)


@api.route("/timelapse/<filename>", methods=["DELETE"])
@restricted_access
def deleteTimelapse(filename):
	if util.is_allowed_file(filename, ["mpg"]):
		timelapse_folder = settings().getBaseFolder("timelapse")
		full_path = os.path.realpath(os.path.join(timelapse_folder, filename))
		if full_path.startswith(timelapse_folder) and os.path.exists(full_path):
			os.remove(full_path)
	return getTimelapseData()


@api.route("/timelapse/unrendered/<name>", methods=["DELETE"])
@restricted_access
def deleteUnrenderedTimelapse(name):
	octoprint.timelapse.delete_unrendered_timelapse(name)
	return NO_CONTENT


@api.route("/timelapse/unrendered/<name>", methods=["POST"])
@restricted_access
def processUnrenderedTimelapseCommand(name):
	# valid file commands, dict mapping command name to mandatory parameters
	valid_commands = {
		"render": []
	}

	command, data, response = get_json_command_from_request(request, valid_commands)
	if response is not None:
		return response

	if command == "render":
		if printer.is_printing() or printer.is_paused():
			return make_response("Printer is currently printing, cannot render timelapse", 409)
		octoprint.timelapse.render_unrendered_timelapse(name)

	return NO_CONTENT


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

		if "retractionZHop" in request.values:
                        config["options"] = {
                                "retractionZHop": 0
                        }

                        try:
                                retractionZHop = float(request.values["retractionZHop"])
                        except ValueError:
                                return make_response("Invalid value for retraction Z-Hop: %r" % request.values["retractionZHop"])
                        else:
                                if retractionZHop > 0:
                                        config["options"]["retractionZHop"] = retractionZHop
                                else:
                                        return make_response("Invalid value for retraction Z-Hop: %d" % retractionZHop)

		if admin_permission.can() and "save" in data and data["save"] in valid_boolean_trues:
			octoprint.timelapse.configure_timelapse(config, True)
		else:
			octoprint.timelapse.configure_timelapse(config)

	return getTimelapseData()

