# coding=utf-8
from __future__ import absolute_import
from flask import make_response

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import tornado.web
import flask
import flask.ext.login
import flask.ext.principal
import functools
import time
import uuid
import threading
import logging
import netaddr

from octoprint.settings import settings
import octoprint.server
import octoprint.users

from werkzeug.contrib.cache import SimpleCache


#~~ monkey patching

def enable_plugin_translations():
	import os
	from flask import _request_ctx_stack
	from babel import support
	import flask.ext.babel

	import octoprint.plugin

	def fixed_get_translations():
		"""Returns the correct gettext translations that should be used for
		this request.  This will never fail and return a dummy translation
		object if used outside of the request or if a translation cannot be
		found.
		"""
		logger = logging.getLogger(__name__)

		ctx = _request_ctx_stack.top
		if ctx is None:
			return None
		translations = getattr(ctx, 'babel_translations', None)
		if translations is None:
			locale = flask.ext.babel.get_locale()
			translations = support.Translations()

			plugins = octoprint.plugin.plugin_manager().enabled_plugins
			for name, plugin in plugins.items():
				dirname = os.path.join(plugin.location, 'translations')
				if not os.path.isdir(dirname):
					continue

				try:
					plugin_translations = support.Translations.load(dirname, [locale])
				except:
					logger.exception("Error while trying to load translations for plugin {name}".format(**locals()))
				else:
					translations = translations.merge(plugin_translations)

			dirname = os.path.join(ctx.app.root_path, 'translations')
			core_translations = support.Translations.load(dirname, [locale])
			translations = translations.merge(core_translations)

			ctx.babel_translations = translations
		return translations

	flask.ext.babel.get_translations = fixed_get_translations

#~~ passive login helper

def passive_login():
	if octoprint.server.userManager is not None:
		user = octoprint.server.userManager.login_user(flask.ext.login.current_user)
	else:
		user = flask.ext.login.current_user

	if user is not None and not user.is_anonymous():
		flask.g.user = user
		flask.ext.principal.identity_changed.send(flask.current_app._get_current_object(), identity=flask.ext.principal.Identity(user.get_id()))
		return flask.jsonify(user.asDict())
	elif settings().getBoolean(["accessControl", "autologinLocal"]) \
			and settings().get(["accessControl", "autologinAs"]) is not None \
			and settings().get(["accessControl", "localNetworks"]) is not None:

		autologinAs = settings().get(["accessControl", "autologinAs"])
		localNetworks = netaddr.IPSet([])
		for ip in settings().get(["accessControl", "localNetworks"]):
			localNetworks.add(ip)

		try:
			remoteAddr = get_remote_address(flask.request)
			if netaddr.IPAddress(remoteAddr) in localNetworks:
				user = octoprint.server.userManager.findUser(autologinAs)
				if user is not None:
					flask.g.user = user
					flask.ext.login.login_user(user)
					flask.ext.principal.identity_changed.send(flask.current_app._get_current_object(), identity=flask.ext.principal.Identity(user.get_id()))
					return flask.jsonify(user.asDict())
		except:
			logger = logging.getLogger(__name__)
			logger.exception("Could not autologin user %s for networks %r" % (autologinAs, localNetworks))

	return ("", 204)


#~~ cache decorator for cacheable views

_cache = SimpleCache()

def cached(timeout=5 * 60, key=lambda: "view/%s" % flask.request.path, unless=None, refreshif=None):
	def decorator(f):
		@functools.wraps(f)
		def decorated_function(*args, **kwargs):
			logger = logging.getLogger(__name__)

			# bypass the cache if "unless" condition is true
			if callable(unless) and unless():
				logger.debug("Cache for {path} bypassed, calling wrapped function".format(path=flask.request.path))
				return f(*args, **kwargs)

			# also bypass the cache if it's disabled completely
			if not settings().getBoolean(["devel", "cache", "enabled"]):
				logger.debug("Cache for {path} disabled, calling wrapped function".format(path=flask.request.path))
				return f(*args, **kwargs)

			cache_key = key()

			# only take the value from the cache if we are not required to refresh it from the wrapped function
			if not callable(refreshif) or not refreshif():
				rv = _cache.get(cache_key)
				if rv is not None:
					logger.debug("Serving entry for {path} from cache".format(path=flask.request.path))
					return rv

			# get value from wrapped function
			logger.debug("No cache entry or refreshing cache for {path}, calling wrapped function".format(path=flask.request.path))
			rv = f(*args, **kwargs)

			# store it in the cache
			_cache.set(cache_key, rv, timeout=timeout)

			return rv

		return decorated_function

	return decorator

def cache_check_headers():
	return "no-cache" in flask.request.cache_control or "no-cache" in flask.request.pragma

#~~ access validators for use with tornado


def admin_validator(request):
	"""
	Validates that the given request is made by an admin user, identified either by API key or existing Flask
	session.

	Must be executed in an existing Flask request context!

	:param request: The Flask request object
	"""

	user = _get_flask_user_from_request(request)
	if user is None or not user.is_authenticated() or not user.is_admin():
		raise tornado.web.HTTPError(403)


def user_validator(request):
	"""
	Validates that the given request is made by an authenticated user, identified either by API key or existing Flask
	session.

	Must be executed in an existing Flask request context!

	:param request: The Flask request object
	"""

	user = _get_flask_user_from_request(request)
	if user is None or not user.is_authenticated():
		raise tornado.web.HTTPError(403)


