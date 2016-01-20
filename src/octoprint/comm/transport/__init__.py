# coding=utf-8
from __future__ import absolute_import, unicode_literals

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2016 The OctoPrint Project - Released under terms of the AGPLv3 License"

from .parameters import get_param_dict

class Transport(object):

	name = None
	key = None
	message_integrity = False

	@classmethod
	def get_connection_options(cls):
		return []

	def __init__(self, *args, **kwargs):
		pass

	def connect(self, **params):
		options = self.get_connection_options()
		param_dict = get_param_dict(params, options)
		self.create_connection(**param_dict)

	def disconnect(self):
		pass

	def create_connection(self, *args, **kwargs):
		pass

	def read(self, size=None):
		return b""

	def write(self, data):
		pass


class SeparatorAwareTransportWrapper(object):

	def __init__(self, transport, separator="\n", chunksize=128):
		self.transport = transport
		self.separator = separator

		self._buffered = b""
		self._chunksize = chunksize

	def read(self, size=None):
		if size is not None:
			return self._internal_read(size)

		data = b""
		while self.separator not in data:
			data += self._internal_read(size=self._chunksize)

		separator_pos = data.index(self.separator)
		separator_end = separator_pos + len(self.separator)
		self._buffered += data[separator_end:]
		return data[:separator_end]

	def _internal_read(self, size=None):
		if self._buffered:
			if size is not None and len(self._buffered) > size:
				# return first size bytes
				data = self._buffered[:size]
				self._buffered = self._buffered[size:]
				return data
			else:
				# fetch data from buffer, reset buffer and recalculate size
				data = self._buffered
				self._buffered = b""
				size -= len(data) if size is not None else None
		else:
			data = b""

		return data + self.transport.read(size)

	def __getattr__(self, item):
		return getattr(self.transport, item)

class LineAwareTransportWrapper(SeparatorAwareTransportWrapper):

	def __init__(self, transport, chunksize=512):
		SeparatorAwareTransportWrapper.__init__(self, transport, separator="\n", chunksize=chunksize)

class PushingTransportWrapper(object):

	def __init__(self, transport):
		self.transport = transport
		self._listeners = set()
		self._receiver_active = False
		self._receiver_thread = None

	def connect(self, **kwargs):
		self.transport.connect(**kwargs)

		import threading

		self._receiver_active = True
		self._receiver_thread = threading.Thread(target=self._receiver_loop)
		self._receiver_thread.daemon = True
		self._receiver_thread.start()

	def disconnect(self):
		self.transport.disconnect()
		self._receiver_active = False

	def wait(self):
		self._receiver_thread.join()

	def register_listener(self, transport_listener):
		self._listeners.add(transport_listener)

	def unregister_listener(self, transport_listener):
		try:
			self._listeners.remove(transport_listener)
		except KeyError:
			# not registered, ah well, we'll ignore that
			pass

	def _send_on_transport_data_received(self, data):
		for listener in self._listeners:
			listener.on_transport_data_received(self, data)

	def _receiver_loop(self):
		while self._receiver_active:
			data = self.transport.read()
			self._send_on_transport_data_received(data)

	def __getattr__(self, item):
		return getattr(self.transport, item)

class TransportListener(object):

	def on_transport_data_received(self, transport, data):
		pass

