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
from octoprint.server.util import apiKeyRequestHandler, corsResponseHandler
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

@api.route("/setup/wizard", methods=["GET"])
def wizardState():
	if not s().getBoolean(["server", "firstRun"]) and not admin_permission.can():
		abort(403)

	result = dict()
	wizard_plugins = octoprint.server.pluginManager.get_implementations(octoprint.plugin.WizardPlugin)
	for implementation in wizard_plugins:
		name = implementation._identifier
		try:
			required = implementation.is_wizard_required()
			details = implementation.get_wizard_details()
		except:
			logging.getLogger(__name__).exception("There was an error fetching wizard details for {}, ignoring".format(name))
		else:
			result[name] = dict(required=required, details=details)

	return jsonify(result)


@api.route("/setup/wizard", methods=["POST"])
def wizardFinish():
	if not s().getBoolean(["server", "firstRun"]) and not admin_permission.can():
		abort(403)

	data = dict()
	try:
		data = request.json
	except:
		abort(400)

	if not "handled" in data:
		abort(400)
	handled = data["handled"]

	if s().getBoolean(["server", "firstRun"]):
		s().setBoolean(["server", "firstRun"], False)

	seen_wizards = dict(s().get(["server", "seenWizards"]))

	wizard_plugins = octoprint.server.pluginManager.get_implementations(octoprint.plugin.WizardPlugin)
	for implementation in wizard_plugins:
		name = implementation._identifier
		try:
			implementation.on_wizard_finish(name in handled)
			if name in handled:
				seen_wizards[name] = implementation.get_wizard_version()
		except:
			logging.getLogger(__name__).exceptino("There was an error finishing the wizard for {}, ignoring".format(name))

	s().set(["server", "seenWizards"], seen_wizards)
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

@api.route("/util/test", methods=["POST"])
@restricted_access
@admin_permission.require(403)
def utilTestPath():
	valid_commands = dict(
		path=["path"],
		url=["url"]
	)

	command, data, response = get_json_command_from_request(request, valid_commands)
	if response is not None:
		return response

	if command == "path":
		import os
		from octoprint.util.paths import normalize

		path = normalize(data["path"])
		if not path:
			return jsonify(path=path, exists=False, typeok=False, access=False, result=False)

		check_type = None
		check_access = []

		if "check_type" in data and data["check_type"] in ("file", "dir"):
			check_type = data["check_type"]

		if "check_access" in data:
			request_check_access = data["check_access"]
			if not isinstance(request_check_access, list):
				request_check_access = list(request_check_access)

			check_access = [check for check in request_check_access if check in ("r", "w", "x")]

		exists = os.path.exists(path)

		# check if path exists
		type_mapping = dict(file=os.path.isfile, dir=os.path.isdir)
		if check_type:
			typeok = type_mapping[check_type](path)
		else:
			typeok = True

		# check if path allows requested access
		access_mapping = dict(r=os.R_OK, w=os.W_OK, x=os.X_OK)
		if check_access:
			access = os.access(path, reduce(lambda x, y: x | y, map(lambda a: access_mapping[a], check_access)))
		else:
			access = True

		return jsonify(path=path, exists=exists, typeok=typeok, access=access, result=exists and typeok and access)

	elif command == "url":
		import requests

		class StatusCodeRange(object):
			def __init__(self, start=None, end=None):
				self.start = start
				self.end = end

			def __contains__(self, item):
				if not isinstance(item, int):
					return False
				if self.start and self.end:
					return self.start <= item < self.end
				elif self.start:
					return self.start <= item
				elif self.end:
					return item < self.end
				else:
					return False

			def as_dict(self):
				return dict(
					start=self.start,
					end=self.end
				)

		status_ranges = dict(
			informational=StatusCodeRange(start=100,end=200),
			success=StatusCodeRange(start=200,end=300),
			redirection=StatusCodeRange(start=300,end=400),
			client_error=StatusCodeRange(start=400,end=500),
			server_error=StatusCodeRange(start=500),
			normal=StatusCodeRange(end=400),
			error=StatusCodeRange(start=400),
			any=StatusCodeRange(start=100)
		)

		url = data["url"]
		method = "HEAD"
		check_status = [status_ranges["normal"]]

		if "method" in data:
			method = data["method"]

		if "status" in data:
			request_status = data["status"]
			if not isinstance(request_status, list):
				request_status = [request_status]

			check_status = []
			for rs in request_status:
				if rs in status_ranges:
					check_status.append(status_ranges[rs])
				else:
					code = requests.codes[rs]
					if code is not None:
						check_status.append([code])

		try:
			response = requests.request(method=method, url=url)
			status = reduce(lambda x, y: x and response.status_code in y, check_status)
		except:
			status = False

		result = dict(
			url=url,
			status=response.status_code,
			result=status.as_dict() if isinstance(status, StatusCodeRange) else status
		)

		if "response" in data and (data["response"] in valid_boolean_trues or data["response"] in ("json", "bytes")):

			import base64
			content = base64.standard_b64encode(response.content)

			if data["response"] == "json":
				try:
					content = response.json()
				except:
					logging.getLogger(__name__).exception("Couldn't convert response to json")
					result["result"] = False

			result["response"] = dict(
				headers=dict(response.headers),
				content=content
			)

		return jsonify(**result)
