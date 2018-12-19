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

class Check(object):
	name = None

	def __init__(self):
		self._active = True
		self._triggered = False

	def received(self, line):
		"""Called when receiving a new line from the printer"""
		pass

	def m115(self, name, data):
		"""Called when receiving the response to an M115 from the printer"""
		pass

	def cap(self, cap, enabled):
		"""Called when receiving a capability report line"""
		pass

	@property
	def active(self):
		"""Whether this check is still active"""
		return self._active

	@property
	def triggered(self):
		"""Whether the check has been triggered"""
		return self._triggered

class AuthorCheck(Check):
	authors = ()

	AUTHOR = "| Author: ".lower()

	def received(self, line):
		if not line:
			return

		lower_line = line.lower()
		if self.AUTHOR in lower_line:
			self._triggered = any(map(lambda x: x in lower_line, self.authors))
			self._active = False

class AnetA8Check(Check):
	"""
	Anet A8 stock firmware

	Identified through firmware name "ANET_A8_".
	"""
	name = "anet_a8"

	def m115(self, name, data):
		self._triggered = name and name.lower().startswith("anet_a8_")
		self._active = False

class AnycubicCheck(Check):
	"""
	Anycubic MEGA stock firmware

	Identified through "Author: (Jolly, xxxxxxxx.CO.)" or "| Author: (**Jolly, xxxxxxxx.CO.**)" in startup messages
	combined with "echo:Vx.y.z" in startup messages, with x.y.z < 1.1.2.
	"""
	name = "anycubic"

	AUTHOR = "| Author: "
	VERSION = "echo:V"

	CRITICAL_AUTHOR1 = "| Author: (Jolly, xxxxxxxx.CO.)".lower()
	CRITICAL_AUTHOR2 = "| Author: (**Jolly, xxxxxxxx.CO.**)".lower()

	FIXED_VERSION = get_comparable_version("1.1.2")

	def __init__(self):
		Check.__init__(self)
		self._author_matches = None
		self._version_matches = None

	def received(self, line):
		if not line:
			return

		lower_line = line.lower()
		if self.AUTHOR in lower_line:
			self._author_matches = self.CRITICAL_AUTHOR1 in lower_line or self.CRITICAL_AUTHOR2 in lower_line
		elif line.startswith(self.VERSION):
			self._version_matches = self._broken_version(line)
		else:
			return

		self._evaluate()

	def _broken_version(self, line):
		version_str = line[len(self.VERSION):]
		version = get_comparable_version(version_str, base=True)
		if version is not None and version <= self.FIXED_VERSION:
			return True
		else:
			return False

	def _evaluate(self):
		if self._author_matches is None or self._version_matches is None:
			return
		self._triggered = self._author_matches and self._version_matches
		self._active = False

class CrealityCR10sCheck(AuthorCheck):
	"""
	Creality CR10s

	Identified through " | Author: (CR-10Slanguage)" in startup messages.
	"""
	name = "creality_cr10s"
	authors = (" | Author: (CR-10Slanguage)".lower(),)

class CrealityEnder3Check(AuthorCheck):
	"""
	Creality Ender3

	Identified through " | Author: (Ender3)" in startup messages.
	"""
	name = "creality_ender3"
	authors = (" | Author: (Ender3)".lower(),)

class MalyanM200Check(Check):
	"""
	Malyan M200 stock firmware prior to version 4.0

	Identified through firmware name "Malyan*", model "M200" and version < 4.0.
	"""
	name = "malyan_m200"

	FIXED_VERSION = get_comparable_version("4.0")

	def m115(self, name, data):
		self._triggered = name and name.lower().startswith("malyan") and data.get("MODEL") == "M200" and get_comparable_version(data.get("VER", "0")) < self.FIXED_VERSION
		self._active = False

class Micro3DIMECheck(Check):
	"""
	Micro3D with IME firmware

	Identified through firmware name "iME*".
	"""
	name = "micro3d_ime"

	def m115(self, name, data):
		self._triggered = name and name.lower().startswith("ime")
		self._active = False

class Micro3DStockCheck(Check):
	"""
	Micro3D with IME firmware

	Identified through firmware name "Micro3D*".
	"""
	name = "micro3d"

	def m115(self, name, data):
		self._triggered = name and name.lower().startswith("micro3d")
		self._active = False

class RepetierBefore092Check(Check):
	"""
	Repetier firmware prior to version 0.92

	Identified through firmware name "Repetier_x.y.z" with x.y.z < 0.92
	"""
	name = "repetier_before_092"

	FIXED_VERSION = get_comparable_version("0.92")

	def m115(self, name, data):
		if name and name.lower().startswith("repetier"):
			version = self._extract_repetier_version(name)
			self._triggered = version is not None and version < self.FIXED_VERSION
		self._active = False

	def _extract_repetier_version(self, name):
		"""
		Extracts the Repetier version number from the firmware name.

		Example: "Repetier_0.91" => 0.91
		"""
		version = None
		if "_" in name:
			_, version = name.split("_", 1)
			version = get_comparable_version(version, base=True)
		return version

class ThermalProtectionCapCheck(Check):
	"""
	Firmware reporting disabled THERMAL_PROTECTION capability
	"""
	name = "capability"

	def cap(self, cap, enabled):
		if cap == "THERMAL_PROTECTION":
			self._triggered = not enabled

SAFETY_CHECKS = {
	"firmware-unsafe": dict(checks=(AnetA8Check(), AnycubicCheck(), CrealityCR10sCheck(), CrealityEnder3Check(),
	                                MalyanM200Check(), Micro3DIMECheck(), Micro3DStockCheck(), RepetierBefore092Check(),
	                                ThermalProtectionCapCheck()),
	                        message=gettext(u"Your printer's firmware is known to lack mandatory safety features (e.g. "
	                                        u"thermal runaway protection). This is a fire risk."))
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
				except:
					self._logger.exception("There was an error running method {} on check {!r}".format(check_type, check))
					continue

				# check if now triggered
				if check.triggered:
					self._register_warning(warning_type, message)
					self._event_bus.fire("plugin_printer_safety_check_warning", dict(check_name=check.name,
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

