"""
This page is in the table of contents.
Comb is a craft plugin to bend the extruder travel paths around holes in the slices, to avoid stringers.

The comb manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Comb

==Operation==
The default 'Activate Comb' checkbox is off.  When it is on, the functions described below will work, when it is off, nothing will be done.

==Settings==
===Running Jump Space===
Default: 2 mm

Defines the running jump space that is added before going from one island to another.  If the running jump space is greater than zero, the departure from the island will also be brought closer to the arrival point on the next island so that the stringer between islands will be shorter.  For an extruder with acceleration code, an extra space before leaving the island means that it will be going at high speed as it exits the island, which means the stringer between islands will be thinner.

==Examples==
The following examples comb the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and comb.py.

> python comb.py
This brings up the comb dialog.

> python comb.py Screw Holder Bottom.stl
The comb tool is parsing the file:
Screw Holder Bottom.stl
..
The comb tool has created the file:
.. Screw Holder Bottom_comb.gcode

"""

from __future__ import absolute_import
try:
	import psyco
	psyco.full()
except:
	pass
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import intercircle
from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_utilities import skeinforge_craft
from skeinforge_application.skeinforge_utilities import skeinforge_polyfile
from skeinforge_application.skeinforge_utilities import skeinforge_profile
import math
import sys


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCraftedText(fileName, text, repository=None):
	"Comb a gcode linear move text."
	return getCraftedTextFromText(archive.getTextIfEmpty(fileName, text), repository)

def getCraftedTextFromText(gcodeText, repository=None):
	"Comb a gcode linear move text."
	if gcodec.isProcedureDoneOrFileIsEmpty(gcodeText, 'comb'):
		return gcodeText
	if repository == None:
		repository = settings.getReadRepository(CombRepository())
	if not repository.activateComb.value:
		return gcodeText
	return CombSkein().getCraftedGcode(gcodeText, repository)

def getJumpPoint(begin, end, loop, runningJumpSpace):
	'Get running jump point inside loop.'
	segment = begin - end
	segmentLength = abs(segment)
	if segmentLength == 0.0:
		return begin
	segment /= segmentLength
	distancePoint = DistancePoint(begin, loop, runningJumpSpace, segment)
	if distancePoint.distance == runningJumpSpace:
		return distancePoint.point
	effectiveDistance = distancePoint.distance
	jumpPoint = distancePoint.point
	segmentLeft = complex(0.70710678118654757, -0.70710678118654757)
	distancePoint = DistancePoint(begin, loop, runningJumpSpace, segmentLeft)
	distancePoint.distance *= 0.5
	if distancePoint.distance > effectiveDistance:
		effectiveDistance = distancePoint.distance
		jumpPoint = distancePoint.point
	segmentRight = complex(0.70710678118654757, 0.70710678118654757)
	distancePoint = DistancePoint(begin, loop, runningJumpSpace, segmentRight)
	distancePoint.distance *= 0.5
	if distancePoint.distance > effectiveDistance:
		effectiveDistance = distancePoint.distance
		jumpPoint = distancePoint.point
	return jumpPoint

def getJumpPointIfInside(boundary, otherPoint, edgeWidth, runningJumpSpace):
	'Get the jump point if it is inside the boundary, otherwise return None.'
	insetBoundary = intercircle.getSimplifiedInsetFromClockwiseLoop(boundary, -edgeWidth)
	closestJumpDistanceIndex = euclidean.getClosestDistanceIndexToLine(otherPoint, insetBoundary)
	jumpIndex = (closestJumpDistanceIndex.index + 1) % len(insetBoundary)
	jumpPoint = euclidean.getClosestPointOnSegment(insetBoundary[closestJumpDistanceIndex.index], insetBoundary[jumpIndex], otherPoint)
	jumpPoint = getJumpPoint(jumpPoint, otherPoint, boundary, runningJumpSpace)
	if euclidean.isPointInsideLoop(boundary, jumpPoint):
		return jumpPoint
	return None

def getNewRepository():
	'Get new repository.'
	return CombRepository()

