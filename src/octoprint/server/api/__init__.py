__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import datetime
import logging

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    g,
    jsonify,
    make_response,
    request,
    session,
)
from flask_login import current_user, login_user, logout_user
from werkzeug.exceptions import HTTPException

import octoprint.access.users
import octoprint.plugin
import octoprint.server
import octoprint.util.net as util_net
from octoprint.access import auth_log
from octoprint.access.permissions import Permissions
from octoprint.events import Events, eventManager
from octoprint.server import NO_CONTENT
from octoprint.server.util import (
    LoginMechanism,
    corsRequestHandler,
    corsResponseHandler,
    csrfRequestHandler,
    loginFromApiKeyRequestHandler,
    loginFromAuthorizationHeaderRequestHandler,
    noCachingExceptGetResponseHandler,
)
from octoprint.server.util.flask import (
    get_json_command_from_request,
    limit,
    no_firstrun_access,
    passive_login,
    session_signature,
    to_api_credentials_seen,
)
from octoprint.settings import settings as s
from octoprint.settings import valid_boolean_trues
from octoprint.vendor.flask_principal import Identity, identity_changed

# ~~ init api blueprint, including sub modules

api = Blueprint("api", __name__)

from . import access as api_access  # noqa: F401,E402
from . import connection as api_connection  # noqa: F401,E402
from . import files as api_files  # noqa: F401,E402
from . import job as api_job  # noqa: F401,E402
from . import languages as api_languages  # noqa: F401,E402
from . import printer as api_printer  # noqa: F401,E402
from . import printer_profiles as api_printer_profiles  # noqa: F401,E402
from . import settings as api_settings  # noqa: F401,E402
from . import slicing as api_slicing  # noqa: F401,E402
from . import system as api_system  # noqa: F401,E402
from . import timelapse as api_timelapse  # noqa: F401,E402
from . import users as api_users  # noqa: F401,E402

VERSION = "0.1"

api.after_request(noCachingExceptGetResponseHandler)

api.before_request(corsRequestHandler)
api.before_request(loginFromAuthorizationHeaderRequestHandler)
api.before_request(loginFromApiKeyRequestHandler)
api.before_request(csrfRequestHandler)
api.after_request(corsResponseHandler)

# ~~ data from plugins


@api.route("/plugin/<string:name>", methods=["GET"])
def pluginData(name):
    api_plugins = octoprint.plugin.plugin_manager().get_filtered_implementations(
        lambda p: p._identifier == name, octoprint.plugin.SimpleApiPlugin
    )
    if not api_plugins:
        abort(404)

    if len(api_plugins) > 1:
        abort(500, description="More than one api provider registered, can't proceed")

    try:
        api_plugin = api_plugins[0]
        if api_plugin.is_api_adminonly() and not current_user.is_admin:
            abort(403)

        response = api_plugin.on_api_get(request)

        if response is not None:
            message = (
                "Rewriting response from {} to use abort(msg, code) - please "
                "consider upgrading the implementation accordingly".format(name)
            )
            if (
                isinstance(response, Response)
                and response.mimetype == "text/html"
                and response.status_code >= 300
            ):
                # this actually looks like an error response
                logging.getLogger(__name__).info(message)
                abort(response.status_code, description=response.data)
            elif (
                isinstance(response, tuple)
                and len(response) == 2
                and isinstance(response[0], (str, bytes))
                and response[1] >= 300
            ):
                # this actually looks like an error response
                logging.getLogger(__name__).info(message)
                abort(response[1], response[0])
            return response
        return NO_CONTENT
    except HTTPException:
        raise
    except Exception:
        logging.getLogger(__name__).exception(
            f"Error calling SimpleApiPlugin {name}", extra={"plugin": name}
        )
        return abort(500)


# ~~ commands for plugins


