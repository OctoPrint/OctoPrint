"""
Intercircle is a collection of utilities for intersecting circles, used to get smooth loops around a collection of points and inset & outset loops.

"""

from __future__ import absolute_import
try:
	import psyco
	psyco.full()
except:
	pass
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import euclidean
import math


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


globalDecreasingRadiusMultipliers = [1.0, 0.55, 0.35, 0.2]
globalIntercircleMultiplier = 1.04 # 1.02 is enough to stop known intersection


def addCircleIntersectionLoop(circleIntersectionLoop, circleIntersections):
	'Add a circle intersection loop.'
	firstCircleIntersection = circleIntersectionLoop[0]
	circleIntersectionAhead = firstCircleIntersection
	for circleIntersectionIndex in xrange(len(circleIntersections) + 1):
		circleIntersectionAhead = circleIntersectionAhead.getCircleIntersectionAhead()
		if circleIntersectionAhead == firstCircleIntersection or circleIntersectionAhead == None:
			firstCircleIntersection.steppedOn = True
			return
		circleIntersectionAhead.addToList(circleIntersectionLoop)
	firstCircleIntersection.steppedOn = True
	print('Warning, addCircleIntersectionLoop would have gone into an endless loop.')
	print('circleIntersectionLoop')
	for circleIntersection in circleIntersectionLoop:
		print(circleIntersection)
		print(circleIntersection.circleNodeAhead)
		print(circleIntersection.circleNodeBehind)
	print('firstCircleIntersection')
	print(firstCircleIntersection)
	print('circleIntersections')
	for circleIntersection in circleIntersections:
		print(circleIntersection)

def addEndCap(begin, end, points, radius):
	'Get circular end cap.'
	beginMinusEnd = begin - end
	beginMinusEndLength = abs(beginMinusEnd)
	if beginMinusEndLength <= 0.0:
		points.append(begin)
		return
	beginMinusEnd *= radius / beginMinusEndLength
	perpendicular = complex(-beginMinusEnd.imag, beginMinusEnd.real)
	numberOfSides = 20 # to end up with close to unit length corners, 5 * 4
	numberOfPositiveSides = numberOfSides / 2
	totalAngle = 0.0
	angle = euclidean.globalTau / float(numberOfSides)
	# dotProductMultiplier to compensate for the corner outset in addInsetPointFromClockwiseTriple
	dotProductMultiplier = 2.0 - 1.0 / math.cos(0.5 * angle)
	for sideIndex in xrange(numberOfPositiveSides + 1):
		circumferentialPoint = math.sin(totalAngle) * beginMinusEnd + math.cos(totalAngle) * perpendicular
		points.append(begin + circumferentialPoint * dotProductMultiplier)
		totalAngle += angle

def addHalfPath(path, points, radius, thresholdRatio=0.9):
	'Add the points from every point on a half path and between points.'
	lessThanRadius = 0.75 * radius
	for pointIndex in xrange(len(path) - 1):
		begin = path[pointIndex]
		center = path[pointIndex + 1]
		centerBegin = getWiddershinsByLength(begin, center, radius)
		if centerBegin != None:
			addPointsFromSegment(begin + centerBegin, center + centerBegin, points, lessThanRadius, thresholdRatio)
		endIndex = pointIndex + 2
		if endIndex < len(path):
			end = path[endIndex]
			centerEnd = getWiddershinsByLength(center, end, radius)
			if centerBegin != None and centerEnd != None:
				centerPerpendicular = 0.5 * (centerBegin + centerEnd)
				points.append(center + centerPerpendicular)
				if euclidean.getCrossProduct(centerBegin, centerEnd) < 0.0:
					points.append(center + centerBegin)
					points.append(center + centerEnd)
			else:
				points.append(center)
	addEndCap(path[0], path[1], points, radius)

