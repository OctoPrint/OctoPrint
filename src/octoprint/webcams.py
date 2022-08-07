import logging

import octoprint.plugin
from octoprint.schema.config.webcam import Webcam


def get_all_webcams():
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


def webcams_to_dicts(allWebcams):
    webcams = []

    for plugin in allWebcams:
        for webcam in allWebcams[plugin]:
            webcam_dict = webcam.dict()
            webcam_dict["provider"] = plugin
            webcams.append(webcam_dict)

    return webcams


def webcams_to_list(allWebcams):
    webcams = []
    for plugin in allWebcams:
        for webcam in allWebcams[plugin]:
            webcams.append(webcam)

    return webcams
