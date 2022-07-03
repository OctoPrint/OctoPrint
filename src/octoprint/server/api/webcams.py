__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging

from flask import jsonify

import octoprint.plugin
import octoprint.timelapse
from octoprint.access.permissions import Permissions
from octoprint.server.api import api
from octoprint.server.util.flask import no_firstrun_access
from octoprint.webcams import WebcamConfiguration


def get_all_webcams():
    webcams = dict()

    def success_callback(name, _, result):
        nonlocal webcams
        if type(result) is list:
            confirmedWebcams = []
            for webcam in result:
                if type(webcam) is WebcamConfiguration:
                    confirmedWebcams.append(webcam)
                else:
                    logging.getLogger(name).error(
                        "Received object in list from `get_webcam_configurations` that is not a WebcamConfiguration"
                    )

            webcams[name] = confirmedWebcams
        elif result is None:
            return
        else:
            logging.getLogger(name).error(
                "Received object from `get_webcam_configurations` that is not a list of WebcamConfiguration"
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


@api.route("/webcams", methods=["GET"])
@no_firstrun_access
@Permissions.WEBCAM.require(403)
def getWebcams():
    webcams = []
    all_webcams = get_all_webcams()
    for plugin in all_webcams:
        for webcam in all_webcams[plugin]:
            webcam_dict = webcam.toDict()
            webcam_dict["provider"] = plugin
            webcams.append(webcam_dict)

    return jsonify(webcams)
