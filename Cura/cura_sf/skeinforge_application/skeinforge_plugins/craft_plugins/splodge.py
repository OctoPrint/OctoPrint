"""
This page is in the table of contents.
Splodge turns the extruder on just before the start of a thread.  This is to give the extrusion a bit anchoring at the beginning.

The splodge manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Splodge

==Operation==
The default 'Activate Splodge' checkbox is on.  When it is on, the functions described below will work, when it is off, the functions will not be called.

==Settings==
===Initial===
====Initial Lift over Extra Thickness====
Default is one.

Defines the amount the extruder will be lifted over the extra thickness of the initial splodge thread.  The higher the ratio, the more the extruder will be lifted over the splodge, if the ratio is too low the extruder might plow through the splodge extrusion.

====Initial Splodge Feed Rate====
Default is one millimeter per second.

Defines the feed rate at which the initial extra extrusion will be added.  With the default feed rate, the splodge will be added slower so it will be thicker than the regular extrusion.

====Initial Splodge Quantity Length====
Default is thirty millimeters.

Defines the quantity length of extra extrusion at the operating feed rate that will be added to the initial thread.  If a splodge quantity length is smaller than 0.1 times the edge width, no splodge of that type will be added.

===Operating===
====Operating Lift over Extra Thickness====
Default is one.

Defines the amount the extruder will be lifted over the extra thickness of the operating splodge thread.

====Operating Splodge Feed Rate====
Default is one millimeter per second.

Defines the feed rate at which the next extra extrusions will be added.

====Operating Splodge Quantity Length====
Default is thirty millimeters.

Defines the quantity length of extra extrusion at the operating feed rate that will be added for the next threads.

==Examples==
The following examples splodge the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and splodge.py.

> python splodge.py
This brings up the splodge dialog.

> python splodge.py Screw Holder Bottom.stl
The splodge tool is parsing the file:
Screw Holder Bottom.stl
..
The splodge tool has created the file:
.. Screw Holder Bottom_splodge.gcode

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_utilities import skeinforge_craft
from skeinforge_application.skeinforge_utilities import skeinforge_polyfile
from skeinforge_application.skeinforge_utilities import skeinforge_profile
import math
import sys


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCraftedText( fileName, text, splodgeRepository = None ):
	"Splodge a gcode linear move file or text."
	return getCraftedTextFromText( archive.getTextIfEmpty(fileName, text), splodgeRepository )

def getCraftedTextFromText( gcodeText, splodgeRepository = None ):
	"Splodge a gcode linear move text."
	if gcodec.isProcedureDoneOrFileIsEmpty( gcodeText, 'splodge'):
		return gcodeText
	if splodgeRepository == None:
		splodgeRepository = settings.getReadRepository( SplodgeRepository() )
	if not splodgeRepository.activateSplodge.value:
		return gcodeText
	return SplodgeSkein().getCraftedGcode( gcodeText, splodgeRepository )

def getNewRepository():
	'Get new repository.'
	return SplodgeRepository()

def writeOutput(fileName, shouldAnalyze=True):
	"Splodge a gcode linear move file."
	skeinforge_craft.writeChainTextWithNounMessage(fileName, 'splodge', shouldAnalyze)


class SplodgeRepository:
	"A class to handle the splodge settings."
	def __init__(self):
		"Set the default settings, execute title & settings fileName."
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.splodge.html', self )
		self.fileNameInput = settings.FileNameInput().getFromFileName( fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Splodge', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Splodge')
		self.activateSplodge = settings.BooleanSetting().getFromValue('Activate Splodge', self, False )
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Initial -', self )
		self.initialLiftOverExtraThickness = settings.FloatSpin().getFromValue( 0.5, 'Initial Lift over Extra Thickness (ratio):', self, 1.5, 1.0 )
		self.initialSplodgeFeedRate = settings.FloatSpin().getFromValue( 0.4, 'Initial Splodge Feed Rate (mm/s):', self, 2.4, 1.0 )
		self.initialSplodgeQuantityLength = settings.FloatSpin().getFromValue( 10.0, 'Initial Splodge Quantity Length (millimeters):', self, 90.0, 30.0 )
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Operating -', self )
		self.operatingLiftOverExtraThickness = settings.FloatSpin().getFromValue( 0.5, 'Operating Lift over Extra Thickness (ratio):', self, 1.5, 1.0 )
		self.operatingSplodgeFeedRate = settings.FloatSpin().getFromValue( 0.4, 'Operating Splodge Feed Rate (mm/s):', self, 2.4, 1.0 )
		self.operatingSplodgeQuantityLength = settings.FloatSpin().getFromValue(0.4, 'Operating Splodge Quantity Length (millimeters):', self, 2.4, 1.0)
		settings.LabelSeparator().getFromRepository(self)
		self.executeTitle = 'Splodge'

	def execute(self):
		"Splodge button has been clicked."
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class SplodgeSkein:
	"A class to splodge a skein of extrusions."
	def __init__(self):
		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.feedRateMinute = 961.0
		self.isExtruderActive = False
		self.hasInitialSplodgeBeenAdded = False
		self.isLastExtruderCommandActivate = False
		self.lastLineOutput = None
		self.lineIndex = 0
		self.lines = None
		self.oldLocation = None
		self.operatingFeedRatePerSecond = 15.0

	def addLineUnlessIdentical(self, line):
		"Add a line, unless it is identical to the last line."
		if line == self.lastLineOutput:
			return
		self.lastLineOutput = line
		self.distanceFeedRate.addLine(line)

	def addLineUnlessIdenticalReactivate(self, line):
		"Add a line, unless it is identical to the last line or another M101."
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if firstWord == 'M101':
			if not self.isLastExtruderCommandActivate:
				self.addLineUnlessIdentical(line)
				self.isLastExtruderCommandActivate = True
			return
		if firstWord == 'M103':
			self.isLastExtruderCommandActivate = False
		self.addLineUnlessIdentical(line)

	def getCraftedGcode( self, gcodeText, splodgeRepository ):
		"Parse gcode text and store the splodge gcode."
		self.lines = archive.getTextLines(gcodeText)
		self.setRotations()
		self.splodgeRepository = splodgeRepository
		self.parseInitialization( splodgeRepository )
		self.boundingRectangle = gcodec.BoundingRectangle().getFromGcodeLines( self.lines[self.lineIndex :], 0.5 * self.edgeWidth )
		self.initialSplodgeFeedRateMinute = 60.0 * splodgeRepository.initialSplodgeFeedRate.value
		self.initialStartupDistance = splodgeRepository.initialSplodgeQuantityLength.value * splodgeRepository.initialSplodgeFeedRate.value / self.operatingFeedRatePerSecond
		self.operatingSplodgeFeedRateMinute = 60.0 * splodgeRepository.operatingSplodgeFeedRate.value
		self.operatingStartupDistance = splodgeRepository.operatingSplodgeQuantityLength.value * splodgeRepository.operatingSplodgeFeedRate.value / self.operatingFeedRatePerSecond
		for self.lineIndex in xrange(self.lineIndex, len(self.lines)):
			line = self.lines[self.lineIndex]
			self.parseLine(line)
		return self.distanceFeedRate.output.getvalue()

	def getInitialSplodgeLine( self, line, location ):
		"Add the initial splodge line."
		if not self.isJustBeforeExtrusion():
			return line
		self.hasInitialSplodgeBeenAdded = True
		if self.splodgeRepository.initialSplodgeQuantityLength.value < self.minimumQuantityLength:
			return line
		return self.getSplodgeLineGivenDistance( self.initialSplodgeFeedRateMinute, line, self.splodgeRepository.initialLiftOverExtraThickness.value, location, self.initialStartupDistance )

	def getNextActiveLocationComplex(self):
		"Get the next active line."
		isActive = False
		for lineIndex in xrange( self.lineIndex + 1, len(self.lines) ):
			line = self.lines[lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			if firstWord == 'M101':
				isActive = True
			if firstWord == 'G1' and isActive:
				return gcodec.getLocationFromSplitLine(self.oldLocation, splitLine).dropAxis()
		return None

	def getOperatingSplodgeLine( self, line, location ):
		"Get the operating splodge line."
		if not self.isJustBeforeExtrusion():
			return line
		if self.splodgeRepository.operatingSplodgeQuantityLength.value < self.minimumQuantityLength:
			return line
		return self.getSplodgeLineGivenDistance( self.operatingSplodgeFeedRateMinute, line, self.splodgeRepository.operatingLiftOverExtraThickness.value, location, self.operatingStartupDistance )

	def getSplodgeLine(self, line, location, splitLine):
		"Get splodged gcode line."
		self.feedRateMinute = gcodec.getFeedRateMinute(self.feedRateMinute, splitLine)
		if self.hasInitialSplodgeBeenAdded:
			return self.getOperatingSplodgeLine(line, location)
		return self.getInitialSplodgeLine(line, location)

	def getSplodgeLineGivenDistance( self, feedRateMinute, line, liftOverExtraThickness, location, startupDistance ):
		"Add the splodge line."
		locationComplex = location.dropAxis()
		relativeStartComplex = None
		nextLocationComplex = self.getNextActiveLocationComplex()
		if nextLocationComplex != None:
			if nextLocationComplex != locationComplex:
				relativeStartComplex = locationComplex - nextLocationComplex
		if relativeStartComplex == None:
			relativeStartComplex = complex( 19.9, 9.9 )
			if self.oldLocation != None:
				oldLocationComplex = self.oldLocation.dropAxis()
				if oldLocationComplex != locationComplex:
					relativeStartComplex = oldLocationComplex - locationComplex
		relativeStartComplex *= startupDistance / abs( relativeStartComplex )
		startComplex = self.getStartInsideBoundingRectangle( locationComplex, relativeStartComplex )
		feedRateMultiplier = feedRateMinute / self.operatingFeedRatePerSecond / 60.0
		splodgeLayerThickness = self.layerHeight / math.sqrt( feedRateMultiplier )
		extraLayerThickness = splodgeLayerThickness - self.layerHeight
		lift = extraLayerThickness * liftOverExtraThickness
		startLine = self.distanceFeedRate.getLinearGcodeMovementWithFeedRate( self.feedRateMinute, startComplex, location.z + lift )
		self.addLineUnlessIdenticalReactivate( startLine )
		self.addLineUnlessIdenticalReactivate('M101')
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		lineLocation = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
		self.distanceFeedRate.addGcodeMovementZWithFeedRate( feedRateMinute, locationComplex, lineLocation.z + lift )
		return ''

	def getStartInsideBoundingRectangle( self, locationComplex, relativeStartComplex ):
		"Get a start inside the bounding rectangle."
		startComplex = locationComplex + relativeStartComplex
		if self.boundingRectangle.isPointInside( startComplex ):
			return startComplex
		for rotation in self.rotations:
			rotatedRelativeStartComplex = relativeStartComplex * rotation
			startComplex = locationComplex + rotatedRelativeStartComplex
			if self.boundingRectangle.isPointInside( startComplex ):
				return startComplex
		return startComplex

	def isJustBeforeExtrusion(self):
		"Determine if activate command is before linear move command."
		for lineIndex in xrange(self.lineIndex + 1, len(self.lines)):
			line = self.lines[lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			if firstWord == 'G1' or firstWord == 'M103':
				return False
			if firstWord == 'M101':
				return True
		return False

	def parseInitialization( self, splodgeRepository ):
		'Parse gcode initialization and store the parameters.'
		for self.lineIndex in xrange(len(self.lines)):
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			self.distanceFeedRate.parseSplitLine(firstWord, splitLine)
			if firstWord == '(</extruderInitialization>)':
				self.addLineUnlessIdenticalReactivate(gcodec.getTagBracketedProcedure('splodge'))
				return
			elif firstWord == '(<layerHeight>':
				self.layerHeight = float(splitLine[1])
			elif firstWord == '(<operatingFeedRatePerSecond>':
				self.operatingFeedRatePerSecond = float(splitLine[1])
			elif firstWord == '(<edgeWidth>':
				self.edgeWidth = float(splitLine[1])
				self.minimumQuantityLength = 0.1 * self.edgeWidth
			self.addLineUnlessIdenticalReactivate(line)

	def parseLine(self, line):
		"Parse a gcode line and add it to the bevel gcode."
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if firstWord == 'G1':
			location = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
			line = self.getSplodgeLine(line, location, splitLine)
			self.oldLocation = location
		elif firstWord == 'M101':
			self.isExtruderActive = True
		elif firstWord == 'M103':
			self.isExtruderActive = False
		self.addLineUnlessIdenticalReactivate(line)

	def setRotations(self):
		"Set the rotations."
		self.rootHalf = math.sqrt( 0.5 )
		self.rotations = []
		self.rotations.append( complex( self.rootHalf, self.rootHalf ) )
		self.rotations.append( complex( self.rootHalf, - self.rootHalf ) )
		self.rotations.append( complex( 0.0, 1.0 ) )
		self.rotations.append( complex(0.0, -1.0) )
		self.rotations.append( complex( - self.rootHalf, self.rootHalf ) )
		self.rotations.append( complex( - self.rootHalf, - self.rootHalf ) )


def main():
	"Display the splodge dialog."
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == "__main__":
	main()
