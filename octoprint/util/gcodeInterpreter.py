from __future__ import absolute_import
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import math
import os
import base64
import zlib
import logging

from octoprint.settings import settings

preferences = {
	"extruder_offset_x1": -22.0,
	"extruder_offset_y1": 0.0,
	"extruder_offset_x2": 0.0,
	"extruder_offset_y2": 0.0,
	"extruder_offset_x3": 0.0,
	"extruder_offset_y3": 0.0,
}

def getPreference(key, default=None):
	if preferences.has_key(key):
		return preferences[key]
	else:
		return default

class AnalysisAborted(Exception):
	pass

class gcode(object):
	def __init__(self):
		self._logger = logging.getLogger(__name__)

		self.layerList = None
		self.extrusionAmount = 0
		self.totalMoveTimeMinute = 0
		self.filename = None
		self.progressCallback = None
		self._abort = False
		self._filamentDiameter = 0
	
	def load(self, filename):
		if os.path.isfile(filename):
			self.filename = filename
			self._fileSize = os.stat(filename).st_size
			with open(filename, "r") as f:
				self._load(f)

	def abort(self):
		self._abort = True

	def calculateVolumeCm3(self):
		radius = self._filamentDiameter / 2
		return (self.extrusionAmount * (math.pi * radius * radius)) / 1000
			
	def _load(self, gcodeFile):
		filePos = 0
		pos = [0.0, 0.0, 0.0]
		posOffset = [0.0, 0.0, 0.0]
		currentE = 0.0
		totalExtrusion = 0.0
		maxExtrusion = 0.0
		currentExtruder = 0
		totalMoveTimeMinute = 0.0
		absoluteE = True
		scale = 1.0
		posAbs = True
		feedRateXY = settings().getFloat(["printerParameters", "movementSpeed", "x"])

		for line in gcodeFile:
			if self._abort:
				raise AnalysisAborted()
			filePos += 1

			try:
				if self.progressCallback is not None and (filePos % 1000 == 0):
					if isinstance(gcodeFile, (file)):
						self.progressCallback(float(gcodeFile.tell()) / float(self._fileSize))
					elif isinstance(gcodeFile, (list)):
						self.progressCallback(float(filePos) / float(len(gcodeFile)))
			except:
				pass

			if ';' in line:
				comment = line[line.find(';')+1:].strip()
				if comment.startswith("filament_diameter"):
					self._filamentDiameter = float(comment.split("=", 1)[1].strip())
				elif comment.startswith("CURA_PROFILE_STRING"):
					curaOptions = self._parseCuraProfileString(comment)
					if "filament_diameter" in curaOptions:
						try:
							self._filamentDiameter = float(curaOptions["filament_diameter"])
						except:
							self._filamentDiameter = 0.0
				line = line[0:line.find(';')]

			T = getCodeInt(line, 'T')
			if T is not None:
				if currentExtruder > 0:
					posOffset[0] -= getPreference('extruder_offset_x%d' % (currentExtruder), 0.0)
					posOffset[1] -= getPreference('extruder_offset_y%d' % (currentExtruder), 0.0)
				currentExtruder = T
				if currentExtruder > 0:
					posOffset[0] += getPreference('extruder_offset_x%d' % (currentExtruder), 0.0)
					posOffset[1] += getPreference('extruder_offset_y%d' % (currentExtruder), 0.0)
			
			G = getCodeInt(line, 'G')
			if G is not None:
				if G == 0 or G == 1:	#Move
					x = getCodeFloat(line, 'X')
					y = getCodeFloat(line, 'Y')
					z = getCodeFloat(line, 'Z')
					e = getCodeFloat(line, 'E')
					f = getCodeFloat(line, 'F')
					oldPos = pos
					pos = pos[:]
					if posAbs:
						if x is not None:
							pos[0] = x * scale + posOffset[0]
						if y is not None:
							pos[1] = y * scale + posOffset[1]
						if z is not None:
							pos[2] = z * scale + posOffset[2]
					else:
						if x is not None:
							pos[0] += x * scale
						if y is not None:
							pos[1] += y * scale
						if z is not None:
							pos[2] += z * scale
					if f is not None:
						feedRateXY = f
					if x is not None or y is not None or z is not None:
						diffX = oldPos[0] - pos[0]
						diffY = oldPos[1] - pos[1]
						totalMoveTimeMinute += math.sqrt(diffX * diffX + diffY * diffY) / feedRateXY
					moveType = 'move'
					if e is not None:
						if absoluteE:
							e -= currentE
						if e > 0.0:
							moveType = 'extrude'
						if e < 0.0:
							moveType = 'retract'
						totalExtrusion += e
						currentE += e
						if totalExtrusion > maxExtrusion:
							maxExtrusion = totalExtrusion
					else:
						e = 0.0
					if moveType == 'move' and oldPos[2] != pos[2]:
						if oldPos[2] > pos[2] and abs(oldPos[2] - pos[2]) > 5.0 and pos[2] < 1.0:
							oldPos[2] = 0.0
				elif G == 4:	#Delay
					S = getCodeFloat(line, 'S')
					if S is not None:
						totalMoveTimeMinute += S / 60.0
					P = getCodeFloat(line, 'P')
					if P is not None:
						totalMoveTimeMinute += P / 60.0 / 1000.0
				elif G == 20:	#Units are inches
					scale = 25.4
				elif G == 21:	#Units are mm
					scale = 1.0
				elif G == 28:	#Home
					x = getCodeFloat(line, 'X')
					y = getCodeFloat(line, 'Y')
					z = getCodeFloat(line, 'Z')
					center = [0.0,0.0,0.0]
					if x is None and y is None and z is None:
						pos = center
					else:
						pos = pos[:]
						if x is not None:
							pos[0] = center[0]
						if y is not None:
							pos[1] = center[1]
						if z is not None:
							pos[2] = center[2]
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
						currentE = e
					if x is not None:
						posOffset[0] = pos[0] - x
					if y is not None:
						posOffset[1] = pos[1] - y
					if z is not None:
						posOffset[2] = pos[2] - z
			else:
				M = getCodeInt(line, 'M')
				if M is not None:
					if M == 82:   #Absolute E
						absoluteE = True
					elif M == 83:   #Relative E
						absoluteE = False
		if self.progressCallback is not None:
			self.progressCallback(100.0)
		self.extrusionAmount = maxExtrusion
		self.totalMoveTimeMinute = totalMoveTimeMinute

	def _parseCuraProfileString(self, comment):
		return {key: value for (key, value) in map(lambda x: x.split("=", 1), zlib.decompress(base64.b64decode(comment[len("CURA_PROFILE_STRING:"):])).split("\b"))}

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
	n = line.find(code) + 1
	if n < 1:
		return None
	m = line.find(' ', n)
	try:
		if m < 0:
			return float(line[n:])
		return float(line[n:m])
	except:
		return None
