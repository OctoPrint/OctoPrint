# coding=utf-8
from __future__ import absolute_import, unicode_literals, print_function, \
	division

"""
Unit tests for ``octoprint.comm.protocol.reprap``.
"""

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2019 The OctoPrint Project - Released under terms of the AGPLv3 License"


import unittest
import mock
import ddt

import octoprint.comm.protocol.reprap

from octoprint.util import to_bytes

from .. import TestTransport


@ddt.ddt
class RepRapProtocolTest(unittest.TestCase):

	def setUp(self):
		printer_profile = mock.MagicMock()
		plugin_manager = mock.MagicMock()
		event_bus = mock.MagicMock()
		settings = mock.MagicMock()

		self.protocol = octoprint.comm.protocol.reprap.ReprapGcodeProtocol(printer_profile=printer_profile,
		                                                                   plugin_manager=plugin_manager,
		                                                                   event_bus=event_bus,
		                                                                   settings=settings)
		self.transport = TestTransport()

	def testHandshake(self):
		self.protocol.connect(self.transport)
		self._perform_and_test_handshake()

	def testHandshakeWithTemperatureAutoreport(self):
		self.protocol.interval["temperature_autoreport"] = 2.0
		self.protocol.connect(self.transport)
		self._perform_and_test_handshake(capabilities=dict(AUTOREPORT_TEMP=True))
		self.transport.expect_and_send("M155 S2\n", "ok\n")

	def testHandshakeWithTemperatureAutoreportButDisabled(self):
		self.protocol._capability_support[octoprint.comm.protocol.reprap.CAPABILITY_AUTOREPORT_TEMP] = False

		self.protocol.connect(self.transport)
		self._perform_and_test_handshake(capabilities=dict(AUTOREPORT_TEMP=True))
		self.transport.expect_and_send("M105\n", "ok T:21.3/0\n")
		self.transport.expect_and_send("M105\n", "ok T:21.3/0\n")

	def testHandshakeWithSdAutoreport(self):
		self.protocol.interval["sd_status_autoreport"] = 2.0
		self.protocol.connect(self.transport)
		self._perform_and_test_handshake(capabilities=dict(AUTOREPORT_SD_STATUS=True))
		self.transport.expect_and_send("M27 S2\n", "ok\n")

	@ddt.data(
		# regular notation
		("Error:Last Line Number is not Last Line Number+1\n", "Resend: N2\nok\n"),
		("Error:Last Line Number is not Last Line Number+1\n", "Resend: 2\nok\n"),

		# short hand notation
		("!! Last Line Number is not Last Line Number+1\n", "rs N2\nok\n"),
		("!! Last Line Number is not Last Line Number+1\n", "rs 2\nok\n"),

		# missing ok
		("Error:Last Line Number is not Last Line Number+1\n", "Resend: N2\n"),
	)
	@ddt.unpack
	def testResendRequest(self, error, request):
		self.protocol.connect(self.transport)
		self._perform_and_test_handshake()
		self.transport.send(error)
		self.transport.send(request)
		self.transport.expect_and_send("N2 M105*37\n", "ok T:21.3/0\n")

	def _perform_and_test_handshake(self, firmware_name=None, capabilities=None):
		if firmware_name is None:
			firmware_name = "ProtocolTest"
		if capabilities is None:
			capabilities = dict()

		firmware_info = "FIRMWARE_NAME:{}\n".format(firmware_name)
		for cap, enabled in capabilities.items():
			firmware_info += "Cap:{}:{}\n".format(cap.upper(), "1" if enabled else "0")
		firmware_info += "ok\n"

		self.transport.expect_and_send("N0 M110 N0*125\n", "start\n")    # tickle 1
		self.transport.expect_and_send("N0 M110 N0*125\n", "ok\n")       # tickle 2
		self.transport.expect_and_send("N0 M110 N0*125\n", "ok\n")       # reset line numbers
		self.transport.expect_and_send("N1 M115*39\n", firmware_info)    # get firmware info
		self.transport.expect_and_send("N2 M105*37\n", "ok T:21.3/0\n")  # temperature query

	@staticmethod
	def _checksummed(line, linenumber):
		result = b"N" + str(linenumber).encode("ascii") + b" " + to_bytes(line)
		checksum = 0
		for c in bytearray(result):
			checksum ^= c
		return result + b"*" + str(checksum).encode("ascii")
