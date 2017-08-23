# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import os
import threading
import logging

from flask import request, jsonify, url_for, make_response
from werkzeug.utils import secure_filename

import octoprint.timelapse
import octoprint.util as util
from octoprint.settings import settings, valid_boolean_trues

from octoprint.server import admin_permission, printer
from octoprint.server.util.flask import redirect_to_tornado, restricted_access, get_json_command_from_request, with_revalidation_checking
from octoprint.server.api import api

from octoprint.server import NO_CONTENT


#~~ timelapse handling

_timelapse_cache_finished = []
_timelapse_cache_finished_lastmodified = None
_timelapse_cache_unrendered = []
_timelapse_cache_unrendered_lastmodified = None
_timelapse_cache_mutex = threading.RLock()

def _config_for_timelapse(timelapse):
	if timelapse is not None and isinstance(timelapse, octoprint.timelapse.ZTimelapse):
		return dict(type="zchange",
		            postRoll=timelapse.post_roll,
		            fps=timelapse.fps,
		            retractionZHop=timelapse.retraction_zhop)
	elif timelapse is not None and isinstance(timelapse, octoprint.timelapse.TimedTimelapse):
		return dict(type="timed",
		            postRoll=timelapse.post_roll,
		            fps=timelapse.fps,
		            interval=timelapse.interval,
		            capturePostRoll=timelapse.capture_post_roll)
	else:
		return dict(type="off")

def _lastmodified(unrendered):
	lm_finished = octoprint.timelapse.last_modified_finished()
	if unrendered:
		lm_unrendered = octoprint.timelapse.last_modified_unrendered()

		if lm_finished is None or lm_unrendered is None:
			return None
		return max(lm_finished, lm_unrendered)
	return lm_finished

def _etag(unrendered, lm=None):
	if lm is None:
		lm = _lastmodified(unrendered)

	timelapse = octoprint.timelapse.current
	config = _config_for_timelapse(timelapse)

	import hashlib
	hash = hashlib.sha1()
	hash.update(str(lm))
	hash.update(repr(config))

	return hash.hexdigest()

@api.route("/timelapse", methods=["GET"])
@with_revalidation_checking(etag_factory=lambda lm=None: _etag(request.values.get("unrendered", "false") in valid_boolean_trues, lm=lm),
                            lastmodified_factory=lambda: _lastmodified(request.values.get("unrendered", "false") in valid_boolean_trues),
                            unless=lambda: request.values.get("force", "false") in valid_boolean_trues)
def getTimelapseData():
	timelapse = octoprint.timelapse.current
	config = _config_for_timelapse(timelapse)

	force = request.values.get("force", "false") in valid_boolean_trues
	unrendered = request.values.get("unrendered", "false") in valid_boolean_trues

	global _timelapse_cache_finished_lastmodified, _timelapse_cache_finished, _timelapse_cache_unrendered_lastmodified, _timelapse_cache_unrendered
	with _timelapse_cache_mutex:
		current_lastmodified_finished = octoprint.timelapse.last_modified_finished()
		current_lastmodified_unrendered = octoprint.timelapse.last_modified_unrendered()

		if not force and _timelapse_cache_finished_lastmodified == current_lastmodified_finished:
			files = _timelapse_cache_finished
		else:
			files = octoprint.timelapse.get_finished_timelapses()
			_timelapse_cache_finished = files
			_timelapse_cache_finished_lastmodified = current_lastmodified_finished

		unrendered_files = []
		if unrendered:
			if not force and _timelapse_cache_unrendered_lastmodified == current_lastmodified_unrendered:
				unrendered_files = _timelapse_cache_unrendered
			else:
				unrendered_files = octoprint.timelapse.get_unrendered_timelapses()
				_timelapse_cache_unrendered = unrendered_files
				_timelapse_cache_unrendered_lastmodified = current_lastmodified_unrendered

	finished_list = []
	for f in files:
		output = dict(f)
		output["url"] = url_for("index") + "downloads/timelapse/" + f["name"]
		finished_list.append(output)

	result = dict(config=config,
	              files=finished_list)

	if unrendered:
		result.update(unrendered=unrendered_files)

	return jsonify(result)


@api.route("/timelapse/<filename>", methods=["GET"])
def downloadTimelapse(filename):
	return redirect_to_tornado(request, url_for("index") + "downloads/timelapse/" + filename)


@api.route("/timelapse/<filename>", methods=["DELETE"])
@restricted_access
def deleteTimelapse(filename):
	if util.is_allowed_file(filename, ["mpg", "mpeg", "mp4"]):
		timelapse_folder = settings().getBaseFolder("timelapse")
		full_path = os.path.realpath(os.path.join(timelapse_folder, filename))
		if full_path.startswith(timelapse_folder) and os.path.exists(full_path):
			try:
				os.remove(full_path)
			except Exception as ex:
				logging.getLogger(__file__).exception("Error deleting timelapse file {}".format(full_path))
				return make_response("Unexpected error: {}".format(ex), 500)

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
			try:
				interval = int(data["interval"])
			except ValueError:
				return make_response("Invalid value for interval: %r" % data["interval"], 400)
			else:
				if interval > 0:
					config["options"]["interval"] = interval
				else:
					return make_response("Invalid value for interval: %d" % interval, 400)

		if "capturePostRoll" in data:
			try:
				capturePostRoll = bool(data["capturePostRoll"])
			except ValueError:
				return make_response("Invalid value for capturePostRoll: %r" % data["capturePostRoll"], 400)
			else:
				if capturePostRoll >= 0:
					config["options"]["capturePostRoll"] = capturePostRoll
				else:
					return make_response("Invalid value for capturePostRoll: %d" % capturePostRoll, 400)

		if "retractionZHop" in data:
			try:
				retractionZHop = float(data["retractionZHop"])
			except ValueError:
				return make_response("Invalid value for retraction Z-Hop: %r" % data["retractionZHop"], 400)
			else:
				if retractionZHop >= 0:
					config["options"]["retractionZHop"] = retractionZHop
				else:
					return make_response("Invalid value for retraction Z-Hop: %d" % retractionZHop, 400)


		if admin_permission.can() and "save" in data and data["save"] in valid_boolean_trues:
			octoprint.timelapse.configure_timelapse(config, True)
		else:
			octoprint.timelapse.configure_timelapse(config)

	return getTimelapseData()

