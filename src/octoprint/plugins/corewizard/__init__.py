# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


import octoprint.plugin


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
		for key, method in required.iteritems():
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
		return self._user_manager is not None and not self._user_manager.hasBeenCustomized()

	def _get_acl_wizard_details(self):
		return dict()

	def _get_acl_wizard_name(self):
		return "Access Control"

	@octoprint.plugin.BlueprintPlugin.route("/acl", methods=["POST"])
	def acl_wizard_api(self):
		from flask import request
		from octoprint.server.api import valid_boolean_trues, NO_CONTENT

		if "ac" in request.values and request.values["ac"] in valid_boolean_trues and \
						"user" in request.values.keys() and "pass1" in request.values.keys() and \
						"pass2" in request.values.keys() and request.values["pass1"] == request.values["pass2"]:
			# configure access control
			self._settings.global_set_boolean(["accessControl", "enabled"], True)
			octoprint.server.userManager.addUser(request.values["user"], request.values["pass1"], True, ["user", "admin"], overwrite=True)
		elif "ac" in request.values.keys() and not request.values["ac"] in valid_boolean_trues:
			# disable access control
			self._settings.global_set_boolean(["accessControl", "enabled"], False)

			octoprint.server.loginManager.anonymous_user = octoprint.users.DummyUser
			octoprint.server.principals.identity_loaders.appendleft(octoprint.users.dummy_identity_loader)

		self._settings.save()
		return NO_CONTENT

	#~~ Webcam subwizard

	def _is_webcam_wizard_required(self):
		webcam_snapshot_url = self._settings.global_get(["webcam", "snapshotUrl"])
		webcam_stream_url = self._settings.global_get(["webcam", "streamUrl"])
		ffmpeg_path = self._settings.global_get(["webcam", "ffmpeg"])

		return not (webcam_snapshot_url and webcam_stream_url and ffmpeg_path)

	def _get_webcam_wizard_details(self):
		return dict()

	def _get_webcam_wizard_name(self):
		return "Webcam & Timelapse"

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
__plugin_description__ = "Provides wizard dialogs for core components"
__plugin_implementation__ = CoreWizardPlugin()
