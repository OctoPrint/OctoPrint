# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

from octoprint.settings import settings
import octoprint.timelapse
import octoprint.server
from octoprint.users import ApiUser

from . import flask
from . import sockjs
from . import tornado
from . import watchdog


def get_user_for_apikey(apikey):
	if settings().get(["api", "enabled"]) and apikey is not None:
		if apikey == settings().get(["api", "key"]):
			# master key was used
			return ApiUser()
		else:
			# user key might have been used
			return octoprint.server.userManager.findUser(apikey=apikey)
	else:
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


#~~ reverse proxy compatible WSGI middleware


class ReverseProxied(object):
	"""
	Wrap the application in this middleware and configure the
	front-end server to add these headers, to let you quietly bind
	this to a URL other than / and to an HTTP scheme that is
	different than what is used locally.

	In nginx:
		location /myprefix {
			proxy_pass http://192.168.0.1:5001;
			proxy_set_header Host $host;
			proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
			proxy_set_header X-Scheme $scheme;
			proxy_set_header X-Script-Name /myprefix;
		}

	Alternatively define prefix and scheme via config.yaml:
		server:
			baseUrl: /myprefix
			scheme: http

	:param app: the WSGI application
	:param header_script_name: the HTTP header in the wsgi environment from which to determine the prefix
	:param header_scheme: the HTTP header in the wsgi environment from which to determine the scheme
	:param base_url: the prefix to use as fallback if headers are not set
	"""

	def __init__(self, app, header_prefix="x-script-name", header_scheme="x-scheme", base_url="", scheme=""):
		self.app = app

		# headers for prefix & scheme, converted to conform to WSGI format
		to_wsgi_format = lambda header: "HTTP_" + header.upper().replace("-", "_")
		self._header_prefix = to_wsgi_format(header_prefix)
		self._header_scheme = to_wsgi_format(header_scheme)

		# fallback prefix & scheme from config
		self._fallback_prefix = base_url
		self._fallback_scheme = scheme

	def __call__(self, environ, start_response):
		# determine prefix
		prefix = environ.get(self._header_prefix, "")
		if not prefix:
			prefix = self._fallback_prefix

		# rewrite SCRIPT_NAME and if necessary also PATH_INFO based on prefix
		if prefix:
			environ["SCRIPT_NAME"] = prefix
			path_info = environ["PATH_INFO"]
			if path_info.startswith(prefix):
				environ["PATH_INFO"] = path_info[len(prefix):]

		# determine scheme
		scheme = environ.get(self._header_scheme, "")
		if not scheme:
			scheme = self._fallback_scheme

		# rewrite wsgi.url_scheme based on scheme
		if scheme:
			environ["wsgi.url_scheme"] = scheme

		# call wrapped app with rewritten environment
		return self.app(environ, start_response)