@api.route("/plugin/<string:name>", methods=["POST"])
@no_firstrun_access
def pluginCommand(name):
    api_plugins = octoprint.plugin.plugin_manager().get_filtered_implementations(
        lambda p: p._identifier == name, octoprint.plugin.SimpleApiPlugin
    )

    if not api_plugins:
        abort(400)

    if len(api_plugins) > 1:
        abort(500, description="More than one api provider registered, can't proceed")

    api_plugin = api_plugins[0]
    try:
        valid_commands = api_plugin.get_api_commands()
        if valid_commands is None:
            abort(405)

        if api_plugin.is_api_adminonly() and not Permissions.ADMIN.can():
            abort(403)

        command, data, response = get_json_command_from_request(request, valid_commands)
        if response is not None:
            return response

        response = api_plugin.on_api_command(command, data)
        if response is not None:
            return response
        return NO_CONTENT
    except HTTPException:
        raise
    except Exception:
        logging.getLogger(__name__).exception(
            f"Error while executing SimpleApiPlugin {name}",
            extra={"plugin": name},
        )
        return abort(500)


# ~~ first run setup


@api.route("/setup/wizard", methods=["GET"])
def wizardState():
    if (
        not s().getBoolean(["server", "firstRun"])
        and octoprint.server.userManager.has_been_customized()
        and not Permissions.ADMIN.can()
    ):
        abort(403)

    seen_wizards = s().get(["server", "seenWizards"])

    result = {}
    wizard_plugins = octoprint.server.pluginManager.get_implementations(
        octoprint.plugin.WizardPlugin
    )
    for implementation in wizard_plugins:
        name = implementation._identifier
        try:
            required = implementation.is_wizard_required()
            details = implementation.get_wizard_details()
            version = implementation.get_wizard_version()
            ignored = octoprint.plugin.WizardPlugin.is_wizard_ignored(
                seen_wizards, implementation
            )
        except Exception:
            logging.getLogger(__name__).exception(
                "There was an error fetching wizard "
                "details for {}, ignoring".format(name),
                extra={"plugin": name},
            )
        else:
            result[name] = {
                "required": required,
                "details": details,
                "version": version,
                "ignored": ignored,
            }

    return jsonify(result)


@api.route("/setup/wizard", methods=["POST"])
def wizardFinish():
    if (
        not s().getBoolean(["server", "firstRun"])
        and octoprint.server.userManager.has_been_customized()
        and not Permissions.ADMIN.can()
    ):
        abort(403)

    data = {}
    try:
        data = request.get_json()
    except Exception:
        abort(400)

    if data is None:
        abort(400)

    if "handled" not in data:
        abort(400)
    handled = data["handled"]

    if s().getBoolean(["server", "firstRun"]):
        s().setBoolean(["server", "firstRun"], False)

    seen_wizards = dict(s().get(["server", "seenWizards"]))

    wizard_plugins = octoprint.server.pluginManager.get_implementations(
        octoprint.plugin.WizardPlugin
    )
    for implementation in wizard_plugins:
        name = implementation._identifier
        try:
            implementation.on_wizard_finish(name in handled)
            if name in handled:
                seen_wizards[name] = implementation.get_wizard_version()
        except Exception:
            logging.getLogger(__name__).exception(
                "There was an error finishing the "
                "wizard for {}, ignoring".format(name),
                extra={"plugin": name},
            )

    s().set(["server", "seenWizards"], seen_wizards)
    s().save()

    return NO_CONTENT


# ~~ system state


@api.route("/version", methods=["GET"])
@Permissions.STATUS.require(403)
def apiVersion():
    return jsonify(
        server=octoprint.server.VERSION,
        api=VERSION,
        text=f"OctoPrint {octoprint.server.DISPLAY_VERSION}",
    )


@api.route("/server", methods=["GET"])
@Permissions.STATUS.require(403)
def serverStatus():
    return jsonify(version=octoprint.server.VERSION, safemode=octoprint.server.safe_mode)


# ~~ Login/user handling


