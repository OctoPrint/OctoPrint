__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"

import collections
import logging
import re
import threading

import psutil
from flask import abort, jsonify, request, url_for
from flask_babel import gettext

from octoprint.access.permissions import Permissions
from octoprint.logging import prefix_multilines
from octoprint.plugin import plugin_manager
from octoprint.server import NO_CONTENT
from octoprint.server.api import api
from octoprint.server.util.flask import no_firstrun_access
from octoprint.settings import settings as s
from octoprint.systemcommands import system_command_manager
from octoprint.util.commandline import CommandlineCaller


@api.route("/system/usage", methods=["GET"])
@no_firstrun_access
@Permissions.SYSTEM.require(403)
def readUsageForFolders():
    return jsonify(usage=_usageForFolders())


@api.route("/system/info", methods=["GET"])
@no_firstrun_access
@Permissions.SYSTEM.require(403)
def getSystemInfo():
    from octoprint.cli.systeminfo import get_systeminfo
    from octoprint.server import (
        connectivityChecker,
        environmentDetector,
        printer,
        safe_mode,
    )
    from octoprint.util import dict_flatten

    systeminfo = get_systeminfo(
        environmentDetector,
        connectivityChecker,
        s(),
        {
            "browser.user_agent": request.headers.get("User-Agent"),
            "octoprint.safe_mode": safe_mode is not None,
            "systeminfo.generator": "systemapi",
        },
    )

    if printer and printer.is_operational():
        firmware_info = printer.firmware_info
        if firmware_info:
            systeminfo.update(
                dict_flatten({"firmware": firmware_info["name"]}, prefix="printer")
            )

    return jsonify(systeminfo=systeminfo)


@api.route("/system/startup", methods=["GET"])
@no_firstrun_access
@Permissions.SYSTEM.require(403)
def getStartupInformation():
    from octoprint.server import safe_mode
    from octoprint.settings import settings

    result = {}

    if safe_mode is not None:
        result["safe_mode"] = safe_mode

    flagged_basefolders = settings().flagged_basefolders
    if flagged_basefolders:
        result["flagged_basefolders"] = flagged_basefolders

    return jsonify(startup=result)


def _usageForFolders():
    data = {}
    for folder_name in s().get(["folder"]).keys():
        path = s().getBaseFolder(folder_name, check_writable=False)
        if path is not None:
            usage = psutil.disk_usage(path)
            data[folder_name] = {"free": usage.free, "total": usage.total}
    return data


@api.route("/system", methods=["POST"])
@no_firstrun_access
@Permissions.SYSTEM.require(403)
def performSystemAction():
    logging.getLogger(__name__).warning(
        f"Deprecated API call to /api/system made by {request.remote_addr}, should be migrated to use /system/commands/custom/<action>"
    )

    data = request.get_json(silent=True)
    if data is None:
        data = request.values

    if "action" not in data:
        abort(400, description="action is missing")

    return executeSystemCommand("custom", data["action"])


@api.route("/system/commands", methods=["GET"])
@no_firstrun_access
@Permissions.SYSTEM.require(403)
def retrieveSystemCommands():
    return jsonify(
        core=_to_client_specs(_get_core_command_specs()),
        plugin=_to_client_specs(_get_plugin_command_specs()),
        custom=_to_client_specs(_get_custom_command_specs()),
    )


@api.route("/system/commands/<string:source>", methods=["GET"])
@no_firstrun_access
@Permissions.SYSTEM.require(403)
def retrieveSystemCommandsForSource(source):
    if source == "core":
        specs = _get_core_command_specs()
    elif source == "custom":
        specs = _get_custom_command_specs()
    elif source == "plugin":
        specs = _get_plugin_command_specs()
    else:
        abort(404)

    return jsonify(_to_client_specs(specs))


@api.route("/system/commands/<string:source>/<string:command>", methods=["POST"])
@no_firstrun_access
@Permissions.SYSTEM.require(403)
def executeSystemCommand(source, command):
    logger = logging.getLogger(__name__)

    if command == "divider":
        abort(400, description="Dividers cannot be executed")

    command_spec = _get_command_spec(source, command)
    if not command_spec:
        abort(404)

    if "command" not in command_spec:
        abort(
            500, description="Command does not define a command to execute, can't proceed"
        )

    do_async = command_spec.get("async", False)
    do_ignore = command_spec.get("ignore", False)
    debug = command_spec.get("debug", False)

    if logger.isEnabledFor(logging.DEBUG) or debug:
        logger.info(
            "Performing command for {}:{}: {}".format(
                source, command, command_spec["command"]
            )
        )
    else:
        logger.info(f"Performing command for {source}:{command}")

    try:
        if "before" in command_spec and callable(command_spec["before"]):
            command_spec["before"]()
    except Exception as e:
        if not do_ignore:
            error = f'Command "before" for {source}:{command} failed: {e}'
            logger.warning(error)
            abort(500, description=error)

    try:

        def execute():
            # we run this with shell=True since we have to trust whatever
            # our admin configured as command and since we want to allow
            # shell-alike handling here...
            return_code, stdout_lines, stderr_lines = CommandlineCaller().call(
                command_spec["command"], shell=True
            )

            if not do_ignore and return_code != 0:
                stdout = "\n".join(stdout_lines)
                stderr = "\n".join(stderr_lines)
                error = f"Command for {source}:{command} failed with return code {return_code}:\n\nSTDOUT:\n{stdout}\n\nSTDERR:\n{stderr}"
                logger.warning(prefix_multilines(error, prefix="! "))
                if not do_async:
                    raise CommandFailed(error)

        if do_async:
            thread = threading.Thread(target=execute)
            thread.daemon = True
            thread.start()

        else:
            try:
                execute()
            except CommandFailed as exc:
                abort(500, exc.error)

    except Exception as e:
        if not do_ignore:
            error = f"Command for {source}:{command} failed: {e}"
            logger.warning(error)
            abort(500, error)

    return NO_CONTENT