def getPathsByIntersectedLoop(begin, end, loop):
	'Get both paths along the loop from the point closest to the begin to the point closest to the end.'
	closestBeginDistanceIndex = euclidean.getClosestDistanceIndexToLine(begin, loop)
	closestEndDistanceIndex = euclidean.getClosestDistanceIndexToLine(end, loop)
	beginIndex = (closestBeginDistanceIndex.index + 1) % len(loop)
	endIndex = (closestEndDistanceIndex.index + 1) % len(loop)
	closestBegin = euclidean.getClosestPointOnSegment(loop[closestBeginDistanceIndex.index], loop[beginIndex], begin)
	closestEnd = euclidean.getClosestPointOnSegment(loop[closestEndDistanceIndex.index], loop[endIndex], end)
	clockwisePath = [closestBegin]
	widdershinsPath = [closestBegin]
	if closestBeginDistanceIndex.index != closestEndDistanceIndex.index:
		widdershinsPath += euclidean.getAroundLoop(beginIndex, endIndex, loop)
		clockwisePath += euclidean.getAroundLoop(endIndex, beginIndex, loop)[: : -1]
	clockwisePath.append(closestEnd)
	widdershinsPath.append(closestEnd)
	return [clockwisePath, widdershinsPath]

def writeOutput(fileName, shouldAnalyze=True):
	"Comb a gcode linear move file."
	skeinforge_craft.writeChainTextWithNounMessage(fileName, 'comb', shouldAnalyze)


class BoundarySegment:
	'A boundary and segment.'
	def __init__(self, begin):
		'Initialize'
		self.segment = [begin]

	def getSegment(self, boundarySegmentIndex, boundarySegments, edgeWidth, runningJumpSpace):
		'Get both paths along the loop from the point closest to the begin to the point closest to the end.'
		nextBoundarySegment = boundarySegments[boundarySegmentIndex + 1]
		nextBegin = nextBoundarySegment.segment[0]
		end = getJumpPointIfInside(self.boundary, nextBegin, edgeWidth, runningJumpSpace)
		if end == None:
			end = self.segment[1]
		nextBegin = getJumpPointIfInside(nextBoundarySegment.boundary, end, edgeWidth, runningJumpSpace)
		if nextBegin != None:
			nextBoundarySegment.segment[0] = nextBegin
		return (self.segment[0], end)


class CombRepository:
	"A class to handle the comb settings."
	def __init__(self):
		"Set the default settings, execute title & settings fileName."
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.comb.html', self )
		self.fileNameInput = settings.FileNameInput().getFromFileName( fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Comb', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Comb')
		self.activateComb = settings.BooleanSetting().getFromValue('Activate Comb', self, True )
		self.runningJumpSpace = settings.FloatSpin().getFromValue(0.0, 'Running Jump Space (mm):', self, 5.0, 2.0)
		self.executeTitle = 'Comb'

	def execute(self):
		"Comb button has been clicked."
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class CombSkein:
	"A class to comb a skein of extrusions."
	def __init__(self):
		'Initialize'
