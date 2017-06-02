# coding=utf-8
from __future__ import absolute_import, division, print_function

from octoprint.util import deprecated
from octoprint.server.api import api
from octoprint.server.api import api_access as access
from octoprint.server.util.flask import restricted_access
from octoprint.access.permissions import Permissions

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


@api.route("/users", methods=["GET"])
@deprecated("/users has been moved to /access/users")
@restricted_access
@Permissions.SETTINGS.require(403)
def getUsers():
	return access.get_users()


@api.route("/users", methods=["POST"])
@deprecated("/users has been moved to /access/users")
@restricted_access
@Permissions.SETTINGS.require(403)
def addUser():
	return access.add_user()


@api.route("/users/<username>", methods=["GET"])
@deprecated("/users/<username> has been moved to /access/users/<username>")
@restricted_access
def getUser(username):
	return access.get_user(username)


@api.route("/users/<username>", methods=["PUT"])
@deprecated("/users/<username> has been moved to /access/users/<username>")
@restricted_access
@Permissions.SETTINGS.require(403)
def updateUser(username):
	return access.update_user(username)


@api.route("/users/<username>", methods=["DELETE"])
@deprecated("/users/<username> has been moved to /access/users/<username>")
@restricted_access
@Permissions.SETTINGS.require(403)
def removeUser(username):
	return access.remove_user(username)


@api.route("/users/<username>/password", methods=["PUT"])
@deprecated("/users/<username> has been moved to /access/users/<username>")
@restricted_access
def changePasswordForUser(username):
	return access.change_password_for_user(username)


@api.route("/users/<username>/settings", methods=["GET"])
@deprecated("/users/<username>/settings has been moved to /access/users/<username>/settings")
@restricted_access
def getSettingsForUser(username):
	return access.get_settings_for_user(username)


@api.route("/users/<username>/settings", methods=["PATCH"])
@deprecated("/users/<username>/settings has been moved to /access/users/<username>/settings")
@restricted_access
def changeSettingsForUser(username):
	return access.change_settings_for_user(username)


@api.route("/users/<username>/apikey", methods=["DELETE"])
@deprecated("/users/<username>/apikey has been moved to /access/users/<username>/apikey")
@restricted_access
def deleteApikeyForUser(username):
	return access.delete_apikey_for_user(username)


@api.route("/users/<username>/apikey", methods=["POST"])
@deprecated("/users/<username>/apikey has been moved to /access/users/<username>/apikey")
@restricted_access
def generateApikeyForUser(username):
	return access.generate_apikey_for_user(username)
