# coding=utf-8
from __future__ import absolute_import, unicode_literals, print_function

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2016 The OctoPrint Project - Released under terms of the AGPLv3 License"

from octoprint.comm.transport import Transport, LineAwareTransportWrapper, PushingTransportWrapper
from octoprint.comm.transport.parameters import TextType, IntegerType, SuggestionType, ConstantNameType

import serial
import logging

class SerialTransport(Transport):
	name = "Serial Connection"
	key = "serial"
	message_integrity = False

	suggested_baudrates = [0, 250000, 230400, 115200, 57600, 38400, 19200, 9600]
	unix_port_patterns = ["/dev/ttyUSB*", "/dev/ttyACM*", "/dev/tty.usb*",
	                      "/dev/cu.*", "/dev/cuaU*", "/dev/rfcomm*"]

	@classmethod
	def for_additional_ports_and_baudrates(cls, additional_ports, additional_baudrates):
		patterns = SerialTransport.unix_port_patterns + additional_ports
		baudrates = SerialTransport.suggested_baudrates + additional_baudrates
		return type(cls.__name__ + "WithAdditionalPorts",
		            (cls,),
		            {"unix_port_patterns": patterns,
		             "suggested_baudrates": baudrates})

	@classmethod
	def get_connection_options(cls):
		return [
			SuggestionType("port", "Port", TextType, cls.get_available_serial_ports(), default="AUTO"),
			SuggestionType("baudrate", "Baudrate", IntegerType, cls.suggested_baudrates, default=0)
		]

	@classmethod
	def get_available_serial_ports(cls):
		import sys

		if sys.platform == "win32":
			# windows
			from serial.tools.list_ports import comports
			ports = comports()

		else:
			# posix
			import glob

			devices = [device
			           for pattern in cls.unix_port_patterns
			           for device in glob.glob(pattern)]

			plat = sys.platform.lower()

			if plat[:5] == "linux":
				# linux
				from serial.tools.list_ports_linux import SysFS
				ports = [info
				         for info in [SysFS(d) for d in devices]
				         if info.subsystem != "platform"]
			else:
				# other posix systems
				from serial.tools import list_ports_common
				ports = [list_ports_common.ListPortInfo(d) for d in devices]

		return [ConstantNameType("AUTO", "Autodetect")] \
		       + [ConstantNameType(port.device, port.description) for port in ports]

	def __init__(self):
		super(SerialTransport, self).__init__()
		self._serial = None

		self._logger = logging.getLogger(__name__)

	def create_connection(self, port="AUTO", baudrate=0):
		self._serial = serial.Serial(port=port, baudrate=baudrate)

	def close(self):
		self._serial.close()

	def read(self, size=None):
		result = self._serial.read(size=size)
		print("<<< {!r}".format(result))
		return result

	def write(self, data):
		self._serial.write(data)
		print(">>> {!r}".format(data))

	def close_connection(self):
		self._serial.close()


class VirtualSerialTransport(SerialTransport):
	name = "Virtual Serial Connection"
	key = "virtual"

	@classmethod
	def get_connection_options(cls):
		return []

	def __init__(self, *args, **kwargs):
		super(VirtualSerialTransport, self).__init__()
		self.virtual_serial_factory = kwargs.get("virtual_serial_factory", None)

	def create_connection(self, *args, **kwargs):
		if self.virtual_serial_factory is None:
			raise ValueError("virtual_serial_factory is unset")

		if not callable(self.virtual_serial_factory):
			raise ValueError("virtual_serial_factory is not callable")

		self._serial = self.virtual_serial_factory()


if __name__ == "__main__":
	for option in VirtualSerialTransport.get_connection_options():
		print(repr(option))

	def create_virtual_serial():
		class VirtualSerial():
			def __init__(self):
				self.active = True
				self.lines = [b"one", b"two", b"three", b"four", b"five"]

			def read(self, size=None):
				if self.active:
					if self.lines:
						data = self.lines.pop(0)
						print("read called: {!r}".format(data))
						return data + b"\n"
					else:
						self.close()
						return ""
				else:
					raise RuntimeError("virtual serial is closed")

			def write(self, data):
				print("write called: {!r}".format(data))

			def close(self):
				self.active = False
				print("Closed")
		return VirtualSerial()

	from octoprint.comm.transport import TransportListener
	class MyTransportListener(TransportListener):
		def on_transport_data_received(self, transport, data):
			print(">>> Received: {!r}".format(data))
			transport.write(b"echo:" + data)

	listener = MyTransportListener()

	#pushingvirtual = PushingTransportWrapper(LineAwareTransportWrapper(VirtualSerialTransport(virtual_serial_factory=create_virtual_serial)))
	#pushingvirtual.register_listener(listener)
	#pushingvirtual.connect()
	#pushingvirtual.write(b"Just a test")
	#pushingvirtual.wait()

	to_send = [b"Send 1", b"Send 2"]
	virtual = LineAwareTransportWrapper(VirtualSerialTransport(virtual_serial_factory=create_virtual_serial))
	virtual.connect()
	for data in to_send:
		data += b"\n"
		print(">>> {!r}".format(data))
		virtual.write(data)
		print("<<< {!r}".format(virtual.read()))
	virtual.close()