#		self.betweenTable = {}
		self.boundaryLoop = None
		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.extruderActive = False
		self.layer = None
		self.layerCount = settings.LayerCount()
		self.layerTable = {}
		self.layerZ = None
		self.lineIndex = 0
		self.lines = None
		self.nextLayerZ = None
		self.oldLocation = None
		self.oldZ = None
		self.operatingFeedRatePerMinute = None
		self.travelFeedRateMinute = None
		self.widdershinTable = {}

	def addGcodePathZ( self, feedRateMinute, path, z ):
		"Add a gcode path, without modifying the extruder, to the output."
		for point in path:
			self.distanceFeedRate.addGcodeMovementZWithFeedRate(feedRateMinute, point, z)

	def addIfTravel(self, splitLine):
		"Add travel move around loops if the extruder is off."
		location = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
		if not self.extruderActive and self.oldLocation != None:
			if len(self.getBoundaries()) > 0:
				highestZ = max(location.z, self.oldLocation.z)
				self.addGcodePathZ(self.travelFeedRateMinute, self.getAroundBetweenPath(self.oldLocation.dropAxis(), location.dropAxis()), highestZ)
		self.oldLocation = location

	def addToLoop(self, location):
		"Add a location to loop."
		if self.layer == None:
			if not self.oldZ in self.layerTable:
				self.layerTable[self.oldZ] = []
			self.layer = self.layerTable[self.oldZ]
		if self.boundaryLoop == None:
			self.boundaryLoop = []
			self.layer.append(self.boundaryLoop)
		self.boundaryLoop.append(location.dropAxis())

	def getAroundBetweenLineSegment(self, begin, boundaries, end):
		'Get the path around the loops in the way of the original line segment.'
		aroundBetweenLineSegment = []
		boundaries = self.getBoundaries()
		points = []
		boundaryIndexes = self.getBoundaryIndexes(begin, boundaries, end, points)
		boundaryIndexesIndex = 0
		while boundaryIndexesIndex < len(boundaryIndexes) - 1:
			if boundaryIndexes[boundaryIndexesIndex + 1] == boundaryIndexes[boundaryIndexesIndex]:
				loopFirst = boundaries[boundaryIndexes[boundaryIndexesIndex]]
				pathBetween = self.getPathBetween(loopFirst, points[boundaryIndexesIndex : boundaryIndexesIndex + 4])
				begin = points[boundaryIndexesIndex]
				end = points[boundaryIndexesIndex + 3]
				pathBetween = self.getInsidePointsAlong(begin, pathBetween[0], points) + pathBetween
				pathBetween += self.getInsidePointsAlong(end, pathBetween[-1], points)
				aroundBetweenLineSegment += pathBetween
				boundaryIndexesIndex += 2
			else:
				boundaryIndexesIndex += 1
		return aroundBetweenLineSegment

	def getAroundBetweenPath(self, begin, end):
		'Get the path around the loops in the way of the original line segment.'
		aroundBetweenPath = []
#		betweens = self.getBetweens()
		boundaries = self.getBoundaries()
		boundarySegments = self.getBoundarySegments(begin, boundaries, end)
		for boundarySegmentIndex, boundarySegment in enumerate(boundarySegments):
			segment = boundarySegment.segment
			if boundarySegmentIndex < len(boundarySegments) - 1 and self.runningJumpSpace > 0.0:
				segment = boundarySegment.getSegment(boundarySegmentIndex, boundarySegments, self.edgeWidth, self.runningJumpSpace)
			aroundBetweenPath += self.getAroundBetweenLineSegment(segment[0], boundaries, segment[1])
			if boundarySegmentIndex < len(boundarySegments) - 1:
				aroundBetweenPath.append(segment[1])
				aroundBetweenPath.append(boundarySegments[boundarySegmentIndex + 1].segment[0])
		for pointIndex in xrange(len(aroundBetweenPath) - 1, -1, -1):
			pointBefore = begin
			beforeIndex = pointIndex - 1
			if beforeIndex >= 0:
				pointBefore = aroundBetweenPath[beforeIndex]
			pointAfter = end
			afterIndex = pointIndex + 1
			if afterIndex < len(aroundBetweenPath):
				pointAfter = aroundBetweenPath[afterIndex]
			if not euclidean.isLineIntersectingLoops(boundaries, pointBefore, pointAfter):
				del aroundBetweenPath[pointIndex]
		return aroundBetweenPath

