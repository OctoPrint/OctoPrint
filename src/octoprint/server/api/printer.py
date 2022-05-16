__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import re

from flask import Response, abort, jsonify, request

from octoprint.access.permissions import Permissions
from octoprint.printer import UnknownScript
from octoprint.server import NO_CONTENT, printer, printerProfileManager
from octoprint.server.api import api
from octoprint.server.util.flask import get_json_command_from_request, no_firstrun_access
from octoprint.settings import settings, valid_boolean_trues

# ~~ Printer


@api.route("/printer", methods=["GET"])
@Permissions.STATUS.require(403)
def printerState():
    if not printer.is_operational():
        abort(409, description="Printer is not operational")

    # process excludes
    excludes = []
    if "exclude" in request.values:
        excludeStr = request.values["exclude"]
        if len(excludeStr.strip()) > 0:
            excludes = list(
                filter(
                    lambda x: x in ["temperature", "sd", "state"],
                    map(lambda x: x.strip(), excludeStr.split(",")),
                )
            )

    result = {}

    # add temperature information
    if "temperature" not in excludes:
        processor = lambda x: x
        heated_bed = printerProfileManager.get_current_or_default()["heatedBed"]
        heated_chamber = printerProfileManager.get_current_or_default()["heatedChamber"]
        if not heated_bed and not heated_chamber:
            processor = _keep_tools
        elif not heated_bed:
            processor = _delete_bed
        elif not heated_chamber:
            processor = _delete_chamber

        result.update({"temperature": _get_temperature_data(processor)})

    # add sd information
    if "sd" not in excludes and settings().getBoolean(["feature", "sdSupport"]):
        result.update({"sd": {"ready": printer.is_sd_ready()}})

    # add state information
    if "state" not in excludes:
        state = printer.get_current_data()["state"]
        result.update({"state": state})

    return jsonify(result)


# ~~ Tool


@api.route("/printer/tool", methods=["POST"])
@no_firstrun_access
@Permissions.CONTROL.require(403)
def printerToolCommand():
    if not printer.is_operational():
        abort(409, description="Printer is not operational")

    valid_commands = {
        "select": ["tool"],
        "target": ["targets"],
        "offset": ["offsets"],
        "extrude": ["amount"],
        "flowrate": ["factor"],
    }
    command, data, response = get_json_command_from_request(request, valid_commands)
    if response is not None:
        return response

    validation_regex = re.compile(r"tool\d+")

    tags = {"source:api", "api:printer.tool"}

    ##~~ tool selection
    if command == "select":
        tool = data["tool"]
        if not isinstance(tool, str) or re.match(validation_regex, tool) is None:
            abort(400, description="tool is invalid")

        printer.change_tool(tool, tags=tags)

    ##~~ temperature
    elif command == "target":
        targets = data["targets"]

        # make sure the targets are valid and the values are numbers
        validated_values = {}
        for tool, value in targets.items():
            if re.match(validation_regex, tool) is None:
                abort(400, description="targets contains invalid tool")
            if not isinstance(value, (int, float)):
                abort(400, description="targets contains invalid value")
            validated_values[tool] = value

        # perform the actual temperature commands
        for tool in validated_values.keys():
            printer.set_temperature(tool, validated_values[tool], tags=tags)

    ##~~ temperature offset
    elif command == "offset":
        offsets = data["offsets"]

        # make sure the targets are valid, the values are numbers and in the range [-50, 50]
        validated_values = {}
        for tool, value in offsets.items():
            if re.match(validation_regex, tool) is None:
                abort(400, description="offsets contains invalid tool")
            if not isinstance(value, (int, float)) or not -50 <= value <= 50:
                abort(400, description="offsets contains invalid value")
            validated_values[tool] = value

        # set the offsets
        printer.set_temperature_offset(validated_values)

    ##~~ extrusion
    elif command == "extrude":
        if printer.is_printing():
            # do not extrude when a print job is running
            abort(409, description="Printer is currently printing")

        amount = data["amount"]
        speed = data.get("speed", None)
        if not isinstance(amount, (int, float)):
            abort(400, description="amount is invalid")
        printer.extrude(amount, speed=speed, tags=tags)

    elif command == "flowrate":
        factor = data["factor"]
        if not isinstance(factor, (int, float)):
            abort(400, description="factor is invalid")
        try:
            printer.flow_rate(factor, tags=tags)
        except ValueError:
            abort(400, description="factor is invalid")

    return NO_CONTENT


@api.route("/printer/tool", methods=["GET"])
@no_firstrun_access
@Permissions.STATUS.require(403)
def printerToolState():
    if not printer.is_operational():
        abort(409, description="Printer is not operational")

    return jsonify(_get_temperature_data(_keep_tools))


##~~ Heated bed


