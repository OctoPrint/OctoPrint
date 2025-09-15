__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import base64
import datetime
import logging
import sys
from typing import Optional, Union

PY3 = sys.version_info >= (3, 0)  # should now always be True, kept for plugins

import flask as _flask
import flask_login

import octoprint.server
import octoprint.timelapse
from octoprint.plugin import plugin_manager
from octoprint.settings import settings
from octoprint.util import to_unicode
from octoprint.util.net import is_loopback_address

from . import flask, sockjs, tornado, watchdog  # noqa: F401


class LoginMechanism:
    PASSWORD = "password"
    REMEMBER_ME = "remember_me"
    AUTOLOGIN = "autologin"
    APIKEY = "apikey"
    AUTHHEADER = "authheader"
    REMOTE_USER = "remote_user"

    _REAUTHENTICATION_ENABLED = (PASSWORD, REMEMBER_ME, AUTOLOGIN)

    @classmethod
    def reauthentication_enabled(cls, login_mechanism):
        return login_mechanism in cls._REAUTHENTICATION_ENABLED

    @classmethod
    def to_log(cls, login_mechanism):
        if login_mechanism == cls.PASSWORD:
            return "credentials"
        elif login_mechanism == cls.REMEMBER_ME:
            return "Remember Me cookie"
        elif login_mechanism == cls.AUTOLOGIN:
            return "autologin"
        elif login_mechanism == cls.APIKEY:
            return "API Key"
        elif login_mechanism == cls.AUTHHEADER:
            return "Basic Authorization header"
        elif login_mechanism == cls.REMOTE_USER:
            return "Remote User header"
        return "unknown method"


def requireLoginRequestHandler():
    if _flask.request.endpoint.endswith(".static"):
        return

    if not octoprint.server.userManager.has_been_customized():
        return

    user = flask_login.current_user
    if user is None or user.is_anonymous or not user.is_active:
        _flask.abort(403)


def corsRequestHandler():
    """
    ``before_request`` handler for blueprints which sets CORS headers for OPTIONS requests if enabled
    """
    if _flask.request.method == "OPTIONS" and settings().getBoolean(
        ["api", "allowCrossOrigin"]
    ):
        # reply to OPTIONS request for CORS headers
        return optionsAllowOrigin(_flask.request)


def corsResponseHandler(resp):
    """
    ``after_request`` handler for blueprints for which CORS is supported.

    Sets ``Access-Control-Allow-Origin`` headers for ``Origin`` request header on response.
    """

    # Allow crossdomain
    allowCrossOrigin = settings().getBoolean(["api", "allowCrossOrigin"])
    if (
        _flask.request.method != "OPTIONS"
        and "Origin" in _flask.request.headers
        and allowCrossOrigin
    ):
        resp.headers["Access-Control-Allow-Origin"] = _flask.request.headers["Origin"]

    return resp


def csrfRequestHandler():
    """
    ``before_request`` handler for blueprints which checks for CRFS double token on
    relevant requests & methods.
    """
    from octoprint.server.util.csrf import validate_csrf_request

    if settings().getBoolean(["devel", "enableCsrfProtection"]):
        validate_csrf_request(_flask.request)


def csrfResponseHandler(resp):
    """
    ``after_request`` handler for updating the CSRF cookie on each response.
    """
    from octoprint.server.util.csrf import add_csrf_cookie

    return add_csrf_cookie(resp)


def noCachingResponseHandler(resp):
    """
    ``after_request`` handler for blueprints which shall set no caching headers
    on their responses.

    Sets ``Cache-Control``, ``Pragma`` and ``Expires`` headers accordingly
    to prevent all client side caching from taking place.
    """

    return flask.add_non_caching_response_headers(resp)


def noCachingExceptGetResponseHandler(resp):
    """
    ``after_request`` handler for blueprints which shall set no caching headers
    on their responses to any requests that are not sent with method ``GET``.

    See :func:`noCachingResponseHandler`.
    """

    if _flask.request.method == "GET":
        return flask.add_no_max_age_response_headers(resp)
    else:
        return flask.add_non_caching_response_headers(resp)


def optionsAllowOrigin(request):
    """
    Shortcut for request handling for CORS OPTIONS requests to set CORS headers.
    """

    resp = _flask.current_app.make_default_options_response()

    # Allow the origin which made the XHR
    resp.headers["Access-Control-Allow-Origin"] = request.headers["Origin"]
    # Allow the actual method
    resp.headers["Access-Control-Allow-Methods"] = request.headers[
        "Access-Control-Request-Method"
    ]
    # Allow for 10 seconds
    resp.headers["Access-Control-Max-Age"] = "10"

    # 'preflight' request contains the non-standard headers the real request will have (like X-Api-Key)
    customRequestHeaders = request.headers.get("Access-Control-Request-Headers", None)
    if customRequestHeaders is not None:
        # If present => allow them all
        resp.headers["Access-Control-Allow-Headers"] = customRequestHeaders

    return resp


