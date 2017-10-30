# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

from flask import request, jsonify, make_response, url_for
from werkzeug.exceptions import BadRequest

from octoprint.server import slicingManager
from octoprint.server.util.flask import restricted_access, with_revalidation_checking
from octoprint.server.api import api, NO_CONTENT

from octoprint.settings import settings as s, valid_boolean_trues

from octoprint.slicing import UnknownSlicer, SlicerNotConfigured, ProfileAlreadyExists, UnknownProfile, CouldNotDeleteProfile


_DATA_FORMAT_VERSION = "v2"


def _lastmodified(configured):
	if configured:
		slicers = slicingManager.configured_slicers
	else:
		slicers = slicingManager.registered_slicers

	lms = [0]
	for slicer in slicers:
		lms.append(slicingManager.profiles_last_modified(slicer))

	return max(lms)


def _etag(configured, lm=None):
	if lm is None:
		lm = _lastmodified(configured)

	import hashlib
	hash = hashlib.sha1()
	hash.update(str(lm))

	if configured:
		slicers = slicingManager.configured_slicers
	else:
		slicers = slicingManager.registered_slicers

	default_slicer = s().get(["slicing", "defaultSlicer"])

	for slicer in sorted(slicers):
		slicer_impl = slicingManager.get_slicer(slicer, require_configured=False)
		hash.update(slicer)
		hash.update(str(slicer_impl.is_slicer_configured()))
		hash.update(str(slicer == default_slicer))
	
	hash.update(_DATA_FORMAT_VERSION) # increment version if we change the API format

	return hash.hexdigest()


@api.route("/slicing", methods=["GET"])
@with_revalidation_checking(etag_factory=lambda lm=None: _etag(request.values.get("configured", "false") in valid_boolean_trues, lm=lm),
                            lastmodified_factory=lambda: _lastmodified(request.values.get("configured", "false") in valid_boolean_trues),
                            unless=lambda: request.values.get("force", "false") in valid_boolean_trues)
def slicingListAll():
	from octoprint.filemanager import get_extensions

	default_slicer = s().get(["slicing", "defaultSlicer"])

	if "configured" in request.values and request.values["configured"] in valid_boolean_trues:
		slicers = slicingManager.configured_slicers
	else:
		slicers = slicingManager.registered_slicers

	result = dict()
	for slicer in slicers:
		try:
			slicer_impl = slicingManager.get_slicer(slicer, require_configured=False)

			extensions = set()
			for source_file_type in slicer_impl.get_slicer_properties().get("source_file_types", ["model"]):
				extensions = extensions.union(get_extensions(source_file_type))

			result[slicer] = dict(
				key=slicer,
				displayName=slicer_impl.get_slicer_properties()["name"],
				sameDevice=slicer_impl.get_slicer_properties()["same_device"],
				default=default_slicer == slicer,
				configured=slicer_impl.is_slicer_configured(),
				profiles=_getSlicingProfilesData(slicer),
				extensions=dict(
					source=list(extensions),
					destination=slicer_impl.get_slicer_properties().get("destination_extensions", ["gco", "gcode", "g"])
				)
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

	saved_profile = slicingManager.save_profile(slicer, name, profile,
	                                            allow_overwrite=True,
	                                            overrides=data,
	                                            display_name=display_name,
	                                            description=description)

	from octoprint.server.api import valid_boolean_trues
	if "default" in json_data and json_data["default"] in valid_boolean_trues:
		slicingManager.set_default_profile(slicer, name, require_exists=False)

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