@api.route("/login", methods=["POST"])
@limit(
    "3/minute;5/10 minutes;10/hour",
    deduct_when=lambda response: response.status_code == 403,
    error_message="You have made too many failed login attempts. Please try again later.",
)
def login():
    data = request.get_json(silent=True)
    if not data:
        data = request.values

    if "user" in data and "pass" in data:
        username = data["user"]
        password = data["pass"]
        remote_addr = request.remote_addr

        if "remember" in data and data["remember"] in valid_boolean_trues:
            remember = True
        else:
            remember = False

        if "usersession.id" in session:
            _logout(current_user)

        user = octoprint.server.userManager.find_user(username)
        if user is not None:
            if octoprint.server.userManager.check_password(username, password):
                if not user.is_active:
                    auth_log(
                        f"Failed login attempt for user {username} from {remote_addr}, user is deactivated"
                    )
                    abort(403)

                user = octoprint.server.userManager.login_user(user)
                session["usersession.id"] = user.session
                session["usersession.signature"] = session_signature(
                    username, user.session
                )
                g.user = user

                login_user(user, remember=remember)
                identity_changed.send(
                    current_app._get_current_object(), identity=Identity(user.get_id())
                )
                session["login_mechanism"] = LoginMechanism.PASSWORD
                session["credentials_seen"] = datetime.datetime.now().timestamp()

                logging.getLogger(__name__).info(
                    "Actively logging in user {} from {}".format(
                        user.get_id(), remote_addr
                    )
                )

                response = user.as_dict()
                response["_is_external_client"] = s().getBoolean(
                    ["server", "ipCheck", "enabled"]
                ) and not util_net.is_lan_address(
                    remote_addr,
                    additional_private=s().get(["server", "ipCheck", "trustedSubnets"]),
                )
                response["_login_mechanism"] = session["login_mechanism"]
                response["_credentials_seen"] = to_api_credentials_seen(
                    session["credentials_seen"]
                )

                r = make_response(jsonify(response))
                r.delete_cookie("active_logout")

                eventManager().fire(
                    Events.USER_LOGGED_IN, payload={"username": user.get_id()}
                )
                auth_log(f"Logging in user {username} from {remote_addr} via credentials")

                return r

            else:
                auth_log(
                    f"Failed login attempt for user {username} from {remote_addr}, wrong password"
                )
        else:
            auth_log(
                f"Failed login attempt for user {username} from {remote_addr}, user is unknown"
            )

        abort(403)

    elif "passive" in data:
        return passive_login()

    abort(400, description="Neither user and pass attributes nor passive flag present")


@api.route("/logout", methods=["POST"])
def logout():
    username = None
    if current_user:
        username = current_user.get_id()

    # logout from user manager...
    _logout(current_user)

    # ... and from flask login (and principal)
    logout_user()

    # ... and send an active logout session cookie
    r = make_response(jsonify(octoprint.server.userManager.anonymous_user_factory()))
    r.set_cookie("active_logout", "true")

    if username:
        eventManager().fire(Events.USER_LOGGED_OUT, payload={"username": username})
        auth_log(f"Logging out user {username} from {request.remote_addr}")

    return r


def _logout(user):
    if "usersession.id" in session:
        del session["usersession.id"]
    if "login_mechanism" in session:
        del session["login_mechanism"]
    octoprint.server.userManager.logout_user(user)


@api.route("/currentuser", methods=["GET"])
def get_current_user():
    return jsonify(
        name=current_user.get_name(),
        permissions=[permission.key for permission in current_user.effective_permissions],
        groups=[group.key for group in current_user.groups],
    )


# ~~ Test utils


@api.route("/util/test", methods=["POST"])
@no_firstrun_access
@Permissions.ADMIN.require(403)
def utilTest():
    valid_commands = {
        "path": ["path"],
        "url": ["url"],
        "server": ["host", "port"],
        "resolution": ["name"],
        "address": [],
    }

    command, data, response = get_json_command_from_request(request, valid_commands)
    if response is not None:
        return response

    if command == "path":
        return _test_path(data)
    elif command == "url":
        return _test_url(data)
    elif command == "server":
        return _test_server(data)
    elif command == "resolution":
        return _test_resolution(data)
    elif command == "address":
        return _test_address(data)


