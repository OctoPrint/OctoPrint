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
import flask.ext.assets
import webassets.updater
import webassets.utils
import functools
import contextlib
import time
import uuid
import threading
import logging
import netaddr
import os

from octoprint.settings import settings
import octoprint.server
import octoprint.users
import octoprint.plugin

from werkzeug.contrib.cache import BaseCache


#~~ monkey patching

def enable_additional_translations(default_locale="en", additional_folders=None):
	import os
	from flask import _request_ctx_stack
	from babel import support, Locale
	import flask.ext.babel

	if additional_folders is None:
		additional_folders = []

	logger = logging.getLogger(__name__)

	def fixed_list_translations(self):
		"""Returns a list of all the locales translations exist for.  The
		list returned will be filled with actual locale objects and not just
		strings.
		"""
		def list_translations(dirname):
			if not os.path.isdir(dirname):
				return []
			result = []
			for folder in os.listdir(dirname):
				locale_dir = os.path.join(dirname, folder, 'LC_MESSAGES')
				if not os.path.isdir(locale_dir):
					continue
				if filter(lambda x: x.endswith('.mo'), os.listdir(locale_dir)):
					result.append(Locale.parse(folder))
			if not result:
				result.append(Locale.parse(self._default_locale))
			return result

		dirs = additional_folders + [os.path.join(self.app.root_path, 'translations')]

		result = [Locale.parse(default_locale)]

		for dir in dirs:
			result += list_translations(dir)
		return result

	def fixed_get_translations():
		"""Returns the correct gettext translations that should be used for
		this request.  This will never fail and return a dummy translation
		object if used outside of the request or if a translation cannot be
		found.
		"""
		ctx = _request_ctx_stack.top
		if ctx is None:
			return None
		translations = getattr(ctx, 'babel_translations', None)
		if translations is None:
			locale = flask.ext.babel.get_locale()
			translations = support.Translations()

			if str(locale) != default_locale:
				# plugin translations
				plugins = octoprint.plugin.plugin_manager().enabled_plugins
				for name, plugin in plugins.items():
					dirs = map(lambda x: os.path.join(x, "_plugins", name), additional_folders) + [os.path.join(plugin.location, 'translations')]
					for dirname in dirs:
						if not os.path.isdir(dirname):
							continue

						try:
							plugin_translations = support.Translations.load(dirname, [locale])
						except:
							logger.exception("Error while trying to load translations for plugin {name}".format(**locals()))
						else:
							if isinstance(plugin_translations, support.Translations):
								translations = translations.merge(plugin_translations)
								logger.debug("Using translation folder {dirname} for locale {locale} of plugin {name}".format(**locals()))
								break
					else:
						logger.debug("No translations for locale {locale} for plugin {name}".format(**locals()))

				# core translations
				dirs = additional_folders + [os.path.join(ctx.app.root_path, 'translations')]
				for dirname in dirs:
					core_translations = support.Translations.load(dirname, [locale])
					if isinstance(core_translations, support.Translations):
						logger.debug("Using translation folder {dirname} for locale {locale} of core translations".format(**locals()))
						break
				else:
					logger.debug("No core translations for locale {locale}")
				translations = translations.merge(core_translations)

			ctx.babel_translations = translations
		return translations

	flask.ext.babel.Babel.list_translations = fixed_list_translations
	flask.ext.babel.get_translations = fixed_get_translations

