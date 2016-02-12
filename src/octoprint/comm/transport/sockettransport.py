# coding=utf-8
from __future__ import absolute_import, print_function, unicode_literals

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"

from octoprint.comm.transport import Transport, LineAwareTransportWrapper
from octoprint.comm.transport.parameters import TextType, IntegerType

import socket

class TcpTransport(Transport):

	name = "TCP Transport"
	key = "tcpsocket"
	message_integrity = True

	@classmethod
	def get_connection_options(cls):
		return [
			TextType("host", "Host"),
			IntegerType("port", "Port", min=1)
		]

	def __init__(self):
		super(TcpTransport, self).__init__()

		self._socket = None

	def create_connection(self, host=None, port=None):
		if host is None:
			raise ValueError("host must not be None")
		if port is None:
			raise ValueError("port must not be None")

		self._socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
		self._socket.connect((host, port))

	def drop_connection(self):
		self._socket.close()

	def do_read(self, size=None, timeout=None):
		if size is None:
			size = 16
		return self._socket.recv(size)

	def do_write(self, data):
		self._socket.sendall(data)

	def __str__(self):
		return "TcpTransport"

if __name__ == "__main__":
	transport = LineAwareTransportWrapper(TcpTransport())
	transport.connect(host="google.de", port=80)
	transport.write(b"GET / HTTP/1.1\r\n\r\n")
	while(True):
		print("<<< {!r}".format(transport.read()))
