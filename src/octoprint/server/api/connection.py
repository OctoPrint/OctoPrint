__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

from flask import abort, jsonify, request

from octoprint.access.permissions import Permissions
from octoprint.server import NO_CONTENT, printer, printerProfileManager
from octoprint.server.api import api
from octoprint.server.util.flask import get_json_command_from_request, no_firstrun_access
from octoprint.settings import settings


@api.route("/connection", methods=["GET"])
@Permissions.STATUS.require(403)
def connectionState():
    state, port, baudrate, printer_profile = printer.get_current_connection()
    current = {
        "state": state,
        "port": port,
        "baudrate": baudrate,
        "printerProfile": printer_profile["id"]
        if printer_profile is not None and "id" in printer_profile
        else "_default",
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
        connection_options = printer.__class__.get_connection_options()

        port = None
        baudrate = None
        printerProfile = None
        if "port" in data:
            port = data["port"]
            if port not in connection_options["ports"] and port != "AUTO":
                abort(400, description="port is invalid")
        if "baudrate" in data:
            baudrate = data["baudrate"]
            if baudrate not in connection_options["baudrates"] and baudrate != 0:
                abort(400, description="baudrate is invalid")
        if "printerProfile" in data:
            printerProfile = data["printerProfile"]
            if not printerProfileManager.exists(printerProfile):
                abort(400, description="printerProfile is invalid")
        if "save" in data and data["save"]:
            settings().set(["serial", "port"], port)
            settings().setInt(["serial", "baudrate"], baudrate)
            printerProfileManager.set_default(printerProfile)
        if "autoconnect" in data:
            settings().setBoolean(["serial", "autoconnect"], data["autoconnect"])
        settings().save()
        printer.connect(port=port, baudrate=baudrate, profile=printerProfile)
    elif command == "disconnect":
        printer.disconnect()
    elif command == "fake_ack":
        printer.fake_ack()

    return NO_CONTENT


def _get_options():
    connection_options = printer.__class__.get_connection_options()
    profile_options = printerProfileManager.get_all()
    default_profile = printerProfileManager.get_default()

    options = {
        "ports": connection_options["ports"],
        "baudrates": connection_options["baudrates"],
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
        "portPreference": connection_options["portPreference"],
        "baudratePreference": connection_options["baudratePreference"],
        "printerProfilePreference": default_profile["id"]
        if "id" in default_profile
        else None,
    }

    return options
