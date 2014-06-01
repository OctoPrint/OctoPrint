# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 Gina Häußge - Released under terms of the AGPLv3 License"

import logging


class Transport(object):

	def __init__(self, messageReceiver=None, stateReceiver=None, logReceiver=None):
		self._transport_logger = logging.getLogger("TRANSPORT")

		self._messageReceiver = messageReceiver
		self._stateReceiver = stateReceiver
		self._logReceiver = logReceiver
		self._state = State.DISCONNECTED
		self._error = None
		self._opt = {}

	def get_properties(self):
		raise NotImplemented()

	def get_connection_options(self):
		return []

	def get_current_connection(self):
		return self._opt

	def connect(self, opt):
		self._opt = opt

	def disconnect(self, onError=False):
		if onError:
			self.changeState(State.DISCONNECTED_WITH_ERROR)
		else:
			self.changeState(State.DISCONNECTED)

	def send(self, command):
		pass

	def receive(self):
		pass

	def changeState(self, newState):
		oldState = self._state
		self._state = newState
		if self._stateReceiver is not None:
			self._stateReceiver.onStateChangeReceived(self, oldState, newState)

	def onError(self, error):
		self.changeState(State.ERROR)
		self._error = error

	def onTimeout(self):
		if self._messageReceiver is not None:
			self._messageReceiver.onTimeoutReceived(self)

	def getError(self):
		return self._error

	def logTx(self, tx):
		if self._logReceiver is not None:
			self._logReceiver.onLogTx(self, tx)

	def logRx(self, rx):
		if self._logReceiver is not None:
			self._logReceiver.onLogRx(self, rx)

	def logError(self, error):
		if self._logReceiver is not None:
			self._logReceiver.onLogError(self, error)

	def onMessageReceived(self, message):
		if self._messageReceiver is not None:
			self._messageReceiver.onMessageReceived(self, message)


class TransportProperties(object):

	FLOWCONTROL = "flowControl"


class State(object):
	OPENING_CONNECTION = "Opening connection"
	DETECTING_CONNECTION = "Detecting connection"
	CONNECTED = "Connected"
	DISCONNECTED = "Disconnected"
	DISCONNECTED_WITH_ERROR = "Disconnected with error"
	ERROR = "Error"


class MessageReceiver(object):
	def onMessageReceived(self, source, message):
		pass

	def onTimeoutReceived(self, source):
		pass


class StateReceiver(object):
	def onStateChangeReceived(self, source, oldState, newState):
		pass


class LogReceiver(object):
	def onLogTx(self, source, tx):
		pass

	def onLogRx(self, source, rx):
		pass

	def onLogError(self, source, error):
		pass
