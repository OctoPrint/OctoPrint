"""
This page is in the table of contents.
The xml.py script is an import translator plugin to get a carving from an Art of Illusion xml file.

An import plugin is a script in the interpret_plugins folder which has the function getCarving.  It is meant to be run from the interpret tool.  To ensure that the plugin works on platforms which do not handle file capitalization properly, give the plugin a lower case name.

The getCarving function takes the file name of an xml file and returns the carving.

An xml file can be exported from Art of Illusion by going to the "File" menu, then going into the "Export" menu item, then picking the XML choice.  This will bring up the XML file chooser window, choose a place to save the file then click "OK".  Leave the "compressFile" checkbox unchecked.  All the objects from the scene will be exported, this plugin will ignore the light and camera.  If you want to fabricate more than one object at a time, you can have multiple objects in the Art of Illusion scene and they will all be carved, then fabricated together.

"""


from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.geometry_utilities.evaluate_elements import setting
from fabmetheus_utilities.geometry.geometry_utilities import boolean_solid
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.solids import triangle_mesh
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import settings
from fabmetheus_utilities import xml_simple_writer
import math


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Nophead <http://hydraraptor.blogspot.com/>\nArt of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getEmptyZLoops(archivableObjects, importRadius, shouldPrintWarning, z, zoneArrangement):
	'Get loops at empty z level.'
	emptyZ = zoneArrangement.getEmptyZ(z)
	visibleObjects = evaluate.getVisibleObjects(archivableObjects)
	visibleObjectLoopsList = boolean_solid.getVisibleObjectLoopsList(importRadius, visibleObjects, emptyZ)
	loops = euclidean.getConcatenatedList(visibleObjectLoopsList)
	if euclidean.isLoopListIntersecting(loops):
		loops = boolean_solid.getLoopsUnion(importRadius, visibleObjectLoopsList)
		if shouldPrintWarning:
			print('Warning, the triangle mesh slice intersects itself in getExtruderPaths in boolean_geometry.')
			print('Something will still be printed, but there is no guarantee that it will be the correct shape.')
			print('Once the gcode is saved, you should check over the layer with a z of:')
			print(z)
	return loops

def getLoopLayers(archivableObjects, importRadius, layerHeight, maximumZ, shouldPrintWarning, z, zoneArrangement):
	'Get loop layers.'
	loopLayers = []
	while z <= maximumZ:
		triangle_mesh.getLoopLayerAppend(loopLayers, z).loops = getEmptyZLoops(archivableObjects, importRadius, True, z, zoneArrangement)
		z += layerHeight
	return loopLayers

def getMinimumZ(geometryObject):
	'Get the minimum of the minimum z of the archivableObjects and the object.'
	booleanGeometry = BooleanGeometry()
	booleanGeometry.archivableObjects = geometryObject.archivableObjects
	booleanGeometry.importRadius = setting.getImportRadius(geometryObject.elementNode)
	booleanGeometry.layerHeight = setting.getLayerHeight(geometryObject.elementNode)
	archivableMinimumZ = booleanGeometry.getMinimumZ()
	geometryMinimumZ = geometryObject.getMinimumZ()
	if archivableMinimumZ == None:
		return geometryMinimumZ
	if geometryMinimumZ == None:
		return archivableMinimumZ
	return min(archivableMinimumZ, geometryMinimumZ)


