# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

from flask import request, jsonify, abort, make_response
from werkzeug.exceptions import BadRequest

import octoprint.access.groups as groups

from octoprint.server import SUCCESS, groupManager
from octoprint.server.api import api
from octoprint.server.util.flask import restricted_access
from octoprint.access.permissions import Permissions

#~~ user settings

@api.route("/groups", methods=["GET"])
@restricted_access
@Permissions.SETTINGS.require(403)
def getGroups():
	if not groupManager.enabled:
		return jsonify(SUCCESS)

	return jsonify({"groups": groupManager.groups})


@api.route("/groups", methods=["POST"])
@restricted_access
@Permissions.SETTINGS.require(403)
def addGroup():
	if not groupManager.enabled:
		return jsonify(SUCCESS)

	if not "application/json" in request.headers["Content-Type"]:
		return make_response("Expected content-type JSON", 400)

	try:
		data = request.json
	except BadRequest:
		return make_response("Malformed JSON body in request", 400)

	if not "name" in data:
		return make_response("Missing mandatory name field", 400)
	if not "permissions" in data:
		return make_response("Missing mandatory permission field", 400)

	name = data["name"]
	description = data["description"]
	permissions = data["permissions"]
	default = data["defaultOn"] if "defaultOn" in data else False

	try:
		groupManager.addGroup(name, description=description, permissions=permissions, default=default)
	except groups.GroupAlreadyExists:
		abort(409)
	return getGroups()


@api.route("/groups/<groupname>", methods=["GET"])
def getGroup(groupname):
	if not groupManager.enabled:
		return jsonify(SUCCESS)

	group = groupManager.findGroup(groupname)
	if group is not None:
		return jsonify(group)
	else:
		abort(404)


@api.route("/groups/<groupname>", methods=["PUT"])
@restricted_access
@Permissions.SETTINGS.require(403)
def updateGroup(groupname):
	if not groupManager.enabled:
		return jsonify(SUCCESS)

	group = groupManager.findGroup(groupname)
	if group is not None:
		if not "application/json" in request.headers["Content-Type"]:
			return make_response("Expected content-type JSON", 400)

		try:
			data = request.json
		except BadRequest:
			return make_response("Malformed JSON body in request", 400)

		try:
			# change permissions
			if "permissions" in data:
				permissions = data["permissions"]
				groupManager.changeGroupPermissions(groupname, permissions)

			if "defaultOn" in data:
				groupManager.changeGroupDefault(groupname, data["defaultOn"])

			if "description" in data:
				groupManager.changeGroupDescription(groupname, data["description"])

			return getGroups()
		except groups.GroupCantbeChanged:
			abort(403)
	else:
		abort(404)


@api.route("/groups/<groupname>", methods=["DELETE"])
@restricted_access
@Permissions.SETTINGS.require(403)
def removeGroup(groupname):
	if not groupManager.enabled:
		return jsonify(SUCCESS)

	try:
		groupManager.removeGroup(groupname)
		return getGroups()
	except groups.UnknownGroup:
		abort(404)
	except groups.GroupUnremovable:
		abort(403)
