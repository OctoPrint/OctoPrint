# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

from octoprint.comm.protocol.reprap.flavors.generic import GenericFlavor

class MarlinFlavor(GenericFlavor):

	key = "marlin"
	name = "Marlin"

	emergency_commands = ["M112", "M108", "M410"]
	heatup_abortable = True


class MarlinLegacyFlavor(GenericFlavor):

	key = "marlinlegacy"
	name = "Legacy Marlin"

	@classmethod
	def identifier(cls, firmware_name, firmware_info):
		return "marlin v1" in firmware_name.lower()


class PrusaMarlinFlavor(MarlinFlavor):

	key = "prusamarlin"
	name = "Marlin: Prusa variant"

	@classmethod
	def identifier(cls, firmware_name, firmware_info):
		return "prusa-firmware" in firmware_name.lower() and "marlin" in firmware_name.lower()
