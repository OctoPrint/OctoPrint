"""
Add material to support overhang or remove material at the overhang angle.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import lineation
from fabmetheus_utilities.geometry.geometry_utilities.evaluate_elements import setting
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import euclidean
import math


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


globalExecutionOrder = 100


def addUnsupportedPointIndexes( alongAway ):
	"Add the indexes of the unsupported points."
	addedUnsupportedPointIndexes = []
	for pointIndex in xrange( len( alongAway.loop ) ):
		point = alongAway.loop[pointIndex]
		if pointIndex not in alongAway.unsupportedPointIndexes:
			if not alongAway.getIsClockwisePointSupported(point):
				alongAway.unsupportedPointIndexes.append( pointIndex )
				addedUnsupportedPointIndexes.append( pointIndex )
	for pointIndex in addedUnsupportedPointIndexes:
		point = alongAway.loop[pointIndex]
		point.y += alongAway.maximumYPlus

def alterClockwiseSupportedPath( alongAway, elementNode ):
	"Get clockwise path with overhangs carved out."
	alongAway.bottomPoints = []
	alongAway.overhangSpan = setting.getOverhangSpan(elementNode)
	maximumY = - 987654321.0
	minimumYPointIndex = 0
	for pointIndex in xrange( len( alongAway.loop ) ):
		point = alongAway.loop[pointIndex]
		if point.y < alongAway.loop[ minimumYPointIndex ].y:
			minimumYPointIndex = pointIndex
		maximumY = max( maximumY, point.y )
	alongAway.maximumYPlus = 2.0 * ( maximumY - alongAway.loop[ minimumYPointIndex ].y )
	alongAway.loop = euclidean.getAroundLoop( minimumYPointIndex, minimumYPointIndex, alongAway.loop )
	overhangClockwise = OverhangClockwise( alongAway )
	alongAway.unsupportedPointIndexes = []
	oldUnsupportedPointIndexesLength = - 987654321.0
	while len( alongAway.unsupportedPointIndexes ) > oldUnsupportedPointIndexesLength:
		oldUnsupportedPointIndexesLength = len( alongAway.unsupportedPointIndexes )
		addUnsupportedPointIndexes( alongAway )
	for pointIndex in alongAway.unsupportedPointIndexes:
		point = alongAway.loop[pointIndex]
		point.y -= alongAway.maximumYPlus
	alongAway.unsupportedPointIndexes.sort()
	alongAway.unsupportedPointIndexLists = []
	oldUnsupportedPointIndex = - 987654321.0
	unsupportedPointIndexList = None
	for unsupportedPointIndex in alongAway.unsupportedPointIndexes:
		if unsupportedPointIndex > oldUnsupportedPointIndex + 1:
			unsupportedPointIndexList = []
			alongAway.unsupportedPointIndexLists.append( unsupportedPointIndexList )
		oldUnsupportedPointIndex = unsupportedPointIndex
		unsupportedPointIndexList.append( unsupportedPointIndex )
	alongAway.unsupportedPointIndexLists.reverse()
	for unsupportedPointIndexList in alongAway.unsupportedPointIndexLists:
		overhangClockwise.alterLoop( unsupportedPointIndexList )

def alterWiddershinsSupportedPath( alongAway, close ):
	"Get widdershins path with overhangs filled in."
	alongAway.bottomPoints = []
	alongAway.minimumY = getMinimumYByPath( alongAway.loop )
	for point in alongAway.loop:
		if point.y - alongAway.minimumY < close:
			alongAway.addToBottomPoints(point)
	ascendingYPoints = alongAway.loop[:]
	ascendingYPoints.sort( compareYAscending )
	overhangWiddershinsLeft = OverhangWiddershinsLeft( alongAway )
	overhangWiddershinsRight = OverhangWiddershinsRight( alongAway )
	for point in ascendingYPoints:
		alterWiddershinsSupportedPathByPoint( alongAway, overhangWiddershinsLeft, overhangWiddershinsRight, point )

def alterWiddershinsSupportedPathByPoint( alongAway, overhangWiddershinsLeft, overhangWiddershinsRight, point ):
	"Get widdershins path with overhangs filled in for point."
	if alongAway.getIsWiddershinsPointSupported(point):
		return
	overhangWiddershins = overhangWiddershinsLeft
	if overhangWiddershinsRight.getDistance() < overhangWiddershinsLeft.getDistance():
		overhangWiddershins = overhangWiddershinsRight
	overhangWiddershins.alterLoop()

def compareYAscending( point, pointOther ):
	"Get comparison in order to sort points in ascending y."
	if point.y < pointOther.y:
		return - 1
	return int( point.y > pointOther.y )

def getManipulatedPaths(close, elementNode, loop, prefix, sideLength):
	"Get path with overhangs removed or filled in."
	if len(loop) < 3:
		print('Warning, loop has less than three sides in getManipulatedPaths in overhang for:')
		print(elementNode)
		return [loop]
	derivation = OverhangDerivation(elementNode, prefix)
	overhangPlaneAngle = euclidean.getWiddershinsUnitPolar(0.5 * math.pi - derivation.overhangRadians)
	if derivation.overhangInclinationRadians != 0.0:
		overhangInclinationCosine = abs(math.cos(derivation.overhangInclinationRadians))
		if overhangInclinationCosine == 0.0:
			return [loop]
		imaginaryTimesCosine = overhangPlaneAngle.imag * overhangInclinationCosine
		overhangPlaneAngle = euclidean.getNormalized(complex(overhangPlaneAngle.real, imaginaryTimesCosine))
	alongAway = AlongAway(loop, overhangPlaneAngle)
	if euclidean.getIsWiddershinsByVector3(loop):
		alterWiddershinsSupportedPath(alongAway, close)
	else:
		alterClockwiseSupportedPath(alongAway, elementNode)
	return [euclidean.getLoopWithoutCloseSequentialPoints(close,  alongAway.loop)]

def getMinimumYByPath(path):
	"Get path with overhangs removed or filled in."
	minimumYByPath = path[0].y
	for point in path:
		minimumYByPath = min( minimumYByPath, point.y )
	return minimumYByPath

def getNewDerivation(elementNode, prefix, sideLength):
	'Get new derivation.'
	return OverhangDerivation(elementNode, prefix)

def processElementNode(elementNode):
	"Process the xml element."
	lineation.processElementNodeByFunction(elementNode, getManipulatedPaths)


class AlongAway:
	"Class to derive the path along the point and away from the point."
	def __init__( self, loop, overhangPlaneAngle ):
		"Initialize."
		self.loop = loop
		self.overhangPlaneAngle = overhangPlaneAngle
		self.ySupport = - self.overhangPlaneAngle.imag

	def __repr__(self):
		"Get the string representation of AlongAway."
		return '%s' % ( self.overhangPlaneAngle )

	def addToBottomPoints(self, point):
		"Add point to bottom points and set y to minimumY."
		self.bottomPoints.append(point)
		point.y = self.minimumY

	def getIsClockwisePointSupported(self, point):
		"Determine if the point on the clockwise loop is supported."
		self.point = point
		self.pointIndex = None
		self.awayIndexes = []
		numberOfIntersectionsBelow = 0
		for pointIndex in xrange( len( self.loop ) ):
			begin = self.loop[pointIndex]
			end = self.loop[ (pointIndex + 1) % len( self.loop ) ]
			if begin != point and end != point:
				self.awayIndexes.append( pointIndex )
				yIntersection = euclidean.getYIntersectionIfExists( begin.dropAxis(), end.dropAxis(), point.x )
				if yIntersection != None:
					numberOfIntersectionsBelow += ( yIntersection < point.y )
			if begin == point:
				self.pointIndex = pointIndex
		if numberOfIntersectionsBelow % 2 == 0:
			return True
		if self.pointIndex == None:
			return True
		if self.getIsPointSupportedBySegment( self.pointIndex - 1 + len( self.loop ) ):
			return True
		return self.getIsPointSupportedBySegment( self.pointIndex + 1 )

	def getIsPointSupportedBySegment( self, endIndex ):
		"Determine if the point on the widdershins loop is supported."
		endComplex = self.loop[ ( endIndex % len( self.loop ) ) ].dropAxis()
		endMinusPointComplex = euclidean.getNormalized( endComplex - self.point.dropAxis() )
		return endMinusPointComplex.imag < self.ySupport

	def getIsWiddershinsPointSupported(self, point):
		"Determine if the point on the widdershins loop is supported."
		if point.y <= self.minimumY:
			return True
		self.point = point
		self.pointIndex = None
		self.awayIndexes = []
		numberOfIntersectionsBelow = 0
		for pointIndex in xrange( len( self.loop ) ):
			begin = self.loop[pointIndex]
			end = self.loop[ (pointIndex + 1) % len( self.loop ) ]
			if begin != point and end != point:
				self.awayIndexes.append( pointIndex )
				yIntersection = euclidean.getYIntersectionIfExists( begin.dropAxis(), end.dropAxis(), point.x )
				if yIntersection != None:
					numberOfIntersectionsBelow += ( yIntersection < point.y )
			if begin == point:
				self.pointIndex = pointIndex
		if numberOfIntersectionsBelow % 2 == 1:
			return True
		if self.pointIndex == None:
			return True
		if self.getIsPointSupportedBySegment( self.pointIndex - 1 + len( self.loop ) ):
			return True
		return self.getIsPointSupportedBySegment( self.pointIndex + 1 )


class OverhangClockwise:
	"Class to get the intersection up from the point."
	def __init__( self, alongAway ):
		"Initialize."
		self.alongAway = alongAway
		self.halfRiseOverWidth = 0.5 * alongAway.overhangPlaneAngle.imag / alongAway.overhangPlaneAngle.real
		self.widthOverRise = alongAway.overhangPlaneAngle.real / alongAway.overhangPlaneAngle.imag

	def __repr__(self):
		"Get the string representation of OverhangClockwise."
		return '%s' % ( self.intersectionPlaneAngle )

	def alterLoop( self, unsupportedPointIndexes ):
		"Alter alongAway loop."
		unsupportedBeginIndex = unsupportedPointIndexes[0]
		unsupportedEndIndex = unsupportedPointIndexes[-1]
		beginIndex = unsupportedBeginIndex - 1
		endIndex = unsupportedEndIndex + 1
		begin = self.alongAway.loop[ beginIndex ]
		end = self.alongAway.loop[ endIndex ]
		truncatedOverhangSpan = self.alongAway.overhangSpan
		width = end.x - begin.x
		heightDifference = abs( end.y - begin.y )
		remainingWidth = width - self.widthOverRise * heightDifference
		if remainingWidth <= 0.0:
			del self.alongAway.loop[ unsupportedBeginIndex : endIndex ]
			return
		highest = begin
		supportX = begin.x + remainingWidth
		if end.y > begin.y:
			highest = end
			supportX = end.x - remainingWidth
		tipY = highest.y + self.halfRiseOverWidth * remainingWidth
		highestBetween = - 987654321.0
		for unsupportedPointIndex in unsupportedPointIndexes:
			highestBetween = max( highestBetween, self.alongAway.loop[ unsupportedPointIndex ].y )
		if highestBetween > highest.y:
			truncatedOverhangSpan = 0.0
			if highestBetween < tipY:
				below = tipY - highestBetween
				truncatedOverhangSpan = min( self.alongAway.overhangSpan, below / self.halfRiseOverWidth )
		truncatedOverhangSpanRadius = 0.5 * truncatedOverhangSpan
		if remainingWidth <= truncatedOverhangSpan:
			supportPoint = Vector3( supportX, highest.y, highest.z )
			self.alongAway.loop[ unsupportedBeginIndex : endIndex ] = [ supportPoint ]
			return
		midSupportX = 0.5 * ( supportX + highest.x )
		if truncatedOverhangSpan <= 0.0:
			supportPoint = Vector3( midSupportX, tipY, highest.z )
			self.alongAway.loop[ unsupportedBeginIndex : endIndex ] = [ supportPoint ]
			return
		supportXLeft = midSupportX - truncatedOverhangSpanRadius
		supportXRight = midSupportX + truncatedOverhangSpanRadius
		supportY = tipY - self.halfRiseOverWidth * truncatedOverhangSpan
		supportPoints = [ Vector3( supportXLeft, supportY, highest.z ), Vector3( supportXRight, supportY, highest.z ) ]
		self.alongAway.loop[ unsupportedBeginIndex : endIndex ] = supportPoints


class OverhangDerivation:
	"Class to hold overhang variables."
	def __init__(self, elementNode, prefix):
		'Set defaults.'
		self.overhangRadians = setting.getOverhangRadians(elementNode)
		self.overhangInclinationRadians = math.radians(evaluate.getEvaluatedFloat(0.0, elementNode,  prefix + 'inclination'))


class OverhangWiddershinsLeft:
	"Class to get the intersection from the point down to the left."
	def __init__( self, alongAway ):
		"Initialize."
		self.alongAway = alongAway
		self.intersectionPlaneAngle = - alongAway.overhangPlaneAngle
		self.setRatios()

	def __repr__(self):
		"Get the string representation of OverhangWiddershins."
		return '%s' % ( self.intersectionPlaneAngle )

	def alterLoop(self):
		"Alter alongAway loop."
		insertedPoint = self.alongAway.point.copy()
		if self.closestXIntersectionIndex != None:
			self.alongAway.loop = self.getIntersectLoop()
			intersectionRelativeComplex = self.closestXDistance * self.intersectionPlaneAngle
			intersectionPoint = insertedPoint + Vector3( intersectionRelativeComplex.real, intersectionRelativeComplex.imag )
			self.alongAway.loop.append( intersectionPoint )
			return
		if self.closestBottomPoint == None:
			return
		if self.closestBottomPoint not in self.alongAway.loop:
			return
		insertedPoint.x = self.bottomX
		closestBottomIndex = self.alongAway.loop.index( self.closestBottomPoint )
		self.alongAway.addToBottomPoints( insertedPoint )
		self.alongAway.loop = self.getBottomLoop( closestBottomIndex, insertedPoint )
		self.alongAway.loop.append( insertedPoint )

	def getBottomLoop( self, closestBottomIndex, insertedPoint ):
		"Get loop around bottom."
		endIndex = closestBottomIndex + len( self.alongAway.loop ) + 1
		return euclidean.getAroundLoop( self.alongAway.pointIndex, endIndex, self.alongAway.loop )

	def getDistance(self):
		"Get distance between point and closest intersection or bottom point along line."
		self.pointMinusBottomY = self.alongAway.point.y - self.alongAway.minimumY
		self.diagonalDistance = self.pointMinusBottomY * self.diagonalRatio
		if self.alongAway.pointIndex == None:
			return self.getDistanceToBottom()
		rotatedLoop = euclidean.getRotatedComplexes( self.intersectionYMirror,  euclidean.getComplexPath( self.alongAway.loop ) )
		rotatedPointComplex = rotatedLoop[ self.alongAway.pointIndex ]
		beginX = rotatedPointComplex.real
		endX = beginX + self.diagonalDistance + self.diagonalDistance
		xIntersectionIndexList = []
		for pointIndex in self.alongAway.awayIndexes:
			beginComplex = rotatedLoop[pointIndex]
			endComplex = rotatedLoop[ (pointIndex + 1) % len( rotatedLoop ) ]
			xIntersection = euclidean.getXIntersectionIfExists( beginComplex, endComplex, rotatedPointComplex.imag )
			if xIntersection != None:
				if xIntersection >= beginX and xIntersection < endX:
					xIntersectionIndexList.append( euclidean.XIntersectionIndex( pointIndex, xIntersection ) )
		self.closestXDistance = 987654321.0
		self.closestXIntersectionIndex = None
		for xIntersectionIndex in xIntersectionIndexList:
			xDistance = abs( xIntersectionIndex.x - beginX )
			if xDistance < self.closestXDistance:
				self.closestXIntersectionIndex = xIntersectionIndex
				self.closestXDistance = xDistance
		if self.closestXIntersectionIndex != None:
			return self.closestXDistance
		return self.getDistanceToBottom()

	def getDistanceToBottom(self):
		"Get distance between point and closest bottom point along line."
		self.bottomX = self.alongAway.point.x + self.pointMinusBottomY * self.xRatio
		self.closestBottomPoint = None
		closestDistanceX = 987654321.0
		for point in self.alongAway.bottomPoints:
			distanceX = abs( point.x - self.bottomX )
			if self.getIsOnside(point.x):
				if distanceX < closestDistanceX:
					closestDistanceX = distanceX
					self.closestBottomPoint = point
		return closestDistanceX + self.diagonalDistance

	def getIntersectLoop(self):
		"Get intersection loop."
		endIndex = self.closestXIntersectionIndex.index + len( self.alongAway.loop ) + 1
		return euclidean.getAroundLoop( self.alongAway.pointIndex, endIndex, self.alongAway.loop )

	def getIsOnside( self, x ):
		"Determine if x is on the side along the direction of the intersection line."
		return x <= self.alongAway.point.x

	def setRatios(self):
		"Set ratios."
		self.diagonalRatio = 1.0 / abs( self.intersectionPlaneAngle.imag )
		self.intersectionYMirror = complex( self.intersectionPlaneAngle.real, - self.intersectionPlaneAngle.imag )
		self.xRatio = self.intersectionPlaneAngle.real / abs( self.intersectionPlaneAngle.imag )


class OverhangWiddershinsRight( OverhangWiddershinsLeft ):
	"Class to get the intersection from the point down to the right."
	def __init__( self, alongAway ):
		"Initialize."
		self.alongAway = alongAway
		self.intersectionPlaneAngle = complex( alongAway.overhangPlaneAngle.real, - alongAway.overhangPlaneAngle.imag )
		self.setRatios()

	def getBottomLoop( self, closestBottomIndex, insertedPoint ):
		"Get loop around bottom."
		endIndex = self.alongAway.pointIndex + len( self.alongAway.loop ) + 1
		return euclidean.getAroundLoop( closestBottomIndex, endIndex, self.alongAway.loop )

	def getIntersectLoop(self):
		"Get intersection loop."
		beginIndex = self.closestXIntersectionIndex.index + len( self.alongAway.loop ) + 1
		endIndex = self.alongAway.pointIndex + len( self.alongAway.loop ) + 1
		return euclidean.getAroundLoop( beginIndex, endIndex, self.alongAway.loop )

	def getIsOnside( self, x ):
		"Determine if x is on the side along the direction of the intersection line."
		return x >= self.alongAway.point.x
