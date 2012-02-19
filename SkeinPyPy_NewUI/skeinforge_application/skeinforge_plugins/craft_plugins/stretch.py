"""
This page is in the table of contents.
Stretch is very important Skeinforge plugin that allows you to partially compensate for the fact that extruded holes are smaller then they should be.  It stretches the threads to partially compensate for filament shrinkage when extruded.

The stretch manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Stretch

Extruded holes are smaller than the model because while printing an arc the head is depositing filament on both sides of the arc but in the inside of the arc you actually need less material then on the outside of the arc. You can read more about this on the RepRap ArcCompensation page:
http://reprap.org/bin/view/Main/ArcCompensation

In general, stretch will widen holes and push corners out.  In practice the filament contraction will not be identical to the algorithm, so even once the optimal parameters are determined, the stretch script will not be able to eliminate the inaccuracies caused by contraction, but it should reduce them.

All the defaults assume that the thread sequence choice setting in fill is the edge being extruded first, then the loops, then the infill.  If the thread sequence choice is different, the optimal thread parameters will also be different.  In general, if the infill is extruded first, the infill would have to be stretched more so that even after the filament shrinkage, it would still be long enough to connect to the loop or edge.

Holes should be made with the correct area for their radius.  In other words, for example if your modeling program approximates a hole of radius one (area = pi) by making a square with the points at [(1,0), (0,1), (-1,0), (0,-1)] (area = 2), the radius should be increased by sqrt(pi/2).  This can be done in fabmetheus xml by writing:
radiusAreal='True'

in the attributes of the object or any parent of that object.  In other modeling programs, you'll have to this manually or make a script.  If area compensation is not done, then changing the stretch parameters to over compensate for too small hole areas will lead to incorrect compensation in other shapes.

==Operation==
The default 'Activate Stretch' checkbox is off.  When it is on, the functions described below will work, when it is off, the functions will not be called.

==Settings==
===Loop Stretch Over Perimeter Width===
Default is 0.1.

Defines the ratio of the maximum amount the loop aka inner shell threads will be stretched compared to the edge width, in general this value should be the same as the 'Perimeter Outside Stretch Over Perimeter Width' setting.

===Path Stretch Over Perimeter Width===
Default is zero.

Defines the ratio of the maximum amount the threads which are not loops, like the infill threads, will be stretched compared to the edge width.

===Perimeter===
====Perimeter Inside Stretch Over Perimeter Width====
Default is 0.32.

Defines the ratio of the maximum amount the inside edge thread will be stretched compared to the edge width, this is the most important setting in stretch.  The higher the value the more it will stretch the edge and the wider holes will be.  If the value is too small, the holes could be drilled out after fabrication, if the value is too high, the holes would be too wide and the part would have to junked.

====Perimeter Outside Stretch Over Perimeter Width====
Default is 0.1.

Defines the ratio of the maximum amount the outside edge thread will be stretched compared to the edge width, in general this value should be around a third of the 'Perimeter Inside Stretch Over Perimeter Width' setting.

===Stretch from Distance over Perimeter Width===
Default is two.

The stretch algorithm works by checking at each turning point on the extrusion path what the direction of the thread is at a distance of 'Stretch from Distance over Perimeter Width' times the edge width, on both sides, and moves the thread in the opposite direction.  So it takes the current turning-point, goes "Stretch from Distance over Perimeter Width" * "Perimeter Width" ahead, reads the direction at that point.  Then it goes the same distance in back in time, reads the direction at that other point.  It then moves the thread in the opposite direction, away from the center of the arc formed by these 2 points+directions.

The magnitude of the stretch increases with:
the amount that the direction of the two threads is similar and
by the '..Stretch Over Perimeter Width' ratio.

==Examples==
The following examples stretch the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and stretch.py.

> python stretch.py
This brings up the stretch dialog.

> python stretch.py Screw Holder Bottom.stl
The stretch tool is parsing the file:
Screw Holder Bottom.stl
..
The stretch tool has created the file:
.. Screw Holder Bottom_stretch.gcode

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import intercircle
from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_utilities import skeinforge_craft
from skeinforge_application.skeinforge_utilities import skeinforge_polyfile
from skeinforge_application.skeinforge_utilities import skeinforge_profile
import sys


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


#maybe speed up feedRate option
def getCraftedText( fileName, gcodeText, stretchRepository = None ):
	"Stretch a gcode linear move text."
	return getCraftedTextFromText( archive.getTextIfEmpty(fileName, gcodeText), stretchRepository )

def getCraftedTextFromText( gcodeText, stretchRepository = None ):
	"Stretch a gcode linear move text."
	if gcodec.isProcedureDoneOrFileIsEmpty( gcodeText, 'stretch'):
		return gcodeText
	if stretchRepository == None:
		stretchRepository = settings.getReadRepository( StretchRepository() )
	if not stretchRepository.activateStretch.value:
		return gcodeText
	return StretchSkein().getCraftedGcode( gcodeText, stretchRepository )

def getNewRepository():
	'Get new repository.'
	return StretchRepository()

def writeOutput(fileName, shouldAnalyze=True):
	"Stretch a gcode linear move file.  Chain stretch the gcode if it is not already stretched."
	skeinforge_craft.writeChainTextWithNounMessage(fileName, 'stretch', shouldAnalyze)


class LineIteratorBackward:
	"Backward line iterator class."
	def __init__( self, isLoop, lineIndex, lines ):
		self.firstLineIndex = None
		self.isLoop = isLoop
		self.lineIndex = lineIndex
		self.lines = lines

	def getIndexBeforeNextDeactivate(self):
		"Get index two lines before the deactivate command."
		for lineIndex in xrange( self.lineIndex + 1, len(self.lines) ):
			line = self.lines[lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			if firstWord == 'M103':
				return lineIndex - 2
		print('This should never happen in stretch, no deactivate command was found for this thread.')
		raise StopIteration, "You've reached the end of the line."

	def getNext(self):
		"Get next line going backward or raise exception."
		while self.lineIndex > 3:
			if self.lineIndex == self.firstLineIndex:
				raise StopIteration, "You've reached the end of the line."
			if self.firstLineIndex == None:
				self.firstLineIndex = self.lineIndex
			nextLineIndex = self.lineIndex - 1
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			if firstWord == 'M103':
				if self.isLoop:
					nextLineIndex = self.getIndexBeforeNextDeactivate()
				else:
					raise StopIteration, "You've reached the end of the line."
			if firstWord == 'G1':
				if self.isBeforeExtrusion():
					if self.isLoop:
						nextLineIndex = self.getIndexBeforeNextDeactivate()
					else:
						raise StopIteration, "You've reached the end of the line."
				else:
					self.lineIndex = nextLineIndex
					return line
			self.lineIndex = nextLineIndex
		raise StopIteration, "You've reached the end of the line."

	def isBeforeExtrusion(self):
		"Determine if index is two or more before activate command."
		linearMoves = 0
		for lineIndex in xrange( self.lineIndex + 1, len(self.lines) ):
			line = self.lines[lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			if firstWord == 'G1':
				linearMoves += 1
			if firstWord == 'M101':
				return linearMoves > 0
			if firstWord == 'M103':
				return False
		print('This should never happen in isBeforeExtrusion in stretch, no activate command was found for this thread.')
		return False


class LineIteratorForward:
	"Forward line iterator class."
	def __init__( self, isLoop, lineIndex, lines ):
		self.firstLineIndex = None
		self.isLoop = isLoop
		self.lineIndex = lineIndex
		self.lines = lines

	def getIndexJustAfterActivate(self):
		"Get index just after the activate command."
		for lineIndex in xrange( self.lineIndex - 1, 3, - 1 ):
			line = self.lines[lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			if firstWord == 'M101':
				return lineIndex + 1
		print('This should never happen in stretch, no activate command was found for this thread.')
		raise StopIteration, "You've reached the end of the line."

	def getNext(self):
		"Get next line or raise exception."
		while self.lineIndex < len(self.lines):
			if self.lineIndex == self.firstLineIndex:
				raise StopIteration, "You've reached the end of the line."
			if self.firstLineIndex == None:
				self.firstLineIndex = self.lineIndex
			nextLineIndex = self.lineIndex + 1
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			if firstWord == 'M103':
				if self.isLoop:
					nextLineIndex = self.getIndexJustAfterActivate()
				else:
					raise StopIteration, "You've reached the end of the line."
			self.lineIndex = nextLineIndex
			if firstWord == 'G1':
				return line
		raise StopIteration, "You've reached the end of the line."


class StretchRepository:
	"A class to handle the stretch settings."
	def __init__(self):
		"Set the default settings, execute title & settings fileName."
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.stretch.html', self )
		self.fileNameInput = settings.FileNameInput().getFromFileName( fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Stretch', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Stretch')
		self.activateStretch = settings.BooleanSetting().getFromValue('Activate Stretch', self, False )
		self.crossLimitDistanceOverEdgeWidth = settings.FloatSpin().getFromValue( 3.0, 'Cross Limit Distance Over Perimeter Width (ratio):', self, 10.0, 5.0 )
		self.loopStretchOverEdgeWidth = settings.FloatSpin().getFromValue( 0.05, 'Loop Stretch Over Perimeter Width (ratio):', self, 0.25, 0.11 )
		self.pathStretchOverEdgeWidth = settings.FloatSpin().getFromValue( 0.0, 'Path Stretch Over Perimeter Width (ratio):', self, 0.2, 0.0 )
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Perimeter -', self )
		self.edgeInsideStretchOverEdgeWidth = settings.FloatSpin().getFromValue( 0.12, 'Perimeter Inside Stretch Over Perimeter Width (ratio):', self, 0.52, 0.32 )
		self.edgeOutsideStretchOverEdgeWidth = settings.FloatSpin().getFromValue( 0.05, 'Perimeter Outside Stretch Over Perimeter Width (ratio):', self, 0.25, 0.1 )
		settings.LabelSeparator().getFromRepository(self)
		self.stretchFromDistanceOverEdgeWidth = settings.FloatSpin().getFromValue( 1.0, 'Stretch From Distance Over Perimeter Width (ratio):', self, 3.0, 2.0 )
		self.executeTitle = 'Stretch'

	def execute(self):
		"Stretch button has been clicked."
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class StretchSkein:
	"A class to stretch a skein of extrusions."
	def __init__(self):
		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.edgeWidth = 0.4
		self.extruderActive = False
		self.feedRateMinute = 959.0
		self.isLoop = False
		self.layerCount = settings.LayerCount()
		self.lineIndex = 0
		self.lines = None
		self.oldLocation = None

	def getCraftedGcode( self, gcodeText, stretchRepository ):
		"Parse gcode text and store the stretch gcode."
		self.lines = archive.getTextLines(gcodeText)
		self.stretchRepository = stretchRepository
		self.parseInitialization()
		for self.lineIndex in xrange(self.lineIndex, len(self.lines)):
			line = self.lines[self.lineIndex]
			self.parseStretch(line)
		return self.distanceFeedRate.output.getvalue()

	def getCrossLimitedStretch( self, crossLimitedStretch, crossLineIterator, locationComplex ):
		"Get cross limited relative stretch for a location."
		try:
			line = crossLineIterator.getNext()
		except StopIteration:
			return crossLimitedStretch
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		pointComplex = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine).dropAxis()
		pointMinusLocation = locationComplex - pointComplex
		pointMinusLocationLength = abs( pointMinusLocation )
		if pointMinusLocationLength <= self.crossLimitDistanceFraction:
			return crossLimitedStretch
		parallelNormal = pointMinusLocation / pointMinusLocationLength
		parallelStretch = euclidean.getDotProduct( parallelNormal, crossLimitedStretch ) * parallelNormal
		if pointMinusLocationLength > self.crossLimitDistance:
			return parallelStretch
		crossNormal = complex( parallelNormal.imag, - parallelNormal.real )
		crossStretch = euclidean.getDotProduct( crossNormal, crossLimitedStretch ) * crossNormal
		crossPortion = ( self.crossLimitDistance - pointMinusLocationLength ) / self.crossLimitDistanceRemainder
		return parallelStretch + crossStretch * crossPortion

	def getRelativeStretch( self, locationComplex, lineIterator ):
		"Get relative stretch for a location."
		lastLocationComplex = locationComplex
		oldTotalLength = 0.0
		pointComplex = locationComplex
		totalLength = 0.0
		while 1:
			try:
				line = lineIterator.getNext()
			except StopIteration:
				locationMinusPoint = locationComplex - pointComplex
				locationMinusPointLength = abs( locationMinusPoint )
				if locationMinusPointLength > 0.0:
					return locationMinusPoint / locationMinusPointLength
				return complex()
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = splitLine[0]
			pointComplex = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine).dropAxis()
			locationMinusPoint = lastLocationComplex - pointComplex
			locationMinusPointLength = abs( locationMinusPoint )
			totalLength += locationMinusPointLength
			if totalLength >= self.stretchFromDistance:
				distanceFromRatio = ( self.stretchFromDistance - oldTotalLength ) / locationMinusPointLength
				totalPoint = distanceFromRatio * pointComplex + ( 1.0 - distanceFromRatio ) * lastLocationComplex
				locationMinusTotalPoint = locationComplex - totalPoint
				return locationMinusTotalPoint / self.stretchFromDistance
			lastLocationComplex = pointComplex
			oldTotalLength = totalLength

	def getStretchedLine( self, splitLine ):
		"Get stretched gcode line."
		location = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
		self.feedRateMinute = gcodec.getFeedRateMinute( self.feedRateMinute, splitLine )
		self.oldLocation = location
		if self.extruderActive and self.threadMaximumAbsoluteStretch > 0.0:
			return self.getStretchedLineFromIndexLocation( self.lineIndex - 1, self.lineIndex + 1, location )
		if self.isJustBeforeExtrusion() and self.threadMaximumAbsoluteStretch > 0.0:
			return self.getStretchedLineFromIndexLocation( self.lineIndex - 1, self.lineIndex + 1, location )
		return self.lines[self.lineIndex]

	def getStretchedLineFromIndexLocation( self, indexPreviousStart, indexNextStart, location ):
		"Get stretched gcode line from line index and location."
		crossIteratorForward = LineIteratorForward( self.isLoop, indexNextStart, self.lines )
		crossIteratorBackward = LineIteratorBackward( self.isLoop, indexPreviousStart, self.lines )
		iteratorForward = LineIteratorForward( self.isLoop, indexNextStart, self.lines )
		iteratorBackward = LineIteratorBackward( self.isLoop, indexPreviousStart, self.lines )
		locationComplex = location.dropAxis()
		relativeStretch = self.getRelativeStretch( locationComplex, iteratorForward ) + self.getRelativeStretch( locationComplex, iteratorBackward )
		relativeStretch *= 0.8
		relativeStretch = self.getCrossLimitedStretch( relativeStretch, crossIteratorForward, locationComplex )
		relativeStretch = self.getCrossLimitedStretch( relativeStretch, crossIteratorBackward, locationComplex )
		relativeStretchLength = abs( relativeStretch )
		if relativeStretchLength > 1.0:
			relativeStretch /= relativeStretchLength
		absoluteStretch = relativeStretch * self.threadMaximumAbsoluteStretch
		stretchedPoint = location.dropAxis() + absoluteStretch
		return self.distanceFeedRate.getLinearGcodeMovementWithFeedRate( self.feedRateMinute, stretchedPoint, location.z )

	def isJustBeforeExtrusion(self):
		"Determine if activate command is before linear move command."
		for lineIndex in xrange( self.lineIndex + 1, len(self.lines) ):
			line = self.lines[lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			if firstWord == 'G1' or firstWord == 'M103':
				return False
			if firstWord == 'M101':
				return True
#		print('This should never happen in isJustBeforeExtrusion in stretch, no activate or deactivate command was found for this thread.')
		return False

	def parseInitialization(self):
		'Parse gcode initialization and store the parameters.'
		for self.lineIndex in xrange(len(self.lines)):
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			self.distanceFeedRate.parseSplitLine(firstWord, splitLine)
			if firstWord == '(</extruderInitialization>)':
				self.distanceFeedRate.addTagBracketedProcedure('stretch')
				return
			elif firstWord == '(<edgeWidth>':
				edgeWidth = float(splitLine[1])
				self.crossLimitDistance = self.edgeWidth * self.stretchRepository.crossLimitDistanceOverEdgeWidth.value
				self.loopMaximumAbsoluteStretch = self.edgeWidth * self.stretchRepository.loopStretchOverEdgeWidth.value
				self.pathAbsoluteStretch = self.edgeWidth * self.stretchRepository.pathStretchOverEdgeWidth.value
				self.edgeInsideAbsoluteStretch = self.edgeWidth * self.stretchRepository.edgeInsideStretchOverEdgeWidth.value
				self.edgeOutsideAbsoluteStretch = self.edgeWidth * self.stretchRepository.edgeOutsideStretchOverEdgeWidth.value
				self.stretchFromDistance = self.stretchRepository.stretchFromDistanceOverEdgeWidth.value * edgeWidth
				self.threadMaximumAbsoluteStretch = self.pathAbsoluteStretch
				self.crossLimitDistanceFraction = 0.333333333 * self.crossLimitDistance
				self.crossLimitDistanceRemainder = self.crossLimitDistance - self.crossLimitDistanceFraction
			self.distanceFeedRate.addLine(line)

	def parseStretch(self, line):
		"Parse a gcode line and add it to the stretch skein."
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if firstWord == 'G1':
			line = self.getStretchedLine(splitLine)
		elif firstWord == 'M101':
			self.extruderActive = True
		elif firstWord == 'M103':
			self.extruderActive = False
			self.setStretchToPath()
		elif firstWord == '(<layer>':
			self.layerCount.printProgressIncrement('stretch')
		elif firstWord == '(<loop>':
			self.isLoop = True
			self.threadMaximumAbsoluteStretch = self.loopMaximumAbsoluteStretch
		elif firstWord == '(</loop>)':
			self.setStretchToPath()
		elif firstWord == '(<edge>':
			self.isLoop = True
			self.threadMaximumAbsoluteStretch = self.edgeInsideAbsoluteStretch
			if splitLine[1] == 'outer':
				self.threadMaximumAbsoluteStretch = self.edgeOutsideAbsoluteStretch
		elif firstWord == '(</edge>)':
			self.setStretchToPath()
		self.distanceFeedRate.addLine(line)

	def setStretchToPath(self):
		"Set the thread stretch to path stretch and is loop false."
		self.isLoop = False
		self.threadMaximumAbsoluteStretch = self.pathAbsoluteStretch


def main():
	"Display the stretch dialog."
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == "__main__":
	main()
