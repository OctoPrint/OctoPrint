import sys, math, re, os, struct, time

import mesh

class objModel(mesh.mesh):
	def __init__(self):
		super(objModel, self).__init__()

	def load(self, filename):
		vertexList = []
		faceList = []
		
		f = open(filename, "r")
		for line in f:
			parts = line.split()
			if len(parts) < 1:
				continue
			if parts[0] == 'v':
				vertexList.append([float(parts[1]), float(parts[2]), float(parts[3])])
			if parts[0] == 'f':
				parts[1] = parts[1].split('/')[0]
				parts[2] = parts[2].split('/')[0]
				parts[3] = parts[3].split('/')[0]
				faceList.append([int(parts[1]), int(parts[2]), int(parts[3])])
		f.close()
		
		self._prepareVertexCount(len(faceList) * 3)
		for f in faceList:
			i = f[0] - 1
			self.addVertex(vertexList[i][0], vertexList[i][1], vertexList[i][2])
			i = f[1] - 1
			self.addVertex(vertexList[i][0], vertexList[i][1], vertexList[i][2])
			i = f[2] - 1
			self.addVertex(vertexList[i][0], vertexList[i][1], vertexList[i][2])
		
		self._postProcessAfterLoad()
		return self
	
