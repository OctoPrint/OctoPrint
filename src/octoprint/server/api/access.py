# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__author__ = "Marc Hannappel <salandora@gmail.com>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"

from flask import request, jsonify, abort, make_response
from werkzeug.exceptions import BadRequest
from flask_login import current_user

import octoprint.access.groups as groups
import octoprint.access.users as users

from octoprint.server import SUCCESS, groupManager, userManager
from octoprint.server.api import api, valid_boolean_trues
from octoprint.server.util.flask import no_firstrun_access
from octoprint.access.permissions import Permissions

#~~ permission api

@api.route("/access/permissions", methods=["GET"])
def get_permissions():
	return jsonify(permissions=[permission.as_dict() for permission in Permissions.all()])

#~~ group api

@api.route("/access/groups", methods=["GET"])
@no_firstrun_access
@Permissions.SETTINGS.require(403)
def get_groups():
	return jsonify(groups=list(map(lambda g: g.as_dict(), groupManager.groups)))


@api.route("/access/groups", methods=["POST"])
@no_firstrun_access
@Permissions.SETTINGS.require(403)
def add_group():
	if not "application/json" in request.headers["Content-Type"]:
		return make_response("Expected content-type JSON", 400)

	try:
		data = request.get_json()
	except BadRequest:
		return make_response("Malformed JSON body in request", 400)

	if not "key" in data:
		return make_response("Missing mandatory key field", 400)
	if not "name" in data:
		return make_response("Missing mandatory name field", 400)
	if not "permissions" in data:
		return make_response("Missing mandatory permissions field", 400)

	key = data["key"]
	name = data["name"]
	description = data.get("description", "")
	permissions = data["permissions"]
	subgroups = data["subgroups"]
	default = data.get("default", False)

	try:
		groupManager.add_group(key, name, description=description, permissions=permissions, subgroups=subgroups, default=default)
	except groups.GroupAlreadyExists:
		abort(409)
	return get_groups()


@api.route("/access/groups/<key>", methods=["GET"])
@no_firstrun_access
@Permissions.SETTINGS.require(403)
def get_group(key):
	group = groupManager.find_group(key)
	if group is not None:
		return jsonify(group)
	else:
		abort(404)


@api.route("/access/groups/<key>", methods=["PUT"])
@no_firstrun_access
@Permissions.SETTINGS.require(403)
def update_group(key):
	if "application/json" not in request.headers["Content-Type"]:
		return make_response("Expected content-type JSON", 400)

	try:
		data = request.get_json()
	except BadRequest:
		return make_response("Malformed JSON body in request", 400)

	try:
		kwargs = dict()

		if "permissions" in data:
			kwargs["permissions"] = data["permissions"]

		if "subgroups" in data:
			kwargs["subgroups"] = data["subgroups"]

		if "default" in data:
			kwargs["default"] = data["default"] in valid_boolean_trues

		if "description" in data:
			kwargs["description"] = data["description"]

		groupManager.update_group(key, **kwargs)

		return get_groups()
	except groups.GroupCantBeChanged:
		abort(403)
	except groups.UnknownGroup:
		abort(404)


@api.route("/access/groups/<key>", methods=["DELETE"])
@no_firstrun_access
@Permissions.SETTINGS.require(403)
def remove_group(key):
	try:
		groupManager.remove_group(key)
		return get_groups()
	except groups.UnknownGroup:
		abort(404)
	except groups.GroupUnremovable:
		abort(403)

#~~ user api

@api.route("/access/users", methods=["GET"])
@no_firstrun_access
@Permissions.SETTINGS.require(403)
def get_users():
	if not userManager.enabled:
		return jsonify(SUCCESS)

	return jsonify(users=list(map(lambda u: u.as_dict(), userManager.get_all_users())))


@api.route("/access/users", methods=["POST"])
@no_firstrun_access
@Permissions.SETTINGS.require(403)
def add_user():
	if not userManager.enabled:
		return jsonify(SUCCESS)

	if not "application/json" in request.headers["Content-Type"]:
		return make_response("Expected content-type JSON", 400)

	try:
		data = request.get_json()
	except BadRequest:
		return make_response("Malformed JSON body in request", 400)

	if data is None:
		return make_response("Malformed JSON body in request", 400)

	if not "name" in data:
		return make_response("Missing mandatory name field", 400)
	if not "password" in data:
		return make_response("Missing mandatory password field", 400)
	if not "active" in data:
		return make_response("Missing mandatory active field", 400)

	name = data["name"]
	password = data["password"]
	active = data["active"] in valid_boolean_trues

	groups = data.get("groups", None)
	permissions = data.get("permissions", None)

	try:
		userManager.add_user(name, password, active, permissions, groups)
	except users.UserAlreadyExists:
		abort(409)
	return get_users()


@api.route("/access/users/<username>", methods=["GET"])
@no_firstrun_access
def get_user(username):
	if not userManager.enabled:
		return jsonify(SUCCESS)

	if current_user is not None and not current_user.is_anonymous and (current_user.get_name() == username or current_user.has_permission(Permissions.ADMIN)):
		user = userManager.find_user(username)
		if user is not None:
			return jsonify(user)
		else:
			abort(404)
	else:
		abort(403)


