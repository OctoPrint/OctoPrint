__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2019 The OctoPrint Project - Released under terms of the AGPLv3 License"

from octoprint.comm.protocol.reprap.flavors import StandardFlavor


class KlipperFlavor(StandardFlavor):

    key = "klipper"
    name = "Klipper"

    unknown_requires_ack = True

    @classmethod
    def identifier(cls, firmware_name, firmware_info):
        return "klipper" in firmware_name.lower()
