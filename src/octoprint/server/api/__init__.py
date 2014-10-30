# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging
import netaddr
import sarge

from flask import Blueprint, request, jsonify, abort, current_app, session, make_response
from flask.ext.login import login_user, logout_user, current_user
from flask.ext.principal import Identity, identity_changed, AnonymousIdentity

import octoprint.util as util
import octoprint.users
import octoprint.server
import octoprint.plugin
from octoprint.server import admin_permission, NO_CONTENT, UI_API_KEY
from octoprint.settings import settings as s, valid_boolean_trues
from octoprint.server.util import get_api_key, get_user_for_apikey
from octoprint.server.util.flask import restricted_access


#~~ init api blueprint, including sub modules

api = Blueprint("api", __name__)

from . import printer as api_printer
from . import job as api_job
from . import connection as api_connection
from . import files as api_files
from . import settings as api_settings
from . import timelapse as api_timelapse
from . import users as api_users
from . import log as api_logs
from . import slicing as api_slicing


VERSION = "0.1"


def optionsAllowOrigin(request):
	""" Always reply 200 on OPTIONS request """

	resp = current_app.make_default_options_response()

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

@api.before_request
def beforeApiRequests():
	"""
	All requests in this blueprint need to be made supplying an API key. This may be the UI_API_KEY, in which case
	the underlying request processing will directly take place, or it may be the global or a user specific case. In any
	case it has to be present and must be valid, so anything other than the above three types will result in denying
	the request.
	"""

	if request.method == 'OPTIONS' and s().getBoolean(["api", "allowCrossOrigin"]):
		return optionsAllowOrigin(request)

	apikey = get_api_key(request)
	if apikey is None:
		# no api key => 401
		return make_response("No API key provided", 401)

	if apikey == UI_API_KEY:
		# ui api key => continue regular request processing
		return

	if not s().get(["api", "enabled"]):
		# api disabled => 401
		return make_response("API disabled", 401)

	if apikey == s().get(["api", "key"]):
		# global api key => continue regular request processing
		return

	user = get_user_for_apikey(apikey)
	if user is not None:
		# user specific api key => continue regular request processing
		return

	# invalid api key => 401
	return make_response("Invalid API key", 401)

@api.after_request
def afterApiRequests(resp):

	# Allow crossdomain
	allowCrossOrigin = s().getBoolean(["api", "allowCrossOrigin"])
	if request.method != 'OPTIONS' and 'Origin' in request.headers and allowCrossOrigin:
		resp.headers['Access-Control-Allow-Origin'] = request.headers['Origin']

	return resp


#~~ data from plugins

@api.route("/plugin/<string:name>", methods=["GET"])
def pluginData(name):
	api_plugins = octoprint.plugin.plugin_manager().get_implementations(octoprint.plugin.SimpleApiPlugin)
	if not name in api_plugins:
		return make_response("Not found", 404)

	api_plugin = api_plugins[name]
	response = api_plugin.on_api_get(request)

	if response is not None:
		return response
	return NO_CONTENT

#~~ commands for plugins

@api.route("/plugin/<string:name>", methods=["POST"])
@restricted_access
def pluginCommand(name):
	api_plugins = octoprint.plugin.plugin_manager().get_implementations(octoprint.plugin.SimpleApiPlugin)
	if not name in api_plugins:
		return make_response("Not found", 404)

	api_plugin = api_plugins[name]
	valid_commands = api_plugin.get_api_commands()
	if valid_commands is None:
		return make_response("Method not allowed", 405)

	command, data, response = util.getJsonCommandFromRequest(request, valid_commands)
	if response is not None:
		return response

	response = api_plugin.on_api_command(command, data)
	if response is not None:
		return response
	return NO_CONTENT

#~~ first run setup


@api.route("/setup", methods=["POST"])
def firstRunSetup():
	if not s().getBoolean(["server", "firstRun"]):
		abort(403)

	if "ac" in request.values.keys() and request.values["ac"] in valid_boolean_trues and \
					"user" in request.values.keys() and "pass1" in request.values.keys() and \
					"pass2" in request.values.keys() and request.values["pass1"] == request.values["pass2"]:
		# configure access control
		s().setBoolean(["accessControl", "enabled"], True)
		octoprint.server.userManager.addUser(request.values["user"], request.values["pass1"], True, ["user", "admin"])
		s().setBoolean(["server", "firstRun"], False)
	elif "ac" in request.values.keys() and not request.values["ac"] in valid_boolean_trues:
		# disable access control
		s().setBoolean(["accessControl", "enabled"], False)
		s().setBoolean(["server", "firstRun"], False)

		octoprint.server.loginManager.anonymous_user = octoprint.users.DummyUser
		octoprint.server.principals.identity_loaders.appendleft(octoprint.users.dummy_identity_loader)

	s().save()
	return NO_CONTENT

