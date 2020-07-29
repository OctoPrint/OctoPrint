# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging
import threading
import octoprint.vendor.sockjs.tornado
import octoprint.vendor.sockjs.tornado.session
import octoprint.vendor.sockjs.tornado.proto
import octoprint.vendor.sockjs.tornado.util
import time

import octoprint.timelapse
import octoprint.server
import octoprint.events
import octoprint.plugin
import octoprint.access.users

from octoprint.events import Events
from octoprint.settings import settings
from octoprint.access.permissions import Permissions
from octoprint.access.users import LoginStatusListener
from octoprint.access.groups import GroupChangeListener
from octoprint.util.json import JsonEncoding

import octoprint.printer

import wrapt
import json


class ThreadSafeSession(octoprint.vendor.sockjs.tornado.session.Session):
	def __init__(self, conn, server, session_id, expiry=None):
		octoprint.vendor.sockjs.tornado.session.Session.__init__(self, conn, server, session_id, expiry=expiry)

	def set_handler(self, handler, start_heartbeat=True):
		if getattr(handler, "__orig_send_pack", None) is None:
			orig_send_pack = handler.send_pack
			mutex = threading.RLock()

			def send_pack(*args, **kwargs):
				with mutex:
					return orig_send_pack(*args, **kwargs)

			handler.send_pack = send_pack
			setattr(handler, "__orig_send_pack", orig_send_pack)

		return octoprint.vendor.sockjs.tornado.session.Session.set_handler(self, handler, start_heartbeat=start_heartbeat)

	def remove_handler(self, handler):
		result = octoprint.vendor.sockjs.tornado.session.Session.remove_handler(self, handler)

		if getattr(handler, "__orig_send_pack", None) is not None:
			handler.send_pack = getattr(handler, "__orig_send_pack")
			delattr(handler, "__orig_send_pack")

		return result


class JsonEncodingSessionWrapper(wrapt.ObjectProxy):
	def send_message(self, msg, stats=True, binary=False):
		self.send_jsonified(json.dumps(octoprint.vendor.sockjs.tornado.util.bytes_to_str(msg),
		                               separators=(',', ':'),
		                               default=JsonEncoding.encode),
		                    stats)