#	def getBetweens(self):
#		'Get betweens for the layer.'
#		if not self.layerZ in self.betweenTable:
#			self.betweenTable[self.layerZ] = []
#			for boundary in self.getBoundaries():
#				self.betweenTable[self.layerZ] += intercircle.getInsetLoopsFromLoop(boundary, self.betweenInset)
#		return self.betweenTable[self.layerZ]
#
	def getBoundaries(self):
		"Get boundaries for the layer."
		if self.layerZ in self.layerTable:
			return self.layerTable[self.layerZ]
		return []

	def getBoundaryIndexes(self, begin, boundaries, end, points):
		'Get boundary indexes and set the points in the way of the original line segment.'
		boundaryIndexes = []
		points.append(begin)
		switchX = []
		segment = euclidean.getNormalized(end - begin)
		segmentYMirror = complex(segment.real, - segment.imag)
		beginRotated = segmentYMirror * begin
		endRotated = segmentYMirror * end
		y = beginRotated.imag
		for boundaryIndex in xrange(len(boundaries)):
			boundary = boundaries[boundaryIndex]
			boundaryRotated = euclidean.getRotatedComplexes(segmentYMirror, boundary)
			euclidean.addXIntersectionIndexesFromLoopY(boundaryRotated, boundaryIndex, switchX, y)
		switchX.sort()
		maximumX = max(beginRotated.real, endRotated.real)
		minimumX = min(beginRotated.real, endRotated.real)
		for xIntersection in switchX:
			if xIntersection.x > minimumX and xIntersection.x < maximumX:
				point = segment * complex(xIntersection.x, y)
				points.append(point)
				boundaryIndexes.append(xIntersection.index)
		points.append(end)
		return boundaryIndexes

	def getBoundarySegments(self, begin, boundaries, end):
		'Get the path broken into boundary segments whenever a different boundary is crossed.'
		boundarySegments = []
		boundarySegment = BoundarySegment(begin)
		boundarySegments.append(boundarySegment)
		points = []
		boundaryIndexes = self.getBoundaryIndexes(begin, boundaries, end, points)
		boundaryIndexesIndex = 0
		while boundaryIndexesIndex < len(boundaryIndexes) - 1:
			if boundaryIndexes[boundaryIndexesIndex + 1] != boundaryIndexes[boundaryIndexesIndex]:
				boundarySegment.boundary = boundaries[boundaryIndexes[boundaryIndexesIndex]]
				nextBoundary = boundaries[boundaryIndexes[boundaryIndexesIndex + 1]]
				if euclidean.isWiddershins(boundarySegment.boundary) and euclidean.isWiddershins(nextBoundary):
					boundarySegment.segment.append(points[boundaryIndexesIndex + 1])
					boundarySegment = BoundarySegment(points[boundaryIndexesIndex + 2])
					boundarySegment.boundary = nextBoundary
					boundarySegments.append(boundarySegment)
					boundaryIndexesIndex += 1
			boundaryIndexesIndex += 1
		boundarySegment.segment.append(points[-1])
		return boundarySegments

	def getCraftedGcode(self, gcodeText, repository):
		"Parse gcode text and store the comb gcode."
		self.runningJumpSpace = repository.runningJumpSpace.value
		self.repository = repository
		self.lines = archive.getTextLines(gcodeText)
		self.parseInitialization()
		for lineIndex in xrange(self.lineIndex, len(self.lines)):
			line = self.lines[lineIndex]
			self.parseBoundariesLayers(line)
		for lineIndex in xrange(self.lineIndex, len(self.lines)):
			line = self.lines[lineIndex]
			self.parseLine(line)
		return self.distanceFeedRate.output.getvalue()

	def getInsidePointsAlong(self, begin, end, points):
		'Get the points along the segment if it is required to keep the path inside the widdershin boundaries.'
		segment = end - begin
		segmentLength = abs(segment)
		if segmentLength < self.quadrupleEdgeWidth:
			return []
		segmentHalfPerimeter = self.halfEdgeWidth / segmentLength * segment
		justAfterBegin = begin + segmentHalfPerimeter
		justBeforeEnd = end - segmentHalfPerimeter
		widdershins = self.getWiddershins()
		if not euclidean.isLineIntersectingLoops(widdershins, justAfterBegin, justBeforeEnd):
			return []
		numberOfSteps = 10
		stepLength = (segmentLength - self.doubleEdgeWidth) / float(numberOfSteps)
		for step in xrange(1, numberOfSteps + 1):
			along = begin + stepLength * step
			if not euclidean.isLineIntersectingLoops(widdershins, along, justBeforeEnd):
				return [along]
		return []

	def getPathBetween(self, loop, points):
		"Add a path between the edge and the fill."
		paths = getPathsByIntersectedLoop(points[1], points[2], loop)
		shortestPath = paths[int(euclidean.getPathLength(paths[1]) < euclidean.getPathLength(paths[0]))]
		if len(shortestPath) < 2:
			return shortestPath
		if abs(points[1] - shortestPath[0]) > abs(points[1] - shortestPath[-1]):
			shortestPath.reverse()
		loopWiddershins = euclidean.isWiddershins(loop)
		pathBetween = []
		for pointIndex in xrange(len(shortestPath)):
			center = shortestPath[pointIndex]
			centerPerpendicular = None
			beginIndex = pointIndex - 1
			if beginIndex >= 0:
				begin = shortestPath[beginIndex]
				centerPerpendicular = intercircle.getWiddershinsByLength(center, begin, self.edgeWidth)
			centerEnd = None
			endIndex = pointIndex + 1
			if endIndex < len(shortestPath):
				end = shortestPath[endIndex]
				centerEnd = intercircle.getWiddershinsByLength(end, center, self.edgeWidth)
			if centerPerpendicular == None:
				centerPerpendicular = centerEnd
			elif centerEnd != None:
				centerPerpendicular = 0.5 * (centerPerpendicular + centerEnd)
			between = None
			if centerPerpendicular == None:
				between = center
			if between == None:
				centerSideWiddershins = center + centerPerpendicular
				if euclidean.isPointInsideLoop(loop, centerSideWiddershins) == loopWiddershins:
					between = centerSideWiddershins
			if between == None:
				centerSideClockwise = center - centerPerpendicular
				if euclidean.isPointInsideLoop(loop, centerSideClockwise) == loopWiddershins:
					between = centerSideClockwise
			if between == None:
				between = center
			pathBetween.append(between)
		return pathBetween

	def getWiddershins(self):
		'Get widdershins for the layer.'
		if self.layerZ in self.widdershinTable:
			return self.widdershinTable[self.layerZ]
		self.widdershinTable[self.layerZ] = []
		for boundary in self.getBoundaries():
			if euclidean.isWiddershins(boundary):
				self.widdershinTable[self.layerZ].append(boundary)
		return self.widdershinTable[self.layerZ]

	def parseBoundariesLayers(self, line):
		"Parse a gcode line."
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if firstWord == 'M103':
			self.boundaryLoop = None
		elif firstWord == '(<boundaryPoint>':
			location = gcodec.getLocationFromSplitLine(None, splitLine)
			self.addToLoop(location)
		elif firstWord == '(<layer>':
			self.boundaryLoop = None
			self.layer = None
			self.oldZ = float(splitLine[1])

	def parseInitialization(self):
		'Parse gcode initialization and store the parameters.'
		for self.lineIndex in xrange(len(self.lines)):
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			self.distanceFeedRate.parseSplitLine(firstWord, splitLine)
			if firstWord == '(</extruderInitialization>)':
				self.distanceFeedRate.addTagBracketedProcedure('comb')
				return
			elif firstWord == '(<edgeWidth>':
				self.edgeWidth = float(splitLine[1])
