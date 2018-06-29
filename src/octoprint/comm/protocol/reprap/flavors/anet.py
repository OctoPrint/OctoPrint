from __future__ import absolute_import, unicode_literals

from .repetier import RepetierFlavor

class AnetA8RepetierFlavor(RepetierFlavor):

	key = "aneta8repetier"
	name = "Anet A8"

	@classmethod
	def identifier(cls, firmware_name, firmware_info):
		return "anet_a8" in firmware_name.lower()

