import os
import threading
import time
from collections import defaultdict

import flask
from flask_babel import gettext

import octoprint.plugin
from octoprint.access import ADMIN_GROUP, USER_GROUP
from octoprint.access.permissions import Permissions
from octoprint.server import NO_CONTENT, current_user
from octoprint.server.util import require_fresh_login_with
from octoprint.server.util.flask import (
    add_non_caching_response_headers,
    credentials_checked_recently,
    ensure_credentials_checked_recently,
    no_firstrun_access,
    restricted_access,
)
from octoprint.settings import valid_boolean_trues
from octoprint.util import ResettableTimer, atomic_write, generate_api_key, yaml

CUTOFF_TIME = 10 * 60  # 10min
POLL_TIMEOUT = 5  # 5 seconds


class AppAlreadyExists(Exception):
    pass


class PendingDecision:
    def __init__(self, app_id, app_token, user_id, user_token, timeout_callback=None):
        self.app_id = app_id
        self.app_token = app_token
        self.user_id = user_id
        self.user_token = user_token
        self.created = time.monotonic()

        if callable(timeout_callback):
            self.poll_timeout = ResettableTimer(
                POLL_TIMEOUT, timeout_callback, [user_token]
            )
            self.poll_timeout.start()

    def external(self):
        return {
            "app_id": self.app_id,
            "user_id": self.user_id,
            "user_token": self.user_token,
        }

    def __repr__(self):
        return "PendingDecision({!r}, {!r}, {!r}, {!r}, timeout_callback=...)".format(
            self.app_id, self.app_token, self.user_id, self.user_token
        )


class ReadyDecision:
    def __init__(self, app_id, app_token, user_id):
        self.app_id = app_id
        self.app_token = app_token
        self.user_id = user_id

    @classmethod
    def for_pending(cls, pending, user_id):
        return cls(pending.app_id, pending.app_token, user_id)

    def __repr__(self):
        return "ReadyDecision({!r}, {!r}, {!r})".format(
            self.app_id, self.app_token, self.user_id
        )


class ActiveKey:
    def __init__(self, app_id, api_key, user_id):
        self.app_id = app_id
        self.api_key = api_key
        self.user_id = user_id

    def external(self, incl_key=False):
        result = {"app_id": self.app_id, "user_id": self.user_id}
        if incl_key:
            result["api_key"] = self.api_key
        return result

    def internal(self):
        return {"app_id": self.app_id, "api_key": self.api_key}

    @classmethod
    def for_internal(cls, internal, user_id):
        return cls(internal["app_id"], internal["api_key"], user_id)

    def __repr__(self):
        return "ActiveKey({!r}, {!r}, {!r})".format(
            self.app_id, self.api_key, self.user_id
        )


