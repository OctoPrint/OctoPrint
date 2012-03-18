"""
Path.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.geometry_tools import dictionary
from fabmetheus_utilities.geometry.geometry_tools import vertex
from fabmetheus_utilities.geometry.geometry_utilities.evaluate_elements import setting
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.geometry_utilities import matrix
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import svg_writer
from fabmetheus_utilities import xml_simple_reader
from fabmetheus_utilities import xml_simple_writer


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def convertElementNode(elementNode, geometryOutput):
	'Convert the xml element by geometryOutput.'
	if geometryOutput == None:
		return
	if len(geometryOutput) < 1:
		return
	if len(geometryOutput) == 1:
		firstLoop = geometryOutput[0]
		if firstLoop.__class__ == list:
			geometryOutput = firstLoop
	firstElement = geometryOutput[0]
	if firstElement.__class__ == list:
		if len(firstElement) > 1:
			convertElementNodeRenameByPaths(elementNode, geometryOutput)
		else:
			convertElementNodeByPath(elementNode, firstElement)
	else:
		convertElementNodeByPath(elementNode, geometryOutput)

def convertElementNodeByPath(elementNode, geometryOutput):
	'Convert the xml element to a path xml element.'
	createLinkPath(elementNode)
	elementNode.xmlObject.vertexes = geometryOutput
	vertex.addGeometryList(elementNode, geometryOutput)

def convertElementNodeRenameByPaths(elementNode, geometryOutput):
	'Convert the xml element to a path xml element and add paths.'
	createLinkPath(elementNode)
	for geometryOutputChild in geometryOutput:
		pathElement = xml_simple_reader.ElementNode()
		pathElement.setParentAddToChildNodes(elementNode)
		convertElementNodeByPath(pathElement, geometryOutputChild)

def createLinkPath(elementNode):
	'Create and link a path object.'
	elementNode.localName = 'path'
	elementNode.linkObject(Path())

def processElementNode(elementNode):
	'Process the xml element.'
	evaluate.processArchivable(Path, elementNode)


class Path(dictionary.Dictionary):
	'A path.'
	def __init__(self):
		'Add empty lists.'
		dictionary.Dictionary.__init__(self)
		self.matrix4X4 = matrix.Matrix()
		self.oldChainTetragrid = None
		self.transformedPath = None
		self.vertexes = []

	def addXMLInnerSection(self, depth, output):
		'Add the xml section for this object.'
		if self.matrix4X4 != None:
			self.matrix4X4.addXML(depth, output)
		xml_simple_writer.addXMLFromVertexes(depth, output, self.vertexes)

	def getFabricationExtension(self):
		'Get fabrication extension.'
		return 'svg'

	def getFabricationText(self, addLayerTemplate):
		'Get fabrication text.'
		carving = SVGFabricationCarving(addLayerTemplate, self.elementNode)
		carving.setCarveLayerHeight(setting.getSheetThickness(self.elementNode))
		carving.processSVGElement(self.elementNode.getOwnerDocument().fileName)
		return str(carving)

	def getMatrix4X4(self):
		"Get the matrix4X4."
		return self.matrix4X4

	def getMatrixChainTetragrid(self):
		'Get the matrix chain tetragrid.'
		return matrix.getTetragridTimesOther(self.elementNode.parentNode.xmlObject.getMatrixChainTetragrid(), self.matrix4X4.tetragrid)

	def getPaths(self):
		'Get all paths.'
		self.transformedPath = None
		if len(self.vertexes) > 0:
			return dictionary.getAllPaths([self.vertexes], self)
		return dictionary.getAllPaths([], self)

	def getTransformedPaths(self):
		'Get all transformed paths.'
		if self.elementNode == None:
			return dictionary.getAllPaths([self.vertexes], self)
		chainTetragrid = self.getMatrixChainTetragrid()
		if self.oldChainTetragrid != chainTetragrid:
			self.oldChainTetragrid = chainTetragrid
			self.transformedPath = None
		if self.transformedPath == None:
			self.transformedPath = matrix.getTransformedVector3s(chainTetragrid, self.vertexes)
		if len(self.transformedPath) > 0:
			return dictionary.getAllTransformedPaths([self.transformedPath], self)
		return dictionary.getAllTransformedPaths([], self)


class SVGFabricationCarving:
	'An svg carving.'
	def __init__(self, addLayerTemplate, elementNode):
		'Add empty lists.'
		self.addLayerTemplate = addLayerTemplate
		self.elementNode = elementNode
		self.layerHeight = 1.0
		self.loopLayers = []

	def __repr__(self):
		'Get the string representation of this carving.'
		return self.getCarvedSVG()

	def addXML(self, depth, output):
		'Add xml for this object.'
		xml_simple_writer.addXMLFromObjects(depth, self.loopLayers, output)

	def getCarveBoundaryLayers(self):
		'Get the  boundary layers.'
		return self.loopLayers

	def getCarveCornerMaximum(self):
		'Get the corner maximum of the vertexes.'
		return self.cornerMaximum

	def getCarveCornerMinimum(self):
		'Get the corner minimum of the vertexes.'
		return self.cornerMinimum

	def getCarvedSVG(self):
		'Get the carved svg text.'
		return svg_writer.getSVGByLoopLayers(self.addLayerTemplate, self, self.loopLayers)

	def getCarveLayerHeight(self):
		'Get the layer height.'
		return self.layerHeight

	def getFabmetheusXML(self):
		'Return the fabmetheus XML.'
		return self.elementNode.getOwnerDocument().getOriginalRoot()

	def getInterpretationSuffix(self):
		'Return the suffix for a carving.'
		return 'svg'

	def processSVGElement(self, fileName):
		'Parse SVG element and store the layers.'
		self.fileName = fileName
		paths = self.elementNode.xmlObject.getPaths()
		oldZ = None
		self.loopLayers = []
		loopLayer = None
		for path in paths:
			if len(path) > 0:
				z = path[0].z
				if z != oldZ:
					loopLayer = euclidean.LoopLayer(z)
					self.loopLayers.append(loopLayer)
					oldZ = z
				loopLayer.loops.append(euclidean.getComplexPath(path))
		if len(self.loopLayers) < 1:
			return
		self.cornerMaximum = Vector3(-987654321.0, -987654321.0, -987654321.0)
		self.cornerMinimum = Vector3(987654321.0, 987654321.0, 987654321.0)
		svg_writer.setSVGCarvingCorners(self.cornerMaximum, self.cornerMinimum, self.layerHeight, self.loopLayers)

	def setCarveImportRadius( self, importRadius ):
		'Set the import radius.'
		pass

	def setCarveIsCorrectMesh( self, isCorrectMesh ):
		'Set the is correct mesh flag.'
		pass

	def setCarveLayerHeight( self, layerHeight ):
		'Set the layer height.'
		self.layerHeight = layerHeight
