# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__author__ = "Gina Häußge <osd@foosel.net> based on work by David Braam"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2013 David Braam, Gina Häußge - Released under terms of the AGPLv3 License"


import base64
import codecs
import io
import logging
import math
import os
import zlib


class Vector3D(object):
    """
    3D vector value

    Supports addition, subtraction and multiplication with a scalar value (float, int) as well as calculating the
    length of the vector.

    Examples:

    >>> a = Vector3D(1.0, 1.0, 1.0)
    >>> b = Vector3D(4.0, 4.0, 4.0)
    >>> a + b == Vector3D(5.0, 5.0, 5.0)
    True
    >>> b - a == Vector3D(3.0, 3.0, 3.0)
    True
    >>> abs(a - b) == Vector3D(3.0, 3.0, 3.0)
    True
    >>> a * 2 == Vector3D(2.0, 2.0, 2.0)
    True
    >>> a * 2 == 2 * a
    True
    >>> a.length == math.sqrt(a.x ** 2 + a.y ** 2 + a.z ** 2)
    True
    >>> copied_a = Vector3D(a)
    >>> a == copied_a
    True
    >>> copied_a.x == a.x and copied_a.y == a.y and copied_a.z == a.z
    True
    """

    def __init__(self, *args):
        if len(args) == 3:
            (self.x, self.y, self.z) = args

        elif len(args) == 1:
            # copy constructor
            other = args[0]
            if not isinstance(other, Vector3D):
                raise ValueError("Object to copy must be a Vector3D instance")

            self.x = other.x
            self.y = other.y
            self.z = other.z

    @property
    def length(self):
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def __add__(self, other):
        try:
            if len(other) == 3:
                return Vector3D(self.x + other[0], self.y + other[1], self.z + other[2])
        except TypeError:
            # doesn't look like a 3-tuple
            pass

        try:
            return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)
        except AttributeError:
            # also doesn't look like a Vector3D
            pass

        raise TypeError(
            "other must be a Vector3D instance or a list or tuple of length 3"
        )

    def __sub__(self, other):
        try:
            if len(other) == 3:
                return Vector3D(self.x - other[0], self.y - other[1], self.z - other[2])
        except TypeError:
            # doesn't look like a 3-tuple
            pass

        try:
            return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)
        except AttributeError:
            # also doesn't look like a Vector3D
            pass

        raise TypeError(
            "other must be a Vector3D instance or a list or tuple of length 3"
        )

    def __mul__(self, other):
        try:
            return Vector3D(self.x * other, self.y * other, self.z * other)
        except TypeError:
            # doesn't look like a scalar
            pass

        raise ValueError("other must be a float or int value")

    def __rmul__(self, other):
        return self.__mul__(other)

    def __abs__(self):
        return Vector3D(abs(self.x), abs(self.y), abs(self.z))

    def __eq__(self, other):
        if not isinstance(other, Vector3D):
            return False
        return self.x == other.x and self.y == other.y and self.z == other.z

    def __str__(self):
        return "Vector3D(x={}, y={}, z={}, length={})".format(
            self.x, self.y, self.z, self.length
        )


class MinMax3D(object):
    """
    Tracks minimum and maximum of recorded values

    Examples:

    >>> minmax = MinMax3D()
    >>> minmax.record(Vector3D(2.0, 2.0, 2.0))
    >>> minmax.min.x == 2.0 == minmax.max.x and minmax.min.y == 2.0 == minmax.max.y and minmax.min.z == 2.0 == minmax.max.z
    True
    >>> minmax.record(Vector3D(1.0, 2.0, 3.0))
    >>> minmax.min.x == 1.0 and minmax.min.y == 2.0 and minmax.min.z == 2.0
    True
    >>> minmax.max.x == 2.0 and minmax.max.y == 2.0 and minmax.max.z == 3.0
    True
    >>> minmax.size == Vector3D(1.0, 0.0, 1.0)
    True
    >>> empty = MinMax3D()
    >>> empty.size == Vector3D(0.0, 0.0, 0.0)
    True
    """

    def __init__(self):
        self.min = Vector3D(float("inf"), float("inf"), float("inf"))
        self.max = Vector3D(-float("inf"), -float("inf"), -float("inf"))

    def record(self, coordinate):
        """
        Records the coordinate, storing the min and max values.

        The input vector components must not be None.
        """
        self.min.x = min(self.min.x, coordinate.x)
        self.min.y = min(self.min.y, coordinate.y)
        self.min.z = min(self.min.z, coordinate.z)
        self.max.x = max(self.max.x, coordinate.x)
        self.max.y = max(self.max.y, coordinate.y)
        self.max.z = max(self.max.z, coordinate.z)

    @property
    def size(self):
        result = Vector3D()
        for c in "xyz":
            min = getattr(self.min, c)
            max = getattr(self.max, c)
            value = abs(max - min) if max >= min else 0.0
            setattr(result, c, value)
        return result


