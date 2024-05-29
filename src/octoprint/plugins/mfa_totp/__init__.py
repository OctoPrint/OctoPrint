import os
import time
from typing import Dict

import pyotp
from flask import abort, jsonify
from flask_babel import gettext
from flask_login import current_user

import octoprint.plugin
from octoprint.schema import BaseModel

CLEANUP_CUTOFF = 60 * 30  # 30 minutes


class MfaTotpUserSettings(BaseModel):
    created: int
    secret: str
    last_used: str = None
    active: bool = False


class MfaTotpSettings(BaseModel):
    users: Dict[str, MfaTotpUserSettings] = {}


class MfaTotpPlugin(
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.MfaPlugin,
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.SimpleApiPlugin,
    octoprint.plugin.TemplatePlugin,
):
    def __init__(self):
        self._data = None

    def initialize(self):
        self._load_data()

    @property
    def _data_file(self):
        return os.path.join(self.get_plugin_data_folder(), "mfa_totp_data.json")

    def _load_data(self):
        if not os.path.exists(self._data_file):
            return MfaTotpSettings()

        try:
            self._data = MfaTotpSettings.parse_file(self._data_file)
        except Exception as e:
            self._logger.exception(f"Error loading TOTP MFA data: {e}")
            self._data = MfaTotpSettings()

        if self._cleanup_data():
            self._save_data()

    def _save_data(self):
        self._cleanup_data()
        try:
            with open(self._data_file, "w") as f:
                f.write(self._data.json(indent=4))
        except Exception as e:
            self._logger.exception(f"Error saving TOTP MFA data: {e}")

    def _cleanup_data(self):
        now = time.time()
        dirty = False
        for userid, user in list(self._data.users.items()):
            if user.created < now - CLEANUP_CUTOFF:
                self._data.users.pop(userid)
                dirty = True
        return dirty

    def _enroll_user(self, userid):
        if userid in self._data.users and self._data.users[userid].active:
            raise ValueError("User already enrolled")

        if userid in self._data.users:
            secret = self._data.users[userid].secret
        else:
            secret = pyotp.random_base32()
            self._data.users[userid] = MfaTotpUserSettings(
                created=time.time(), secret=secret
            )
            self._save_data()

        return self._provisioning_uri(userid)

    def _provisioning_uri(self, userid):
        if userid not in self._data.users:
            raise ValueError("User not enrolled")

        secret = self._data.users[userid].secret
        return pyotp.totp.TOTP(secret).provisioning_uri(
            name=userid, issuer_name="OctoPrint"
        )

    def _verify_user(self, userid, token):
        if userid not in self._data.users:
            return False

        if self._data.users[userid].last_used == token:
            # prevent replay attacks
            return False

        secret = self._data.users[userid].secret
        if pyotp.TOTP(secret).verify(token):
            self._data.users[userid].last_used = token
            self._save_data()
            return True

    ##~~ AssetPlugin mixin

    def get_assets(self):
        return {
            "js": ["js/mfa_totp.js"],
            "clientjs": ["clientjs/mfa_totp.js"],
        }

    ##~~ TemplatePlugin mixin

    def get_template_configs(self):
        return [
            {
                "type": "usersettings",
                "name": gettext("2FA: TOTP"),
            },
        ]

    ##~~ SimpleApiPlugin mixin

    def on_api_get(self, request):
        userid = current_user.get_id()
        return jsonify(
            active=userid in self._data.users and self._data.users[userid].active
        )

    def get_api_commands(self):
        return {"enroll": [], "activate": ["token"], "deactivate": []}

    def on_api_command(self, command, data):
        user = current_user
        if not user or not user.is_authenticated or not user.is_active:
            return abort(403)

        userid = user.get_id()

        if command == "enroll":
            # user enrollment: generate secret and return provisioning URI
            if userid in self._data.users and self._data.users[userid].active:
                return abort(409, "User already enrolled")
            return jsonify(uri=self._enroll_user(userid))

        elif command == "activate":
            # activate user: verify token, only then activate user
            if userid not in self._data.users:
                return abort(404, "User not enrolled")
            if self._data.users[userid].active:
                return abort(409, "User enrollment already verified")

            token = data.get("token", "")
            if not self._verify_user(userid, token):
                return abort(403, "Invalid token")

            self._data.users[userid].active = True
            self._save_data()
            return jsonify()

        elif command == "deactivate":
            # deactivate user: verify token, only then deactivate user
            if userid not in self._data.users:
                return abort(404, "User not enrolled")

            if self._data.users[userid].active:
                token = data.get("token", "")
                if not self._verify_user(userid, token):
                    return abort(403, "Invalid token")

            self._data.users.pop(userid)
            self._save_data()
            return jsonify(True)

    ##~~ MfaPlugin mixin

    def get_mfa_form(self, *args, **kwargs):
        return gettext("TOTP"), "mfa_totp_form.jinja2"

    def is_mfa_step_required(self, request, user, data, *args, **kwargs):
        userid = user.get_id()
        if userid not in self._data.users or not self._data.users[userid].active:
            return False

        token = data.get(f"mfa-{self._identifier}-token", "")
        if not token:
            return True

        if not self._verify_user(userid, token):
            return abort(403)

        return False


__plugin_name__ = gettext("Two Factor Authentication: TOTP")
__plugin_pythoncompat__ = ">=3.7,<4"
__plugin_author__ = "foosel"
__plugin_license__ = "AGPLv3"
__plugin_description__ = gettext(
    "Plugin to support TOTP based Two Factor Authentication in OctoPrint."
)
__plugin_implementation__ = MfaTotpPlugin()
