from __future__ import absolute_import, unicode_literals

from octoprint.comm.protocol.reprap.flavors.generic import GenericFlavor

class ReprapFirmwareFlavor(GenericFlavor):

	key = "reprapfirmware"
	name = "RepRapFirmware"

	sd_relative_path = True

	@classmethod
	def identifier(cls, firmware_name, firmware_info):
		return "reprapfirmware" in firmware_name.lower()

