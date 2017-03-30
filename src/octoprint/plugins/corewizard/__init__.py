# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


import octoprint.plugin


from flask.ext.babel import gettext


class CoreWizardPlugin(octoprint.plugin.AssetPlugin,
                       octoprint.plugin.TemplatePlugin,
                       octoprint.plugin.WizardPlugin,
                       octoprint.plugin.SettingsPlugin,
                       octoprint.plugin.BlueprintPlugin):

	#~~ TemplatePlugin API

	def get_template_configs(self):
		required = self._get_subwizard_attrs("_is_", "_wizard_required")
		names = self._get_subwizard_attrs("_get_", "_wizard_name")
		additional = self._get_subwizard_attrs("_get_", "_additional_wizard_template_data")

		result = list()
		for key, method in required.items():
			if not method():
				continue

			if not key in names:
				continue

			name = names[key]()
			if not name:
				continue

			config = dict(type="wizard", name=name, template="corewizard_{}_wizard.jinja2".format(key), div="wizard_plugin_corewizard_{}".format(key))
			if key in additional:
				additional_result = additional[key]()
				if additional_result:
					config.update(additional_result)
			result.append(config)

		return result

	#~~ AssetPlugin API

	def get_assets(self):
		return dict(
			js=["js/corewizard.js"]
		)

	#~~ WizardPlugin API

	def is_wizard_required(self):
		methods = self._get_subwizard_attrs("_is_", "_wizard_required")
		return self._settings.global_get(["server", "firstRun"]) and any(map(lambda m: m(), methods.values()))

	def get_wizard_details(self):
		result = dict()

		def add_result(key, method):
			result[key] = method()
		self._get_subwizard_attrs("_get_", "_wizard_details", add_result)

		return result

	#~~ ACL subwizard

	def _is_acl_wizard_required(self):
		return self._user_manager.enabled and not self._user_manager.hasBeenCustomized()

	def _get_acl_wizard_details(self):
		return dict()

	def _get_acl_wizard_name(self):
		return gettext("Access Control")

	def _get_acl_additional_wizard_template_data(self):
		return dict(mandatory=self._is_acl_wizard_required())

	@octoprint.plugin.BlueprintPlugin.route("/acl", methods=["POST"])
	def acl_wizard_api(self):
		from flask import request
		from octoprint.server.api import valid_boolean_trues, NO_CONTENT

		data = request.values
		if hasattr(request, "json") and request.json:
			data = request.json

		if "ac" in data and data["ac"] in valid_boolean_trues and \
						"user" in data.keys() and "pass1" in data.keys() and \
						"pass2" in data.keys() and data["pass1"] == data["pass2"]:
			# configure access control
			self._settings.global_set_boolean(["accessControl", "enabled"], True)
			self._user_manager.enable()
			self._user_manager.addUser(data["user"], data["pass1"], True, ["user", "admin"], overwrite=True)
		elif "ac" in data.keys() and not data["ac"] in valid_boolean_trues:
			# disable access control
			self._settings.global_set_boolean(["accessControl", "enabled"], False)

			octoprint.server.loginManager.anonymous_user = octoprint.users.DummyUser
			octoprint.server.principals.identity_loaders.appendleft(octoprint.users.dummy_identity_loader)

			self._user_manager.disable()
		self._settings.save()
		return NO_CONTENT

	#~~ Webcam subwizard

	def _is_webcam_wizard_required(self):
		webcam_snapshot_url = self._settings.global_get(["webcam", "snapshot"])
		webcam_stream_url = self._settings.global_get(["webcam", "stream"])
		ffmpeg_path = self._settings.global_get(["webcam", "ffmpeg"])

		return not (webcam_snapshot_url and webcam_stream_url and ffmpeg_path)

	def _get_webcam_wizard_details(self):
		return dict()

	def _get_webcam_wizard_name(self):
		return gettext("Webcam & Timelapse")

	#~~ Server commands subwizard

	def _is_servercommands_wizard_required(self):
		system_shutdown_command = self._settings.global_get(["server", "commands", "systemShutdownCommand"])
		system_restart_command = self._settings.global_get(["server", "commands", "systemRestartCommand"])
		server_restart_command = self._settings.global_get(["server", "commands", "serverRestartCommand"])

		return not (system_shutdown_command and system_restart_command and server_restart_command)

	def _get_servercommands_wizard_details(self):
		return dict()

	def _get_servercommands_wizard_name(self):
		return gettext("Server Commands")

	#~~ Printer profile subwizard

	def _is_printerprofile_wizard_required(self):
		return self._printer_profile_manager.is_default_unmodified() and self._printer_profile_manager.profile_count == 1

	def _get_printerprofile_wizard_details(self):
		return dict()

	def _get_printerprofile_wizard_name(self):
		return gettext("Default Printer Profile")

	#~~ helpers

	def _get_subwizard_attrs(self, start, end, callback=None):
		result = dict()

		for item in dir(self):
			if not item.startswith(start) or not item.endswith(end):
				continue

			key = item[len(start):-len(end)]
			if not key:
				continue

			attr = getattr(self, item)
			if callable(callback):
				callback(key, attr)
			result[key] = attr

		return result


__plugin_name__ = "Core Wizard"
__plugin_author__ = "Gina Häußge"
__plugin_description__ = "Provides wizard dialogs for core components and functionality"
__plugin_disabling_discouraged__ = gettext("Without this plugin OctoPrint will no longer be able to perform "
                                           "setup steps that might be required after an update.")
__plugin_license__ = "AGPLv3"
__plugin_implementation__ = CoreWizardPlugin()