#				self.betweenInset = 0.7 * self.edgeWidth
				self.doubleEdgeWidth = self.edgeWidth + self.edgeWidth
				self.halfEdgeWidth = 0.5 * self.edgeWidth
				self.quadrupleEdgeWidth = self.doubleEdgeWidth + self.doubleEdgeWidth
			elif firstWord == '(<travelFeedRatePerSecond>':
				self.travelFeedRateMinute = 60.0 * float(splitLine[1])
			self.distanceFeedRate.addLine(line)

	def parseLine(self, line):
		"Parse a gcode line and add it to the comb skein."
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if self.distanceFeedRate.getIsAlteration(line):
			return
		if firstWord == 'G1':
			self.addIfTravel(splitLine)
			self.layerZ = self.nextLayerZ
		elif firstWord == 'M101':
			self.extruderActive = True
		elif firstWord == 'M103':
			self.extruderActive = False
		elif firstWord == '(<layer>':
			self.layerCount.printProgressIncrement('comb')
			self.nextLayerZ = float(splitLine[1])
			if self.layerZ == None:
				self.layerZ = self.nextLayerZ
		self.distanceFeedRate.addLineCheckAlteration(line)


class DistancePoint:
	'A class to get the distance of the point along a segment inside a loop.'
	def __init__(self, begin, loop, runningJumpSpace, segment):
		'Initialize'
		self.distance = 0.0
		self.point = begin
		steps = 10
		spaceOverSteps = runningJumpSpace / float(steps)
		for numerator in xrange(1, steps + 1):
			distance = float(numerator) * spaceOverSteps
			point = begin + segment * distance
			if euclidean.isPointInsideLoop(loop, point):
				self.distance = distance
				self.point = point
			else:
				return


def main():
	"Display the comb dialog."
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == "__main__":
	main()