def addInsetPointFromClockwiseTriple(begin, center, end, loop, radius):
	'Get inset point with possible intersection from clockwise triple, out from widdershins loop.'
	centerMinusBegin = center - begin
	centerMinusBeginLength = abs(centerMinusBegin)
	centerMinusBeginClockwise = None
	if centerMinusBeginLength > 0.0:
		centerMinusBeginClockwise = complex(centerMinusBegin.imag, -centerMinusBegin.real) / centerMinusBeginLength
	endMinusCenter = end - center
	endMinusCenterLength = abs(endMinusCenter)
	endMinusCenterClockwise = None
	if endMinusCenterLength > 0.0:
		endMinusCenterClockwise = complex(endMinusCenter.imag, -endMinusCenter.real) / endMinusCenterLength
	if centerMinusBeginClockwise == None and endMinusCenterClockwise == None:
		return
	if centerMinusBeginClockwise == None:
		loop.append(center + endMinusCenterClockwise * radius)
		return
	if endMinusCenterClockwise == None:
		loop.append(center + centerMinusBeginClockwise * radius)
		return
	centerClockwise = 0.5 * (centerMinusBeginClockwise + endMinusCenterClockwise)
	dotProduct = euclidean.getDotProduct(centerMinusBeginClockwise, centerClockwise)
	loop.append(center + centerClockwise * radius / max(0.4, abs(dotProduct))) # 0.4 to avoid pointy corners

def addOrbits( distanceFeedRate, loop, orbitalFeedRatePerSecond, temperatureChangeTime, z ):
	'Add orbits with the extruder off.'
	timeInOrbit = 0.0
	while timeInOrbit < temperatureChangeTime:
		for point in loop:
			distanceFeedRate.addGcodeMovementZWithFeedRate( 60.0 * orbitalFeedRatePerSecond, point, z )
		timeInOrbit += euclidean.getLoopLength(loop) / orbitalFeedRatePerSecond

def addOrbitsIfLarge( distanceFeedRate, loop, orbitalFeedRatePerSecond, temperatureChangeTime, z ):
	'Add orbits with the extruder off if the orbits are large enough.'
	if orbitsAreLarge( loop, temperatureChangeTime ):
		addOrbits( distanceFeedRate, loop, orbitalFeedRatePerSecond, temperatureChangeTime, z )

def addPointsFromSegment( pointBegin, pointEnd, points, radius, thresholdRatio=0.9 ):
	'Add point complexes between the endpoints of a segment.'
	if radius <= 0.0:
		print('This should never happen, radius should never be zero or less in addPointsFromSegment in intercircle.')
	thresholdRadius = radius * thresholdRatio # a higher number would be faster but would leave bigger dangling loops and extra dangling loops.
	thresholdDiameter = thresholdRadius + thresholdRadius
	segment = pointEnd - pointBegin
	segmentLength = abs(segment)
	extraCircles = int( math.floor( segmentLength / thresholdDiameter ) )
	if extraCircles < 1:
		return
	if segmentLength == 0.0:
		print('Warning, segmentLength = 0.0 in intercircle.')
		print('pointBegin')
		print(pointBegin)
		print(pointEnd)
		return
	if extraCircles < 2:
		lengthIncrement = segmentLength / ( float(extraCircles) + 1.0 )
		segment *= lengthIncrement / segmentLength
		pointBegin += segment
	else:
		pointBegin += segment * thresholdDiameter / segmentLength
		remainingLength = segmentLength - thresholdDiameter - thresholdDiameter
		lengthIncrement = remainingLength / ( float(extraCircles) - 1.0 )
		segment *= lengthIncrement / segmentLength
	for circleIndex in xrange(extraCircles):
		points.append( pointBegin )
		pointBegin += segment

def directLoop(isWiddershins, loop):
	'Direct the loop.'
	if euclidean.isWiddershins(loop) != isWiddershins:
		loop.reverse()

def directLoopLists(isWiddershins, loopLists):
	'Direct the loop lists.'
	for loopList in loopLists:
		directLoops(isWiddershins, loopList)

def directLoops(isWiddershins, loops):
	'Direct the loops.'
	for loop in loops:
		directLoop(isWiddershins, loop)

def getAroundsFromLoop(loop, radius, thresholdRatio=0.9):
	'Get the arounds from the loop.'
	return getAroundsFromPoints(getPointsFromLoop(loop, radius, thresholdRatio), radius)

def getAroundsFromLoops( loops, radius, thresholdRatio=0.9 ):
	'Get the arounds from the loops.'
	return getAroundsFromPoints(getPointsFromLoops(loops, radius, thresholdRatio), radius)

