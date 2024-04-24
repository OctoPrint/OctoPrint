from flask_babel import gettext

import octoprint.plugin


class MfaTotpPlugin(octoprint.plugin.MfaPlugin):
    def get_mfa_form(self, *args, **kwargs):
        return "mfa_totp_form.jinja2"


__plugin_name__ = gettext("TOTP Fulti Factor Authentication")
__plugin_pythoncompat__ = ">=3.7,<4"
__plugin_author__ = "foosel"
__plugin_license__ = "AGPLv3"
__plugin_description__ = gettext(
    "Plugin to support TOTP based Multi Factor Authentication in OctoPrint."
)
__plugin_implementation__ = MfaTotpPlugin()
