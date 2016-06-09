# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

from flask import request, jsonify, make_response, url_for
from werkzeug.exceptions import BadRequest

from octoprint.server import slicingManager
from octoprint.server.util.flask import restricted_access
from octoprint.server.api import api, NO_CONTENT

from octoprint.settings import settings as s, valid_boolean_trues

from octoprint.slicing import UnknownSlicer, SlicerNotConfigured, ProfileAlreadyExists, UnknownProfile, CouldNotDeleteProfile


@api.route("/slicing", methods=["GET"])
def slicingListAll():
	default_slicer = s().get(["slicing", "defaultSlicer"])

	if "configured" in request.values and request.values["configured"] in valid_boolean_trues:
		slicers = slicingManager.configured_slicers
	else:
		slicers = slicingManager.registered_slicers

	result = dict()
	for slicer in slicers:
		try:
			slicer_impl = slicingManager.get_slicer(slicer, require_configured=False)
			result[slicer] = dict(
				key=slicer,
				displayName=slicer_impl.get_slicer_properties()["name"],
				default=default_slicer == slicer,
				configured = slicer_impl.is_slicer_configured(),
				profiles=_getSlicingProfilesData(slicer)
			)
		except (UnknownSlicer, SlicerNotConfigured):
			# this should never happen
			pass

	return jsonify(result)

@api.route("/slicing/<string:slicer>/profiles", methods=["GET"])
def slicingListSlicerProfiles(slicer):
	configured = False
	if "configured" in request.values and request.values["configured"] in valid_boolean_trues:
		configured = True

	try:
		return jsonify(_getSlicingProfilesData(slicer, require_configured=configured))
	except (UnknownSlicer, SlicerNotConfigured):
		return make_response("Unknown slicer {slicer}".format(**locals()), 404)

@api.route("/slicing/<string:slicer>/profiles/<string:name>", methods=["GET"])
def slicingGetSlicerProfile(slicer, name):
	try:
		profile = slicingManager.load_profile(slicer, name, require_configured=False)
	except UnknownSlicer:
		return make_response("Unknown slicer {slicer}".format(**locals()), 404)
	except UnknownProfile:
		return make_response("Profile not found", 404)

	result = _getSlicingProfileData(slicer, name, profile)
	result["data"] = profile.data
	return jsonify(result)

@api.route("/slicing/<string:slicer>/profiles/<string:name>", methods=["PUT"])
@restricted_access
def slicingAddSlicerProfile(slicer, name):
	if not "application/json" in request.headers["Content-Type"]:
		return make_response("Expected content-type JSON", 400)

	try:
		json_data = request.json
	except BadRequest:
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

	try:
		profile = slicingManager.save_profile(slicer, name, data,
		                                      allow_overwrite=True, display_name=display_name, description=description)
	except UnknownSlicer:
		return make_response("Unknown slicer {slicer}".format(**locals()), 404)

	result = _getSlicingProfileData(slicer, name, profile)
	r = make_response(jsonify(result), 201)
	r.headers["Location"] = result["resource"]
	return r

@api.route("/slicing/<string:slicer>/profiles/<string:name>", methods=["PATCH"])
@restricted_access
def slicingPatchSlicerProfile(slicer, name):
	if not "application/json" in request.headers["Content-Type"]:
		return make_response("Expected content-type JSON", 400)

	try:
		profile = slicingManager.load_profile(slicer, name, require_configured=False)
	except UnknownSlicer:
		return make_response("Unknown slicer {slicer}".format(**locals()), 404)
	except UnknownProfile:
		return make_response("Profile {name} for slicer {slicer} not found".format(**locals()), 404)

	try:
		json_data = request.json
	except BadRequest:
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

	saved_profile = slicingManager.save_profile(slicer, name, profile,
	                                            allow_overwrite=True, overrides=data, display_name=display_name, description=description)
	return jsonify(_getSlicingProfileData(slicer, name, saved_profile))

@api.route("/slicing/<string:slicer>/profiles/<string:name>", methods=["DELETE"])
@restricted_access
def slicingDelSlicerProfile(slicer, name):
	try:
		slicingManager.delete_profile(slicer, name)
	except UnknownSlicer:
		return make_response("Unknown slicer {slicer}".format(**locals()), 404)
	except CouldNotDeleteProfile as e:
		return make_response("Could not delete profile {profile} for slicer {slicer}: {cause}".format(profile=name, slicer=slicer, cause=str(e.cause)), 500)

	return NO_CONTENT

def _getSlicingProfilesData(slicer, require_configured=False):
	profiles = slicingManager.all_profiles(slicer, require_configured=require_configured)

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
