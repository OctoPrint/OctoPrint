# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import copy

from flask import jsonify, make_response, request, url_for
from werkzeug.exceptions import BadRequest

from octoprint.server.api import api, NO_CONTENT
from octoprint.server.util.flask import restricted_access
from octoprint.util import dict_merge

from octoprint.server import printerProfileManager
from octoprint.printer.profile import InvalidProfileError, CouldNotOverwriteError, SaveError


@api.route("/printerprofiles", methods=["GET"])
def printerProfilesList():
	all_profiles = printerProfileManager.get_all()
	return jsonify(dict(profiles=_convert_profiles(all_profiles)))

@api.route("/printerprofiles", methods=["POST"])
@restricted_access
def printerProfilesAdd():
	if not "application/json" in request.headers["Content-Type"]:
		return make_response("Expected content-type JSON", 400)

	try:
		json_data = request.json
	except BadRequest:
		return make_response("Malformed JSON body in request", 400)

	if not "profile" in json_data:
		return make_response("No profile included in request", 400)

	base_profile = printerProfileManager.get_default()
	if "basedOn" in json_data and isinstance(json_data["basedOn"], basestring):
		other_profile = printerProfileManager.get(json_data["basedOn"])
		if other_profile is not None:
			base_profile = other_profile

	if "id" in base_profile:
		del base_profile["id"]
	if "name" in base_profile:
		del base_profile["name"]
	if "default" in base_profile:
		del base_profile["default"]

	new_profile = json_data["profile"]
	make_default = False
	if "default" in new_profile:
		make_default = True
		del new_profile["default"]

	profile = dict_merge(base_profile, new_profile)
	try:
		saved_profile = printerProfileManager.save(profile, allow_overwrite=False, make_default=make_default)
	except InvalidProfileError:
		return make_response("Profile is invalid", 400)
	except CouldNotOverwriteError:
		return make_response("Profile already exists and overwriting was not allowed", 400)
	except Exception as e:
		return make_response("Could not save profile: %s" % str(e), 500)
	else:
		return jsonify(dict(profile=_convert_profile(saved_profile)))

@api.route("/printerprofiles/<string:identifier>", methods=["GET"])
def printerProfilesGet(identifier):
	profile = printerProfileManager.get(identifier)
	if profile is None:
		return make_response("Unknown profile: %s" % identifier, 404)
	else:
		return jsonify(_convert_profile(profile))

@api.route("/printerprofiles/<string:identifier>", methods=["DELETE"])
@restricted_access
def printerProfilesDelete(identifier):
	if printerProfileManager.get_current_or_default()["id"] == identifier:
		return make_response("Cannot delete currently selected profile: %s" % identifier, 409)
	printerProfileManager.remove(identifier)
	return NO_CONTENT

@api.route("/printerprofiles/<string:identifier>", methods=["PATCH"])
@restricted_access
def printerProfilesUpdate(identifier):
	if not "application/json" in request.headers["Content-Type"]:
		return make_response("Expected content-type JSON", 400)

	try:
		json_data = request.json
	except BadRequest:
		return make_response("Malformed JSON body in request", 400)

	if not "profile" in json_data:
		return make_response("No profile included in request", 400)

	profile = printerProfileManager.get(identifier)
	if profile is None:
		profile = printerProfileManager.get_default()

	new_profile = json_data["profile"]
	new_profile = dict_merge(profile, new_profile)

	make_default = False
	if "default" in new_profile:
		make_default = True
		del new_profile["default"]

	new_profile["id"] = identifier

	try:
		saved_profile = printerProfileManager.save(new_profile, allow_overwrite=True, make_default=make_default)
	except InvalidProfileError:
		return make_response("Profile is invalid", 400)
	except CouldNotOverwriteError:
		return make_response("Profile already exists and overwriting was not allowed", 400)
	except Exception as e:
		return make_response("Could not save profile: %s" % str(e), 500)
	else:
		return jsonify(dict(profile=_convert_profile(saved_profile)))

def _convert_profiles(profiles):
	result = dict()
	for identifier, profile in profiles.items():
		result[identifier] = _convert_profile(profile)
	return result

def _convert_profile(profile):
	default = printerProfileManager.get_default()["id"]
	current = printerProfileManager.get_current_or_default()["id"]

	converted = copy.deepcopy(profile)
	converted["resource"] = url_for(".printerProfilesGet", identifier=profile["id"], _external=True)
	converted["default"] = (profile["id"] == default)
	converted["current"] = (profile["id"] == current)
	return converted