def getAroundsFromPath(path, radius, thresholdRatio=0.9):
	'Get the arounds from the path.'
	radius = abs(radius)
	points = getPointsFromPath(path, radius, thresholdRatio)
	return getAroundsFromPathPoints(points, radius, thresholdRatio=0.9)

def getAroundsFromPathPoints(points, radius, thresholdRatio=0.9):
	'Get the arounds from the path.'
	centers = getCentersFromPoints(points, 0.8 * radius)
	arounds = []
	for center in centers:
		if euclidean.isWiddershins(center):
			arounds.append(euclidean.getSimplifiedPath(center, radius))
	return arounds

def getAroundsFromPaths(paths, radius, thresholdRatio=0.9):
	'Get the arounds from the path.'
	radius = abs(radius)
	points = []
	for path in paths:
		points += getPointsFromPath(path, radius, thresholdRatio)
	return getAroundsFromPathPoints(points, radius, thresholdRatio=0.9)

def getAroundsFromPoints( points, radius ):
	'Get the arounds from the points.'
	arounds = []
	radius = abs(radius)
	centers = getCentersFromPoints(points, globalIntercircleMultiplier * radius)
	for center in centers:
		inset = getSimplifiedInsetFromClockwiseLoop(center, radius)
		if isLargeSameDirection(inset, center, radius):
			arounds.append(inset)
	return arounds

def getCentersFromCircleNodes( circleNodes, radius ):
	'Get the complex centers of the circle intersection loops from circle nodes.'
	if len( circleNodes ) < 2:
		return []
	circleIntersections = getCircleIntersectionsFromCircleNodes( circleNodes )
	circleIntersectionLoops = getCircleIntersectionLoops( circleIntersections )
	return getCentersFromIntersectionLoops( circleIntersectionLoops, radius )

def getCentersFromIntersectionLoop(circleIntersectionLoop, radius):
	'Get the centers from the intersection loop.'
	loop = []
	for circleIntersection in circleIntersectionLoop:
		loop.append(circleIntersection.circleNodeAhead.actualPoint)
	return loop

def getCentersFromIntersectionLoops( circleIntersectionLoops, radius ):
	'Get the centers from the intersection loops.'
	centers = []
	for circleIntersectionLoop in circleIntersectionLoops:
		centers.append( getCentersFromIntersectionLoop( circleIntersectionLoop, radius ) )
	return centers

def getCentersFromLoop( loop, radius ):
	'Get the centers of the loop.'
	circleNodes = getCircleNodesFromLoop( loop, radius )
	return getCentersFromCircleNodes( circleNodes, radius )

def getCentersFromLoopDirection( isWiddershins, loop, radius ):
	'Get the centers of the loop which go around in the given direction.'
	centers = getCentersFromLoop( loop, radius )
	return getLoopsFromLoopsDirection( isWiddershins, centers )

def getCentersFromPoints(points, radius):
	'Get the centers from the points.'
	circleNodes = getCircleNodesFromPoints(points, abs(radius))
	return getCentersFromCircleNodes(circleNodes, abs(radius))

def getCircleIntersectionLoops( circleIntersections ):
	'Get all the loops going through the circle intersections.'
	circleIntersectionLoops = []
	for circleIntersection in circleIntersections:
		if not circleIntersection.steppedOn:
			circleIntersectionLoop = [ circleIntersection ]
			circleIntersectionLoops.append( circleIntersectionLoop )
			addCircleIntersectionLoop( circleIntersectionLoop, circleIntersections )
	return circleIntersectionLoops

def getCircleIntersectionsFromCircleNodes(circleNodes):
	'Get all the circle intersections which exist between all the circle nodes.'
	if len( circleNodes ) < 1:
		return []
	circleIntersections = []
	index = 0
	pixelTable = {}
	for circleNode in circleNodes:
		euclidean.addElementToPixelListFromPoint(circleNode, pixelTable, circleNode.dividedPoint)
	accumulatedCircleNodeTable = {}
	for circleNodeIndex in xrange(len(circleNodes)):
		circleNodeBehind = circleNodes[circleNodeIndex]
		circleNodeIndexMinusOne = circleNodeIndex - 1
		if circleNodeIndexMinusOne >= 0:
			circleNodeAdditional = circleNodes[circleNodeIndexMinusOne]
			euclidean.addElementToPixelListFromPoint(circleNodeAdditional, accumulatedCircleNodeTable, 0.5 * circleNodeAdditional.dividedPoint)
		withinNodes = circleNodeBehind.getWithinNodes(accumulatedCircleNodeTable)
		for circleNodeAhead in withinNodes:
			circleIntersectionForward = CircleIntersection(circleNodeAhead, index, circleNodeBehind)
			if not circleIntersectionForward.isWithinCircles(pixelTable):
				circleIntersections.append(circleIntersectionForward)
				circleNodeBehind.circleIntersections.append(circleIntersectionForward)
				index += 1
			circleIntersectionBackward = CircleIntersection(circleNodeBehind, index, circleNodeAhead)
			if not circleIntersectionBackward.isWithinCircles(pixelTable):
				circleIntersections.append(circleIntersectionBackward)
				circleNodeAhead.circleIntersections.append(circleIntersectionBackward)
				index += 1
	return circleIntersections