@api.route("/printer/bed", methods=["POST"])
@no_firstrun_access
@Permissions.CONTROL.require(403)
def printerBedCommand():
    if not printer.is_operational():
        abort(409, description="Printer is not operational")

    if not printerProfileManager.get_current_or_default()["heatedBed"]:
        abort(409, description="Printer does not have a heated bed")

    valid_commands = {"target": ["target"], "offset": ["offset"]}
    command, data, response = get_json_command_from_request(request, valid_commands)
    if response is not None:
        return response

    tags = {"source:api", "api:printer.bed"}

    ##~~ temperature
    if command == "target":
        target = data["target"]

        # make sure the target is a number
        if not isinstance(target, (int, float)):
            abort(400, description="target is invalid")

        # perform the actual temperature command
        printer.set_temperature("bed", target, tags=tags)

    ##~~ temperature offset
    elif command == "offset":
        offset = data["offset"]

        # make sure the offset is valid
        if not isinstance(offset, (int, float)) or not -50 <= offset <= 50:
            abort(400, description="offset is invalid")

        # set the offsets
        printer.set_temperature_offset({"bed": offset})

    return NO_CONTENT


@api.route("/printer/bed", methods=["GET"])
@no_firstrun_access
@Permissions.STATUS.require(403)
def printerBedState():
    if not printer.is_operational():
        abort(409, description="Printer is not operational")

    if not printerProfileManager.get_current_or_default()["heatedBed"]:
        abort(409, description="Printer does not have a heated bed")

    data = _get_temperature_data(_keep_bed)
    if isinstance(data, Response):
        return data
    else:
        return jsonify(data)


##~~ Heated chamber


@api.route("/printer/chamber", methods=["POST"])
@no_firstrun_access
@Permissions.CONTROL.require(403)
def printerChamberCommand():
    if not printer.is_operational():
        abort(409, description="Printer is not operational")

    if not printerProfileManager.get_current_or_default()["heatedChamber"]:
        abort(409, description="Printer does not have a heated chamber")

    valid_commands = {"target": ["target"], "offset": ["offset"]}
    command, data, response = get_json_command_from_request(request, valid_commands)
    if response is not None:
        return response

    tags = {"source:api", "api:printer.chamber"}

    ##~~ temperature
    if command == "target":
        target = data["target"]

        # make sure the target is a number
        if not isinstance(target, (int, float)):
            abort(400, description="target is invalid")

        # perform the actual temperature command
        printer.set_temperature("chamber", target, tags=tags)

    ##~~ temperature offset
    elif command == "offset":
        offset = data["offset"]

        # make sure the offset is valid
        if not isinstance(offset, (int, float)) or not -50 <= offset <= 50:
            abort(400, description="offset is invalid")

        # set the offsets
        printer.set_temperature_offset({"chamber": offset})

    return NO_CONTENT


@api.route("/printer/chamber", methods=["GET"])
@no_firstrun_access
@Permissions.STATUS.require(403)
def printerChamberState():
    if not printer.is_operational():
        abort(409, description="Printer is not operational")

    if not printerProfileManager.get_current_or_default()["heatedChamber"]:
        abort(409, description="Printer does not have a heated chamber")

    data = _get_temperature_data(_keep_chamber)
    if isinstance(data, Response):
        return data
    else:
        return jsonify(data)


##~~ Print head


@api.route("/printer/printhead", methods=["POST"])
@no_firstrun_access
@Permissions.CONTROL.require(403)
def printerPrintheadCommand():
    valid_commands = {"jog": [], "home": ["axes"], "feedrate": ["factor"]}
    command, data, response = get_json_command_from_request(request, valid_commands)
    if response is not None:
        return response

    if not printer.is_operational() or (printer.is_printing() and command != "feedrate"):
        # do not jog when a print job is running or we don't have a connection
        abort(409, description="Printer is not operational or currently printing")

    tags = {"source:api", "api:printer.printhead"}

    valid_axes = ["x", "y", "z"]
    ##~~ jog command
    if command == "jog":
        # validate all jog instructions, make sure that the values are numbers
        validated_values = {}
        for axis in valid_axes:
            if axis in data:
                value = data[axis]
                if not isinstance(value, (int, float)):
                    abort(400, description="axis value is invalid")
                validated_values[axis] = value

        absolute = "absolute" in data and data["absolute"] in valid_boolean_trues
        speed = data.get("speed", None)

        # execute the jog commands
        printer.jog(validated_values, relative=not absolute, speed=speed, tags=tags)

    ##~~ home command
    elif command == "home":
        validated_values = []
        axes = data["axes"]
        for axis in axes:
            if axis not in valid_axes:
                abort(400, description="axis is invalid")
            validated_values.append(axis)

        # execute the home command
        printer.home(validated_values, tags=tags)

    elif command == "feedrate":
        factor = data["factor"]
        if not isinstance(factor, (int, float)):
            abort(400, description="factor is invalid")
        try:
            printer.feed_rate(factor, tags=tags)
        except ValueError:
            abort(400, description="factor is invalid")

    return NO_CONTENT