def get_user_for_apikey(
    apikey: str, remote_address: str = None
) -> "Optional[octoprint.access.users.User]":
    """
    Tries to find a user based on the given API key.

    Will only perform any action if the API key is not None and not empty.

    If the API key is the master key, the master user will be returned.

    If the API key is a user key, the user will be returned.

    If the API key is neither, the key will be passed to all registered key validators
    and the first non-None result will be returned.

    Args:
        apikey (str): the API key to check
        remote_address (str): the (optional) remote address of the client

    Returns:
        octoprint.access.users.User: the user found, or None if none was found
    """
    if apikey is None:
        return None

    user = None

    if apikey == settings().get(["api", "key"]):  # TODO Remove in 1.13.0
        # global api key was used
        logging.getLogger(__name__).warning(
            "The global API key was just used. The global API key is deprecated and will cease to function with OctoPrint 1.13.0."
        )
        user = octoprint.server.userManager.api_user_factory()

    else:
        user = octoprint.server.userManager.find_user(apikey=apikey)

        if user is None:
            apikey_hooks = plugin_manager().get_hooks(
                "octoprint.accesscontrol.keyvalidator"
            )
            for name, hook in apikey_hooks.items():
                try:
                    user = hook(apikey)
                    if user is not None:
                        break
                except Exception:
                    logging.getLogger(__name__).exception(
                        "Error running api key validator for plugin {} and key {}".format(
                            name, apikey
                        ),
                        extra={"plugin": name},
                    )

            else:
                if is_loopback_address(remote_address):
                    plugin = plugin_manager().resolve_plugin_apikey(apikey)
                    if plugin:
                        user = octoprint.server.userManager.internal_user_factory()

    if user:
        _flask.session["login_mechanism"] = LoginMechanism.APIKEY
        _flask.session["credentials_seen"] = datetime.datetime.now().timestamp()
    return user


def get_user_for_remote_user_header(
    request: _flask.Request,
) -> "Optional[octoprint.access.users.User]":
    """
    Tries to find a user based on the configured remote user request header.

    Will only perform any action if the trustRemoteUser setting is enabled.
    """
    if not settings().getBoolean(["accessControl", "trustRemoteUser"]):
        return None

    header = request.headers.get(settings().get(["accessControl", "remoteUserHeader"]))
    if header is None:
        return None

    user = octoprint.server.userManager.find_user(userid=header)

    if user is None and settings().getBoolean(["accessControl", "addRemoteUsers"]):
        octoprint.server.userManager.add_user(
            header, settings().generateApiKey(), active=True
        )
        user = octoprint.server.userManager.find_user(userid=header)

    if user and settings().getBoolean(["accessControl", "trustRemoteGroups"]):
        groupHeader = request.headers.get(
            settings().get(["accessControl", "remoteGroupsHeader"])
        )
        if groupHeader:
            groups = groupHeader.split(",")
            mapping = settings().get(["accessControl", "remoteGroupsMapping"])
            if mapping:
                groups = [mapping.get(group, group) for group in groups]
            octoprint.server.userManager.change_user_groups(header, groups)

    if user:
        _flask.session["login_mechanism"] = LoginMechanism.REMOTE_USER
        _flask.session["credentials_seen"] = datetime.datetime.now().timestamp()
    return user


def get_user_for_authorization_header(
    request: _flask.Request, header: str = "Authorization"
) -> "Optional[octoprint.access.users.User]":
    """
    Tries to find a user based on the Authorization request header.

    Will only perform any action if the trustBasicAuthentication setting is enabled.

    If configured accordingly, will also check if the password used for the Basic Authentication
    matches the one stored for the user.

    Args:
        request: the request object
        header (str): the header to check for the authorization header, defaults to "Authorization"
    """

    value = request.headers.get(header)

    if not settings().getBoolean(["accessControl", "trustBasicAuthentication"]):
        return None

    if value is None:
        return None

    if not value.startswith("Basic "):
        # we only support Basic Authentication here
        return None

    value = value.replace("Basic ", "", 1)
    try:
        value = to_unicode(base64.b64decode(value))
    except TypeError:
        return None

    name, password = value.split(":", 1)
    if not octoprint.server.userManager.enabled:
        return None

    user = octoprint.server.userManager.find_user(userid=name)
    if settings().getBoolean(
        ["accessControl", "checkBasicAuthenticationPassword"]
    ) and not octoprint.server.userManager.check_password(name, password):
        # password check enabled and password don't match
        return None

    if user:
        _flask.session["login_mechanism"] = LoginMechanism.AUTHHEADER
        _flask.session["credentials_seen"] = datetime.datetime.now().timestamp()
    return user


