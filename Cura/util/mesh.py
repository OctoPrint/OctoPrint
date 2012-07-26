import sys, math, re, os, struct, time

import util3d

import numpy

class mesh(object):
	def __init__(self):
		self.vertexes = None
		self.origonalVertexes = None
		self.vertexCount = 0

	def addVertex(self, x, y, z):
		n = self.vertexCount
		self.origonalVertexes[n][0] = x
		self.origonalVertexes[n][1] = y
		self.origonalVertexes[n][2] = z
		self.vertexCount += 1
	
	def _prepareVertexCount(self, vertexNumber):
		#Set the amount of faces before loading data in them. This way we can create the numpy arrays before we fill them.
		self.origonalVertexes = numpy.zeros((vertexNumber, 3), float)
		self.normal = numpy.zeros((vertexNumber / 3, 3))
		self.vertexCount = 0

	def _postProcessAfterLoad(self):
		self.vertexes = self.origonalVertexes.copy()
		self.getMinimumZ()

	def getMinimumZ(self):
		self.min = self.vertexes.min(0)
		self.max = self.vertexes.max(0)
		self.size = self.max - self.min
		return self.min[2]
	
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
			x = self.origonalVertexes[i][0]
			y = self.origonalVertexes[i][1]
			z = self.origonalVertexes[i][2]
			if swapXZ:
				x, z = z, x
			if swapYZ:
				y, z = z, y
			self.vertexes[i][0] = x * mat00 + y * mat01
			self.vertexes[i][1] = x * mat10 + y * mat11
			self.vertexes[i][2] = z * scaleZ

		for i in xrange(0, len(self.origonalVertexes), 3):
			v1 = self.vertexes[i]
			v2 = self.vertexes[i+1]
			v3 = self.vertexes[i+2]
			self.normal[i/3] = numpy.cross((v2 - v1), (v3 - v1))
			self.normal[i/3] /= (self.normal[i/3] * self.normal[i/3]).sum()

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

