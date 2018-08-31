# coding=utf-8
from __future__ import absolute_import

import flask
import threading
import os
from binascii import hexlify
from collections import defaultdict
from flask_babel import gettext

import octoprint.plugin
from octoprint.settings import valid_boolean_trues
from octoprint.server.util.flask import restricted_access, no_firstrun_access
from octoprint.server import NO_CONTENT, current_user, user_permission


class AppAlreadyExists(Exception):
	pass


class PendingDecision(object):
	def __init__(self, app_id, app_token, user_id, user_token):
		self.app_id = app_id
		self.app_token = app_token
		self.user_id = user_id
		self.user_token = user_token

	def external(self):
		return dict(app_id=self.app_id,
		            user_id=self.user_id,
		            user_token=self.user_token)


class ReadyDecision(object):
	def __init__(self, app_id, app_token, user_id):
		self.app_id = app_id
		self.app_token = app_token
		self.user_id = user_id

	@classmethod
	def for_pending(cls, pending, user_id):
		return cls(pending.app_id, pending.app_token, user_id)


class ActiveKey(object):
	def __init__(self, app_id, api_key):
		self.app_id = app_id
		self.api_key = api_key

	def external(self):
		return dict(app_id=self.app_id,
		            api_key=self.api_key)


class AppKeysPlugin(octoprint.plugin.AssetPlugin,
                    octoprint.plugin.BlueprintPlugin,
                    octoprint.plugin.SimpleApiPlugin,
                    octoprint.plugin.TemplatePlugin):

	def __init__(self):
		self._pending_decisions = []
		self._pending_lock = threading.RLock()

		self._ready_decisions = []
		self._ready_lock = threading.RLock()

		self._keys = defaultdict(list)
		self._keys_lock = threading.RLock()

	##~~ TemplatePlugin

	def get_template_configs(self):
		return [dict(type="usersettings", name=gettext("Application Keys"), custom_bindings=False)]

	##~~ AssetPlugin

	def get_assets(self):
		return dict(js=["js/appkeys.js"],
		            clientjs=["clientjs/appkeys.js"],
		            less=["less/appkeys.less"],
		            css=["css/appkeys.css"])

	##~~ BlueprintPlugin mixin

	@octoprint.plugin.BlueprintPlugin.route("/request", methods=["POST"])
	@no_firstrun_access
	def handle_request(self):
		data = flask.request.json
		if not "app" in data:
			return flask.make_response("No app name provided", 400)

		app_name = data["app"]
		user_id = None
		if "user" in data:
			user_id = data["user"]

		app_token, user_token = self._add_pending_decision(app_name, user_id=user_id)

		self._plugin_manager.send_plugin_message(self._identifier, dict(type="request_access",
		                                                                app_name=app_name,
		                                                                user_token=user_token,
		                                                                user_id=user_id))
		response = flask.jsonify(app_token=app_token)
		response.status_code = 202
		response.headers["Location"] = flask.url_for(".handle_decision_poll", app_token=app_token, _external=True)
		return response

	@octoprint.plugin.BlueprintPlugin.route("/request/<app_token>")
	@no_firstrun_access
	def handle_decision_poll(self, app_token):
		if self._is_pending(app_token):
			response = flask.jsonify(message="Awaiting decision")
			response.status_code = 202
			return response

		result = self._get_decision(app_token)
		if result:
			return flask.jsonify(api_key=result)

		return flask.abort(404)

	@octoprint.plugin.BlueprintPlugin.route("/decision/<user_token>", methods=["POST"])
	@restricted_access
	def handle_decision(self, user_token):
		data = flask.request.json
		if not "decision" in data:
			return flask.make_response("No decision provided", 400)
		decision = data["decision"] in valid_boolean_trues
		user_id = current_user.get_name()

		result = self._set_decision(user_token, decision, user_id)
		if not result:
			return flask.abort(404)

		return NO_CONTENT

	def is_blueprint_protected(self):
		return False # No API key required to request API access

	##~~ SimpleApiPlugin mixin

	def get_api_commands(self):
		return dict(generate=["app"],
		            revoke=["key"])

	def on_api_get(self, request):
		user_id = current_user.get_name()
		if not user_id:
			return flask.abort(403)

		return flask.jsonify(keys=map(lambda x: x.external(), self._api_keys_for_user(user_id)),
		                     pending=dict((x.user_token, x.external()) for x in self._get_pending(user_id)))

	def on_api_command(self, command, data):
		user_id = current_user.get_name()
		if not user_id:
			return flask.abort(403)

		if command == "revoke":
			api_key = data.get("key")
			if not api_key:
				return flask.abort(400)

			self._delete_api_key(user_id, api_key)

		elif command == "generate":
			# manual generateKey
			app_name = data.get("app")
			if not app_name:
				return flask.abort(400)

			self._add_api_key(user_id, app_name.strip())

		return NO_CONTENT

	##~~ key validator hook

	def validate_api_key(self, api_key, *args, **kwargs):
		return self._user_for_api_key(api_key)

	##~~ Helpers

	def _add_pending_decision(self, app_name, user_id=None):
		app_token = self._generate_key()
		user_token = self._generate_key()

		with self._pending_lock:
			self._pending_decisions.append(PendingDecision(app_name, app_token, user_id, user_token))

		return app_token, user_token

	def _is_pending(self, app_token):
		with self._pending_lock:
			for data in self._pending_decisions:
				if data.app_token == app_token:
					return True

		return False

	def _get_pending(self, user_id):
		result = []
		with self._pending_lock:
			for data in self._pending_decisions:
				if data.user_id == user_id or data.user_id is None:
					result.append(data)
		return result

	def _set_decision(self, user_token, decision, user_id):
		with self._pending_lock:
			for data in self._pending_decisions:
				if data.user_token == user_token and (data.user_id == user_id or data.user_id is None):
					pending = data
					break
			else:
				return False # not found

		if decision:
			with self._ready_lock:
				self._ready_decisions.append(ReadyDecision.for_pending(pending, user_id))

		with self._pending_lock:
			self._pending_decisions = filter(lambda x: x.user_token != user_token, self._pending_decisions)

		return True

	def _get_decision(self, app_token):
		with self._ready_lock:
			for data in self._ready_decisions:
				if data.app_token == app_token:
					decision = data
					break
			else:
				return False # not found

		api_key = self._add_api_key(decision.user_id, decision.app_id)

		with self._ready_lock:
			self._ready_decisions = filter(lambda x: x.app_token != app_token, self._ready_decisions)

		return api_key

	def _add_api_key(self, user_id, app_name):
		with self._keys_lock:
			# TODO: persist to disk
			for key in self._keys[user_id]:
				if key.app_id.lower() == app_name.lower():
					return key.api_key

			key = ActiveKey(app_name, self._generate_key())
			self._keys[user_id].append(key)
			return key.api_key

	def _delete_api_key(self, user_id, api_key):
		with self._keys_lock:
			# TODO: persist to disk
			self._keys[user_id] = filter(lambda x: x.api_key != api_key, self._keys[user_id])

	def _user_for_api_key(self, api_key):
		with self._keys_lock:
			for user_id, data in self._keys.items():
				if filter(lambda x: x.api_key == api_key, data):
					return self._user_manager.findUser(userid=user_id)
		return None

	def _api_keys_for_user(self, user_id):
		with self._keys_lock:
			return self._keys.get(user_id, [])

	def _generate_key(self):
		return hexlify(os.urandom(16))

__plugin_name__ = "Application Keys Plugin"
__plugin_description__ = "TODO"
__plugin_author__ = "Gina Häußge, Aldo Hoeben"
__plugin_implementation__ = AppKeysPlugin()
__plugin_hooks__ = {
	"octoprint.accesscontrol.keyvalidator": __plugin_implementation__.validate_api_key
}