def _get_flask_user_from_request(request):
	"""
	Retrieves the current flask user from the request context. Uses API key if available, otherwise the current
	user session if available.

	:param request: flask request from which to retrieve the current user
	:return: the user or None if no user could be determined
	"""
	import octoprint.server.util
	import flask.ext.login
	from octoprint.settings import settings

	apikey = octoprint.server.util.get_api_key(request)
	if settings().get(["api", "enabled"]) and apikey is not None:
		user = octoprint.server.util.get_user_for_apikey(apikey)
	else:
		user = flask.ext.login.current_user

	return user


def redirect_to_tornado(request, target, code=302):
	"""
	Redirects from flask to tornado, flask request context must exist.

	:param request:
	:param target:
	:param code:
	:return:
	"""

	import flask

	requestUrl = request.url
	appBaseUrl = requestUrl[:requestUrl.find(flask.url_for("index") + "api")]

	redirectUrl = appBaseUrl + target
	if "?" in requestUrl:
		fragment = requestUrl[requestUrl.rfind("?"):]
		redirectUrl += fragment
	return flask.redirect(redirectUrl, code=code)


def restricted_access(func, api_enabled=True):
	"""
	If you decorate a view with this, it will ensure that first setup has been
	done for OctoPrint's Access Control plus that any conditions of the
	login_required decorator are met. It also allows to login using the masterkey or any
	of the user's apikeys if API access is enabled globally and for the decorated view.

	If OctoPrint's Access Control has not been setup yet (indicated by the "firstRun"
	flag from the settings being set to True and the userManager not indicating
	that it's user database has been customized from default), the decorator
	will cause a HTTP 403 status code to be returned by the decorated resource.

	If an API key is provided and it matches a known key, the user will be logged in and
	the view will be called directly. If the provided key doesn't match any known key,
	a HTTP 403 status code will be returned by the decorated resource.

	Otherwise the result of calling login_required will be returned.
	"""
	@functools.wraps(func)
	def decorated_view(*args, **kwargs):
		# if OctoPrint hasn't been set up yet, abort
		if settings().getBoolean(["server", "firstRun"]) and (octoprint.server.userManager is None or not octoprint.server.userManager.hasBeenCustomized()):
			return flask.make_response("OctoPrint isn't setup yet", 403)

		# if API is globally enabled, enabled for this request and an api key is provided that is not the current UI API key, try to use that
		apikey = octoprint.server.util.get_api_key(flask.request)
		if settings().get(["api", "enabled"]) and api_enabled and apikey is not None and apikey != octoprint.server.UI_API_KEY:
			user = octoprint.server.util.get_user_for_apikey(apikey)

			if user is None:
				return flask.make_response("Invalid API key", 401)
			if flask.ext.login.login_user(user, remember=False):
				flask.ext.principal.identity_changed.send(flask.current_app._get_current_object(), identity=flask.ext.principal.Identity(user.get_id()))
				return func(*args, **kwargs)

		# call regular login_required decorator
		return flask.ext.login.login_required(func)(*args, **kwargs)
	return decorated_view


class AppSessionManager(object):

	VALIDITY_UNVERIFIED = 1 * 60 # 1 minute
	VALIDITY_VERIFIED = 2 * 60 * 60 # 2 hours

	def __init__(self):
		self._sessions = dict()
		self._oldest = None
		self._mutex = threading.RLock()

		self._logger = logging.getLogger(__name__)

	def create(self):
		self._clean_sessions()

		key = ''.join('%02X' % ord(z) for z in uuid.uuid4().bytes)
		created = time.time()
		valid_until = created + self.__class__.VALIDITY_UNVERIFIED

		with self._mutex:
			self._sessions[key] = (created, False, valid_until)
		return key, valid_until

	def remove(self, key):
		with self._mutex:
			if not key in self._sessions:
				return
			del self._sessions[key]

	def verify(self, key):
		self._clean_sessions()

		if not key in self._sessions:
			return False

		with self._mutex:
			created, verified, _ = self._sessions[key]
			if verified:
				return False

			valid_until = created + self.__class__.VALIDITY_VERIFIED
			self._sessions[key] = created, True, created + self.__class__.VALIDITY_VERIFIED

		return key, valid_until

	def validate(self, key):
		self._clean_sessions()
		return key in self._sessions and self._sessions[key][1]

	def _clean_sessions(self):
		if self._oldest is not None and self._oldest > time.time():
			return

		with self._mutex:
			self._oldest = None
			for key, value in self._sessions.items():
				created, verified, valid_until = value
				if not verified:
					valid_until = created + self.__class__.VALIDITY_UNVERIFIED

				if valid_until < time.time():
					del self._sessions[key]
				elif self._oldest is None or valid_until < self._oldest:
					self._oldest = valid_until

			self._logger.debug("App sessions after cleanup: %r" % self._sessions)


def get_remote_address(request):
	forwardedFor = request.headers.get("X-Forwarded-For", None)
	if forwardedFor is not None:
		return forwardedFor.split(",")[0]
	return request.remote_addr


def get_json_command_from_request(request, valid_commands):
	if not "application/json" in request.headers["Content-Type"]:
		return None, None, make_response("Expected content-type JSON", 400)

	data = request.json
	if not "command" in data.keys() or not data["command"] in valid_commands.keys():
		return None, None, make_response("Expected valid command", 400)

	command = data["command"]
	for parameter in valid_commands[command]:
		if not parameter in data:
			return None, None, make_response("Mandatory parameter %s missing for command %s" % (parameter, command), 400)

	return command, data, None
