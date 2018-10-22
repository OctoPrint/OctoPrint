# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging
import netaddr

from flask import Blueprint, request, jsonify, abort, current_app, session, make_response, g
from flask_login import login_user, logout_user, current_user
from flask_principal import Identity, identity_changed, AnonymousIdentity

import octoprint.util as util
import octoprint.util.net as util_net
import octoprint.users
import octoprint.server
import octoprint.plugin
from octoprint.server import admin_permission, NO_CONTENT
from octoprint.settings import settings as s, valid_boolean_trues
from octoprint.server.util import noCachingExceptGetResponseHandler, enforceApiKeyRequestHandler, loginFromApiKeyRequestHandler, loginFromAuthorizationHeaderRequestHandler, corsRequestHandler, corsResponseHandler
from octoprint.server.util.flask import restricted_access, get_json_command_from_request, passive_login, get_remote_address


#~~ init api blueprint, including sub modules

api = Blueprint("api", __name__)

from . import printer as api_printer
from . import job as api_job
from . import connection as api_connection
from . import files as api_files
from . import settings as api_settings
from . import timelapse as api_timelapse
from . import users as api_users
from . import slicing as api_slicing
from . import printer_profiles as api_printer_profiles
from . import languages as api_languages
from . import system as api_system


VERSION = "0.1"

api.after_request(noCachingExceptGetResponseHandler)

api.before_request(corsRequestHandler)
api.before_request(enforceApiKeyRequestHandler)
api.before_request(loginFromAuthorizationHeaderRequestHandler)
api.before_request(loginFromApiKeyRequestHandler)
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

	seen_wizards = s().get(["server", "seenWizards"])

	result = dict()
	wizard_plugins = octoprint.server.pluginManager.get_implementations(octoprint.plugin.WizardPlugin)
	for implementation in wizard_plugins:
		name = implementation._identifier
		try:
			required = implementation.is_wizard_required()
			details = implementation.get_wizard_details()
			version = implementation.get_wizard_version()
			ignored = octoprint.plugin.WizardPlugin.is_wizard_ignored(seen_wizards, implementation)
		except:
			logging.getLogger(__name__).exception("There was an error fetching wizard details for {}, ignoring".format(name))
		else:
			result[name] = dict(required=required, details=details, version=version, ignored=ignored)

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
			logging.getLogger(__name__).exception("There was an error finishing the wizard for {}, ignoring".format(name))

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


#~~ Login/user handling


@api.route("/login", methods=["POST"])
def login():
	data = request.values
	if hasattr(request, "json") and request.json:
		data = request.json

	if octoprint.server.userManager.enabled and "user" in data and "pass" in data:
		username = data["user"]
		password = data["pass"]

		if "remember" in data and data["remember"] in valid_boolean_trues:
			remember = True
		else:
			remember = False

		if "usersession.id" in session:
			_logout(current_user)

		user = octoprint.server.userManager.findUser(username)
		if user is not None:
			if octoprint.server.userManager.checkPassword(username, password):
				if not user.is_active():
					return make_response(("Your account is deactivated", 403, []))

				if octoprint.server.userManager.enabled:
					user = octoprint.server.userManager.login_user(user)
					session["usersession.id"] = user.session
					g.user = user
				login_user(user, remember=remember)
				identity_changed.send(current_app._get_current_object(), identity=Identity(user.get_id()))

				remote_addr = get_remote_address(request)
				logging.getLogger(__name__).info("Actively logging in user {} from {}".format(user.get_id(), remote_addr))

				response = user.asDict()
				response["_is_external_client"] = s().getBoolean(["server", "ipCheck", "enabled"]) \
				                                  and not util_net.is_lan_address(remote_addr,
				                                                                  additional_private=s().get(["server", "ipCheck", "trustedSubnets"]))
				return jsonify(response)

		return make_response(("User unknown or password incorrect", 401, []))

	elif "passive" in data:
		return passive_login()
	return NO_CONTENT


@api.route("/logout", methods=["POST"])
@restricted_access
def logout():
	# logout from user manager...
	_logout(current_user)

	# ... and from flask login (and principal)
	logout_user()

	return NO_CONTENT


def _logout(user):
	if "usersession.id" in session:
		del session["usersession.id"]
	octoprint.server.userManager.logout_user(user)


#~~ Test utils


@api.route("/util/test", methods=["POST"])
@restricted_access
@admin_permission.require(403)
def utilTest():
	valid_commands = dict(
		path=["path"],
		url=["url"],
		server=["host", "port"]
	)

	command, data, response = get_json_command_from_request(request, valid_commands)
	if response is not None:
		return response

	if command == "path":
		return _test_path(data)
	elif command == "url":
		return _test_url(data)
	elif command == "server":
		return _test_server(data)

