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

from octoprint.comm.protocol.reprap import ReprapGcodeProtocol

from .. import TestTransport


class RepRapProtocolTest(unittest.TestCase):

	def setUp(self):
		printer_profile = mock.MagicMock()
		plugin_manager = mock.MagicMock()
		event_bus = mock.MagicMock()
		settings = mock.MagicMock()

		self.protocol = ReprapGcodeProtocol(printer_profile=printer_profile,
		                                    plugin_manager=plugin_manager,
		                                    event_bus=event_bus,
		                                    settings=settings)
		self.transport = TestTransport()

	def testHandshake(self):
		self.transport.outgoing += b"start\nThis is a test\nNothing to see here\n"
		self.protocol.connect(self.transport)
