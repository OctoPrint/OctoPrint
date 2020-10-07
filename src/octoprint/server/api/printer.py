# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import re

from flask import Response, jsonify, make_response, request
from past.builtins import basestring, long, unicode
from werkzeug.exceptions import BadRequest

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
        return make_response("Printer is not operational", 409)

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
        return make_response("Printer is not operational", 409)

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
        if not isinstance(tool, basestring) or re.match(validation_regex, tool) is None:
            return make_response("Invalid tool: %s" % tool, 400)
        if not tool.startswith("tool"):
            return make_response("Invalid tool for selection: %s" % tool, 400)

        printer.change_tool(tool, tags=tags)

    ##~~ temperature
    elif command == "target":
        targets = data["targets"]

        # make sure the targets are valid and the values are numbers
        validated_values = {}
        for tool, value in targets.items():
            if re.match(validation_regex, tool) is None:
                return make_response(
                    "Invalid target for setting temperature: %s" % tool, 400
                )
            if not isinstance(value, (int, long, float)):
                return make_response("Not a number for %s: %r" % (tool, value), 400)
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
                return make_response(
                    "Invalid target for setting temperature: %s" % tool, 400
                )
            if not isinstance(value, (int, long, float)):
                return make_response("Not a number for %s: %r" % (tool, value), 400)
            if not -50 <= value <= 50:
                return make_response(
                    "Offset %s not in range [-50, 50]: %f" % (tool, value), 400
                )
            validated_values[tool] = value

        # set the offsets
        printer.set_temperature_offset(validated_values)

    ##~~ extrusion
    elif command == "extrude":
        if printer.is_printing():
            # do not extrude when a print job is running
            return make_response("Printer is currently printing", 409)

        amount = data["amount"]
        speed = data.get("speed", None)
        if not isinstance(amount, (int, long, float)):
            return make_response("Not a number for extrusion amount: %r" % amount, 400)
        printer.extrude(amount, speed=speed, tags=tags)

    elif command == "flowrate":
        factor = data["factor"]
        if not isinstance(factor, (int, long, float)):
            return make_response("Not a number for flow rate: %r" % factor, 400)
        try:
            printer.flow_rate(factor, tags=tags)
        except ValueError as e:
            return make_response("Invalid value for flow rate: %s" % str(e), 400)

    return NO_CONTENT


@api.route("/printer/tool", methods=["GET"])
@no_firstrun_access
@Permissions.STATUS.require(403)
def printerToolState():
    if not printer.is_operational():
        return make_response("Printer is not operational", 409)

    return jsonify(_get_temperature_data(_keep_tools))


##~~ Heated bed


@api.route("/printer/bed", methods=["POST"])
@no_firstrun_access
@Permissions.CONTROL.require(403)
def printerBedCommand():
    if not printer.is_operational():
        return make_response("Printer is not operational", 409)

    if not printerProfileManager.get_current_or_default()["heatedBed"]:
        return make_response("Printer does not have a heated bed", 409)

    valid_commands = {"target": ["target"], "offset": ["offset"]}
    command, data, response = get_json_command_from_request(request, valid_commands)
    if response is not None:
        return response

    tags = {"source:api", "api:printer.bed"}

    ##~~ temperature
    if command == "target":
        target = data["target"]

        # make sure the target is a number
        if not isinstance(target, (int, long, float)):
            return make_response("Not a number: %r" % target, 400)

        # perform the actual temperature command
        printer.set_temperature("bed", target, tags=tags)

    ##~~ temperature offset
    elif command == "offset":
        offset = data["offset"]

        # make sure the offset is valid
        if not isinstance(offset, (int, long, float)):
            return make_response("Not a number: %r" % offset, 400)
        if not -50 <= offset <= 50:
            return make_response("Offset not in range [-50, 50]: %f" % offset, 400)

        # set the offsets
        printer.set_temperature_offset({"bed": offset})

    return NO_CONTENT


@api.route("/printer/bed", methods=["GET"])
@no_firstrun_access
@Permissions.STATUS.require(403)
def printerBedState():
    if not printer.is_operational():
        return make_response("Printer is not operational", 409)

    if not printerProfileManager.get_current_or_default()["heatedBed"]:
        return make_response("Printer does not have a heated bed", 409)

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
        return make_response("Printer is not operational", 409)

    if not printerProfileManager.get_current_or_default()["heatedChamber"]:
        return make_response("Printer does not have a heated chamber", 409)

    valid_commands = {"target": ["target"], "offset": ["offset"]}
    command, data, response = get_json_command_from_request(request, valid_commands)
    if response is not None:
        return response

    tags = {"source:api", "api:printer.chamber"}

    ##~~ temperature
    if command == "target":
        target = data["target"]

        # make sure the target is a number
        if not isinstance(target, (int, long, float)):
            return make_response("Not a number: %r" % target, 400)

        # perform the actual temperature command
        printer.set_temperature("chamber", target, tags=tags)

    ##~~ temperature offset
    elif command == "offset":
        offset = data["offset"]

        # make sure the offset is valid
        if not isinstance(offset, (int, long, float)):
            return make_response("Not a number: %r" % offset, 400)
        if not -50 <= offset <= 50:
            return make_response("Offset not in range [-50, 50]: %f" % offset, 400)

        # set the offsets
        printer.set_temperature_offset({"chamber": offset})

    return NO_CONTENT


