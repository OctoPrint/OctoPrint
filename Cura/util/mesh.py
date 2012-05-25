from __future__ import absolute_import
import __init__

import sys, math, re, os, struct, time

from util import util3d

class meshFace(object):
	def __init__(self, v0, v1, v2):
		self.v = [v0, v1, v2]

class mesh(object):
	def __init__(self):
		self.faces = []
		self.vertexes = []

	def addFace(self, v0, v1, v2):
		self.vertexes.append(v0)
		self.vertexes.append(v1)
		self.vertexes.append(v2)
		self.faces.append(meshFace(v0, v1, v2))

	def _postProcessAfterLoad(self):
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

	def splitToParts(self):
		t0 = time.time()

		print "%f: " % (time.time() - t0), "Splitting a model with %d vertexes." % (len(self.vertexes))
		removeDict = {}
		tree = util3d.AABBTree()
		off = util3d.Vector3(0.0001,0.0001,0.0001)
		newVertexList = []
		for v in self.vertexes:
			e = util3d.AABB(v-off, v+off)
			q = tree.query(e)
			if len(q) < 1:
				e.vector = v
				tree.insert(e)
				newVertexList.append(v)
			else:
				removeDict[v] = q[0].vector
		print "%f: " % (time.time() - t0), "Marked %d duplicate vertexes for removal." % (len(removeDict))
		
		#Make facelists so we can quickly remove all the vertexes.
		for v in self.vertexes:
			v.faceList = []
		for f in self.faces:
			f.v[0].faceList.append(f)
			f.v[1].faceList.append(f)
			f.v[2].faceList.append(f)

		self.vertexes = newVertexList
		for v1 in removeDict.iterkeys():
			v0 = removeDict[v1]
			for f in v1.faceList:
				if f.v[0] == v1:
					f.v[0] = v0
				if f.v[1] == v1:
					f.v[1] = v0
				if f.v[2] == v1:
					f.v[2] = v0
		print "%f: " % (time.time() - t0), "Building face lists after vertex removal."
		for v in self.vertexes:
			v.faceList = []
		for f in self.faces:
			f.v[0].faceList.append(f)
			f.v[1].faceList.append(f)
			f.v[2].faceList.append(f)
		
		print "%f: " % (time.time() - t0), "Building parts."
		partList = []
		doneSet = set()
		for f in self.faces:
			if not f in doneSet:
				partList.append(self._createPartFromFacewalk(f, doneSet))
		print "%f: " % (time.time() - t0), "Split into %d parts" % (len(partList))
		return partList

	def _createPartFromFacewalk(self, startFace, doneSet):
		m = mesh()
		todoList = [startFace]
		doneSet.add(startFace)
		while len(todoList) > 0:
			f = todoList.pop()
			m._partAddFacewalk(f, doneSet, todoList)
		return m

	def _partAddFacewalk(self, f, doneSet, todoList):
		self.addFace(f.v[0], f.v[1], f.v[2])
		for f1 in f.v[0].faceList:
			if f1 not in doneSet:
				todoList.append(f1)
				doneSet.add(f1)
		for f1 in f.v[1].faceList:
			if f1 not in doneSet:
				todoList.append(f1)
				doneSet.add(f1)
		for f1 in f.v[2].faceList:
			if f1 not in doneSet:
				todoList.append(f1)
				doneSet.add(f1)

