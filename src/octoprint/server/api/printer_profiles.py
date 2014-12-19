# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import copy

from flask import jsonify, make_response, request, url_for

from octoprint.server.api import api, NO_CONTENT
from octoprint.server.util.flask import restricted_access
from octoprint.util import dict_merge

from octoprint.server import printerProfileManager


@api.route("/printerprofiles", methods=["GET"])
def printerProfilesList():
	all_profiles = printerProfileManager.get_all()
	return jsonify(dict(profiles=_convert_profiles(all_profiles)))

@api.route("/printerprofiles", methods=["POST"])
@restricted_access
def printerProfilesAdd():
	if not "application/json" in request.headers["Content-Type"]:
		return None, None, make_response("Expected content-type JSON", 400)

	json_data = request.json
	if not "profile" in json_data:
		return None, None, make_response("No profile included in request", 400)

	base_profile = printerProfileManager.get_default()
	if "basedOn" in json_data and isinstance(json_data["basedOn"], basestring):
		other_profile = printerProfileManager.get(json_data["basedOn"])
		if other_profile is not None:
			base_profile = other_profile

	if "id" in base_profile:
		del base_profile["id"]
	if "name" in base_profile:
		del base_profile["name"]
	profile = dict_merge(base_profile, json_data["profile"])
	if not _validate_profile(profile):
		return None, None, make_response("Profile is invalid, missing obligatory values", 400)

	return _overwrite_profile(profile)

@api.route("/printerprofiles/<string:identifier>", methods=["GET"])
def printerProfilesGet(identifier):
	profile = printerProfileManager.get(identifier)
	if profile is None:
		make_response("Unknown profile: %s" % identifier, 404)
	return jsonify(_convert_profile(profile))

@api.route("/printerprofiles/<string:identifier>", methods=["DELETE"])
@restricted_access
def printerProfilesDelete(identifier):
	printerProfileManager.remove(identifier)
	return NO_CONTENT

@api.route("/printerprofiles/<string:identifier>", methods=["PATCH"])
@restricted_access
def printerProfilesUpdate(identifier):
	if not "application/json" in request.headers["Content-Type"]:
		return None, None, make_response("Expected content-type JSON", 400)

	json_data = request.json
	if not "profile" in json_data:
		make_response("No profile included in request", 400)

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
	if not _validate_profile(new_profile):
		make_response("Combined profile is invalid, missing obligatory values", 400)

	try:
		saved_profile = printerProfileManager.save(new_profile, allow_overwrite=True, make_default=make_default)
	except Exception as e:
		make_response("Could not save profile: %s" % e.message)

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

def _validate_profile(profile):
	if not "name" in profile \
			and "volume" in profile \
			and "width" in profile["volume"] \
			and "depth" in profile["volume"] \
			and "height" in profile["volume"] \
			and "formFactor" in profile["volume"] \
			and "heatedBed" in profile \
			and "extruder" in profile \
			and "count" in profile["extruder"] \
			and "offsets" in profile["extruder"] \
			and len(profile["extruder"]["offsets"]) == profile["extruder"]["count"]:
		return False

	for dimension in ("width", "depth", "height"):
		try:
			profile["volume"][dimension] = float(profile["volume"][dimension])
		except:
			return False

	if not profile["volume"]["formFactor"] in ("rectangular", "circular"):
		return False

	try:
		profile["heatedBed"] = bool(profile["heatedBed"])
	except:
		return False

	try:
		profile["extruder"]["count"] = int(profile["extruder"]["count"])
	except:
		return False

	converted_offsets = []
	for offset in profile["extruder"]["offsets"]:
		try:
			converted_offsets.append((float(offset[0]), float(offset[1])))
		except:
			return False
	profile["extruder"]["offsets"] = converted_offsets

	return True

def _overwrite_profile(profile):
	if not "id" in profile and not "name" in profile:
		return None, None, make_response("Profile must contain either id or name")
	elif not "name" in profile:
		return None, None, make_response("Profile must contain a name")

	try:
		saved_profile = printerProfileManager.save(profile, allow_overwrite=False)
	except Exception as e:
		return None, None, make_response("Could not save profile: %s" % e.message)

	return jsonify(dict(profile=_convert_profile(saved_profile)))
