# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

from octoprint.settings import settings
import octoprint.timelapse
import octoprint.server
from octoprint.users import ApiUser

from octoprint.util import deprecated
from octoprint.plugin import plugin_manager

import flask as _flask
import logging

from . import flask
from . import sockjs
from . import tornado
from . import watchdog


def enforceApiKeyRequestHandler():
	"""
	``before_request`` handler for blueprints which makes sure an API key is provided
	"""

	import octoprint.server

	if _flask.request.method == 'OPTIONS':
		# we ignore OPTIONS requests here
		return

	if _flask.request.endpoint and (_flask.request.endpoint == "static" or _flask.request.endpoint.endswith(".static")):
		# no further handling for static resources
		return

	apikey = get_api_key(_flask.request)

	if apikey is None:
		return _flask.make_response("No API key provided", 401)

	if apikey != octoprint.server.UI_API_KEY and not settings().getBoolean(["api", "enabled"]):
		# api disabled => 401
		return _flask.make_response("API disabled", 401)

apiKeyRequestHandler = deprecated("apiKeyRequestHandler has been renamed to enforceApiKeyRequestHandler")(enforceApiKeyRequestHandler)


def loginFromApiKeyRequestHandler():
	"""
	``before_request`` handler for blueprints which creates a login session for the provided api key (if available)

	UI_API_KEY and app session keys are handled as anonymous keys here and ignored.
	"""

	apikey = get_api_key(_flask.request)
	
	if not apikey:
		return
	
	if apikey == octoprint.server.UI_API_KEY:
		return
	
	if octoprint.server.appSessionManager.validate(apikey):
		return
	
	user = get_user_for_apikey(apikey)
	if user is not None and _flask.ext.login.login_user(user, remember=False):
		_flask.ext.principal.identity_changed.send(_flask.current_app._get_current_object(),
		                                           identity=_flask.ext.principal.Identity(user.get_id()))
	else:
		return _flask.make_response("Invalid API key", 401)


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
	if settings().getBoolean(["api", "enabled"]) and apikey is not None:
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
				logging.getLogger(__name__).exception("Error running api key validator for plugin {} and key {}".format(name, apikey))
	return None


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
