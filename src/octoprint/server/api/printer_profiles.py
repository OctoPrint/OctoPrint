__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import copy

from flask import abort, jsonify, request, url_for

from octoprint.access.permissions import Permissions
from octoprint.printer.profile import CouldNotOverwriteError, InvalidProfileError
from octoprint.server import printerProfileManager
from octoprint.server.api import NO_CONTENT, api, valid_boolean_trues
from octoprint.server.util.flask import no_firstrun_access, with_revalidation_checking
from octoprint.util import dict_merge


def _lastmodified():
    return printerProfileManager.last_modified


def _etag(lm=None):
    if lm is None:
        lm = _lastmodified()

    import hashlib

    hash = hashlib.sha1()

    def hash_update(value):
        value = value.encode("utf-8")
        hash.update(value)

    hash_update(str(lm))
    hash_update(repr(printerProfileManager.get_default()))
    hash_update(repr(printerProfileManager.get_current()))
    return hash.hexdigest()


@api.route("/printerprofiles", methods=["GET"])
@with_revalidation_checking(
    etag_factory=_etag,
    lastmodified_factory=_lastmodified,
    unless=lambda: request.values.get("force", "false") in valid_boolean_trues,
)
@no_firstrun_access
@Permissions.CONNECTION.require(403)
def printerProfilesList():
    all_profiles = printerProfileManager.get_all()
    return jsonify({"profiles": _convert_profiles(all_profiles)})


@api.route("/printerprofiles", methods=["POST"])
@no_firstrun_access
@Permissions.SETTINGS.require(403)
def printerProfilesAdd():
    if "application/json" not in request.headers["Content-Type"]:
        abort(400, description="Expected content-type JSON")

    json_data = request.get_json()

    if json_data is None:
        abort(400, description="Malformed JSON body in request")

    if "profile" not in json_data:
        abort(400, description="profile is missing")

    base_profile = printerProfileManager.get_default()
    if "basedOn" in json_data and isinstance(json_data["basedOn"], str):
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

    if "id" not in profile:
        abort(400, description="profile.id is missing")
    if "name" not in profile:
        abort(400, description="profile.name is missing")

    try:
        saved_profile = printerProfileManager.save(
            profile, allow_overwrite=False, make_default=make_default, trigger_event=True
        )
    except InvalidProfileError:
        abort(400, description="profile is invalid")
    except CouldNotOverwriteError:
        abort(400, description="Profile already exists and overwriting was not allowed")
    except Exception as e:
        abort(500, description="Could not save profile: %s" % str(e))
    else:
        return jsonify({"profile": _convert_profile(saved_profile)})


@api.route("/printerprofiles/<string:identifier>", methods=["GET"])
@no_firstrun_access
@Permissions.CONNECTION.require(403)
def printerProfilesGet(identifier):
    profile = printerProfileManager.get(identifier)
    if profile is None:
        abort(404)
    else:
        return jsonify(_convert_profile(profile))


@api.route("/printerprofiles/<string:identifier>", methods=["DELETE"])
@no_firstrun_access
@Permissions.SETTINGS.require(403)
def printerProfilesDelete(identifier):
    current_profile = printerProfileManager.get_current()
    if current_profile and current_profile["id"] == identifier:
        abort(409, description="Cannot delete currently selected profile")

    default_profile = printerProfileManager.get_default()
    if default_profile and default_profile["id"] == identifier:
        abort(409, description="Cannot delete default profile")

    printerProfileManager.remove(identifier, trigger_event=True)
    return NO_CONTENT


@api.route("/printerprofiles/<string:identifier>", methods=["PATCH"])
@no_firstrun_access
@Permissions.SETTINGS.require(403)
def printerProfilesUpdate(identifier):
    if "application/json" not in request.headers["Content-Type"]:
        abort(400, description="Expected content-type JSON")

    json_data = request.get_json()
    if json_data is None:
        abort(400, description="Malformed JSON body in request")

    if "profile" not in json_data:
        abort(400, description="profile missing")

    profile = printerProfileManager.get(identifier)
    if profile is None:
        profile = printerProfileManager.get_default()

    new_profile = json_data["profile"]
    merged_profile = dict_merge(profile, new_profile)

    make_default = False
    if "default" in merged_profile:
        make_default = True
        del new_profile["default"]

        merged_profile["id"] = identifier

    try:
        saved_profile = printerProfileManager.save(
            merged_profile,
            allow_overwrite=True,
            make_default=make_default,
            trigger_event=True,
        )
    except InvalidProfileError:
        abort(400, description="profile is invalid")
    except CouldNotOverwriteError:
        abort(400, description="Profile already exists and overwriting was not allowed")
    except Exception as e:
        abort(500, description="Could not save profile: %s" % str(e))
    else:
        return jsonify({"profile": _convert_profile(saved_profile)})


def _convert_profiles(profiles):
    result = {}
    for identifier, profile in profiles.items():
        result[identifier] = _convert_profile(profile)
    return result


def _convert_profile(profile):
    default = printerProfileManager.get_default()["id"]
    current = printerProfileManager.get_current_or_default()["id"]

    converted = copy.deepcopy(profile)
    converted["resource"] = url_for(
        ".printerProfilesGet", identifier=profile["id"], _external=True
    )
    converted["default"] = profile["id"] == default
    converted["current"] = profile["id"] == current
    return converted
