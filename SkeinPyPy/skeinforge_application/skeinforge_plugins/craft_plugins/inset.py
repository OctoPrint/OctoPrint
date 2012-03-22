#! /usr/bin/env python
"""
This page is in the table of contents.
Inset will inset the outside outlines by half the edge width, and outset the inside outlines by the same amount.

The inset manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Inset

==Settings==
===Add Custom Code for Temperature Reading===
Default is on.

When selected, the M105 custom code for temperature reading will be added at the beginning of the file.

===Infill in Direction of Bridge===
Default is on.

When selected, the infill will be in the direction of any bridge across a gap, so that the fill will be able to span a bridge easier.

===Loop Order Choice===
Default loop order choice is 'Ascending Area'.

When overlap is to be removed, for each loop, the overlap is checked against the list of loops already extruded.  If the latest loop overlaps an already extruded loop, the overlap is removed from the latest loop.  The loops are ordered according to their areas.

====Ascending Area====
When selected, the loops will be ordered in ascending area.  With thin walled parts, if overlap is being removed the outside of the container will not be extruded.  Holes will be the correct size.

====Descending Area====
When selected, the loops will be ordered in descending area.  With thin walled parts, if overlap is being removed the inside of the container will not be extruded.  Holes will be missing the interior wall so they will be slightly wider than model size.

===Overlap Removal Width over Perimeter Width===
Default is 0.6.

Defines the ratio of the overlap removal width over the edge width.  Any part of the extrusion that comes within the overlap removal width of another is removed.  This is to prevent the extruder from depositing two extrusions right beside each other.  If the 'Overlap Removal Width over Perimeter Width' is less than 0.2, the overlap will not be removed.

===Turn Extruder Heater Off at Shut Down===
Default is on.

When selected, the M104 S0 gcode line will be added to the end of the file to turn the extruder heater off by setting the extruder heater temperature to 0.

===Volume Fraction===
Default: 0.82

The 'Volume Fraction' is the estimated volume of the thread compared to the box defined by the layer height and infill width. This is used in dwindle, splodge, and statistic. It is in inset because inset is a required extrusion tool, earlier in the chain than dwindle and splodge. In dwindle and splodge it is used to determine the filament volume, in statistic it is used to determine the extrusion diameter.

==Examples==
The following examples inset the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and inset.py.

> python inset.py
This brings up the inset dialog.

> python inset.py Screw Holder Bottom.stl
The inset tool is parsing the file:
Screw Holder Bottom.stl
..
The inset tool has created the file:
.. Screw Holder Bottom_inset.gcode

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
import cmath
import math
import os
import sys


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def addAlreadyFilledArounds( alreadyFilledArounds, loop, radius ):
	"Add already filled loops around loop to alreadyFilledArounds."
	radius = abs(radius)
	alreadyFilledLoop = []
	slightlyGreaterThanRadius = intercircle.globalIntercircleMultiplier * radius
	muchGreaterThanRadius = 2.5 * radius
	centers = intercircle.getCentersFromLoop( loop, slightlyGreaterThanRadius )
	for center in centers:
		alreadyFilledInset = intercircle.getSimplifiedInsetFromClockwiseLoop( center, radius )
		if intercircle.isLargeSameDirection( alreadyFilledInset, center, radius ):
			alreadyFilledLoop.append( alreadyFilledInset )
	if len( alreadyFilledLoop ) > 0:
		alreadyFilledArounds.append( alreadyFilledLoop )

def addSegmentOutline( isThick, outlines, pointBegin, pointEnd, width ):
	"Add a diamond or hexagonal outline for a line segment."
	width = abs( width )
	exclusionWidth = 0.6 * width
	slope = 0.2
	if isThick:
		slope = 3.0
		exclusionWidth = 0.8 * width
	segment = pointEnd - pointBegin
	segmentLength = abs(segment)
	if segmentLength == 0.0:
		return
	normalizedSegment = segment / segmentLength
	outline = []
	segmentYMirror = complex(normalizedSegment.real, -normalizedSegment.imag)
	pointBeginRotated = segmentYMirror * pointBegin
	pointEndRotated = segmentYMirror * pointEnd
	along = 0.05
	alongLength = along * segmentLength
	if alongLength > 0.1 * exclusionWidth:
		along *= 0.1 * exclusionWidth / alongLength
	alongEnd = 1.0 - along
	remainingToHalf = 0.5 - along
	alongToWidth = exclusionWidth / slope / segmentLength
	pointBeginIntermediate = euclidean.getIntermediateLocation( along, pointBeginRotated, pointEndRotated )
	pointEndIntermediate = euclidean.getIntermediateLocation( alongEnd, pointBeginRotated, pointEndRotated )
	outline.append( pointBeginIntermediate )
	verticalWidth = complex( 0.0, exclusionWidth )
	if alongToWidth > 0.9 * remainingToHalf:
		verticalWidth = complex( 0.0, slope * remainingToHalf * segmentLength )
		middle = ( pointBeginIntermediate + pointEndIntermediate ) * 0.5
		middleDown = middle - verticalWidth
		middleUp = middle + verticalWidth
		outline.append( middleUp )
		outline.append( pointEndIntermediate )
		outline.append( middleDown )
	else:
		alongOutsideBegin = along + alongToWidth
		alongOutsideEnd = alongEnd - alongToWidth
		outsideBeginCenter = euclidean.getIntermediateLocation( alongOutsideBegin, pointBeginRotated, pointEndRotated )
		outsideBeginCenterDown = outsideBeginCenter - verticalWidth
		outsideBeginCenterUp = outsideBeginCenter + verticalWidth
		outsideEndCenter = euclidean.getIntermediateLocation( alongOutsideEnd, pointBeginRotated, pointEndRotated )
		outsideEndCenterDown = outsideEndCenter - verticalWidth
		outsideEndCenterUp = outsideEndCenter + verticalWidth
		outline.append( outsideBeginCenterUp )
		outline.append( outsideEndCenterUp )
		outline.append( pointEndIntermediate )
		outline.append( outsideEndCenterDown )
		outline.append( outsideBeginCenterDown )
	outlines.append( euclidean.getRotatedComplexes( normalizedSegment, outline ) )

def getBridgeDirection(belowLoops, layerLoops, radius):
	'Get span direction for the majority of the overhanging extrusion edge, if any.'
	if len(belowLoops) < 1:
		return None
	belowOutsetLoops = intercircle.getInsetLoopsFromLoops(belowLoops, -radius)
	bridgeRotation = complex()
	for loop in layerLoops:
		for pointIndex, point in enumerate(loop):
			previousIndex = (pointIndex + len(loop) - 1) % len(loop)
			bridgeRotation += getOverhangDirection(belowOutsetLoops, loop[previousIndex], point)
	if abs(bridgeRotation) < 0.75 * radius:
		return None
	else:
		return cmath.sqrt(bridgeRotation / abs(bridgeRotation))

def getCraftedText( fileName, text='', repository=None):
	"Inset the preface file or text."
	return getCraftedTextFromText(archive.getTextIfEmpty(fileName, text), repository)

def getCraftedTextFromText(gcodeText, repository=None):
	"Inset the preface gcode text."
	if gcodec.isProcedureDoneOrFileIsEmpty( gcodeText, 'inset'):
		return gcodeText
	if repository == None:
		repository = settings.getReadRepository( InsetRepository() )
	return InsetSkein().getCraftedGcode(gcodeText, repository)

def getDoubledRoundZ( overhangingSegment, segmentRoundZ ):
	'Get doubled plane angle around z of the overhanging segment.'
	endpoint = overhangingSegment[0]
	roundZ = endpoint.point - endpoint.otherEndpoint.point
	roundZ *= segmentRoundZ
	if abs( roundZ ) == 0.0:
		return complex()
	if roundZ.real < 0.0:
		roundZ *= - 1.0
	roundZLength = abs( roundZ )
	return roundZ * roundZ / roundZLength

def getInteriorSegments(loops, segments):
	'Get segments inside the loops.'
	interiorSegments = []
	for segment in segments:
		center = 0.5 * (segment[0].point + segment[1].point)
		if euclidean.getIsInFilledRegion(loops, center):
			interiorSegments.append(segment)
	return interiorSegments

def getIsIntersectingWithinList(loop, loopList):
	"Determine if the loop is intersecting or is within the loop list."
	leftPoint = euclidean.getLeftPoint(loop)
	for otherLoop in loopList:
		if euclidean.getNumberOfIntersectionsToLeft(otherLoop, leftPoint) % 2 == 1:
			return True
	return euclidean.isLoopIntersectingLoops(loop, loopList)

def getNewRepository():
	'Get new repository.'
	return InsetRepository()

def getOverhangDirection( belowOutsetLoops, segmentBegin, segmentEnd ):
	'Add to span direction from the endpoint segments which overhang the layer below.'
	segment = segmentEnd - segmentBegin
	normalizedSegment = euclidean.getNormalized( complex( segment.real, segment.imag ) )
	segmentYMirror = complex(normalizedSegment.real, -normalizedSegment.imag)
	segmentBegin = segmentYMirror * segmentBegin
	segmentEnd = segmentYMirror * segmentEnd
	solidXIntersectionList = []
	y = segmentBegin.imag
	solidXIntersectionList.append( euclidean.XIntersectionIndex( - 1.0, segmentBegin.real ) )
	solidXIntersectionList.append( euclidean.XIntersectionIndex( - 1.0, segmentEnd.real ) )
	for belowLoopIndex in xrange( len( belowOutsetLoops ) ):
		belowLoop = belowOutsetLoops[ belowLoopIndex ]
		rotatedOutset = euclidean.getRotatedComplexes( segmentYMirror, belowLoop )
		euclidean.addXIntersectionIndexesFromLoopY( rotatedOutset, belowLoopIndex, solidXIntersectionList, y )
	overhangingSegments = euclidean.getSegmentsFromXIntersectionIndexes( solidXIntersectionList, y )
	overhangDirection = complex()
	for overhangingSegment in overhangingSegments:
		overhangDirection += getDoubledRoundZ( overhangingSegment, normalizedSegment )
	return overhangDirection

def getSegmentsFromLoopListsPoints( loopLists, pointBegin, pointEnd ):
	"Get endpoint segments from the beginning and end of a line segment."
	normalizedSegment = pointEnd - pointBegin
	normalizedSegmentLength = abs( normalizedSegment )
	if normalizedSegmentLength == 0.0:
		return []
	normalizedSegment /= normalizedSegmentLength
	segmentYMirror = complex(normalizedSegment.real, -normalizedSegment.imag)
	pointBeginRotated = segmentYMirror * pointBegin
	pointEndRotated = segmentYMirror * pointEnd
	rotatedLoopLists = []
	for loopList in loopLists:
		rotatedLoopLists.append(euclidean.getRotatedComplexLists(segmentYMirror, loopList))
	xIntersectionIndexList = []
	xIntersectionIndexList.append( euclidean.XIntersectionIndex( - 1, pointBeginRotated.real ) )
	xIntersectionIndexList.append( euclidean.XIntersectionIndex( - 1, pointEndRotated.real ) )
	euclidean.addXIntersectionIndexesFromLoopListsY( rotatedLoopLists, xIntersectionIndexList, pointBeginRotated.imag )
	segments = euclidean.getSegmentsFromXIntersectionIndexes( xIntersectionIndexList, pointBeginRotated.imag )
	for segment in segments:
		for endpoint in segment:
			endpoint.point *= normalizedSegment
	return segments

def isCloseToLast( paths, point, radius ):
	"Determine if the point is close to the last point of the last path."
	if len(paths) < 1:
		return False
	lastPath = paths[-1]
	return abs( lastPath[-1] - point ) < radius

def isIntersectingItself( loop, width ):
	"Determine if the loop is intersecting itself."
	outlines = []
	for pointIndex in xrange(len(loop)):
		pointBegin = loop[pointIndex]
		pointEnd = loop[(pointIndex + 1) % len(loop)]
		if euclidean.isLineIntersectingLoops( outlines, pointBegin, pointEnd ):
			return True
		addSegmentOutline( False, outlines, pointBegin, pointEnd, width )
	return False

def isIntersectingWithinLists( loop, loopLists ):
	"Determine if the loop is intersecting or is within the loop lists."
	for loopList in loopLists:
		if getIsIntersectingWithinList( loop, loopList ):
			return True
	return False

def writeOutput(fileName, shouldAnalyze=True):
	"Inset the carving of a gcode file."
	skeinforge_craft.writeChainTextWithNounMessage(fileName, 'inset', shouldAnalyze)


class InsetRepository:
	"A class to handle the inset settings."
	def __init__(self):
		"Set the default settings, execute title & settings fileName."
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.inset.html', self)
		self.baseNameSynonymDictionary = {
			'Infill in Direction of Bridge' : 'carve.csv',
			'Infill Width over Thickness (ratio):' : 'fill.csv'}
		self.fileNameInput = settings.FileNameInput().getFromFileName(fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Inset', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Inset')
		self.addCustomCodeForTemperatureReading = settings.BooleanSetting().getFromValue('Add Custom Code for Temperature Reading', self, True)
		self.infillInDirectionOfBridge = settings.BooleanSetting().getFromValue('Infill in Direction of Bridge', self, True)
		self.infillWidthOverThickness = settings.FloatSpin().getFromValue(1.3, 'Infill Width over Thickness (ratio):', self, 1.7, 1.5)
		self.loopOrderChoice = settings.MenuButtonDisplay().getFromName('Loop Order Choice:', self )
		self.loopOrderAscendingArea = settings.MenuRadio().getFromMenuButtonDisplay(self.loopOrderChoice, 'Ascending Area', self, True)
		self.loopOrderDescendingArea = settings.MenuRadio().getFromMenuButtonDisplay(self.loopOrderChoice, 'Descending Area', self, False)
		self.overlapRemovalWidthOverEdgeWidth = settings.FloatSpin().getFromValue(0.3, 'Overlap Removal Width over Perimeter Width (ratio):', self, 0.9, 0.6)
		self.turnExtruderHeaterOffAtShutDown = settings.BooleanSetting().getFromValue('Turn Extruder Heater Off at Shut Down', self, True)
		self.volumeFraction = settings.FloatSpin().getFromValue(0.7, 'Volume Fraction (ratio):', self, 0.9, 0.82)
		self.executeTitle = 'Inset'

	def execute(self):
		"Inset button has been clicked."
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class InsetSkein:
	"A class to inset a skein of extrusions."
	def __init__(self):
		'Initialize.'
		self.belowLoops = []
		self.boundary = None
		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.layerCount = settings.LayerCount()
		self.lineIndex = 0
		self.loopLayer = None

	def addGcodeFromPerimeterPaths(self, isIntersectingSelf, loop, loopLayer, loopLists, radius):
		"Add the edge paths to the output."
		segments = []
		outlines = []
		thickOutlines = []
		allLoopLists = loopLists[:] + [thickOutlines]
		aroundLists = loopLists
		for pointIndex in xrange(len(loop)):
			pointBegin = loop[pointIndex]
			pointEnd = loop[(pointIndex + 1) % len(loop)]
			if isIntersectingSelf:
				if euclidean.isLineIntersectingLoops(outlines, pointBegin, pointEnd):
					segments += getSegmentsFromLoopListsPoints(allLoopLists, pointBegin, pointEnd)
				else:
					segments += getSegmentsFromLoopListsPoints(loopLists, pointBegin, pointEnd)
				addSegmentOutline(False, outlines, pointBegin, pointEnd, self.overlapRemovalWidth)
				addSegmentOutline(True, thickOutlines, pointBegin, pointEnd, self.overlapRemovalWidth)
			else:
				segments += getSegmentsFromLoopListsPoints(loopLists, pointBegin, pointEnd)
		edgePaths = []
		path = []
		muchSmallerThanRadius = 0.1 * radius
		segments = getInteriorSegments(loopLayer.loops, segments)
		for segment in segments:
			pointBegin = segment[0].point
			if not isCloseToLast(edgePaths, pointBegin, muchSmallerThanRadius):
				path = [pointBegin]
				edgePaths.append(path)
			path.append(segment[1].point)
		if len(edgePaths) > 1:
			firstPath = edgePaths[0]
			lastPath = edgePaths[-1]
			if abs(lastPath[-1] - firstPath[0]) < 0.1 * muchSmallerThanRadius:
				connectedBeginning = lastPath[: -1] + firstPath
				edgePaths[0] = connectedBeginning
				edgePaths.remove(lastPath)
		muchGreaterThanRadius = 6.0 * radius
		for edgePath in edgePaths:
			if euclidean.getPathLength(edgePath) > muchGreaterThanRadius:
				self.distanceFeedRate.addGcodeFromThreadZ(edgePath, loopLayer.z)

	def addGcodeFromRemainingLoop(self, loop, loopLayer, loopLists, radius):
		"Add the remainder of the loop which does not overlap the alreadyFilledArounds loops."
		centerOutset = intercircle.getLargestCenterOutsetLoopFromLoopRegardless(loop, radius)
		euclidean.addNestedRingBeginning(self.distanceFeedRate, centerOutset.outset, loopLayer.z)
		self.addGcodePerimeterBlockFromRemainingLoop(centerOutset.center, loopLayer, loopLists, radius)
		self.distanceFeedRate.addLine('(</boundaryPerimeter>)')
		self.distanceFeedRate.addLine('(</nestedRing>)')

	def addGcodePerimeterBlockFromRemainingLoop(self, loop, loopLayer, loopLists, radius):
		"Add the perimter block remainder of the loop which does not overlap the alreadyFilledArounds loops."
		if self.repository.overlapRemovalWidthOverEdgeWidth.value < 0.2:
			self.distanceFeedRate.addPerimeterBlock(loop, loopLayer.z)
			return
		isIntersectingSelf = isIntersectingItself(loop, self.overlapRemovalWidth)
		if isIntersectingWithinLists(loop, loopLists) or isIntersectingSelf:
			self.addGcodeFromPerimeterPaths(isIntersectingSelf, loop, loopLayer, loopLists, radius)
		else:
			self.distanceFeedRate.addPerimeterBlock(loop, loopLayer.z)
		addAlreadyFilledArounds(loopLists, loop, self.overlapRemovalWidth)

	def addInitializationToOutput(self):
		"Add initialization gcode to the output."
		if self.repository.addCustomCodeForTemperatureReading.value:
			self.distanceFeedRate.addLine('M105') # Custom code for temperature reading.

	def addInset(self, loopLayer):
		"Add inset to the layer."
		alreadyFilledArounds = []
		extrudateLoops = intercircle.getInsetLoopsFromLoops(loopLayer.loops, self.halfEdgeWidth)
		if self.repository.infillInDirectionOfBridge.value:
			bridgeRotation = getBridgeDirection(self.belowLoops, extrudateLoops, self.halfEdgeWidth)
			if bridgeRotation != None:
				self.distanceFeedRate.addTagBracketedLine('bridgeRotation', bridgeRotation)
		self.belowLoops = loopLayer.loops
		triangle_mesh.sortLoopsInOrderOfArea(not self.repository.loopOrderAscendingArea.value, extrudateLoops)
		for extrudateLoop in extrudateLoops:
			self.addGcodeFromRemainingLoop(extrudateLoop, loopLayer, alreadyFilledArounds, self.halfEdgeWidth)

	def getCraftedGcode(self, gcodeText, repository):
		"Parse gcode text and store the bevel gcode."
		self.repository = repository
		self.lines = archive.getTextLines(gcodeText)
		self.parseInitialization()
		for line in self.lines[self.lineIndex :]:
			self.parseLine(line)
		return self.distanceFeedRate.output.getvalue()

	def parseInitialization(self):
		'Parse gcode initialization and store the parameters.'
		for self.lineIndex in xrange(len(self.lines)):
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			self.distanceFeedRate.parseSplitLine(firstWord, splitLine)
			if firstWord == '(<decimalPlacesCarried>':
				self.addInitializationToOutput()
			elif firstWord == '(</extruderInitialization>)':
				self.distanceFeedRate.addTagBracketedProcedure('inset')
				return
			elif firstWord == '(<layerHeight>':
				layerHeight = float(splitLine[1])
				self.infillWidth = self.repository.infillWidthOverThickness.value * layerHeight
				self.distanceFeedRate.addTagRoundedLine('infillWidth', self.infillWidth)
				self.distanceFeedRate.addTagRoundedLine('volumeFraction', self.repository.volumeFraction.value)
			elif firstWord == '(<edgeWidth>':
				self.edgeWidth = float(splitLine[1])
				self.halfEdgeWidth = 0.5 * self.edgeWidth
				self.overlapRemovalWidth = self.edgeWidth * self.repository.overlapRemovalWidthOverEdgeWidth.value
			self.distanceFeedRate.addLine(line)

	def parseLine(self, line):
		"Parse a gcode line and add it to the inset skein."
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if firstWord == '(<boundaryPoint>':
			location = gcodec.getLocationFromSplitLine(None, splitLine)
			self.boundary.append(location.dropAxis())
		elif firstWord == '(</crafting>)':
				self.distanceFeedRate.addLine(line)
				if self.repository.turnExtruderHeaterOffAtShutDown.value:
					self.distanceFeedRate.addLine('M104 S0') # Turn extruder heater off.
				return
		elif firstWord == '(<layer>':
			self.layerCount.printProgressIncrement('inset')
			self.loopLayer = euclidean.LoopLayer(float(splitLine[1]))
			self.distanceFeedRate.addLine(line)
		elif firstWord == '(</layer>)':
			self.addInset(self.loopLayer)
			self.loopLayer = None
		elif firstWord == '(<nestedRing>)':
			self.boundary = []
			self.loopLayer.loops.append(self.boundary)
		if self.loopLayer == None:
			self.distanceFeedRate.addLine(line)


def main():
	"Display the inset dialog."
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == "__main__":
	main()
