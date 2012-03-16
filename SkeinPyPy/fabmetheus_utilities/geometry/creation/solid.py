"""
Solid has functions for 3D shapes.

Solid has some of the same functions as lineation, however you can not define geometry by dictionary string in the target because there is no getGeometryOutputByArguments function.  You would have to define a shape by making the shape element.  Also, you can not define geometry by 'get<Creation Name>, because the target only gets element.  Instead you would have the shape element, and set the target in solid to that element.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import lineation
from fabmetheus_utilities.geometry.geometry_tools import path
from fabmetheus_utilities.geometry.geometry_utilities import boolean_geometry
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.geometry_utilities import matrix
from fabmetheus_utilities.geometry.solids import triangle_mesh
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import euclidean
import math


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getGeometryOutputByFunction(elementNode, geometryFunction):
	'Get geometry output by manipulationFunction.'
	if elementNode.xmlObject == None:
		print('Warning, there is no object in getGeometryOutputByFunction in solid for:')
		print(elementNode)
		return None
	geometryOutput = elementNode.xmlObject.getGeometryOutput()
	if geometryOutput == None:
		print('Warning, there is no geometryOutput in getGeometryOutputByFunction in solid for:')
		print(elementNode)
		return None
	return geometryFunction(elementNode, geometryOutput, '')

def getGeometryOutputByManipulation(elementNode, geometryOutput):
	'Get geometryOutput manipulated by the plugins in the manipulation shapes & solids folders.'
	xmlProcessor = elementNode.getXMLProcessor()
	matchingPlugins = getSolidMatchingPlugins(elementNode)
	matchingPlugins.sort(evaluate.compareExecutionOrderAscending)
	for matchingPlugin in matchingPlugins:
		prefix = matchingPlugin.__name__.replace('_', '') + '.'
		geometryOutput = matchingPlugin.getManipulatedGeometryOutput(elementNode, geometryOutput, prefix)
	return geometryOutput

def getLoopLayersSetCopy(elementNode, geometryOutput, importRadius, radius):
	'Get the loop layers and set the copyShallow.'
	halfLayerHeight = 0.5 * radius
	copyShallow = elementNode.getCopyShallow()
	processElementNodeByGeometry(copyShallow, geometryOutput)
	targetMatrix = matrix.getBranchMatrixSetElementNode(elementNode)
	matrix.setElementNodeDictionaryMatrix(copyShallow, targetMatrix)
	transformedVertexes = copyShallow.xmlObject.getTransformedVertexes()
	minimumZ = boolean_geometry.getMinimumZ(copyShallow.xmlObject)
	if minimumZ == None:
		copyShallow.parentNode.xmlObject.archivableObjects.remove(copyShallow.xmlObject)
		return []
	maximumZ = euclidean.getTopPath(transformedVertexes)
	copyShallow.attributes['visible'] = True
	copyShallowObjects = [copyShallow.xmlObject]
	bottomLoopLayer = euclidean.LoopLayer(minimumZ)
	z = minimumZ + 0.1 * radius
	zoneArrangement = triangle_mesh.ZoneArrangement(radius, transformedVertexes)
	bottomLoopLayer.loops = boolean_geometry.getEmptyZLoops(copyShallowObjects, importRadius, False, z, zoneArrangement)
	loopLayers = [bottomLoopLayer]
	z = minimumZ + halfLayerHeight
	loopLayers += boolean_geometry.getLoopLayers(copyShallowObjects, importRadius, halfLayerHeight, maximumZ, False, z, zoneArrangement)
	copyShallow.parentNode.xmlObject.archivableObjects.remove(copyShallow.xmlObject)
	return loopLayers

def getLoopOrEmpty(loopIndex, loopLayers):
	'Get the loop, or if the loopIndex is out of range, get an empty list.'
	if loopIndex < 0 or loopIndex >= len(loopLayers):
		return []
	return loopLayers[loopIndex].loops[0]

def getNewDerivation(elementNode):
	'Get new derivation.'
	return SolidDerivation(elementNode)

def getSolidMatchingPlugins(elementNode):
	'Get solid plugins in the manipulation matrix, shapes & solids folders.'
	xmlProcessor = elementNode.getXMLProcessor()
	matchingPlugins = evaluate.getMatchingPlugins(elementNode, xmlProcessor.manipulationMatrixDictionary)
	return matchingPlugins + evaluate.getMatchingPlugins(elementNode, xmlProcessor.manipulationShapeDictionary)

def processArchiveRemoveSolid(elementNode, geometryOutput):
	'Process the target by the manipulationFunction.'
	solidMatchingPlugins = getSolidMatchingPlugins(elementNode)
	if len(solidMatchingPlugins) == 0:
		elementNode.parentNode.xmlObject.archivableObjects.append(elementNode.xmlObject)
		matrix.getBranchMatrixSetElementNode(elementNode)
		return
	processElementNodeByGeometry(elementNode, getGeometryOutputByManipulation(elementNode, geometryOutput))

def processElementNode(elementNode):
	'Process the xml element.'
	processElementNodeByDerivation(None, elementNode)

def processElementNodeByDerivation(derivation, elementNode):
	'Process the xml element by derivation.'
	if derivation == None:
		derivation = SolidDerivation(elementNode)
	elementAttributesCopy = elementNode.attributes.copy()
	for target in derivation.targets:
		targetAttributesCopy = target.attributes.copy()
		target.attributes = elementAttributesCopy
		processTarget(target)
		target.attributes = targetAttributesCopy

def processElementNodeByFunction(elementNode, manipulationFunction):
	'Process the xml element.'
	if 'target' not in elementNode.attributes:
		print('Warning, there was no target in processElementNodeByFunction in solid for:')
		print(elementNode)
		return
	target = evaluate.getEvaluatedLinkValue(elementNode, str(elementNode.attributes['target']).strip())
	if target.__class__.__name__ == 'ElementNode':
		manipulationFunction(elementNode, target)
		return
	path.convertElementNode(elementNode, target)
	manipulationFunction(elementNode, elementNode)

def processElementNodeByFunctionPair(elementNode, geometryFunction, pathFunction):
	'Process the xml element by the appropriate manipulationFunction.'
	elementAttributesCopy = elementNode.attributes.copy()
	targets = evaluate.getElementNodesByKey(elementNode, 'target')
	for target in targets:
		targetAttributesCopy = target.attributes.copy()
		target.attributes = elementAttributesCopy
		processTargetByFunctionPair(geometryFunction, pathFunction, target)
		target.attributes = targetAttributesCopy

def processElementNodeByGeometry(elementNode, geometryOutput):
	'Process the xml element by geometryOutput.'
	if geometryOutput != None:
		elementNode.getXMLProcessor().convertElementNode(elementNode, geometryOutput)

def processTarget(target):
	'Process the target.'
	if target.xmlObject == None:
		print('Warning, there is no object in processElementNode in solid for:')
		print(target)
		return
	geometryOutput = target.xmlObject.getGeometryOutput()
	if geometryOutput == None:
		print('Warning, there is no geometryOutput in processElementNode in solid for:')
		print(target.xmlObject)
		return
	geometryOutput = getGeometryOutputByManipulation(target, geometryOutput)
	lineation.removeChildNodesFromElementObject(target)
	target.getXMLProcessor().convertElementNode(target, geometryOutput)

def processTargetByFunctionPair(geometryFunction, pathFunction, target):
	'Process the target by the manipulationFunction.'
	if target.xmlObject == None:
		print('Warning, there is no object in processTargetByFunctions in solid for:')
		print(target)
		return
	if len(target.xmlObject.getPaths()) > 0:
		lineation.processTargetByFunction(pathFunction, target)
		return
	geometryOutput = getGeometryOutputByFunction(target, geometryFunction)
	lineation.removeChildNodesFromElementObject(target)
	target.getXMLProcessor().convertElementNode(target, geometryOutput)


class SolidDerivation:
	'Class to hold solid variables.'
	def __init__(self, elementNode):
		'Set defaults.'
		self.targets = evaluate.getElementNodesByKey(elementNode, 'target')
