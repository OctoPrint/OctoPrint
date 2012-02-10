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
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.solids import group
from fabmetheus_utilities.geometry.solids import triangle_mesh
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import intercircle
import math


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Nophead <http://hydraraptor.blogspot.com/>\nArt of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def addLineLoopsIntersections( loopLoopsIntersections, loops, pointBegin, pointEnd ):
	'Add intersections of the line with the loops.'
	normalizedSegment = pointEnd - pointBegin
	normalizedSegmentLength = abs( normalizedSegment )
	if normalizedSegmentLength <= 0.0:
		return
	lineLoopsIntersections = []
	normalizedSegment /= normalizedSegmentLength
	segmentYMirror = complex(normalizedSegment.real, -normalizedSegment.imag)
	pointBeginRotated = segmentYMirror * pointBegin
	pointEndRotated = segmentYMirror * pointEnd
	addLoopsXSegmentIntersections( lineLoopsIntersections, loops, pointBeginRotated.real, pointEndRotated.real, segmentYMirror, pointBeginRotated.imag )
	for lineLoopsIntersection in lineLoopsIntersections:
		point = complex( lineLoopsIntersection, pointBeginRotated.imag ) * normalizedSegment
		loopLoopsIntersections.append(point)

def addLineXSegmentIntersection( lineLoopsIntersections, segmentFirstX, segmentSecondX, vector3First, vector3Second, y ):
	'Add intersections of the line with the x segment.'
	xIntersection = euclidean.getXIntersectionIfExists( vector3First, vector3Second, y )
	if xIntersection == None:
		return
	if xIntersection < min( segmentFirstX, segmentSecondX ):
		return
	if xIntersection <= max( segmentFirstX, segmentSecondX ):
		lineLoopsIntersections.append( xIntersection )

def addLoopLoopsIntersections( loop, loopsLoopsIntersections, otherLoops ):
	'Add intersections of the loop with the other loops.'
	for pointIndex in xrange(len(loop)):
		pointBegin = loop[pointIndex]
		pointEnd = loop[(pointIndex + 1) % len(loop)]
		addLineLoopsIntersections( loopsLoopsIntersections, otherLoops, pointBegin, pointEnd )

def addLoopsXSegmentIntersections( lineLoopsIntersections, loops, segmentFirstX, segmentSecondX, segmentYMirror, y ):
	'Add intersections of the loops with the x segment.'
	for loop in loops:
		addLoopXSegmentIntersections( lineLoopsIntersections, loop, segmentFirstX, segmentSecondX, segmentYMirror, y )

def addLoopXSegmentIntersections( lineLoopsIntersections, loop, segmentFirstX, segmentSecondX, segmentYMirror, y ):
	'Add intersections of the loop with the x segment.'
	rotatedLoop = euclidean.getRotatedComplexes( segmentYMirror, loop )
	for pointIndex in xrange( len( rotatedLoop ) ):
		pointFirst = rotatedLoop[pointIndex]
		pointSecond = rotatedLoop[ (pointIndex + 1) % len( rotatedLoop ) ]
		addLineXSegmentIntersection( lineLoopsIntersections, segmentFirstX, segmentSecondX, pointFirst, pointSecond, y )

def getInBetweenLoopsFromLoops(loops, radius):
	'Get the in between loops from loops.'
	inBetweenLoops = []
	for loop in loops:
		inBetweenLoop = []
		for pointIndex in xrange(len(loop)):
			pointBegin = loop[pointIndex]
			pointEnd = loop[(pointIndex + 1) % len(loop)]
			intercircle.addPointsFromSegment(pointBegin, pointEnd, inBetweenLoop, radius)
		inBetweenLoops.append(inBetweenLoop)
	return inBetweenLoops

