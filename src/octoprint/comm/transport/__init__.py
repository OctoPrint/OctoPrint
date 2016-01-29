# coding=utf-8
from __future__ import absolute_import, unicode_literals

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2016 The OctoPrint Project - Released under terms of the AGPLv3 License"

from .parameters import get_param_dict

import logging
import time

from octoprint.util.listener import ListenerAware

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

	def connect(self, **params):
		if self.state == TransportState.CONNECTED:
			raise AlreadyConnectedError("Already connected, disconnect first")
		options = self.get_connection_options()
		param_dict = get_param_dict(params, options)
		self.create_connection(**param_dict)

	def disconnect(self):
		pass

	def create_connection(self, *args, **kwargs):
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


class TransportState(object):
	CONNECTED = "connected"
	DISCONNECTED = "disconnected"


class NotConnectedError(Exception):
	pass


class AlreadyConnectedError(Exception):
	pass


class SeparatorAwareTransportWrapper(ListenerAware):

	def __init__(self, transport, separator, internal_timeout=0.1):
		super(SeparatorAwareTransportWrapper, self).__init__()

		self.transport = transport
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

	def write(self, data):
		self.transport.write(data)
		self.notify_listeners("on_transport_log_sent_data", self, data)

	def __getattr__(self, item):
		return getattr(self.transport, item)

class LineAwareTransportWrapper(SeparatorAwareTransportWrapper):

	def __init__(self, transport):
		SeparatorAwareTransportWrapper.__init__(self, transport, b"\n")

class PushingTransportWrapper(object):

	def __init__(self, transport, name="pushingTransportReceiveLoop", timeout=None):
		self.transport = transport
		self.name = name
		self.timeout = timeout

		self._receiver_active = False
		self._receiver_thread = None

	def connect(self, **kwargs):
		self.transport.connect(**kwargs)

		import threading

		self._receiver_active = True
		self._receiver_thread = threading.Thread(target=self._receiver_loop, name=self.name)
		self._receiver_thread.daemon = True
		self._receiver_thread.start()

	def disconnect(self):
		self.transport.disconnect()
		self._receiver_active = False

	def wait(self):
		self._receiver_thread.join()

	def _receiver_loop(self):
		while self._receiver_active:
			data = self.transport.read(timeout=self.timeout)
			self.notify_listeners("on_transport_data_pushed", self, data)

	def __getattr__(self, item):
		return getattr(self.transport, item)

class TransportListener(object):

	def on_transport_log_sent_data(self, transport, data):
		pass

	def on_transport_log_received_data(self, transport, data):
		pass

	def on_transport_log_message(self, transport, data):
		pass

class PushingTransportWrapperListener(object):

	def on_transport_data_pushed(self, transport, data):
		pass

