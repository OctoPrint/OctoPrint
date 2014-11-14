# coding=utf-8
from __future__ import absolute_import

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

from octoprint.settings import settings
import octoprint.server
import octoprint.users


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

