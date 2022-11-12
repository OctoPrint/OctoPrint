import logging

import octoprint.plugin
from octoprint.plugin import plugin_manager
from octoprint.schema.config.webcam import Webcam
from octoprint.settings import settings


def get_webcams():
    webcams = dict()

    def success_callback(name, _, result):
        nonlocal webcams
        if type(result) is list:
            for webcam in result:
                if type(webcam) is not Webcam:
                    logging.getLogger(name).error(
                        "Received object in list from `get_webcam_configurations` that is not a instance of Webcam"
                    )
                elif webcam.name in webcams:
                    logging.getLogger(name).error(
                        f"Webcam name {webcam.name} is already used but must be unique"
                    )
                else:
                    webcams[webcam.name] = ProvidedWebcam(
                        config=webcam,
                        providerIdentifier=name,
                    )
        elif result is None:
            return
        else:
            logging.getLogger(name).error(
                "Received object from `get_webcam_configurations` that is not a list of Webcam instances"
            )

    def error_callback(name, _, exc):
        logging.getLogger(name).info(exc)

    octoprint.plugin.call_plugin(
        octoprint.plugin.WebcamProviderPlugin,
        "get_webcam_configurations",
        sorting_context="WebcamProviderPlugin.get_webcam_configurations",
        callback=success_callback,
        error_callback=error_callback,
    )

    return webcams


def get_default_webcam():
    webcams = get_webcams()
    webcamsList = list(webcams.values())
    s = settings()
    defaultWebcamName = s.get(["webcam", "defaultWebcam"])
    defaultWebcam = webcams.get(defaultWebcamName)
    if defaultWebcam is not None:
        return defaultWebcam
    else:
        webcamsList[0] if len(webcamsList) > 0 else None


def get_webcams_as_dicts():
    def toDict(webcam):
        webcam_dict = webcam.config.dict()
        webcam_dict["provider"] = webcam.providerIdentifier
        return webcam_dict

    return list(map(lambda item: toDict(item), get_webcams().values()))


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
        self.providerPlugin = (
            plugin_manager().get_plugin(providerIdentifier).__plugin_implementation__
        )

        if self.config is None:
            raise Exception("Can't create ProvidedWebcam with None config")

        if self.providerIdentifier is None:
            raise Exception("Can't create ProvidedWebcam with None providerIdentifier")

        if self.providerPlugin is None:
            raise Exception("Can't create ProvidedWebcam with None providerPlugin")