def get_api_key(
    request: Union[_flask.Request, "tornado.httputil.HTTPServerRequest"],
) -> Optional[str]:
    """
    Extracts the API key from the given request.

    The request may be a Flask or Tornado request object. Attempts will
    be made to read the API key from the "apikey" request parameter,
    the "X-Api-Key" header, or the "Authorization" header in "Bearer" mode.

    Args:
        request: the request object, either a Flask or a Tornado request

    Returns:
        str: the API key, or None if not found
    """

    # Check Flask GET/POST arguments
    if hasattr(request, "values") and "apikey" in request.values:
        return request.values["apikey"]

    # Check Tornado GET/POST arguments
    if (
        hasattr(request, "arguments")
        and "apikey" in request.arguments
        and len(request.arguments["apikey"]) > 0
        and len(request.arguments["apikey"].strip()) > 0
    ):
        return request.arguments["apikey"]

    # Check Tornado and Flask headers
    if "X-Api-Key" in request.headers:
        return request.headers.get("X-Api-Key")

    # Check Tornado and Flask headers
    if "Authorization" in request.headers:
        header = request.headers.get("Authorization")
        if header.startswith("Bearer "):
            token = header.replace("Bearer ", "", 1)
            return token

    return None


def get_plugin_hash():
    from octoprint.plugin import plugin_manager

    plugin_signature = lambda impl: f"{impl._identifier}:{impl._plugin_version}"
    template_plugins = list(
        map(
            plugin_signature,
            plugin_manager().get_implementations(octoprint.plugin.TemplatePlugin),
        )
    )
    asset_plugins = list(
        map(
            plugin_signature,
            plugin_manager().get_implementations(octoprint.plugin.AssetPlugin),
        )
    )
    ui_plugins = sorted(set(template_plugins + asset_plugins))

    import hashlib

    plugin_hash = hashlib.sha1()
    plugin_hash.update(",".join(ui_plugins).encode("utf-8"))
    return plugin_hash.hexdigest()


def has_permissions(*permissions):
    """
    Determines if the current user (either from the session, api key or authorization
    header) has all of the requested permissions.

    Args:
        *permissions: list of all permissions required to pass the check

    Returns: True if the user has all permissions, False otherwise
    """
    flask.passive_login()
    return all(p.can() for p in permissions)


def require_fresh_login_with(permissions=None, user_id=None):
    """
    Requires a login with fresh credentials.

    Args:
        permissions: list of all permissions required to pass the check
        user_id: required user to pass the check

    Returns: a flask redirect response to return if a login is required, or None
    """

    from octoprint.server import current_user, userManager
    from octoprint.server.util.flask import credentials_checked_recently

    response = require_login_with(permissions=permissions, user_id=user_id)
    if response is not None:
        return response

    login_kwargs = {
        "redirect": _flask.request.script_root + _flask.request.full_path,
        "reauthenticate": "true",
        "user_id": current_user.get_id(),
    }
    if (
        not _flask.g.get("preemptive_recording_active", False)
        and userManager.has_been_customized()
    ):
        if not credentials_checked_recently():
            return _flask.redirect(_flask.url_for("login", **login_kwargs))

    return None


def require_login_with(permissions=None, user_id=None):
    """
    Requires a login with the given permissions and/or user id.

    Args:
        permissions: list of all permissions required to pass the check
        user_id: required user to pass the check

    Returns: a flask redirect response to return if a login is required, or None
    """

    from octoprint.server import current_user, userManager

    login_kwargs = {"redirect": _flask.request.script_root + _flask.request.full_path}
    if (
        not _flask.g.get("preemptive_recording_active", False)
        and userManager.has_been_customized()
    ):
        requires_login = False

        if permissions is not None and not has_permissions(*permissions):
            requires_login = True
            login_kwargs["permissions"] = ",".join([x.key for x in permissions])

        if user_id is not None and current_user.get_id() != user_id:
            requires_login = True
            login_kwargs["user_id"] = user_id

        if requires_login:
            return _flask.redirect(_flask.url_for("login", **login_kwargs))

    return None


def require_login(*permissions):
    """
    Returns a redirect response to the login view if the permission requirements are
    not met.

    Args:
        *permissions: a list of permissions required to pass the check

    Returns: a flask redirect response to return if a login is required, or None
    """
    from octoprint.server import userManager

    if not permissions:
        return None

    if (
        not _flask.g.get("preemptive_recording_active", False)
        and userManager.has_been_customized()
    ):
        if not has_permissions(*permissions):
            return _flask.redirect(
                _flask.url_for(
                    "login",
                    redirect=_flask.request.script_root + _flask.request.full_path,
                    permissions=",".join([x.key for x in permissions]),
                )
            )

    return None


def validate_local_redirect(url, allowed_paths):
    """Validates the given local redirect URL against the given allowed paths.

    An `url` is valid for a local redirect if it has neither scheme nor netloc defined,
    and its path is one of the given allowed paths.

    Args:
        url (str): URL to validate
        allowed_paths (List[str]): List of allowed paths, only paths contained
            or prefixed (if allowed path ends with "*") will be considered valid.

    Returns:
        bool: Whether the `url` passed validation or not.
    """
    from urllib.parse import urljoin, urlparse

    parsed = urlparse(url)
    path = urljoin("/", parsed.path)

    return (
        parsed.scheme == ""
        and parsed.netloc == ""
        and any(
            (path.startswith(x[:-1]) if x.endswith("*") else path == x)
            for x in allowed_paths
        )
    )