def getCircleNodesFromLoop(loop, radius, thresholdRatio=0.9):
	'Get the circle nodes from every point on a loop and between points.'
	radius = abs(radius)
	points = getPointsFromLoop( loop, radius, thresholdRatio )
	return getCircleNodesFromPoints( points, radius )

def getCircleNodesFromPoints(points, radius):
	'Get the circle nodes from a path.'
	if radius == 0.0:
		print('Warning, radius is 0 in getCircleNodesFromPoints in intercircle.')
		print(points)
		return []
	circleNodes = []
	oneOverRadius = 1.000001 / radius # to avoid problem of accidentally integral radius
	points = euclidean.getAwayPoints(points, radius)
	for point in points:
		circleNodes.append(CircleNode(oneOverRadius, point))
	return circleNodes

def getInsetLoopsFromLoop(loop, radius, thresholdRatio=0.9):
	'Get the inset loops, which might overlap.'
	if radius == 0.0:
		return [loop]
	isInset = radius > 0
	insetLoops = []
	isLoopWiddershins = euclidean.isWiddershins(loop)
	arounds = getAroundsFromLoop(loop, radius, thresholdRatio)
	for around in arounds:
		leftPoint = euclidean.getLeftPoint(around)
		shouldBeWithin = (isInset == isLoopWiddershins)
		if euclidean.isPointInsideLoop(loop, leftPoint) == shouldBeWithin:
			if isLoopWiddershins != euclidean.isWiddershins(around):
				around.reverse()
			insetLoops.append(around)
	return insetLoops

def getInsetLoopsFromLoops(loops, radius):
	'Get the inset loops, which might overlap.'
	insetLoops = []
	for loop in loops:
		insetLoops += getInsetLoopsFromLoop(loop, radius)
	return insetLoops

def getInsetLoopsFromVector3Loop(loop, radius, thresholdRatio=0.9):
	'Get the inset loops from vector3 loop, which might overlap.'
	if len(loop) < 2:
		return [loop]
	loopComplex = euclidean.getComplexPath(loop)
	loopComplexes = getInsetLoopsFromLoop(loopComplex, radius)
	return euclidean.getVector3Paths(loopComplexes, loop[0].z)

def getInsetSeparateLoopsFromLoops(loops, radius, thresholdRatio=0.9):
	'Get the separate inset loops.'
	if radius == 0.0:
		return loops
	isInset = radius > 0
	insetSeparateLoops = []
	arounds = getAroundsFromLoops(loops, abs(radius), thresholdRatio)
	for around in arounds:
		if isInset == euclidean.getIsInFilledRegion(loops, around[0]):
			if isInset:
				around.reverse()
			insetSeparateLoops.append(around)
	return insetSeparateLoops

def getInsetSeparateLoopsFromAroundLoops(loops, radius, radiusAround, thresholdRatio=0.9):
	'Get the separate inset loops.'
	if radius == 0.0:
		return loops
	isInset = radius > 0
	insetSeparateLoops = []
	radius = abs(radius)
	radiusAround = max(abs(radiusAround), radius)
	points = getPointsFromLoops(loops, radiusAround, thresholdRatio)
	centers = getCentersFromPoints(points, globalIntercircleMultiplier * radiusAround)
	for center in centers:
		inset = getSimplifiedInsetFromClockwiseLoop(center, radius)
		if isLargeSameDirection(inset, center, radius):
			if isInset == euclidean.getIsInFilledRegion(loops, inset[0]):
				if isInset:
					inset.reverse()
				insetSeparateLoops.append(inset)
	return insetSeparateLoops