def fix_webassets_cache():
	from webassets import cache

	error_logger = logging.getLogger(__name__ + ".fix_webassets_cache")

	def fixed_set(self, key, data):
		import os
		import tempfile
		import pickle
		import shutil

		if not os.path.exists(self.directory):
			error_logger.warn("Cache directory {} doesn't exist, not going "
			                  "to attempt to write cache file".format(self.directory))

		md5 = '%s' % cache.make_md5(self.V, key)
		filename = os.path.join(self.directory, md5)
		fd, temp_filename = tempfile.mkstemp(prefix='.' + md5,
		                                     dir=self.directory)
		try:
			with os.fdopen(fd, 'wb') as f:
				pickle.dump(data, f)
				f.flush()
			shutil.move(temp_filename, filename)
		except:
			os.remove(temp_filename)
			raise

	def fixed_get(self, key):
		import os
		import errno
		import warnings
		from webassets.cache import make_md5

		if not os.path.exists(self.directory):
			error_logger.warn("Cache directory {} doesn't exist, not going "
			                  "to attempt to read cache file".format(self.directory))
			return None

		try:
			hash = make_md5(self.V, key)
		except IOError as e:
			if e.errno != errno.ENOENT:
				raise
			return None

		filename = os.path.join(self.directory, '%s' % hash)
		try:
			f = open(filename, 'rb')
		except IOError as e:
			if e.errno != errno.ENOENT:
				raise
			return None
		try:
			result = f.read()
		finally:
			f.close()

		unpickled = webassets.cache.safe_unpickle(result)
		if unpickled is None:
			warnings.warn('Ignoring corrupted cache file %s' % filename)
		return unpickled

	cache.FilesystemCache.set = fixed_set
	cache.FilesystemCache.get = fixed_get

def fix_webassets_filtertool():
	from webassets.merge import FilterTool, log, MemoryHunk

	error_logger = logging.getLogger(__name__ + ".fix_webassets_filtertool")

	def fixed_wrap_cache(self, key, func):
		"""Return cache value ``key``, or run ``func``.
		"""
		if self.cache:
			if not self.no_cache_read:
				log.debug('Checking cache for key %s', key)
				content = self.cache.get(key)
				if not content in (False, None):
					log.debug('Using cached result for %s', key)
					return MemoryHunk(content)

		try:
			content = func().getvalue()
			if self.cache:
				try:
					log.debug('Storing result in cache with key %s', key,)
					self.cache.set(key, content)
				except:
					error_logger.exception("Got an exception while trying to save file to cache, not caching")
			return MemoryHunk(content)
		except:
			error_logger.exception("Got an exception while trying to apply filter, ignoring file")
			return MemoryHunk(u"")

	FilterTool._wrap_cache = fixed_wrap_cache

#~~ passive login helper

def passive_login():
	if octoprint.server.userManager.enabled:
		user = octoprint.server.userManager.login_user(flask.ext.login.current_user)
	else:
		user = flask.ext.login.current_user

	if user is not None and not user.is_anonymous():
		flask.ext.principal.identity_changed.send(flask.current_app._get_current_object(), identity=flask.ext.principal.Identity(user.get_id()))
		if hasattr(user, "get_session"):
			flask.session["usersession.id"] = user.get_session()
		flask.g.user = user
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

	return "", 204


#~~ cache decorator for cacheable views

class LessSimpleCache(BaseCache):
	"""
	Slightly improved version of :class:`SimpleCache`.

	Setting ``default_timeout`` or ``timeout`` to ``-1`` will have no timeout be applied at all.
	"""

	def __init__(self, threshold=500, default_timeout=300):
		BaseCache.__init__(self, default_timeout=default_timeout)
		self._cache = {}
		self.clear = self._cache.clear
		self._threshold = threshold

	def _prune(self):
		if self.over_threshold():
			now = time.time()
			for idx, (key, (expires, _)) in enumerate(self._cache.items()):
				if expires is not None and expires <= now or idx % 3 == 0:
					self._cache.pop(key, None)

	def get(self, key):
		import pickle
		now = time.time()
		expires, value = self._cache.get(key, (0, None))
		if expires is None or expires > now:
			return pickle.loads(value)

	def set(self, key, value, timeout=None):
		import pickle
		self._prune()
		self._cache[key] = (self.calculate_timeout(timeout=timeout),
		                    pickle.dumps(value, pickle.HIGHEST_PROTOCOL))

	def add(self, key, value, timeout=None):
		self.set(key, value, timeout=None)
		self._cache.setdefault(key, self._cache[key])

	def delete(self, key):
		self._cache.pop(key, None)

	def calculate_timeout(self, timeout=None):
		if timeout is None:
			timeout = self.default_timeout
		if timeout is -1:
			return None
		return time.time() + timeout

	def over_threshold(self):
		if self._threshold is None:
			return False
		return len(self._cache) > self._threshold