def getInsetPointsByInsetLoop( insetLoop, inside, loops, radius ):
	'Get the inset points of the inset loop inside the loops.'
	insetPointsByInsetLoop = []
	for pointIndex in xrange( len( insetLoop ) ):
		pointBegin = insetLoop[ ( pointIndex + len( insetLoop ) - 1 ) % len( insetLoop ) ]
		pointCenter = insetLoop[pointIndex]
		pointEnd = insetLoop[ (pointIndex + 1) % len( insetLoop ) ]
		if getIsInsetPointInsideLoops( inside, loops, pointBegin, pointCenter, pointEnd, radius ):
			insetPointsByInsetLoop.append( pointCenter )
	return insetPointsByInsetLoop

def getInsetPointsByInsetLoops( insetLoops, inside, loops, radius ):
	'Get the inset points of the inset loops inside the loops.'
	insetPointsByInsetLoops = []
	for insetLoop in insetLoops:
		insetPointsByInsetLoops += getInsetPointsByInsetLoop( insetLoop, inside, loops, radius )
	return insetPointsByInsetLoops

def getIsInsetPointInsideLoops( inside, loops, pointBegin, pointCenter, pointEnd, radius ):
	'Determine if the inset point is inside the loops.'
	centerMinusBegin = euclidean.getNormalized( pointCenter - pointBegin )
	centerMinusBeginWiddershins = complex( - centerMinusBegin.imag, centerMinusBegin.real )
	endMinusCenter = euclidean.getNormalized( pointEnd - pointCenter )
	endMinusCenterWiddershins = complex( - endMinusCenter.imag, endMinusCenter.real )
	widdershinsNormalized = euclidean.getNormalized( centerMinusBeginWiddershins + endMinusCenterWiddershins ) * radius
	return euclidean.getIsInFilledRegion( loops,  pointCenter + widdershinsNormalized ) == inside

def getLoopsDifference(importRadius, loopLists):
	'Get difference loops.'
	halfImportRadius = 0.5 * importRadius # so that there are no misses on shallow angles
	radiusSide = 0.01 * importRadius
	negativeLoops = getLoopsUnion(importRadius, loopLists[1 :])
	intercircle.directLoops(False, negativeLoops)
	positiveLoops = loopLists[0]
	intercircle.directLoops(True, positiveLoops)
	corners = getInsetPointsByInsetLoops(negativeLoops, True, positiveLoops, radiusSide)
	corners += getInsetPointsByInsetLoops(positiveLoops, False, negativeLoops, radiusSide)
	allPoints = corners[:]
	allPoints += getInsetPointsByInsetLoops(getInBetweenLoopsFromLoops(negativeLoops, halfImportRadius), True, positiveLoops, radiusSide)
	allPoints += getInsetPointsByInsetLoops(getInBetweenLoopsFromLoops(positiveLoops, halfImportRadius), False, negativeLoops, radiusSide)
	return triangle_mesh.getDescendingAreaOrientedLoops(allPoints, corners, importRadius)

def getLoopsIntersection(importRadius, loopLists):
	'Get intersection loops.'
	intercircle.directLoopLists(True, loopLists)
	if len(loopLists) < 1:
		return []
	if len(loopLists) < 2:
		return loopLists[0]
	intercircle.directLoopLists(True, loopLists)
	loopsIntersection = loopLists[0]
	for loopList in loopLists[1 :]:
		loopsIntersection = getLoopsIntersectionByPair(importRadius, loopsIntersection, loopList)
	return loopsIntersection

def getLoopsIntersectionByPair(importRadius, loopsFirst, loopsLast):
	'Get intersection loops for a pair of loop lists.'
	halfImportRadius = 0.5 * importRadius # so that there are no misses on shallow angles
	radiusSide = 0.01 * importRadius
	corners = []
	corners += getInsetPointsByInsetLoops(loopsFirst, True, loopsLast, radiusSide)
	corners += getInsetPointsByInsetLoops(loopsLast, True, loopsFirst, radiusSide)
	allPoints = corners[:]
	allPoints += getInsetPointsByInsetLoops(getInBetweenLoopsFromLoops(loopsFirst, halfImportRadius), True, loopsLast, radiusSide)
	allPoints += getInsetPointsByInsetLoops(getInBetweenLoopsFromLoops(loopsLast, halfImportRadius), True, loopsFirst, radiusSide)
	return triangle_mesh.getDescendingAreaOrientedLoops(allPoints, corners, importRadius)

