# coding=utf-8
from __future__ import absolute_import, unicode_literals, print_function

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2016 The OctoPrint Project - Released under terms of the AGPLv3 License"

from octoprint.comm.transport import Transport
from octoprint.comm.transport.types import TextType, IntegerType, SuggestionType, ConstantNameType

import serial

class SerialTransport(Transport):
	name = "Serial Connection"
	url_scheme = "serial"
	message_integrity = False

	suggested_baudrates = [0, 250000, 230400, 115200, 57600, 38400, 19200, 9600]
	unix_port_patterns = ["/dev/ttyUSB*", "/dev/ttyACM*", "/dev/tty.usb*",
	                      "/dev/cu.*", "/dev/cuaU*", "/dev/rfcomm*"]

	@staticmethod
	def for_additional_ports(additional_ports):
		patterns = SerialTransport.unix_port_patterns + additional_ports
		return type("SerialTransportWithAdditionalPorts",
		            (SerialTransport,),
		            {"unix_port_patterns": patterns})

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
		Transport.__init__(self)

		self._serial = None

	def create_connection(self, port, baudrate):
		self._serial = serial.Serial(port=port, baudrate=baudrate)

	def send(self, message):
		self._serial.write(message)

	def close_connection(self):
		self._serial.close()


class VirtualSerialTransport(SerialTransport):
	virtual_serial = None

	@staticmethod
	def for_virtual_serial(virtual_serial):
		return type("CustomizedVirtualSerialTransport",
		            (VirtualSerialTransport,),
		            {"virtual_serial": virtual_serial})

	@classmethod
	def get_connection_options(cls):
		return []


if __name__ == "__main__":
	for option in SerialTransport.get_connection_options():
		print(repr(option))
