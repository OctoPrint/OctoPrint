__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"

import inspect
import sys

from flask_babel import gettext

import octoprint.plugin
from octoprint.access import ADMIN_GROUP, USER_GROUP


# noinspection PyUnresolvedReferences,PyMethodMayBeStatic
class ServerCommandsSubwizard:
    def _is_servercommands_wizard_firstrunonly(self):
        return True

    def _is_servercommands_wizard_required(self):
        system_shutdown_command = self._settings.global_get(
            ["server", "commands", "systemShutdownCommand"]
        )
        system_restart_command = self._settings.global_get(
            ["server", "commands", "systemRestartCommand"]
        )
        server_restart_command = self._settings.global_get(
            ["server", "commands", "serverRestartCommand"]
        )

        return not (
            system_shutdown_command and system_restart_command and server_restart_command
        )

    def _get_servercommands_wizard_details(self):
        return {"required": self._is_servercommands_wizard_required()}

    def _get_servercommands_wizard_name(self):
        return gettext("Server Commands")


# noinspection PyUnresolvedReferences,PyMethodMayBeStatic
class WebcamSubwizard:
    def _is_webcam_wizard_firstrunonly(self):
        return True

    def _is_webcam_wizard_required(self):
        webcam_snapshot_url = self._settings.global_get(["webcam", "snapshot"])
        webcam_stream_url = self._settings.global_get(["webcam", "stream"])
        ffmpeg_path = self._settings.global_get(["webcam", "ffmpeg"])

        return not (webcam_snapshot_url and webcam_stream_url and ffmpeg_path)

    def _get_webcam_wizard_details(self):
        return {"required": self._is_webcam_wizard_required()}

    def _get_webcam_wizard_name(self):
        return gettext("Webcam & Timelapse")


# noinspection PyUnresolvedReferences,PyMethodMayBeStatic
class AclSubwizard:
    def _is_acl_wizard_firstrunonly(self):
        return False

    def _is_acl_wizard_required(self):
        return not self._user_manager.has_been_customized()

    def _get_acl_wizard_details(self):
        return {"required": self._is_acl_wizard_required()}

    def _get_acl_wizard_name(self):
        return gettext("Access Control")

    def _get_acl_additional_wizard_template_data(self):
        return {"mandatory": self._is_acl_wizard_required()}

    @octoprint.plugin.BlueprintPlugin.route("/acl", methods=["POST"])
    def acl_wizard_api(self):
        from flask import abort, request

        from octoprint.server.api import NO_CONTENT

        if (
            not self._settings.global_get(["server", "firstRun"])
            and self._user_manager.has_been_customized()
        ):
            abort(404)

        data = request.get_json()
        if data is None:
            data = request.values

        if (
            "user" in data
            and "pass1" in data
            and "pass2" in data
            and data["pass1"] == data["pass2"]
        ):
            # configure access control
            self._user_manager.add_user(
                data["user"],
                data["pass1"],
                True,
                [],
                [USER_GROUP, ADMIN_GROUP],
                overwrite=True,
            )
        self._settings.save()
        return NO_CONTENT


# noinspection PyUnresolvedReferences,PyMethodMayBeStatic
class OnlineCheckSubwizard:
    def _is_onlinecheck_wizard_firstrunonly(self):
        return False

    def _is_onlinecheck_wizard_required(self):
        return self._settings.global_get(["server", "onlineCheck", "enabled"]) is None

    def _get_onlinecheck_wizard_details(self):
        return {"required": self._is_onlinecheck_wizard_required()}

    def _get_onlinecheck_wizard_name(self):
        return gettext("Online Connectivity Check")

    def _get_onlinecheck_additional_wizard_template_data(self):
        return {"mandatory": self._is_onlinecheck_wizard_required()}


# noinspection PyUnresolvedReferences,PyMethodMayBeStatic
class PluginBlacklistSubwizard:
    def _is_pluginblacklist_wizard_firstrunonly(self):
        return False

    def _is_pluginblacklist_wizard_required(self):
        return self._settings.global_get(["server", "pluginBlacklist", "enabled"]) is None

    def _get_pluginblacklist_wizard_details(self):
        return {"required": self._is_pluginblacklist_wizard_required()}

    def _get_pluginblacklist_wizard_name(self):
        return gettext("Plugin Blacklist")

    def _get_pluginblacklist_additional_wizard_template_data(self):
        return {"mandatory": self._is_pluginblacklist_wizard_required()}


# noinspection PyUnresolvedReferences,PyMethodMayBeStatic
class PrinterProfileSubwizard:
    def _is_printerprofile_wizard_firstrunonly(self):
        return True

    def _is_printerprofile_wizard_required(self):
        return (
            self._printer_profile_manager.is_default_unmodified()
            and self._printer_profile_manager.profile_count == 1
        )

    def _get_printerprofile_wizard_details(self):
        return {"required": self._is_printerprofile_wizard_required()}

    def _get_printerprofile_wizard_name(self):
        return gettext("Default Printer Profile")


Subwizards = type(
    "Subwizards",
    tuple(
        cls
        for clsname, cls in inspect.getmembers(sys.modules[__name__], inspect.isclass)
        if clsname.endswith("Subwizard")
    ),
    {},
)