def _test_path(data):
    import os

    from octoprint.util.paths import normalize

    path = normalize(data["path"], real=False)
    if not path:
        return jsonify(
            path=path,
            exists=False,
            typeok=False,
            broken_symlink=False,
            access=False,
            result=False,
        )

    unreal_path = path
    path = os.path.realpath(path)

    check_type = None
    check_access = []

    if "check_type" in data and data["check_type"] in ("file", "dir"):
        check_type = data["check_type"]

    if "check_access" in data:
        request_check_access = data["check_access"]
        if not isinstance(request_check_access, list):
            request_check_access = list(request_check_access)

        check_access = [
            check for check in request_check_access if check in ("r", "w", "x")
        ]

    allow_create_dir = data.get("allow_create_dir", False) and check_type == "dir"
    check_writable_dir = data.get("check_writable_dir", False) and check_type == "dir"
    if check_writable_dir and "w" not in check_access:
        check_access.append("w")

    # check if path exists
    exists = os.path.exists(path)
    if not exists:
        if os.path.islink(unreal_path):
            # broken symlink, see #2644
            logging.getLogger(__name__).error(
                "{} is a broken symlink pointing at non existing {}".format(
                    unreal_path, path
                )
            )
            return jsonify(
                path=unreal_path,
                exists=False,
                typeok=False,
                broken_symlink=True,
                access=False,
                result=False,
            )

        elif check_type == "dir" and allow_create_dir:
            try:
                os.makedirs(path)
            except Exception:
                logging.getLogger(__name__).exception(
                    f"Error while trying to create {path}"
                )
                return jsonify(
                    path=path,
                    exists=False,
                    typeok=False,
                    broken_symlink=False,
                    access=False,
                    result=False,
                )
            else:
                exists = True

    # check path type
    type_mapping = {"file": os.path.isfile, "dir": os.path.isdir}
    if check_type:
        typeok = type_mapping[check_type](path)
    else:
        typeok = exists

    # check if path allows requested access
    access_mapping = {"r": os.R_OK, "w": os.W_OK, "x": os.X_OK}
    if check_access:
        mode = 0
        for a in map(lambda x: access_mapping[x], check_access):
            mode |= a
        access = os.access(path, mode)
    else:
        access = exists

    if check_writable_dir and check_type == "dir":
        try:
            test_path = os.path.join(path, ".testballoon.txt")
            with open(test_path, "wb") as f:
                f.write(b"Test")
            os.remove(test_path)
        except Exception:
            logging.getLogger(__name__).exception(
                f"Error while testing if {path} is really writable"
            )
            return jsonify(
                path=path,
                exists=exists,
                typeok=typeok,
                broken_symlink=False,
                access=False,
                result=False,
            )

    return jsonify(
        path=path,
        exists=exists,
        typeok=typeok,
        broken_symlink=False,
        access=access,
        result=exists and typeok and access,
    )