_cache = LessSimpleCache()

def cached(timeout=5 * 60, key=lambda: "view:%s" % flask.request.path, unless=None, refreshif=None, unless_response=None):
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
			rv = _cache.get(cache_key)

			# only take the value from the cache if we are not required to refresh it from the wrapped function
			if rv is not None and (not callable(refreshif) or not refreshif(rv)):
				logger.debug("Serving entry for {path} from cache".format(path=flask.request.path))
				if not "X-From-Cache" in rv.headers:
					rv.headers["X-From-Cache"] = "true"
				return rv

			# get value from wrapped function
			logger.debug("No cache entry or refreshing cache for {path} (key: {key}), calling wrapped function".format(path=flask.request.path, key=cache_key))
			rv = f(*args, **kwargs)

			# do not store if the "unless_response" condition is true
			if callable(unless_response) and unless_response(rv):
				logger.debug("Not caching result for {path}, bypassed".format(path=flask.request.path))
				return rv

			# store it in the cache
			_cache.set(cache_key, rv, timeout=timeout)

			return rv

		return decorated_function

	return decorator

def cache_check_headers():
	return "no-cache" in flask.request.cache_control or "no-cache" in flask.request.pragma

def cache_check_response_headers(response):
	if not isinstance(response, flask.Response):
		return False

	headers = response.headers

	if "Cache-Control" in headers and "no-cache" in headers["Cache-Control"]:
		return True

	if "Pragma" in headers and "no-cache" in headers["Pragma"]:
		return True

	if "Expires" in headers and headers["Expires"] in ("0", "-1"):
		return True

	return False


