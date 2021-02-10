__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

from .anet import *  # noqa: F401,F403
from .generic import *  # noqa: F401,F403
from .klipper import *  # noqa: F401,F403
from .malyan import *  # noqa: F401,F403
from .marlin import *  # noqa: F401,F403
from .repetier import *  # noqa: F401,F403
from .reprapfirmware import *  # noqa: F401,F403
from .smoothieware import *  # noqa: F401,F403


class FlavorOverride:
    def __init__(self, flavor, overrides):
        self._flavor = flavor
        self._overrides = overrides

    @property
    def flavor(self):
        return self._flavor

    @flavor.setter
    def flavor(self, value):
        self._flavor = value

    @property
    def overrides(self):
        return self._overrides

    @overrides.setter
    def overrides(self, value):
        self._overrides = value

    def __getattr__(self, item):
        try:
            return self._overrides[item]
        except KeyError:
            return getattr(self._flavor, item)
