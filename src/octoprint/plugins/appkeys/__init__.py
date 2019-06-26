# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import flask
import threading
import os
import yaml
import io
import time
from binascii import hexlify
from collections import defaultdict
from flask_babel import gettext

import octoprint.plugin
from octoprint.settings import valid_boolean_trues
from octoprint.server.util.flask import restricted_access, no_firstrun_access
from octoprint.server import NO_CONTENT, current_user, admin_permission
from octoprint.util import atomic_write, monotonic_time, ResettableTimer

from octoprint.access import ADMIN_GROUP
from octoprint.access.permissions import Permissions


CUTOFF_TIME = 10 * 60 # 10min
POLL_TIMEOUT = 5 # 5 seconds

class AppAlreadyExists(Exception):
	pass


class PendingDecision(object):
	def __init__(self, app_id, app_token, user_id, user_token, timeout_callback=None):
		self.app_id = app_id
		self.app_token = app_token
		self.user_id = user_id
		self.user_token = user_token
		self.created = monotonic_time()

		if callable(timeout_callback):
			self.poll_timeout = ResettableTimer(POLL_TIMEOUT, timeout_callback, [user_token])
			self.poll_timeout.start()

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
	def __init__(self, app_id, api_key, user_id):
		self.app_id = app_id
		self.api_key = api_key
		self.user_id = user_id

	def external(self):
		return dict(app_id=self.app_id,
		            api_key=self.api_key,
		            user_id=self.user_id)

	def internal(self):
		return dict(app_id=self.app_id,
		            api_key=self.api_key)

	@classmethod
	def for_internal(cls, internal, user_id):
		return cls(internal["app_id"], internal["api_key"], user_id)


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

		self._key_path = None

	def initialize(self):
		self._key_path = os.path.join(self.get_plugin_data_folder(), "keys.yaml")
		self._load_keys()

	# Additional permissions hook

	def get_additional_permissions(self):
		return [
			dict(key="ADMIN",
			     name="Admin access",
			     description=gettext("Allows administrating all application keys"),
			     roles=["admin"],
			     dangerous=True,
			     default_groups=[ADMIN_GROUP])
		]

	##~~ TemplatePlugin

	def get_template_configs(self):
		return [dict(type="usersettings", name=gettext("Application Keys")),
		        dict(type="settings", name=gettext("Application Keys"))]

	##~~ AssetPlugin

	def get_assets(self):
		return dict(js=["js/appkeys.js"],
		            clientjs=["clientjs/appkeys.js"],
		            less=["less/appkeys.less"],
		            css=["css/appkeys.css"])

	##~~ BlueprintPlugin mixin

	@octoprint.plugin.BlueprintPlugin.route("/probe", methods=["GET"])
	@no_firstrun_access
	def handle_probe(self):
		return NO_CONTENT

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
		response.status_code = 201
		response.headers["Location"] = flask.url_for(".handle_decision_poll", app_token=app_token, _external=True)
		return response

	@octoprint.plugin.BlueprintPlugin.route("/request/<app_token>")
	@no_firstrun_access
	def handle_decision_poll(self, app_token):
		result = self._get_pending_by_app_token(app_token)
		if result:
			for pending_decision in result:
				pending_decision.poll_timeout.reset()

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

		# Close access_request dialog for this request on all open OctoPrint connections
		self._plugin_manager.send_plugin_message(self._identifier, dict(
			type="end_request",
			user_token=user_token
		))

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

		if request.values.get("all") in valid_boolean_trues and Permissions.PLUGIN_APPKEYS_ADMIN.can():
			keys = self._all_api_keys()
		else:
			keys = self._api_keys_for_user(user_id)

		return flask.jsonify(keys=list(map(lambda x: x.external(), keys)),
		                     pending=dict((x.user_token, x.external()) for x in self._get_pending_by_user_id(user_id)))

	def on_api_command(self, command, data):
		user_id = current_user.get_name()
		if not user_id:
			return flask.abort(403)

		if command == "revoke":
			api_key = data.get("key")
			if not api_key:
				return flask.abort(400)

			if not admin_permission.can():
				user_for_key = self._user_for_api_key(api_key)
				if user_for_key is None or user_for_key.user_id != user_id:
					return flask.abort(403)

			self._delete_api_key(api_key)

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
			self._remove_stale_pending()
			self._pending_decisions.append(PendingDecision(app_name, app_token, user_id, user_token,
			                                               timeout_callback=self._expire_pending))

		return app_token, user_token

	def _get_pending_by_app_token(self, app_token):
		result = []
		with self._pending_lock:
			self._remove_stale_pending()
			for data in self._pending_decisions:
				if data.app_token == app_token:
					result.append(data)
		return result

	def _get_pending_by_user_id(self, user_id):
		result = []
		with self._pending_lock:
			self._remove_stale_pending()
			for data in self._pending_decisions:
				if data.user_id == user_id or data.user_id is None:
					result.append(data)
		return result

	def _expire_pending(self, user_token):
		with self._pending_lock:
			len_before = len(self._pending_decisions)
			self._pending_decisions = list(filter(lambda x: x.user_token != user_token,
				                                  self._pending_decisions))
			len_after = len(self._pending_decisions)

			if len_after < len_before:
				self._plugin_manager.send_plugin_message(self._identifier, dict(
					type="end_request",
					user_token=user_token
				))

	def _remove_stale_pending(self):
		with self._pending_lock:
			cutoff = monotonic_time() - CUTOFF_TIME
			len_before = len(self._pending_decisions)
			self._pending_decisions = list(filter(lambda x: x.created >= cutoff,
			                                      self._pending_decisions))
			len_after = len(self._pending_decisions)
			if len_after < len_before:
				self._logger.info("Deleted {} stale pending authorization requests".format(len_before - len_after))

	def _set_decision(self, user_token, decision, user_id):
		with self._pending_lock:
			self._remove_stale_pending()
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
			self._pending_decisions = list(filter(lambda x: x.user_token != user_token,
				                                  self._pending_decisions))

		return True

	def _get_decision(self, app_token):
		self._remove_stale_pending()

		with self._ready_lock:
			for data in self._ready_decisions:
				if data.app_token == app_token:
					decision = data
					break
			else:
				return False # not found

		api_key = self._add_api_key(decision.user_id, decision.app_id)

		with self._ready_lock:
			self._ready_decisions = list(filter(lambda x: x.app_token != app_token,
				                                self._ready_decisions))

		return api_key

	def _add_api_key(self, user_id, app_name):
		with self._keys_lock:
			for key in self._keys[user_id]:
				if key.app_id.lower() == app_name.lower():
					return key.api_key

			key = ActiveKey(app_name, self._generate_key(), user_id)
			self._keys[user_id].append(key)
			self._save_keys()
			return key.api_key

	def _delete_api_key(self, api_key):
		with self._keys_lock:
			for user_id, data in self._keys.items():
				self._keys[user_id] = list(filter(lambda x: x.api_key != api_key, data))
			self._save_keys()

	def _user_for_api_key(self, api_key):
		with self._keys_lock:
			for user_id, data in self._keys.items():
				if any(filter(lambda x: x.api_key == api_key, data)):
					if self._user_manager.enabled:
						return self._user_manager.findUser(userid=user_id)
					elif user_id == "_admin" or user_id == "dummy":
						# dummy = backwards compatible
						return self._user_manager.anonymous_user_factory()
		return None

	def _api_keys_for_user(self, user_id):
		with self._keys_lock:
			return self._keys[user_id]

	def _all_api_keys(self):
		with self._keys_lock:
			result = []
			for user_id, keys in self._keys.items():
				result += keys
		return result

	def _generate_key(self):
		return hexlify(os.urandom(16))

	def _load_keys(self):
		with self._keys_lock:
			if not os.path.exists(self._key_path):
				return

			try:
				with io.open(self._key_path, 'rt', encoding="utf-8", errors="strict") as f:
					persisted = yaml.safe_load(f)
			except Exception:
				self._logger.exception("Could not load application keys from {}".format(self._key_path))
				return

			if not isinstance(persisted, dict):
				return

			keys = defaultdict(list)
			for user_id, persisted_keys in persisted.items():
				keys[user_id] = [ActiveKey.for_internal(x, user_id) for x in persisted_keys]
			self._keys = keys

	def _save_keys(self):
		with self._keys_lock:
			to_persist = dict()
			for user_id, keys in self._keys.items():
				to_persist[user_id] = [x.internal() for x in keys]

			try:
				with atomic_write(self._key_path, mode='wt') as f:
					yaml.safe_dump(to_persist, f, allow_unicode=True)
			except Exception:
				self._logger.exception("Could not write application keys to {}".format(self._key_path))

__plugin_name__ = "Application Keys Plugin"
__plugin_description__ = "Implements a workflow for third party clients to obtain API keys"
__plugin_author__ = "Gina Häußge, Aldo Hoeben"
__plugin_disabling_discouraged__ = gettext("Without this plugin third party clients will no longer be able to "
                                           "obtain an API key without you manually copy-pasting it.")
__plugin_implementation__ = AppKeysPlugin()
__plugin_hooks__ = {
	"octoprint.accesscontrol.keyvalidator": __plugin_implementation__.validate_api_key,
	"octoprint.access.permissions": __plugin_implementation__.get_additional_permissions
}
