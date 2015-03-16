# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

from flask import request, jsonify, make_response, url_for
from flask.exceptions import JSONBadRequest

from octoprint.server import slicingManager
from octoprint.server.util.flask import restricted_access
from octoprint.server.api import api, NO_CONTENT

from octoprint.settings import settings as s, valid_boolean_trues

from octoprint.slicing import SlicerNotConfigured


@api.route("/slicing", methods=["GET"])
def slicingListAll():
	default_slicer = s().get(["slicing", "defaultSlicer"])

	if "configured" in request.values and request.values["configured"] in valid_boolean_trues:
		slicers = slicingManager.configured_slicers
	else:
		slicers = slicingManager.registered_slicers

	result = dict()
	for slicer in slicers:
		slicer_impl = slicingManager.get_slicer(slicer, require_configured=False)
		result[slicer] = dict(
			key=slicer,
			displayName=slicer_impl.get_slicer_properties()["name"],
			default=default_slicer == slicer,
			configured = slicer_impl.is_slicer_configured(),
			profiles=_getSlicingProfilesData(slicer)
		)

	return jsonify(result)

@api.route("/slicing/<string:slicer>/profiles", methods=["GET"])
def slicingListSlicerProfiles(slicer):
	if not slicer in slicingManager.registered_slicers:
		return make_response("Unknown slicer {slicer}".format(**locals()), 404)

	configured = False
	if "configured" in request.values and request.values["configured"] in valid_boolean_trues:
		if not slicer in slicingManager.configured_slicers:
			return make_response("Unknown slicer {slicer}".format(**locals()), 404)
		configured = True

	return jsonify(_getSlicingProfilesData(slicer, require_configured=configured))

@api.route("/slicing/<string:slicer>/profiles/<string:name>", methods=["GET"])
def slicingGetSlicerProfile(slicer, name):
	if not slicer in slicingManager.registered_slicers:
		return make_response("Unknown slicer {slicer}".format(**locals()), 404)

	profile = slicingManager.load_profile(slicer, name)
	if not profile:
		return make_response("Profile not found", 404)

	result = _getSlicingProfileData(slicer, name, profile)
	result["data"] = profile.data
	return jsonify(result)

@api.route("/slicing/<string:slicer>/profiles/<string:name>", methods=["PUT"])
@restricted_access
def slicingAddSlicerProfile(slicer, name):
	if not slicer in slicingManager.registered_slicers:
		return make_response("Unknown slicer {slicer}".format(**locals()), 404)

	if not "application/json" in request.headers["Content-Type"]:
		return make_response("Expected content-type JSON", 400)

	try:
		json_data = request.json
	except JSONBadRequest:
		return make_response("Malformed JSON body in request", 400)

	data = dict()
	display_name = None
	description = None
	if "data" in json_data:
		data = json_data["data"]
	if "displayName" in json_data:
		display_name = json_data["displayName"]
	if "description" in json_data:
		description = json_data["description"]

	profile = slicingManager.save_profile(slicer, name, data, display_name=display_name, description=description)

	result = _getSlicingProfileData(slicer, name, profile)
	r = make_response(jsonify(result), 201)
	r.headers["Location"] = result["resource"]
	return r

@api.route("/slicing/<string:slicer>/profiles/<string:name>", methods=["PATCH"])
@restricted_access
def slicingPatchSlicerProfile(slicer, name):
	if not slicer in slicingManager.registered_slicers:
		return make_response("Unknown slicer {slicer}".format(**locals()), 404)

	if not "application/json" in request.headers["Content-Type"]:
		return make_response("Expected content-type JSON", 400)

	profile = slicingManager.load_profile(slicer, name)
	if not profile:
		return make_response("Profile not found", 404)

	try:
		json_data = request.json
	except JSONBadRequest:
		return make_response("Malformed JSON body in request", 400)

	data = dict()
	display_name = None
	description = None
	if "data" in json_data:
		data = json_data["data"]
	if "displayName" in json_data:
		display_name = json_data["displayName"]
	if "description" in json_data:
		description = json_data["description"]

	from octoprint.server.api import valid_boolean_trues
	if "default" in json_data and json_data["default"] in valid_boolean_trues:
		default_profiles = s().get(["slicing", "defaultProfiles"])
		if not default_profiles:
			default_profiles = dict()
		default_profiles[slicer] = name
		s().set(["slicing", "defaultProfiles"], default_profiles)
		s().save(force=True)

	slicingManager.save_profile(slicer, name, profile, overrides=data, display_name=display_name, description=description)
	return NO_CONTENT

@api.route("/slicing/<string:slicer>/profiles/<string:name>", methods=["DELETE"])
@restricted_access
def slicingDelSlicerProfile(slicer, name):
	if not slicer in slicingManager.registered_slicers:
		return make_response("Unknown slicer {slicer}".format(**locals()), 404)

	slicingManager.delete_profile(slicer, name)
	return NO_CONTENT

def _getSlicingProfilesData(slicer, require_configured=False):
	try:
		profiles = slicingManager.all_profiles(slicer, require_configured=require_configured)
	except SlicerNotConfigured:
		return dict()

	result = dict()
	for name, profile in profiles.items():
		result[name] = _getSlicingProfileData(slicer, name, profile)
	return result

def _getSlicingProfileData(slicer, name, profile):
	defaultProfiles = s().get(["slicing", "defaultProfiles"])
	result = dict(
		key=name,
		default=defaultProfiles and slicer in defaultProfiles and defaultProfiles[slicer] == name,
		resource=url_for(".slicingGetSlicerProfile", slicer=slicer, name=name, _external=True)
	)
	if profile.display_name is not None:
		result["displayName"] = profile.display_name
	if profile.description is not None:
		result["description"] = profile.description
	return result