#~~ system state


@api.route("/state", methods=["GET"])
@restricted_access
def apiPrinterState():
	return make_response(("/api/state has been deprecated, use /api/printer instead", 405, []))


@api.route("/version", methods=["GET"])
@restricted_access
def apiVersion():
	return jsonify({
		"server": octoprint.server.VERSION,
		"api": octoprint.server.api.VERSION
	})

@api.route("/version", methods=["GET"])
@restricted_access
def apiVersion():
	return jsonify({
		"server": octoprint.server.VERSION,
		"api": VERSION
	})

#~~ system control


@api.route("/system", methods=["POST"])
@restricted_access
@admin_permission.require(403)
def performSystemAction():
	logger = logging.getLogger(__name__)
	if "action" in request.values.keys():
		action = request.values["action"]
		available_actions = s().get(["system", "actions"])
		for availableAction in available_actions:
			if availableAction["action"] == action:
				logger.info("Performing command: %s" % availableAction["command"])
				try:
					# Note: we put the command in brackets since sarge (up to the most recently released version) has
					# a bug concerning shell=True commands. Once sarge 0.1.4 we can upgrade to that and remove this
					# workaround again
					#
					# See https://bitbucket.org/vinay.sajip/sarge/issue/21/behavior-is-not-like-popen-using-shell
					p = sarge.run([availableAction["command"]], stderr=sarge.Capture(), shell=True)
					if p.returncode != 0:
						returncode = p.returncode
						stderr_text = p.stderr.text
						logger.warn("Command failed with return code %i: %s" % (returncode, stderr_text))
						return make_response(("Command failed with return code %i: %s" % (returncode, stderr_text), 500, []))
				except Exception, e:
					logger.warn("Command failed: %s" % e)
					return make_response(("Command failed: %s" % e, 500, []))
	return NO_CONTENT


#~~ Login/user handling


@api.route("/login", methods=["POST"])
def login():
	if octoprint.server.userManager is not None and "user" in request.values.keys() and "pass" in request.values.keys():
		username = request.values["user"]
		password = request.values["pass"]

		if "remember" in request.values.keys() and request.values["remember"] == "true":
			remember = True
		else:
			remember = False

		if "usersession.id" in session:
			_logout(current_user)

		user = octoprint.server.userManager.findUser(username)
		if user is not None:
			if octoprint.server.userManager.checkPassword(username, password):
				if octoprint.server.userManager is not None:
					user = octoprint.server.userManager.login_user(user)
					session["usersession.id"] = user.get_session()
				login_user(user, remember=remember)
				identity_changed.send(current_app._get_current_object(), identity=Identity(user.get_id()))
				return jsonify(user.asDict())
		return make_response(("User unknown or password incorrect", 401, []))

	elif "passive" in request.values.keys():
		if octoprint.server.userManager is not None:
			user = octoprint.server.userManager.login_user(current_user)
		else:
			user = current_user

		if user is not None and not user.is_anonymous():
			identity_changed.send(current_app._get_current_object(), identity=Identity(user.get_id()))
			return jsonify(user.asDict())
		elif s().getBoolean(["accessControl", "autologinLocal"]) \
			and s().get(["accessControl", "autologinAs"]) is not None \
			and s().get(["accessControl", "localNetworks"]) is not None:

			autologinAs = s().get(["accessControl", "autologinAs"])
			localNetworks = netaddr.IPSet([])
			for ip in s().get(["accessControl", "localNetworks"]):
				localNetworks.add(ip)

			try:
				remoteAddr = util.getRemoteAddress(request)
				if netaddr.IPAddress(remoteAddr) in localNetworks:
					user = octoprint.server.userManager.findUser(autologinAs)
					if user is not None:
						login_user(user)
						identity_changed.send(current_app._get_current_object(), identity=Identity(user.get_id()))
						return jsonify(user.asDict())
			except:
				logger = logging.getLogger(__name__)
				logger.exception("Could not autologin user %s for networks %r" % (autologinAs, localNetworks))
	return NO_CONTENT


@api.route("/logout", methods=["POST"])
@restricted_access
def logout():
	# Remove session keys set by Flask-Principal
	for key in ('identity.id', 'identity.name', 'identity.auth_type'):
		if key in session:
			del session[key]
	identity_changed.send(current_app._get_current_object(), identity=AnonymousIdentity())

	_logout(current_user)
	logout_user()

	return NO_CONTENT

def _logout(user):
	if "usersession.id" in session:
		del session["usersession.id"]
	octoprint.server.userManager.logout_user(user)