def getIsLarge(loop, radius):
	'Determine if the loop is large enough.'
	return euclidean.getMaximumSpan(loop) > 2.01 * abs(radius)

def getLargestCenterOutsetLoopFromLoop(loop, radius, thresholdRatio=0.9):
	'Get the largest circle outset loop from the loop.'
	if radius == 0.0:
		return loop
	radius = abs(radius)
	points = getPointsFromLoop(loop, radius, thresholdRatio)
	centers = getCentersFromPoints(points, globalIntercircleMultiplier * radius)
	largestCenterOutset = None
	largestOutsetArea = -987654321.0
	for center in centers:
		outset = getSimplifiedInsetFromClockwiseLoop(center, radius)
		if isLargeSameDirection(outset, center, radius):
			if euclidean.isPathInsideLoop(loop, outset) != euclidean.isWiddershins(loop):
				centerOutset = CenterOutset(center, outset)
				outsetArea = abs(euclidean.getAreaLoop(outset))
				if outsetArea > largestOutsetArea:
					largestOutsetArea = outsetArea
					largestCenterOutset = centerOutset
	if largestCenterOutset == None:
		return None
	largestCenterOutset.center = euclidean.getSimplifiedLoop(largestCenterOutset.center, radius)
	return largestCenterOutset

def getLargestCenterOutsetLoopFromLoopRegardless(loop, radius):
	'Get the largest circle outset loop from the loop, even if the radius has to be shrunk and even if there is still no outset loop.'
	global globalDecreasingRadiusMultipliers
	for decreasingRadiusMultiplier in globalDecreasingRadiusMultipliers:
		decreasingRadius = radius * decreasingRadiusMultiplier
		largestCenterOutsetLoop = getLargestCenterOutsetLoopFromLoop(loop, decreasingRadius)
		if largestCenterOutsetLoop != None:
			return largestCenterOutsetLoop
	return CenterOutset(loop, loop)

def getLargestInsetLoopFromLoop(loop, radius):
	'Get the largest inset loop from the loop.'
	loops = getInsetLoopsFromLoop(loop, radius)
	return euclidean.getLargestLoop(loops)

def getLargestInsetLoopFromLoopRegardless( loop, radius ):
	'Get the largest inset loop from the loop, even if the radius has to be shrunk and even if there is still no inset loop.'
	global globalDecreasingRadiusMultipliers
	for decreasingRadiusMultiplier in globalDecreasingRadiusMultipliers:
		decreasingRadius = radius * decreasingRadiusMultiplier
		largestInsetLoop = getLargestInsetLoopFromLoop( loop, decreasingRadius )
		if len( largestInsetLoop ) > 0:
			return largestInsetLoop
	print('This should never happen, there should always be a largestInsetLoop in getLargestInsetLoopFromLoopRegardless in intercircle.')
	print(loop)
	return loop

def getLoopsFromLoopsDirection( isWiddershins, loops ):
	'Get the loops going round in a given direction.'
	directionalLoops = []
	for loop in loops:
		if euclidean.isWiddershins(loop) == isWiddershins:
			directionalLoops.append(loop)
	return directionalLoops

def getPointsFromLoop(loop, radius, thresholdRatio=0.9):
	'Get the points from every point on a loop and between points.'
	if radius == 0.0:
		print('Warning, radius is 0 in getPointsFromLoop in intercircle.')
		print(loop)
		return loop
	radius = abs(radius)
	points = []
	for pointIndex in xrange(len(loop)):
		pointBegin = loop[pointIndex]
		pointEnd = loop[(pointIndex + 1) % len(loop)]
		points.append( pointBegin )
		addPointsFromSegment( pointBegin, pointEnd, points, radius, thresholdRatio )
	return points

def getPointsFromLoops(loops, radius, thresholdRatio=0.9):
	'Get the points from every point on a loop and between points.'
	points = []
	for loop in loops:
		points += getPointsFromLoop(loop, radius, thresholdRatio)
	return points

