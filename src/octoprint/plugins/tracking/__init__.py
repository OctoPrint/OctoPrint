# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

import octoprint.plugin

from flask.ext.babel import gettext

import requests
import hashlib
import logging

# noinspection PyCompatibility
import concurrent.futures

from octoprint.util import RepeatedTimer
from octoprint.util.version import get_octoprint_version_string
from octoprint.events import Events

TRACKING_URL = "https://tracking.octoprint.org/track/{id}/{event}/?{args}"

# noinspection PyMissingConstructor
class TrackingPlugin(octoprint.plugin.SettingsPlugin,
                     octoprint.plugin.EnvironmentDetectionPlugin,
                     octoprint.plugin.StartupPlugin,
                     octoprint.plugin.TemplatePlugin,
                     octoprint.plugin.AssetPlugin,
                     octoprint.plugin.WizardPlugin,
                     octoprint.plugin.EventHandlerPlugin):

	def __init__(self):
		self._environment = None
		self._url = None
		self._ping_worker = None
		self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

	def initialize(self):
		self._init_tracking()

	##~~ SettingsPlugin

	def get_settings_defaults(self):
		return dict(enabled=None,
		            unique_id=None,
		            server=TRACKING_URL,
		            ping=15*60)

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
		self._track_startup()

		ping = self._settings.get_int(["ping"])
		if ping:
			self._ping_worker = RepeatedTimer(ping, self._track_ping)
			self._ping_worker.start()

	##~~ EventHandlerPlugin

	def on_event(self, event, payload):
		if event.startswith("plugin_pluginmanager_"):
			self._track_plugin_event(event, payload)
		elif event in (Events.PRINT_STARTED, Events.PRINT_DONE, Events.PRINT_FAILED, Events.PRINT_CANCELLED):
			self._track_printjob_event(event, payload)

	##~~ TemplatePlugin

	def get_template_configs(self):
		return [
			dict(type="settings", name=gettext("Anonymous Usage Tracking"), template="tracking_settings.jinja2", custom_bindings=False),
			dict(type="wizard", name=gettext("Anonymous Usage Tracking"), template="tracking_wizard.jinja2", custom_bindings=True, mandatory=True)
		]

	##~~ AssetPlugin

	def get_assets(self):
		return dict(js=["js/tracking.js"])

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

	def _track_startup(self):
		self._track("startup",
		            version=get_octoprint_version_string(),
		            os=self._environment[b"os"][b"id"])

	def _track_ping(self):
		self._track("ping")

	def _track_plugin_event(self, event, payload):
		if event.endswith("_installplugin"):
			self._track("install_plugin", plugin=payload.get(b"id"), plugin_version=payload.get(b"version"))
		elif event.endswith("_uninstallplugin"):
			self._track("uninstall_plugin", plugin=payload.get(b"id"), plugin_version=payload.get(b"version"))
		elif event.endswith("_enableplugin"):
			self._track("enable_plugin", plugin=payload.get(b"id"), plugin_version=payload.get(b"version"))
		elif event.endswith("_disableplugin"):
			self._track("disable_plugin", plugin=payload.get(b"id"), plugin_version=payload.get(b"version"))

	def _track_printjob_event(self, event, payload):
		sha = hashlib.sha1()
		sha.update(payload.get("name"))

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
			track_event = "print_failed"
		elif event == Events.PRINT_CANCELLED:
			track_event = "print_cancelled"

		if track_event is not None:
			self._track(track_event, **args)

	def _track(self, event, **kwargs):
		if not self._settings.get_boolean([b"enabled"]):
			return

		self._executor.submit(self._do_track, event, **kwargs)

	def _do_track(self, event, **kwargs):
		server = self._settings.get([b"server"])
		url = server.format(id=self._settings.get([b"unique_id"]),
		                    event=event,
		                    args="&".join(map(lambda x: "{}={}".format(x[0], x[1]), kwargs.items())))

		headers = {"User-Agent": "OctoPrint/{}".format(get_octoprint_version_string())}
		try:
			requests.get(url,
			             timeout=3.1,
			             headers=headers)
			self._logger.debug("Sent tracking event to {}".format(url))
		except:
			if self._logger.isEnabledFor(logging.DEBUG):
				self._logger.exception("Error while sending event to anonymous usage tracking".format(url))
			else:
				pass

__plugin_name__ = "Anonymous Usage Tracking"
__plugin_description__ = "Anonymous version and usage tracking, see homepage for details on what gets tracked"
__plugin_homepage__ = "https://tracking.octoprint.org"
__plugin_author__ = "Gina Häußge"

__plugin_implementation__ = TrackingPlugin()
