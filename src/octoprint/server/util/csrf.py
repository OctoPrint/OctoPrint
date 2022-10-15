"""CSRF double cookie implementation"""

__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

import flask

from octoprint.server.util.flask import OctoPrintFlaskResponse

exempt_views = set()


def _get_view_location(view):
    if isinstance(view, str):
        return view
    else:
        return f"{view.__module__}.{view.__name__}"


def add_exempt_view(view):
    exempt_views.add(_get_view_location(view))


def is_exempt(view):
    if not view:
        return False

    return _get_view_location(view) in exempt_views


def generate_csrf_token():
    import hashlib
    import os

    from itsdangerous import URLSafeTimedSerializer

    value = hashlib.sha1(os.urandom(64)).hexdigest()

    secret = flask.current_app.config["SECRET_KEY"]
    s = URLSafeTimedSerializer(secret, salt="octoprint-csrf-token")

    return s.dumps(value)


def validate_csrf_tokens(cookie, header):
    import hmac

    from itsdangerous import URLSafeTimedSerializer

    if cookie is None or header is None:
        return False

    secret = flask.current_app.config["SECRET_KEY"]
    s = URLSafeTimedSerializer(secret, salt="octoprint-csrf-token")

    try:
        # TODO: set max age for values, once we have a REST based heartbeat
        # that takes care of regular cookie refresh
        value_cookie = s.loads(cookie)
        value_header = s.loads(header)
        return hmac.compare_digest(value_cookie, value_header)
    except Exception:
        return False


def add_csrf_cookie(response):
    if not isinstance(response, OctoPrintFlaskResponse):
        response = flask.make_response(response)

    token = generate_csrf_token()
    response.set_cookie("csrf_token", token, httponly=False)
    return response


def validate_csrf_request(request):
    if request.method in ["GET", "HEAD", "OPTIONS"]:
        # Irrelevant method for CSRF, bypass
        return

    session = getattr(flask, "session", {})
    if len(session) == 0 or session.get("login_mechanism") == "apikey":
        # empty session, not a browser context
        return

    if is_exempt(request.endpoint):
        # marked as exempt, bypass
        return

    cookie = request.cookies.get("csrf_token", None)
    header = request.headers.get("X-CSRF-Token", None)

    if not validate_csrf_tokens(cookie, header):
        flask.abort(400, "CSRF validation failed")


def csrf_exempt(view):
    add_exempt_view(view)
    return view