def getPointsFromPath(path, radius, thresholdRatio=0.9):
	'Get the points from every point on a path and between points.'
	if len(path) < 1:
		return []
	if len(path) < 2:
		return path
	radius = abs(radius)
	points = []
	addHalfPath(path, points, radius, thresholdRatio)
	addHalfPath(path[: : -1], points, radius, thresholdRatio)
	return points

def getSimplifiedInsetFromClockwiseLoop(loop, radius):
	'Get loop inset from clockwise loop, out from widdershins loop.'
	inset = []
	for pointIndex, begin in enumerate(loop):
		center = loop[(pointIndex + 1) % len(loop)]
		end = loop[(pointIndex + 2) % len(loop)]
		addInsetPointFromClockwiseTriple(begin, center, end, inset, radius)
	return getWithoutIntersections(euclidean.getSimplifiedLoop(inset, radius))

def getWiddershinsByLength(begin, end, length):
	'Get the widdershins by length.'
	endMinusBegin = end - begin
	endMinusBeginLength = abs(endMinusBegin)
	if endMinusBeginLength <= 0.0:
		return None
	endMinusBegin *= length / endMinusBeginLength
	return complex(-endMinusBegin.imag, endMinusBegin.real)

def getWithoutIntersections( loop ):
	'Get loop without intersections.'
	lastLoopLength = len( loop )
	while lastLoopLength > 3:
		removeIntersection( loop )
		if len( loop ) == lastLoopLength:
			return loop
		lastLoopLength = len( loop )
	return loop

def isLargeSameDirection(inset, loop, radius):
	'Determine if the inset is in the same direction as the loop and it is large enough.'
	if euclidean.isWiddershins(inset) != euclidean.isWiddershins(loop):
		return False
	return getIsLarge(inset, radius) and len(inset) > 2

def isLoopIntersectingLoop( anotherLoop, loop ):
	'Determine if the a loop is intersecting another loop.'
	for pointIndex in xrange(len(loop)):
		pointFirst = loop[pointIndex]
		pointSecond = loop[(pointIndex + 1) % len(loop)]
		segment = pointFirst - pointSecond
		normalizedSegment = euclidean.getNormalized(segment)
		segmentYMirror = complex(normalizedSegment.real, -normalizedSegment.imag)
		segmentFirstPoint = segmentYMirror * pointFirst
		segmentSecondPoint = segmentYMirror * pointSecond
		if euclidean.isLoopIntersectingInsideXSegment( anotherLoop, segmentFirstPoint.real, segmentSecondPoint.real, segmentYMirror, segmentFirstPoint.imag ):
			return True
	return False

def orbitsAreLarge( loop, temperatureChangeTime ):
	'Determine if the orbits are large enough.'
	if len(loop) < 1:
		print('Zero length loop which was skipped over, this should never happen.')
		return False
	return temperatureChangeTime > 1.5

def removeIntersection( loop ):
	'Get loop without the first intersection.'
	for pointIndex, ahead in enumerate(loop):
		behind = loop[ ( pointIndex + len( loop ) - 1 ) % len( loop ) ]
		behindEnd = loop[ ( pointIndex + len( loop ) - 2 ) % len( loop ) ]
		behindMidpoint = 0.5 * ( behind + behindEnd )
		aheadEnd = loop[ (pointIndex + 1) % len( loop ) ]
		aheadMidpoint = 0.5 * ( ahead + aheadEnd )
		normalizedSegment = behind - behindMidpoint
		normalizedSegmentLength = abs( normalizedSegment )
		if normalizedSegmentLength > 0.0:
			normalizedSegment /= normalizedSegmentLength
			segmentYMirror = complex(normalizedSegment.real, -normalizedSegment.imag)
			behindRotated = segmentYMirror * behind
			behindMidpointRotated = segmentYMirror * behindMidpoint
			aheadRotated = segmentYMirror * ahead
			aheadMidpointRotated = segmentYMirror * aheadMidpoint
			y = behindRotated.imag
			xIntersection = euclidean.getXIntersectionIfExists( aheadRotated, aheadMidpointRotated, y )
			if xIntersection != None:
				if xIntersection > min( behindMidpointRotated.real, behindRotated.real ) and xIntersection < max( behindMidpointRotated.real, behindRotated.real ):
					intersectionPoint = normalizedSegment * complex( xIntersection, y )
					loop[ ( pointIndex + len( loop ) - 1 ) % len( loop ) ] = intersectionPoint
					del loop[pointIndex]
					return


