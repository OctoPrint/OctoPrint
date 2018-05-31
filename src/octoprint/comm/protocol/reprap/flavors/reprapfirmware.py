
from octoprint.comm.protocol.reprap.flavors.generic import GenericFlavor

class ReprapFirmwareFlavor(GenericFlavor):

	key = "reprapfirmware"

	sd_relative_path = True

	@classmethod
	def identifier(cls, firmware_name, firmware_info):
		return "reprapfirmware" in firmware_name.lower()

