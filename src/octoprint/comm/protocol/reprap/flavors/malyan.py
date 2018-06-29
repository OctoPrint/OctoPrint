from __future__ import absolute_import, unicode_literals

from octoprint.comm.protocol.reprap.flavors.generic import GenericFlavor

class MalyanFlavor(GenericFlavor):

	key = "malyan"
	name = "Malyan"

	always_send_checksum = False
	block_while_dwelling = True
	sd_always_available = True

	@classmethod
	def identifier(cls, firmware_name, firmware_info):
		return "malyan" in firmware_name.lower()

