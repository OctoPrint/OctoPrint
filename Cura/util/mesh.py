from __future__ import absolute_import
import __init__

import sys
import math
import re
import os
import struct

from util import util3d

class meshFace(object):
	def __init__(self, v0, v1, v2):
		self.v = [v0, v1, v2]

class mesh(object):
	def __init__(self):
		self.faces = []
		self.vertexes = []

	def addFace(self, v0, v1, v2):
		self.faces.append(meshFace(v0, v1, v2))
		self.vertexes.append(v0)
		self.vertexes.append(v1)
		self.vertexes.append(v2)

	def _createOrigonalVertexCopy(self):
		self.origonalVertexes = list(self.vertexes)
		for i in xrange(0, len(self.origonalVertexes)):
			self.origonalVertexes[i] = self.origonalVertexes[i].copy()
		self.getMinimumZ()

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
		self.size = maxv - minv
		return self.min.z
	
	def getMaximum(self):
		return self.max
	def getMinimum(self):
		return self.min
	def getSize(self):
		return self.size

	def setRotateMirror(self, rotate, mirrorX, mirrorY, mirrorZ, swapXZ, swapYZ):
		rotate = rotate / 180.0 * math.pi
		scaleX = 1.0
		scaleY = 1.0
		scaleZ = 1.0
		if mirrorX:
			scaleX = -scaleX
		if mirrorY:
			scaleY = -scaleY
		if mirrorZ:
			scaleZ = -scaleZ
		mat00 = math.cos(rotate) * scaleX
		mat01 =-math.sin(rotate) * scaleY
		mat10 = math.sin(rotate) * scaleX
		mat11 = math.cos(rotate) * scaleY
		
		for i in xrange(0, len(self.origonalVertexes)):
			x = self.origonalVertexes[i].x
			y = self.origonalVertexes[i].y
			z = self.origonalVertexes[i].z
			if swapXZ:
				x, z = z, x
			if swapYZ:
				y, z = z, y
			self.vertexes[i].x = x * mat00 + y * mat01
			self.vertexes[i].y = x * mat10 + y * mat11
			self.vertexes[i].z = z * scaleZ

		for face in self.faces:
			v1 = face.v[0]
			v2 = face.v[1]
			v3 = face.v[2]
			face.normal = (v2 - v1).cross(v3 - v1)
			face.normal.normalize()

		minZ = self.getMinimumZ()
		minV = self.getMinimum()
		maxV = self.getMaximum()
		for v in self.vertexes:
			v.z -= minZ
			v.x -= minV.x + (maxV.x - minV.x) / 2
			v.y -= minV.y + (maxV.y - minV.y) / 2
		self.getMinimumZ()

if __name__ == '__main__':
	for filename in sys.argv[1:]:
		stlModel().load(filename)
