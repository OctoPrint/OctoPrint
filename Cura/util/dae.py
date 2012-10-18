import sys, math, re, os, struct, time
from  xml.parsers.expat import ParserCreate

import mesh

class daeModel(mesh.mesh):
	def __init__(self):
		super(daeModel, self).__init__()

	def load(self, filename):
		r = ParserCreate()
		r.StartElementHandler = self._StartElementHandler
		r.EndElementHandler = self._EndElementHandler
		r.CharacterDataHandler = self._CharacterDataHandler

		self._base = {}
		self._cur = self._base
		self._idMap = {}
		self._geometryList = []
		r.ParseFile(open(filename, "r"))
		for geo in self._geometryList:
			self._ParseGeometry(self._idMap[geo['_url']])
		self._base = None
		self._cur = None
		self._idMap = None
		
		self._postProcessAfterLoad()
		return self
	
	def _StartElementHandler(self, name, attributes):
		while name in self._cur:
			name += "!"
		self._cur[name] = {'_parent': self._cur}
		self._cur = self._cur[name]
		for k in attributes.keys():
			self._cur['_' + k] = attributes[k]
		
		if 'id' in attributes:
			self._idMap['#' + attributes['id']] = self._cur
		
		if name == 'instance_geometry':
			self._geometryList.append(self._cur)
		
	def _EndElementHandler(self, name):
		self._cur = self._cur['_parent']

	def _CharacterDataHandler(self, data):
		if len(data.strip()) < 1:
			return
		if '_data' in self._cur:
			self._cur['_data'] += data
		else:
			self._cur['_data'] = data
	
	def _GetWithKey(self, item, basename, key, value):
		input = basename
		while input in item:
			if item[basename]['_'+key] == value:
				return self._idMap[item[input]['_source']]
			basename += "!"
	
	def _ParseGeometry(self, geo):
		indexList = map(int, geo['mesh']['triangles']['p']['_data'].split())
		vertex = self._GetWithKey(geo['mesh']['triangles'], 'input', 'semantic', 'VERTEX')
		positionList = map(float, self._GetWithKey(vertex, 'input', 'semantic', 'POSITION')['float_array']['_data'].split())
		
		self._prepareVertexCount(len(indexList))
		for idx in indexList:
			self.addVertex(positionList[idx*3], positionList[idx*3+1], positionList[idx*3+2])
