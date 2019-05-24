# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2019 The OctoPrint Project - Released under terms of the AGPLv3 License"


from flask import jsonify, make_response, request, url_for
from werkzeug.exceptions import BadRequest

from octoprint.server import connectionProfileManager
from octoprint.server.api import api, NO_CONTENT, valid_boolean_trues
from octoprint.server.util.flask import no_firstrun_access, with_revalidation_checking
from octoprint.util import dict_merge

from octoprint.comm.connectionprofile import InvalidProfileError, SaveError

from octoprint.access.permissions import Permissions

def _lastmodified():
	return connectionProfileManager.last_modified

def _etag(lm=None):
	if lm is None:
		lm = _lastmodified()

	import hashlib
	hash = hashlib.sha1()
	def hash_update(value):
		value = value.encode('utf-8')
		hash.update(value)
	hash_update(str(lm))
	return hash.hexdigest()


@api.route("/connectionprofiles", methods=["GET"])
@with_revalidation_checking(etag_factory=_etag,
                            lastmodified_factory=_lastmodified,
                            unless=lambda: request.values.get("force", "false") in valid_boolean_trues)
@no_firstrun_access
@Permissions.CONNECTION.require(403)
def connectionProfilesList():
	all_profiles = connectionProfileManager.get_all()
	return jsonify(dict(profiles=_convert_profiles(all_profiles)))

@api.route("/connectionprofiles", methods=["POST"])
@no_firstrun_access
@Permissions.SETTINGS.require(403)
def connectionProfilesAdd():
	if not "application/json" in request.headers["Content-Type"]:
		return make_response("Expected content-type JSON", 400)

	try:
		json_data = request.get_json()
	except BadRequest:
		return make_response("Malformed JSON body in request", 400)

	if json_data is None:
		return make_response("Malformed JSON body in request", 400)

	if not "profile" in json_data:
		return make_response("No profile included in request", 400)

	new_profile = json_data["profile"]
	if not "id" in new_profile:
		return make_response("Profile does not contain mandatory 'id' field", 400)
	if not "name" in new_profile:
		return make_response("Profile does not contain mandatory 'name' field", 400)

	make_default = False
	if "default" in new_profile:
		make_default = True
		del new_profile["default"]

	profile = connectionProfileManager.to_profile(new_profile)

	try:
		connectionProfileManager.save(profile, allow_overwrite=False, make_default=make_default)
	except InvalidProfileError:
		return make_response("Profile is invalid", 400)
	except SaveError:
		return make_response("Profile {} could not be saved".format(profile["id"]), 400)
	except Exception as e:
		return make_response("Could not save profile: {}".format(e), 500)
	else:
		return jsonify(dict(profile=profile.as_dict()))

@api.route("/connectionprofiles/<string:identifier>", methods=["GET"])
@no_firstrun_access
@Permissions.CONNECTION.require(403)
def connectionProfilesGet(identifier):
	profile = connectionProfileManager.get(identifier)
	if profile is None:
		return make_response("Unknown profile: {}".format(identifier), 404)
	else:
		return jsonify(dict(profile=profile.as_dict()))

@api.route("/connectionprofiles/<string:identifier>", methods=["DELETE"])
@no_firstrun_access
@Permissions.SETTINGS.require(403)
def connectionProfilesDelete(identifier):
	#current_profile = connectionProfileManager.get_current()
	#if current_profile and current_profile["id"] == identifier:
	#	return make_response("Cannot delete currently selected profile: {}".format(identifier), 409)

	#default_profile = connectionProfileManager.get_default()
	#if default_profile and default_profile["id"] == identifier:
	#	return make_response("Cannot delete default profile: {}".format(identifier), 409)

	connectionProfileManager.remove(identifier)
	return NO_CONTENT

#@api.route("/connectionprofiles/<string:identifier>", methods=["PATCH"])
#@no_firstrun_access
#@Permissions.SETTINGS.require(403)
#def printerProfilesUpdate(identifier):
#	if not "application/json" in request.headers["Content-Type"]:
#		return make_response("Expected content-type JSON", 400)
#
#	try:
#		json_data = request.get_json()
#	except BadRequest:
#		return make_response("Malformed JSON body in request", 400)
#
#	if json_data is None:
#		return make_response("Malformed JSON body in request", 400)
#
#	if not "profile" in json_data:
#		return make_response("No profile included in request", 400)
#
#	profile = printerProfileManager.get(identifier)
#	if profile is None:
#		profile = printerProfileManager.get_default()
#
#	new_profile = json_data["profile"]
#	merged_profile = dict_merge(profile, new_profile)
#
#	make_default = False
#	if "default" in merged_profile:
#		make_default = True
#		del new_profile["default"]
#
#		merged_profile["id"] = identifier
#
#	try:
#		saved_profile = printerProfileManager.save(merged_profile, allow_overwrite=True, make_default=make_default)
#	except InvalidProfileError:
#		return make_response("Profile is invalid", 400)
#	except CouldNotOverwriteError:
#		return make_response("Profile already exists and overwriting was not allowed", 400)
#	except Exception as e:
#		return make_response("Could not save profile: %s" % str(e), 500)
#	else:
#		return jsonify(dict(profile=_convert_profile(saved_profile)))

def _convert_profiles(profiles):
	result = dict()
	for identifier, profile in profiles.items():
		result[identifier] = profile.as_dict()
	return result
