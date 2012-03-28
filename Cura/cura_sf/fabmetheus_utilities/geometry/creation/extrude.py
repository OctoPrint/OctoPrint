"""
Boolean geometry extrusion.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import lineation
from fabmetheus_utilities.geometry.creation import solid
from fabmetheus_utilities.geometry.geometry_utilities.evaluate_elements import setting
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.solids import triangle_mesh
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities.vector3index import Vector3Index
from fabmetheus_utilities import euclidean
import math


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def addLoop(derivation, endMultiplier, loopLists, path, portionDirectionIndex, portionDirections, vertexes):
	'Add an indexed loop to the vertexes.'
	portionDirection = portionDirections[ portionDirectionIndex ]
	if portionDirection.directionReversed == True:
		loopLists.append([])
	loops = loopLists[-1]
	interpolationOffset = derivation.interpolationDictionary['offset']
	offset = interpolationOffset.getVector3ByPortion( portionDirection )
	if endMultiplier != None:
		if portionDirectionIndex == 0:
			setOffsetByMultiplier( interpolationOffset.path[1], interpolationOffset.path[0], endMultiplier, offset )
		elif portionDirectionIndex == len( portionDirections ) - 1:
			setOffsetByMultiplier( interpolationOffset.path[-2], interpolationOffset.path[-1], endMultiplier, offset )
	scale = derivation.interpolationDictionary['scale'].getComplexByPortion( portionDirection )
	twist = derivation.interpolationDictionary['twist'].getYByPortion( portionDirection )
	projectiveSpace = euclidean.ProjectiveSpace()
	if derivation.tiltTop == None:
		tilt = derivation.interpolationDictionary['tilt'].getComplexByPortion( portionDirection )
		projectiveSpace = projectiveSpace.getByTilt( tilt )
	else:
		normals = getNormals( interpolationOffset, offset, portionDirection )
		normalFirst = normals[0]
		normalAverage = getNormalAverage(normals)
		if derivation.tiltFollow and derivation.oldProjectiveSpace != None:
			projectiveSpace = derivation.oldProjectiveSpace.getNextSpace( normalAverage )
		else:
			projectiveSpace = projectiveSpace.getByBasisZTop( normalAverage, derivation.tiltTop )
		derivation.oldProjectiveSpace = projectiveSpace
		projectiveSpace.unbuckle( derivation.maximumUnbuckling, normalFirst )
	projectiveSpace = projectiveSpace.getSpaceByXYScaleAngle( twist, scale )
	loop = []
	if ( abs( projectiveSpace.basisX ) + abs( projectiveSpace.basisY ) ) < 0.0001:
		vector3Index = Vector3Index(len(vertexes))
		addOffsetAddToLists( loop, offset, vector3Index, vertexes )
		loops.append(loop)
		return
	for point in path:
		vector3Index = Vector3Index(len(vertexes))
		projectedVertex = projectiveSpace.getVector3ByPoint(point)
		vector3Index.setToVector3( projectedVertex )
		addOffsetAddToLists( loop, offset, vector3Index, vertexes )
	loops.append(loop)

def addNegatives(derivation, negatives, paths):
	'Add pillars output to negatives.'
	portionDirections = getSpacedPortionDirections(derivation.interpolationDictionary)
	for path in paths:
		loopLists = getLoopListsByPath(derivation, 1.000001, path, portionDirections)
		geometryOutput = triangle_mesh.getPillarsOutput(loopLists)
		negatives.append(geometryOutput)

def addNegativesPositives(derivation, negatives, paths, positives):
	'Add pillars output to negatives and positives.'
	portionDirections = getSpacedPortionDirections(derivation.interpolationDictionary)
	for path in paths:
		endMultiplier = None
		if not euclidean.getIsWiddershinsByVector3(path):
			endMultiplier = 1.000001
		loopLists = getLoopListsByPath(derivation, endMultiplier, path, portionDirections)
		geometryOutput = triangle_mesh.getPillarsOutput(loopLists)
		if endMultiplier == None:
			positives.append(geometryOutput)
		else:
			negatives.append(geometryOutput)

def addOffsetAddToLists(loop, offset, vector3Index, vertexes):
	'Add an indexed loop to the vertexes.'
	vector3Index += offset
	loop.append(vector3Index)
	vertexes.append(vector3Index)

def addPositives(derivation, paths, positives):
	'Add pillars output to positives.'
	portionDirections = getSpacedPortionDirections(derivation.interpolationDictionary)
	for path in paths:
		loopLists = getLoopListsByPath(derivation, None, path, portionDirections)
		geometryOutput = triangle_mesh.getPillarsOutput(loopLists)
		positives.append(geometryOutput)

def addSpacedPortionDirection( portionDirection, spacedPortionDirections ):
	'Add spaced portion directions.'
	lastSpacedPortionDirection = spacedPortionDirections[-1]
	if portionDirection.portion - lastSpacedPortionDirection.portion > 0.003:
		spacedPortionDirections.append( portionDirection )
		return
	if portionDirection.directionReversed > lastSpacedPortionDirection.directionReversed:
		spacedPortionDirections.append( portionDirection )

def addTwistPortions( interpolationTwist, remainderPortionDirection, twistPrecision ):
	'Add twist portions.'
	lastPortionDirection = interpolationTwist.portionDirections[-1]
	if remainderPortionDirection.portion == lastPortionDirection.portion:
		return
	lastTwist = interpolationTwist.getYByPortion( lastPortionDirection )
	remainderTwist = interpolationTwist.getYByPortion( remainderPortionDirection )
	twistSegments = int( math.floor( abs( remainderTwist - lastTwist ) / twistPrecision ) )
	if twistSegments < 1:
		return
	portionDifference = remainderPortionDirection.portion - lastPortionDirection.portion
	twistSegmentsPlusOne = float( twistSegments + 1 )
	for twistSegment in xrange( twistSegments ):
		additionalPortion = portionDifference * float( twistSegment + 1 ) / twistSegmentsPlusOne
		portionDirection = PortionDirection( lastPortionDirection.portion + additionalPortion )
		interpolationTwist.portionDirections.append( portionDirection )

def comparePortionDirection( portionDirection, otherPortionDirection ):
	'Comparison in order to sort portion directions in ascending order of portion then direction.'
	if portionDirection.portion > otherPortionDirection.portion:
		return 1
	if portionDirection.portion < otherPortionDirection.portion:
		return - 1
	if portionDirection.directionReversed < otherPortionDirection.directionReversed:
		return - 1
	return portionDirection.directionReversed > otherPortionDirection.directionReversed

def getGeometryOutput(derivation, elementNode):
	'Get triangle mesh from attribute dictionary.'
	if derivation == None:
		derivation = ExtrudeDerivation(elementNode)
	if len(euclidean.getConcatenatedList(derivation.target)) == 0:
		print('Warning, in extrude there are no paths.')
		print(elementNode.attributes)
		return None
	return getGeometryOutputByLoops(derivation, derivation.target)

def getGeometryOutputByArguments(arguments, elementNode):
	'Get triangle mesh from attribute dictionary by arguments.'
	return getGeometryOutput(None, elementNode)

def getGeometryOutputByLoops(derivation, loops):
	'Get geometry output by sorted, nested loops.'
	loops.sort(key=euclidean.getAreaVector3LoopAbsolute, reverse=True)
	complexLoops = euclidean.getComplexPaths(loops)
	nestedRings = []
	for loopIndex, loop in enumerate(loops):
		complexLoop = complexLoops[loopIndex]
		leftPoint = euclidean.getLeftPoint(complexLoop)
		isInFilledRegion = euclidean.getIsInFilledRegion(complexLoops[: loopIndex] + complexLoops[loopIndex + 1 :], leftPoint)
		if isInFilledRegion == euclidean.isWiddershins(complexLoop):
			loop.reverse()
		nestedRing = euclidean.NestedRing()
		nestedRing.boundary = complexLoop
		nestedRing.vector3Loop = loop
		nestedRings.append(nestedRing)
	nestedRings = euclidean.getOrderedNestedRings(nestedRings)
	nestedRings = euclidean.getFlattenedNestedRings(nestedRings)
	portionDirections = getSpacedPortionDirections(derivation.interpolationDictionary)
	if len(nestedRings) < 1:
		return {}
	if len(nestedRings) == 1:
		geometryOutput = getGeometryOutputByNestedRing(derivation, nestedRings[0], portionDirections)
		return solid.getGeometryOutputByManipulation(derivation.elementNode, geometryOutput)
	shapes = []
	for nestedRing in nestedRings:
		shapes.append(getGeometryOutputByNestedRing(derivation, nestedRing, portionDirections))
	return solid.getGeometryOutputByManipulation(derivation.elementNode, {'union' : {'shapes' : shapes}})

def getGeometryOutputByNegativesPositives(elementNode, negatives, positives):
	'Get triangle mesh from elementNode, negatives and positives.'
	positiveOutput = triangle_mesh.getUnifiedOutput(positives)
	if len(negatives) < 1:
		return solid.getGeometryOutputByManipulation(elementNode, positiveOutput)
	if len(positives) < 1:
		negativeOutput = triangle_mesh.getUnifiedOutput(negatives)
		return solid.getGeometryOutputByManipulation(elementNode, negativeOutput)
	return solid.getGeometryOutputByManipulation(elementNode, {'difference' : {'shapes' : [positiveOutput] + negatives}})

def getGeometryOutputByNestedRing(derivation, nestedRing, portionDirections):
	'Get geometry output by sorted, nested loops.'
	loopLists = getLoopListsByPath(derivation, None, nestedRing.vector3Loop, portionDirections)
	outsideOutput = triangle_mesh.getPillarsOutput(loopLists)
	if len(nestedRing.innerNestedRings) < 1:
		return outsideOutput
	shapes = [outsideOutput]
	for nestedRing.innerNestedRing in nestedRing.innerNestedRings:
		loopLists = getLoopListsByPath(derivation, 1.000001, nestedRing.innerNestedRing.vector3Loop, portionDirections)
		shapes.append(triangle_mesh.getPillarsOutput(loopLists))
	return {'difference' : {'shapes' : shapes}}

def getLoopListsByPath(derivation, endMultiplier, path, portionDirections):
	'Get loop lists from path.'
	vertexes = []
	loopLists = [[]]
	derivation.oldProjectiveSpace = None
	for portionDirectionIndex in xrange(len(portionDirections)):
		addLoop(derivation, endMultiplier, loopLists, path, portionDirectionIndex, portionDirections, vertexes)
	return loopLists

def getNewDerivation(elementNode):
	'Get new derivation.'
	return ExtrudeDerivation(elementNode)

def getNormalAverage(normals):
	'Get normal.'
	if len(normals) < 2:
		return normals[0]
	return (normals[0] + normals[1]).getNormalized()

def getNormals( interpolationOffset, offset, portionDirection ):
	'Get normals.'
	normals = []
	portionFrom = portionDirection.portion - 0.0001
	portionTo = portionDirection.portion + 0.0001
	if portionFrom >= 0.0:
		normals.append( ( offset - interpolationOffset.getVector3ByPortion( PortionDirection( portionFrom ) ) ).getNormalized() )
	if portionTo <= 1.0:
		normals.append( ( interpolationOffset.getVector3ByPortion( PortionDirection( portionTo ) ) - offset ).getNormalized() )
	return normals

def getSpacedPortionDirections( interpolationDictionary ):
	'Get sorted portion directions.'
	portionDirections = []
	for interpolationDictionaryValue in interpolationDictionary.values():
		portionDirections += interpolationDictionaryValue.portionDirections
	portionDirections.sort( comparePortionDirection )
	if len( portionDirections ) < 1:
		return []
	spacedPortionDirections = [ portionDirections[0] ]
	for portionDirection in portionDirections[1 :]:
		addSpacedPortionDirection( portionDirection, spacedPortionDirections )
	return spacedPortionDirections

def insertTwistPortions(derivation, elementNode):
	'Insert twist portions and radian the twist.'
	interpolationDictionary = derivation.interpolationDictionary
	interpolationTwist = Interpolation().getByPrefixX(elementNode, derivation.twistPathDefault, 'twist')
	interpolationDictionary['twist'] = interpolationTwist
	for point in interpolationTwist.path:
		point.y = math.radians(point.y)
	remainderPortionDirections = interpolationTwist.portionDirections[1 :]
	interpolationTwist.portionDirections = [interpolationTwist.portionDirections[0]]
	if elementNode != None:
		twistPrecision = setting.getTwistPrecisionRadians(elementNode)
	for remainderPortionDirection in remainderPortionDirections:
		addTwistPortions(interpolationTwist, remainderPortionDirection, twistPrecision)
		interpolationTwist.portionDirections.append(remainderPortionDirection)

def processElementNode(elementNode):
	'Process the xml element.'
	solid.processElementNodeByGeometry(elementNode, getGeometryOutput(None, elementNode))

def setElementNodeToEndStart(elementNode, end, start):
	'Set elementNode attribute dictionary to a tilt following path from the start to end.'
	elementNode.attributes['path'] = [start, end]
	elementNode.attributes['tiltFollow'] = 'true'
	elementNode.attributes['tiltTop'] = Vector3(0.0, 0.0, 1.0)

def setOffsetByMultiplier(begin, end, multiplier, offset):
	'Set the offset by the multiplier.'
	segment = end - begin
	delta = segment * multiplier - segment
	offset.setToVector3(offset + delta)


class ExtrudeDerivation:
	'Class to hold extrude variables.'
	def __init__(self, elementNode):
		'Initialize.'
		self.elementNode = elementNode
		self.interpolationDictionary = {}
		self.tiltFollow = evaluate.getEvaluatedBoolean(True, elementNode, 'tiltFollow')
		self.tiltTop = evaluate.getVector3ByPrefix(None, elementNode, 'tiltTop')
		self.maximumUnbuckling = evaluate.getEvaluatedFloat(5.0, elementNode, 'maximumUnbuckling')
		scalePathDefault = [Vector3(1.0, 1.0, 0.0), Vector3(1.0, 1.0, 1.0)]
		self.interpolationDictionary['scale'] = Interpolation().getByPrefixZ(elementNode, scalePathDefault, 'scale')
		self.target = evaluate.getTransformedPathsByKey([], elementNode, 'target')
		if self.tiltTop == None:
			offsetPathDefault = [Vector3(), Vector3(0.0, 0.0, 1.0)]
			self.interpolationDictionary['offset'] = Interpolation().getByPrefixZ(elementNode, offsetPathDefault, '')
			tiltPathDefault = [Vector3(), Vector3(0.0, 0.0, 1.0)]
			self.interpolationDictionary['tilt'] = Interpolation().getByPrefixZ(elementNode, tiltPathDefault, 'tilt')
			for point in self.interpolationDictionary['tilt'].path:
				point.x = math.radians(point.x)
				point.y = math.radians(point.y)
		else:
			offsetAlongDefault = [Vector3(), Vector3(1.0, 0.0, 0.0)]
			self.interpolationDictionary['offset'] = Interpolation().getByPrefixAlong(elementNode, offsetAlongDefault, '')
		self.twist = evaluate.getEvaluatedFloat(0.0, elementNode, 'twist')
		self.twistPathDefault = [Vector3(), Vector3(1.0, self.twist) ]
		insertTwistPortions(self, elementNode)


class Interpolation:
	'Class to interpolate a path.'
	def __init__(self):
		'Set index.'
		self.interpolationIndex = 0

	def __repr__(self):
		'Get the string representation of this Interpolation.'
		return str(self.__dict__)

	def getByDistances(self):
		'Get by distances.'
		beginDistance = self.distances[0]
		self.interpolationLength = self.distances[-1] - beginDistance
		self.close = abs(0.000001 * self.interpolationLength)
		self.portionDirections = []
		oldDistance = -self.interpolationLength # so the difference should not be close
		for distance in self.distances:
			deltaDistance = distance - beginDistance
			portionDirection = PortionDirection(deltaDistance / self.interpolationLength)
			if abs(deltaDistance - oldDistance) < self.close:
				portionDirection.directionReversed = True
			self.portionDirections.append(portionDirection)
			oldDistance = deltaDistance
		return self

	def getByPrefixAlong(self, elementNode, path, prefix):
		'Get interpolation from prefix and xml element along the path.'
		if len(path) < 2:
			print('Warning, path is too small in evaluate in Interpolation.')
			return
		if elementNode == None:
			self.path = path
		else:
			self.path = evaluate.getTransformedPathByPrefix(elementNode, path, prefix)
		self.distances = [0.0]
		previousPoint = self.path[0]
		for point in self.path[1 :]:
			distanceDifference = abs(point - previousPoint)
			self.distances.append(self.distances[-1] + distanceDifference)
			previousPoint = point
		return self.getByDistances()

	def getByPrefixX(self, elementNode, path, prefix):
		'Get interpolation from prefix and xml element in the z direction.'
		if len(path) < 2:
			print('Warning, path is too small in evaluate in Interpolation.')
			return
		if elementNode == None:
			self.path = path
		else:
			self.path = evaluate.getTransformedPathByPrefix(elementNode, path, prefix)
		self.distances = []
		for point in self.path:
			self.distances.append(point.x)
		return self.getByDistances()

	def getByPrefixZ(self, elementNode, path, prefix):
		'Get interpolation from prefix and xml element in the z direction.'
		if len(path) < 2:
			print('Warning, path is too small in evaluate in Interpolation.')
			return
		if elementNode == None:
			self.path = path
		else:
			self.path = evaluate.getTransformedPathByPrefix(elementNode, path, prefix)
		self.distances = []
		for point in self.path:
			self.distances.append(point.z)
		return self.getByDistances()

	def getComparison( self, first, second ):
		'Compare the first with the second.'
		if abs( second - first ) < self.close:
			return 0
		if second > first:
			return 1
		return - 1

	def getComplexByPortion( self, portionDirection ):
		'Get complex from z portion.'
		self.setInterpolationIndexFromTo( portionDirection )
		return self.oneMinusInnerPortion * self.startVertex.dropAxis() + self.innerPortion * self.endVertex.dropAxis()

	def getInnerPortion(self):
		'Get inner x portion.'
		fromDistance = self.distances[ self.interpolationIndex ]
		innerLength = self.distances[ self.interpolationIndex + 1 ] - fromDistance
		if abs( innerLength ) == 0.0:
			return 0.0
		return ( self.absolutePortion - fromDistance ) / innerLength

	def getVector3ByPortion( self, portionDirection ):
		'Get vector3 from z portion.'
		self.setInterpolationIndexFromTo( portionDirection )
		return self.oneMinusInnerPortion * self.startVertex + self.innerPortion * self.endVertex

	def getYByPortion( self, portionDirection ):
		'Get y from x portion.'
		self.setInterpolationIndexFromTo( portionDirection )
		return self.oneMinusInnerPortion * self.startVertex.y + self.innerPortion * self.endVertex.y

	def setInterpolationIndex( self, portionDirection ):
		'Set the interpolation index.'
		self.absolutePortion = self.distances[0] + self.interpolationLength * portionDirection.portion
		interpolationIndexes = range( 0, len( self.distances ) - 1 )
		if portionDirection.directionReversed:
			interpolationIndexes.reverse()
		for self.interpolationIndex in interpolationIndexes:
			begin = self.distances[ self.interpolationIndex ]
			end = self.distances[ self.interpolationIndex + 1 ]
			if self.getComparison( begin, self.absolutePortion ) != self.getComparison( end, self.absolutePortion ):
				return

	def setInterpolationIndexFromTo( self, portionDirection ):
		'Set the interpolation index, the start vertex and the end vertex.'
		self.setInterpolationIndex( portionDirection )
		self.innerPortion = self.getInnerPortion()
		self.oneMinusInnerPortion = 1.0 - self.innerPortion
		self.startVertex = self.path[ self.interpolationIndex ]
		self.endVertex = self.path[ self.interpolationIndex + 1 ]


class PortionDirection:
	'Class to hold a portion and direction.'
	def __init__( self, portion ):
		'Initialize.'
		self.directionReversed = False
		self.portion = portion

	def __repr__(self):
		'Get the string representation of this PortionDirection.'
		return '%s: %s' % ( self.portion, self.directionReversed )
