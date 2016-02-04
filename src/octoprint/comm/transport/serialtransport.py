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

	@classmethod
	def get_available_baudrates(cls):
		return cls.suggested_baudrates

	def __init__(self, *args, **kwargs):
		super(SerialTransport, self).__init__()

		self.serial_factory = kwargs.get("serial_factory", None)

		self._logger = logging.getLogger(__name__)
		self._serial = None

	def create_connection(self, port="AUTO", baudrate=0):
		factory = self.serial_factory
		if self.serial_factory is None:
			factory = serial.Serial

		self._serial = factory(port=port, baudrate=baudrate)

	def drop_connection(self):
		if self._serial is not None:
			self._serial.close()
			self._serial = None

	def close(self):
		self._serial.close()

	def do_read(self, size=None, timeout=None):
		return self._serial.read(size=size)

	def do_write(self, data):
		self._serial.write(data)

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
