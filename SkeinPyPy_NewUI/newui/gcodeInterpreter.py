import sys
import math
import threading
import re

from newui import util3d

class gcode():
	def __init__(self, filename):
		f = open(filename, 'r')
		pos = util3d.Vector3()
		posOffset = util3d.Vector3()
		currentE = 0
		pathList = []
		scale = 1.0
		posAbs = True
		feedRate = 3600
		pathType = 'CUSTOM';
		layerNr = 0;	#Note layer 0 will be the start code.
		startCodeDone = False
		currentPath = {'type': 'move', 'pathType': pathType, 'list': [pos.copy()], 'layerNr': layerNr}
		for line in f:
			if line.startswith(';TYPE:'):
				pathType = line[6:].strip()
				if pathType != "CUSTOM":
					startCodeDone = True
			G = self.getCodeInt(line, 'G')
			if G is not None:
				if G == 0 or G == 1:	#Move
					x = self.getCodeFloat(line, 'X')
					y = self.getCodeFloat(line, 'Y')
					z = self.getCodeFloat(line, 'Z')
					e = self.getCodeFloat(line, 'E')
					f = self.getCodeFloat(line, 'F')
					if x is not None:
						if posAbs:
							pos.x = x * scale
						else:
							pos.x += x * scale
					if y is not None:
						if posAbs:
							pos.y = y * scale
						else:
							pos.y += y * scale
					if z is not None:
						oldZ = pos.z
						if posAbs:
							pos.z = z * scale
						else:
							pos.z += z * scale
						if oldZ != pos.z and startCodeDone:
							layerNr += 1
					if f is not None:
						feedRate = f
					newPoint = pos.copy()
					moveType = 'move'
					if e is not None:
						if e > currentE:
							moveType = 'extrude'
						if e < currentE:
							moveType = 'retract'
						currentE = e
					if currentPath['type'] != moveType or currentPath['pathType'] != pathType:
						pathList.append(currentPath)
						currentPath = {'type': moveType, 'pathType': pathType, 'list': [currentPath['list'][-1]], 'layerNr': layerNr}
					currentPath['list'].append(newPoint)
				elif G == 20:	#Units are inches
					scale = 25.4
				elif G == 21:	#Units are mm
					scale = 1.0
				elif G == 28:	#Home
					x = self.getCodeFloat(line, 'X')
					y = self.getCodeFloat(line, 'Y')
					z = self.getCodeFloat(line, 'Z')
					if x is None and y is None and z is None:
						pos = util3d.Vector3()
					else:
						if x is not None:
							pos.x = 0.0
						if y is not None:
							pos.y = 0.0
						if z is not None:
							pos.z = 0.0
				elif G == 90:	#Absolute position
					posAbs = True
				elif G == 91:	#Relative position
					posAbs = False
				elif G == 92:
					x = self.getCodeFloat(line, 'X')
					y = self.getCodeFloat(line, 'Y')
					z = self.getCodeFloat(line, 'Z')
					e = self.getCodeFloat(line, 'E')
					if e is not None:
						currentE = e
					if x is not None:
						posOffset.x = pos.x + x
					if y is not None:
						posOffset.y = pos.y + y
					if z is not None:
						posOffset.z = pos.z + z
				else:
					print "Unknown G code:" + str(G)
			else:
				M = self.getCodeInt(line, 'M')
				if M is not None:
					if M == 1:	#Message with possible wait (ignored)
						pass
					elif M == 84:	#Disable step drivers
						pass
					elif M == 92:	#Set steps per unit
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
					elif M == 113:	#Extruder PWM (these should not be in the final GCode, but they are)
						pass
					else:
						print "Unknown M code:" + str(M)
		self.layerCount = layerNr
		self.pathList = pathList

	def getCodeInt(self, str, id):
		m = re.search(id + '([^\s]+)', str)
		if m == None:
			return None
		try:
			return int(m.group(1))
		except:
			return None

	def getCodeFloat(self, str, id):
		m = re.search(id + '([^\s]+)', str)
		if m == None:
			return None
		try:
			return float(m.group(1))
		except:
			return None

