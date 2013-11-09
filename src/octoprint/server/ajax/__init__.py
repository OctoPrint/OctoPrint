# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

import logging
import subprocess
import netaddr

from flask import Blueprint, request, jsonify, abort, current_app, session, make_response
from flask.ext.login import login_user, logout_user, current_user
from flask.ext.principal import Identity, identity_changed, AnonymousIdentity

import octoprint.util as util
import octoprint.users
from octoprint.server import restricted_access, SUCCESS, admin_permission, loginManager, principals
from octoprint.settings import settings as s, valid_boolean_trues

#~~ init ajax blueprint, including sub modules

ajax = Blueprint("ajax", __name__)

from . import control as ajax_control
from . import gcodefiles as ajax_gcodefiles
from . import settings as ajax_settings
from . import timelapse as ajax_timelapse
from . import users as ajax_users


#~~ first run setup


@ajax.route("/setup", methods=["POST"])
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

		loginManager.anonymous_user = octoprint.users.DummyUser
		principals.identity_loaders.appendleft(octoprint.users.dummy_identity_loader)

	s().save()
	return jsonify(SUCCESS)


#~~ system control


@ajax.route("/system", methods=["POST"])
@restricted_access
@admin_permission.require(403)
def performSystemAction():
	logger = logging.getLogger(__name__)
	if request.values.has_key("action"):
		action = request.values["action"]
		availableActions = s().get(["system", "actions"])
		for availableAction in availableActions:
			if availableAction["action"] == action:
				logger.info("Performing command: %s" % availableAction["command"])
				try:
					subprocess.check_output(availableAction["command"], shell=True)
				except subprocess.CalledProcessError, e:
					logger.warn("Command failed with return code %i: %s" % (e.returncode, e.message))
					return make_response(("Command failed with return code %i: %s" % (e.returncode, e.message), 500, []))
				except Exception, ex:
					logger.exception("Command failed")
					return make_response(("Command failed: %r" % ex, 500, []))
	return jsonify(SUCCESS)


#~~ Login/user handling


@ajax.route("/login", methods=["POST"])
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
	return jsonify(SUCCESS)


@ajax.route("/logout", methods=["POST"])
@restricted_access
def logout():
	# Remove session keys set by Flask-Principal
	for key in ('identity.id', 'identity.auth_type'):
		del session[key]
	identity_changed.send(current_app._get_current_object(), identity=AnonymousIdentity())

	logout_user()

	return jsonify(SUCCESS)