@api.route("/printer/chamber", methods=["GET"])
@no_firstrun_access
@Permissions.STATUS.require(403)
def printerChamberState():
    if not printer.is_operational():
        return make_response("Printer is not operational", 409)

    if not printerProfileManager.get_current_or_default()["heatedChamber"]:
        return make_response("Printer does not have a heated chamber", 409)

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
        return make_response("Printer is not operational or currently printing", 409)

    tags = {"source:api", "api:printer.printhead"}

    valid_axes = ["x", "y", "z"]
    ##~~ jog command
    if command == "jog":
        # validate all jog instructions, make sure that the values are numbers
        validated_values = {}
        for axis in valid_axes:
            if axis in data:
                value = data[axis]
                if not isinstance(value, (int, long, float)):
                    return make_response(
                        "Not a number for axis %s: %r" % (axis, value), 400
                    )
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
                return make_response("Invalid axis: %s" % axis, 400)
            validated_values.append(axis)

        # execute the home command
        printer.home(validated_values, tags=tags)

    elif command == "feedrate":
        factor = data["factor"]
        if not isinstance(factor, (int, long, float)):
            return make_response("Not a number for feed rate: %r" % factor, 400)
        try:
            printer.feed_rate(factor, tags=tags)
        except ValueError as e:
            return make_response("Invalid value for feed rate: %s" % str(e), 400)

    return NO_CONTENT


##~~ SD Card


@api.route("/printer/sd", methods=["POST"])
@no_firstrun_access
@Permissions.CONTROL.require(403)
def printerSdCommand():
    if not settings().getBoolean(["feature", "sdSupport"]):
        return make_response("SD support is disabled", 404)

    if not printer.is_operational() or printer.is_printing() or printer.is_paused():
        return make_response("Printer is not operational or currently busy", 409)

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
        return make_response("SD support is disabled", 404)

    return jsonify(ready=printer.is_sd_ready())


##~~ Commands


@api.route("/printer/command", methods=["POST"])
@no_firstrun_access
@Permissions.CONTROL.require(403)
def printerCommand():
    if not printer.is_operational():
        return make_response("Printer is not operational", 409)

    if "application/json" not in request.headers["Content-Type"]:
        return make_response("Expected content type JSON", 400)

    try:
        data = request.get_json()
    except BadRequest:
        return make_response("Malformed JSON body in request", 400)

    if data is None:
        return make_response("Malformed JSON body in request", 400)

    if "command" in data and "commands" in data:
        return make_response("'command' and 'commands' are mutually exclusive", 400)
    elif ("command" in data or "commands" in data) and "script" in data:
        return make_response(
            "'command'/'commands' and 'script' are mutually exclusive", 400
        )
    elif not ("command" in data or "commands" in data or "script" in data):
        return make_response("Need one of 'command', 'commands' or 'script'", 400)

    parameters = {}
    if "parameters" in data:
        parameters = data["parameters"]

    tags = {"source:api", "api:printer.command"}

    if "command" in data or "commands" in data:
        if "command" in data:
            commands = [data["command"]]
        else:
            if not isinstance(data["commands"], (list, tuple)):
                return make_response("'commands' needs to be a list", 400)
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
            return make_response("Unknown script: {script_name}".format(**locals()), 404)

    return NO_CONTENT


@api.route("/printer/command/custom", methods=["GET"])
@no_firstrun_access
@Permissions.CONTROL.require(403)
def getCustomControls():
    customControls = settings().get(["controls"])
    return jsonify(controls=customControls)


def _get_temperature_data(preprocessor):
    if not printer.is_operational():
        return make_response("Printer is not operational", 409)

    tempData = printer.get_current_temperatures()

    if "history" in request.values and request.values["history"] in valid_boolean_trues:
        tempHistory = printer.get_temperature_history()

        limit = 300
        if "limit" in request.values and unicode(request.values["limit"]).isnumeric():
            limit = int(request.values["limit"])

        history = list(tempHistory)
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
