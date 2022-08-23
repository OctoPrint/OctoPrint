import logging

import octoprint.plugin
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
                    webcams[webcam.name] = ProvidedWebcam(webcam, name)
        elif result is None:
            return
        else:
            logging.getLogger(name).error(
                "Received object from `get_webcam_configurations` that is not a list of Webcam instances"
            )

    def error_callback(name, _, exc):
        logging.getLogger(name).info(exc)

    octoprint.plugin.call_plugin(
        octoprint.plugin.WebcamPlugin,
        "get_webcam_configurations",
        sorting_context="WebcamPlugin.get_webcam_configurations",
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
        webcam_dict = webcam.webcam.dict()
        webcam_dict["provider"] = webcam.provider
        return webcam_dict

    return list(map(lambda item: toDict(item), get_webcams().values()))


class ProvidedWebcam:
    webcam: Webcam
    """the webcam configuration"""

    provider: str
    """name of the plugin providing this Webcam"""

    def __init__(self, webcam, provider):
        self.webcam = webcam
        self.provider = provider

        if self.webcam is None:
            raise Exception("Can't create ProvidedWebcam with None webcam")

        if self.provider is None:
            raise Exception("Can't create ProvidedWebcam with None provider")