def getLoopsListsIntersections( loopsList ):
	'Get intersections betweens the loops lists.'
	loopsListsIntersections = []
	for loopsIndex in xrange( len( loopsList ) ):
		loops = loopsList[ loopsIndex ]
		for otherLoops in loopsList[ : loopsIndex ]:
			loopsListsIntersections += getLoopsLoopsIntersections( loops, otherLoops )
	return loopsListsIntersections

def getLoopsLoopsIntersections( loops, otherLoops ):
	'Get all the intersections of the loops with the other loops.'
	loopsLoopsIntersections = []
	for loop in loops:
		addLoopLoopsIntersections( loop, loopsLoopsIntersections, otherLoops )
	return loopsLoopsIntersections

def getLoopsUnion(importRadius, loopLists):
	'Get joined loops sliced through shape.'
	allPoints = []
	corners = getLoopsListsIntersections(loopLists)
	radiusSideNegative = -0.01 * importRadius
	intercircle.directLoopLists(True, loopLists)
	for loopListIndex in xrange(len(loopLists)):
		insetLoops = loopLists[ loopListIndex ]
		inBetweenInsetLoops = getInBetweenLoopsFromLoops(insetLoops, importRadius)
		otherLoops = euclidean.getConcatenatedList(loopLists[: loopListIndex] + loopLists[loopListIndex + 1 :])
		corners += getInsetPointsByInsetLoops(insetLoops, False, otherLoops, radiusSideNegative)
		allPoints += getInsetPointsByInsetLoops(inBetweenInsetLoops, False, otherLoops, radiusSideNegative)
	allPoints += corners[:]
	return triangle_mesh.getDescendingAreaOrientedLoops(allPoints, corners, importRadius)

def getVisibleObjectLoopsList( importRadius, visibleObjects, z ):
	'Get visible object loops list.'
	visibleObjectLoopsList = []
	for visibleObject in visibleObjects:
		visibleObjectLoops = visibleObject.getLoops(importRadius, z)
		visibleObjectLoopsList.append( visibleObjectLoops )
	return visibleObjectLoopsList


class BooleanSolid( group.Group ):
	'A boolean solid object.'
	def getDifference(self, importRadius, visibleObjectLoopsList):
		'Get subtracted loops sliced through shape.'
		return getLoopsDifference(importRadius, visibleObjectLoopsList)

	def getIntersection(self, importRadius, visibleObjectLoopsList):
		'Get intersected loops sliced through shape.'
		return getLoopsIntersection(importRadius, visibleObjectLoopsList)

	def getLoops(self, importRadius, z):
		'Get loops sliced through shape.'
		visibleObjects = evaluate.getVisibleObjects(self.archivableObjects)
		if len( visibleObjects ) < 1:
			return []
		visibleObjectLoopsList = getVisibleObjectLoopsList( importRadius, visibleObjects, z )
		loops = self.getLoopsFromObjectLoopsList(importRadius, visibleObjectLoopsList)
		return euclidean.getSimplifiedLoops( loops, importRadius )

	def getLoopsFromObjectLoopsList(self, importRadius, visibleObjectLoopsList):
		'Get loops from visible object loops list.'
		return self.operationFunction(importRadius, visibleObjectLoopsList)

	def getTransformedPaths(self):
		'Get all transformed paths.'
		importRadius = setting.getImportRadius(self.elementNode)
		loopsFromObjectLoopsList = self.getLoopsFromObjectLoopsList(importRadius, self.getComplexTransformedPathLists())
		return euclidean.getVector3Paths(loopsFromObjectLoopsList)

	def getUnion(self, importRadius, visibleObjectLoopsList):
		'Get joined loops sliced through shape.'
		return getLoopsUnion(importRadius, visibleObjectLoopsList)

	def getXMLLocalName(self):
		'Get xml class name.'
		return self.operationFunction.__name__.lower()[ len('get') : ]
