__author__ = "Gina Häußge <osd@foosel.net> based on work by David Braam"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2013 David Braam, Gina Häußge - Released under terms of the AGPLv3 License"


import base64
import codecs
import io
import logging
import math
import os
import re
import zlib


class Vector3D:
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


class MinMax3D:
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
    >>> weird = MinMax3D(min_z=-1.0)
    >>> weird.record(Vector3D(2.0, 2.0, 2.0))
    >>> weird.record(Vector3D(1.0, 2.0, 3.0))
    >>> weird.min.z == -1.0
    True
    >>> weird.size == Vector3D(1.0, 0.0, 4.0)
    True
    """

    def __init__(
        self,
        min_x=None,
        min_y=None,
        min_z=None,
        max_x=None,
        max_y=None,
        max_z=None,
    ):
        min_x = min_x if min_x is not None else float("inf")
        min_y = min_y if min_y is not None else float("inf")
        min_z = min_z if min_z is not None else float("inf")
        max_x = max_x if max_x is not None else -float("inf")
        max_y = max_y if max_y is not None else -float("inf")
        max_z = max_z if max_z is not None else -float("inf")

        self.min = Vector3D(min_x, min_y, min_z)
        self.max = Vector3D(max_x, max_y, max_z)

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


regex_command = re.compile(
    r"^\s*((?P<codeGM>[GM]\d+)(\.(?P<subcode>\d+))?|(?P<codeT>T)(?P<tool>\d+))"
)
"""Regex for a GCODE command."""


class gcode:
    def __init__(self, incl_layers=False, progress_callback=None):
        self._logger = logging.getLogger(__name__)
        self.extrusionAmount = [0]
        self.extrusionVolume = [0]
        self.totalMoveTimeMinute = 0
        self.filename = None
        self._abort = False
        self._reenqueue = True
        self._filamentDiameter = 0
        self._minMax = MinMax3D()
        self._progress_callback = progress_callback

        self._incl_layers = incl_layers
        self._layers = []
        self._current_layer = None

    def _track_layer(self, pos, arc=None):
        if not self._incl_layers:
            return

        if self._current_layer is None or self._current_layer["z"] != pos.z:
            self._current_layer = {"z": pos.z, "minmax": MinMax3D(), "commands": 1}
            self._layers.append(self._current_layer)

        elif self._current_layer:
            self._current_layer["minmax"].record(pos)
            if arc is not None:
                self._addArcMinMax(
                    self._current_layer["minmax"],
                    arc["startAngle"],
                    arc["endAngle"],
                    arc["center"],
                    arc["radius"],
                )

    def _track_command(self):
        if self._current_layer:
            self._current_layer["commands"] += 1

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

    @property
    def layers(self):
        return [
            {
                "num": num + 1,
                "z": layer["z"],
                "commands": layer["commands"],
                "bounds": {
                    "minX": layer["minmax"].min.x,
                    "maxX": layer["minmax"].max.x,
                    "minY": layer["minmax"].min.y,
                    "maxY": layer["minmax"].max.y,
                },
            }
            for num, layer in enumerate(self._layers)
        ]

    def load(
        self,
        filename,
        throttle=None,
        speedx=6000,
        speedy=6000,
        offsets=None,
        max_extruders=10,
        g90_extruder=False,
        bed_z=0.0,
    ):
        self._minMax.min.z = bed_z
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
                percentage = readBytes / self._fileSize
            elif isinstance(gcodeFile, (list)):
                percentage = lineNo / len(gcodeFile)
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

            match = regex_command.search(line)
            gcode = tool = None
            if match:
                values = match.groupdict()
                if "codeGM" in values and values["codeGM"]:
                    gcode = values["codeGM"]
                elif "codeT" in values and values["codeT"]:
                    gcode = values["codeT"]
                    tool = int(values["tool"])

            # G codes
            if gcode in ("G0", "G1", "G00", "G01"):  # Move
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
                    x * scale if x is not None else (0.0 if relativeMode else pos.x),
                    y * scale if y is not None else (0.0 if relativeMode else pos.y),
                    z * scale if z is not None else (0.0 if relativeMode else pos.z),
                )

                if relativeMode:
                    # Relative mode: add to current position
                    pos += newPos
                else:
                    # Absolute mode: apply tool offsets
                    pos = newPos

                if f is not None and f != 0:
                    feedrate = f

                if e is not None:
                    if relativeMode or relativeE:
                        # e is already relative, nothing to do
                        pass
                    else:
                        e -= currentE[currentExtruder]

                    # If move with extrusion, calculate new min/max coordinates of model
                    if e > 0 and move:
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
                    e = 0

                # move time in x, y, z, will be 0 if no movement happened
                moveTimeXYZ = abs((oldPos - pos).length / feedrate)

                # time needed for extruding, will be 0 if no extrusion happened
                extrudeTime = abs(e / feedrate)

                # time to add is maximum of both
                totalMoveTimeMinute += max(moveTimeXYZ, extrudeTime)

                # process layers if there's extrusion
                if e:
                    self._track_layer(pos)

            if gcode in ("G2", "G3", "G02", "G03"):  # Arc Move
                x = getCodeFloat(line, "X")
                y = getCodeFloat(line, "Y")
                z = getCodeFloat(line, "Z")
                e = getCodeFloat(line, "E")
                i = getCodeFloat(line, "I")
                j = getCodeFloat(line, "J")
                r = getCodeFloat(line, "R")
                f = getCodeFloat(line, "F")

                # this is a move or print head stays on position
                move = (
                    x is not None
                    or y is not None
                    or z is not None
                    or i is not None
                    or j is not None
                    or r is not None
                )

                oldPos = pos

                # Use new coordinates if provided. If not provided, use prior coordinates (minus tool offset)
                # in absolute and 0.0 in relative mode.
                newPos = Vector3D(
                    x * scale if x is not None else (0.0 if relativeMode else pos.x),
                    y * scale if y is not None else (0.0 if relativeMode else pos.y),
                    z * scale if z is not None else (0.0 if relativeMode else pos.z),
                )

                if relativeMode:
                    # Relative mode: add to current position
                    pos += newPos
                else:
                    # Absolute mode: apply tool offsets
                    pos = newPos

                if f is not None and f != 0:
                    feedrate = f

                # get radius and offset
                i = 0 if i is None else i
                j = 0 if j is None else j
                r = math.sqrt(i * i + j * j) if r is None else r

                # calculate angles
                centerArc = Vector3D(oldPos.x + i, oldPos.y + j, oldPos.z)
                startAngle = math.atan2(oldPos.y - centerArc.y, oldPos.x - centerArc.x)
                endAngle = math.atan2(pos.y - centerArc.y, pos.x - centerArc.x)

                if gcode == "G2":
                    startAngle, endAngle = endAngle, startAngle
                if startAngle < 0:
                    startAngle += math.pi * 2
                if endAngle < 0:
                    endAngle += math.pi * 2

                # from now on we only think in counter-clockwise direction

                if e is not None:
                    if relativeMode or relativeE:
                        # e is already relative, nothing to do
                        pass
                    else:
                        e -= currentE[currentExtruder]

                    # If move with extrusion, calculate new min/max coordinates of model
                    if e > 0 and move:
                        # extrusion and move -> oldPos & pos relevant for print area & dimensions
                        self._minMax.record(oldPos)
                        self._minMax.record(pos)
                        self._addArcMinMax(
                            self._minMax, startAngle, endAngle, centerArc, r
                        )

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
                    e = 0

                # move time in x, y, z, will be 0 if no movement happened
                moveTimeXYZ = abs((oldPos - pos).length / feedrate)

                # time needed for extruding, will be 0 if no extrusion happened
                extrudeTime = abs(e / feedrate)

                # time to add is maximum of both
                totalMoveTimeMinute += max(moveTimeXYZ, extrudeTime)

                # process layers if there's extrusion
                if e:
                    self._track_layer(
                        pos,
                        {
                            "startAngle": startAngle,
                            "endAngle": endAngle,
                            "center": centerArc,
                            "radius": r,
                        },
                    )

            elif gcode == "G4":  # Delay
                S = getCodeFloat(line, "S")
                if S is not None:
                    totalMoveTimeMinute += S / 60
                P = getCodeFloat(line, "P")
                if P is not None:
                    totalMoveTimeMinute += P / 60 / 1000
            elif gcode == "G10":  # Firmware retract
                totalMoveTimeMinute += fwretractTime
            elif gcode == "G11":  # Firmware retract recover
                totalMoveTimeMinute += fwrecoverTime
            elif gcode == "G20":  # Units are inches
                scale = 25.4
            elif gcode == "G21":  # Units are mm
                scale = 1.0
            elif gcode == "G28":  # Home
                x = getCodeFloat(line, "X")
                y = getCodeFloat(line, "Y")
                z = getCodeFloat(line, "Z")
                origin = Vector3D(0.0, 0.0, 0.0)
                if x is None and y is None and z is None:
                    pos = origin
                else:
                    pos = Vector3D(pos)
                    if x is not None:
                        pos.x = origin.x
                    if y is not None:
                        pos.y = origin.y
                    if z is not None:
                        pos.z = origin.z
            elif gcode == "G90":  # Absolute position
                relativeMode = False
                if g90_extruder:
                    relativeE = False
            elif gcode == "G91":  # Relative position
                relativeMode = True
                if g90_extruder:
                    relativeE = True
            elif gcode == "G92":
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
            # M codes
            elif gcode == "M82":  # Absolute E
                relativeE = False
            elif gcode == "M83":  # Relative E
                relativeE = True
            elif gcode in ("M207", "M208"):  # Firmware retract settings
                s = getCodeFloat(line, "S")
                f = getCodeFloat(line, "F")
                if s is not None and f is not None:
                    if gcode == "M207":
                        fwretractTime = s / f
                        fwretractDist = s
                    else:
                        fwrecoverTime = (fwretractDist + s) / f
            elif gcode == "M605":  # Duplication/Mirroring mode
                s = getCodeInt(line, "S")
                if s in [2, 4, 5, 6]:
                    # Duplication / Mirroring mode selected. Printer firmware copies extrusion commands
                    # from first extruder to all other extruders
                    duplicationMode = True
                else:
                    duplicationMode = False

            # T codes
            elif tool is not None:
                if tool > max_extruders:
                    self._logger.warning(
                        "GCODE tried to select tool %d, that looks wrong, ignoring for GCODE analysis"
                        % tool
                    )
                elif tool == currentExtruder:
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

                    currentExtruder = tool

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

            if gcode or tool:
                self._track_command()

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

    def _intersectsAngle(self, start, end, angle):
        if end < start and angle == 0:
            # angle crosses 0 degrees
            return True
        else:
            return start <= angle <= end

    def _addArcMinMax(self, minmax, startAngle, endAngle, centerArc, radius):
        startDeg = math.degrees(startAngle)
        endDeg = math.degrees(endAngle)

        if self._intersectsAngle(startDeg, endDeg, 0):
            # arc crosses positive x
            minmax.max.x = max(minmax.max.x, centerArc.x + radius)
        if self._intersectsAngle(startDeg, endDeg, 90):
            # arc crosses positive y
            minmax.max.y = max(minmax.max.y, centerArc.y + radius)
        if self._intersectsAngle(startDeg, endDeg, 180):
            # arc crosses negative x
            minmax.min.x = min(minmax.min.x, centerArc.x - radius)
        if self._intersectsAngle(startDeg, endDeg, 270):
            # arc crosses negative y
            minmax.min.y = min(minmax.min.y, centerArc.y - radius)

    def get_result(self):
        result = {
            "total_time": self.totalMoveTimeMinute,
            "extrusion_length": self.extrusionAmount,
            "extrusion_volume": self.extrusionVolume,
            "dimensions": self.dimensions,
            "printing_area": self.printing_area,
        }
        if self._incl_layers:
            result["layers"] = self.layers

        return result


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
