# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

from flask import request, jsonify, abort, make_response
from flask.ext.login import current_user

import octoprint.users as users

from octoprint.server import restricted_access, SUCCESS, admin_permission, userManager
from octoprint.server.ajax import ajax


#~~ user settings


@ajax.route("/users", methods=["GET"])
@restricted_access
@admin_permission.require(403)
def getUsers():
	if userManager is None:
		return jsonify(SUCCESS)

	return jsonify({"users": userManager.getAllUsers()})


@ajax.route("/users", methods=["POST"])
@restricted_access
@admin_permission.require(403)
def addUser():
	if userManager is None:
		return jsonify(SUCCESS)

	if "application/json" in request.headers["Content-Type"]:
		data = request.json

		name = data["name"]
		password = data["password"]
		active = data["active"]

		roles = ["user"]
		if "admin" in data.keys() and data["admin"]:
			roles.append("admin")

		try:
			userManager.addUser(name, password, active, roles)
		except users.UserAlreadyExists:
			abort(409)
	return getUsers()


@ajax.route("/users/<username>", methods=["GET"])
@restricted_access
def getUser(username):
	if userManager is None:
		return jsonify(SUCCESS)

	if current_user is not None and not current_user.is_anonymous() and (current_user.get_name() == username or current_user.is_admin()):
		user = userManager.findUser(username)
		if user is not None:
			return jsonify(user.asDict())
		else:
			abort(404)
	else:
		abort(403)


@ajax.route("/users/<username>", methods=["PUT"])
@restricted_access
@admin_permission.require(403)
def updateUser(username):
	if userManager is None:
		return jsonify(SUCCESS)

	user = userManager.findUser(username)
	if user is not None:
		if "application/json" in request.headers["Content-Type"]:
			data = request.json

			# change roles
			roles = ["user"]
			if "admin" in data.keys() and data["admin"]:
				roles.append("admin")
			userManager.changeUserRoles(username, roles)

			# change activation
			if "active" in data.keys():
				userManager.changeUserActivation(username, data["active"])
		return getUsers()
	else:
		abort(404)


@ajax.route("/users/<username>", methods=["DELETE"])
@restricted_access
@admin_permission.require(http_exception=403)
def removeUser(username):
	if userManager is None:
		return jsonify(SUCCESS)

	try:
		userManager.removeUser(username)
		return getUsers()
	except users.UnknownUser:
		abort(404)


@ajax.route("/users/<username>/password", methods=["PUT"])
@restricted_access
def changePasswordForUser(username):
	if userManager is None:
		return jsonify(SUCCESS)

	if current_user is not None and not current_user.is_anonymous() and (current_user.get_name() == username or current_user.is_admin()):
		if "application/json" in request.headers["Content-Type"]:
			data = request.json
			if "password" in data.keys() and data["password"]:
				try:
					userManager.changeUserPassword(username, data["password"])
				except users.UnknownUser:
					return make_response(("Unknown user: %s" % username, 404, []))
		return jsonify(SUCCESS)
	else:
		return make_response(("Forbidden", 403, []))


@ajax.route("/users/<username>/apikey", methods=["DELETE"])
@restricted_access
def deleteApikeyForUser(username):
	if userManager is None:
		return jsonify(SUCCESS)

	if current_user is not None and not current_user.is_anonymous() and (current_user.get_name() == username or current_user.is_admin()):
		try:
			userManager.deleteApikey(username)
		except users.UnknownUser:
			return make_response(("Unknown user: %s" % username, 404, []))
		return jsonify(SUCCESS)
	else:
		return make_response(("Forbidden", 403, []))


@ajax.route("/users/<username>/apikey", methods=["POST"])
@restricted_access
def generateApikeyForUser(username):
	if userManager is None:
		return jsonify(SUCCESS)

	if current_user is not None and not current_user.is_anonymous() and (current_user.get_name() == username or current_user.is_admin()):
		try:
			apikey = userManager.generateApiKey(username)
		except users.UnknownUser:
			return make_response(("Unknown user: %s" % username, 404, []))
		return jsonify({"apikey": apikey})
	else:
		return make_response(("Forbidden", 403, []))
