"""
Boolean geometry disjoin.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.geometry_tools import path
from fabmetheus_utilities.geometry.geometry_utilities.evaluate_elements import setting
from fabmetheus_utilities.geometry.geometry_utilities import boolean_geometry
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.geometry_utilities import matrix
from fabmetheus_utilities.geometry.solids import difference
from fabmetheus_utilities.geometry.solids import triangle_mesh
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import xml_simple_reader
from fabmetheus_utilities.vector3 import Vector3


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getLinkedElementNode(idSuffix, parentNode, target):
	'Get elementNode with identifiers and parentNode.'
	linkedElementNode = xml_simple_reader.ElementNode()
	euclidean.overwriteDictionary(target.attributes, ['id', 'name', 'quantity'], linkedElementNode.attributes)
	linkedElementNode.addSuffixToID(idSuffix)
	tagKeys = target.getTagKeys()
	tagKeys.append('disjoin')
	tagKeys.sort()
	tags = ', '.join(tagKeys)
	linkedElementNode.attributes['tags'] = tags
	linkedElementNode.setParentAddToChildNodes(parentNode)
	linkedElementNode.addToIdentifierDictionaries()
	return linkedElementNode

def getNewDerivation(elementNode):
	'Get new derivation.'
	return DisjoinDerivation(elementNode)

def processElementNode(elementNode):
	'Process the xml element.'
	processElementNodeByDerivation(None, elementNode)

def processElementNodeByDerivation(derivation, elementNode):
	'Process the xml element by derivation.'
	if derivation == None:
		derivation = DisjoinDerivation(elementNode)
	targetElementNode = derivation.targetElementNode
	if targetElementNode == None:
		print('Warning, disjoin could not get target for:')
		print(elementNode)
		return
	xmlObject = targetElementNode.xmlObject
	if xmlObject == None:
		print('Warning, processElementNodeByDerivation in disjoin could not get xmlObject for:')
		print(targetElementNode)
		print(derivation.elementNode)
		return
	matrix.getBranchMatrixSetElementNode(targetElementNode)
	transformedVertexes = xmlObject.getTransformedVertexes()
	if len(transformedVertexes) < 1:
		print('Warning, transformedVertexes is zero in processElementNodeByDerivation in disjoin for:')
		print(xmlObject)
		print(targetElementNode)
		print(derivation.elementNode)
		return
	elementNode.localName = 'group'
	elementNode.getXMLProcessor().processElementNode(elementNode)
	targetChainMatrix = matrix.Matrix(xmlObject.getMatrixChainTetragrid())
	minimumZ = boolean_geometry.getMinimumZ(xmlObject)
	z = minimumZ + 0.5 * derivation.sheetThickness
	zoneArrangement = triangle_mesh.ZoneArrangement(derivation.layerHeight, transformedVertexes)
	oldVisibleString = targetElementNode.attributes['visible']
	targetElementNode.attributes['visible'] = True
	loops = boolean_geometry.getEmptyZLoops([xmlObject], derivation.importRadius, False, z, zoneArrangement)
	targetElementNode.attributes['visible'] = oldVisibleString
	vector3Loops = euclidean.getVector3Paths(loops, z)
	pathElement = getLinkedElementNode('_sheet', elementNode, targetElementNode)
	path.convertElementNode(pathElement, vector3Loops)
	targetOutput = xmlObject.getGeometryOutput()
	differenceElement = getLinkedElementNode('_solid', elementNode, targetElementNode)
	targetElementCopy = targetElementNode.getCopy('_positive', differenceElement)
	targetElementCopy.attributes['visible'] = True
	targetElementCopy.attributes.update(targetChainMatrix.getAttributes('matrix.'))
	complexMaximum = euclidean.getMaximumByVector3Path(transformedVertexes).dropAxis()
	complexMinimum = euclidean.getMinimumByVector3Path(transformedVertexes).dropAxis()
	centerComplex = 0.5 * (complexMaximum + complexMinimum)
	centerVector3 = Vector3(centerComplex.real, centerComplex.imag, minimumZ)
	slightlyMoreThanHalfExtent = 0.501 * (complexMaximum - complexMinimum)
	inradius = Vector3(slightlyMoreThanHalfExtent.real, slightlyMoreThanHalfExtent.imag, derivation.sheetThickness)
	cubeElement = xml_simple_reader.ElementNode()
	cubeElement.attributes['inradius'] = str(inradius)
	if not centerVector3.getIsDefault():
		cubeElement.attributes['translate.'] = str(centerVector3)
	cubeElement.localName = 'cube'
	cubeElement.setParentAddToChildNodes(differenceElement)
	difference.processElementNode(differenceElement)


class DisjoinDerivation:
	"Class to hold disjoin variables."
	def __init__(self, elementNode):
		'Set defaults.'
		self.elementNode = elementNode
		self.importRadius = setting.getImportRadius(elementNode)
		self.layerHeight = setting.getLayerHeight(elementNode)
		self.sheetThickness = setting.getSheetThickness(elementNode)
		self.targetElementNode = evaluate.getElementNodeByKey(elementNode, 'target')
