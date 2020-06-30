# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2020 The OctoPrint Project - Released under terms of the AGPLv3 License"

import octoprint.plugin

from octoprint.access import USER_GROUP
from octoprint.access.permissions import Permissions
from octoprint.events import Events

import flask
from flask_babel import gettext

import time

class ActionCommandNotificationPlugin(octoprint.plugin.AssetPlugin,
                                      octoprint.plugin.SettingsPlugin,
                                      octoprint.plugin.SimpleApiPlugin,
                                      octoprint.plugin.TemplatePlugin,
                                      octoprint.plugin.EventHandlerPlugin):

	def __init__(self):
		self._notifications = []

	# Additional permissions hook

	def get_additional_permissions(self):
		return [
			dict(key="SHOW",
			     name="Show printer notifications",
			     description=gettext("Allows to see printer notifications"),
			     default_groups=[USER_GROUP],
			     roles=["show"]),
			dict(key="CLEAR",
			     name="Clear printer notifications",
			     description=gettext("Allows to clear printer notifications"),
			     default_groups=[USER_GROUP],
			     roles=["clear"])
		]

	#~ AssetPlugin

	def get_assets(self):
		return dict(js=["js/action_command_notification.js"],
		            clientjs=["clientjs/action_command_notification.js"],
		            css=["css/action_command_notification.css"])

	#~ EventHandlerPlugin

	def on_event(self, event, payload):
		if event == Events.DISCONNECTED:
			self._clear_notifications()

	#~ SettingsPlugin

	def get_settings_defaults(self):
		return dict(enable=True,
		            enable_popups=False)

	#~ SimpleApiPlugin

	def on_api_get(self, request):
		if not Permissions.PLUGIN_ACTION_COMMAND_NOTIFICATION_SHOW.can():
			return flask.abort(403, "Insufficient permissions")
		return flask.jsonify(notifications=[dict(timestamp=notification[0],
		                                         message=notification[1]) for notification in self._notifications])

	def get_api_commands(self):
		return dict(clear=[])

	def on_api_command(self, command, data):
		if command == "clear":
			if not Permissions.PLUGIN_ACTION_COMMAND_NOTIFICATION_CLEAR.can():
				return flask.abort(403, "Insufficient permissions")
			self._clear_notifications()

	#~ TemplatePlugin

	def get_template_configs(self):
		return [
			dict(type="settings",
			     name=gettext("Printer Notifications"),
			     custom_bindings=False),
			dict(type="sidebar",
			     name=gettext("Printer Notifications"),
			     icon="bell-o",
			     styles_wrapper=["display: none"],
			     data_bind="visible: loginState.hasPermissionKo(access.permissions.PLUGIN_ACTION_COMMAND_NOTIFICATION_SHOW)"
			               " && settings.settings.plugins.action_command_notification.enable()")
		]

	#~ action command handler

	def action_command_handler(self, comm, line, action, *args, **kwargs):
		if not self._settings.get_boolean(["enable"]):
			return

		parts = action.split(None, 1)
		if len(parts) == 1:
			action = parts[0]
			parameter = ""
		else:
			action, parameter = parts

		if action != "notification":
			return

		message = parameter.strip()
		self._notifications.append((time.time(), message))
		self._plugin_manager.send_plugin_message(self._identifier, dict(message=message))

		self._logger.info("Got a notification: {}".format(message))

	def _clear_notifications(self):
		self._notifications = []
		self._plugin_manager.send_plugin_message(self._identifier, dict())
		self._logger.info("Notifications cleared")

__plugin_name__ = "Action Command Notification Support"
__plugin_description__ = "Allows your printer to trigger notifications via action commands on the connection"
__plugin_author__ = "Gina Häußge"
__plugin_disabling_discouraged__ = gettext("Without this plugin your printer will no longer be able to trigger"
                                           " notifications in OctoPrint")
__plugin_license__ = "AGPLv3"
__plugin_pythoncompat__ = ">=2.7,<4"
__plugin_implementation__ = ActionCommandNotificationPlugin()
__plugin_hooks__ = {
	"octoprint.comm.protocol.action": __plugin_implementation__.action_command_handler,
	"octoprint.access.permissions": __plugin_implementation__.get_additional_permissions
}