class BoundingLoop:
	'A class to hold a bounding loop composed of a minimum complex, a maximum complex and an outset loop.'
	def __eq__(self, other):
		'Determine whether this bounding loop is identical to other one.'
		if other == None:
			return False
		return self.minimum == other.minimum and self.maximum == other.maximum and self.loop == other.loop

	def __repr__(self):
		'Get the string representation of this bounding loop.'
		return '%s, %s, %s' % ( self.minimum, self.maximum, self.loop )

	def getFromLoop( self, loop ):
		'Get the bounding loop from a path.'
		self.loop = loop
		self.maximum = euclidean.getMaximumByComplexPath(loop)
		self.minimum = euclidean.getMinimumByComplexPath(loop)
		return self

	def getOutsetBoundingLoop( self, outsetDistance ):
		'Outset the bounding rectangle and loop by a distance.'
		outsetBoundingLoop = BoundingLoop()
		outsetBoundingLoop.maximum = self.maximum + complex( outsetDistance, outsetDistance )
		outsetBoundingLoop.minimum = self.minimum - complex( outsetDistance, outsetDistance )
		greaterThanOutsetDistance = 1.1 * outsetDistance
		centers = getCentersFromLoopDirection( True, self.loop, greaterThanOutsetDistance )
		outsetBoundingLoop.loop = getSimplifiedInsetFromClockwiseLoop( centers[0], outsetDistance )
		return outsetBoundingLoop

	def isEntirelyInsideAnother( self, anotherBoundingLoop ):
		'Determine if this bounding loop is entirely inside another bounding loop.'
		if self.minimum.imag < anotherBoundingLoop.minimum.imag or self.minimum.real < anotherBoundingLoop.minimum.real:
			return False
		if self.maximum.imag > anotherBoundingLoop.maximum.imag or self.maximum.real > anotherBoundingLoop.maximum.real:
			return False
		for point in self.loop:
			if euclidean.getNumberOfIntersectionsToLeft( anotherBoundingLoop.loop, point ) % 2 == 0:
				return False
		return not isLoopIntersectingLoop( anotherBoundingLoop.loop, self.loop ) #later check for intersection on only acute angles

	def isOverlappingAnother( self, anotherBoundingLoop ):
		'Determine if this bounding loop is intersecting another bounding loop.'
		if self.isRectangleMissingAnother( anotherBoundingLoop ):
			return False
		for point in self.loop:
			if euclidean.getNumberOfIntersectionsToLeft( anotherBoundingLoop.loop, point ) % 2 == 1:
				return True
		for point in anotherBoundingLoop.loop:
			if euclidean.getNumberOfIntersectionsToLeft( self.loop, point ) % 2 == 1:
				return True
		return isLoopIntersectingLoop( anotherBoundingLoop.loop, self.loop ) #later check for intersection on only acute angles

	def isOverlappingAnotherInList( self, boundingLoops ):
		'Determine if this bounding loop is intersecting another bounding loop in a list.'
		for boundingLoop in boundingLoops:
			if self.isOverlappingAnother( boundingLoop ):
				return True
		return False

	def isRectangleMissingAnother( self, anotherBoundingLoop ):
		'Determine if the rectangle of this bounding loop is missing the rectangle of another bounding loop.'
		if self.maximum.imag < anotherBoundingLoop.minimum.imag or self.maximum.real < anotherBoundingLoop.minimum.real:
			return True
		return self.minimum.imag > anotherBoundingLoop.maximum.imag or self.minimum.real > anotherBoundingLoop.maximum.real


class CenterOutset:
	'A class to hold a center and an outset.'
	def __init__(self, center, outset):
		'Set the center and outset.'
		self.center = center
		self.outset = outset

	def __repr__(self):
		'Get the string representation of this CenterOutset.'
		return '%s\n%s' % (self.center, self.outset)


