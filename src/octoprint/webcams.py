class WebcamConfiguration:
    """
    A configuration describing a webcam.

    Arguments:
        name (str): Identifier of this webcam configuration.
        display_name (str): Displayable name for this webcam configuration.
        snapshot (str): The URL to get the snapshot from, optional.
        legacy (obj): A LegacyWebcamConfiguration object that will be used in the settings to allow backwards compatibility with older clients, optional
        rotate_90 (bool): Whether the snpashot needs to be rotated by 90deg counter clockwise
        flip_h (bool): Whether the snpashot needs to be flipped horizontally
        flip_v (bool): Whether the snpashot needs to be flipped veritcally
        attachments (dict): A dictionary with domain specific configurations for the webcam that are not part of the standard configuration
    """

    def __init__(
        self, name, display_name, snapshot, legacy, rotate_90, flip_h, flip_v, attachments
    ):
        self.name = name
        self.display_name = display_name
        self.snapshot = snapshot
        self.legacy = legacy
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
        )


class LegacyWebcamConfiguration:
    """
    A configuration describing a webcam.

    Arguments:
        stream (str): The URL to get an MJPEG stream from, optional.
        snapshot (str): The URL to get the snapshot from, optional.
        rotate_90 (bool): Whether the snpashot needs to be rotated by 90deg counter clockwise, optional.
        flip_h (bool): Whether the snpashot needs to be flipped horizontally, optional.
        flip_v (bool): Whether the snpashot needs to be flipped veritcally, optional.
        stream_timeout (str): The timoeut of the stream in seconds, optional.
        stream_webrtc_ice_servers (str): The WebRTC STUN and TURN servers, optional.
        stream_ratio (str): The stream's aspect ratio, e.g. "16:9", optional.
        cache_buster (bool): Whether the the URL should be randomized to bust caches, optional.
    """

    def __init__(
        self,
        snapshot,
        stream,
        rotate_90,
        flip_h,
        flip_v,
        stream_timeout,
        stream_ratio,
        stream_webrtc_ice_servers,
        cache_buster,
    ):
        self.stream_timeout = stream_timeout
        self.stream_ratio = stream_ratio
        self.stream_webrtc_ice_servers = stream_webrtc_ice_servers
        self.cache_buster = cache_buster
        self.snapshot = snapshot
        self.stream = stream
        self.rotate_90 = rotate_90
        self.flip_h = flip_h
        self.flip_v = flip_v

    def toDict(self):
        return dict(
            snapshot=self.snapshot,
            stream=self.stream,
            rotate90=self.rotate_90,
            flipH=self.flip_h,
            flipV=self.flip_v,
            streamRatio=self.stream_ratio,
            cacheBuster=self.cache_buster,
            streamWebRtcIceServers=self.stream_webrtc_ice_servers,
        )
