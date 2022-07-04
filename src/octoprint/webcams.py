import logging
from itertools import chain

import octoprint.plugin


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


def webcams_to_dict(allWebcams):
    webcams = []
    for plugin in allWebcams:
        for webcam in allWebcams[plugin]:
            webcam_dict = webcam.toDict()
            webcam_dict["provider"] = plugin
            webcams.append(webcam_dict)

    return webcams


def webcams_to_list(allWebcams):
    return sorted(set(chain(*allWebcams.values())))


class WebcamConfiguration:
    """
    A configuration describing a webcam.

    Arguments:
        name (str): Identifier of this webcam configuration.
        display_name (str): Displayable name for this webcam configuration.
        snapshot (str): The URL to get the snapshot from, optional.
        rotate_90 (bool): Whether the snpashot needs to be rotated by 90deg counter clockwise
        flip_h (bool): Whether the snpashot needs to be flipped horizontally
        flip_v (bool): Whether the snpashot needs to be flipped veritcally
        attachments (dict): A dictionary with domain specific configurations for the webcam that are not part of the standard configuration
        compat (obj): A CompatWebcamConfiguration object that will be used in the settings to allow backwards compatibility with older clients, optional
    """

    def __init__(
        self,
        name,
        display_name,
        snapshot,
        rotate_90,
        flip_h,
        flip_v,
        attachments=None,
        compat=None,
    ):
        self.name = name
        self.display_name = display_name
        self.snapshot = snapshot
        self.compat = compat
        self.rotate_90 = rotate_90
        self.flip_h = flip_h
        self.flip_v = flip_v
        self.attachments = attachments

    def toDict(self):
        return dict(
            name=self.name,
            displayName=self.display_name,
            snapshot=self.snapshot,
            rotate90=self.rotate_90,
            flipH=self.flip_h,
            flipV=self.flip_v,
            attachments=self.attachments,
            compatStream=self.compat.stream if self.compat is not None else None,
        )


class CompatWebcamConfiguration:
    """
    A configuration describing a webcam how it was configured in OctoPrint 1.8 and older. Information from this model can be
    used to let older clients use a webcam. Information that is still present in WebcamConfiguration is omitted.

    Arguments:
        stream (str): The URL to get an MJPEG stream from, optional.
        stream_timeout (str): The timoeut of the stream in seconds, optional.
        stream_webrtc_ice_servers (str): The WebRTC STUN and TURN servers, optional.
        stream_ratio (str): The stream's aspect ratio, e.g. "16:9", optional.
        cache_buster (bool): Whether the the URL should be randomized to bust caches, optional.
    """

    def __init__(
        self,
        stream=None,
        stream_timeout=None,
        stream_ratio=None,
        stream_webrtc_ice_servers=None,
        cache_buster=None,
    ):
        self.stream_timeout = stream_timeout
        self.stream_ratio = stream_ratio
        self.stream_webrtc_ice_servers = stream_webrtc_ice_servers
        self.cache_buster = cache_buster
        self.stream = stream

    def toDict(self):
        return dict(
            stream=self.stream,
            streamRatio=self.stream_ratio,
            cacheBuster=self.cache_buster,
            streamWebRtcIceServers=self.stream_webrtc_ice_servers,
        )
