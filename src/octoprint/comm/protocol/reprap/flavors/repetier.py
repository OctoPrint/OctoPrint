# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


from octoprint.comm.protocol.reprap.flavors import ReprapGcodeFlavor

class RepetierFlavor(ReprapGcodeFlavor):

	always_send_checksum = True
