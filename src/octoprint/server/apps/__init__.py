# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import rsa
from flask import Blueprint, request, make_response, jsonify

import octoprint.server
import octoprint.plugin

from octoprint.server.util import noCachingResponseHandler, corsResponseHandler
from octoprint.settings import settings as s

apps = Blueprint("apps", __name__)

apps.after_request(noCachingResponseHandler)
apps.after_request(corsResponseHandler)

@apps.route("/auth", methods=["GET"])
def getSessionKey():
	unverified_key, valid_until = octoprint.server.appSessionManager.create()
	return jsonify(unverifiedKey=unverified_key, validUntil=valid_until)

@apps.route("/auth", methods=["POST"])
def verifySessionKey():
	if not "application/json" in request.headers["Content-Type"]:
		return None, None, make_response("Expected content-type JSON", 400)

	data = request.json
	for key in ("appid", "key", "_sig"):
		if not key in data:
			return make_response("Missing argument: {key}".format(key=key), 400)

	appid = str(data["appid"])
	if not "appversion" in data:
		appversion = "any"
	else:
		appversion = str(data["appversion"])
	key = str(data["key"])

	# calculate message that was signed
	message = "{appid}:{appversion}:{key}".format(**locals())

	# decode signature
	import base64
	signature = data["_sig"]
	signature = base64.decodestring("\n".join([signature[x:x+64] for x in range(0, len(signature), 64)]))

	# fetch and validate app information
	lookup_key = appid + ":" + appversion
	apps = _get_registered_apps()
	if not lookup_key in apps or not apps[lookup_key]["enabled"] or not "pubkey" in apps[lookup_key]:
		octoprint.server.appSessionManager.remove(key)
		return make_response("Invalid app: {lookup_key}".format(lookup_key=lookup_key), 401)

	pubkey_string = apps[lookup_key]["pubkey"]
	pubkey_string = "\n".join([pubkey_string[x:x+64] for x in range(0, len(pubkey_string), 64)])
	try:
		pubkey = rsa.PublicKey.load_pkcs1("-----BEGIN RSA PUBLIC KEY-----\n" + pubkey_string + "\n-----END RSA PUBLIC KEY-----\n")
	except:
		octoprint.server.appSessionManager.remove(key)
		return make_response("Invalid pubkey stored in server", 500)

	# verify signature
	try:
		rsa.verify(message, signature, pubkey)
	except rsa.VerificationError:
		octoprint.server.appSessionManager.remove(key)
		return make_response("Invalid signature", 401)

	# generate new session key and return it
	result = octoprint.server.appSessionManager.verify(key)
	if not result:
		return make_response("Invalid key or already verified", 401)

	verified_key, valid_until = result
	return jsonify(key=verified_key, validUntil=valid_until)

__registered_apps = None
def _get_registered_apps():
	global __registered_apps

	if __registered_apps is not None:
		return __registered_apps

	apps = s().get(["api", "apps"], merged=True)
	for app, app_data in apps.items():
		if not "enabled" in app_data:
			apps[app]["enabled"] = True

	hooks = octoprint.server.pluginManager.get_hooks("octoprint.accesscontrol.appkey")
	for name, hook in hooks.items():
		try:
			additional_apps = hook()
		except:
			import logging
			logging.getLogger(__name__).exception("Error while retrieving additional appkeys from plugin {name}".format(**locals()))
			continue

		any_version_enabled = dict()

		for app_data in additional_apps:
			id, version, pubkey = app_data
			key = id + ":" + version
			if key in apps:
				continue

			if not id in any_version_enabled:
				any_version_enabled[id] = False

			if version == "any":
				any_version_enabled[id] = True

			apps[key] = dict(
				pubkey=pubkey,
				enabled=True
			)

		for id, enabled in any_version_enabled.items():
			if enabled:
				continue
			apps[id + ":any"] = dict(
				pubkey=None,
				enabled=False
			)

	__registered_apps = apps
	return apps

def clear_registered_app():
	global __registered_apps
	__registered_apps = None
