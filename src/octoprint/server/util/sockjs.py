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

	def _getRemoteAddress(self, info):
		forwardedFor = info.headers.get("X-Forwarded-For")
		if forwardedFor is not None:
			return forwardedFor.split(",")[0]
		return info.ip

	def on_open(self, info):
		self._remoteAddress = self._getRemoteAddress(info)
		self._logger.info("New connection from client: %s" % self._remoteAddress)

		# connected => update the API key, might be necessary if the client was left open while the server restarted
		self._emit("connected", {"apikey": octoprint.server.UI_API_KEY, "version": octoprint.server.VERSION, "display_version": octoprint.server.DISPLAY_VERSION})

		self._printer.register_callback(self)
		self._fileManager.register_slicingprogress_callback(self)
		octoprint.timelapse.registerCallback(self)
		self._pluginManager.register_message_receiver(self.on_plugin_message)

		self._eventManager.fire(Events.CLIENT_OPENED, {"remoteAddress": self._remoteAddress})
		for event in octoprint.events.all_events():
			self._eventManager.subscribe(event, self._onEvent)

		octoprint.timelapse.notifyCallbacks(octoprint.timelapse.current)

	def on_close(self):
		self._logger.info("Client connection closed: %s" % self._remoteAddress)
		self._printer.unregister_callback(self)
		self._fileManager.unregister_slicingprogress_callback(self)
		octoprint.timelapse.unregisterCallback(self)
		self._pluginManager.unregister_message_receiver(self.on_plugin_message)

		self._eventManager.fire(Events.CLIENT_CLOSED, {"remoteAddress": self._remoteAddress})
		for event in octoprint.events.all_events():
			self._eventManager.unsubscribe(event, self._onEvent)

	def on_message(self, message):
		pass

	def on_printer_send_current_data(self, data):
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
