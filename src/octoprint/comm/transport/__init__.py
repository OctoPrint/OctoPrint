# coding=utf-8
from __future__ import absolute_import, unicode_literals

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2016 The OctoPrint Project - Released under terms of the AGPLv3 License"

from .parameters import get_param_dict

import logging
import time

from octoprint.util.listener import ListenerAware
from octoprint.plugin import plugin_manager

_registry = dict()

def register_transports():
	from .serialtransport import SerialTransport, VirtualSerialTransport
	from .sockettransport import TcpTransport

	logger = logging.getLogger(__name__)

	# stock transports
	register_transport(SerialTransport)
	register_transport(VirtualSerialTransport)
	register_transport(TcpTransport)

	# more transports provided by plugins
	hooks = plugin_manager().get_hooks(b"octoprint.comm.transport.register")
	for name, hook in hooks.items():
		try:
			transports = hook()
			for transport in transports:
				try:
					register_transport(transport)
				except:
					logger.exception("Error while registering transport class {} for plugin {}".format(transport, name))
		except:
			logger.exception("Error executing octoprint.comm.transport.register hook for plugin {}".format(name))


def register_transport(transport_class):
	if not hasattr(transport_class, "key"):
		raise ValueError("Transport class {} is missing key".format(transport_class))
	_registry[transport_class.key] = transport_class


def lookup_transport(key):
	return _registry.get(key)


class Transport(ListenerAware):

	name = None
	key = None
	message_integrity = False

	@classmethod
	def get_connection_options(cls):
		return []

	def __init__(self, *args, **kwargs):
		super(Transport, self).__init__()

		self._logger = logging.getLogger(__name__)
		self._state = TransportState.DISCONNECTED

	@property
	def state(self):
		return self._state

	@state.setter
	def state(self, value):
		old_state = self.state
		self._state = value
		self.notify_listeners("on_transport_log_message", self, "Transport state changed from '{}' to '{}'".format(old_state, value))

	def connect(self, **params):
		if self.state == TransportState.CONNECTED:
			raise TransportAlreadyConnectedError("Already connected, disconnect first")
		options = self.get_connection_options()
		param_dict = get_param_dict(params, options)
		self.create_connection(**param_dict)
		self.state = TransportState.CONNECTED
		self.notify_listeners("on_transport_connected", self)

	def disconnect(self, error=None):
		if self.state == TransportState.DISCONNECTED:
			raise TransportNotConnectedError("Already disconnected")
		self.drop_connection()

		if error:
			self.state = TransportState.DISCONNECTED_WITH_ERROR
			self.notify_listeners("on_transport_log_message", self, error)
		else:
			self.state = TransportState.DISCONNECTED

		self.notify_listeners("on_transport_disconnected", self, error=error)

	def create_connection(self, *args, **kwargs):
		pass

	def drop_connection(self):
		pass

	def read(self, size=None, timeout=None):
		data = self.do_read(size=size, timeout=timeout)
		self.notify_listeners("on_transport_log_received_data", self, data)
		return data

	def write(self, data):
		self.do_write(data)
		self.notify_listeners("on_transport_log_sent_data", self, data)

	def do_read(self, size=None, timeout=None):
		return b""

	def do_write(self, data):
		pass

	def __str__(self):
		return self.__class__.__name__


class TransportState(object):
	CONNECTED = "connected"
	DISCONNECTED = "disconnected"
	DISCONNECTED_WITH_ERROR = "disconnected_with_error"


class TransportNotConnectedError(Exception):
	pass


class TransportAlreadyConnectedError(Exception):
	pass


class TransportWrapper(ListenerAware):

	unforwarded_handlers = []
	"""Allows to explicitly disable certain transport listener handlers on sub classes."""

	def __init__(self, transport):
		ListenerAware.__init__(self)
		self.transport = transport
		self.transport.register_listener(self)

		# make sure we forward any transport listener calls to our own registered listeners

		def forward_handler(name):
			def f(*args, **kwargs):
				# replace references to self.transport with self
				args = [self if arg == self.transport else arg for arg in args]
				kwargs = dict((key, self if value == self.transport else value) for key, value in kwargs.items())

				# forward
				self.notify_listeners(name, *args, **kwargs)
			return f

		for handler in filter(lambda x: x.startswith("on_transport_"), dir(TransportListener)):
			if handler not in self.__class__.unforwarded_handlers:
				setattr(self, handler, forward_handler(handler))

	def __getattr__(self, item):
		return getattr(self.transport, item)


class SeparatorAwareTransportWrapper(TransportWrapper):

	unforwarded_handlers = ["on_transport_log_received_data"]
	"""We have read overwritten and hence send our own received_data notification."""

	def __init__(self, transport, separator, internal_timeout=0.1):
		TransportWrapper.__init__(self, transport)

		self.separator = separator
		self.internal_timeout = internal_timeout

		self._buffered = b""

	def read(self, size=None, timeout=None):
		data = self._buffered
		self._buffered = b""

		rest = timeout
		while self.separator not in data and (rest is None or rest > 0):
			start = time.time()
			read = self.transport.read(1, timeout=self.internal_timeout)
			end = time.time()

			if rest is not None:
				rest -= end - start if end > start else 0
				if rest < 0:
					rest = 0

			if read is None:
				# EOF
				break
			data += read

		if rest is not None and rest <= 0:
			# couldn't read a full line within the timeout, returning empty line and
			# buffering already read data
			self._buffered = data
			data = b""

		self.notify_listeners("on_transport_log_received_data", self, data)
		return data

	def __str__(self):
		return "SeparatorAwareTransportWrapper({}, separator={})".format(self.transport, self.separator)

class LineAwareTransportWrapper(SeparatorAwareTransportWrapper):

	def __init__(self, transport):
		SeparatorAwareTransportWrapper.__init__(self, transport, b"\n")

	def __str__(self):
		return "LineAwareTransportWrapper({})".format(self.transport)

class PushingTransportWrapper(TransportWrapper):

	def __init__(self, transport, name="pushingTransportReceiveLoop", timeout=None):
		super(PushingTransportWrapper, self).__init__(transport)
		self.name = name
		self.timeout = timeout

		self._receiver_active = False
		self._receiver_thread = None

	@property
	def active(self):
		return self._receiver_active

	def connect(self, **kwargs):
		self.transport.connect(**kwargs)

		import threading

		self._receiver_active = True
		self._receiver_thread = threading.Thread(target=self._receiver_loop, name=self.name)
		self._receiver_thread.daemon = True
		self._receiver_thread.start()

	def disconnect(self):
		self._receiver_active = False
		self.transport.disconnect()

	def wait(self):
		self._receiver_thread.join()

	def _receiver_loop(self):
		while self._receiver_active:
			try:
				data = self.transport.read(timeout=self.timeout)
				self.notify_listeners("on_transport_data_pushed", self, data)
			except:
				if self._receiver_active:
					raise

	def __str__(self):
		return "PushingTransportWrapper({})".format(self.transport)

class TransportListener(object):

	def on_transport_connected(self, transport):
		pass

	def on_transport_disconnected(self, transport, error=None):
		pass

	def on_transport_log_sent_data(self, transport, data):
		pass

	def on_transport_log_received_data(self, transport, data):
		pass

	def on_transport_log_message(self, transport, data):
		pass

class PushingTransportWrapperListener(object):

	def on_transport_data_pushed(self, transport, data):
		pass

