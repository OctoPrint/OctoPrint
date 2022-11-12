__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import base64
import logging
import sys

PY3 = sys.version_info >= (3, 0)  # should now always be True, kept for plugins

import flask as _flask
import flask_login

import octoprint.server
import octoprint.timelapse
import octoprint.vendor.flask_principal as flask_principal
from octoprint.plugin import plugin_manager
from octoprint.settings import settings
from octoprint.util import deprecated, to_unicode

from . import flask, sockjs, tornado, watchdog  # noqa: F401


@deprecated(
    "API keys are no longer needed for anonymous access and thus this is now obsolete"
)
def enforceApiKeyRequestHandler():
    pass


apiKeyRequestHandler = deprecated(
    "apiKeyRequestHandler has been renamed to enforceApiKeyRequestHandler"
)(enforceApiKeyRequestHandler)


def loginFromApiKeyRequestHandler():
    """
    ``before_request`` handler for blueprints which creates a login session for the provided api key (if available)

    App session keys are handled as anonymous keys here and ignored.
    """
    try:
        if loginUserFromApiKey():
            _flask.g.login_via_apikey = True
    except InvalidApiKeyException:
        _flask.abort(403, "Invalid API key")


def loginFromAuthorizationHeaderRequestHandler():
    """
    ``before_request`` handler for creating login sessions based on the Authorization header.
    """
    try:
        if loginUserFromAuthorizationHeader():
            _flask.g.login_via_header = True
    except InvalidApiKeyException:
        _flask.abort(403, "Invalid credentials in Basic Authorization header")


class InvalidApiKeyException(Exception):
    pass


def loginUserFromApiKey():
    apikey = get_api_key(_flask.request)
    if not apikey:
        return False

    user = get_user_for_apikey(apikey)
    if user is None:
        # invalid API key = no API key
        raise InvalidApiKeyException("Invalid API key")

    return loginUser(user, login_mechanism="apikey")


def loginUserFromAuthorizationHeader():
    authorization_header = get_authorization_header(_flask.request)
    user = get_user_for_authorization_header(authorization_header)
    return loginUser(user, login_mechanism="authheader")


def loginUser(user, remember=False, login_mechanism=None):
    """
    Logs the provided ``user`` into Flask Login and Principal if not None and active

    Args:
            user: the User to login. May be None in which case the login will fail
            remember: Whether to set the ``remember`` flag on the Flask Login operation

    Returns: (bool) True if the login succeeded, False otherwise

    """
    if (
        user is not None
        and user.is_active
        and flask_login.login_user(user, remember=remember)
    ):
        flask_principal.identity_changed.send(
            _flask.current_app._get_current_object(),
            identity=flask_principal.Identity(user.get_id()),
        )
        if login_mechanism:
            _flask.session["login_mechanism"] = login_mechanism
        return True
    return False


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


def get_user_for_apikey(apikey):
    if apikey is not None:
        if apikey == settings().get(["api", "key"]):
            # master key was used
            return octoprint.server.userManager.api_user_factory()

        user = octoprint.server.userManager.find_user(apikey=apikey)
        if user is not None:
            # user key was used
            return user

        apikey_hooks = plugin_manager().get_hooks("octoprint.accesscontrol.keyvalidator")
        for name, hook in apikey_hooks.items():
            try:
                user = hook(apikey)
                if user is not None:
                    return user
            except Exception:
                logging.getLogger(__name__).exception(
                    "Error running api key validator "
                    "for plugin {} and key {}".format(name, apikey),
                    extra={"plugin": name},
                )
    return None


def get_user_for_remote_user_header(request):
    if not settings().getBoolean(["accessControl", "trustRemoteUser"]):
        return None

    header = request.headers.get(settings().get(["accessControl", "remoteUserHeader"]))
    if header is None:
        return None

    user = octoprint.server.userManager.findUser(userid=header)

    if user is None and settings().getBoolean(["accessControl", "addRemoteUsers"]):
        octoprint.server.userManager.addUser(
            header, settings().generateApiKey(), active=True
        )
        user = octoprint.server.userManager.findUser(userid=header)

    return user


def get_user_for_authorization_header(header):
    if not settings().getBoolean(["accessControl", "trustBasicAuthentication"]):
        return None

    if header is None:
        return None

    if not header.startswith("Basic "):
        # we currently only support Basic Authentication
        return None

    header = header.replace("Basic ", "", 1)
    try:
        header = to_unicode(base64.b64decode(header))
    except TypeError:
        return None

    name, password = header.split(":", 1)
    if not octoprint.server.userManager.enabled:
        return None

    user = octoprint.server.userManager.find_user(userid=name)
    if settings().getBoolean(
        ["accessControl", "checkBasicAuthenticationPassword"]
    ) and not octoprint.server.userManager.check_password(name, password):
        # password check enabled and password don't match
        return None

    return user


def get_api_key(request):
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


def get_authorization_header(request):
    # Tornado and Flask headers
    return request.headers.get("Authorization")


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
    logged_in = False

    try:
        if loginUserFromApiKey():
            logged_in = True
    except InvalidApiKeyException:
        pass  # ignored

    if not logged_in:
        loginUserFromAuthorizationHeader()

    flask.passive_login()
    return all(map(lambda p: p.can(), permissions))


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
        _flask.request.headers.get("X-Preemptive-Recording", "no") == "no"
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
        _flask.request.headers.get("X-Preemptive-Recording", "no") == "no"
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
            will be considered valid.

    Returns:
        bool: Whether the `url` passed validation or not.
    """
    from urllib.parse import urlparse

    parsed = urlparse(url)
    return parsed.scheme == "" and parsed.netloc == "" and parsed.path in allowed_paths
