__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

from enum import Enum
from typing import List, Optional

from octoprint.schema import BaseModel
from octoprint.vendor.with_attrs_docs import with_attrs_docs


class RatioEnum(str, Enum):
    sixteen_nine = "16:9"
    four_three = "4:3"


@with_attrs_docs
class WebcamCompatibility(BaseModel):
    streamTimeout: int = 5
    """The timeout of the stream in seconds"""

    streamRatio: RatioEnum = RatioEnum.sixteen_nine
    """The stream's native aspect ratio"""

    streamWebrtcIceServers: List[str] = ["stun:stun.l.google.com:19302"]
    """The WebRTC STUN and TURN servers"""

    cacheBuster: bool = False
    """Whether the URL should be randomized to bust caches"""

    stream: str
    """The URL to get an MJPEG stream from"""

    snapshot: str = None
    """The URL to get the snapshot from"""

    snapshotTimeout: int = 5
    """The timeout when retrieving snapshots"""

    snapshotSslValidation: bool = True
    """Whether to validate SSL certificates when retrieving a snapshot"""


@with_attrs_docs
class Webcam(BaseModel):
    name: str
    """Identifier of this webcam"""

    displayName: str
    """Displayable name for this webcam"""

    canSnapshot: bool = False
    """Whether this webcam can take a snapshot."""

    snapshotDisplay: str = None
    """Human readable information about how a snapshot is captured or a HTTP URL from which the snapshot is loaded (optional, only for user reference)"""

    flipH: bool = False
    """Whether to flip the webcam horizontally."""

    flipV: bool = False
    """Whether to flip the webcam vertically."""

    rotate90: bool = False
    """Whether to rotate the webcam 90° counter clockwise."""

    extras: dict = {}
    """Unstructured data describing this webcam"""

    compat: Optional[WebcamCompatibility] = None
    """A compatibility configuration to allow older clients to make use of this webcam"""
