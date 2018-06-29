from __future__ import absolute_import, unicode_literals

from octoprint.comm.protocol.reprap.flavors.generic import GenericFlavor

class ReprapFirmwareFlavor(GenericFlavor):

	key = "smoothieware"
	name = "Smoothieware"

