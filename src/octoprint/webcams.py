import logging

import octoprint.plugin
from octoprint.schema.config.webcam import Webcam
from octoprint.settings import settings


def get_webcams():
    webcams = dict()

    def success_callback(name, _, result):
        nonlocal webcams
        if type(result) is list:
            confirmedWebcams = []
            for webcam in result:
                if type(webcam) is Webcam:
                    confirmedWebcams.append(webcam)
                else:
                    logging.getLogger(name).error(
                        "Received object in list from `get_webcam_configurations` that is not a instance of Webcam"
                    )

            webcams[name] = confirmedWebcams
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
    webcamsList = get_webcams_as_list()
    s = settings()
    defaultWebcamName = s.get(["webcam", "defaultWebcam"])
    if defaultWebcamName is not None:
        return next((w for w in webcamsList if w.name == defaultWebcamName), None)
    else:
        webcamsList[0] if len(webcamsList) > 0 else None


def get_webcams_as_dicts():
    allWebcams = get_webcams()
    webcams = []

    for plugin in allWebcams:
        for webcam in allWebcams[plugin]:
            webcam_dict = webcam.dict()
            webcam_dict["provider"] = plugin
            webcams.append(webcam_dict)

    return webcams


def get_webcams_as_list():
    allWebcams = get_webcams()
    webcams = []

    for plugin in allWebcams:
        for webcam in allWebcams[plugin]:
            webcams.append(webcam)

    return webcams
