__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

from flask import redirect, url_for

from octoprint.server.api import api

# NOTE: The redirects here should rather be 308 PERMANENT REDIRECT, however RFC7538 doesn't seem to be supported
# by all browsers yet. So we stick to 307 TEMPORARY REDIRECT as defined in RFC7231 although it's definitely not a
# temporary redirect we have here.


@api.route("/users", methods=["GET"])
def deprecated_get_users():
    return redirect(url_for("api.get_users"), code=307)


@api.route("/users", methods=["POST"])
def addUser():
    return redirect(url_for("api.add_user"), code=307)


@api.route("/users/<username>", methods=["GET"])
def getUser(username):
    return redirect(url_for("api.get_user", username=username), code=307)


@api.route("/users/<username>", methods=["PUT"])
def updateUser(username):
    return redirect(url_for("api.update_user", username=username), code=307)


@api.route("/users/<username>", methods=["DELETE"])
def removeUser(username):
    return redirect(url_for("api.remove_user", username=username), code=307)


@api.route("/users/<username>/password", methods=["PUT"])
def changePasswordForUser(username):
    return redirect(url_for("api.change_password_for_user", username=username), code=307)


@api.route("/users/<username>/settings", methods=["GET"])
def getSettingsForUser(username):
    return redirect(url_for("api.get_settings_for_user", username=username), code=307)


@api.route("/users/<username>/settings", methods=["PATCH"])
def changeSettingsForUser(username):
    return redirect(url_for("api.change_settings_for_user", username=username), code=307)


@api.route("/users/<username>/apikey", methods=["DELETE"])
def deleteApikeyForUser(username):
    return redirect(url_for("api.delete_apikey_for_user", username=username), code=307)


@api.route("/users/<username>/apikey", methods=["POST"])
def generateApikeyForUser(username):
    return redirect(url_for("api.generate_apikey_for_user", username=username), code=307)