class AnalysisAborted(Exception):
    def __init__(self, reenqueue=True, *args, **kwargs):
        self.reenqueue = reenqueue
        Exception.__init__(self, *args, **kwargs)


class gcode(object):
    def __init__(self, progress_callback=None):
        self._logger = logging.getLogger(__name__)
        self.layerList = None
        self.extrusionAmount = [0]
        self.extrusionVolume = [0]
        self.totalMoveTimeMinute = 0
        self.filename = None
        self._abort = False
        self._reenqueue = True
        self._filamentDiameter = 0
        self._minMax = MinMax3D()
        self._progress_callback = progress_callback

    @property
    def dimensions(self):
        size = self._minMax.size
        return {"width": size.x, "depth": size.y, "height": size.z}

    @property
    def printing_area(self):
        return {
            "minX": None if math.isinf(self._minMax.min.x) else self._minMax.min.x,
            "minY": None if math.isinf(self._minMax.min.y) else self._minMax.min.y,
            "minZ": None if math.isinf(self._minMax.min.z) else self._minMax.min.z,
            "maxX": None if math.isinf(self._minMax.max.x) else self._minMax.max.x,
            "maxY": None if math.isinf(self._minMax.max.y) else self._minMax.max.y,
            "maxZ": None if math.isinf(self._minMax.max.z) else self._minMax.max.z,
        }

    def load(
        self,
        filename,
        throttle=None,
        speedx=6000,
        speedy=6000,
        offsets=None,
        max_extruders=10,
        g90_extruder=False,
    ):
        if os.path.isfile(filename):
            self.filename = filename
            self._fileSize = os.stat(filename).st_size

            with codecs.open(filename, encoding="utf-8", errors="replace") as f:
                self._load(
                    f,
                    throttle=throttle,
                    speedx=speedx,
                    speedy=speedy,
                    offsets=offsets,
                    max_extruders=max_extruders,
                    g90_extruder=g90_extruder,
                )

    def abort(self, reenqueue=True):
        self._abort = True
        self._reenqueue = reenqueue

    def _load(
        self,
        gcodeFile,
        throttle=None,
        speedx=6000,
        speedy=6000,
        offsets=None,
        max_extruders=10,
        g90_extruder=False,
    ):
        lineNo = 0
        readBytes = 0
        pos = Vector3D(0.0, 0.0, 0.0)
        currentE = [0.0]
        totalExtrusion = [0.0]
        maxExtrusion = [0.0]
        currentExtruder = 0
        totalMoveTimeMinute = 0.0
        relativeE = False
        relativeMode = False
        duplicationMode = False
        scale = 1.0
        fwretractTime = 0
        fwretractDist = 0
        fwrecoverTime = 0
        feedrate = min(speedx, speedy)
        if feedrate == 0:
            # some somewhat sane default if axes speeds are insane...
            feedrate = 2000

        if offsets is None or not isinstance(offsets, (list, tuple)):
            offsets = []
        if len(offsets) < max_extruders:
            offsets += [(0, 0)] * (max_extruders - len(offsets))

        for line in gcodeFile:
            if self._abort:
                raise AnalysisAborted(reenqueue=self._reenqueue)
            lineNo += 1
            readBytes += len(line.encode("utf-8"))

            if isinstance(gcodeFile, (io.IOBase, codecs.StreamReaderWriter)):
                percentage = float(readBytes) / float(self._fileSize)
            elif isinstance(gcodeFile, (list)):
                percentage = float(lineNo) / float(len(gcodeFile))
            else:
                percentage = None

            try:
                if (
                    self._progress_callback is not None
                    and (lineNo % 1000 == 0)
                    and percentage is not None
                ):
                    self._progress_callback(percentage)
            except Exception as exc:
                self._logger.debug(
                    "Progress callback %r error: %s", self._progress_callback, exc
                )

            if ";" in line:
                comment = line[line.find(";") + 1 :].strip()
                if comment.startswith("filament_diameter"):
                    # Slic3r
                    filamentValue = comment.split("=", 1)[1].strip()
                    try:
                        self._filamentDiameter = float(filamentValue)
                    except ValueError:
                        try:
                            self._filamentDiameter = float(
                                filamentValue.split(",")[0].strip()
                            )
                        except ValueError:
                            self._filamentDiameter = 0.0
                elif comment.startswith("CURA_PROFILE_STRING") or comment.startswith(
                    "CURA_OCTO_PROFILE_STRING"
                ):
                    # Cura 15.04.* & OctoPrint Cura plugin
                    if comment.startswith("CURA_PROFILE_STRING"):
                        prefix = "CURA_PROFILE_STRING:"
                    else:
                        prefix = "CURA_OCTO_PROFILE_STRING:"

                    curaOptions = self._parseCuraProfileString(comment, prefix)
                    if "filament_diameter" in curaOptions:
                        try:
                            self._filamentDiameter = float(
                                curaOptions["filament_diameter"]
                            )
                        except ValueError:
                            self._filamentDiameter = 0.0
                elif comment.startswith("filamentDiameter,"):
                    # Simplify3D
                    filamentValue = comment.split(",", 1)[1].strip()
                    try:
                        self._filamentDiameter = float(filamentValue)
                    except ValueError:
                        self._filamentDiameter = 0.0
                line = line[0 : line.find(";")]

            G = getCodeInt(line, "G")
            M = getCodeInt(line, "M")
            T = getCodeInt(line, "T")

            if G is not None:
                if G == 0 or G == 1:  # Move
                    x = getCodeFloat(line, "X")
                    y = getCodeFloat(line, "Y")
                    z = getCodeFloat(line, "Z")
                    e = getCodeFloat(line, "E")
                    f = getCodeFloat(line, "F")

                    if x is not None or y is not None or z is not None:
                        # this is a move
                        move = True
                    else:
                        # print head stays on position
                        move = False

                    oldPos = pos

                    # Use new coordinates if provided. If not provided, use prior coordinates (minus tool offset)
                    # in absolute and 0.0 in relative mode.
                    newPos = Vector3D(
                        x if x is not None else (0.0 if relativeMode else pos.x),
                        y if y is not None else (0.0 if relativeMode else pos.y),
                        z if z is not None else (0.0 if relativeMode else pos.z),
                    )

                    if relativeMode:
                        # Relative mode: scale and add to current position
                        pos += newPos * scale
                    else:
                        # Absolute mode: scale coordinates and apply tool offsets
                        pos = newPos * scale

                    if f is not None and f != 0:
                        feedrate = f

                    if e is not None:
                        if relativeMode or relativeE:
                            # e is already relative, nothing to do
                            pass
                        else:
                            e -= currentE[currentExtruder]

                        # If move with extrusion, calculate new min/max coordinates of model
                        if e > 0.0 and move:
                            # extrusion and move -> oldPos & pos relevant for print area & dimensions
                            self._minMax.record(oldPos)
                            self._minMax.record(pos)

                        totalExtrusion[currentExtruder] += e
                        currentE[currentExtruder] += e
                        maxExtrusion[currentExtruder] = max(
                            maxExtrusion[currentExtruder], totalExtrusion[currentExtruder]
                        )

                        if currentExtruder == 0 and len(currentE) > 1 and duplicationMode:
                            # Copy first extruder length to other extruders
                            for i in range(1, len(currentE)):
                                totalExtrusion[i] += e
                                currentE[i] += e
                                maxExtrusion[i] = max(maxExtrusion[i], totalExtrusion[i])
                    else:
                        e = 0.0

                    # move time in x, y, z, will be 0 if no movement happened
                    moveTimeXYZ = abs((oldPos - pos).length / feedrate)

                    # time needed for extruding, will be 0 if no extrusion happened
                    extrudeTime = abs(e / feedrate)

                    # time to add is maximum of both
                    totalMoveTimeMinute += max(moveTimeXYZ, extrudeTime)

                elif G == 4:  # Delay
                    S = getCodeFloat(line, "S")
                    if S is not None:
                        totalMoveTimeMinute += S / 60.0
                    P = getCodeFloat(line, "P")
                    if P is not None:
                        totalMoveTimeMinute += P / 60.0 / 1000.0
                elif G == 10:  # Firmware retract
                    totalMoveTimeMinute += fwretractTime
                elif G == 11:  # Firmware retract recover
                    totalMoveTimeMinute += fwrecoverTime
                elif G == 20:  # Units are inches
                    scale = 25.4
                elif G == 21:  # Units are mm
                    scale = 1.0
                elif G == 28:  # Home
                    x = getCodeFloat(line, "X")
                    y = getCodeFloat(line, "Y")
                    z = getCodeFloat(line, "Z")
                    center = Vector3D(0.0, 0.0, 0.0)
                    if x is None and y is None and z is None:
                        pos = center
                    else:
                        pos = Vector3D(pos)
                        if x is not None:
                            pos.x = center.x
                        if y is not None:
                            pos.y = center.y
                        if z is not None:
                            pos.z = center.z
                elif G == 90:  # Absolute position
                    relativeMode = False
                    if g90_extruder:
                        relativeE = False
                elif G == 91:  # Relative position
                    relativeMode = True
                    if g90_extruder:
                        relativeE = True
                elif G == 92:
                    x = getCodeFloat(line, "X")
                    y = getCodeFloat(line, "Y")
                    z = getCodeFloat(line, "Z")
                    e = getCodeFloat(line, "E")

                    if e is None and x is None and y is None and z is None:
                        # no parameters, set all axis to 0
                        currentE[currentExtruder] = 0.0
                        pos.x = 0.0
                        pos.y = 0.0
                        pos.z = 0.0
                    else:
                        # some parameters set, only set provided axes
                        if e is not None:
                            currentE[currentExtruder] = e
                        if x is not None:
                            pos.x = x
                        if y is not None:
                            pos.y = y
                        if z is not None:
                            pos.z = z

            elif M is not None:
                if M == 82:  # Absolute E
                    relativeE = False
                elif M == 83:  # Relative E
                    relativeE = True
                elif M == 207 or M == 208:  # Firmware retract settings
                    s = getCodeFloat(line, "S")
                    f = getCodeFloat(line, "F")
                    if s is not None and f is not None:
                        if M == 207:
                            fwretractTime = s / f
                            fwretractDist = s
                        else:
                            fwrecoverTime = (fwretractDist + s) / f
                elif M == 605:  # Duplication/Mirroring mode
                    s = getCodeInt(line, "S")
                    if s in [2, 4, 5, 6]:
                        # Duplication / Mirroring mode selected. Printer firmware copies extrusion commands
                        # from first extruder to all other extruders
                        duplicationMode = True
                    else:
                        duplicationMode = False

            elif T is not None:
                if T > max_extruders:
                    self._logger.warning(
                        "GCODE tried to select tool %d, that looks wrong, ignoring for GCODE analysis"
                        % T
                    )
                elif T == currentExtruder:
                    pass
                else:
                    pos.x -= (
                        offsets[currentExtruder][0]
                        if currentExtruder < len(offsets)
                        else 0
                    )
                    pos.y -= (
                        offsets[currentExtruder][1]
                        if currentExtruder < len(offsets)
                        else 0
                    )

                    currentExtruder = T

                    pos.x += (
                        offsets[currentExtruder][0]
                        if currentExtruder < len(offsets)
                        else 0
                    )
                    pos.y += (
                        offsets[currentExtruder][1]
                        if currentExtruder < len(offsets)
                        else 0
                    )

                    if len(currentE) <= currentExtruder:
                        for _ in range(len(currentE), currentExtruder + 1):
                            currentE.append(0.0)
                    if len(maxExtrusion) <= currentExtruder:
                        for _ in range(len(maxExtrusion), currentExtruder + 1):
                            maxExtrusion.append(0.0)
                    if len(totalExtrusion) <= currentExtruder:
                        for _ in range(len(totalExtrusion), currentExtruder + 1):
                            totalExtrusion.append(0.0)

            if throttle is not None:
                throttle(lineNo, readBytes)
        if self._progress_callback is not None:
            self._progress_callback(100.0)

        self.extrusionAmount = maxExtrusion
        self.extrusionVolume = [0] * len(maxExtrusion)
        for i in range(len(maxExtrusion)):
            radius = self._filamentDiameter / 2
            self.extrusionVolume[i] = (
                self.extrusionAmount[i] * (math.pi * radius * radius)
            ) / 1000
        self.totalMoveTimeMinute = totalMoveTimeMinute

    def _parseCuraProfileString(self, comment, prefix):
        return {
            key: value
            for (key, value) in map(
                lambda x: x.split(b"=", 1),
                zlib.decompress(base64.b64decode(comment[len(prefix) :])).split(b"\b"),
            )
        }

    def get_result(self):
        return {
            "total_time": self.totalMoveTimeMinute,
            "extrusion_length": self.extrusionAmount,
            "extrusion_volume": self.extrusionVolume,
            "dimensions": self.dimensions,
            "printing_area": self.printing_area,
        }


def getCodeInt(line, code):
    return getCode(line, code, int)


def getCodeFloat(line, code):
    return getCode(line, code, float)


def getCode(line, code, c):
    n = line.find(code) + 1
    if n < 1:
        return None
    m = line.find(" ", n)
    try:
        if m < 0:
            result = c(line[n:])
        else:
            result = c(line[n:m])
    except ValueError:
        return None

    if math.isnan(result) or math.isinf(result):
        return None

    return result