class AppKeysPlugin(
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.BlueprintPlugin,
    octoprint.plugin.SimpleApiPlugin,
    octoprint.plugin.TemplatePlugin,
):
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
            {
                "key": "ADMIN",
                "name": "Admin access",
                "description": gettext("Allows administrating all application keys"),
                "roles": ["admin"],
                "dangerous": True,
                "default_groups": [ADMIN_GROUP],
            },
            {
                "key": "GRANT",
                "name": "Grant access",
                "description": gettext("Allows to grant app access"),
                "roles": ["user"],
                "default_groups": [USER_GROUP],
            },
        ]

    ##~~ TemplatePlugin

    def get_template_configs(self):
        return [
            {"type": "usersettings", "name": gettext("Application Keys")},
            {"type": "settings", "name": gettext("Application Keys")},
        ]

    ##~~ AssetPlugin

    def get_assets(self):
        return {
            "js": ["js/appkeys.js"],
            "clientjs": ["clientjs/appkeys.js"],
            "less": ["less/appkeys.less"],
            "css": ["css/appkeys.css"],
        }

    ##~~ BlueprintPlugin mixin

    @octoprint.plugin.BlueprintPlugin.route("/probe", methods=["GET"])
    @no_firstrun_access
    def handle_probe(self):
        return NO_CONTENT

    @octoprint.plugin.BlueprintPlugin.route("/request", methods=["POST"])
    @octoprint.plugin.BlueprintPlugin.csrf_exempt()
    @no_firstrun_access
    def handle_request(self):
        data = flask.request.json
        if data is None:
            flask.abort(400, description="Missing key request")

        if "app" not in data:
            flask.abort(400, description="No app name provided")

        app_name = data["app"]
        user_id = None
        if "user" in data and data["user"]:
            user_id = data["user"]

        app_token, user_token = self._add_pending_decision(app_name, user_id=user_id)
        auth_dialog = flask.url_for(
            "plugin.appkeys.handle_auth_dialog", app_token=app_token, _external=True
        ) + (f"?user={user_id}" if user_id else "")

        self._plugin_manager.send_plugin_message(
            self._identifier,
            {
                "type": "request_access",
                "app_name": app_name,
                "user_token": user_token,
                "user_id": user_id,
            },
        )
        response = flask.jsonify(app_token=app_token, auth_dialog=auth_dialog)
        response.status_code = 201
        response.headers["Location"] = flask.url_for(
            ".handle_decision_poll", app_token=app_token, _external=True
        )
        return response

    @octoprint.plugin.BlueprintPlugin.route("/request/<app_token>", methods=["GET"])
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

    @octoprint.plugin.BlueprintPlugin.route("/auth/<app_token>", methods=["GET"])
    @no_firstrun_access
    def handle_auth_dialog(self, app_token):
        from octoprint.server.util.csrf import add_csrf_cookie

        user_id = current_user.get_name()
        required_user = flask.request.args.get("user", None)

        pendings = self._get_pending_by_app_token(app_token)
        if not pendings:
            return flask.abort(404)

        response = require_fresh_login_with(
            permissions=[Permissions.PLUGIN_APPKEYS_GRANT], user_id=required_user
        )
        if response:
            return response

        pending = None
        for p in pendings:
            if p.user_id == required_user or (not required_user and p.user_id == user_id):
                pending = p
                break
        else:
            return flask.abort(404)

        app_id = pending.app_id
        user_token = pending.user_token
        redirect_url = flask.request.args.get("redirect", "")

        response = flask.make_response(
            flask.render_template(
                "plugin_appkeys/appkeys_authdialog.jinja2",
                app=app_id,
                user=user_id,
                user_token=user_token,
                redirect_url=redirect_url,
                theming=[],
                request_text=gettext(
                    '"<strong>%(app)s</strong>" has requested access to control OctoPrint through the API.'
                ),
            )
        )
        return add_csrf_cookie(add_non_caching_response_headers(response))

    @octoprint.plugin.BlueprintPlugin.route("/decision/<user_token>", methods=["POST"])
    @restricted_access
    def handle_decision(self, user_token):
        data = flask.request.json
        if "decision" not in data:
            flask.abort(400, description="No decision provided")

        if not Permissions.PLUGIN_APPKEYS_GRANT.can():
            flask.abort(403, description="No permission to grant app access")

        ensure_credentials_checked_recently()

        decision = data["decision"] in valid_boolean_trues
        user_id = current_user.get_name()

        result = self._set_decision(user_token, decision, user_id)
        if not result:
            return flask.abort(404)

        # Close access_request dialog for this request on all open OctoPrint connections
        self._plugin_manager.send_plugin_message(
            self._identifier, {"type": "end_request", "user_token": user_token}
        )

        return NO_CONTENT

    def is_blueprint_protected(self):
        return False  # No API key required to request API access

    def is_blueprint_csrf_protected(self):
        return True  # protect anything that isn't explicitly marked as exempt

    ##~~ SimpleApiPlugin mixin

    def get_api_commands(self):
        return {"generate": ["app"], "revoke": []}

    def on_api_get(self, request):
        user_id = current_user.get_name()
        if not user_id:
            return flask.abort(403)

        # GET ?app_id=...[&user_id=...]
        if request.values.get("app"):
            app_id = request.values.get("app")
            user_id = request.values.get("user", user_id)
            if (
                user_id != current_user.get_name()
                and not Permissions.PLUGIN_APPKEYS_ADMIN.can()
            ):
                return flask.abort(403)

            key = self._api_key_for_user_and_app_id(user_id, app_id)
            if not key:
                return flask.abort(404)

            return flask.jsonify(
                key=key.external(incl_key=credentials_checked_recently())
            )

        # GET ?all=true (admin only)
        if (
            request.values.get("all") in valid_boolean_trues
            and Permissions.PLUGIN_APPKEYS_ADMIN.can()
        ):
            keys = self._all_api_keys()

        else:
            keys = self._api_keys_for_user(user_id)

        return flask.jsonify(
            keys=list(
                map(lambda x: x.external(), keys),
            ),
            pending={
                x.user_token: x.external() for x in self._get_pending_by_user_id(user_id)
            },
        )

    def on_api_command(self, command, data):
        user_id = current_user.get_name()
        if not user_id:
            return flask.abort(403)

        if command == "revoke":
            api_key = data.get("key")

            if api_key:
                # deprecated key based revoke?
                from flask import request

                self._logger.warning(
                    f"Deprecated key based revoke command sent to /api/plugin/appkeys by {request.remote_addr}, should be migrated to use app id/user tuple"
                )

            else:
                # newer app/user based revoke?
                user = data.get("user", user_id)
                app = data.get("app")
                if not app:
                    return flask.abort(400, description="Need either app or key")

                api_key = self._api_key_for_user_and_app_id(user, app)

            if not api_key:
                return flask.abort(400, description="Need either app or key")

            if not Permissions.PLUGIN_APPKEYS_ADMIN.can():
                user_for_key = self._user_for_api_key(api_key)
                if user_for_key is None or user_for_key.get_id() != user_id:
                    return flask.abort(403)

            ensure_credentials_checked_recently()

            self._delete_api_key(api_key)

        elif command == "generate":
            # manual generateKey
            app_name = data.get("app")
            if not app_name:
                return flask.abort(400)

            selected_user_id = data.get("user", user_id)
            if selected_user_id != user_id and not Permissions.PLUGIN_APPKEYS_ADMIN.can():
                return flask.abort(403)

            ensure_credentials_checked_recently()

            key = self._add_api_key(selected_user_id, app_name.strip())
            return flask.jsonify(user_id=selected_user_id, app_id=app_name, api_key=key)

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
            self._pending_decisions.append(
                PendingDecision(
                    app_name,
                    app_token,
                    user_id,
                    user_token,
                    timeout_callback=self._expire_pending,
                )
            )

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
            self._pending_decisions = list(
                filter(lambda x: x.user_token != user_token, self._pending_decisions)
            )
            len_after = len(self._pending_decisions)

            if len_after < len_before:
                self._plugin_manager.send_plugin_message(
                    self._identifier, {"type": "end_request", "user_token": user_token}
                )

    def _remove_stale_pending(self):
        with self._pending_lock:
            cutoff = time.monotonic() - CUTOFF_TIME
            len_before = len(self._pending_decisions)
            self._pending_decisions = list(
                filter(lambda x: x.created >= cutoff, self._pending_decisions)
            )
            len_after = len(self._pending_decisions)
            if len_after < len_before:
                self._logger.info(
                    "Deleted {} stale pending authorization requests".format(
                        len_before - len_after
                    )
                )

    def _set_decision(self, user_token, decision, user_id):
        with self._pending_lock:
            self._remove_stale_pending()
            for data in self._pending_decisions:
                if data.user_token == user_token and (
                    data.user_id == user_id or data.user_id is None
                ):
                    pending = data
                    break
            else:
                return False  # not found

        if decision:
            with self._ready_lock:
                self._ready_decisions.append(ReadyDecision.for_pending(pending, user_id))

        with self._pending_lock:
            self._pending_decisions = list(
                filter(lambda x: x.user_token != user_token, self._pending_decisions)
            )

        return True

    def _get_decision(self, app_token):
        self._remove_stale_pending()

        with self._ready_lock:
            for data in self._ready_decisions:
                if data.app_token == app_token:
                    decision = data
                    break
            else:
                return False  # not found

        api_key = self._add_api_key(decision.user_id, decision.app_id)

        with self._ready_lock:
            self._ready_decisions = list(
                filter(lambda x: x.app_token != app_token, self._ready_decisions)
            )

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
        if isinstance(api_key, ActiveKey):
            api_key = api_key.api_key

        with self._keys_lock:
            for user_id, data in self._keys.items():
                self._keys[user_id] = list(filter(lambda x: x.api_key != api_key, data))
            self._save_keys()

    def _user_for_api_key(self, api_key):
        if isinstance(api_key, ActiveKey):
            api_key = api_key.api_key

        with self._keys_lock:
            for user_id, data in self._keys.items():
                if any(filter(lambda x: x.api_key == api_key, data)):
                    return self._user_manager.find_user(userid=user_id)
        return None

    def _api_keys_for_user(self, user_id):
        with self._keys_lock:
            return self._keys[user_id]

    def _all_api_keys(self):
        with self._keys_lock:
            result = []
            for keys in self._keys.values():
                result += keys
        return result

    def _api_key_for_user_and_app_id(self, user_id, app_id):
        with self._keys_lock:
            if user_id not in self._keys:
                return None

            for key in self._keys[user_id]:
                if key.app_id.lower() == app_id.lower():
                    return key

        return None

    def _generate_key(self):
        return generate_api_key()

    def _load_keys(self):
        with self._keys_lock:
            if not os.path.exists(self._key_path):
                return

            try:
                persisted = yaml.load_from_file(path=self._key_path)
            except Exception:
                self._logger.exception(
                    f"Could not load application keys from {self._key_path}"
                )
                return

            if not isinstance(persisted, dict):
                return

            keys = defaultdict(list)
            for user_id, persisted_keys in persisted.items():
                keys[user_id] = [
                    ActiveKey.for_internal(x, user_id) for x in persisted_keys
                ]
            self._keys = keys

    def _save_keys(self):
        with self._keys_lock:
            to_persist = {}
            for user_id, keys in self._keys.items():
                to_persist[user_id] = [x.internal() for x in keys]

            try:
                with atomic_write(self._key_path, mode="wt") as f:
                    yaml.save_to_file(to_persist, file=f)
            except Exception:
                self._logger.exception(
                    f"Could not write application keys to {self._key_path}"
                )


__plugin_name__ = "Application Keys Plugin"
__plugin_description__ = (
    "Implements a workflow for third party clients to obtain API keys"
)
__plugin_author__ = "Gina Häußge, Aldo Hoeben"
__plugin_disabling_discouraged__ = gettext(
    "Without this plugin third party clients will no longer be able to "
    "obtain an API key without you manually copy-pasting it."
)
__plugin_license__ = "AGPLv3"
__plugin_pythoncompat__ = ">=3.7,<4"
__plugin_implementation__ = AppKeysPlugin()
__plugin_hooks__ = {
    "octoprint.accesscontrol.keyvalidator": __plugin_implementation__.validate_api_key,
    "octoprint.access.permissions": __plugin_implementation__.get_additional_permissions,
}