class PreemptiveCache(object):

	def __init__(self, cachefile):
		self.cachefile = cachefile

		self._lock = threading.RLock()
		self._logger = logging.getLogger(__name__ + "." + self.__class__.__name__)
		self._log_access = True

	def record(self, data, unless=None):
		if callable(unless) and unless():
			return

		entry_data = data
		if callable(entry_data):
			entry_data = entry_data()

		if entry_data is not None:
			from flask import request
			self.add_data(request.path, entry_data)

	@contextlib.contextmanager
	def disable_access_logging(self):
		with self._lock:
			self._log_access = False
			yield
			self._log_access = True

	def clean_all_data(self, cleanup_function):
		assert callable(cleanup_function)

		with self._lock:
			all_data = self.get_all_data()
			for root, entries in all_data.items():
				old_count = len(entries)
				entries = cleanup_function(root, entries)
				if not entries:
					del all_data[root]
					self._logger.debug("Removed root {} from preemptive cache".format(root))
				elif len(entries) < old_count:
					all_data[root] = entries
					self._logger.debug("Removed {} from preemptive cache for root {}".format(old_count - len(entries), root))
			self.set_all_data(all_data)

		return all_data

	def get_all_data(self):
		import yaml

		cache_data = None
		with self._lock:
			try:
				with open(self.cachefile, "r") as f:
					cache_data = yaml.safe_load(f)
			except IOError as e:
				import errno
				if e.errno != errno.ENOENT:
					raise
			except:
				self._logger.exception("Error while reading {}".format(self.cachefile))

		if cache_data is None:
			cache_data = dict()

		return cache_data

	def get_data(self, root):
		cache_data = self.get_all_data()
		return cache_data.get(root, dict())

	def set_all_data(self, data):
		from octoprint.util import atomic_write
		import yaml

		with self._lock:
			try:
				with atomic_write(self.cachefile, "wb") as handle:
					yaml.safe_dump(data, handle,default_flow_style=False, indent="    ", allow_unicode=True)
			except:
				self._logger.exception("Error while writing {}".format(self.cachefile))

	def set_data(self, root, data):
		with self._lock:
			all_data = self.get_all_data()
			all_data[root] = data
			self.set_all_data(all_data)

	def add_data(self, root, data):
		from octoprint.util import dict_filter

		def strip_ignored(d):
			return dict_filter(d, lambda k, v: not k.startswith("_"))

		def compare(a, b):
			return set(strip_ignored(a).items()) == set(strip_ignored(b).items())

		def split_matched_and_unmatched(entry, entries):
			matched = []
			unmatched = []

			for e in entries:
				if compare(e, entry):
					matched.append(e)
				else:
					unmatched.append(e)

			return matched, unmatched

		with self._lock:
			cache_data = self.get_all_data()

			if not root in cache_data:
				cache_data[root] = []

			existing, other = split_matched_and_unmatched(data, cache_data[root])

			def get_newest(entries):
				result = None
				for entry in entries:
					if "_timestamp" in entry and (result is None or ("_timestamp" in entry and result["_timestamp"] < entry["_timestamp"])):
						result = entry
				return result

			to_persist = get_newest(existing)
			if not to_persist:
				import copy
				to_persist = copy.deepcopy(data)
				to_persist["_timestamp"] = time.time()
				to_persist["_count"] = 1
				self._logger.info("Adding entry for {} and {!r}".format(root, to_persist))
			elif self._log_access:
				to_persist["_timestamp"] = time.time()
				to_persist["_count"] = to_persist.get("_count", 0) + 1
				self._logger.debug("Updating timestamp and counter for {} and {!r}".format(root, data))
			else:
				self._logger.debug("Not updating timestamp and counter for {} and {!r}, currently flagged as disabled".format(root, data))

			self.set_data(root, [to_persist] + other)


def preemptively_cached(cache, data, unless=None):
	def decorator(f):
		@functools.wraps(f)
		def decorated_function(*args, **kwargs):
			cache.record(data, unless=unless)
			return f(*args, **kwargs)
		return decorated_function
	return decorator


def etagged(etag):
	def decorator(f):
		@functools.wraps(f)
		def decorated_function(*args, **kwargs):
			rv = f(*args, **kwargs)
			if isinstance(rv, flask.Response):
				result = etag
				if callable(result):
					result = result(rv)
				if result:
					rv.set_etag(result)
			return rv
		return decorated_function
	return decorator


def lastmodified(date):
	def decorator(f):
		@functools.wraps(f)
		def decorated_function(*args, **kwargs):
			rv = f(*args, **kwargs)
			if not "Last-Modified" in rv.headers:
				result = date
				if callable(result):
					result = result(rv)

				if not isinstance(result, basestring):
					from werkzeug.http import http_date
					result = http_date(result)

				if result:
					rv.headers["Last-Modified"] = result
			return rv
		return decorated_function
	return decorator


def conditional(condition, met):
	def decorator(f):
		@functools.wraps(f)
		def decorated_function(*args, **kwargs):
			if callable(condition) and condition():
				# condition has been met, return met-response
				rv = met
				if callable(met):
					rv = met()
				return rv

			# condition hasn't been met, call decorated function
			return f(*args, **kwargs)
		return decorated_function
	return decorator


def check_etag(etag):
	return flask.request.method in ("GET", "HEAD") and \
	       flask.request.if_none_match and \
	       etag in flask.request.if_none_match


def check_lastmodified(lastmodified):
	return flask.request.method in ("GET", "HEAD") and \
	       flask.request.if_modified_since and \
	       lastmodified >= flask.request.if_modified_since


