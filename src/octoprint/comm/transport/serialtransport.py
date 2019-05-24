# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

from octoprint.comm.transport import Transport, LineAwareTransportWrapper, PushingTransportWrapper
from octoprint.comm.util.parameters import TextType, IntegerType, SuggestionType, Value

import serial
import logging

class SerialTransport(Transport):
	name = "Serial Connection"
	key = "serial"
	message_integrity = False

	suggested_baudrates = [250000, 230400, 115200, 57600, 38400, 19200, 9600]
	unix_port_patterns = ["/dev/ttyUSB*", "/dev/ttyACM*", "/dev/tty.usb*",
	                      "/dev/cu.*", "/dev/cuaU*", "/dev/rfcomm*"]

	max_write_passes = 5

	@classmethod
	def for_additional_ports_and_baudrates(cls, additional_ports, additional_baudrates):
		patterns = SerialTransport.unix_port_patterns
		if additional_ports:
			patterns += additional_ports

		baudrates = SerialTransport.suggested_baudrates
		if additional_baudrates:
			baudrates += additional_baudrates

		return type(cls.__name__ + b"WithAdditionalPorts",
		            (cls,),
		            {b"unix_port_patterns": patterns,
		             b"suggested_baudrates": baudrates})

	@classmethod
	def get_connection_options(cls):
		return [
			SuggestionType("port", "Port", cls.get_available_serial_ports(), lambda value: Value(value)),
			SuggestionType("baudrate", "Baudrate", cls.get_available_baudrates(), lambda value: Value(value), default=0)
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

		port_values = [Value(None, title="Auto detect")] + sorted([Value(port.device, title=port.description) for port in ports], key=lambda x: x.title)
		return port_values

	@classmethod
	def get_available_baudrates(cls):
		return [Value(0, title="Auto detect")] + \
		       sorted([Value(baudrate) for baudrate in cls.suggested_baudrates], key=lambda x: x.title, reverse=True)

	def __init__(self, *args, **kwargs):
		super(SerialTransport, self).__init__()

		self.serial_factory = kwargs.get("serial_factory", None)

		self._logger = logging.getLogger(__name__)
		self._serial = None

		self._closing = False

	def create_connection(self, port="AUTO", baudrate=0):
		factory = self.serial_factory
		if self.serial_factory is None:
			factory = self._default_serial_factory

		self._closing = False
		self._serial = factory(port=port, baudrate=baudrate)
		self.set_current_args(port=port, baudrate=baudrate)

		return True

	def drop_connection(self):
		error = False

		if self._serial is not None:
			self._closing = True

			try:
				if callable(getattr(self._serial, "cancel_read", None)):
					self._serial.cancel_read()
			except Exception:
				self._logger.exception("Error while cancelling pending reads from the serial port")

			try:
				if callable(getattr(self._serial, "cancel_write", None)):
					self._serial.cancel_write()
			except Exception:
				self._logger.exception("Error while cancelling pending writes to the serial port")

			try:
				self._serial.close()
			except Exception:
				self._logger.exception("Error while closing the serial port")
				error = True

			self._serial = None

		return not error

	def do_read(self, size=None, timeout=None):
		return self._serial.read(size=size)

	def do_write(self, data):
		written = 0
		passes = 0

		def try_to_write(d):
			result = self._serial.write(d)
			if result is None or not isinstance(result, int):
				# probably some plugin not returning the written bytes, assuming all of them
				return len(data)
			else:
				return result

		while written < len(data):
			to_send = data[written:]
			old_written = written

			try:
				written += try_to_write(to_send)
			except serial.SerialTimeoutException:
				self._logger.warn("Serial timeout while writing to serial port, trying again.")
				try:
					# second try
					written += try_to_write(to_send)
				except Exception:
					if not self._closing:
						message = "Unexpected error while writing to serial port"
						self._logger.exception(message)
						self.disconnect(error=message)
					break
			except Exception:
				if not self._closing:
					message = "Unexpected error while writing to serial port"
					self._logger.exception(message)
					self.disconnect(error=message)
				break

			if old_written == written:
				passes += 1
				if passes > self.max_write_passes:
					message = "Could not write anything to the serial port in {} tries, something appears to be " \
					          "wrong with the printer communication".format(self.max_write_passes)
					self._logger.error(message)
					self.disconnect(error=message)
					break

	@property
	def in_waiting(self):
		return getattr(self._serial, "in_waiting", 0)

	def _default_serial_factory(self, port=None, baudrate=None):
		return serial.Serial(port=port, baudrate=baudrate)

	def __str__(self):
		return "SerialTransport"

if __name__ == "__main__":
	# list ports
	ports = SerialTransport.get_available_serial_ports()
	for port in ports:
		print(port.title + ": " + port.value)