##~~ SD Card


@api.route("/printer/sd", methods=["POST"])
@no_firstrun_access
@Permissions.CONTROL.require(403)
def printerSdCommand():
    if not settings().getBoolean(["feature", "sdSupport"]):
        abort(404, description="SD support is disabled")

    if not printer.is_operational() or printer.is_printing() or printer.is_paused():
        abort(409, description="Printer is not operational or currently busy")

    valid_commands = {"init": [], "refresh": [], "release": []}
    command, data, response = get_json_command_from_request(request, valid_commands)
    if response is not None:
        return response

    tags = {"source:api", "api:printer.sd"}

    if command == "init":
        printer.init_sd_card(tags=tags)
    elif command == "refresh":
        printer.refresh_sd_files(tags=tags)
    elif command == "release":
        printer.release_sd_card(tags=tags)

    return NO_CONTENT


@api.route("/printer/sd", methods=["GET"])
@no_firstrun_access
@Permissions.STATUS.require(403)
def printerSdState():
    if not settings().getBoolean(["feature", "sdSupport"]):
        abort(404, description="SD support is disabled")

    return jsonify(ready=printer.is_sd_ready())


##~~ Commands


@api.route("/printer/command", methods=["POST"])
@no_firstrun_access
@Permissions.CONTROL.require(403)
def printerCommand():
    if not printer.is_operational():
        abort(409, description="Printer is not operational")

    if "application/json" not in request.headers["Content-Type"]:
        abort(400, description="Expected content type JSON")

    data = request.get_json()

    if data is None:
        abort(400, description="Malformed JSON body in request")

    if "command" in data and "commands" in data:
        abort(400, description="'command' and 'commands' are mutually exclusive")
    elif ("command" in data or "commands" in data) and "script" in data:
        abort(400, description="'command'/'commands' and 'script' are mutually exclusive")
    elif not ("command" in data or "commands" in data or "script" in data):
        abort(400, description="Need one of 'command', 'commands' or 'script'")

    parameters = {}
    if "parameters" in data:
        parameters = data["parameters"]

    tags = {"source:api", "api:printer.command"}

    if "command" in data or "commands" in data:
        if "command" in data:
            commands = [data["command"]]
        else:
            if not isinstance(data["commands"], (list, tuple)):
                abort(400, description="commands is invalid")
            commands = data["commands"]

        commandsToSend = []
        for command in commands:
            commandToSend = command
            if len(parameters) > 0:
                commandToSend = command % parameters
            commandsToSend.append(commandToSend)

        printer.commands(commandsToSend, tags=tags)

    elif "script" in data:
        script_name = data["script"]
        context = {"parameters": parameters}
        if "context" in data:
            context["context"] = data["context"]

        try:
            printer.script(script_name, context=context, tags=tags)
        except UnknownScript:
            abort(404, description="Unknown script")

    return NO_CONTENT


@api.route("/printer/command/custom", methods=["GET"])
@no_firstrun_access
@Permissions.CONTROL.require(403)
def getCustomControls():
    customControls = settings().get(["controls"])
    return jsonify(controls=customControls)


def _get_temperature_data(preprocessor):
    if not printer.is_operational():
        abort(409, description="Printer is not operational")

    tempData = printer.get_current_temperatures()

    if "history" in request.values and request.values["history"] in valid_boolean_trues:
        history = printer.get_temperature_history()

        limit = 300
        if "limit" in request.values and str(request.values["limit"]).isnumeric():
            limit = int(request.values["limit"])

        limit = min(limit, len(history))

        tempData.update(
            {"history": list(map(lambda x: preprocessor(x), history[-limit:]))}
        )

    return preprocessor(tempData)


def _keep_tools(x):
    return _delete_from_data(x, lambda k: not k.startswith("tool") and k != "history")


def _keep_bed(x):
    return _delete_from_data(x, lambda k: k != "bed" and k != "history")


def _delete_bed(x):
    return _delete_from_data(x, lambda k: k == "bed")


def _keep_chamber(x):
    return _delete_from_data(x, lambda k: k != "chamber" and k != "history")


def _delete_chamber(x):
    return _delete_from_data(x, lambda k: k == "chamber")


def _delete_from_data(x, key_matcher):
    data = dict(x)
    # must make list of keys first to avoid
    # RuntimeError: dictionary changed size during iteration
    for k in list(data.keys()):
        if key_matcher(k):
            del data[k]
    return data
