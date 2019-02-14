# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"

import octoprint.plugin

from octoprint.comm.transport.serialtransport import SerialTransport

class VirtualSerialTransport(SerialTransport):
	name = "Virtual Connection"
	key = "virtual"

	@classmethod
	def get_connection_options(cls):
		return []

	def create_connection(self, *args, **kwargs):
		from . import virtual
		self._serial = virtual.VirtualPrinter()


class VirtualPrinterPlugin(octoprint.plugin.SettingsPlugin):
	def register_transport_hook(self, *args, **kwargs):
		return [VirtualSerialTransport]


__plugin_name__ = "Virtual Printer"
__plugin_author__ = "Gina Häußge, based on work by Daid Braam"
__plugin_homepage__ = "https://github.com/foosel/OctoPrint/wiki/Plugin:-Virtual-Printer"
__plugin_license__ = "AGPLv3"
__plugin_description__ = "Provides a virtual printer via a virtual serial port for development and testing purposes"


def __plugin_load__():
	plugin = VirtualPrinterPlugin()

	global __plugin_implementation__
	__plugin_implementation__ = plugin

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.comm.transport.register": plugin.register_transport_hook
	}