def _test_url(data):
    import requests

    from octoprint import util as util

    class StatusCodeRange:
        def __init__(self, start=None, end=None):
            self.start = start
            self.end = end

        def __contains__(self, item):
            if not isinstance(item, int):
                return False
            if self.start and self.end:
                return self.start <= item < self.end
            elif self.start:
                return self.start <= item
            elif self.end:
                return item < self.end
            else:
                return False

        def as_dict(self):
            return {"start": self.start, "end": self.end}

    status_ranges = {
        "informational": StatusCodeRange(start=100, end=200),
        "success": StatusCodeRange(start=200, end=300),
        "redirection": StatusCodeRange(start=300, end=400),
        "client_error": StatusCodeRange(start=400, end=500),
        "server_error": StatusCodeRange(start=500, end=600),
        "normal": StatusCodeRange(end=400),
        "error": StatusCodeRange(start=400, end=600),
        "any": StatusCodeRange(start=100),
        "timeout": StatusCodeRange(start=0, end=1),
    }

    url = data["url"]
    method = data.get("method", "HEAD")
    timeout = 3.0
    valid_ssl = True
    check_status = [status_ranges["normal"]]
    content_type_whitelist = None
    content_type_blacklist = None

    if "timeout" in data:
        try:
            timeout = float(data["timeout"])
        except Exception:
            abort(400, description="timeout is invalid")

    if "validSsl" in data:
        valid_ssl = data["validSsl"] in valid_boolean_trues

    if "status" in data:
        request_status = data["status"]
        if not isinstance(request_status, list):
            request_status = [request_status]

        check_status = []
        for rs in request_status:
            if isinstance(rs, int):
                check_status.append([rs])
            else:
                if rs in status_ranges:
                    check_status.append(status_ranges[rs])
                else:
                    code = requests.codes[rs]
                    if code is not None:
                        check_status.append([code])

    if "content_type_whitelist" in data:
        if not isinstance(data["content_type_whitelist"], (list, tuple)):
            abort(400, description="content_type_whitelist must be a list of mime types")
        content_type_whitelist = list(
            map(util.parse_mime_type, data["content_type_whitelist"])
        )
    if "content_type_blacklist" in data:
        if not isinstance(data["content_type_whitelist"], (list, tuple)):
            abort(400, description="content_type_blacklist must be a list of mime types")
        content_type_blacklist = list(
            map(util.parse_mime_type, data["content_type_blacklist"])
        )

    response_result = None
    outcome = True
    status = 0
    try:
        with requests.request(
            method=method, url=url, timeout=timeout, verify=valid_ssl, stream=True
        ) as response:
            status = response.status_code
            outcome = outcome and any(map(lambda x: status in x, check_status))
            content_type = response.headers.get("content-type")

            response_result = {
                "headers": dict(response.headers),
                "content_type": content_type,
            }

            if not content_type and data.get("content_type_guess") in valid_boolean_trues:
                content = response.content
                content_type = util.guess_mime_type(bytearray(content))

            if not content_type:
                content_type = "application/octet-stream"

            response_result = {"assumed_content_type": content_type}

            parsed_content_type = util.parse_mime_type(content_type)

            in_whitelist = content_type_whitelist is None or any(
                map(
                    lambda x: util.mime_type_matches(parsed_content_type, x),
                    content_type_whitelist,
                )
            )
            in_blacklist = content_type_blacklist is not None and any(
                map(
                    lambda x: util.mime_type_matches(parsed_content_type, x),
                    content_type_blacklist,
                )
            )

            if not in_whitelist or in_blacklist:
                # we don't support this content type
                response.close()
                outcome = False

            elif "response" in data and (
                data["response"] in valid_boolean_trues
                or data["response"] in ("json", "bytes")
            ):
                if data["response"] == "json":
                    content = response.json()

                else:
                    import base64

                    content = base64.standard_b64encode(response.content)

                response_result["content"] = content
    except Exception:
        logging.getLogger(__name__).exception(
            f"Error while running a test {method} request on {url}"
        )
        outcome = False

    result = {"url": url, "status": status, "result": outcome}
    if response_result:
        result["response"] = response_result

    return jsonify(**result)


def _test_server(data):
    host = data["host"]
    try:
        port = int(data["port"])
    except Exception:
        abort(400, description="Invalid value for port")

    timeout = 3.05
    if "timeout" in data:
        try:
            timeout = float(data["timeout"])
        except Exception:
            abort(400, description="Invalid value for timeout")

    protocol = data.get("protocol", "tcp")
    if protocol not in ("tcp", "udp"):
        abort(400, description="Invalid value for protocol")

    from octoprint.util import server_reachable

    reachable = server_reachable(host, port, timeout=timeout, proto=protocol)

    result = {"host": host, "port": port, "protocol": protocol, "result": reachable}

    return jsonify(**result)


def _test_resolution(data):
    name = data["name"]

    from octoprint.util.net import resolve_host

    resolvable = len(resolve_host(name)) > 0

    result = {"name": name, "result": resolvable}

    return jsonify(**result)


def _test_address(data):
    import netaddr

    from octoprint.util.net import get_lan_ranges, sanitize_address

    remote_addr = data.get("address")
    if not remote_addr:
        remote_addr = request.remote_addr

    remote_addr = sanitize_address(remote_addr)
    ip = netaddr.IPAddress(remote_addr)

    lan_subnets = get_lan_ranges()

    detected_subnet = None
    for subnet in lan_subnets:
        if ip in subnet:
            detected_subnet = subnet
            break

    result = {
        "is_lan_address": detected_subnet is not None,
        "address": remote_addr,
    }

    if detected_subnet is not None:
        result["subnet"] = str(detected_subnet)

    return jsonify(**result)