@api.route("/access/users/<username>", methods=["PUT"])
@no_firstrun_access
@Permissions.SETTINGS.require(403)
def update_user(username):
	if not userManager.enabled:
		return jsonify(SUCCESS)

	user = userManager.find_user(username)
	if user is not None:
		if not "application/json" in request.headers["Content-Type"]:
			return make_response("Expected content-type JSON", 400)

		try:
			data = request.get_json()
		except BadRequest:
			return make_response("Malformed JSON body in request", 400)


		# change groups
		if "groups" in data:
			groups = data["groups"]
			userManager.change_user_groups(username, groups)

		# change permissions
		if "permissions" in data:
			permissions = data["permissions"]
			userManager.change_user_permissions(username, permissions)

		if data is None:
			return make_response("Malformed JSON body in request", 400)

		# change activation
		if "active" in data:
			userManager.change_user_activation(username, data["active"] in valid_boolean_trues)

		return get_users()
	else:
		abort(404)


@api.route("/access/users/<username>", methods=["DELETE"])
@no_firstrun_access
@Permissions.SETTINGS.require(403)
def remove_user(username):
	if not userManager.enabled:
		return jsonify(SUCCESS)

	try:
		userManager.remove_user(username)
		return get_users()
	except users.UnknownUser:
		abort(404)


@api.route("/access/users/<username>/password", methods=["PUT"])
@no_firstrun_access
def change_password_for_user(username):
	if not userManager.enabled:
		return jsonify(SUCCESS)

	if current_user is not None and not current_user.is_anonymous and (current_user.get_name() == username or current_user.is_admin):
		if not "application/json" in request.headers["Content-Type"]:
			return make_response("Expected content-type JSON", 400)

		try:
			data = request.get_json()
		except BadRequest:
			return make_response("Malformed JSON body in request", 400)

		if data is None:
			return make_response("Malformed JSON body in request", 400)

		if not "password" in data or not data["password"]:
			return make_response("password is missing from request", 400)

		try:
			userManager.change_user_password(username, data["password"])
		except users.UnknownUser:
			return make_response(("Unknown user: %s" % username, 404, []))

		return jsonify(SUCCESS)
	else:
		return make_response(("Forbidden", 403, []))


@api.route("/access/users/<username>/settings", methods=["GET"])
@no_firstrun_access
def get_settings_for_user(username):
	if not userManager.enabled:
		return jsonify(SUCCESS)

	if current_user is None or current_user.is_anonymous or (current_user.get_name() != username and not current_user.has_permission(Permissions.ADMIN)):
		return make_response("Forbidden", 403)

	try:
		return jsonify(userManager.get_all_user_settings(username))
	except users.UnknownUser:
		return make_response("Unknown user: %s" % username, 404)

@api.route("/access/users/<username>/settings", methods=["PATCH"])
@no_firstrun_access
def change_settings_for_user(username):
	if not userManager.enabled:
		return jsonify(SUCCESS)

	if current_user is None or current_user.is_anonymous or (current_user.get_name() != username and not current_user.has_permission(Permissions.ADMIN)):
		return make_response("Forbidden", 403)

	try:
		data = request.get_json()
	except BadRequest:
		return make_response("Malformed JSON body in request", 400)

	if data is None:
		return make_response("Malformed JSON body in request", 400)

	try:
		userManager.change_user_settings(username, data)
		return jsonify(SUCCESS)
	except users.UnknownUser:
		return make_response("Unknown user: %s" % username, 404)

@api.route("/access/users/<username>/apikey", methods=["DELETE"])
@no_firstrun_access
def delete_apikey_for_user(username):
	if not userManager.enabled:
		return jsonify(SUCCESS)

	if current_user is not None and not current_user.is_anonymous and (current_user.get_name() == username or current_user.has_permission(Permissions.ADMIN)):
		try:
			userManager.delete_api_key(username)
		except users.UnknownUser:
			return make_response(("Unknown user: %s" % username, 404, []))
		return jsonify(SUCCESS)
	else:
		return make_response(("Forbidden", 403, []))


@api.route("/access/users/<username>/apikey", methods=["POST"])
@no_firstrun_access
def generate_apikey_for_user(username):
	if not userManager.enabled:
		return jsonify(SUCCESS)

	if current_user is not None and not current_user.is_anonymous and (current_user.get_name() == username or current_user.has_permission(Permissions.ADMIN)):
		try:
			apikey = userManager.generate_api_key(username)
		except users.UnknownUser:
			return make_response(("Unknown user: %s" % username, 404, []))
		return jsonify({"apikey": apikey})
	else:
		return make_response(("Forbidden", 403, []))

def _to_external_permissions(*permissions):
	return list(map(lambda p: p.get_name(), permissions))

def _to_external_groups(*groups):
	return list(map(lambda g: g.get_name(), groups))
