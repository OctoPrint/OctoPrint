__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

from flask import abort, jsonify, request

from octoprint.access.permissions import Permissions
from octoprint.schema.api import job as apischema
from octoprint.server import NO_CONTENT, current_user, printer
from octoprint.server.api import api
from octoprint.server.util.flask import (
    api_versioned,
    get_json_command_from_request,
    no_firstrun_access,
)


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
    params = data.get("params")

    with Permissions.PRINT.require(403):
        if command == "start":
            if activePrintjob:
                abort(
                    409,
                    description="Printer already has an active print job, did you mean 'restart'?",
                )
            printer.start_print(tags=tags, user=user, params=params)
        elif command == "restart":
            if not printer.is_paused():
                abort(
                    409,
                    description="Printer does not have an active print job or is not paused",
                )
            printer.start_print(tags=tags, user=user, params=params)
        elif command == "pause":
            if not activePrintjob:
                abort(
                    409,
                    description="Printer is neither printing nor paused, 'pause' command cannot be performed",
                )
            action = data.get("action", "toggle")
            if action == "toggle":
                printer.toggle_pause_print(tags=tags, user=user, params=params)
            elif action == "pause":
                printer.pause_print(tags=tags, user=user, params=params)
            elif action == "resume":
                printer.resume_print(tags=tags, user=user, params=params)
            else:
                abort(400, description="Unknown action")
        elif command == "cancel":
            if not activePrintjob:
                abort(
                    409,
                    description="Printer is neither printing nor paused, 'cancel' command cannot be performed",
                )
            printer.cancel_print(tags=tags, user=user, params=params)
    return NO_CONTENT


@api.route("/job", methods=["GET"])
@api_versioned
@Permissions.STATUS.require(403)
def jobState():
    response = _get_api_job_response()

    job_info = response.job
    job_info_pre_2_0_0 = apischema.ApiJobInfo_pre_2_0_0(
        file=job_info.file,
        estimatedPrintTime=job_info.estimatedPrintTime,
        lastPrintTime=None,
        filament=job_info.filament,
        user=job_info.user,
    )

    response_pre_2_0_0 = apischema.ApiJobResponse_pre_2_0_0(
        job=job_info_pre_2_0_0,
        progress=response.progress,
        state=response.state,
        error=response.error,
    )

    return jsonify(**response_pre_2_0_0.model_dump(by_alias=True))


@jobState.version(">=2.0.0")
@Permissions.STATUS.require(403)
def jobState_post_2_0_0():
    return jsonify(**_get_api_job_response().model_dump(by_alias=True, exclude_none=True))


def _get_api_job_response() -> apischema.ApiJobResponse:
    current_data = printer.get_current_data()

    file_data = current_data["job"].get("file", {})

    file = apischema.ApiJobFile(
        name=file_data.get("name"),
        path=file_data.get("path"),
        display=file_data.get("display"),
        origin=file_data.get("origin"),
        size=file_data.get("size"),
        date=file_data.get("date"),
        upload=file_data.get("upload"),
    )

    job_data = current_data["job"]
    job = apischema.ApiJobInfo(
        file=file,
        estimatedPrintTime=job_data.get("estimatedPrintTime"),
        filament=job_data.get("filament"),
        user=job_data.get("user"),
    )

    progress = apischema.ApiProgressInfo(**current_data["progress"])

    response = apischema.ApiJobResponse(
        job=job, progress=progress, state=current_data["state"]["text"]
    )
    if current_data["state"]["error"]:
        response.error = current_data["state"]["error"]

    return response