class BooleanGeometry:
	'A boolean geometry scene.'
	def __init__(self):
		'Add empty lists.'
		self.archivableObjects = []
		self.belowLoops = []
		self.importRadius = 0.6
		self.layerHeight = 0.4
		self.loopLayers = []

	def __repr__(self):
		'Get the string representation of this carving.'
		elementNode = None
		if len(self.archivableObjects) > 0:
			elementNode = self.archivableObjects[0].elementNode
		output = xml_simple_writer.getBeginGeometryXMLOutput(elementNode)
		self.addXML( 1, output )
		return xml_simple_writer.getEndGeometryXMLString(output)

	def addXML(self, depth, output):
		'Add xml for this object.'
		xml_simple_writer.addXMLFromObjects( depth, self.archivableObjects, output )

	def getCarveBoundaryLayers(self):
		'Get the boundary layers.'
		if self.getMinimumZ() == None:
			return []
		z = self.minimumZ + 0.5 * self.layerHeight
		self.loopLayers = getLoopLayers(self.archivableObjects, self.importRadius, self.layerHeight, self.maximumZ, True, z, self.zoneArrangement)
		self.cornerMaximum = Vector3(-912345678.0, -912345678.0, -912345678.0)
		self.cornerMinimum = Vector3(912345678.0, 912345678.0, 912345678.0)
		for loopLayer in self.loopLayers:
			for loop in loopLayer.loops:
				for point in loop:
					pointVector3 = Vector3(point.real, point.imag, loopLayer.z)
					self.cornerMaximum.maximize(pointVector3)
					self.cornerMinimum.minimize(pointVector3)
		self.cornerMaximum.z += self.halfHeight
		self.cornerMinimum.z -= self.halfHeight
		for loopLayerIndex in xrange(len(self.loopLayers) -1, -1, -1):
			loopLayer = self.loopLayers[loopLayerIndex]
			if len(loopLayer.loops) > 0:
				return self.loopLayers[: loopLayerIndex + 1]
		return []

	def getCarveCornerMaximum(self):
		'Get the corner maximum of the vertexes.'
		return self.cornerMaximum

	def getCarveCornerMinimum(self):
		'Get the corner minimum of the vertexes.'
		return self.cornerMinimum

	def getCarveLayerHeight(self):
		'Get the layer height.'
		return self.layerHeight

	def getFabmetheusXML(self):
		'Return the fabmetheus XML.'
		if len(self.archivableObjects) > 0:
			return self.archivableObjects[0].elementNode.getOwnerDocument().getOriginalRoot()
		return None

	def getInterpretationSuffix(self):
		'Return the suffix for a boolean carving.'
		return 'xml'

	def getMatrix4X4(self):
		'Get the matrix4X4.'
		return None

	def getMatrixChainTetragrid(self):
		'Get the matrix chain tetragrid.'
		return None

	def getMinimumZ(self):
		'Get the minimum z.'
		vertexes = []
		for visibleObject in evaluate.getVisibleObjects(self.archivableObjects):
			vertexes += visibleObject.getTransformedVertexes()
		if len(vertexes) < 1:
			return None
		self.maximumZ = -912345678.0
		self.minimumZ = 912345678.0
		for vertex in vertexes:
			self.maximumZ = max(self.maximumZ, vertex.z)
			self.minimumZ = min(self.minimumZ, vertex.z)
		self.zoneArrangement = triangle_mesh.ZoneArrangement(self.layerHeight, vertexes)
		self.halfHeight = 0.5 * self.layerHeight
		self.setActualMinimumZ()
		return self.minimumZ

	def getNumberOfEmptyZLoops(self, z):
		'Get number of empty z loops.'
		return len(getEmptyZLoops(self.archivableObjects, self.importRadius, False, z, self.zoneArrangement))

	def setActualMinimumZ(self):
		'Get the actual minimum z at the lowest rotated boundary layer.'
		halfHeightOverMyriad = 0.0001 * self.halfHeight
		while self.minimumZ < self.maximumZ:
			if self.getNumberOfEmptyZLoops(self.minimumZ + halfHeightOverMyriad) > 0:
				if self.getNumberOfEmptyZLoops(self.minimumZ - halfHeightOverMyriad) < 1:
					return
				increment = -self.halfHeight
				while abs(increment) > halfHeightOverMyriad:
					self.minimumZ += increment
					increment = 0.5 * abs(increment)
					if self.getNumberOfEmptyZLoops(self.minimumZ) > 0:
						increment = -increment
				self.minimumZ = round(self.minimumZ, -int(round(math.log10(halfHeightOverMyriad) + 1.5)))
				return
			self.minimumZ += self.layerHeight

	def setCarveImportRadius( self, importRadius ):
		'Set the import radius.'
		self.importRadius = importRadius

	def setCarveIsCorrectMesh( self, isCorrectMesh ):
		'Set the is correct mesh flag.'
		self.isCorrectMesh = isCorrectMesh

	def setCarveLayerHeight( self, layerHeight ):
		'Set the layer height.'
		self.layerHeight = layerHeight
