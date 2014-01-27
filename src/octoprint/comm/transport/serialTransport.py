# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 Gina Häußge - Released under terms of the AGPLv3 License"


import threading
import serial

from . import Transport, TransportProperties, State
from octoprint.util import getExceptionString
from octoprint.util.virtual import VirtualPrinter


class SerialTransport(Transport):

	def __init__(self, messageReceiver, stateReceiver, logReceiver):
		Transport.__init__(self, messageReceiver, stateReceiver, logReceiver)

		self._serial = None
		self._port = None
		self._baudrate = None
		self._connectionTimeout = None
		self._writeTimeout = None

		self._timeoutCounter = 0
		self._maxTimeouts = 20

		self._thread = None

	def getProperties(self):
		return {
			TransportProperties.FLOWCONTROL: False
		}

	def connect(self, opt):
		self._port = opt["port"] if "port" in opt else None
		self._baudrate = opt["baudrate"] if "baudrate" in opt else None
		self._connectionTimeout = opt["connectionTimeout"] if "connectionTimeout" in opt else 2.0
		self._communicationTimeout = opt["communicationTimeout"] if "communicationTimeout" in opt else 5.0
		self._writeTimeout = opt["writeTimeout"] if "writeTimeout" in opt else 10000

		if self._connect():
			self._thread = threading.Thread(target=self._monitor, name="SerialTransportMonitor")
			self._thread.daemon = True
			self._thread.start()

	def disconnect(self, onError=False):
		try:
			self._serial.close()
		finally:
			self._serial = None
		self._thread = None
		Transport.disconnect(self, onError)

	def send(self, command):
		self.logTx(command)

		commandToSend = command + "\n"
		try:
			self._serial.write(commandToSend)
		except serial.SerialTimeoutException:
			self.logError("Serial timeout while writing to serial port, trying again.")

			try:
				self._serial.write(commandToSend)
			except:
				exceptionString = getExceptionString()
				self.logError("Unexpected error while writing serial port: %s" % exceptionString)
				self.onError(exceptionString)
				self.disconnect(True)
		except:
			exceptionString = getExceptionString()
			self.logError("Unexpected error while writing serial port: %s" % exceptionString)
			self.onError(exceptionString)
			self.disconnect(True)

	def _monitor(self):
		error = None
		while True:
			line = self._readline()
			if line is None:
				error = "Serial connection closed unexpectedly"
				break
			if line == "":
				self._timeoutCounter += 1
				self.onTimeout()
				if self._maxTimeouts and self._timeoutCounter > self._maxTimeouts:
					error = "Printer did not respond at all over %d retries, considering it dead" % self._maxTimeouts
					break
			else:
				self._timeoutCounter = 0
			self.onMessageReceived(line.strip())

		if error is not None:
			self.logError(error)
			# TODO further error handling

	def _connect(self):
		self.changeState(State.OPENING_CONNECTION)
		try:
			self._serial = serial.Serial(self._port, self._baudrate, timeout=self._communicationTimeout, writeTimeout=self._writeTimeout)
			return True
		except:
			self.logError("Unexpected error while connecting to serial port: %s %s" % (self._port, getExceptionString()))
			self.onError("Failed to open serial port, permissions correct?")
			return False

	def _readline(self):
		if self._serial is None:
			return None

		try:
			line = self._serial.readline()
		except:
			exceptionString = getExceptionString()
			self.logError("Unexpected error while reading serial port: %s" % exceptionString)
			self.onError(exceptionString)
			self.disconnect()
			return None

		if line != "":
			self.logRx(unicode(line, "ascii", "replace").encode("ascii", "replace").rstrip())
		return line


class VirtualSerialTransport(SerialTransport):
	def _connect(self):
		self.changeState(State.OPENING_CONNECTION)
		self._serial = VirtualPrinter()
		self.changeState(State.CONNECTED)
		return True
