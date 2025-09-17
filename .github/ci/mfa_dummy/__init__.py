import octoprint.plugin
from octoprint.plugin.types import WrongMfaCredentials


class MfaDummyPlugin(octoprint.plugin.MfaPlugin):
    def is_mfa_enabled(self, user):
        return user.get_id() == "mfa"

    def has_mfa_credentials(self, request, user, data, *args, **kwargs):
        userid = user.get_id()
        if userid != "mfa":
            return True

        token = data.get(f"mfa-{self._identifier}-token", "")
        if not token:
            # token not there? we need to ask for it
            return False

        if token != "secret":
            raise WrongMfaCredentials("Incorrect token")

        return True


__plugin_name__ = "MFA Dummy"
__plugin_version__ = "0.1.0"
__plugin_description__ = "A dummy MFA plugin for testing"
__plugin_pythoncompat__ = ">=3,<4"
__plugin_implementation__ = MfaDummyPlugin()
