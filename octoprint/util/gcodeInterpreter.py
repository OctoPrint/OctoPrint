from __future__ import absolute_import
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import sys
import math
import os
import base64
import zlib
import logging

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

def gcodePath(newType, pathType, layerThickness, startPoint):
	return {'type': newType,
			'pathType': pathType,
			'layerThickness': layerThickness,
			'points': [startPoint],
			'extrusion': [0.0]}

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
			gcodeFile = open(filename, 'r')
			self._load(gcodeFile)
			gcodeFile.close()
	
	def loadList(self, l):
		self.filename = None
		self._load(l)

	def abort(self):
		self._abort = True

	def calculateVolumeCm3(self):
		radius = self._filamentDiameter / 2
		return (self.extrusionAmount * (math.pi * radius * radius)) / 1000
			
	def calculateWeight(self):
		#Calculates the weight of the filament in kg
		volumeM3 = self.calculateVolumeCm3() /(1000*1000)
		return volumeM3 * getPreference('filament_physical_density')
	
	def calculateCost(self):
		cost_kg = getPreference('filament_cost_kg')
		cost_meter = getPreference('filament_cost_meter')
		if cost_kg > 0.0 and cost_meter > 0.0:
			return "%.2f / %.2f" % (self.calculateWeight() * cost_kg, self.extrusionAmount / 1000 * cost_meter)
		elif cost_kg > 0.0:
			return "%.2f" % (self.calculateWeight() * cost_kg)
		elif cost_meter > 0.0:
			return "%.2f" % (self.extrusionAmount / 1000 * cost_meter)
		return None
	
	def _load(self, gcodeFile):
		filePos = 0
		self.layerList = []
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
		feedRate = 3600.0
		unknownGcodes = {}
		unknownMcodes = {}

		for line in gcodeFile:
			if self._abort:
				raise AnalysisAborted()
			if type(line) is tuple:
				line = line[0]
			filePos += 1
			if self.progressCallback is not None and (filePos % 1000 == 0):
				if isinstance(gcodeFile, (file)):
					self.progressCallback(float(gcodeFile.tell()) / float(self._fileSize))
				elif isinstance(gcodeFile, (list)):
					self.progressCallback(float(filePos) / float(len(gcodeFile)))

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
						feedRate = f
					if x is not None or y is not None or z is not None:
						diffX = oldPos[0] - pos[0]
						diffY = oldPos[1] - pos[1]
						totalMoveTimeMinute += math.sqrt(diffX * diffX + diffY * diffY) / feedRate
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
					if getPreference('machine_center_is_zero') == 'True':
						center = [getPreference('machine_width') / 2, getPreference('machine_depth') / 2,0.0]
					else:
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
					if G not in unknownGcodes:
						self._logger.info("Unknown G code: %r" % G)
						unknownGcodes[G] = True
			else:
				M = getCodeInt(line, 'M')
				if M is not None:
					if M == 0:	#Message with possible wait (ignored)
						pass
					elif M == 1:	#Message with possible wait (ignored)
						pass
					elif M == 80:	#Enable power supply
						pass
					elif M == 81:	#Suicide/disable power supply
						pass
					elif M == 82:   #Absolute E
						absoluteE = True
					elif M == 83:   #Relative E
						absoluteE = False
					elif M == 84:	#Disable step drivers
						pass
					elif M == 92:	#Set steps per unit
						pass
					elif M == 101:	#Enable extruder
						pass
					elif M == 103:	#Disable extruder
						pass
					elif M == 104:	#Set temperature, no wait
						pass
					elif M == 105:	#Get temperature
						pass
					elif M == 106:	#Enable fan
						pass
					elif M == 107:	#Disable fan
						pass
					elif M == 108:	#Extruder RPM (these should not be in the final GCode, but they are)
						pass
					elif M == 109:	#Set temperature, wait
						pass
					elif M == 110:	#Reset N counter
						pass
					elif M == 113:	#Extruder PWM (these should not be in the final GCode, but they are)
						pass
					elif M == 117:	#LCD message
						pass
					elif M == 140:	#Set bed temperature
						pass
					elif M == 190:	#Set bed temperature & wait
						pass
					elif M == 221:	#Extrude amount multiplier
						s = getCodeFloat(line, 'S')
					else:
						if M not in unknownMcodes:
							self._logger.info("Unknown M code: %r" % M)
							unknownMcodes[M] = True
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

if __name__ == '__main__':
	from time import time
	t = time()
	for filename in sys.argv[1:]:
		g = gcode()
		g.load(filename)
		print g.totalMoveTimeMinute
		print g.extrusionAmount
		print g.calculateVolumeCm3()
	print time() - t