def add_non_caching_response_headers(response):
	response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
	response.headers["Pragma"] = "no-cache"
	response.headers["Expires"] = "-1"
	return response


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


def restricted_access(func):
	"""
	If you decorate a view with this, it will ensure that first setup has been
	done for OctoPrint's Access Control plus that any conditions of the
	login_required decorator are met. It also allows to login using the masterkey or any
	of the user's apikeys if API access is enabled globally and for the decorated view.

	If OctoPrint's Access Control has not been setup yet (indicated by the "firstRun"
	flag from the settings being set to True and the userManager not indicating
	that it's user database has been customized from default), the decorator
	will cause a HTTP 403 status code to be returned by the decorated resource.

	If the API key matches the UI API key, the result of calling login_required for the
	view will be returned (browser session mode).

	Otherwise the API key will be attempted to be resolved to a user. If that is
	successful the user will be logged in and the view will be called directly.
	Otherwise a HTTP 401 status code will be returned.
	"""
	@functools.wraps(func)
	def decorated_view(*args, **kwargs):
		# if OctoPrint hasn't been set up yet, abort
		if settings().getBoolean(["server", "firstRun"]) and settings().getBoolean(["accessControl", "enabled"]) and (octoprint.server.userManager is None or not octoprint.server.userManager.hasBeenCustomized()):
			return flask.make_response("OctoPrint isn't setup yet", 403)

		apikey = octoprint.server.util.get_api_key(flask.request)
		if apikey == octoprint.server.UI_API_KEY:
			# UI API key => call regular login_required decorator, we are using browser sessions here
			return flask.ext.login.login_required(func)(*args, **kwargs)

		# try to determine user for key
		user = octoprint.server.util.get_user_for_apikey(apikey)
		if user is None:
			# no user or no key => go away
			return flask.make_response("Invalid API key", 401)

		if not flask.ext.login.login_user(user, remember=False):
			# user for API key could not be logged in => go away
			return flask.make_response("Invalid API key", 401)

		flask.ext.principal.identity_changed.send(flask.current_app._get_current_object(), identity=flask.ext.principal.Identity(user.get_id()))
		return func(*args, **kwargs)

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
	content_type = request.headers.get("Content-Type", None)
	if content_type is None or not "application/json" in content_type:
		return None, None, make_response("Expected content-type JSON", 400)

	data = request.json
	if not "command" in data.keys() or not data["command"] in valid_commands.keys():
		return None, None, make_response("Expected valid command", 400)

	command = data["command"]
	for parameter in valid_commands[command]:
		if not parameter in data:
			return None, None, make_response("Mandatory parameter %s missing for command %s" % (parameter, command), 400)

	return command, data, None

##~~ Flask-Assets resolver with plugin asset support

class PluginAssetResolver(flask.ext.assets.FlaskResolver):

	def split_prefix(self, ctx, item):
		app = ctx.environment._app
		if item.startswith("plugin/"):
			try:
				prefix, plugin, name = item.split("/", 2)
				blueprint = prefix + "." + plugin

				directory = flask.ext.assets.get_static_folder(app.blueprints[blueprint])
				item = name
				endpoint = blueprint + ".static"
				return directory, item, endpoint
			except (ValueError, KeyError):
				pass

		return flask.ext.assets.FlaskResolver.split_prefix(self, ctx, item)

	def resolve_output_to_path(self, ctx, target, bundle):
		import os
		return os.path.normpath(os.path.join(ctx.environment.directory, target))

##~~ Webassets updater that takes changes in the configuration into account

