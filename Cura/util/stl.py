from __future__ import absolute_import
import __init__

import sys
import math
import re
import os
import struct

from util import util3d

class stlFace():
	def __init__(self, v0, v1, v2):
		self.v = [v0, v1, v2]

class stlModel():
	def __init__(self):
		self.faces = []
		self.vertexes = []

	def load(self, filename):
		f = open(filename, "rb")
		if f.read(6).lower() == "solid ":
			self._loadAscii(f)
			if len(self.faces) < 1:
				f.seek(6, os.SEEK_SET)
				self._loadBinary(f)
		else:
			self._loadBinary(f)
		f.close()
	
	def _loadAscii(self, f):
		cnt = 0
		for line in f:
			if 'vertex' in line:
				data = line.split()
				if cnt == 0:
					v0 = util3d.Vector3(float(data[1]), float(data[2]), float(data[3]))
					cnt = 1
				elif cnt == 1:
					v1 = util3d.Vector3(float(data[1]), float(data[2]), float(data[3]))
					cnt = 2
				elif cnt == 2:
					v2 = util3d.Vector3(float(data[1]), float(data[2]), float(data[3]))
					self.faces.append(stlFace(v0, v1, v2))
					self.vertexes.append(v0)
					self.vertexes.append(v1)
					self.vertexes.append(v2)
					cnt = 0

	def _loadBinary(self, f):
		#Skip the header
		f.read(80-6)
		faceCount = struct.unpack('<I', f.read(4))[0]
		for idx in xrange(0, faceCount):
			data = struct.unpack("<ffffffffffffH", f.read(50))
			v0 = util3d.Vector3(data[3], data[4], data[5])
			v1 = util3d.Vector3(data[6], data[7], data[8])
			v2 = util3d.Vector3(data[9], data[10], data[11])
			self.faces.append(stlFace(v0, v1, v2))
			self.vertexes.append(v0)
			self.vertexes.append(v1)
			self.vertexes.append(v2)

	def getMinimumZ(self):
		minv = self.vertexes[0].copy()
		maxv = self.vertexes[0].copy()
		for v in self.vertexes:
			minv.x = min(minv.x, v.x)
			minv.y = min(minv.y, v.y)
			minv.z = min(minv.z, v.z)
			maxv.x = max(maxv.x, v.x)
			maxv.y = max(maxv.y, v.y)
			maxv.z = max(maxv.z, v.z)
		self.min = minv
		self.max = maxv
		return self.min.z
	
	def getMaximum(self):
		return self.max
	def getMinimum(self):
		return self.min

if __name__ == '__main__':
	for filename in sys.argv[1:]:
		stlModel().load(filename)

