"""
Boolean geometry carve.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.geometry_tools import path
from fabmetheus_utilities.geometry.geometry_utilities.evaluate_elements import setting
from fabmetheus_utilities.geometry.geometry_utilities import boolean_geometry
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.geometry_utilities import matrix
from fabmetheus_utilities.geometry.solids import triangle_mesh
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import xml_simple_reader


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
	tagKeys.append('carve')
	tagKeys.sort()
	tags = ', '.join(tagKeys)
	linkedElementNode.attributes['tags'] = tags
	linkedElementNode.setParentAddToChildNodes(parentNode)
	linkedElementNode.addToIdentifierDictionaries()
	return linkedElementNode

def getNewDerivation(elementNode):
	'Get new derivation.'
	return CarveDerivation(elementNode)

def processElementNode(elementNode):
	'Process the xml element.'
	processElementNodeByDerivation(None, elementNode)

def processElementNodeByDerivation(derivation, elementNode):
	'Process the xml element by derivation.'
	if derivation == None:
		derivation = CarveDerivation(elementNode)
	targetElementNode = derivation.targetElementNode
	if targetElementNode == None:
		print('Warning, carve could not get target for:')
		print(elementNode)
		return
	xmlObject = targetElementNode.xmlObject
	if xmlObject == None:
		print('Warning, processElementNodeByDerivation in carve could not get xmlObject for:')
		print(targetElementNode)
		print(derivation.elementNode)
		return
	matrix.getBranchMatrixSetElementNode(targetElementNode)
	transformedVertexes = xmlObject.getTransformedVertexes()
	if len(transformedVertexes) < 1:
		print('Warning, transformedVertexes is zero in processElementNodeByDerivation in carve for:')
		print(xmlObject)
		print(targetElementNode)
		print(derivation.elementNode)
		return
	elementNode.localName = 'group'
	elementNode.getXMLProcessor().processElementNode(elementNode)
	minimumZ = boolean_geometry.getMinimumZ(xmlObject)
	maximumZ = euclidean.getTopPath(transformedVertexes)
	zoneArrangement = triangle_mesh.ZoneArrangement(derivation.layerHeight, transformedVertexes)
	oldVisibleString = targetElementNode.attributes['visible']
	targetElementNode.attributes['visible'] = True
	z = minimumZ + 0.5 * derivation.layerHeight
	loopLayers = boolean_geometry.getLoopLayers([xmlObject], derivation.importRadius, derivation.layerHeight, maximumZ, False, z, zoneArrangement)
	targetElementNode.attributes['visible'] = oldVisibleString
	for loopLayerIndex, loopLayer in enumerate(loopLayers):
		if len(loopLayer.loops) > 0:
			pathElement = getLinkedElementNode('_carve_%s' % loopLayerIndex, elementNode, targetElementNode)
			vector3Loops = euclidean.getVector3Paths(loopLayer.loops, loopLayer.z)
			path.convertElementNode(pathElement, vector3Loops)


class CarveDerivation:
	"Class to hold carve variables."
	def __init__(self, elementNode):
		'Set defaults.'
		self.elementNode = elementNode
		self.importRadius = setting.getImportRadius(elementNode)
		self.layerHeight = setting.getLayerHeight(elementNode)
		self.targetElementNode = evaluate.getElementNodeByKey(elementNode, 'target')