class CircleIntersection:
	'An intersection of two complex circles.'
	def __init__( self, circleNodeAhead, index, circleNodeBehind ):
		self.aheadMinusBehind = 0.5 * ( circleNodeAhead.dividedPoint - circleNodeBehind.dividedPoint )
		self.circleNodeAhead = circleNodeAhead
		self.circleNodeBehind = circleNodeBehind
		self.index = index
		self.steppedOn = False
		demichordWidth = math.sqrt( 1.0 - self.aheadMinusBehind.real * self.aheadMinusBehind.real - self.aheadMinusBehind.imag * self.aheadMinusBehind.imag )
		rotatedClockwiseQuarter = complex( self.aheadMinusBehind.imag, - self.aheadMinusBehind.real )
		rotatedClockwiseQuarterLength = abs( rotatedClockwiseQuarter )
		if rotatedClockwiseQuarterLength == 0:
			print('Warning, rotatedClockwiseQuarter in getDemichord in intercircle is 0')
			print(circleNodeAhead.dividedPoint)
			print(circleNodeBehind.dividedPoint)
			self.demichord = 0.0
		else:
			self.demichord = rotatedClockwiseQuarter * demichordWidth / rotatedClockwiseQuarterLength
		self.positionRelativeToBehind = self.aheadMinusBehind + self.demichord

	def __repr__(self):
		'Get the string representation of this CircleIntersection.'
		return '%s, %s, %s, %s' % (self.index, self.getAbsolutePosition(), self.circleNodeBehind, self.circleNodeAhead)

	def addToList( self, circleIntersectionPath ):
		'Add this to the circle intersection path, setting stepped on to be true.'
		self.steppedOn = True
		circleIntersectionPath.append(self)

	def getAbsolutePosition(self):
		'Get the absolute position.'
		return self.positionRelativeToBehind + self.circleNodeBehind.dividedPoint

	def getCircleIntersectionAhead(self):
		'Get the first circle intersection on the circle node ahead.'
		circleIntersections = self.circleNodeAhead.circleIntersections
		circleIntersectionAhead = None
		largestDot = -912345678.0
		for circleIntersection in circleIntersections:
			if not circleIntersection.steppedOn:
				circleIntersectionRelativeToMidpoint = euclidean.getNormalized(circleIntersection.positionRelativeToBehind + self.aheadMinusBehind)
				dot = euclidean.getDotProduct(self.demichord, circleIntersectionRelativeToMidpoint)
				if dot > largestDot:
					largestDot = dot
					circleIntersectionAhead = circleIntersection
		if circleIntersectionAhead == None:
			print('Warning, circleIntersectionAhead in getCircleIntersectionAhead in intercircle is None for:')
			print(self.circleNodeAhead.dividedPoint)
			print('circleIntersectionsAhead')
			for circleIntersection in circleIntersections:
				print(circleIntersection.circleNodeAhead.dividedPoint)
			print('circleIntersectionsBehind')
			for circleIntersection in self.circleNodeBehind.circleIntersections:
				print(circleIntersection.circleNodeAhead.dividedPoint)
			print('This may lead to a loop not being sliced.')
			print('If this is a problem, you may as well send a bug report, even though I probably can not fix this particular problem.')
		return circleIntersectionAhead

	def isWithinCircles(self, pixelTable):
		'Determine if this circle intersection is within the circle node circles.'
		absolutePosition = self.getAbsolutePosition()
		squareValues = euclidean.getSquareValuesFromPoint(pixelTable, absolutePosition)
		for squareValue in squareValues:
			if abs(squareValue.dividedPoint - absolutePosition) < 1.0:
				if squareValue != self.circleNodeAhead and squareValue != self.circleNodeBehind:
					return True
		return False


class CircleNode:
	'A complex node of complex circle intersections.'
	def __init__(self, oneOverRadius, point):
		self.actualPoint = point
		self.circleIntersections = []
		self.dividedPoint = point * oneOverRadius
#		self.index = index # when debugging bring back index

	def __repr__(self):
		'Get the string representation of this CircleNode.'
#		return '%s, %s, %s' % (self.index, self.dividedPoint, len(self.circleIntersections)) # when debugging bring back index
		return '%s, %s' % (self.dividedPoint, len(self.circleIntersections))

	def getWithinNodes(self, pixelTable):
		'Get the nodes this circle node is within.'
		withinNodes = []
		squareValues = euclidean.getSquareValuesFromPoint(pixelTable, 0.5 * self.dividedPoint)
		for squareValue in squareValues:
			if abs(self.dividedPoint - squareValue.dividedPoint) < 2.0:
				withinNodes.append(squareValue)
		return withinNodes
