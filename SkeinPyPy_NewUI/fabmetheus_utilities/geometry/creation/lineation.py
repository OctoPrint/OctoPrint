"""
Polygon path.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.geometry_tools import path
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.geometry_utilities import matrix
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import euclidean
import math


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getComplexByDictionary(dictionary, valueComplex):
	'Get complex by dictionary.'
	if 'x' in dictionary:
		valueComplex = complex(euclidean.getFloatFromValue(dictionary['x']),valueComplex.imag)
	if 'y' in dictionary:
		valueComplex = complex(valueComplex.real, euclidean.getFloatFromValue(dictionary['y']))
	return valueComplex

def getComplexByDictionaryListValue(value, valueComplex):
	'Get complex by dictionary, list or value.'
	if value.__class__ == complex:
		return value
	if value.__class__ == dict:
		return getComplexByDictionary(value, valueComplex)
	if value.__class__ == list:
		return getComplexByFloatList(value, valueComplex)
	floatFromValue = euclidean.getFloatFromValue(value)
	if floatFromValue ==  None:
		return valueComplex
	return complex( floatFromValue, floatFromValue )

def getComplexByFloatList( floatList, valueComplex ):
	'Get complex by float list.'
	if len(floatList) > 0:
		valueComplex = complex(euclidean.getFloatFromValue(floatList[0]), valueComplex.imag)
	if len(floatList) > 1:
		valueComplex = complex(valueComplex.real, euclidean.getFloatFromValue(floatList[1]))
	return valueComplex

def getComplexByMultiplierPrefix(elementNode, multiplier, prefix, valueComplex):
	'Get complex from multiplier, prefix and xml element.'
	if multiplier == 0.0:
		return valueComplex
	oldMultipliedValueComplex = valueComplex * multiplier
	complexByPrefix = getComplexByPrefix(elementNode, prefix, oldMultipliedValueComplex)
	if complexByPrefix == oldMultipliedValueComplex:
		return valueComplex
	return complexByPrefix / multiplier

def getComplexByMultiplierPrefixes(elementNode, multiplier, prefixes, valueComplex):
	'Get complex from multiplier, prefixes and xml element.'
	for prefix in prefixes:
		valueComplex = getComplexByMultiplierPrefix(elementNode, multiplier, prefix, valueComplex)
	return valueComplex

def getComplexByPrefix(elementNode, prefix, valueComplex):
	'Get complex from prefix and xml element.'
	value = evaluate.getEvaluatedValue(None, elementNode, prefix)
	if value != None:
		valueComplex = getComplexByDictionaryListValue(value, valueComplex)
	x = evaluate.getEvaluatedFloat(None, elementNode, prefix + '.x')
	if x != None:
		valueComplex = complex( x, getComplexIfNone( valueComplex ).imag )
	y = evaluate.getEvaluatedFloat(None, elementNode, prefix + '.y')
	if y != None:
		valueComplex = complex( getComplexIfNone( valueComplex ).real, y )
	return valueComplex

def getComplexByPrefixBeginEnd(elementNode, prefixBegin, prefixEnd, valueComplex):
	'Get complex from element node, prefixBegin and prefixEnd.'
	valueComplex = getComplexByPrefix(elementNode, prefixBegin, valueComplex)
	if prefixEnd in elementNode.attributes:
		return 0.5 * getComplexByPrefix(elementNode, valueComplex + valueComplex, prefixEnd)
	else:
		return valueComplex

def getComplexByPrefixes(elementNode, prefixes, valueComplex):
	'Get complex from prefixes and xml element.'
	for prefix in prefixes:
		valueComplex = getComplexByPrefix(elementNode, prefix, valueComplex)
	return valueComplex

def getComplexIfNone( valueComplex ):
	'Get new complex if the original complex is none.'
	if valueComplex == None:
		return complex()
	return valueComplex

def getFloatByPrefixBeginEnd(elementNode, prefixBegin, prefixEnd, valueFloat):
	'Get float from prefixBegin, prefixEnd and xml element.'
	valueFloat = evaluate.getEvaluatedFloat(valueFloat, elementNode, prefixBegin)
	if prefixEnd in elementNode.attributes:
		return 0.5 * evaluate.getEvaluatedFloat(valueFloat + valueFloat, elementNode, prefixEnd)
	return valueFloat

def getFloatByPrefixSide(defaultValue, elementNode, prefix, side):
	'Get float by prefix and side.'
	if elementNode == None:
		return defaultValue
	if side != None:
		key = prefix + 'OverSide'
		if key in elementNode.attributes:
			defaultValue = euclidean.getFloatFromValue(evaluate.getEvaluatedValueObliviously(elementNode, key)) * side
	return evaluate.getEvaluatedFloat(defaultValue, elementNode, prefix)

def getGeometryOutput(derivation, elementNode):
	'Get geometry output from paths.'
	if derivation == None:
		derivation = LineationDerivation(elementNode)
	geometryOutput = []
	for path in derivation.target:
		sideLoop = SideLoop(path)
		geometryOutput += getGeometryOutputByLoop(elementNode, sideLoop)
	return geometryOutput

def getGeometryOutputByArguments(arguments, elementNode):
	'Get vector3 vertexes from attribute dictionary by arguments.'
	return getGeometryOutput(None, elementNode)

def getGeometryOutputByLoop(elementNode, sideLoop):
	'Get geometry output by side loop.'
	sideLoop.rotate(elementNode)
	return getGeometryOutputByManipulation(elementNode, sideLoop)

def getGeometryOutputByManipulation(elementNode, sideLoop):
	'Get geometry output by manipulation.'
	sideLoop.loop = euclidean.getLoopWithoutCloseSequentialPoints( sideLoop.close, sideLoop.loop )
	return sideLoop.getManipulationPluginLoops(elementNode)

def getInradius(defaultInradius, elementNode):
	'Get inradius.'
	defaultInradius = getComplexByPrefixes(elementNode, ['demisize', 'inradius'], defaultInradius)
	return getComplexByMultiplierPrefix(elementNode, 2.0, 'size', defaultInradius)

def getMinimumRadius(beginComplexSegmentLength, endComplexSegmentLength, radius):
	'Get minimum radius.'
	return min(abs(radius), 0.5 * min(beginComplexSegmentLength, endComplexSegmentLength))

def getNewDerivation(elementNode):
	'Get new derivation.'
	return LineationDerivation(elementNode)

def getNumberOfBezierPoints(begin, elementNode, end):
	'Get the numberOfBezierPoints.'
	numberOfBezierPoints = int(math.ceil(0.5 * evaluate.getSidesMinimumThreeBasedOnPrecision(elementNode, abs(end - begin))))
	return evaluate.getEvaluatedInt(numberOfBezierPoints, elementNode, 'sides')

def getPackedGeometryOutputByLoop(elementNode, sideLoop):
	'Get packed geometry output by side loop.'
	sideLoop.rotate(elementNode)
	return getGeometryOutputByManipulation(elementNode, sideLoop)

def getRadiusAverage(radiusComplex):
	'Get average radius from radiusComplex.'
	return math.sqrt(radiusComplex.real * radiusComplex.imag)

def getRadiusComplex(elementNode, radius):
	'Get radius complex for elementNode.'
	radius = getComplexByPrefixes(elementNode, ['demisize', 'radius'], radius)
	return getComplexByMultiplierPrefixes(elementNode, 2.0, ['diameter', 'size'], radius)

def getStrokeRadiusByPrefix(elementNode, prefix):
	'Get strokeRadius by prefix.'
	strokeRadius = getFloatByPrefixBeginEnd(elementNode, prefix + 'strokeRadius', prefix + 'strokeWidth', 1.0)
	return getFloatByPrefixBeginEnd(elementNode, prefix + 'radius', prefix + 'diameter', strokeRadius)

def processElementNode(elementNode):
	'Process the xml element.'
	path.convertElementNode(elementNode, getGeometryOutput(None, elementNode))

def processElementNodeByFunction(elementNode, manipulationFunction):
	'Process the xml element by the manipulationFunction.'
	elementAttributesCopy = elementNode.attributes.copy()
	targets = evaluate.getElementNodesByKey(elementNode, 'target')
	for target in targets:
		targetAttributesCopy = target.attributes.copy()
		target.attributes = elementAttributesCopy
		processTargetByFunction(manipulationFunction, target)
		target.attributes = targetAttributesCopy

def processTargetByFunction(manipulationFunction, target):
	'Process the target by the manipulationFunction.'
	if target.xmlObject == None:
		print('Warning, there is no object in processTargetByFunction in lineation for:')
		print(target)
		return
	geometryOutput = []
	transformedPaths = target.xmlObject.getTransformedPaths()
	for transformedPath in transformedPaths:
		sideLoop = SideLoop(transformedPath)
		sideLoop.rotate(target)
		sideLoop.loop = euclidean.getLoopWithoutCloseSequentialPoints( sideLoop.close, sideLoop.loop )
		geometryOutput += manipulationFunction(sideLoop.close, target, sideLoop.loop, '', sideLoop.sideLength)
	if len(geometryOutput) < 1:
		print('Warning, there is no geometryOutput in processTargetByFunction in lineation for:')
		print(target)
		return
	removeChildNodesFromElementObject(target)
	path.convertElementNode(target, geometryOutput)

def removeChildNodesFromElementObject(elementNode):
	'Process the xml element by manipulationFunction.'
	elementNode.removeChildNodesFromIDNameParent()
	if elementNode.xmlObject != None:
		if elementNode.parentNode.xmlObject != None:
			if elementNode.xmlObject in elementNode.parentNode.xmlObject.archivableObjects:
				elementNode.parentNode.xmlObject.archivableObjects.remove(elementNode.xmlObject)

def setClosedAttribute(elementNode, revolutions):
	'Set the closed attribute of the elementNode.'
	closedBoolean = evaluate.getEvaluatedBoolean(revolutions <= 1, elementNode, 'closed')
	elementNode.attributes['closed'] = str(closedBoolean).lower()


class LineationDerivation:
	'Class to hold lineation variables.'
	def __init__(self, elementNode):
		'Set defaults.'
		self.target = evaluate.getTransformedPathsByKey([], elementNode, 'target')


class SideLoop:
	'Class to handle loop, side angle and side length.'
	def __init__(self, loop, sideAngle=None, sideLength=None):
		'Initialize.'
		if sideAngle == None:
			if len(loop) > 0:
				sideAngle = 2.0 * math.pi / float(len(loop))
			else:
				sideAngle = 1.0
				print('Warning, loop has no sides in SideLoop in lineation.')
		if sideLength == None:
			if len(loop) > 0:
				sideLength = euclidean.getLoopLength(loop) / float(len(loop))
			else:
				sideLength = 1.0
				print('Warning, loop has no length in SideLoop in lineation.')
		self.loop = loop
		self.sideAngle = abs(sideAngle)
		self.sideLength = abs(sideLength)
		self.close = 0.001 * sideLength

	def getManipulationPluginLoops(self, elementNode):
		'Get loop manipulated by the plugins in the manipulation paths folder.'
		xmlProcessor = elementNode.getXMLProcessor()
		matchingPlugins = evaluate.getMatchingPlugins(elementNode, xmlProcessor.manipulationMatrixDictionary)
		matchingPlugins += evaluate.getMatchingPlugins(elementNode, xmlProcessor.manipulationPathDictionary)
		matchingPlugins += evaluate.getMatchingPlugins(elementNode, xmlProcessor.manipulationShapeDictionary)
		matchingPlugins.sort(evaluate.compareExecutionOrderAscending)
		loops = [self.loop]
		for matchingPlugin in matchingPlugins:
			matchingLoops = []
			prefix = matchingPlugin.__name__.replace('_', '') + '.'
			for loop in loops:
				matchingLoops += matchingPlugin.getManipulatedPaths(self.close, elementNode, loop, prefix, self.sideLength)
			loops = matchingLoops
		return loops

	def rotate(self, elementNode):
		'Rotate.'
		rotation = math.radians(evaluate.getEvaluatedFloat(0.0, elementNode, 'rotation'))
		rotation += evaluate.getEvaluatedFloat(0.0, elementNode, 'rotationOverSide') * self.sideAngle
		if rotation != 0.0:
			planeRotation = euclidean.getWiddershinsUnitPolar( rotation )
			for vertex in self.loop:
				rotatedComplex = vertex.dropAxis() * planeRotation
				vertex.x = rotatedComplex.real
				vertex.y = rotatedComplex.imag
		if 'clockwise' in elementNode.attributes:
			isClockwise = euclidean.getBooleanFromValue(evaluate.getEvaluatedValueObliviously(elementNode, 'clockwise'))
			if isClockwise == euclidean.getIsWiddershinsByVector3( self.loop ):
				self.loop.reverse()


class Spiral:
	'Class to add a spiral.'
	def __init__(self, spiral, stepRatio):
		'Initialize.'
		self.spiral = spiral
		if self.spiral == None:
			return
		self.spiralIncrement = self.spiral * stepRatio
		self.spiralTotal = Vector3()

	def __repr__(self):
		'Get the string representation of this Spiral.'
		return self.spiral

	def getSpiralPoint(self, unitPolar, vector3):
		'Add spiral to the vector.'
		if self.spiral == None:
			return vector3
		vector3 += Vector3(unitPolar.real * self.spiralTotal.x, unitPolar.imag * self.spiralTotal.y, self.spiralTotal.z)
		self.spiralTotal += self.spiralIncrement
		return vector3
