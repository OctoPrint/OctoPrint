__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

from flask import abort, jsonify, request

from octoprint.access.permissions import Permissions
from octoprint.server import NO_CONTENT, current_user, printer
from octoprint.server.api import api
from octoprint.server.util.flask import get_json_command_from_request, no_firstrun_access


@api.route("/job", methods=["POST"])
@no_firstrun_access
def controlJob():
    if not printer.is_operational():
        abort(409, description="Printer is not operational")

    valid_commands = {"start": [], "restart": [], "pause": [], "cancel": []}

    command, data, response = get_json_command_from_request(request, valid_commands)
    if response is not None:
        return response

    activePrintjob = printer.is_printing() or printer.is_paused()

    tags = {"source:api", "api:job"}

    user = current_user.get_name()

    with Permissions.PRINT.require(403):
        if command == "start":
            if activePrintjob:
                abort(
                    409,
                    description="Printer already has an active print job, did you mean 'restart'?",
                )
            printer.start_print(tags=tags, user=user)
        elif command == "restart":
            if not printer.is_paused():
                abort(
                    409,
                    description="Printer does not have an active print job or is not paused",
                )
            printer.start_print(tags=tags, user=user)
        elif command == "pause":
            if not activePrintjob:
                abort(
                    409,
                    description="Printer is neither printing nor paused, 'pause' command cannot be performed",
                )
            action = data.get("action", "toggle")
            if action == "toggle":
                printer.toggle_pause_print(tags=tags, user=user)
            elif action == "pause":
                printer.pause_print(tags=tags, user=user)
            elif action == "resume":
                printer.resume_print(tags=tags, user=user)
            else:
                abort(400, description="Unknown action")
        elif command == "cancel":
            if not activePrintjob:
                abort(
                    409,
                    description="Printer is neither printing nor paused, 'cancel' command cannot be performed",
                )
            printer.cancel_print(tags=tags, user=user)
    return NO_CONTENT


@api.route("/job", methods=["GET"])
@Permissions.STATUS.require(403)
def jobState():
    currentData = printer.get_current_data()
    response = {
        "job": currentData["job"],
        "progress": currentData["progress"],
        "state": currentData["state"]["text"],
    }
    if currentData["state"]["error"]:
        response["error"] = currentData["state"]["error"]

    return jsonify(**response)
