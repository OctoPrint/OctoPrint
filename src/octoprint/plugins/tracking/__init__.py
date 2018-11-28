# coding=utf-8
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

from octoprint.util import RepeatedTimer
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

	def initialize(self):
		self._init_tracking()

	##~~ SettingsPlugin

	def get_settings_defaults(self):
		return dict(enabled=None,
		            unique_id=None,
		            server=TRACKING_URL,
		            ping=15*60,
		            events=dict(startup=True,
		                        printjob=True,
		                        plugin=True,
		                        update=True,
		                        printer=True,
		                        throttled=True))

	def get_settings_restricted_paths(self):
		return dict(admin=[["enabled"], ["unique_id"], ["events"]],
		            never=[["server"], ["ping"]])

	def on_settings_save(self, data):
		enabled = self._settings.get([b"enabled"])

		octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

		if enabled is None and self._settings.get([b"enabled"]):
			# tracking was just enabled, let's init it and send a startup event
			self._init_tracking()
			self._track_startup()

	##~~ EnvironmentDetectionPlugin

	def on_environment_detected(self, environment, *args, **kwargs):
		self._environment = environment

	##~~ StartupPlugin

	def on_after_startup(self):
		ping = self._settings.get_int(["ping"])
		if ping:
			self._ping_worker = RepeatedTimer(ping, self._track_ping)
			self._ping_worker.start()

		# cautiously look for the get_throttled helper from pi_support
		pi_helper = self._plugin_manager.get_helpers("pi_support", "get_throttled")
		if pi_helper and 'get_throttled' in pi_helper:
			self._helpers_get_throttle_state = pi_helper['get_throttled']

		# now that we have everything set up, phone home.
		self._track_startup()

	##~~ ShutdownPlugin

	def on_shutdown(self):
		self._track_shutdown()

	##~~ EventHandlerPlugin

	def on_event(self, event, payload):
		if event.startswith("plugin_pluginmanager_"):
			self._track_plugin_event(event, payload)
		elif event.startswith("plugin_softwareupdate_"):
			self._track_update_event(event, payload)
		elif event in ("plugin_pi_support_throttle_state",):
			self._throttle_state = payload
			self._track_throttle_event(event, payload)
		elif event in (Events.PRINT_STARTED, Events.PRINT_DONE, Events.PRINT_FAILED, Events.PRINT_CANCELLED):
			self._track_printjob_event(event, payload)
		elif event in (Events.CONNECTED,):
			self._printer_connection_parameters = dict(port=payload["port"],
			                                           baudrate=payload["baudrate"])
			self._record_next_firmware_info = True
		elif event in (Events.FIRMWARE_DATA,) and self._record_next_firmware_info:
			self._record_next_firmware_info = False
			self._track_printer_event(event, payload)

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
		return self._settings.get([b"enabled"]) is None

	##~~ helpers

	def _init_tracking(self):
		if not self._settings.get_boolean([b"enabled"]):
			return
		self._init_id()
		self._logger.info("Initialized anonymous tracking")

	def _init_id(self):
		if self._settings.get_boolean([b"enabled"]) and not self._settings.get([b"unique_id"]):
			import uuid
			self._settings.set([b"unique_id"], str(uuid.uuid4()))
			self._settings.save()

	def _track_ping(self):
		self._track("ping")

	def _track_startup(self):
		if not self._settings.get_boolean(["events", "startup"]):
			return

		payload = dict(version=get_octoprint_version_string(),
		               os=self._environment[b"os"][b"id"],
		               python=self._environment[b"python"][b"version"],
		               pip=self._environment[b"python"][b"pip"],
		               cores=self._environment[b"hardware"][b"cores"],
		               freq=self._environment[b"hardware"][b"freq"],
		               ram=self._environment[b"hardware"][b"ram"])

		if b"plugins" in self._environment and b"pi_support" in self._environment[b"plugins"]:
			payload[b"pi_model"] = self._environment[b"plugins"][b"pi_support"][b"model"]

			if b"octopi_version" in self._environment[b"plugins"][b"pi_support"]:
				payload[b"octopi_version"] = self._environment[b"plugins"][b"pi_support"][b"octopi_version"]

		self._track("startup", **payload)

	def _track_shutdown(self):
		if not self._settings.get_boolean(["events", "startup"]):
			return

		self._track("shutdown")

	def _track_plugin_event(self, event, payload):
		if not self._settings.get_boolean(["events", "plugin"]):
			return

		if event.endswith("_installplugin"):
			self._track("install_plugin", plugin=payload.get(b"id"), plugin_version=payload.get(b"version"))
		elif event.endswith("_uninstallplugin"):
			self._track("uninstall_plugin", plugin=payload.get(b"id"), plugin_version=payload.get(b"version"))
		elif event.endswith("_enableplugin"):
			self._track("enable_plugin", plugin=payload.get(b"id"), plugin_version=payload.get(b"version"))
		elif event.endswith("_disableplugin"):
			self._track("disable_plugin", plugin=payload.get(b"id"), plugin_version=payload.get(b"version"))

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

		args = dict(throttled_now=payload[b"current_issue"],
		            throttled_past=payload[b"past_issue"],
		            throttled_mask=payload[b"raw_value"],
		            throttled_voltage_now=payload[b"current_undervoltage"],
		            throttled_voltage_past=payload[b"past_undervoltage"],
		            throttled_overheat_now=payload[b"current_overheat"],
		            throttled_overheat_past=payload[b"past_overheat"])

		if payload[b"current_issue"]:
			track_event = "system_throttled"
		else:
			track_event = "system_unthrottled"

		if track_event is not None:
			self._track(track_event, **args)

	def _track_printjob_event(self, event, payload):
		if not self._settings.get_boolean(["events", "printjob"]):
			return

		sha = hashlib.sha1()
		sha.update(payload.get("path"))
		sha.update(self._settings.get([b"unique_id"]))

		track_event = None
		args = dict(origin=payload.get(b"origin"), file=sha.hexdigest())

		if event == Events.PRINT_STARTED:
			track_event = "print_started"
		elif event == Events.PRINT_DONE:
			try:
				elapsed = int(payload.get(b"time"))
			except ValueError:
				elapsed = "unknown"
			args[b"elapsed"] = elapsed
			track_event = "print_done"
		elif event == Events.PRINT_FAILED:
			try:
				elapsed = int(payload.get(b"time"))
			except ValueError:
				elapsed = "unknown"
			args[b"elapsed"] = elapsed
			args[b"reason"] = payload.get(b"reason", "unknown")
			track_event = "print_failed"
		elif event == Events.PRINT_CANCELLED:
			track_event = "print_cancelled"

		if callable(self._helpers_get_throttle_state):
			try:
				throttle_state = self._helpers_get_throttle_state(run_now=True)
				if throttle_state and (throttle_state.get(b"current_issue", False) or throttle_state.get(b"past_issue", False)):
					args[b"throttled_now"] = throttle_state[b"current_issue"]
					args[b"throttled_past"] = throttle_state[b"past_issue"]
					args[b"throttled_mask"] = throttle_state[b"raw_value"]
			except:
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

	def _track(self, event, **kwargs):
		if not self._settings.get_boolean([b"enabled"]):
			return

		self._executor.submit(self._do_track, event, **kwargs)

	def _do_track(self, event, **kwargs):
		if not self._connectivity_checker.online:
			return

		server = self._settings.get([b"server"])
		url = server.format(id=self._settings.get([b"unique_id"]), event=event)
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
		except:
			if self._logger.isEnabledFor(logging.DEBUG):
				self._logger.exception("Error while sending event to anonymous usage tracking".format(url))
			else:
				pass

__plugin_name__ = "Anonymous Usage Tracking"
__plugin_description__ = "Anonymous version and usage tracking, see homepage for details on what gets tracked"
__plugin_url__ = "https://tracking.octoprint.org"
__plugin_author__ = "Gina Häußge"

__plugin_implementation__ = TrackingPlugin()
