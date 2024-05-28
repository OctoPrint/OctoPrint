import os
from typing import Dict

import pyotp
from flask import abort, jsonify
from flask_babel import gettext
from flask_login import current_user

import octoprint.plugin
from octoprint.schema import BaseModel


class MfaTotpUserSettings(BaseModel):
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
        self._data = self._load_data()

    @property
    def _data_file(self):
        return self._settings.get_plugin_data_path("mfa_totp_data.json")

    def _load_data(self):
        if not os.path.exists(self._data_file):
            return MfaTotpSettings()

        try:
            return MfaTotpSettings.parse_file(self._data_file)
        except Exception as e:
            self._logger.exception(f"Error loading TOTP MFA data: {e}")
            return MfaTotpSettings()

    def _save_data(self):
        data_file = self._settings.get_plugin_data_path("mfa_totp_data.json")
        try:
            self._data.save_to_file(data_file)
        except Exception as e:
            self._logger.exception(f"Error saving TOTP MFA data: {e}")

    def _enroll_user(self, user):
        userid = user.get_id()
        if userid in self._data.users:
            raise ValueError("User already enrolled")

        secret = pyotp.random_base32()
        self._data.users[userid] = MfaTotpUserSettings(secret=secret)
        self._save_data()

        return pyotp.totp.TOTP(secret).provisioning_uri(
            name=userid, issuer_name="OctoPrint"
        )

    def _verify_user(self, user, token):
        userid = user.get_id()
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

    ##~~ TemplatePlugin mixin

    def get_template_configs(self):
        return [
            {
                "type": "usersettings",
                "name": gettext("TOTP Multi Factor Authentication"),
                "custom_bindings": True,
            },
        ]

    ##~~ SimpleApiPlugin mixin

    def on_api_get(self, request):
        userid = current_user.get_id()
        return jsonify(
            active=userid in self._data.users and self._data.users[userid].active
        )

    def get_api_commands(self):
        return {"enroll": [], "activate": ["token"], "deactivate": ["token"]}

    def on_api_command(self, command, data):
        user = current_user
        if not user or not user.is_authenticated or not user.is_active:
            return abort(403)

        userid = user.get_id()

        if command == "enroll":
            # user enrollment: generate secret and return provisioning URI
            if userid in self._data.users:
                return abort(409, "User already enrolled")
            return jsonify(uri=self._enroll_user(data["user"]))

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

            token = data.get("token", "")
            if not self._verify_user(userid, token):
                return abort(403, "Invalid token")

            self._data.users[userid].active = False
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

        if not self._verify_user(user, token):
            return abort(403)

        return False


__plugin_name__ = gettext("TOTP Multi Factor Authentication")
__plugin_pythoncompat__ = ">=3.7,<4"
__plugin_author__ = "foosel"
__plugin_license__ = "AGPLv3"
__plugin_description__ = gettext(
    "Plugin to support TOTP based Multi Factor Authentication in OctoPrint."
)
__plugin_implementation__ = MfaTotpPlugin()
