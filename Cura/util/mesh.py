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
		self.normal = numpy.zeros((vertexNumber, 3), float)
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
		
		mat = numpy.array([[mat00,mat10,0],[mat01,mat11,0],[0,0,scaleZ]], float)
		if swapXZ:
			mat = numpy.array([mat[2],mat[1],mat[0]], float)
		if swapYZ:
			mat = numpy.array([mat[0],mat[2],mat[1]], float)
		self.vertexes = (numpy.matrix(self.origonalVertexes, copy = False) * numpy.matrix(mat)).getA()

		tris = self.vertexes.reshape(self.vertexCount / 3, 3, 3)
		normals = numpy.cross( tris[::,1 ] - tris[::,0]  , tris[::,2 ] - tris[::,0] )
		lens = numpy.sqrt( normals[:,0]**2 + normals[:,1]**2 + normals[:,2]**2 )
		normals[:,0] /= lens
		normals[:,1] /= lens
		normals[:,2] /= lens
		
		n = numpy.zeros((self.vertexCount / 3, 9), float)
		n[:,0:3] = normals
		n[:,3:6] = normals
		n[:,6:9] = normals
		self.normal = n.reshape(self.vertexCount, 3)
		self.invNormal = -self.normal
		
		self.getMinimumZ()

	def splitToParts(self, callback = None):
		t0 = time.time()

		print "%f: " % (time.time() - t0), "Splitting a model with %d vertexes." % (len(self.vertexes))
		removeDict = {}
		tree = util3d.AABBTree()
		off = numpy.array([0.0001,0.0001,0.0001])
		for idx in xrange(0, self.vertexCount):
			v = self.vertexes[idx]
			e = util3d.AABB(v-off, v+off)
			q = tree.query(e)
			if len(q) < 1:
				e.idx = idx
				tree.insert(e)
			else:
				removeDict[idx] = q[0].idx
			if callback != None and (idx % 100) == 0:
				callback(idx)
		print "%f: " % (time.time() - t0), "Marked %d duplicate vertexes for removal." % (len(removeDict))

		faceList = []
		for idx in xrange(0, self.vertexCount, 3):
			f = [idx, idx + 1, idx + 2]
			if removeDict.has_key(f[0]):
				f[0] = removeDict[f[0]]
			if removeDict.has_key(f[1]):
				f[1] = removeDict[f[1]]
			if removeDict.has_key(f[2]):
				f[2] = removeDict[f[2]]
			faceList.append(f)
		
		print "%f: " % (time.time() - t0), "Building face lists after vertex removal."
		vertexFaceList = []
		for idx in xrange(0, self.vertexCount):
			vertexFaceList.append([])
		for idx in xrange(0, len(faceList)):
			f = faceList[idx]
			vertexFaceList[f[0]].append(idx)
			vertexFaceList[f[1]].append(idx)
			vertexFaceList[f[2]].append(idx)
		
		print "%f: " % (time.time() - t0), "Building parts."
		self._vertexFaceList = vertexFaceList
		self._faceList = faceList
		partList = []
		doneSet = set()
		for idx in xrange(0, len(faceList)):
			if not idx in doneSet:
				partList.append(self._createPartFromFacewalk(idx, doneSet))
		print "%f: " % (time.time() - t0), "Split into %d parts" % (len(partList))
		self._vertexFaceList = None
		self._faceList = None
		return partList

	def _createPartFromFacewalk(self, startFaceIdx, doneSet):
		m = mesh()
		m._prepareVertexCount(self.vertexCount)
		todoList = [startFaceIdx]
		doneSet.add(startFaceIdx)
		while len(todoList) > 0:
			faceIdx = todoList.pop()
			self._partAddFacewalk(m, faceIdx, doneSet, todoList)
		return m

	def _partAddFacewalk(self, part, faceIdx, doneSet, todoList):
		f = self._faceList[faceIdx]
		v0 = self.vertexes[f[0]]
		v1 = self.vertexes[f[1]]
		v2 = self.vertexes[f[2]]
		part.addVertex(v0[0], v0[1], v0[2])
		part.addVertex(v1[0], v1[1], v1[2])
		part.addVertex(v2[0], v2[1], v2[2])
		for f1 in self._vertexFaceList[f[0]]:
			if f1 not in doneSet:
				todoList.append(f1)
				doneSet.add(f1)
		for f1 in self._vertexFaceList[f[1]]:
			if f1 not in doneSet:
				todoList.append(f1)
				doneSet.add(f1)
		for f1 in self._vertexFaceList[f[2]]:
			if f1 not in doneSet:
				todoList.append(f1)
				doneSet.add(f1)