class PrinterStateConnection(octoprint.vendor.sockjs.tornado.SockJSConnection,
                             octoprint.printer.PrinterCallback,
                             LoginStatusListener,
                             GroupChangeListener):

	_event_permissions = {Events.USER_LOGGED_IN: [Permissions.ADMIN],
	                      Events.USER_LOGGED_OUT: [Permissions.ADMIN],
	                      "*": []}

	_event_payload_processors = {Events.CLIENT_OPENED: [lambda user, payload: payload if user.has_permission(Permissions.ADMIN) else dict()],
	                             Events.CLIENT_AUTHED: [lambda user, payload: payload if user.has_permission(Permissions.ADMIN) else dict()],
	                             "*": []}

	_emit_permissions = {"connected": [],
	                     "reauthRequired": [],
	                     "plugin": lambda payload: [] if payload.get("plugin") == "backup" and settings().getBoolean(["server", "firstRun"]) else [Permissions.STATUS],
	                     "*": [Permissions.STATUS]}

	_unauthed_backlog_max = 100

	def __init__(self, printer, fileManager, analysisQueue, userManager, groupManager, eventManager, pluginManager, session):
		if isinstance(session, octoprint.vendor.sockjs.tornado.session.Session):
			session = JsonEncodingSessionWrapper(session)

		octoprint.vendor.sockjs.tornado.SockJSConnection.__init__(self, session)

		self._logger = logging.getLogger(__name__)

		self._temperatureBacklog = []
		self._temperatureBacklogMutex = threading.Lock()
		self._logBacklog = []
		self._logBacklogMutex = threading.Lock()
		self._messageBacklog = []
		self._messageBacklogMutex = threading.Lock()

		self._unauthed_backlog = []
		self._unauthed_backlog_mutex = threading.RLock()

		self._printer = printer
		self._fileManager = fileManager
		self._analysisQueue = analysisQueue
		self._userManager = userManager
		self._groupManager = groupManager
		self._eventManager = eventManager
		self._pluginManager = pluginManager

		self._remoteAddress = None
		self._user = self._userManager.anonymous_user_factory()

		self._throttle_factor = 1
		self._last_current = 0
		self._base_rate_limit = 0.5

		self._held_back_current = None
		self._held_back_mutex = threading.RLock()

		self._register_hooks = self._pluginManager.get_hooks("octoprint.server.sockjs.register")
		self._authed_hooks = self._pluginManager.get_hooks("octoprint.server.sockjs.authed")
		self._emit_hooks = self._pluginManager.get_hooks("octoprint.server.sockjs.emit")

		self._registered = False
		self._authed = False

	@staticmethod
	def _get_remote_address(info):
		forwarded_for = info.headers.get("X-Forwarded-For")
		if forwarded_for is not None:
			return forwarded_for.split(",")[0]
		return info.ip

	def __str__(self):
		if self._remoteAddress:
			return "{!r} connected to {}".format(self, self._remoteAddress)
		else:
			return "Unconnected {!r}".format(self)

	def on_open(self, info):
		self._pluginManager.register_message_receiver(self.on_plugin_message)
		self._remoteAddress = self._get_remote_address(info)
		self._logger.info("New connection from client: %s" % self._remoteAddress)

		self._userManager.register_login_status_listener(self)
		self._groupManager.register_listener(self)

		plugin_signature = lambda impl: "{}:{}".format(impl._identifier, impl._plugin_version)
		template_plugins = list(map(plugin_signature, self._pluginManager.get_implementations(octoprint.plugin.TemplatePlugin)))
		asset_plugins = list(map(plugin_signature, self._pluginManager.get_implementations(octoprint.plugin.AssetPlugin)))
		ui_plugins = sorted(set(template_plugins + asset_plugins))

		import hashlib
		plugin_hash = hashlib.md5()
		plugin_hash.update(",".join(ui_plugins).encode('utf-8'))

		config_hash = settings().config_hash

		# connected => update the API key, might be necessary if the client was left open while the server restarted
		self._emit("connected", dict(version=octoprint.server.VERSION,
		                             display_version=octoprint.server.DISPLAY_VERSION,
		                             branch=octoprint.server.BRANCH,
		                             plugin_hash=plugin_hash.hexdigest(),
		                             config_hash=config_hash,
		                             debug=octoprint.server.debug,
		                             safe_mode=octoprint.server.safe_mode,
		                             permissions=[permission.as_dict() for permission in Permissions.all()]))

		self._eventManager.fire(Events.CLIENT_OPENED, {"remoteAddress": self._remoteAddress})
		self._register()

	def on_close(self):
		self._user = self._userManager.anonymous_user_factory()
		self._groupManager.unregister_listener(self)
		self._userManager.unregister_login_status_listener(self)

		self._unregister()
		self._eventManager.fire(Events.CLIENT_CLOSED, {"remoteAddress": self._remoteAddress})

		self._logger.info("Client connection closed: %s" % self._remoteAddress)

		self._on_logout()
		self._remoteAddress = None
		self._pluginManager.unregister_message_receiver(self.on_plugin_message)

	def on_message(self, message):
		try:
			import json
			message = json.loads(message)
		except Exception:
			self._logger.warning("Invalid JSON received from client {}, ignoring: {!r}".format(self._remoteAddress, message))
			return

		if "auth" in message:
			try:
				parts = message["auth"].split(":")
				if not len(parts) == 2:
					raise ValueError()
			except ValueError:
				self._logger.warning("Got invalid auth message from client {}, ignoring: {!r}".format(self._remoteAddress, message["auth"]))
			else:
				user_id, user_session = parts

				if self._userManager.validate_user_session(user_id, user_session):
					user = self._userManager.find_user(userid=user_id, session=user_session)
					self._on_login(user)
				else:
					self._logger.warning("Unknown user/session combo: {}:{}".format(user_id, user_session))
					self._on_logout()

			self._register()

		elif "throttle" in message:
			try:
				throttle = int(message["throttle"])
				if throttle < 1:
					raise ValueError()
			except ValueError:
				self._logger.warning("Got invalid throttle factor from client {}, ignoring: {!r}".format(self._remoteAddress, message["throttle"]))
			else:
				self._throttle_factor = throttle
				self._logger.debug("Set throttle factor for client {} to {}".format(self._remoteAddress, self._throttle_factor))

	def on_printer_send_current_data(self, data):
		if not self._user.has_permission(Permissions.STATUS):
			return

		# make sure we rate limit the updates according to our throttle factor
		with self._held_back_mutex:
			if self._held_back_current is not None:
				self._held_back_current.cancel()
				self._held_back_current = None

			now = time.time()
			delta = self._last_current + self._base_rate_limit * self._throttle_factor - now
			if delta > 0:
				self._held_back_current = threading.Timer(delta, lambda: self.on_printer_send_current_data(data))
				self._held_back_current.start()
				return

		self._last_current = now

		# add current temperature, log and message backlogs to sent data
		with self._temperatureBacklogMutex:
			temperatures = self._temperatureBacklog
			self._temperatureBacklog = []

		with self._logBacklogMutex:
			logs = self._logBacklog
			self._logBacklog = []

		with self._messageBacklogMutex:
			messages = self._messageBacklog
			self._messageBacklog = []

		busy_files = [dict(origin=v[0], path=v[1]) for v in self._fileManager.get_busy_files()]
		if "job" in data and data["job"] is not None \
				and "file" in data["job"] and "path" in data["job"]["file"] and "origin" in data["job"]["file"] \
				and data["job"]["file"]["path"] is not None and data["job"]["file"]["origin"] is not None \
				and (self._printer.is_printing() or self._printer.is_paused()):
			busy_files.append(dict(origin=data["job"]["file"]["origin"], path=data["job"]["file"]["path"]))

		data.update({
			"serverTime": time.time(),
			"temps": temperatures,
			"logs": logs,
			"messages": messages,
			"busyFiles": busy_files,
		})
		self._emit("current", payload=data)

	def on_printer_send_initial_data(self, data):
		data_to_send = dict(data)
		data_to_send["serverTime"] = time.time()
		self._emit("history", payload=data_to_send)

	def sendEvent(self, type, payload=None):
		permissions = self._event_permissions.get(type, self._event_permissions["*"])
		permissions = [x(self._user) if callable(x) else x for x in permissions]
		if not self._user or not all(map(lambda p: self._user.has_permission(p), permissions)):
			return

		processors = self._event_payload_processors.get(type, self._event_payload_processors["*"])
		for processor in processors:
			payload = processor(self._user, payload)

		self._emit("event", payload=dict(type=type, payload=payload))

	def sendTimelapseConfig(self, timelapseConfig):
		self._emit("timelapse", payload=timelapseConfig)

	def sendSlicingProgress(self, slicer, source_location, source_path, dest_location, dest_path, progress):
		self._emit("slicingProgress", payload=dict(slicer=slicer,
		                                           source_location=source_location,
		                                           source_path=source_path,
		                                           dest_location=dest_location,
		                                           dest_path=dest_path,
		                                           progress=progress))

	def sendRenderProgress(self, progress):
		self._emit("renderProgress",
		           dict(progress=progress)
		)

	def on_plugin_message(self, plugin, data, permissions=None):
		self._emit("plugin", payload=dict(plugin=plugin, data=data), permissions=permissions)

	def on_printer_add_log(self, data):
		with self._logBacklogMutex:
			self._logBacklog.append(data)

	def on_printer_add_message(self, data):
		with self._messageBacklogMutex:
			self._messageBacklog.append(data)

	def on_printer_add_temperature(self, data):
		with self._temperatureBacklogMutex:
			self._temperatureBacklog.append(data)

	def on_user_logged_out(self, user, stale=False):
		if user.get_id() == self._user.get_id() and hasattr(user, "session") and hasattr(self._user, "session") and user.session == self._user.session:
			self._logger.info("User {} logged out, logging out on socket".format(user.get_id()))
			self._on_logout()

			if stale:
				self._sendReauthRequired("stale")
			else:
				self._sendReauthRequired("logout")

	def on_user_modified(self, user):
		if user.get_id() == self._user.get_id():
			self._sendReauthRequired("modified")

	def on_user_removed(self, userid):
		if self._user.get_id() == userid:
			self._logger.info("User {} deleted, logging out on socket".format(userid))
			self._on_logout()
			self._sendReauthRequired("removed")

	def on_group_permissions_changed(self, group, added=None, removed=None):
		if self._user.is_anonymous and group == self._groupManager.guest_group:
			self._sendReauthRequired("modified")

	def on_group_subgroups_changed(self, group, added=None, removed=None):
		if self._user.is_anonymous and group == self._groupManager.guest_group:
			self._sendReauthRequired("modified")

	def _onEvent(self, event, payload):
		self.sendEvent(event, payload)

	def _register(self):
		"""Register this socket with the system if STATUS permission is available."""

		proceed = True
		for name, hook in self._register_hooks.items():
			try:
				proceed = proceed and hook(self, self._user)
			except Exception:
				self._logger.exception("Error processing register hook handler for plugin {}".format(name),
				                       extra=dict(plugin=name))

		if not proceed:
			return

		if self._registered:
			return

		if not self._user.has_permission(Permissions.STATUS):
			return

		# printer
		self._printer.register_callback(self)
		self._printer.send_initial_callback(self)

		# files
		self._fileManager.register_slicingprogress_callback(self)

		# events
		for event in octoprint.events.all_events():
			self._eventManager.subscribe(event, self._onEvent)

		# timelapse
		octoprint.timelapse.register_callback(self)
		octoprint.timelapse.notify_callback(self, timelapse=octoprint.timelapse.current)
		if octoprint.timelapse.current_render_job is not None:
			# This is a horrible hack for now to allow displaying a notification that a render job is still
			# active in the backend on a fresh connect of a client. This needs to be substituted with a proper
			# job management for timelapse rendering, analysis stuff etc that also gets cancelled when prints
			# start and so on.
			#
			# For now this is the easiest way though to at least inform the user that a timelapse is still ongoing.
			#
			# TODO remove when central job management becomes available and takes care of this for us
			self.sendEvent(Events.MOVIE_RENDERING, payload=octoprint.timelapse.current_render_job)
		self._registered = True

	def _unregister(self):
		"""Unregister this socket from the system"""

		self._printer.unregister_callback(self)
		self._fileManager.unregister_slicingprogress_callback(self)
		octoprint.timelapse.unregister_callback(self)
		for event in octoprint.events.all_events():
			self._eventManager.unsubscribe(event, self._onEvent)

	def _reregister(self):
		"""Unregister and register again"""
		self._unregister()
		self._register()

	def _sendReauthRequired(self, reason):
		self._emit("reauthRequired", payload=dict(reason=reason))

	def _emit(self, type, payload=None, permissions=None):
		proceed = True
		for name, hook in self._emit_hooks.items():
			try:
				proceed = proceed and hook(self, self._user, type, payload)
			except Exception:
				self._logger.exception("Error processing emit hook handler from plugin {}".format(name),
				                       extra=dict(plugin=name))

		if not proceed:
			return

		if permissions is None:
			permissions = self._emit_permissions.get(type, self._emit_permissions["*"])
			permissions = permissions(payload) if callable(permissions) else [x for x in permissions]

		if not self._user or not all(map(lambda p: self._user.has_permission(p), permissions)):
			if not self._authed:
				with self._unauthed_backlog_mutex:
					if len(self._unauthed_backlog) < self._unauthed_backlog_max:
						self._unauthed_backlog.append((type, payload))
						self._logger.debug("Socket message held back until permissions cleared, added to backlog: {}".format(type))
					else:
						self._logger.debug("Socket message held back, but backlog full. Throwing message away: {}".format(type))
			return

		self._do_emit(type, payload)

	def _do_emit(self, type, payload):
		try:
			self.send({type: payload})
		except Exception as e:
			if self._logger.isEnabledFor(logging.DEBUG):
				self._logger.exception("Could not send message to client {}".format(self._remoteAddress))
			else:
				self._logger.warning("Could not send message to client {}: {}".format(self._remoteAddress, e))

	def _on_login(self, user):
		self._user = user
		self._logger.info("User {} logged in on the socket from client {}".format(user.get_name(),
		                                                                          self._remoteAddress))
		self._authed = True

		for name, hook in self._authed_hooks.items():
			try:
				hook(self, self._user)
			except Exception:
				self._logger.exception("Error processing authed hook handler for plugin {}".format(name),
				                       extra=dict(plugin=name))

		# if we have a backlog from being unauthed, process that now
		with self._unauthed_backlog_mutex:
			backlog = self._unauthed_backlog
			self._unauthed_backlog = []

		if len(backlog):
			self._logger.debug("Sending {} messages on the socket that were held back".format(len(backlog)))
			for message, payload in backlog:
				self._do_emit(message, payload)

		# trigger ClientAuthed event
		octoprint.events.eventManager().fire(octoprint.events.Events.CLIENT_AUTHED,
		                                     payload=dict(username=user.get_name(),
		                                                  remoteAddress=self._remoteAddress))

	def _on_logout(self):
		self._user = self._userManager.anonymous_user_factory()
		self._authed = False

		for name, hook in self._authed_hooks.items():
			try:
				hook(self, self._user)
			except Exception:
				self._logger.exception("Error processing authed hook handler for plugin {}".format(name),
				                       extra=dict(plugin=name))

