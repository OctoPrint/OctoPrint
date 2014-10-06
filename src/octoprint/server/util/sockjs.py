# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging
import threading
import sockjs.tornado

import octoprint.timelapse
import octoprint.server
from octoprint.events import Events


class PrinterStateConnection(sockjs.tornado.SockJSConnection):
	def __init__(self, printer, fileManager, analysisQueue, userManager, eventManager, session):
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

	def _getRemoteAddress(self, info):
		forwardedFor = info.headers.get("X-Forwarded-For")
		if forwardedFor is not None:
			return forwardedFor.split(",")[0]
		return info.ip

	def on_open(self, info):
		remoteAddress = self._getRemoteAddress(info)
		self._logger.info("New connection from client: %s" % remoteAddress)

		# connected => update the API key, might be necessary if the client was left open while the server restarted
		self._emit("connected", {"apikey": octoprint.server.UI_API_KEY, "version": octoprint.server.VERSION, "display_version": octoprint.server.DISPLAY_VERSION})

		self._printer.registerCallback(self)
		octoprint.timelapse.registerCallback(self)

		self._eventManager.fire(Events.CLIENT_OPENED, {"remoteAddress": remoteAddress})
		for event in octoprint.events.all_events():
			self._eventManager.subscribe(event, self._onEvent)

		octoprint.timelapse.notifyCallbacks(octoprint.timelapse.current)

	def on_close(self):
		self._logger.info("Client connection closed")
		self._printer.unregisterCallback(self)
		octoprint.timelapse.unregisterCallback(self)

		self._eventManager.fire(Events.CLIENT_CLOSED)
		for event in octoprint.events.all_events():
			self._eventManager.unsubscribe(event, self._onEvent)

	def on_message(self, message):
		pass

	def sendCurrentData(self, data):
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

		data.update({
			"temps": temperatures,
			"logs": logs,
			"messages": messages
		})
		self._emit("current", data)

	def sendHistoryData(self, data):
		self._emit("history", data)

	def sendEvent(self, type, payload=None):
		self._emit("event", {"type": type, "payload": payload})

	def sendFeedbackCommandOutput(self, name, output):
		self._emit("feedbackCommandOutput", {"name": name, "output": output})

	def sendTimelapseConfig(self, timelapseConfig):
		self._emit("timelapse", timelapseConfig)

	def addLog(self, data):
		with self._logBacklogMutex:
			self._logBacklog.append(data)

	def addMessage(self, data):
		with self._messageBacklogMutex:
			self._messageBacklog.append(data)

	def addTemperature(self, data):
		with self._temperatureBacklogMutex:
			self._temperatureBacklog.append(data)

	def _onEvent(self, event, payload):
		self.sendEvent(event, payload)

	def _emit(self, type, payload):
		self.send({type: payload})