def _to_client_specs(specs):
    result = list()
    for spec in specs.values():
        if "action" not in spec or "source" not in spec:
            continue
        copied = {
            k: v for k, v in spec.items() if k in ("source", "action", "name", "confirm")
        }
        copied["resource"] = url_for(
            ".executeSystemCommand",
            source=spec["source"],
            command=spec["action"],
            _external=True,
        )
        result.append(copied)
    return result


def _get_command_spec(source, action):
    if source == "core":
        return _get_core_command_spec(action)
    elif source == "custom":
        return _get_custom_command_spec(action)
    elif source == "plugin":
        return _get_plugin_command_spec(action)
    else:
        return None


def _get_core_command_specs():
    def enable_safe_mode():
        s().set(["server", "startOnceInSafeMode"], True)
        s().save()

    commands = collections.OrderedDict(
        shutdown={
            "command": system_command_manager().get_system_shutdown_command(),
            "name": gettext("Shutdown system"),
            "confirm": gettext(
                "<strong>You are about to shutdown the system.</strong></p><p>This action may disrupt any ongoing print jobs (depending on your printer's controller and general setup that might also apply to prints run directly from your printer's internal storage)."
            ),
        },
        reboot={
            "command": system_command_manager().get_system_restart_command(),
            "name": gettext("Reboot system"),
            "confirm": gettext(
                "<strong>You are about to reboot the system.</strong></p><p>This action may disrupt any ongoing print jobs (depending on your printer's controller and general setup that might also apply to prints run directly from your printer's internal storage)."
            ),
        },
        restart={
            "command": system_command_manager().get_server_restart_command(),
            "name": gettext("Restart OctoPrint"),
            "confirm": gettext(
                "<strong>You are about to restart the OctoPrint server.</strong></p><p>This action may disrupt any ongoing print jobs (depending on your printer's controller and general setup that might also apply to prints run directly from your printer's internal storage)."
            ),
        },
        restart_safe={
            "command": system_command_manager().get_server_restart_command(),
            "name": gettext("Restart OctoPrint in safe mode"),
            "confirm": gettext(
                "<strong>You are about to restart the OctoPrint server in safe mode.</strong></p><p>This action may disrupt any ongoing print jobs (depending on your printer's controller and general setup that might also apply to prints run directly from your printer's internal storage)."
            ),
            "before": enable_safe_mode,
        },
    )

    available_commands = collections.OrderedDict()
    for action, spec in commands.items():
        if not spec["command"]:
            continue
        spec.update({"action": action, "source": "core", "async": True, "debug": True})
        available_commands[action] = spec
    return available_commands


def _get_core_command_spec(action):
    available_actions = _get_core_command_specs()
    if action not in available_actions:
        logging.getLogger(__name__).warning(
            "Command for core action {} is not configured, you need to configure the command before it can be used".format(
                action
            )
        )
        return None

    return available_actions[action]


_plugin_action_regex = re.compile(r"[a-z0-9_-]+")


def _get_plugin_command_specs(plugin=None):
    specs = collections.OrderedDict()

    hooks = plugin_manager().get_hooks("octoprint.system.additional_commands")
    if plugin is not None:
        if plugin in hooks:
            hooks = {plugin: hooks[plugin]}
        else:
            hooks = {}

    for name, hook in hooks.items():
        try:
            plugin_specs = hook()
            for spec in plugin_specs:
                action = spec.get("action")
                if (
                    not action
                    or action == "divider"
                    or not _plugin_action_regex.match(action)
                ):
                    continue
                action = name.lower() + ":" + action

                copied = dict(spec)
                copied["source"] = "plugin"
                copied["action"] = action
                specs[action] = copied
        except Exception:
            logging.getLogger(__name__).exception(
                f"Error while fetching additional actions from plugin {name}",
                extra={"plugin": name},
            )
    return specs


def _get_plugin_command_spec(action):
    plugin = action.split(":", 1)[0]
    available_actions = _get_plugin_command_specs(plugin=plugin)
    return available_actions.get(action)


def _get_custom_command_specs():
    specs = collections.OrderedDict()
    dividers = 0
    for spec in s().get(["system", "actions"]):
        if "action" not in spec:
            continue
        copied = dict(spec)
        copied["source"] = "custom"

        action = spec["action"]
        if action == "divider":
            dividers += 1
            action = f"divider_{dividers}"
        specs[action] = copied
    return specs


def _get_custom_command_spec(action):
    available_actions = _get_custom_command_specs()
    return available_actions.get(action)


class CommandFailed(Exception):
    def __init__(self, error):
        self.error = error
