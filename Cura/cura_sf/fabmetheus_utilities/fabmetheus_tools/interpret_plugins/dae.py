from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.geometry_tools import face
from fabmetheus_utilities.geometry.solids import triangle_mesh
from fabmetheus_utilities.vector3 import Vector3

from  xml.parsers.expat import ParserCreate

def getCarving(fileName=''):
	"Get the triangle mesh for the dae file."
	return daeModel().load(fileName)

class daeModel(triangle_mesh.TriangleMesh):
	def __init__(self):
		triangle_mesh.TriangleMesh.__init__(self)

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
		
		for idx in xrange(0, len(positionList), 3):
			self.vertexes.append(Vector3(positionList[idx], positionList[idx+1], positionList[idx+2]))
		for idx in xrange(0, len(indexList), 3):
			f = face.Face()
			f.index = len(self.faces)
			f.vertexIndexes.append(indexList[idx])
			f.vertexIndexes.append(indexList[idx+1])
			f.vertexIndexes.append(indexList[idx+2])
			self.faces.append(f)
