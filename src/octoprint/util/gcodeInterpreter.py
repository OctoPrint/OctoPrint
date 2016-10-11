# coding=utf-8
from __future__ import absolute_import, division, print_function
__author__ = "Gina Häußge <osd@foosel.net> based on work by David Braam"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2013 David Braam, Gina Häußge - Released under terms of the AGPLv3 License"


import math
import os
import base64
import zlib
import logging

from octoprint.settings import settings


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

	def __init__(self, *args, **kwargs):
		self.x = kwargs.get("x", 0.0)
		self.y = kwargs.get("y", 0.0)
		self.z = kwargs.get("z", 0.0)

		if len(args) == 3:
			self.x = args[0]
			self.y = args[1]
			self.z = args[2]

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
		if isinstance(other, Vector3D):
			return Vector3D(self.x + other.x,
			                self.y + other.y,
			                self.z + other.z)
		elif isinstance(other, (tuple, list)) and len(other) == 3:
			return Vector3D(self.x + other[0],
			                self.y + other[1],
			                self.z + other[2])
		else:
			raise ValueError("other must be a Vector3D instance or a list or tuple of length 3")

	def __sub__(self, other):
		if isinstance(other, Vector3D):
			return Vector3D(self.x - other.x,
			                self.y - other.y,
			                self.z - other.z)
		elif isinstance(other, (tuple, list)) and len(other) == 3:
			return Vector3D(self.x - other[0],
			                self.y - other[1],
			                self.z - other[2])
		else:
			raise ValueError("other must be a Vector3D instance or a list or tuple")

	def __mul__(self, other):
		if isinstance(other, (int, float)):
			return Vector3D(self.x * other,
			                self.y * other,
			                self.z * other)
		else:
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
		return "Vector3D(x={}, y={}, z={}, length={})".format(self.x, self.y, self.z, self.length)


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
	>>> partial = MinMax3D()
	>>> partial.record(Vector3D(2.0, None, 2.0))
	>>> partial.min.x == 2.0 == partial.max.x and partial.min.y == None == partial.max.y and partial.min.z == 2.0 == partial.max.z
	True
	>>> partial.record(Vector3D(1.0, None, 3.0))
	>>> partial.min.x == 1.0 and partial.min.y == None and partial.min.z == 2.0
	True
	>>> partial.max.x == 2.0 and partial.max.y == None and partial.max.z == 3.0
	True
	>>> partial.size == Vector3D(1.0, 0.0, 1.0)
	True
	"""

	def __init__(self):
		self.min = Vector3D(None, None, None)
		self.max = Vector3D(None, None, None)

	def record(self, coordinate):
		for c in "xyz":
			current_min = getattr(self.min, c)
			current_max = getattr(self.max, c)
			value = getattr(coordinate, c)
			setattr(self.min, c, value if current_min is None or value < current_min else current_min)
			setattr(self.max, c, value if current_max is None or value > current_max else current_max)

	@property
	def size(self):
		result = Vector3D()
		for c in "xyz":
			min = getattr(self.min, c)
			max = getattr(self.max, c)
			value = abs(max - min) if min is not None and max is not None else 0.0
			setattr(result, c, value)
		return result


class AnalysisAborted(Exception):
	pass


class gcode(object):
	def __init__(self):
		self._logger = logging.getLogger(__name__)
		self.layerList = None
		self.extrusionAmount = [0]
		self.extrusionVolume = [0]
		self.totalMoveTimeMinute = 0
		self.filename = None
		self.progressCallback = None
		self._abort = False
		self._filamentDiameter = 0
		self._minMax = MinMax3D()

	@property
	def dimensions(self):
		size = self._minMax.size
		return dict(width=size.x,
		            depth=size.y,
		            height=size.z)

	@property
	def printing_area(self):
		return dict(minX=self._minMax.min.x,
		            minY=self._minMax.min.y,
		            minZ=self._minMax.min.z,
		            maxX=self._minMax.max.x,
		            maxY=self._minMax.max.y,
		            maxZ=self._minMax.max.z)

	def load(self, filename, printer_profile, throttle=None):
		if os.path.isfile(filename):
			self.filename = filename
			self._fileSize = os.stat(filename).st_size

			import codecs
			with codecs.open(filename, encoding="utf-8", errors="replace") as f:
				self._load(f, printer_profile, throttle=throttle)

	def abort(self):
		self._abort = True

	def _load(self, gcodeFile, printer_profile, throttle=None):
		filePos = 0
		readBytes = 0
		pos = Vector3D(0.0, 0.0, 0.0)
		posOffset = Vector3D(0.0, 0.0, 0.0)
		currentE = [0.0]
		totalExtrusion = [0.0]
		maxExtrusion = [0.0]
		currentExtruder = 0
		totalMoveTimeMinute = 0.0
		absoluteE = True
		scale = 1.0
		posAbs = True
		fwretractTime = 0
		fwretractDist = 0
		fwrecoverTime = 0
		feedrate = min(printer_profile["axes"]["x"]["speed"], printer_profile["axes"]["y"]["speed"])
		if feedrate == 0:
			# some somewhat sane default if axes speeds are insane...
			feedrate = 2000
		offsets = printer_profile["extruder"]["offsets"]

		for line in gcodeFile:
			if self._abort:
				raise AnalysisAborted()
			filePos += 1
			readBytes += len(line)

			if isinstance(gcodeFile, (file)):
				percentage = float(readBytes) / float(self._fileSize)
			elif isinstance(gcodeFile, (list)):
				percentage = float(filePos) / float(len(gcodeFile))
			else:
				percentage = None

			try:
				if self.progressCallback is not None and (filePos % 1000 == 0) and percentage is not None:
					self.progressCallback(percentage)
			except:
				pass

			if ';' in line:
				comment = line[line.find(';')+1:].strip()
				if comment.startswith("filament_diameter"):
					filamentValue = comment.split("=", 1)[1].strip()
					try:
						self._filamentDiameter = float(filamentValue)
					except ValueError:
						try:
							self._filamentDiameter = float(filamentValue.split(",")[0].strip())
						except ValueError:
							self._filamentDiameter = 0.0
				elif comment.startswith("CURA_PROFILE_STRING") or comment.startswith("CURA_OCTO_PROFILE_STRING"):
					if comment.startswith("CURA_PROFILE_STRING"):
						prefix = "CURA_PROFILE_STRING:"
					else:
						prefix = "CURA_OCTO_PROFILE_STRING:"

					curaOptions = self._parseCuraProfileString(comment, prefix)
					if "filament_diameter" in curaOptions:
						try:
							self._filamentDiameter = float(curaOptions["filament_diameter"])
						except:
							self._filamentDiameter = 0.0
				line = line[0:line.find(';')]

			G = getCodeInt(line, 'G')
			M = getCodeInt(line, 'M')
			T = getCodeInt(line, 'T')

			if G is not None:
				if G == 0 or G == 1:	#Move
					x = getCodeFloat(line, 'X')
					y = getCodeFloat(line, 'Y')
					z = getCodeFloat(line, 'Z')
					e = getCodeFloat(line, 'E')
					f = getCodeFloat(line, 'F')

					oldPos = pos
					newPos = Vector3D(x if x is not None else pos.x,
					                  y if y is not None else pos.y,
					                  z if z is not None else pos.z)

					if posAbs:
						pos = newPos * scale + posOffset
					else:
						pos += newPos * scale
					if f is not None and f != 0:
						feedrate = f

					if e is not None:
						if absoluteE:
							# make sure e is relative
							e -= currentE[currentExtruder]
						# If move includes extrusion, calculate new min/max coordinates of model
						if e > 0.0:
							# extrusion -> relevant for print area & dimensions
							self._minMax.record(pos)
						totalExtrusion[currentExtruder] += e
						currentE[currentExtruder] += e
						maxExtrusion[currentExtruder] = max(maxExtrusion[currentExtruder],
						                                    totalExtrusion[currentExtruder])
					else:
						e = 0.0

					# move time in x, y, z, will be 0 if no movement happened
					moveTimeXYZ = abs((oldPos - pos).length / feedrate)

					# time needed for extruding, will be 0 if no extrusion happened
					extrudeTime = abs(e / feedrate)

					# time to add is maximum of both
					totalMoveTimeMinute += max(moveTimeXYZ, extrudeTime)

				elif G == 4:	#Delay
					S = getCodeFloat(line, 'S')
					if S is not None:
						totalMoveTimeMinute += S / 60.0
					P = getCodeFloat(line, 'P')
					if P is not None:
						totalMoveTimeMinute += P / 60.0 / 1000.0
				elif G == 10:   #Firmware retract
					totalMoveTimeMinute += fwretractTime
				elif G == 11:   #Firmware retract recover
					totalMoveTimeMinute += fwrecoverTime
				elif G == 20:	#Units are inches
					scale = 25.4
				elif G == 21:	#Units are mm
					scale = 1.0
				elif G == 28:	#Home
					x = getCodeFloat(line, 'X')
					y = getCodeFloat(line, 'Y')
					z = getCodeFloat(line, 'Z')
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
				elif G == 90:	#Absolute position
					posAbs = True
				elif G == 91:	#Relative position
					posAbs = False
				elif G == 92:
					x = getCodeFloat(line, 'X')
					y = getCodeFloat(line, 'Y')
					z = getCodeFloat(line, 'Z')
					e = getCodeFloat(line, 'E')
					if e is not None:
						currentE[currentExtruder] = e
					if x is not None:
						posOffset.x = pos.x - x
					if y is not None:
						posOffset.y = pos.y - y
					if z is not None:
						posOffset.z = pos.z - z

			elif M is not None:
				if M == 82:   #Absolute E
					absoluteE = True
				elif M == 83:   #Relative E
					absoluteE = False
				elif M == 207 or M == 208: #Firmware retract settings
					s = getCodeFloat(line, 'S')
					f = getCodeFloat(line, 'F')
					if s is not None and f is not None:
						if M == 207:
							fwretractTime = s / f
							fwretractDist = s
						else:
							fwrecoverTime = (fwretractDist + s) / f

			elif T is not None:
				if T > settings().getInt(["gcodeAnalysis", "maxExtruders"]):
					self._logger.warn("GCODE tried to select tool %d, that looks wrong, ignoring for GCODE analysis" % T)
				else:
					posOffset.x -= offsets[currentExtruder][0] if currentExtruder < len(offsets) else 0
					posOffset.y -= offsets[currentExtruder][1] if currentExtruder < len(offsets) else 0

					currentExtruder = T

					posOffset.x += offsets[currentExtruder][0] if currentExtruder < len(offsets) else 0
					posOffset.y += offsets[currentExtruder][1] if currentExtruder < len(offsets) else 0

					if len(currentE) <= currentExtruder:
						for i in range(len(currentE), currentExtruder + 1):
							currentE.append(0.0)
					if len(maxExtrusion) <= currentExtruder:
						for i in range(len(maxExtrusion), currentExtruder + 1):
							maxExtrusion.append(0.0)
					if len(totalExtrusion) <= currentExtruder:
						for i in range(len(totalExtrusion), currentExtruder + 1):
							totalExtrusion.append(0.0)

			if throttle is not None:
				throttle()

		if self.progressCallback is not None:
			self.progressCallback(100.0)

		self.extrusionAmount = maxExtrusion
		self.extrusionVolume = [0] * len(maxExtrusion)
		for i in range(len(maxExtrusion)):
			radius = self._filamentDiameter / 2
			self.extrusionVolume[i] = (self.extrusionAmount[i] * (math.pi * radius * radius)) / 1000
		self.totalMoveTimeMinute = totalMoveTimeMinute

	def _parseCuraProfileString(self, comment, prefix):
		return {key: value for (key, value) in map(lambda x: x.split("=", 1), zlib.decompress(base64.b64decode(comment[len(prefix):])).split("\b"))}

def getCodeInt(line, code):
	n = line.find(code) + 1
	if n < 1:
		return None
	m = line.find(' ', n)
	try:
		if m < 0:
			return int(line[n:])
		return int(line[n:m])
	except:
		return None


def getCodeFloat(line, code):
	import math
	n = line.find(code) + 1
	if n < 1:
		return None
	m = line.find(' ', n)
	try:
		if m < 0:
			val = float(line[n:])
		else:
			val = float(line[n:m])
		return val if not (math.isnan(val) or math.isinf(val)) else None
	except:
		return None
