from flask import abort
from flask_babel import gettext

import octoprint.plugin


class MfaTotpPlugin(octoprint.plugin.MfaPlugin):
    def get_mfa_form(self, *args, **kwargs):
        return gettext("TOTP"), "mfa_totp_form.jinja2"

    def is_mfa_step_required(self, request, user, data, *args, **kwargs):
        if user.get_name() == "admin":
            token = data.get(f"mfa-{self._identifier}-token", "")
            if not token:
                return True

            if token != "secret":
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