class SettingsCheckUpdater(webassets.updater.BaseUpdater):

	updater = "always"

	def __init__(self):
		self._delegate = webassets.updater.get_updater(self.__class__.updater)

	def needs_rebuild(self, bundle, ctx):
		return self._delegate.needs_rebuild(bundle, ctx) or self.changed_settings(ctx)

	def changed_settings(self, ctx):
		import json

		if not ctx.cache:
			return False

		cache_key = ('octo', 'settings')
		current_hash = webassets.utils.hash_func(json.dumps(settings().effective_yaml))
		cached_hash = ctx.cache.get(cache_key)
		# This may seem counter-intuitive, but if no cache entry is found
		# then we actually return "no update needed". This is because
		# otherwise if no cache / a dummy cache is used, then we would be
		# rebuilding every single time.
		if not cached_hash is None:
			return cached_hash != current_hash
		return False

	def build_done(self, bundle, ctx):
		import json

		self._delegate.build_done(bundle, ctx)
		if not ctx.cache:
			return

		cache_key = ('octo', 'settings')
		cache_value = webassets.utils.hash_func(json.dumps(settings().effective_yaml))
		ctx.cache.set(cache_key, cache_value)

##~~ plugin assets collector

def collect_plugin_assets(enable_gcodeviewer=True, preferred_stylesheet="css"):
	logger = logging.getLogger(__name__ + ".collect_plugin_assets")

	supported_stylesheets = ("css", "less")
	assets = dict(
		js=[],
		css=[],
		less=[]
	)
	assets["js"] = [
		'js/app/viewmodels/appearance.js',
		'js/app/viewmodels/connection.js',
		'js/app/viewmodels/control.js',
		'js/app/viewmodels/firstrun.js',
		'js/app/viewmodels/files.js',
		'js/app/viewmodels/loginstate.js',
		'js/app/viewmodels/navigation.js',
		'js/app/viewmodels/printerstate.js',
		'js/app/viewmodels/printerprofiles.js',
		'js/app/viewmodels/settings.js',
		'js/app/viewmodels/slicing.js',
		'js/app/viewmodels/temperature.js',
		'js/app/viewmodels/terminal.js',
		'js/app/viewmodels/timelapse.js',
		'js/app/viewmodels/users.js',
		'js/app/viewmodels/log.js',
		'js/app/viewmodels/usersettings.js',
		'js/app/viewmodels/about.js'
	]
	if enable_gcodeviewer:
		assets["js"] += [
			'js/app/viewmodels/gcode.js',
			'gcodeviewer/js/ui.js',
			'gcodeviewer/js/gCodeReader.js',
			'gcodeviewer/js/renderer.js'
		]

	if preferred_stylesheet == "less":
		assets["less"].append('less/octoprint.less')
	elif preferred_stylesheet == "css":
		assets["css"].append('css/octoprint.css')

	asset_plugins = octoprint.plugin.plugin_manager().get_implementations(octoprint.plugin.AssetPlugin)
	for implementation in asset_plugins:
		name = implementation._identifier
		try:
			all_assets = implementation.get_assets()
			basefolder = implementation.get_asset_folder()
		except:
			logger.exception("Got an error while trying to collect assets from {}, ignoring assets from the plugin".format(name))
			continue

		def asset_exists(category, asset):
			exists = os.path.exists(os.path.join(basefolder, asset))
			if not exists:
				logger.warn("Plugin {} is referring to non existing {} asset {}".format(name, category, asset))
			return exists

		if "js" in all_assets:
			for asset in all_assets["js"]:
				if not asset_exists("js", asset):
					continue
				assets["js"].append('plugin/{name}/{asset}'.format(**locals()))

		if preferred_stylesheet in all_assets:
			for asset in all_assets[preferred_stylesheet]:
				if not asset_exists(preferred_stylesheet, asset):
					continue
				assets[preferred_stylesheet].append('plugin/{name}/{asset}'.format(**locals()))
		else:
			for stylesheet in supported_stylesheets:
				if not stylesheet in all_assets:
					continue

				for asset in all_assets[stylesheet]:
					if not asset_exists(stylesheet, asset):
						continue
					assets[stylesheet].append('plugin/{name}/{asset}'.format(**locals()))
				break

	return assets
