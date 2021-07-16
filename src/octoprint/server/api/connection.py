__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging

from flask import abort, jsonify, make_response, request
from werkzeug.exceptions import BadRequest

from octoprint.access.permissions import Permissions
from octoprint.comm.connectionprofile import InvalidProfileError, SaveError
from octoprint.comm.protocol import all_protocols
from octoprint.comm.transport import all_transports
from octoprint.server import (
    NO_CONTENT,
    connectionProfileManager,
    printer,
    printerProfileManager,
)
from octoprint.server.api import api, valid_boolean_trues
from octoprint.server.util.flask import (
    get_json_command_from_request,
    no_firstrun_access,
    with_revalidation_checking,
)
from octoprint.settings import settings
from octoprint.settings.parameters import get_param_structure
from octoprint.util import dict_merge

##~~ Connection state & commands


@api.route("/connection", methods=["GET"])
@Permissions.STATUS.require(403)
def connectionState():
    params = printer.get_current_connection_parameters()
    current = {
        "state": params["state"],
        "connection": params["connection"],
        "profile": params["printer_profile"],
        "protocol": params["protocol"],
        "protocolOptions": params["protocol_args"],
        "transport": params["transport"],
        "transportOptions": params["transport_args"],
    }
    return jsonify(current=current)


@api.route("/connection", methods=["POST"])
@no_firstrun_access
@Permissions.CONNECTION.require(403)
def connectionCommand():
    valid_commands = {"connect": [], "disconnect": [], "fake_ack": []}

    command, data, response = get_json_command_from_request(request, valid_commands)
    if response is not None:
        return response

    if command == "connect":
        kwargs = {}

        if "connection" in data:
            kwargs["connection"] = data["connection"]

        if "protocol" in data:
            kwargs["protocol"] = data["protocol"]

        if "protocolOptions" in data:
            kwargs["protocol_options"] = data["protocolOptions"]

        if "transport" in data:
            kwargs["transport"] = data["transport"]

        if "transportOptions" in data:
            kwargs["transport_options"] = data["transportOptions"]

        if "printerProfile" in data:
            printerProfile = data["printerProfile"]
            if not printerProfileManager.exists(printerProfile):
                abort(400, description="printerProfile is invalid")
            kwargs["profile"] = printerProfile

        if "autoconnect" in data:
            settings().setBoolean(
                ["connection", "profiles", "autoconnect_default"], data["autoconnect"]
            )

        ##~~ legacy

        # TODO remove in 2.5

        if "port" in data.keys():
            kwargs["port"] = data["port"]

        if "baudrate" in data.keys():
            kwargs["baudrate"] = data["baudrate"]

        settings().save()
        printer.connect(**kwargs)

    elif command == "disconnect":
        printer.disconnect()

    elif command == "fake_ack":
        printer.fake_ack()

    return NO_CONTENT


##~~ Connection options (profiles, protocols, transports)


@api.route("/connection/options", methods=["GET"])
@Permissions.STATUS.require(403)
def connectionOptions():

    printer_profiles = printerProfileManager.get_all()
    default_printer = printerProfileManager.get_default()

    connection_profiles = connectionProfileManager.get_all()
    default_connection = connectionProfileManager.get_default()

    options = {
        "printerProfiles": [
            {
                "id": printer_profile["id"],
                "name": printer_profile["name"]
                if "name" in printer_profile
                else printer_profile["id"],
            }
            for printer_profile in printer_profiles.values()
            if "id" in printer_profile
        ],
        "connectionProfiles": [
            connection_profile.as_dict()
            for connection_profile in connection_profiles.values()
        ],
        "printerProfilePreference": default_printer["id"]
        if "id" in default_printer
        else None,
        "connectionProfilePreference": default_connection.id
        if default_connection
        else None,
        "protocols": _get_protocols(),
        "transports": _get_transports(),
    }

    return jsonify(options=options)


##~~ Connection profiles


def _connection_profiles_lastmodified():
    return connectionProfileManager.last_modified


