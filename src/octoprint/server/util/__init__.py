# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import base64

from octoprint.settings import settings
import octoprint.timelapse
import octoprint.server
from octoprint.users import ApiUser

from octoprint.util import deprecated
from octoprint.plugin import plugin_manager

import flask as _flask
import flask_login
import flask_principal
import logging

from . import flask
from . import sockjs
from . import tornado
from . import watchdog


@deprecated("API keys are no longer needed for anonymous access and thus this is now obsolete")
def enforceApiKeyRequestHandler():
	pass

apiKeyRequestHandler = deprecated("apiKeyRequestHandler has been renamed to enforceApiKeyRequestHandler")(enforceApiKeyRequestHandler)


def loginFromApiKeyRequestHandler():
	"""
	``before_request`` handler for blueprints which creates a login session for the provided api key (if available)

	App session keys are handled as anonymous keys here and ignored.
	"""
	try:
		if loginUserFromApiKey():
			_flask.g.login_via_apikey = True
	except InvalidApiKeyException:
		return _flask.make_response("Invalid API key", 403)


def loginFromAuthorizationHeaderRequestHandler():
	"""
	``before_request`` handler for creating login sessions based on the Authorization header.
	"""
	try:
		if loginUserFromAuthorizationHeader():
			_flask.g.login_via_header = True
	except InvalidApiKeyException:
		return _flask.make_response("Invalid API key", 403)


class InvalidApiKeyException(Exception): pass


def loginUserFromApiKey():
	apikey = get_api_key(_flask.request)

	if not apikey:
		return False

	user = get_user_for_apikey(apikey)
	if user is None:
		# invalid API key = no API key
		return False

	if not loginUser(user):
		return False

	return True


def loginUserFromAuthorizationHeader():
	authorization_header = get_authorization_header(_flask.request)
	user = get_user_for_authorization_header(authorization_header)
	return loginUser(user)


def loginUser(user, remember=False):
	"""
	Logs the provided ``user`` into Flask Login and Principal if not None and active

	Args:
		user: the User to login. May be None in which case the login will fail
		remember: Whether to set the ``remember`` flag on the Flask Login operation

	Returns: (bool) True if the login succeeded, False otherwise

	"""
	if user is not None and user.is_active() and flask_login.login_user(user, remember=remember):
		flask_principal.identity_changed.send(_flask.current_app._get_current_object(),
		                                      identity=flask_principal.Identity(user.get_id()))
		return True
	return False


def corsRequestHandler():
	"""
	``before_request`` handler for blueprints which sets CORS headers for OPTIONS requests if enabled
	"""
	if _flask.request.method == 'OPTIONS' and settings().getBoolean(["api", "allowCrossOrigin"]):
		# reply to OPTIONS request for CORS headers
		return optionsAllowOrigin(_flask.request)


def corsResponseHandler(resp):
	"""
	``after_request`` handler for blueprints for which CORS is supported.

	Sets ``Access-Control-Allow-Origin`` headers for ``Origin`` request header on response.
	"""

	# Allow crossdomain
	allowCrossOrigin = settings().getBoolean(["api", "allowCrossOrigin"])
	if _flask.request.method != 'OPTIONS' and 'Origin' in _flask.request.headers and allowCrossOrigin:
		resp.headers['Access-Control-Allow-Origin'] = _flask.request.headers['Origin']

	return resp


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
	resp.headers['Access-Control-Allow-Origin'] = request.headers['Origin']
	# Allow the actual method
	resp.headers['Access-Control-Allow-Methods'] = request.headers['Access-Control-Request-Method']
	# Allow for 10 seconds
	resp.headers['Access-Control-Max-Age'] = "10"

	# 'preflight' request contains the non-standard headers the real request will have (like X-Api-Key)
	customRequestHeaders = request.headers.get('Access-Control-Request-Headers', None)
	if customRequestHeaders is not None:
		# If present => allow them all
		resp.headers['Access-Control-Allow-Headers'] = customRequestHeaders

	return resp


def get_user_for_apikey(apikey):
	if apikey is not None:
		if apikey == settings().get(["api", "key"]) or octoprint.server.appSessionManager.validate(apikey):
			# master key or an app session key was used
			return ApiUser()

		if octoprint.server.userManager.enabled:
			user = octoprint.server.userManager.findUser(apikey=apikey)
			if user is not None:
				# user key was used
				return user

		apikey_hooks = plugin_manager().get_hooks("octoprint.accesscontrol.keyvalidator")
		for name, hook in apikey_hooks.items():
			try:
				user = hook(apikey)
				if user is not None:
					return user
			except:
				logging.getLogger(__name__).exception("Error running api key validator "
				                                      "for plugin {} and key {}".format(name, apikey),
				                                      extra=dict(plugin=name))
	return None


def get_user_for_remote_user_header(request):
	if not octoprint.server.userManager.enabled:
		return None

	if not settings().getBoolean(["accessControl", "trustRemoteUser"]):
		return None

	header = request.headers.get(settings().get(["accessControl", "remoteUserHeader"]))
	if header is None:
		return None

	user = octoprint.server.userManager.findUser(userid=header)

	if user is None and settings().getBoolean(["accessControl", "addRemoteUsers"]):
		octoprint.server.userManager.addUser(header, settings().generateApiKey(), active=True)
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

	header = header.replace('Basic ', '', 1)
	try:
		header = base64.b64decode(header)
	except TypeError:
		return None

	name, password = header.split(':', 1)
	if not octoprint.server.userManager.enabled:
		return None

	user = octoprint.server.userManager.findUser(userid=name)
	if settings().getBoolean(["accessControl", "checkBasicAuthenticationPassword"]) \
			and not octoprint.server.userManager.checkPassword(name, password):
		# password check enabled and password don't match
		return None

	return user


def get_api_key(request):
	# Check Flask GET/POST arguments
	if hasattr(request, "values") and "apikey" in request.values:
		return request.values["apikey"]

	# Check Tornado GET/POST arguments
	if hasattr(request, "arguments") and "apikey" in request.arguments \
		and len(request.arguments["apikey"]) > 0 and len(request.arguments["apikey"].strip()) > 0:
		return request.arguments["apikey"]

	# Check Tornado and Flask headers
	if "X-Api-Key" in request.headers.keys():
		return request.headers.get("X-Api-Key")

	return None


def get_authorization_header(request):
	# Tornado and Flask headers
	return request.headers.get("Authorization")


def get_plugin_hash():
	from octoprint.plugin import plugin_manager

	plugin_signature = lambda impl: "{}:{}".format(impl._identifier, impl._plugin_version)
	template_plugins = map(plugin_signature, plugin_manager().get_implementations(octoprint.plugin.TemplatePlugin))
	asset_plugins = map(plugin_signature, plugin_manager().get_implementations(octoprint.plugin.AssetPlugin))
	ui_plugins = sorted(set(template_plugins + asset_plugins))

	import hashlib
	plugin_hash = hashlib.sha1()
	plugin_hash.update(",".join(ui_plugins))
	return plugin_hash.hexdigest()
