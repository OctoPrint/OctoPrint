# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging
import netaddr
import sarge

from flask import Blueprint, request, jsonify, abort, current_app, session, make_response, g
from flask.ext.login import login_user, logout_user, current_user
from flask.ext.principal import Identity, identity_changed, AnonymousIdentity

import octoprint.util as util
import octoprint.users
import octoprint.server
import octoprint.plugin
from octoprint.server import admin_permission, NO_CONTENT
from octoprint.settings import settings as s, valid_boolean_trues
from octoprint.server.util import noCachingResponseHandler, apiKeyRequestHandler, corsResponseHandler
from octoprint.server.util.flask import restricted_access, get_json_command_from_request, passive_login


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
from . import printer_profiles as api_printer_profiles
from . import languages as api_languages


VERSION = "0.1"

api.after_request(noCachingResponseHandler)

api.before_request(apiKeyRequestHandler)
api.after_request(corsResponseHandler)

#~~ data from plugins

@api.route("/plugin/<string:name>", methods=["GET"])
def pluginData(name):
	api_plugins = octoprint.plugin.plugin_manager().get_filtered_implementations(lambda p: p._identifier == name, octoprint.plugin.SimpleApiPlugin)
	if not api_plugins:
		return make_response("Not found", 404)

	if len(api_plugins) > 1:
		return make_response("More than one api provider registered for {name}, can't proceed".format(name=name), 500)

	api_plugin = api_plugins[0]
	if api_plugin.is_api_adminonly() and not current_user.is_admin():
		return make_response("Forbidden", 403)

	response = api_plugin.on_api_get(request)

	if response is not None:
		return response
	return NO_CONTENT

#~~ commands for plugins

@api.route("/plugin/<string:name>", methods=["POST"])
@restricted_access
def pluginCommand(name):
	api_plugins = octoprint.plugin.plugin_manager().get_filtered_implementations(lambda p: p._identifier == name, octoprint.plugin.SimpleApiPlugin)

	if not api_plugins:
		return make_response("Not found", 404)

	if len(api_plugins) > 1:
		return make_response("More than one api provider registered for {name}, can't proceed".format(name=name), 500)

	api_plugin = api_plugins[0]
	valid_commands = api_plugin.get_api_commands()
	if valid_commands is None:
		return make_response("Method not allowed", 405)

	if api_plugin.is_api_adminonly() and not current_user.is_admin():
		return make_response("Forbidden", 403)

	command, data, response = get_json_command_from_request(request, valid_commands)
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
		octoprint.server.userManager.enable()
		octoprint.server.userManager.addUser(request.values["user"], request.values["pass1"], True, ["user", "admin"])
		s().setBoolean(["server", "firstRun"], False)
	elif "ac" in request.values.keys() and not request.values["ac"] in valid_boolean_trues:
		# disable access control
		s().setBoolean(["accessControl", "enabled"], False)
		s().setBoolean(["server", "firstRun"], False)

		octoprint.server.loginManager.anonymous_user = octoprint.users.DummyUser
		octoprint.server.principals.identity_loaders.appendleft(octoprint.users.dummy_identity_loader)
		octoprint.server.userManager.disable()

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
				async = availableAction["async"] if "async" in availableAction else False
				ignore = availableAction["ignore"] if "ignore" in availableAction else False
				logger.info("Performing command: %s" % availableAction["command"])
				try:
					# we run this with shell=True since we have to trust whatever
					# our admin configured as command and since we want to allow
					# shell-alike handling here...
					p = sarge.run(availableAction["command"], stderr=sarge.Capture(), shell=True, async=async)
					if not async:
						if not ignore and p.returncode != 0:
							returncode = p.returncode
							stderr_text = p.stderr.text
							logger.warn("Command failed with return code %i: %s" % (returncode, stderr_text))
							return make_response(("Command failed with return code %i: %s" % (returncode, stderr_text), 500, []))
				except Exception, e:
					if not ignore:
						logger.warn("Command failed: %s" % e)
						return make_response(("Command failed: %s" % e, 500, []))
				break
	return NO_CONTENT


#~~ Login/user handling


@api.route("/login", methods=["POST"])
def login():
	if octoprint.server.userManager.enabled and "user" in request.values.keys() and "pass" in request.values.keys():
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
				if octoprint.server.userManager.enabled:
					user = octoprint.server.userManager.login_user(user)
					session["usersession.id"] = user.get_session()
					g.user = user
				login_user(user, remember=remember)
				identity_changed.send(current_app._get_current_object(), identity=Identity(user.get_id()))
				return jsonify(user.asDict())
		return make_response(("User unknown or password incorrect", 401, []))

	elif "passive" in request.values:
		return passive_login()
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
