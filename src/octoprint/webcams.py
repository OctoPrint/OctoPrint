__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging

import octoprint.plugin
from octoprint.plugin import plugin_manager
from octoprint.schema.webcam import Webcam


def get_webcams(plugin_manager=None):
    webcams = dict()

    def success_callback(name, plugin, result):
        nonlocal webcams

        logger = logging.getLogger(__name__)

        if result is None:
            return

        if not isinstance(result, (list, tuple)):
            logger.error(
                f"Received object from `get_webcam_configurations` of plugin {name} that is not a list of Webcam instances",
                extra={"plugin": name},
            )
            return

        for webcam in result:
            if not isinstance(webcam, Webcam):
                logger.warning(
                    f"Received object in list from `get_webcam_configurations` of plugin {name} that is not an instance of Webcam, skipping",
                    extra={"plugin": name},
                )
                continue
            if webcam.name in webcams:
                logger.warning(
                    f"Webcam name {webcam.name} provided by plugin {name} is already in use",
                    extra={"plugin": name},
                )
                continue

            webcams[webcam.name] = ProvidedWebcam(
                config=webcam,
                providerIdentifier=name,
            )

    def error_callback(name, _, exc):
        logging.getLogger(__name__).info(exc)

    octoprint.plugin.call_plugin(
        octoprint.plugin.WebcamProviderPlugin,
        "get_webcam_configurations",
        sorting_context="WebcamProviderPlugin.get_webcam_configurations",
        callback=success_callback,
        error_callback=error_callback,
        manager=plugin_manager,
    )

    return webcams


def get_default_webcam(settings=None, plugin_manager=None):
    def fallbackFilter(webcam: Webcam):
        return webcam.config.compat

    return __get_webcam_by_setting("defaultWebcam", fallbackFilter)


def get_snapshot_webcam(settings=None, plugin_manager=None):
    def fallbackFilter(webcam: Webcam):
        return webcam.config.canSnapshot

    return __get_webcam_by_setting("snapshotWebcam", fallbackFilter)


def __get_webcam_by_setting(setting, fallbackFilter, settings=None, plugin_manager=None):
    webcams = get_webcams(plugin_manager=plugin_manager)
    if not webcams:
        return None

    if settings is None:
        from octoprint.settings import settings as s

        settings = s()

    name = settings.get(["webcam", setting])
    webcam = webcams.get(name)

    if webcam:
        return webcam

    return next(filter(fallbackFilter, iter(webcams.values())), None)


def get_webcams_as_dicts(plugin_manager=None):
    def to_dict(webcam):
        webcam_dict = webcam.config.dict()
        webcam_dict["provider"] = webcam.providerIdentifier
        return webcam_dict

    return list(map(to_dict, get_webcams(plugin_manager=plugin_manager).values()))


class WebcamNotAbleToTakeSnapshotException(Exception):
    """Raised a webcam that is not able to take a snapshot is used to take a snapshot"""

    def __init__(self, webcam_name):
        self.webcam_name = webcam_name
        self.message = f"Webcam {webcam_name} can't take snapshots"
        super().__init__(self.message)


class ProvidedWebcam:
    config: Webcam
    """the ``WebcamConfiguration`` configuration"""

    providerIdentifier: str
    """identifier of the plugin providing this Webcam"""

    providerPlugin: str
    """plugin instance of the plugin providing this Webcam"""

    def __init__(self, config, providerIdentifier):
        self.config = config
        self.providerIdentifier = providerIdentifier

        providerPluginInfo = plugin_manager().get_plugin_info(providerIdentifier)
        if providerPluginInfo is None:
            raise Exception(f"Can't find plugin {providerIdentifier}")
        if not providerPluginInfo.implementation:
            raise Exception(
                f"Plugin {providerIdentifier} does not have an implementation"
            )
        self.providerPlugin = providerPluginInfo.implementation

        if self.config is None:
            raise Exception("Can't create ProvidedWebcam with None config")

        if self.providerIdentifier is None:
            raise Exception("Can't create ProvidedWebcam with None providerIdentifier")
