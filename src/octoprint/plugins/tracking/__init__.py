# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

import octoprint.plugin

from flask_babel import gettext

import requests
import hashlib
import logging

try:
	# noinspection PyCompatibility
	from urllib.parse import urlencode
except ImportError:
	from urllib import urlencode

# noinspection PyCompatibility
import concurrent.futures

from octoprint.util import RepeatedTimer, monotonic_time
from octoprint.util.version import get_octoprint_version_string
from octoprint.events import Events

TRACKING_URL = "https://tracking.octoprint.org/track/{id}/{event}/"

# noinspection PyMissingConstructor
class TrackingPlugin(octoprint.plugin.SettingsPlugin,
                     octoprint.plugin.EnvironmentDetectionPlugin,
                     octoprint.plugin.StartupPlugin,
                     octoprint.plugin.ShutdownPlugin,
                     octoprint.plugin.TemplatePlugin,
                     octoprint.plugin.AssetPlugin,
                     octoprint.plugin.WizardPlugin,
                     octoprint.plugin.EventHandlerPlugin):

	def __init__(self):
		self._environment = None
		self._throttle_state = None
		self._helpers_get_throttle_state = None
		self._printer_connection_parameters = None
		self._url = None
		self._ping_worker = None
		self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

		self._record_next_firmware_info = False

		self._startup_time = monotonic_time()

	def initialize(self):
		self._init_id()

	##~~ SettingsPlugin

	def get_settings_defaults(self):
		return dict(enabled=None,
		            unique_id=None,
		            server=TRACKING_URL,
		            ping=15*60,
		            events=dict(startup=True,
		                        printjob=True,
		                        commerror=True,
		                        plugin=True,
		                        update=True,
		                        printer=True,
		                        printer_safety_check=True,
		                        throttled=True))

	def get_settings_restricted_paths(self):
		return dict(admin=[["enabled"], ["unique_id"], ["events"]],
		            never=[["server"], ["ping"]])

	def on_settings_save(self, data):
		enabled = self._settings.get(["enabled"])

		octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

		if enabled is None and self._settings.get(["enabled"]):
			# tracking was just enabled, let's start up tracking
			self._start_tracking()

	##~~ EnvironmentDetectionPlugin

	def on_environment_detected(self, environment, *args, **kwargs):
		self._environment = environment

	##~~ StartupPlugin

	def on_after_startup(self):
		self._start_tracking()

	##~~ ShutdownPlugin

	def on_shutdown(self):
		if not self._settings.get_boolean(["enabled"]):
			return
		self._track_shutdown()

	##~~ EventHandlerPlugin

	# noinspection PyUnresolvedReferences
	def on_event(self, event, payload):
		if not self._settings.get_boolean(["enabled"]):
			return

		if event in (Events.PRINT_STARTED, Events.PRINT_DONE, Events.PRINT_FAILED, Events.PRINT_CANCELLED):
			self._track_printjob_event(event, payload)

		elif event in (Events.ERROR,):
			self._track_commerror_event(event, payload)

		elif event in (Events.CONNECTED,):
			self._printer_connection_parameters = dict(port=payload["port"],
			                                           baudrate=payload["baudrate"])
			self._record_next_firmware_info = True

		elif event in (Events.FIRMWARE_DATA,) and self._record_next_firmware_info:
			self._record_next_firmware_info = False
			self._track_printer_event(event, payload)

		elif hasattr(Events, "PLUGIN_PLUGINMANAGER_INSTALL_PLUGIN") and \
			event in (Events.PLUGIN_PLUGINMANAGER_INSTALL_PLUGIN, Events.PLUGIN_PLUGINMANAGER_UNINSTALL_PLUGIN,
			          Events.PLUGIN_PLUGINMANAGER_ENABLE_PLUGIN, Events.PLUGIN_PLUGINMANAGER_DISABLE_PLUGIN):
			self._track_plugin_event(event, payload)

		elif hasattr(Events, "PLUGIN_SOFTWAREUPDATE_UPDATE_SUCCEEDED") and \
			event in (Events.PLUGIN_SOFTWAREUPDATE_UPDATE_SUCCEEDED, Events.PLUGIN_SOFTWAREUPDATE_UPDATE_FAILED):
			self._track_update_event(event, payload)

		elif hasattr(Events, "PLUGIN_PI_SUPPORT_THROTTLE_STATE") and event in (Events.PLUGIN_PI_SUPPORT_THROTTLE_STATE,):
			self._throttle_state = payload
			self._track_throttle_event(event, payload)

		elif hasattr(Events, "PLUGIN_PRINTER_SAFETY_CHECK_WARNING") and event in (Events.PLUGIN_PRINTER_SAFETY_CHECK_WARNING,):
			self._track_printer_safety_event(event, payload)

	##~~ TemplatePlugin

	def get_template_configs(self):
		return [
			dict(type="settings", name=gettext("Anonymous Usage Tracking"), template="tracking_settings.jinja2", custom_bindings=False),
			dict(type="wizard", name=gettext("Anonymous Usage Tracking"), template="tracking_wizard.jinja2", custom_bindings=True, mandatory=True)
		]

	##~~ AssetPlugin

	def get_assets(self):
		return dict(js=["js/usage.js"])

	##~~ WizardPlugin

	def is_wizard_required(self):
		return self._settings.get(["enabled"]) is None

	##~~ helpers

	def _init_id(self):
		if not self._settings.get(["unique_id"]):
			import uuid
			self._settings.set(["unique_id"], str(uuid.uuid4()))
			self._settings.save()

	def _start_tracking(self):
		if not self._settings.get_boolean(["enabled"]):
			return

		if self._ping_worker is None:
			ping = self._settings.get_int(["ping"])
			if ping:
				self._ping_worker = RepeatedTimer(ping, self._track_ping, run_first=True)
				self._ping_worker.start()

		if self._helpers_get_throttle_state is None:
			# cautiously look for the get_throttled helper from pi_support
			pi_helper = self._plugin_manager.get_helpers("pi_support", "get_throttled")
			if pi_helper and 'get_throttled' in pi_helper:
				self._helpers_get_throttle_state = pi_helper['get_throttled']

		# now that we have everything set up, phone home.
		self._track_startup()

	def _track_ping(self):
		if not self._settings.get_boolean(["enabled"]):
			return

		uptime = int(monotonic_time() - self._startup_time)
		self._track("ping", octoprint_uptime=uptime)

	def _track_startup(self):
		if not self._settings.get_boolean(["events", "startup"]):
			return

		payload = dict(version=get_octoprint_version_string(),
		               os=self._environment["os"]["id"],
		               python=self._environment["python"]["version"],
		               pip=self._environment["python"]["pip"],
		               cores=self._environment["hardware"]["cores"],
		               freq=self._environment["hardware"]["freq"],
		               ram=self._environment["hardware"]["ram"])

		if "plugins" in self._environment and "pi_support" in self._environment["plugins"]:
			payload["pi_model"] = self._environment["plugins"]["pi_support"]["model"]

			if "octopi_version" in self._environment["plugins"]["pi_support"]:
				payload["octopi_version"] = self._environment["plugins"]["pi_support"]["octopi_version"]

		self._track("startup", **payload)

	def _track_shutdown(self):
		if not self._settings.get_boolean(["enabled"]):
			return

		if not self._settings.get_boolean(["events", "startup"]):
			return

		self._track("shutdown")

	def _track_plugin_event(self, event, payload):
		if not self._settings.get_boolean(["events", "plugin"]):
			return

		if event.endswith("_install_plugin"):
			self._track("install_plugin", plugin=payload.get("id"), plugin_version=payload.get("version"))
		elif event.endswith("_uninstall_plugin"):
			self._track("uninstall_plugin", plugin=payload.get("id"), plugin_version=payload.get("version"))
		elif event.endswith("_enable_plugin"):
			self._track("enable_plugin", plugin=payload.get("id"), plugin_version=payload.get("version"))
		elif event.endswith("_disable_plugin"):
			self._track("disable_plugin", plugin=payload.get("id"), plugin_version=payload.get("version"))

	def _track_update_event(self, event, payload):
		if not self._settings.get_boolean(["events", "update"]):
			return

		if event.endswith("_update_succeeded"):
			self._track("update_successful", target=payload.get("target"), from_version=payload.get("from_version"), to_version=payload.get("to_version"))
		elif event.endswith("_update_failed"):
			self._track("update_failed", target=payload.get("target"), from_version=payload.get("from_version"), to_version=payload.get("to_version"))

	def _track_throttle_event(self, event, payload):
		if not self._settings.get_boolean(["events", "throttled"]):
			return

		args = dict(throttled_now=payload["current_issue"],
		            throttled_past=payload["past_issue"],
		            throttled_mask=payload["raw_value"],
		            throttled_voltage_now=payload["current_undervoltage"],
		            throttled_voltage_past=payload["past_undervoltage"],
		            throttled_overheat_now=payload["current_overheat"],
		            throttled_overheat_past=payload["past_overheat"])

		if payload["current_issue"]:
			track_event = "system_throttled"
		else:
			track_event = "system_unthrottled"

		if track_event is not None:
			self._track(track_event, **args)

	def _track_commerror_event(self, event, payload):
		if not self._settings.get_boolean(["events", "commerror"]):
			return

		if not "reason" in payload or not "error" in payload:
			return

		track_event = "commerror_{}".format(payload["reason"])
		args = dict(commerror_text=payload["error"])

		if callable(self._helpers_get_throttle_state):
			try:
				throttle_state = self._helpers_get_throttle_state(run_now=True)
				if throttle_state and (throttle_state.get("current_issue", False) or throttle_state.get("past_issue", False)):
					args["throttled_now"] = throttle_state["current_issue"]
					args["throttled_past"] = throttle_state["past_issue"]
					args["throttled_mask"] = throttle_state["raw_value"]
			except Exception:
				# ignored
				pass

		self._track(track_event, **args)

	def _track_printjob_event(self, event, payload):
		if not self._settings.get_boolean(["events", "printjob"]):
			return

		unique_id = self._settings.get(["unique_id"])
		if not unique_id:
			return

		sha = hashlib.sha1()
		sha.update(payload.get("path").encode("utf-8"))
		sha.update(unique_id.encode("utf-8"))

		track_event = None
		args = dict(origin=payload.get("origin"), file=sha.hexdigest())

		if event == Events.PRINT_STARTED:
			track_event = "print_started"
		elif event == Events.PRINT_DONE:
			try:
				elapsed = int(payload.get("time", 0))
				if elapsed:
					args["elapsed"] = elapsed
			except ValueError:
				pass
			track_event = "print_done"
		elif event == Events.PRINT_FAILED:
			try:
				elapsed = int(payload.get("time", 0))
				if elapsed:
					args["elapsed"] = elapsed
			except ValueError:
				pass
			args["reason"] = payload.get("reason", "unknown")

			if "error" in payload and self._settings.get_boolean(["events", "commerror"]):
				args["commerror_text"] = payload["error"]

			track_event = "print_failed"
		elif event == Events.PRINT_CANCELLED:
			try:
				elapsed = int(payload.get("time", 0))
				if elapsed:
					args["elapsed"] = elapsed
			except ValueError:
				pass
			track_event = "print_cancelled"

		if callable(self._helpers_get_throttle_state):
			try:
				throttle_state = self._helpers_get_throttle_state(run_now=True)
				if throttle_state and (throttle_state.get("current_issue", False) or throttle_state.get("past_issue", False)):
					args["throttled_now"] = throttle_state["current_issue"]
					args["throttled_past"] = throttle_state["past_issue"]
					args["throttled_mask"] = throttle_state["raw_value"]
			except Exception:
				# ignored
				pass

		if track_event is not None:
			self._track(track_event, **args)

	def _track_printer_event(self, event, payload):
		if not self._settings.get_boolean(["events", "printer"]):
			return

		if event in (Events.FIRMWARE_DATA,):
			args = dict(firmware_name=payload["name"])
			if self._printer_connection_parameters:
				args["printer_port"] = self._printer_connection_parameters["port"]
				args["printer_baudrate"] = self._printer_connection_parameters["baudrate"]
			self._track("printer_connected", **args)

	def _track_printer_safety_event(self, event, payload):
		if not self._settings.get_boolean(["events", "printer_safety_check"]):
			return

		self._track("printer_safety_warning",
		            printer_safety_warning_type=payload.get("warning_type", "unknown"),
		            printer_safety_check_name=payload.get("check_name", "unknown"))

	def _track(self, event, **kwargs):
		if not self._settings.get_boolean(["enabled"]):
			return

		self._executor.submit(self._do_track, event, **kwargs)

	def _do_track(self, event, **kwargs):
		if not self._connectivity_checker.online:
			return

		if not self._settings.get_boolean(["enabled"]):
			return

		unique_id = self._settings.get(["unique_id"])
		if not unique_id:
			return

		server = self._settings.get(["server"])
		url = server.format(id=unique_id, event=event)
		# Don't print the URL or UUID! That would expose the UUID in forums/tickets
		# if pasted. It's okay for the user to know their uuid, but it shouldn't be shared.

		headers = {"User-Agent": "OctoPrint/{}".format(get_octoprint_version_string())}
		try:
			params = urlencode(kwargs, doseq=True).replace("+", "%20")

			requests.get(url,
			             params=params,
			             timeout=3.1,
			             headers=headers)
			self._logger.info("Sent tracking event {}, payload: {!r}".format(event, kwargs))
		except Exception:
			if self._logger.isEnabledFor(logging.DEBUG):
				self._logger.exception("Error while sending event to anonymous usage tracking".format(url))
			else:
				pass

__plugin_name__ = "Anonymous Usage Tracking"
__plugin_description__ = "Anonymous version and usage tracking, see homepage for details on what gets tracked"
__plugin_url__ = "https://tracking.octoprint.org"
__plugin_author__ = "Gina Häußge"

__plugin_implementation__ = TrackingPlugin()
