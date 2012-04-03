"""
This page is in the table of contents.
Mill is a script to mill the outlines.

==Operation==
The default 'Activate Mill' checkbox is on.  When it is on, the functions described below will work, when it is off, the functions will not be called.

==Settings==
===Add Loops===
====Add Inner Loops====
Default is on.

When selected, the inner milling loops will be added.

====Add Outer Loops====
Default is on.

When selected, the outer milling loops will be added.

===Cross Hatch===
Default is on.

When selected, there will be alternating horizontal and vertical milling paths, if it is off there will only be horizontal milling paths.

===Loop Outset===
====Loop Inner Outset over Perimeter Width====
Default is 0.5.

Defines the ratio of the amount the inner milling loop will be outset over the edge width.

====Loop Outer Outset over Perimeter Width====
Default is one.

Defines the ratio of the amount the outer milling loop will be outset over the edge width.  The 'Loop Outer Outset over Perimeter Width' ratio should be greater than the 'Loop Inner Outset over Perimeter Width' ratio.

===Mill Width over Perimeter Width===
Default is one.

Defines the ratio of the mill line width over the edge width.  If the ratio is one, all the material will be milled.  The greater the 'Mill Width over Perimeter Width' the farther apart the mill lines will be and so less of the material will be directly milled, the remaining material might still be removed in chips if the ratio is not much greater than one.

==Examples==
The following examples mill the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and mill.py.

> python mill.py
This brings up the mill dialog.

> python mill.py Screw Holder Bottom.stl
The mill tool is parsing the file:
Screw Holder Bottom.stl
..
The mill tool has created the file:
Screw Holder Bottom_mill.gcode

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
from fabmetheus_utilities.geometry.solids import triangle_mesh
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import intercircle
from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_utilities import skeinforge_craft
from skeinforge_application.skeinforge_utilities import skeinforge_polyfile
from skeinforge_application.skeinforge_utilities import skeinforge_profile
import math
import os
import sys


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCraftedText( fileName, gcodeText = '', repository=None):
	'Mill the file or gcodeText.'
	return getCraftedTextFromText( archive.getTextIfEmpty(fileName, gcodeText), repository )

def getCraftedTextFromText(gcodeText, repository=None):
	'Mill a gcode linear move gcodeText.'
	if gcodec.isProcedureDoneOrFileIsEmpty( gcodeText, 'mill'):
		return gcodeText
	if repository == None:
		repository = settings.getReadRepository( MillRepository() )
	if not repository.activateMill.value:
		return gcodeText
	return MillSkein().getCraftedGcode(gcodeText, repository)

def getNewRepository():
	'Get new repository.'
	return MillRepository()

def getPointsFromSegmentTable(segmentTable):
	'Get the points from the segment table.'
	points = []
	segmentTableKeys = segmentTable.keys()
	segmentTableKeys.sort()
	for segmentTableKey in segmentTableKeys:
		for segment in segmentTable[segmentTableKey]:
			for endpoint in segment:
				points.append(endpoint.point)
	return points

def isPointOfTableInLoop( loop, pointTable ):
	'Determine if a point in the point table is in the loop.'
	for point in loop:
		if point in pointTable:
			return True
	return False

def writeOutput(fileName, shouldAnalyze=True):
	'Mill a gcode linear move file.'
	skeinforge_craft.writeChainTextWithNounMessage(fileName, 'mill', shouldAnalyze)


class Average:
	'A class to hold values and get the average.'
	def __init__(self):
		self.reset()

	def addValue( self, value ):
		'Add a value to the total and the number of values.'
		self.numberOfValues += 1
		self.total += value

	def getAverage(self):
		'Get the average.'
		if self.numberOfValues == 0:
			print('should never happen, self.numberOfValues in Average is zero')
			return 0.0
		return self.total / float( self.numberOfValues )

	def reset(self):
		'Set the number of values and the total to the default.'
		self.numberOfValues = 0
		self.total = 0.0


class MillRepository:
	'A class to handle the mill settings.'
	def __init__(self):
		'Set the default settings, execute title & settings fileName.'
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.mill.html', self )
		self.fileNameInput = settings.FileNameInput().getFromFileName( fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Mill', self, '')
		self.activateMill = settings.BooleanSetting().getFromValue('Activate Mill', self, True )
		settings.LabelDisplay().getFromName('- Add Loops -', self )
		self.addInnerLoops = settings.BooleanSetting().getFromValue('Add Inner Loops', self, True )
		self.addOuterLoops = settings.BooleanSetting().getFromValue('Add Outer Loops', self, True )
		self.crossHatch = settings.BooleanSetting().getFromValue('Cross Hatch', self, True )
		settings.LabelDisplay().getFromName('- Loop Outset -', self )
		self.loopInnerOutsetOverEdgeWidth = settings.FloatSpin().getFromValue( 0.3, 'Loop Inner Outset over Perimeter Width (ratio):', self, 0.7, 0.5 )
		self.loopOuterOutsetOverEdgeWidth = settings.FloatSpin().getFromValue( 0.8, 'Loop Outer Outset over Perimeter Width (ratio):', self, 1.4, 1.0 )
		self.millWidthOverEdgeWidth = settings.FloatSpin().getFromValue( 0.8, 'Mill Width over Edge Width (ratio):', self, 1.8, 1.0 )
		self.executeTitle = 'Mill'

	def execute(self):
		'Mill button has been clicked.'
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)



class MillSkein:
	'A class to mill a skein of extrusions.'
	def __init__(self):
		self.aroundPixelTable = {}
		self.average = Average()
		self.boundaryLayers = []
		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.edgeWidth = 0.6
		self.isExtruderActive = False
		self.layerIndex = 0
		self.lineIndex = 0
		self.lines = None
		self.oldLocation = None

	def addGcodeFromLoops(self, loops, z):
		'Add gcode from loops.'
		if self.oldLocation == None:
			self.oldLocation = Vector3()
		self.oldLocation.z = z
		for loop in loops:
			self.distanceFeedRate.addGcodeFromThreadZ(loop, z)
			euclidean.addToThreadsFromLoop(self.halfEdgeWidth, 'loop', loop, self.oldLocation, self)

	def addGcodeFromThreadZ( self, thread, z ):
		'Add a thread to the output.'
		self.distanceFeedRate.addGcodeFromThreadZ( thread, z )

	def addMillThreads(self):
		'Add the mill threads to the skein.'
		boundaryLayer = self.boundaryLayers[self.layerIndex]
		endpoints = euclidean.getEndpointsFromSegmentTable( boundaryLayer.segmentTable )
		if len(endpoints) < 1:
			return
		paths = euclidean.getPathsFromEndpoints(endpoints, 5.0 * self.millWidth, self.aroundPixelTable, 1.0, self.aroundWidth)
		averageZ = self.average.getAverage()
		if self.repository.addInnerLoops.value:
			self.addGcodeFromLoops( boundaryLayer.innerLoops, averageZ )
		if self.repository.addOuterLoops.value:
			self.addGcodeFromLoops( boundaryLayer.outerLoops, averageZ )
		for path in paths:
			simplifiedPath = euclidean.getSimplifiedPath( path, self.millWidth )
			self.distanceFeedRate.addGcodeFromThreadZ( simplifiedPath, averageZ )

	def addSegmentTableLoops( self, boundaryLayerIndex ):
		'Add the segment tables and loops to the boundary.'
		boundaryLayer = self.boundaryLayers[boundaryLayerIndex]
		euclidean.subtractXIntersectionsTable(boundaryLayer.outerHorizontalTable, boundaryLayer.innerHorizontalTable)
		euclidean.subtractXIntersectionsTable(boundaryLayer.outerVerticalTable, boundaryLayer.innerVerticalTable)
		boundaryLayer.horizontalSegmentTable = self.getHorizontalSegmentTableForXIntersectionsTable(
			boundaryLayer.outerHorizontalTable)
		boundaryLayer.verticalSegmentTable = self.getVerticalSegmentTableForXIntersectionsTable(
			boundaryLayer.outerVerticalTable)
		betweenPoints = getPointsFromSegmentTable(boundaryLayer.horizontalSegmentTable)
		betweenPoints += getPointsFromSegmentTable(boundaryLayer.verticalSegmentTable)
		innerPoints = euclidean.getPointsByHorizontalDictionary(self.millWidth, boundaryLayer.innerHorizontalTable)
		innerPoints += euclidean.getPointsByVerticalDictionary(self.millWidth, boundaryLayer.innerVerticalTable)
		innerPointTable = {}
		for innerPoint in innerPoints:
			innerPointTable[innerPoint] = None
		boundaryLayer.innerLoops = []
		boundaryLayer.outerLoops = []
		millRadius = 0.75 * self.millWidth
		loops = triangle_mesh.getDescendingAreaOrientedLoops(betweenPoints, betweenPoints, millRadius)
		for loop in loops:
			if isPointOfTableInLoop(loop, innerPointTable):
				boundaryLayer.innerLoops.append(loop)
			else:
				boundaryLayer.outerLoops.append(loop)
		if self.repository.crossHatch.value and boundaryLayerIndex % 2 == 1:
			boundaryLayer.segmentTable = boundaryLayer.verticalSegmentTable
		else:
			boundaryLayer.segmentTable = boundaryLayer.horizontalSegmentTable

	def getCraftedGcode(self, gcodeText, repository):
		'Parse gcode text and store the mill gcode.'
		self.repository = repository
		self.lines = archive.getTextLines(gcodeText)
		self.parseInitialization()
		self.parseBoundaries()
		for line in self.lines[self.lineIndex :]:
			self.parseLine(line)
		return self.distanceFeedRate.output.getvalue()

	def getHorizontalSegmentTableForXIntersectionsTable( self, xIntersectionsTable ):
		'Get the horizontal segment table from the xIntersectionsTable.'
		horizontalSegmentTable = {}
		xIntersectionsTableKeys = xIntersectionsTable.keys()
		xIntersectionsTableKeys.sort()
		for xIntersectionsTableKey in xIntersectionsTableKeys:
			xIntersections = xIntersectionsTable[ xIntersectionsTableKey ]
			segments = euclidean.getSegmentsFromXIntersections( xIntersections, xIntersectionsTableKey * self.millWidth )
			horizontalSegmentTable[ xIntersectionsTableKey ] = segments
		return horizontalSegmentTable

	def getHorizontalXIntersectionsTable(self, loops):
		'Get the horizontal x intersections table from the loops.'
		horizontalXIntersectionsTable = {}
		euclidean.addXIntersectionsFromLoopsForTable(loops, horizontalXIntersectionsTable, self.millWidth)
		return horizontalXIntersectionsTable

	def getVerticalSegmentTableForXIntersectionsTable( self, xIntersectionsTable ):
		'Get the vertical segment table from the xIntersectionsTable which has the x and y swapped.'
		verticalSegmentTable = {}
		xIntersectionsTableKeys = xIntersectionsTable.keys()
		xIntersectionsTableKeys.sort()
		for xIntersectionsTableKey in xIntersectionsTableKeys:
			xIntersections = xIntersectionsTable[ xIntersectionsTableKey ]
			segments = euclidean.getSegmentsFromXIntersections( xIntersections, xIntersectionsTableKey * self.millWidth )
			for segment in segments:
				for endpoint in segment:
					endpoint.point = complex( endpoint.point.imag, endpoint.point.real )
			verticalSegmentTable[ xIntersectionsTableKey ] = segments
		return verticalSegmentTable

	def parseBoundaries(self):
		'Parse the boundaries and add them to the boundary layers.'
		boundaryLoop = None
		boundaryLayer = None
		for line in self.lines[self.lineIndex :]:
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			if firstWord == '(</boundaryPerimeter>)':
				boundaryLoop = None
			elif firstWord == '(<boundaryPoint>':
				location = gcodec.getLocationFromSplitLine(None, splitLine)
				if boundaryLoop == None:
					boundaryLoop = []
					boundaryLayer.loops.append(boundaryLoop)
				boundaryLoop.append(location.dropAxis())
			elif firstWord == '(<layer>':
				boundaryLayer = euclidean.LoopLayer(float(splitLine[1]))
				self.boundaryLayers.append(boundaryLayer)
		if len(self.boundaryLayers) < 2:
			return
		for boundaryLayer in self.boundaryLayers:
			boundaryLayer.innerOutsetLoops = intercircle.getInsetSeparateLoopsFromLoops(boundaryLayer.loops, -self.loopInnerOutset)
			boundaryLayer.outerOutsetLoops = intercircle.getInsetSeparateLoopsFromLoops(boundaryLayer.loops, -self.loopOuterOutset)
			boundaryLayer.innerHorizontalTable = self.getHorizontalXIntersectionsTable( boundaryLayer.innerOutsetLoops )
			boundaryLayer.outerHorizontalTable = self.getHorizontalXIntersectionsTable( boundaryLayer.outerOutsetLoops )
			boundaryLayer.innerVerticalTable = self.getHorizontalXIntersectionsTable( euclidean.getDiagonalFlippedLoops( boundaryLayer.innerOutsetLoops ) )
			boundaryLayer.outerVerticalTable = self.getHorizontalXIntersectionsTable( euclidean.getDiagonalFlippedLoops( boundaryLayer.outerOutsetLoops ) )
		for boundaryLayerIndex in xrange( len(self.boundaryLayers) - 2, - 1, - 1 ):
			boundaryLayer = self.boundaryLayers[ boundaryLayerIndex ]
			boundaryLayerBelow = self.boundaryLayers[ boundaryLayerIndex + 1 ]
			euclidean.joinXIntersectionsTables( boundaryLayerBelow.outerHorizontalTable, boundaryLayer.outerHorizontalTable )
			euclidean.joinXIntersectionsTables( boundaryLayerBelow.outerVerticalTable, boundaryLayer.outerVerticalTable )
		for boundaryLayerIndex in xrange( 1, len(self.boundaryLayers) ):
			boundaryLayer = self.boundaryLayers[ boundaryLayerIndex ]
			boundaryLayerAbove = self.boundaryLayers[ boundaryLayerIndex - 1 ]
			euclidean.joinXIntersectionsTables( boundaryLayerAbove.innerHorizontalTable, boundaryLayer.innerHorizontalTable )
			euclidean.joinXIntersectionsTables( boundaryLayerAbove.innerVerticalTable, boundaryLayer.innerVerticalTable )
		for boundaryLayerIndex in xrange( len(self.boundaryLayers) ):
			self.addSegmentTableLoops(boundaryLayerIndex)

	def parseInitialization(self):
		'Parse gcode initialization and store the parameters.'
		for self.lineIndex in xrange(len(self.lines)):
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			self.distanceFeedRate.parseSplitLine(firstWord, splitLine)
			if firstWord == '(</extruderInitialization>)':
				self.distanceFeedRate.addTagBracketedProcedure('mill')
				return
			elif firstWord == '(<edgeWidth>':
				self.edgeWidth = float(splitLine[1])
				self.aroundWidth = 0.1 * self.edgeWidth
				self.halfEdgeWidth = 0.5 * self.edgeWidth
				self.millWidth = self.edgeWidth * self.repository.millWidthOverEdgeWidth.value
				self.loopInnerOutset = self.halfEdgeWidth + self.edgeWidth * self.repository.loopInnerOutsetOverEdgeWidth.value
				self.loopOuterOutset = self.halfEdgeWidth + self.edgeWidth * self.repository.loopOuterOutsetOverEdgeWidth.value
			self.distanceFeedRate.addLine(line)

	def parseLine(self, line):
		'Parse a gcode line and add it to the mill skein.'
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if firstWord == 'G1':
			location = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
			if self.isExtruderActive:
				self.average.addValue(location.z)
				if self.oldLocation != None:
					euclidean.addValueSegmentToPixelTable( self.oldLocation.dropAxis(), location.dropAxis(), self.aroundPixelTable, None, self.aroundWidth )
			self.oldLocation = location
		elif firstWord == 'M101':
			self.isExtruderActive = True
		elif firstWord == 'M103':
			self.isExtruderActive = False
		elif firstWord == '(<layer>':
			settings.printProgress(self.layerIndex, 'mill')
			self.aroundPixelTable = {}
			self.average.reset()
		elif firstWord == '(</layer>)':
			if len(self.boundaryLayers) > self.layerIndex:
				self.addMillThreads()
			self.layerIndex += 1
		self.distanceFeedRate.addLine(line)


def main():
	'Display the mill dialog.'
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == '__main__':
	main()
