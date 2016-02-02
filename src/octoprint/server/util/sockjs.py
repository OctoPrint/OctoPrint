# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging
import threading
import sockjs.tornado
import time

import octoprint.timelapse
import octoprint.server
from octoprint.events import Events

import octoprint.printer


class PrinterStateConnection(sockjs.tornado.SockJSConnection, octoprint.printer.PrinterCallback):
	def __init__(self, printer, fileManager, analysisQueue, userManager, eventManager, pluginManager, session):
		sockjs.tornado.SockJSConnection.__init__(self, session)

		self._logger = logging.getLogger(__name__)

		self._temperatureBacklog = []
		self._temperatureBacklogMutex = threading.Lock()
		self._logBacklog = []
		self._logBacklogMutex = threading.Lock()
		self._messageBacklog = []
		self._messageBacklogMutex = threading.Lock()

		self._printer = printer
		self._fileManager = fileManager
		self._analysisQueue = analysisQueue
		self._userManager = userManager
		self._eventManager = eventManager
		self._pluginManager = pluginManager

		self._remoteAddress = None

		self._throttleFactor = 1
		self._lastCurrent = 0
		self._baseRateLimit = 0.5

	def _getRemoteAddress(self, info):
		forwardedFor = info.headers.get("X-Forwarded-For")
		if forwardedFor is not None:
			return forwardedFor.split(",")[0]
		return info.ip

	def on_open(self, info):
		self._remoteAddress = self._getRemoteAddress(info)
		self._logger.info("New connection from client: %s" % self._remoteAddress)

		plugin_signature = lambda impl: "{}:{}".format(impl._identifier, impl._plugin_version)
		template_plugins = map(plugin_signature, self._pluginManager.get_implementations(octoprint.plugin.TemplatePlugin))
		asset_plugins = map(plugin_signature, self._pluginManager.get_implementations(octoprint.plugin.AssetPlugin))
		ui_plugins = sorted(set(template_plugins + asset_plugins))

		import hashlib
		plugin_hash = hashlib.md5()
		plugin_hash.update(",".join(ui_plugins))

		# connected => update the API key, might be necessary if the client was left open while the server restarted
		self._emit("connected", {
			"apikey": octoprint.server.UI_API_KEY,
			"version": octoprint.server.VERSION,
			"display_version": octoprint.server.DISPLAY_VERSION,
			"branch": octoprint.server.BRANCH,
			"plugin_hash": plugin_hash.hexdigest()
		})

		self._printer.register_callback(self)
		self._fileManager.register_slicingprogress_callback(self)
		octoprint.timelapse.register_callback(self)
		self._pluginManager.register_message_receiver(self.on_plugin_message)

		self._eventManager.fire(Events.CLIENT_OPENED, {"remoteAddress": self._remoteAddress})
		for event in octoprint.events.all_events():
			self._eventManager.subscribe(event, self._onEvent)

		octoprint.timelapse.notify_callbacks(octoprint.timelapse.current)

		# This is a horrible hack for now to allow displaying a notification that a render job is still
		# active in the backend on a fresh connect of a client. This needs to be substituted with a proper
		# job management for timelapse rendering, analysis stuff etc that also gets cancelled when prints
		# start and so on.
		#
		# For now this is the easiest way though to at least inform the user that a timelapse is still ongoing.
		#
		# TODO remove when central job management becomes available and takes care of this for us
		if octoprint.timelapse.current_render_job is not None:
			self._emit("event", {"type": Events.MOVIE_RENDERING, "payload": octoprint.timelapse.current_render_job})

	def on_close(self):
		self._logger.info("Client connection closed: %s" % self._remoteAddress)
		self._printer.unregister_callback(self)
		self._fileManager.unregister_slicingprogress_callback(self)
		octoprint.timelapse.unregister_callback(self)
		self._pluginManager.unregister_message_receiver(self.on_plugin_message)

		self._eventManager.fire(Events.CLIENT_CLOSED, {"remoteAddress": self._remoteAddress})
		for event in octoprint.events.all_events():
			self._eventManager.unsubscribe(event, self._onEvent)

	def on_message(self, message):
		try:
			import json
			message = json.loads(message)
		except:
			self._logger.warn("Invalid JSON received from client {}, ignoring: {!r}".format(self._remoteAddress, message))
			return

		if "throttle" in message:
			try:
				throttle = int(message["throttle"])
				if throttle < 1:
					raise ValueError()
			except ValueError:
				self._logger.warn("Got invalid throttle factor from client {}, ignoring: {!r}".format(self._remoteAddress, message["throttle"]))
			else:
				self._throttleFactor = throttle
				self._logger.debug("Set throttle factor for client {} to {}".format(self._remoteAddress, self._throttleFactor))

	def on_printer_send_current_data(self, data):
		# make sure we rate limit the updates according to our throttle factor
		now = time.time()
		if now < self._lastCurrent + self._baseRateLimit * self._throttleFactor:
			return
		self._lastCurrent = now

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

		busy_files = [dict(origin=v[0], name=v[1]) for v in self._fileManager.get_busy_files()]
		if "job" in data and data["job"] is not None \
				and "file" in data["job"] and "name" in data["job"]["file"] and "origin" in data["job"]["file"] \
				and data["job"]["file"]["name"] is not None and data["job"]["file"]["origin"] is not None \
				and (self._printer.is_printing() or self._printer.is_paused()):
			busy_files.append(dict(origin=data["job"]["file"]["origin"], name=data["job"]["file"]["name"]))

		data.update({
			"serverTime": time.time(),
			"temps": temperatures,
			"logs": logs,
			"messages": messages,
			"busyFiles": busy_files,
		})
		self._emit("current", data)

	def on_printer_send_initial_data(self, data):
		data_to_send = dict(data)
		data_to_send["serverTime"] = time.time()
		self._emit("history", data_to_send)

	def sendEvent(self, type, payload=None):
		self._emit("event", {"type": type, "payload": payload})

	def sendTimelapseConfig(self, timelapseConfig):
		self._emit("timelapse", timelapseConfig)

	def sendSlicingProgress(self, slicer, source_location, source_path, dest_location, dest_path, progress):
		self._emit("slicingProgress",
		           dict(slicer=slicer, source_location=source_location, source_path=source_path, dest_location=dest_location, dest_path=dest_path, progress=progress)
		)

	def on_plugin_message(self, plugin, data):
		self._emit("plugin", dict(plugin=plugin, data=data))

	def on_printer_add_log(self, data):
		with self._logBacklogMutex:
			self._logBacklog.append(data)

	def on_printer_add_message(self, data):
		with self._messageBacklogMutex:
			self._messageBacklog.append(data)

	def on_printer_add_temperature(self, data):
		with self._temperatureBacklogMutex:
			self._temperatureBacklog.append(data)

	def _onEvent(self, event, payload):
		self.sendEvent(event, payload)

	def _emit(self, type, payload):
		try:
			self.send({type: payload})
		except Exception as e:
			self._logger.warn("Could not send message to client %s: %s" % (self._remoteAddress, str(e)))
