__author__ = "Marc Hannappel Salandora"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

from octoprint.settings import settings
from octoprint import slicers

REGISTERED_SLICERS = {
	"cura": {
		"enabled": False,
		"path": "/default/path/to/cura",
		"config": "/default/path/to/your/cura/config.ini",
	},
	"slic3r": {
		"enabled": False,
		"path": "/default/path/to/slic3r",
		"config": "/default/path/to/your/slic3r/config.ini",
	}
}
SLICER_DESCRIPTORS = {
	"cura": [
		"Cura",
		"Enable slicing via Cura",
		"Path to Cura",
		"Path to Cura config"
	],
	"slic3r": [
		"Slic3r",
		"Enable slicing via Slic3r",
		"Path to Slic3r",
		"Path to Slic3r config",
	],
}



def SlicingSupported():
    """Simple Function to check if a slicer is enabled"""

    slicing_enabled = False
    for key in REGISTERED_SLICERS.iterkeys():
        slicing_enabled = settings().getBoolean(["slicers", key, "enabled"]) or slicing_enabled
        if slicing_enabled:
            break

    return slicing_enabled

def create_slicer():
        if not SlicingSupported():
            return None

        createSlicer = None
        configPath = None
        for key in REGISTERED_SLICERS.iterkeys():
            if settings().getBoolean(["slicers", key, "enabled"]):
                _slicerModule = __import__("octoprint.slicers." + key, globals(), locals(), ["SlicerFactory"], -1)
                createSlicer = _slicerModule.SlicerFactory.create_slicer
                configPath = settings().get(["slicers", key, "config"])
                break

        if createSlicer is None:
            return None

        return [createSlicer(), configPath]