def _connection_profiles_etag(lm=None):
    if lm is None:
        lm = _connection_profiles_lastmodified()

    import hashlib

    hash = hashlib.sha1()

    def hash_update(value):
        value = value.encode("utf-8")
        hash.update(value)

    hash_update(str(lm))
    hash_update(repr(connectionProfileManager.get_default()))
    hash_update(repr(connectionProfileManager.get_current()))
    return hash.hexdigest()


@api.route("/connection/profiles", methods=["GET"])
@with_revalidation_checking(
    etag_factory=_connection_profiles_etag,
    lastmodified_factory=_connection_profiles_lastmodified,
    unless=lambda: request.values.get("force", "false") in valid_boolean_trues,
)
@no_firstrun_access
@Permissions.CONNECTION.require(403)
def connectionProfilesList():
    all_profiles = connectionProfileManager.get_all()
    return jsonify({"profiles": _convert_connection_profiles(all_profiles)})


@api.route("/connection/profiles/<string:identifier>", methods=["GET"])
@no_firstrun_access
@Permissions.CONNECTION.require(403)
def connectionProfilesGet(identifier):
    profile = connectionProfileManager.get(identifier)
    if profile is None:
        return make_response(f"Unknown profile: {identifier}", 404)
    else:
        return jsonify({"profile": _convert_connection_profile(profile)})


@api.route("/connection/profiles/<string:identifier>", methods=["PUT"])
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
        return make_response(f"Profile {profile.id} could not be saved", 400)
    except Exception as e:
        logging.getLogger(__name__).exception(e)
        return make_response(
            f"Could not save profile due to an unexpected error: {e}", 500
        )
    else:
        return jsonify({"profile": _convert_connection_profile(profile)})


@api.route("/connection/profiles/<string:identifier>", methods=["DELETE"])
@no_firstrun_access
@Permissions.SETTINGS.require(403)
def connectionProfilesDelete(identifier):
    current_profile = connectionProfileManager.get_current()
    if current_profile and current_profile.id == identifier:
        return make_response(
            f"Cannot delete currently selected profile: {identifier}", 409
        )

    default_profile = connectionProfileManager.get_default()
    if default_profile and default_profile.id == identifier:
        return make_response(f"Cannot delete default profile: {identifier}", 409)

    connectionProfileManager.remove(identifier)
    return NO_CONTENT


@api.route("/connection/profiles/<string:identifier>", methods=["PATCH"])
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
        return make_response(f"Profile {profile.id} could not be saved", 400)
    except Exception as e:
        return make_response(
            f"Could not save profile due to an unexpected error: {e}", 500
        )
    else:
        return jsonify({"profile": _convert_connection_profile(saved_profile)})


def _convert_connection_profiles(profiles):
    result = {}
    for identifier, profile in profiles.items():
        result[identifier] = _convert_connection_profile(profile)
    return result


def _convert_connection_profile(profile):
    current = connectionProfileManager.get_current()
    default = connectionProfileManager.get_default()

    result = profile.as_dict()
    result["current"] = profile.id == current.id if current is not None else False
    result["default"] = profile.id == default.id if default is not None else False
    return result


##~~ Protocols


@api.route("/connection/protocols", methods=["GET"])
@no_firstrun_access
@Permissions.CONNECTION.require(403)
def getProtocols():
    return jsonify({"protocols": _get_protocols()})


##~~ Transports


@api.route("/connection/transports", methods=["GET"])
@no_firstrun_access
@Permissions.CONNECTION.require(403)
def getTransports():
    return jsonify({"transports": _get_transports()})


##~~ Helpers


def _get_protocols():
    protocols = []
    for protocol in all_protocols():
        protocols.append(
            {
                "name": protocol.name,
                "key": protocol.key,
                "options": get_param_structure(protocol.get_connection_options()),
                "settings": get_param_structure(protocol.settings),
            }
        )
    return protocols


def _get_transports():
    transports = []
    for transport in all_transports():
        transports.append(
            {
                "name": transport.name,
                "key": transport.key,
                "options": get_param_structure(transport.get_connection_options()),
                "settings": get_param_structure(transport.settings),
            }
        )
    return transports