def _test_path(data):
	import os
	from octoprint.util.paths import normalize

	path = normalize(data["path"], real=False)
	if not path:
		return jsonify(path=path, exists=False, typeok=False, broken_symlink=False, access=False, result=False)

	unreal_path = path
	path = os.path.realpath(path)

	check_type = None
	check_access = []

	if "check_type" in data and data["check_type"] in ("file", "dir"):
		check_type = data["check_type"]

	if "check_access" in data:
		request_check_access = data["check_access"]
		if not isinstance(request_check_access, list):
			request_check_access = list(request_check_access)

		check_access = [check for check in request_check_access if check in ("r", "w", "x")]

	allow_create_dir = data.get("allow_create_dir", False) and check_type == "dir"
	check_writable_dir = data.get("check_writable_dir", False) and check_type == "dir"
	if check_writable_dir and "w" not in check_access:
		check_access.append("w")

	# check if path exists
	exists = os.path.exists(path)
	if not exists:
		if os.path.islink(unreal_path):
			# broken symlink, see #2644
			logging.getLogger(__name__).error("{} is a broken symlink pointing at non existing {}".format(unreal_path, path))
			return jsonify(path=unreal_path, exists=False, typeok=False, broken_symlink=True, access=False, result=False)

		elif check_type == "dir" and allow_create_dir:
			try:
				os.makedirs(path)
			except:
				logging.getLogger(__name__).exception("Error while trying to create {}".format(path))
				return jsonify(path=path, exists=False, typeok=False, broken_symlink=False, access=False, result=False)
			else:
				exists = True

	# check path type
	type_mapping = dict(file=os.path.isfile, dir=os.path.isdir)
	if check_type:
		typeok = type_mapping[check_type](path)
	else:
		typeok = exists

	# check if path allows requested access
	access_mapping = dict(r=os.R_OK, w=os.W_OK, x=os.X_OK)
	if check_access:
		mode = 0
		for a in map(lambda x: access_mapping[x], check_access):
			mode |= a
		access = os.access(path, mode)
	else:
		access = exists

	if check_writable_dir and check_type == "dir":
		try:
			test_path = os.path.join(path, ".testballoon.txt")
			with open(test_path, "wb") as f:
				f.write("Test")
			os.remove(test_path)
		except:
			logging.getLogger(__name__).exception("Error while testing if {} is really writable".format(path))
			return jsonify(path=path, exists=exists, typeok=typeok, broken_symlink=False, access=False, result=False)

	return jsonify(path=path, exists=exists, typeok=typeok, broken_symlink=False, access=access, result=exists and typeok and access)


def _test_url(data):
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
		informational=StatusCodeRange(start=100, end=200),
		success=StatusCodeRange(start=200, end=300),
		redirection=StatusCodeRange(start=300, end=400),
		client_error=StatusCodeRange(start=400, end=500),
		server_error=StatusCodeRange(start=500, end=600),
		normal=StatusCodeRange(end=400),
		error=StatusCodeRange(start=400, end=600),
		any=StatusCodeRange(start=100),
		timeout=StatusCodeRange(start=0, end=1)
	)

	url = data["url"]
	method = data.get("method", "HEAD")
	timeout = 3.0
	valid_ssl = True
	check_status = [status_ranges["normal"]]
	content_type_whitelist = None
	content_type_blacklist = None

	if "timeout" in data:
		try:
			timeout = float(data["timeout"])
		except:
			return make_response("{!r} is not a valid value for timeout (must be int or float)".format(data["timeout"]),
			                     400)

	if "validSsl" in data:
		valid_ssl = data["validSsl"] in valid_boolean_trues

	if "status" in data:
		request_status = data["status"]
		if not isinstance(request_status, list):
			request_status = [request_status]

		check_status = []
		for rs in request_status:
			if isinstance(rs, int):
				check_status.append([rs])
			else:
				if rs in status_ranges:
					check_status.append(status_ranges[rs])
				else:
					code = requests.codes[rs]
					if code is not None:
						check_status.append([code])

	if "content_type_whitelist" in data:
		if not isinstance(data["content_type_whitelist"], (list, tuple)):
			return make_response("content_type_whitelist must be a list of mime types")
		content_type_whitelist = map(util.parse_mime_type, data["content_type_whitelist"])
	if "content_type_blacklist" in data:
		if not isinstance(data["content_type_whitelist"], (list, tuple)):
			return make_response("content_type_blacklist must be a list of mime types")
		content_type_blacklist = map(util.parse_mime_type, data["content_type_blacklist"])

	response_result = None
	outcome = True
	status = 0
	try:
		with requests.request(method=method, url=url, timeout=timeout, verify=valid_ssl, stream=True) as response:
			status = response.status_code
			outcome = outcome and any(map(lambda x: status in x, check_status))
			content_type = response.headers.get("content-type")

			response_result = dict(headers=dict(response.headers),
			                       content_type=content_type)

			parsed_content_type = util.parse_mime_type(content_type)
			in_whitelist = content_type_whitelist is None or any(
				map(lambda x: util.mime_type_matches(parsed_content_type, x), content_type_whitelist))
			in_blacklist = content_type_blacklist is not None and any(
				map(lambda x: util.mime_type_matches(parsed_content_type, x), content_type_blacklist))

			if not in_whitelist or in_blacklist:
				# we don't support this content type
				response.close()
				outcome = False

			elif "response" in data and (
					data["response"] in valid_boolean_trues or data["response"] in ("json", "bytes")):
				if data["response"] == "json":
					content = response.json()

				else:
					import base64
					content = base64.standard_b64encode(response.content)

				response_result["content"] = content
	except:
		logging.getLogger(__name__).exception("Error while running a test {} request on {}".format(method, url))
		outcome = False

	result = dict(
		url=url,
		status=status,
		result=outcome
	)
	if response_result:
		result["response"] = response_result

	return jsonify(**result)

def _test_server(data):
	host = data["host"]
	try:
		port = int(data["port"])
	except:
		return make_response("{!r} is not a valid value for port (must be int)".format(data["port"]), 400)

	timeout = 3.05
	if "timeout" in data:
		try:
			timeout = float(data["timeout"])
		except:
			return make_response("{!r} is not a valid value for timeout (must be int or float)".format(data["timeout"]),
			                     400)

	protocol = data.get("protocol", "tcp")
	if protocol not in ("tcp", "udp"):
		return make_response("{!r} is not a valid value for protocol, must be tcp or udp".format(protocol), 400)

	from octoprint.util import server_reachable
	reachable = server_reachable(host, port, timeout=timeout, proto=protocol)

	result = dict(host=host,
	              port=port,
	              protocol=protocol,
	              result=reachable)

	return jsonify(**result)
