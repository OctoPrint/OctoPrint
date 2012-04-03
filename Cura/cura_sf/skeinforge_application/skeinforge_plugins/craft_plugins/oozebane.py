"""
This page is in the table of contents.
Oozebane is a script to turn off the extruder before the end of a thread and turn it on before the beginning.

The oozebane manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Oozebane

After oozebane turns the extruder on, it slows the feed rate down where the thread starts.  Then it speeds it up in steps so in theory the thread will remain at roughly the same thickness from the beginning.

==Operation==
The default 'Activate Oozebane' checkbox is on.  When it is on, the functions described below will work, when it is off, the functions will not be called.

==Settings==
===After Startup Distance===
Default is 1.2.

When oozebane reaches the point where the extruder would of turned on, it slows down so that the thread will be thick at that point.  Afterwards it speeds the extruder back up to operating speed.  The speed up distance is the "After Startup Distance".

===Early Shutdown Distance===
Default is 1.2.

Defines the distance before the end of the thread that the extruder will be turned off.  It is the most important oozebane setting.  A higher distance means the extruder will turn off sooner and the end of the line will be thinner.

===Early Startup Maximum Distance===
Default is 1.2.

Defines the maximum distance before the thread starts that the extruder will be turned on

===Early Startup Distance Constant===
Default is twenty.

The longer the extruder has been off, the earlier the extruder will turn back on, the ratio is one minus one over e to the power of the distance the extruder has been off over the "Early Startup Distance Constant".

===First Early Startup Distance===
Default is twenty five.

Defines the distance before the first thread starts that the extruder will be turned off.  This value should be high because, according to Marius, the extruder takes a second or two to extrude when starting for the first time.

===Minimum Distance for Early Shutdown===
Default is zero.

Defines the minimum distance that the extruder has to be off after the thread end for the early shutdown feature to activate.

===Minimum Distance for Early Startup===
Default is zero.

Defines the minimum distance that the extruder has to be off before the thread begins for the early start up feature to activate.

===Slowdown Startup Steps===
Default is three.

When oozebane turns the extruder off, it slows the feed rate down in steps so in theory the thread will remain at roughly the same thickness until the end.  The "Slowdown Startup Steps" setting is the number of steps, the more steps the smaller the size of the step that the feed rate will be decreased and the larger the size of the resulting gcode file.

==Examples==
The following examples oozebane the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and oozebane.py.

> python oozebane.py
This brings up the oozebane dialog.

> python oozebane.py Screw Holder Bottom.stl
The oozebane tool is parsing the file:
Screw Holder Bottom.stl
..
The oozebane tool has created the file:
.. Screw Holder Bottom_oozebane.gcode

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


def getCraftedText( fileName, text, oozebaneRepository = None ):
	"Oozebane a gcode linear move file or text."
	return getCraftedTextFromText( archive.getTextIfEmpty(fileName, text), oozebaneRepository )

def getCraftedTextFromText( gcodeText, oozebaneRepository = None ):
	"Oozebane a gcode linear move text."
	if gcodec.isProcedureDoneOrFileIsEmpty( gcodeText, 'oozebane'):
		return gcodeText
	if oozebaneRepository == None:
		oozebaneRepository = settings.getReadRepository( OozebaneRepository() )
	if not oozebaneRepository.activateOozebane.value:
		return gcodeText
	return OozebaneSkein().getCraftedGcode( gcodeText, oozebaneRepository )

def getNewRepository():
	'Get new repository.'
	return OozebaneRepository()

def writeOutput(fileName, shouldAnalyze=True):
	"Oozebane a gcode linear move file."
	skeinforge_craft.writeChainTextWithNounMessage(fileName, 'oozebane', shouldAnalyze)


class OozebaneRepository:
	"A class to handle the oozebane settings."
	def __init__(self):
		"Set the default settings, execute title & settings fileName."
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.oozebane.html', self )
		self.fileNameInput = settings.FileNameInput().getFromFileName( fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Oozebane', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Oozebane')
		self.activateOozebane = settings.BooleanSetting().getFromValue('Activate Oozebane', self, False )
		self.afterStartupDistance = settings.FloatSpin().getFromValue( 0.7, 'After Startup Distance (millimeters):', self, 1.7, 1.2 )
		self.earlyShutdownDistance = settings.FloatSpin().getFromValue( 0.7, 'Early Shutdown Distance (millimeters):', self, 1.7, 1.2 )
		self.earlyStartupDistanceConstant = settings.FloatSpin().getFromValue( 10.0, 'Early Startup Distance Constant (millimeters):', self, 30.0, 20.0 )
		self.earlyStartupMaximumDistance = settings.FloatSpin().getFromValue( 0.7, 'Early Startup Maximum Distance (millimeters):', self, 1.7, 1.2 )
		self.firstEarlyStartupDistance = settings.FloatSpin().getFromValue( 5.0, 'First Early Startup Distance (millimeters):', self, 45.0, 25.0 )
		self.minimumDistanceForEarlyStartup = settings.FloatSpin().getFromValue( 0.0, 'Minimum Distance for Early Startup (millimeters):', self, 10.0, 0.0 )
		self.minimumDistanceForEarlyShutdown = settings.FloatSpin().getFromValue( 0.0, 'Minimum Distance for Early Shutdown (millimeters):', self, 10.0, 0.0 )
		self.slowdownStartupSteps = settings.IntSpin().getFromValue( 2, 'Slowdown Startup Steps (positive integer):', self, 5, 3 )
		self.executeTitle = 'Oozebane'

	def execute(self):
		"Oozebane button has been clicked."
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class OozebaneSkein:
	"A class to oozebane a skein of extrusions."
	def __init__(self):
		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.distanceFromThreadEndToThreadBeginning = None
		self.earlyStartupDistance = None
		self.extruderInactiveLongEnough = True
		self.feedRateMinute = 961.0
		self.isExtruderActive = False
		self.isFirstExtrusion = True
		self.isShutdownEarly = False
		self.isStartupEarly = False
		self.lineIndex = 0
		self.lines = None
		self.oldLocation = None
		self.operatingFeedRateMinute = 959.0
		self.shutdownStepIndex = 999999999
		self.startupStepIndex = 999999999

	def addAfterStartupLine( self, splitLine ):
		"Add the after startup lines."
		distanceAfterThreadBeginning = self.getDistanceAfterThreadBeginning()
		location = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
		segment = self.oldLocation - location
		segmentLength = segment.magnitude()
		distanceBack = distanceAfterThreadBeginning - self.afterStartupDistances[ self.startupStepIndex ]
		if segmentLength > 0.0:
			locationBack = location + segment * distanceBack / segmentLength
			feedRate = self.operatingFeedRateMinute * self.afterStartupFlowRates[ self.startupStepIndex ]
			if not self.isCloseToEither( locationBack, location, self.oldLocation ):
				self.distanceFeedRate.addLine( self.getLinearMoveWithFeedRate( feedRate, locationBack ) )
		self.startupStepIndex += 1

	def addLineSetShutdowns(self, line):
		"Add a line and set the shutdown variables."
		self.distanceFeedRate.addLine(line)
		self.isShutdownEarly = True

	def getActiveFeedRateRatio(self):
		"Get the feed rate of the first active move over the operating feed rate."
		isSearchExtruderActive = self.isExtruderActive
		for afterIndex in xrange(self.lineIndex, len(self.lines)):
			line = self.lines[ afterIndex ]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			if firstWord == 'G1':
				if isSearchExtruderActive:
					return gcodec.getFeedRateMinute( self.feedRateMinute, splitLine ) / self.operatingFeedRateMinute
			elif firstWord == 'M101':
				isSearchExtruderActive = True
		print('active feed rate ratio was not found in oozebane.')
		return 1.0

	def getAddAfterStartupLines(self, line):
		"Get and / or add after the startup lines."
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		while self.isDistanceAfterThreadBeginningGreater():
			self.addAfterStartupLine(splitLine)
		if self.startupStepIndex >= len( self.afterStartupDistances ):
			self.startupStepIndex = len( self.afterStartupDistances ) + 999999999999
			return self.getLinearMoveWithFeedRateSplitLine( self.operatingFeedRateMinute, splitLine )
		feedRate = self.operatingFeedRateMinute * self.getStartupFlowRateMultiplier( self.getDistanceAfterThreadBeginning() / self.afterStartupDistance, len( self.afterStartupDistances ) )
		return self.getLinearMoveWithFeedRateSplitLine( feedRate, splitLine )

	def getAddBeforeStartupLines(self, line):
		"Get and / or add before the startup lines."
		distanceThreadBeginning = self.getDistanceToThreadBeginning()
		if distanceThreadBeginning == None:
			return line
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		self.extruderInactiveLongEnough = False
		self.isStartupEarly = True
		location = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
		segment = self.oldLocation - location
		segmentLength = segment.magnitude()
		distanceBack = self.earlyStartupDistance - distanceThreadBeginning
		if segmentLength <= 0.0:
			print('This should never happen, segmentLength is zero in getAddBeforeStartupLines in oozebane.')
			print(line)
			self.extruderInactiveLongEnough = True
			self.isStartupEarly = False
			return line
		locationBack = location + segment * distanceBack / segmentLength
		self.distanceFeedRate.addLine( self.getLinearMoveWithFeedRate( gcodec.getFeedRateMinute( self.feedRateMinute, splitLine ) , locationBack ) )
		self.distanceFeedRate.addLine('M101')
		if self.isCloseToEither( locationBack, location, self.oldLocation ):
			return ''
		return self.getLinearMoveWithFeedRate( self.operatingFeedRateMinute, location )

	def getAddShutSlowDownLine(self, line):
		"Add the shutdown and slowdown lines."
		if self.shutdownStepIndex >= len( self.earlyShutdownDistances ):
			self.shutdownStepIndex = len( self.earlyShutdownDistances ) + 99999999
			return False
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		distanceThreadEnd = self.getDistanceToExtruderOffCommand( self.earlyShutdownDistances[ self.shutdownStepIndex ] )
		location = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
		if distanceThreadEnd == None:
			distanceThreadEnd = self.getDistanceToExtruderOffCommand( self.earlyShutdownDistances[0] )
			if distanceThreadEnd != None:
				shutdownFlowRateMultiplier = self.getShutdownFlowRateMultiplier( 1.0 - distanceThreadEnd / self.earlyShutdownDistance, len( self.earlyShutdownDistances ) )
				line = self.getLinearMoveWithFeedRate( self.feedRateMinute * shutdownFlowRateMultiplier, location )
			self.distanceFeedRate.addLine(line)
			return False
		segment = self.oldLocation - location
		segmentLength = segment.magnitude()
		distanceBack = self.earlyShutdownDistances[ self.shutdownStepIndex ] - distanceThreadEnd
		locationBack = location
		if segmentLength > 0.0:
			locationBack = location + segment * distanceBack / segmentLength
		if self.shutdownStepIndex == 0:
			if not self.isCloseToEither( locationBack, location, self.oldLocation ):
				line = self.getLinearMoveWithFeedRate( self.feedRateMinute, locationBack )
			self.distanceFeedRate.addLine(line)
			self.addLineSetShutdowns('M103')
			return True
		if self.isClose( locationBack, self.oldLocation ):
			return True
		feedRate = self.feedRateMinute * self.earlyShutdownFlowRates[ self.shutdownStepIndex ]
		line = self.getLinearMoveWithFeedRate( feedRate, locationBack )
		if self.isClose( locationBack, location ):
			line = self.getLinearMoveWithFeedRate( feedRate, location )
		self.distanceFeedRate.addLine(line)
		return True

	def getAddShutSlowDownLines(self, line):
		"Get and / or add the shutdown and slowdown lines."
		while self.getAddShutSlowDownLine(line):
			self.shutdownStepIndex += 1
		return ''

	def getCraftedGcode( self, gcodeText, oozebaneRepository ):
		"Parse gcode text and store the oozebane gcode."
		self.lines = archive.getTextLines(gcodeText)
		self.oozebaneRepository = oozebaneRepository
		self.parseInitialization( oozebaneRepository )
		for self.lineIndex in xrange(self.lineIndex, len(self.lines)):
			line = self.lines[self.lineIndex]
			self.parseLine(line)
		return self.distanceFeedRate.output.getvalue()

	def getDistanceAfterThreadBeginning(self):
		"Get the distance after the beginning of the thread."
		line = self.lines[self.lineIndex]
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		lastThreadLocation = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
		totalDistance = 0.0
		extruderOnReached = False
		for beforeIndex in xrange( self.lineIndex - 1, 3, - 1 ):
			line = self.lines[ beforeIndex ]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			if firstWord == 'G1':
				location = gcodec.getLocationFromSplitLine( lastThreadLocation, splitLine )
				totalDistance += location.distance( lastThreadLocation )
				lastThreadLocation = location
				if extruderOnReached:
					return totalDistance
			elif firstWord == 'M101':
				extruderOnReached = True
		return None

	def getDistanceToExtruderOffCommand( self, remainingDistance ):
		"Get the distance to the word."
		line = self.lines[self.lineIndex]
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		lastThreadLocation = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
		totalDistance = 0.0
		for afterIndex in xrange( self.lineIndex + 1, len(self.lines) ):
			line = self.lines[ afterIndex ]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			if firstWord == 'G1':
				location = gcodec.getLocationFromSplitLine( lastThreadLocation, splitLine )
				totalDistance += location.distance( lastThreadLocation )
				lastThreadLocation = location
				if totalDistance >= remainingDistance:
					return None
			elif firstWord == 'M103':
				return totalDistance
		return None

	def getDistanceToThreadBeginning(self):
		"Get the distance to the beginning of the thread."
		if self.earlyStartupDistance == None:
			return None
		line = self.lines[self.lineIndex]
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		lastThreadLocation = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
		totalDistance = 0.0
		for afterIndex in xrange( self.lineIndex + 1, len(self.lines) ):
			line = self.lines[ afterIndex ]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			if firstWord == 'G1':
				location = gcodec.getLocationFromSplitLine( lastThreadLocation, splitLine )
				totalDistance += location.distance( lastThreadLocation )
				lastThreadLocation = location
				if totalDistance >= self.earlyStartupDistance:
					return None
			elif firstWord == 'M101':
				return totalDistance
		return None

	def getDistanceToThreadBeginningAfterThreadEnd( self, remainingDistance ):
		"Get the distance to the thread beginning after the end of this thread."
		extruderOnReached = False
		line = self.lines[self.lineIndex]
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		lastThreadLocation = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
		threadEndReached = False
		totalDistance = 0.0
		for afterIndex in xrange( self.lineIndex + 1, len(self.lines) ):
			line = self.lines[ afterIndex ]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			if firstWord == 'G1':
				location = gcodec.getLocationFromSplitLine( lastThreadLocation, splitLine )
				if threadEndReached:
					totalDistance += location.distance( lastThreadLocation )
					if totalDistance >= remainingDistance:
						return None
					if extruderOnReached:
						return totalDistance
				lastThreadLocation = location
			elif firstWord == 'M101':
				extruderOnReached = True
			elif firstWord == 'M103':
				threadEndReached = True
		return None

	def getDistanceToThreadEnd(self):
		"Get the distance to the end of the thread."
		if self.shutdownStepIndex >= len( self.earlyShutdownDistances ):
			return None
		return self.getDistanceToExtruderOffCommand( self.earlyShutdownDistances[ self.shutdownStepIndex ] )

	def getLinearMoveWithFeedRate( self, feedRate, location ):
		"Get a linear move line with the feed rate."
		return self.distanceFeedRate.getLinearGcodeMovementWithFeedRate( feedRate, location.dropAxis(), location.z )

	def getLinearMoveWithFeedRateSplitLine( self, feedRate, splitLine ):
		"Get a linear move line with the feed rate and split line."
		location = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
		return self.getLinearMoveWithFeedRate( feedRate, location )

	def getOozebaneLine(self, line):
		"Get oozebaned gcode line."
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		self.feedRateMinute = gcodec.getFeedRateMinute( self.feedRateMinute, splitLine )
		if self.oldLocation == None:
			return line
		if self.startupStepIndex < len( self.afterStartupDistances ):
			return self.getAddAfterStartupLines(line)
		if self.extruderInactiveLongEnough:
			return self.getAddBeforeStartupLines(line)
		if self.shutdownStepIndex < len( self.earlyShutdownDistances ):
			return self.getAddShutSlowDownLines(line)
		if self.isStartupEarly:
			return self.getLinearMoveWithFeedRateSplitLine( self.operatingFeedRateMinute, splitLine )
		return line

	def getShutdownFlowRateMultiplier( self, along, numberOfDistances ):
		"Get the shut down flow rate multipler."
		if numberOfDistances <= 0:
			return 1.0
		return 1.0 - 0.5 / float( numberOfDistances ) - along * float( numberOfDistances - 1 ) / float( numberOfDistances )

	def getStartupFlowRateMultiplier( self, along, numberOfDistances ):
		"Get the startup flow rate multipler."
		if numberOfDistances <= 0:
			return 1.0
		return min( 1.0, 0.5 / float( numberOfDistances ) + along )

	def isClose( self, location, otherLocation ):
		"Determine if the location is close to the other location."
		return location.distanceSquared( otherLocation ) < self.closeSquared

	def isCloseToEither( self, location, otherLocationFirst, otherLocationSecond ):
		"Determine if the location is close to the other locations."
		if self.isClose( location, otherLocationFirst ):
			return True
		return self.isClose( location, otherLocationSecond )

	def isDistanceAfterThreadBeginningGreater(self):
		"Determine if the distance after the thread beginning is greater than the step index after startup distance."
		if self.startupStepIndex >= len( self.afterStartupDistances ):
			return False
		return self.getDistanceAfterThreadBeginning() > self.afterStartupDistances[ self.startupStepIndex ]

	def parseInitialization( self, oozebaneRepository ):
		'Parse gcode initialization and store the parameters.'
		for self.lineIndex in xrange(len(self.lines)):
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			self.distanceFeedRate.parseSplitLine(firstWord, splitLine)
			if firstWord == '(</extruderInitialization>)':
				self.distanceFeedRate.addTagBracketedProcedure('oozebane')
				return
			elif firstWord == '(<operatingFeedRatePerSecond>':
				self.operatingFeedRateMinute = 60.0 * float(splitLine[1])
				self.feedRateMinute = self.operatingFeedRateMinute
			elif firstWord == '(<edgeWidth>':
				self.edgeWidth = float(splitLine[1])
				self.setExtrusionWidth( oozebaneRepository )
			self.distanceFeedRate.addLine(line)

	def parseLine(self, line):
		"Parse a gcode line and add it to the bevel gcode."
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if firstWord == 'G1':
			self.setEarlyStartupDistance(splitLine)
			line = self.getOozebaneLine(line)
			self.oldLocation = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
		elif firstWord == 'M101':
			self.isExtruderActive = True
			self.extruderInactiveLongEnough = False
			if self.getDistanceToExtruderOffCommand( self.earlyShutdownDistance ) == None:
				self.setEarlyShutdown()
			if self.getDistanceToExtruderOffCommand( 1.03 * ( self.earlyShutdownDistance + self.afterStartupDistance ) ) == None:
				afterStartupRatio = 1.0
				if self.minimumDistanceForEarlyStartup > 0.0:
					if self.distanceFromThreadEndToThreadBeginning != None:
						afterStartupRatio = self.distanceFromThreadEndToThreadBeginning / self.minimumDistanceForEarlyStartup
				self.setAfterStartupFlowRates( afterStartupRatio )
				self.startupStepIndex = 9999999999
				if len( self.afterStartupDistances ) > 0:
					self.startupStepIndex = 0
			if self.isStartupEarly:
				self.isStartupEarly = False
				return
		elif firstWord == 'M103':
			self.isExtruderActive = False
			self.shutdownStepIndex = 999999999
			if self.getDistanceToThreadBeginning() == None:
				self.extruderInactiveLongEnough = True
			self.distanceFromThreadEndToThreadBeginning = None
			self.earlyStartupDistance = None
			if self.isShutdownEarly:
				self.isShutdownEarly = False
				return
		self.distanceFeedRate.addLine(line)

	def setAfterStartupFlowRates( self, afterStartupRatio ):
		"Set the after startup flow rates."
		afterStartupRatio = min( 1.0, afterStartupRatio )
		afterStartupRatio = max( 0.0, afterStartupRatio )
		self.afterStartupDistance = afterStartupRatio * self.getActiveFeedRateRatio() * self.oozebaneRepository.afterStartupDistance.value
		self.afterStartupDistances = []
		self.afterStartupFlowRate = 1.0
		self.afterStartupFlowRates = []
		afterStartupSteps = int( math.floor( afterStartupRatio * float( self.oozebaneRepository.slowdownStartupSteps.value ) ) )
		if afterStartupSteps < 1:
			return
		if afterStartupSteps < 2:
			afterStartupSteps = 2
		for stepIndex in xrange( afterStartupSteps ):
			afterWay = ( stepIndex + 1 ) / float( afterStartupSteps )
			afterMiddleWay = self.getStartupFlowRateMultiplier( stepIndex / float( afterStartupSteps ), afterStartupSteps )
			self.afterStartupDistances.append( afterWay * self.afterStartupDistance )
			if stepIndex == 0:
				self.afterStartupFlowRate = afterMiddleWay
			else:
				self.afterStartupFlowRates.append( afterMiddleWay )
		if afterStartupSteps > 0:
			self.afterStartupFlowRates.append(1.0)

	def setEarlyShutdown(self):
		"Set the early shutdown variables."
		distanceToThreadBeginning = self.getDistanceToThreadBeginningAfterThreadEnd( self.minimumDistanceForEarlyShutdown )
		earlyShutdownRatio = 1.0
		if distanceToThreadBeginning != None:
			if self.minimumDistanceForEarlyShutdown > 0.0:
				earlyShutdownRatio = distanceToThreadBeginning / self.minimumDistanceForEarlyShutdown
		self.setEarlyShutdownFlowRates( earlyShutdownRatio )
		if len( self.earlyShutdownDistances ) > 0:
			self.shutdownStepIndex = 0

	def setEarlyShutdownFlowRates( self, earlyShutdownRatio ):
		"Set the extrusion width."
		earlyShutdownRatio = min( 1.0, earlyShutdownRatio )
		earlyShutdownRatio = max( 0.0, earlyShutdownRatio )
		self.earlyShutdownDistance = earlyShutdownRatio * self.getActiveFeedRateRatio() * self.oozebaneRepository.earlyShutdownDistance.value
		self.earlyShutdownDistances = []
		self.earlyShutdownFlowRates = []
		earlyShutdownSteps = int( math.floor( earlyShutdownRatio * float( self.oozebaneRepository.slowdownStartupSteps.value ) ) )
		if earlyShutdownSteps < 2:
			earlyShutdownSteps = 0
		earlyShutdownStepsMinusOne = float( earlyShutdownSteps ) - 1.0
		for stepIndex in xrange( earlyShutdownSteps ):
			downMiddleWay = self.getShutdownFlowRateMultiplier( stepIndex / earlyShutdownStepsMinusOne, earlyShutdownSteps )
			downWay = 1.0 - stepIndex / earlyShutdownStepsMinusOne
			self.earlyShutdownFlowRates.append( downMiddleWay )
			self.earlyShutdownDistances.append( downWay * self.earlyShutdownDistance )

	def setEarlyStartupDistance( self, splitLine ):
		"Set the early startup distance."
		if self.earlyStartupDistance != None:
			return
		self.distanceFromThreadEndToThreadBeginning = 0.0
		lastThreadLocation = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
		if self.oldLocation != None:
			self.distanceFromThreadEndToThreadBeginning = lastThreadLocation.distance( self.oldLocation )
		for afterIndex in xrange( self.lineIndex + 1, len(self.lines) ):
			line = self.lines[ afterIndex ]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			if firstWord == 'G1':
				location = gcodec.getLocationFromSplitLine( lastThreadLocation, splitLine )
				self.distanceFromThreadEndToThreadBeginning += location.distance( lastThreadLocation )
				lastThreadLocation = location
			elif firstWord == 'M101':
				distanceConstantRatio = self.distanceFromThreadEndToThreadBeginning / self.earlyStartupDistanceConstant
				earlyStartupOperatingDistance = self.earlyStartupMaximumDistance * ( 1.0 - math.exp( - distanceConstantRatio ) )
				if self.isFirstExtrusion:
					earlyStartupOperatingDistance = self.oozebaneRepository.firstEarlyStartupDistance.value
					self.isFirstExtrusion = False
				self.earlyStartupDistance = earlyStartupOperatingDistance * self.getActiveFeedRateRatio()
				return

	def setExtrusionWidth( self, oozebaneRepository ):
		"Set the extrusion width."
		self.closeSquared = 0.01 * self.edgeWidth * self.edgeWidth
		self.earlyStartupMaximumDistance = oozebaneRepository.earlyStartupMaximumDistance.value
		self.earlyStartupDistanceConstant = oozebaneRepository.earlyStartupDistanceConstant.value
		self.minimumDistanceForEarlyStartup = oozebaneRepository.minimumDistanceForEarlyStartup.value
		self.minimumDistanceForEarlyShutdown = oozebaneRepository.minimumDistanceForEarlyShutdown.value
		self.setEarlyShutdownFlowRates(1.0)
		self.setAfterStartupFlowRates(1.0)


def main():
	"Display the oozebane dialog."
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == "__main__":
	main()
