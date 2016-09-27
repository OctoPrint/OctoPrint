# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

from octoprint.settings import settings
import octoprint.timelapse
import octoprint.server
from octoprint.users import ApiUser

import flask as _flask

from . import flask
from . import sockjs
from . import tornado
from . import watchdog


def apiKeyRequestHandler():
	"""
	``before_request`` handler for blueprints for which all requests need to be made supplying an API key.

	This may be the UI_API_KEY, in which case the underlying request processing will directly take place, or it may be
	the global, an app specific or a user specific one. In any case it has to be present and must be valid, so anything
	other than the above types will result in the application denying the request.
	"""

	import octoprint.server

	if _flask.request.method == 'OPTIONS' and settings().getBoolean(["api", "allowCrossOrigin"]):
		return optionsAllowOrigin(_flask.request)

	if _flask.request.endpoint == "static" or _flask.request.endpoint.endswith(".static"):
		return

	apikey = get_api_key(_flask.request)
	if apikey is None:
		# no api key => 401
		return _flask.make_response("No API key provided", 401)

	if apikey == octoprint.server.UI_API_KEY:
		# ui api key => continue regular request processing
		return

	if not settings().get(["api", "enabled"]):
		# api disabled => 401
		return _flask.make_response("API disabled", 401)

	if apikey == settings().get(["api", "key"]):
		# global api key => continue regular request processing
		return

	if octoprint.server.appSessionManager.validate(apikey):
		# app session key => continue regular request processing
		return

	user = get_user_for_apikey(apikey)
	if user is not None:
		# user specific api key => continue regular request processing
		return

	# invalid api key => 401
	return _flask.make_response("Invalid API key", 401)


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
	if settings().get(["api", "enabled"]) and apikey is not None:
		if apikey == settings().get(["api", "key"]) or octoprint.server.appSessionManager.validate(apikey):
			# master key or an app session key was used
			return ApiUser()
		elif octoprint.server.userManager.enabled:
			# user key might have been used
			return octoprint.server.userManager.findUser(apikey=apikey)
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
