__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

from enum import Enum
from typing import Optional

from octoprint.schema import BaseModel
from octoprint.vendor.with_attrs_docs import with_attrs_docs


class TimelapseTypeEnum(str, Enum):
    off = "off"
    zchange = "zchange"
    timed = "timed"


class RenderAfterPrintEnum(str, Enum):
    off = "off"
    always = "always"
    success = "success"
    failure = "failure"


@with_attrs_docs
class TimelapseOptions(BaseModel):
    interval: Optional[int] = None
    """``timed`` timelapses only: The interval which to leave between images in seconds."""

    capturePostRoll: Optional[bool] = None
    """``timed`` timelapses only: Whether to capture the snapshots for the post roll (``true``) or just copy the last captured snapshot from the print over and over again (``false``)."""

    retractionZHop: Optional[float] = None
    """``zchange`` timelapses only: z-hop height during retractions to ignore for capturing snapshots."""


@with_attrs_docs
class TimelapseConfig(BaseModel):
    type: TimelapseTypeEnum = TimelapseTypeEnum.off
    """The timelapse type."""

    fps: int = 25
    """The framerate at which to render the movie."""

    postRoll: int = 0
    """
    The number of seconds in the rendered video to add after a finished print. The exact way how the
    additional images will be recorded depends on timelapse type. ``zchange`` timelapses will take one
    final picture and add it ``fps * postRoll`` times. ``timed`` timelapses continue to record just
    like at the beginning, so the recording will continue another ``fps * postRoll * interval`` seconds.
    This behaviour can be overridden by setting the ``capturePostRoll`` option to ``false``, in which case
    the post roll will be created identically to ``zchange`` mode.
    """

    renderAfterPrint: RenderAfterPrintEnum = RenderAfterPrintEnum.always
    """Determines whether rendering the timelapse should be done automatically after the print is finished. This can be done always, only after successful prints, only after failed prints, or never."""

    options: TimelapseOptions = TimelapseOptions()
    """Additional options depending on the timelapse type."""


@with_attrs_docs
class WebcamConfig(BaseModel):
    webcamEnabled: bool = True
    """Use this option to enable display of a webcam stream in the UI, e.g. via MJPG-Streamer. Webcam support will be disabled if not set."""

    timelapseEnabled: bool = True
    """Use this option to enable timelapse support via snapshot, e.g. via MJPG-Streamer. Timelapse support will be disabled if not set."""

    ffmpeg: Optional[str] = None
    """Path to ffmpeg binary to use for creating timelapse recordings. Timelapse support will be disabled if not set."""

    ffmpegThreads: int = 1
    """Number of how many threads to instruct ffmpeg to use for encoding."""

    ffmpegVideoCodec: str = "libx264"
    """Videocodec to be used for encoding."""

    bitrate: str = "10000k"
    """The bitrate to use for rendering the timelapse video. This gets directly passed to ffmpeg."""

    watermark: bool = True
    """Whether to include a "created with OctoPrint" watermark in the generated timelapse recordings."""

    ffmpegCommandline: str = '{ffmpeg} -framerate {fps} -i "{input}" -vcodec {videocodec} -threads {threads} -b:v {bitrate} -f {containerformat} -y {filters} "{output}"'
    """
    The full commandline to use for rendering timelapse recordings through ffmpeg. Supports the following placeholders:

    - ``ffmpeg``: the ffmpeg command as defined under ``webcam.ffmpeg``
    - ``fps``: the fps setting as defined by the timelapse configuration
    - ``input``: the path to the input files
    - ``videocodec``: the video codec to use, as defined in ``webcam.ffmpegVideoCodec``
    - ``threads``: the number of threads to use, as defined in ``webcam.ffmpegThreads``
    - ``bitrate``: the bitrate to use, as defined in ``webcam.bitrate``
    - ``containerformat``: the container format to use, based on the selected codec
    - ``filters``: the filter chain
    - ``output``: the path to the output file
    """

    ffmpegThumbnailCommandline: str = (
        '{ffmpeg} -sseof -1 -i "{input}" -update 1 -q:v 0.7 "{output}"'
    )
    """
    The full commandline to use for generating thumbnails through ffmpeg. Supports the following placeholders:

    - ``ffmpeg``: the ffmpeg command as defined under ``webcam.ffmpeg``
    - ``input``: the path to the input file
    - ``output``: the path to the output file
    """

    timelapse: TimelapseConfig = TimelapseConfig()
    """The default timelapse settings."""

    cleanTmpAfterDays: int = 7
    """After how many days unrendered timelapses will be deleted."""

    renderAfterPrintDelay: int = 0
    """Delay to wait for after print end before rendering timelapse, in seconds. If another print gets started during this time, the rendering will be postponed."""

    defaultWebcam: str = "classic"
    """The name of the default webcam"""

    snapshotWebcam: str = "classic"
    """The name of the default webcam to use for snapshots"""
