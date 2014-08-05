# coding=utf-8
from octoprint.server.util import getApiKey, getUserForApiKey

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

import logging
import netaddr
import sarge

from flask import Blueprint, request, jsonify, abort, current_app, session, make_response
from flask.ext.login import login_user, logout_user, current_user
from flask.ext.principal import Identity, identity_changed, AnonymousIdentity

import octoprint.util as util
import octoprint.users
import octoprint.server
from octoprint.server import restricted_access, admin_permission, NO_CONTENT, UI_API_KEY
from octoprint.settings import settings as s, valid_boolean_trues

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


VERSION = "1.0"


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

	apikey = getApiKey(request)
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

	user = getUserForApiKey(apikey)
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

		user = octoprint.server.userManager.findUser(username)
		if user is not None:
			if user.check_password(octoprint.users.UserManager.createPasswordHash(password)):
				login_user(user, remember=remember)
				identity_changed.send(current_app._get_current_object(), identity=Identity(user.get_id()))
				return jsonify(user.asDict())
		return make_response(("User unknown or password incorrect", 401, []))
	elif "passive" in request.values.keys():
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
	for key in ('identity.id', 'identity.auth_type'):
		del session[key]
	identity_changed.send(current_app._get_current_object(), identity=AnonymousIdentity())

	logout_user()

	return NO_CONTENT

