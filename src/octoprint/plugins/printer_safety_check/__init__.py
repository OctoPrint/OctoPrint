# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

import octoprint.plugin

from octoprint.events import Events
from octoprint.access import USER_GROUP
from octoprint.access.permissions import Permissions
from octoprint.util import to_unicode

from .checks.firmware_unsafe import FirmwareUnsafeChecks

import flask
from flask_babel import gettext

import textwrap

TERMINAL_SAFETY_WARNING = """
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
{message}

Learn more at https://faq.octoprint.org/warning-{warning_type}
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

"""

SAFETY_CHECKS = {
	"firmware-unsafe": FirmwareUnsafeChecks.as_dict()
}

class PrinterSafetyCheckPlugin(octoprint.plugin.AssetPlugin,
                               octoprint.plugin.EventHandlerPlugin,
                               octoprint.plugin.SimpleApiPlugin,
                               octoprint.plugin.TemplatePlugin):

	# noinspection PyMissingConstructor
	def __init__(self):
		self._warnings = dict()
		self._scan_received = True

	##~~ TemplatePlugin API

	def get_template_configs(self):
		return [
			dict(type="sidebar",
			     name=gettext("Printer Safety Warning"),
			     data_bind="visible: printerState.isOperational() && loginState.isAdmin() && warnings().length > 0",
			     icon="exclamation-triangle",
			     styles_wrapper=["display: none"])
		]

	##~~ AssetPlugin API

	def get_assets(self):
		return dict(js=("js/printer_safety_check.js",),
		            clientjs=("clientjs/printer_safety_check.js",),
		            css=("css/printer_safety_check.css",),
		            less=("less/printer_safety_check.less",))

	##~~ EventHandlerPlugin API

	def on_event(self, event, payload):
		if event == Events.DISCONNECTED:
			self._reset_warnings()
			self._reset_state()
			self._reset_checks()

	##~~ SimpleApiPlugin API

	def on_api_get(self, request):
		if not Permissions.PLUGIN_PRINTER_SAFETY_CHECK_DISPLAY.can():
			return flask.make_response("Insufficient rights", 403)
		return flask.jsonify(self._warnings)

	##~~ GCODE received hook handler

	def on_gcode_received(self, comm_instance, line, *args, **kwargs):
		if self._scan_received:
			self._run_checks("received", to_unicode(line, errors="replace"))
		return line

	##~~ Firmware info hook handler

	def on_firmware_info_received(self, comm_instance, firmware_name, firmware_data):
		self._run_checks("m115",
		                 to_unicode(firmware_name, errors="replace"),
		                 dict((to_unicode(key, errors="replace"), to_unicode(value, errors="replace"))
		                      for key, value in firmware_data.items()))
		self._scan_received = False

	##~~ Firmware capability hook handler

	def on_firmware_cap_received(self, comm_instance, cap, enabled, all_caps):
		self._run_checks("cap",
		                 to_unicode(cap, errors="replace"),
		                 enabled)

	##~~ Additional permissions hook handler

	def get_additional_permissions(self):
		return [
			dict(key="DISPLAY",
			     name="Display printer safety warnings",
			     description=gettext("Allows to see printer safety warnings"),
			     roles=["display"],
			     default_groups=[USER_GROUP])
		]

	##~~ Helpers

	def _run_checks(self, check_type, *args, **kwargs):
		changes = False

		for warning_type, check_data in SAFETY_CHECKS.items():
			checks = check_data.get("checks")
			message = check_data.get("message")
			if not checks or not message:
				continue

			for check in checks:
				if not check.active:
					# skip non active checks
					continue

				method = getattr(check, check_type, None)
				if not callable(method):
					# skip uncallable checks
					continue

				# execute method
				try:
					method(*args, **kwargs)
				except Exception:
					self._logger.exception("There was an error running method {} on check {!r}".format(check_type, check))
					continue

				# check if now triggered
				if check.triggered:
					self._register_warning(warning_type, message)

					# noinspection PyUnresolvedReferences
					self._event_bus.fire(Events.PLUGIN_PRINTER_SAFETY_CHECK_WARNING, dict(check_name=check.name,
					                                                                      warning_type=warning_type))
					changes = True
					break

		if changes:
			self._ping_clients()

	def _register_warning(self, warning_type, message):
		self._log_to_terminal(TERMINAL_SAFETY_WARNING.format(message="\n".join(textwrap.wrap(message, 75)),
		                                                     warning_type=warning_type))
		self._warnings[warning_type] = message

	def _reset_warnings(self):
		self._warnings.clear()
		self._ping_clients()

	def _reset_state(self):
		self._scan_received = True

	def _reset_checks(self):
		for warning_type, check_data in SAFETY_CHECKS.items():
			checks = check_data.get("checks")
			if not checks:
				continue

			for check in checks:
				check.reset()

	def _log_to_terminal(self, message):
		if self._printer:
			lines = message.split("\n")
			self._printer.log_lines(*lines)

	def _ping_clients(self):
		self._plugin_manager.send_plugin_message(self._identifier, dict(type="update"))


def register_custom_events(*args, **kwargs):
	return ["warning",]


__plugin_name__ = "Printer Safety Check"
__plugin_author__ = "Gina Häußge"
__plugin_url__ = "http://docs.octoprint.org/en/master/bundledplugins/printer_safety_check.html"
__plugin_description__ = "Checks for unsafe printers/printer firmwares"
__plugin_disabling_discouraged__ = gettext("Without this plugin OctoPrint will no longer be able to "
                                           "check if the printer it is connected to has a known safety "
                                           "issue and inform you about that fact.")
__plugin_license__ = "AGPLv3"
__plugin_implementation__ = PrinterSafetyCheckPlugin()
__plugin_hooks__ = {
	"octoprint.comm.protocol.gcode.received": __plugin_implementation__.on_gcode_received,
	"octoprint.comm.protocol.firmware.info": __plugin_implementation__.on_firmware_info_received,
	"octoprint.comm.protocol.firmware.capabilities": __plugin_implementation__.on_firmware_cap_received,
	"octoprint.events.register_custom_events": register_custom_events,
	"octoprint.access.permissions": __plugin_implementation__.get_additional_permissions
}

