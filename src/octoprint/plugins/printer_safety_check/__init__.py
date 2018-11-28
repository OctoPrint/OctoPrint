# coding=utf-8
from __future__ import absolute_import, division, print_function

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

import octoprint.plugin

from octoprint.events import Events
from octoprint.server import user_permission
from octoprint.util.version import get_comparable_version

import flask
from flask_babel import gettext

import textwrap

TERMINAL_SAFETY_WARNING = """
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
{message}

Learn more at https://faq.octoprint.org/warning-{warning_type}
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

"""

# Anet A8
ANETA8_M115_TEST = lambda name, data: name and name.lower().startswith("anet_a8_")

# Anycubic MEGA
ANYCUBIC_AUTHOR1 = "| Author: (Jolly, xxxxxxxx.CO.)".lower()
ANYCUBIC_AUTHOR2 = "| Author: (**Jolly, xxxxxxxx.CO.**)".lower()
ANYCUBIC_RECEIVED_TEST = lambda line: line and (ANYCUBIC_AUTHOR1 in line.lower() or ANYCUBIC_AUTHOR2 in line.lower())

# Creality CR-10s
CR10S_AUTHOR = " | Author: (CR-10Slanguage)".lower()
CR10S_RECEIVED_TEST = lambda line: line and CR10S_AUTHOR in line.lower()

# Creality Ender 3
ENDER3_AUTHOR = " | Author: (Ender3)".lower()
ENDER3_RECEIVED_TEST = lambda line: line and ENDER3_AUTHOR in line.lower()

# iMe on Micro3D
IME_M115_TEST = lambda name, data: name and name.lower().startswith("ime")

# Malyan M200 aka Monoprice Select Mini
MALYANM200_M115_TEST = lambda name, data: name and name.lower().startswith("malyan") and data.get("MODEL") == "M200"

# Stock Micro3D
MICRO3D_M115_TEST = lambda name, data: name and name.lower().startswith("micro3d")

# Any Repetier versions < 0.92
REPETIER_BEFORE_092_M115_TEST = lambda name, data: name and name.lower().startswith("repetier") and extract_repetier_version(name) is not None and extract_repetier_version(name) < get_comparable_version("0.92")

# THERMAL_PROTECTION capability reported as disabled
THERMAL_PROTECTION_CAP_TEST = lambda cap, enabled: cap == "THERMAL_PROTECTION" and not enabled

SAFETY_CHECKS = {
	"firmware-unsafe": dict(m115=(ANETA8_M115_TEST, IME_M115_TEST, MALYANM200_M115_TEST, MICRO3D_M115_TEST,
	                              REPETIER_BEFORE_092_M115_TEST),
	                        received=(ANYCUBIC_RECEIVED_TEST, CR10S_RECEIVED_TEST, ENDER3_RECEIVED_TEST),
	                        cap=(THERMAL_PROTECTION_CAP_TEST,),
	                        message=gettext(u"Your printer's firmware is known to lack mandatory safety features (e.g. "
	                                        u"thermal runaway protection). This is a fire risk."))
}

def extract_repetier_version(name):
	"""
	Extracts the Repetier version number from the firmware name.

	Example: "Repetier_0.91" => 0.91
	"""
	version = None
	if "_" in name:
		_, version = name.split("_", 1)
		version = get_comparable_version(version, base=True)
	return version

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

	##~~ SimpleApiPlugin API

	def on_api_get(self, request):
		if not user_permission.can():
			return flask.make_response("Insufficient rights", 403)
		return flask.jsonify(self._warnings)

	##~~ GCODE received hook handler

	def on_gcode_received(self, comm_instance, line, *args, **kwargs):
		if self._scan_received:
			self._run_checks("received", line)
		return line

	##~~ Firmware info hook handler

	def on_firmware_info_received(self, comm_instance, firmware_name, firmware_data):
		self._run_checks("m115", firmware_name, firmware_data)
		self._scan_received = False

	##~~ Firmware capability hook handler

	def on_firmware_cap_received(self, comm_instance, cap, enabled, all_caps):
		self._run_checks("cap", cap, enabled)

	##~~ Helpers

	def _run_checks(self, check_type, *args, **kwargs):
		changes = False

		for warning_type, check_data in SAFETY_CHECKS.items():
			checks = check_data.get(check_type)
			message = check_data.get("message")
			if not checks or not message:
				continue

			if any(x(*args, **kwargs) for x in checks):
				self._register_warning(warning_type, message)
				changes = True

		if changes:
			self._ping_clients()

	def _register_warning(self, warning_type, message):
		self._log_to_terminal(TERMINAL_SAFETY_WARNING.format(message="\n".join(textwrap.wrap(message, 75)),
		                                                     warning_type=warning_type))
		self._warnings[warning_type] = message

	def _reset_warnings(self):
		self._warnings.clear()
		self._ping_clients()

	def _log_to_terminal(self, message):
		if self._printer:
			lines = message.split("\n")
			self._printer.log_lines(*lines)

	def _ping_clients(self):
		self._plugin_manager.send_plugin_message(self._identifier, dict(type="update"))

__plugin_name__ = "Printer Safety Check"
__plugin_author__ = "Gina Häußge"
__plugin_url__ = "http://docs.octoprint.org/en/master/bundledplugins/printer_safety_check.html"
__plugin_description__ = "Checks for unsafe printers/printer firmwares"
__plugin_disabling_discouraged__ = gettext("Without this plugin OctoPrint will no longer be able to "
                                           "check if the printer it is connected to has a known safety"
                                           "issue and inform you about that fact.")
__plugin_license__ = "AGPLv3"
__plugin_implementation__ = PrinterSafetyCheckPlugin()
__plugin_hooks__ = {
	"octoprint.comm.protocol.gcode.received": __plugin_implementation__.on_gcode_received,
	"octoprint.comm.protocol.firmware.info": __plugin_implementation__.on_firmware_info_received,
	"octoprint.comm.protocol.firmware.capabilities": __plugin_implementation__.on_firmware_cap_received
}

