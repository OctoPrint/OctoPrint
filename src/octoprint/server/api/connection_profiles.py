__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2019 The OctoPrint Project - Released under terms of the AGPLv3 License"


from flask import jsonify, make_response, request
from werkzeug.exceptions import BadRequest

from octoprint.access.permissions import Permissions
from octoprint.comm.connectionprofile import InvalidProfileError, SaveError
from octoprint.server import connectionProfileManager
from octoprint.server.api import NO_CONTENT, api, valid_boolean_trues
from octoprint.server.util.flask import no_firstrun_access, with_revalidation_checking
from octoprint.util import dict_merge


def _lastmodified():
    return connectionProfileManager.last_modified


def _etag(lm=None):
    if lm is None:
        lm = _lastmodified()

    import hashlib

    hash = hashlib.sha1()

    def hash_update(value):
        value = value.encode("utf-8")
        hash.update(value)

    hash_update(str(lm))
    hash_update(repr(connectionProfileManager.get_default()))
    hash_update(repr(connectionProfileManager.get_current()))
    return hash.hexdigest()


@api.route("/connectionprofiles", methods=["GET"])
@with_revalidation_checking(
    etag_factory=_etag,
    lastmodified_factory=_lastmodified,
    unless=lambda: request.values.get("force", "false") in valid_boolean_trues,
)
@no_firstrun_access
@Permissions.CONNECTION.require(403)
def connectionProfilesList():
    all_profiles = connectionProfileManager.get_all()
    return jsonify({"profiles": _convert_profiles(all_profiles)})


@api.route("/connectionprofiles/<string:identifier>", methods=["GET"])
@no_firstrun_access
@Permissions.CONNECTION.require(403)
def connectionProfilesGet(identifier):
    profile = connectionProfileManager.get(identifier)
    if profile is None:
        return make_response("Unknown profile: {}".format(identifier), 404)
    else:
        return jsonify({"profile": _convert_profile(profile)})


@api.route("/connectionprofiles/<string:identifier>", methods=["PUT"])
@no_firstrun_access
@Permissions.CONNECTION.require(403)
def connectionProfileSet(identifier):
    if "application/json" not in request.headers["Content-Type"]:
        return make_response("Expected content-type JSON", 400)

    try:
        json_data = request.get_json()
    except BadRequest:
        return make_response("Malformed JSON body in request", 400)

    if json_data is None:
        return make_response("Malformed JSON body in request", 400)

    if "profile" not in json_data:
        return make_response("No profile included in request", 400)

    allow_overwrite = json_data.get("overwrite", False)
    make_default = json_data.get("default", False)

    new_profile = json_data["profile"]
    if "name" not in new_profile:
        return make_response("Profile does not contain mandatory 'name' field", 400)

    if "id" not in new_profile:
        new_profile["id"] = identifier

    profile = connectionProfileManager.to_profile(new_profile)

    try:
        connectionProfileManager.save(
            profile, allow_overwrite=allow_overwrite, make_default=make_default
        )
    except InvalidProfileError:
        return make_response("Profile is invalid", 400)
    except SaveError:
        return make_response("Profile {} could not be saved".format(profile.id), 400)
    except Exception as e:
        return make_response(
            "Could not save profile due to an unexpected error: {}".format(e), 500
        )
    else:
        return jsonify({"profile": _convert_profile(profile)})


@api.route("/connectionprofiles/<string:identifier>", methods=["DELETE"])
@no_firstrun_access
@Permissions.SETTINGS.require(403)
def connectionProfilesDelete(identifier):
    current_profile = connectionProfileManager.get_current()
    if current_profile and current_profile["id"] == identifier:
        return make_response(
            "Cannot delete currently selected profile: {}".format(identifier), 409
        )

    default_profile = connectionProfileManager.get_default()
    if default_profile and default_profile["id"] == identifier:
        return make_response("Cannot delete default profile: {}".format(identifier), 409)

    connectionProfileManager.remove(identifier)
    return NO_CONTENT


@api.route("/connectionprofiles/<string:identifier>", methods=["PATCH"])
@no_firstrun_access
@Permissions.SETTINGS.require(403)
def connectionProfilesUpdate(identifier):
    if "application/json" not in request.headers["Content-Type"]:
        return make_response("Expected content-type JSON", 400)

    try:
        json_data = request.get_json()
    except BadRequest:
        return make_response("Malformed JSON body in request", 400)

    if json_data is None:
        return make_response("Malformed JSON body in request", 400)

    if "profile" not in json_data:
        return make_response("No profile included in request", 400)

    profile = connectionProfileManager.get(identifier)
    if profile is None:
        return make_response("Profile {} doesn't exist", 404)

    profile_data = json_data["profile"]
    make_default = profile_data.pop("default", False)
    profile_data.pop("id", None)

    merged_profile_data = dict_merge(profile.as_dict(), profile_data)
    new_profile = connectionProfileManager.to_profile(merged_profile_data)

    try:
        saved_profile = connectionProfileManager.save(
            new_profile, allow_overwrite=True, make_default=make_default
        )
    except InvalidProfileError:
        return make_response("Profile is invalid", 400)
    except SaveError:
        return make_response("Profile {} could not be saved".format(profile.id), 400)
    except Exception as e:
        return make_response(
            "Could not save profile due to an unexpected error: {}".format(e), 500
        )
    else:
        return jsonify({"profile": _convert_profile(saved_profile)})


def _convert_profiles(profiles):
    result = {}
    for identifier, profile in profiles.items():
        result[identifier] = _convert_profile(profile)
    return result


def _convert_profile(profile):
    current = connectionProfileManager.get_current()
    default = connectionProfileManager.get_default()

    result = profile.as_dict()
    result["current"] = profile.id == current.id if current is not None else False
    result["default"] = profile.id == default.id if default is not None else False
    return result
