__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

from flask import abort, jsonify, make_response, request, url_for

from octoprint.access.permissions import Permissions
from octoprint.server import slicingManager
from octoprint.server.api import NO_CONTENT, api
from octoprint.server.util.flask import no_firstrun_access, with_revalidation_checking
from octoprint.settings import settings as s
from octoprint.settings import valid_boolean_trues
from octoprint.slicing import (
    CouldNotDeleteProfile,
    SlicerNotConfigured,
    UnknownProfile,
    UnknownSlicer,
)

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

    def hash_update(value):
        value = value.encode("utf-8")
        hash.update(value)

    hash_update(str(lm))

    if configured:
        slicers = slicingManager.configured_slicers
    else:
        slicers = slicingManager.registered_slicers

    default_slicer = s().get(["slicing", "defaultSlicer"])

    for slicer in sorted(slicers):
        slicer_impl = slicingManager.get_slicer(slicer, require_configured=False)
        hash_update(slicer)
        hash_update(str(slicer_impl.is_slicer_configured()))
        hash_update(str(slicer == default_slicer))

    hash_update(_DATA_FORMAT_VERSION)  # increment version if we change the API format

    return hash.hexdigest()


@api.route("/slicing", methods=["GET"])
@with_revalidation_checking(
    etag_factory=lambda lm=None: _etag(
        request.values.get("configured", "false") in valid_boolean_trues, lm=lm
    ),
    lastmodified_factory=lambda: _lastmodified(
        request.values.get("configured", "false") in valid_boolean_trues
    ),
    unless=lambda: request.values.get("force", "false") in valid_boolean_trues,
)
@Permissions.SLICE.require(403)
def slicingListAll():
    from octoprint.filemanager import get_extensions

    default_slicer = s().get(["slicing", "defaultSlicer"])

    if (
        "configured" in request.values
        and request.values["configured"] in valid_boolean_trues
    ):
        slicers = slicingManager.configured_slicers
    else:
        slicers = slicingManager.registered_slicers

    result = {}
    for slicer in slicers:
        try:
            slicer_impl = slicingManager.get_slicer(slicer, require_configured=False)

            extensions = set()
            for source_file_type in slicer_impl.get_slicer_properties().get(
                "source_file_types", ["model"]
            ):
                extensions = extensions.union(get_extensions(source_file_type))

            result[slicer] = {
                "key": slicer,
                "displayName": slicer_impl.get_slicer_properties().get("name", "n/a"),
                "sameDevice": slicer_impl.get_slicer_properties().get(
                    "same_device", True
                ),
                "default": default_slicer == slicer,
                "configured": slicer_impl.is_slicer_configured(),
                "profiles": _getSlicingProfilesData(slicer),
                "extensions": {
                    "source": list(extensions),
                    "destination": slicer_impl.get_slicer_properties().get(
                        "destination_extensions", ["gco", "gcode", "g"]
                    ),
                },
            }
        except (UnknownSlicer, SlicerNotConfigured):
            # this should never happen
            pass

    return jsonify(result)


@api.route("/slicing/<string:slicer>/profiles", methods=["GET"])
@no_firstrun_access
@Permissions.SLICE.require(403)
def slicingListSlicerProfiles(slicer):
    configured = False
    if (
        "configured" in request.values
        and request.values["configured"] in valid_boolean_trues
    ):
        configured = True

    try:
        return jsonify(_getSlicingProfilesData(slicer, require_configured=configured))
    except (UnknownSlicer, SlicerNotConfigured):
        abort(404)


@api.route("/slicing/<string:slicer>/profiles/<string:name>", methods=["GET"])
@no_firstrun_access
@Permissions.SLICE.require(403)
def slicingGetSlicerProfile(slicer, name):
    try:
        profile = slicingManager.load_profile(slicer, name, require_configured=False)
    except UnknownSlicer:
        abort(404)
    except UnknownProfile:
        abort(404)

    result = _getSlicingProfileData(slicer, name, profile)
    result["data"] = profile.data
    return jsonify(result)


@api.route("/slicing/<string:slicer>/profiles/<string:name>", methods=["PUT"])
@no_firstrun_access
@Permissions.SETTINGS.require(403)
def slicingAddSlicerProfile(slicer, name):
    json_data = request.get_json()

    data = {}
    display_name = None
    description = None
    if "data" in json_data:
        data = json_data["data"]
    if "displayName" in json_data:
        display_name = json_data["displayName"]
    if "description" in json_data:
        description = json_data["description"]

    try:
        profile = slicingManager.save_profile(
            slicer,
            name,
            data,
            allow_overwrite=True,
            display_name=display_name,
            description=description,
        )
    except UnknownSlicer:
        abort(404, description="Unknown slicer")

    result = _getSlicingProfileData(slicer, name, profile)
    r = make_response(jsonify(result), 201)
    r.headers["Location"] = result["resource"]
    return r


@api.route("/slicing/<string:slicer>/profiles/<string:name>", methods=["PATCH"])
@no_firstrun_access
@Permissions.SETTINGS.require(403)
def slicingPatchSlicerProfile(slicer, name):
    json_data = request.get_json()

    try:
        profile = slicingManager.load_profile(slicer, name, require_configured=False)
    except UnknownSlicer:
        return abort(404)
    except UnknownProfile:
        return abort(404)

    data = {}
    display_name = None
    description = None
    if "data" in json_data:
        data = json_data["data"]
    if "displayName" in json_data:
        display_name = json_data["displayName"]
    if "description" in json_data:
        description = json_data["description"]

    saved_profile = slicingManager.save_profile(
        slicer,
        name,
        profile,
        allow_overwrite=True,
        overrides=data,
        display_name=display_name,
        description=description,
    )

    from octoprint.server.api import valid_boolean_trues

    if "default" in json_data and json_data["default"] in valid_boolean_trues:
        slicingManager.set_default_profile(slicer, name, require_exists=False)

    return jsonify(_getSlicingProfileData(slicer, name, saved_profile))


@api.route("/slicing/<string:slicer>/profiles/<string:name>", methods=["DELETE"])
@no_firstrun_access
@Permissions.SETTINGS.require(403)
def slicingDelSlicerProfile(slicer, name):
    try:
        slicingManager.delete_profile(slicer, name)
    except UnknownSlicer:
        abort(404)
    except CouldNotDeleteProfile as e:
        abort(
            500,
            description="Could not delete profile for slicer: {cause}".format(
                cause=str(e.cause)
            ),
        )

    return NO_CONTENT


def _getSlicingProfilesData(slicer, require_configured=False):
    profiles = slicingManager.all_profiles(slicer, require_configured=require_configured)

    result = {}
    for name, profile in profiles.items():
        result[name] = _getSlicingProfileData(slicer, name, profile)
    return result


def _getSlicingProfileData(slicer, name, profile):
    defaultProfiles = s().get(["slicing", "defaultProfiles"])
    result = {
        "key": name,
        "default": defaultProfiles
        and slicer in defaultProfiles
        and defaultProfiles[slicer] == name,
        "resource": url_for(
            ".slicingGetSlicerProfile", slicer=slicer, name=name, _external=True
        ),
    }
    if profile.display_name is not None:
        result["displayName"] = profile.display_name
    if profile.description is not None:
        result["description"] = profile.description
    return result
