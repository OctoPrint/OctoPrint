__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

from flask import abort, jsonify, request

from octoprint.access.permissions import Permissions
from octoprint.comm.protocol import all_protocols
from octoprint.comm.transport import all_transports
from octoprint.server import (
    NO_CONTENT,
    connectionProfileManager,
    printer,
    printerProfileManager,
)
from octoprint.server.api import api
from octoprint.server.util.flask import get_json_command_from_request, no_firstrun_access
from octoprint.settings import settings


def _convert_transport_options(options):
    return [option.as_dict() for option in options]


def _convert_protocol_options(options):
    return [option.as_dict() for option in options]


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

    return jsonify({"current": current, "options": _get_options()})


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

        if "save" in data and data["save"]:  # TODO
            """
            settings().set(["serial", "port"], port)
            settings().setInt(["serial", "baudrate"], baudrate)
            printerProfileManager.set_default(kwargs.get("profile"))
            """

        if "autoconnect" in data:
            settings().setBoolean(["serial", "autoconnect"], data["autoconnect"])

        ##~~ legacy

        # TODO remove in 1.5.0

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


def _get_options():
    transports = []
    for transport in all_transports():
        transports.append(
            {
                "name": transport.name,
                "key": transport.key,
                "options": _convert_transport_options(transport.get_connection_options()),
            }
        )

    protocols = []
    for protocol in all_protocols():
        protocols.append(
            {
                "name": protocol.name,
                "key": protocol.key,
                "options": _convert_protocol_options(protocol.get_connection_options()),
            }
        )

    profile_options = printerProfileManager.get_all()
    default_profile = printerProfileManager.get_default()

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
            for printer_profile in profile_options.values()
            if "id" in printer_profile
        ],
        "connectionProfiles": [
            connection_profile.as_dict()
            for connection_profile in connection_profiles.values()
        ],
        "printerProfilePreference": default_profile["id"]
        if "id" in default_profile
        else None,
        "connectionProfilePreference": default_connection.id
        if default_connection
        else None,
        "protocols": protocols,
        "transports": transports,
    }

    return options
