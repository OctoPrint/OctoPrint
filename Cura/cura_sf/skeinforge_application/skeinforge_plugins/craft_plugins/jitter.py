"""
This page is in the table of contents.
This craft tool jitters the loop end position to a different place on each layer to prevent a ridge from being created on the side of the object.

The jitter manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Jitter

==Operation==
The default 'Activate Jitter' checkbox is on.  When it is on, the functions described below will work, when it is off, nothing will be done.

==Settings==
===Jitter Over Perimeter Width===
Default: 2

Defines the amount the loop ends will be jittered over the edge width.  A high value means the loops will start all over the place and a low value means loops will start at roughly the same place on each layer.

For example if you turn jitter off and print a cube every outside shell on the cube will start from exactly the same point so you will have a visible "mark/line/seam" on the side of the cube.  Using the jitter tool you move that start point around hence you avoid that visible seam. 


==Examples==
The following examples jitter the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and jitter.py.

> python jitter.py
This brings up the jitter dialog.

> python jitter.py Screw Holder Bottom.stl
The jitter tool is parsing the file:
Screw Holder Bottom.stl
..
The jitter tool has created the file:
.. Screw Holder Bottom_jitter.gcode

"""

from __future__ import absolute_import

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


def getCraftedText( fileName, text, jitterRepository = None ):
	'Jitter a gcode linear move text.'
	return getCraftedTextFromText( archive.getTextIfEmpty(fileName, text), jitterRepository )

def getCraftedTextFromText( gcodeText, jitterRepository = None ):
	'Jitter a gcode linear move text.'
	if gcodec.isProcedureDoneOrFileIsEmpty( gcodeText, 'jitter'):
		return gcodeText
	if jitterRepository == None:
		jitterRepository = settings.getReadRepository( JitterRepository() )
	if not jitterRepository.activateJitter.value:
		return gcodeText
	return JitterSkein().getCraftedGcode( jitterRepository, gcodeText )

def getJitteredLoop( jitterDistance, jitterLoop ):
	'Get a jittered loop path.'
	loopLength = euclidean.getLoopLength( jitterLoop )
	lastLength = 0.0
	pointIndex = 0
	totalLength = 0.0
	jitterPosition = ( jitterDistance + 256.0 * loopLength ) % loopLength
	while totalLength < jitterPosition and pointIndex < len( jitterLoop ):
		firstPoint = jitterLoop[pointIndex]
		secondPoint  = jitterLoop[ (pointIndex + 1) % len( jitterLoop ) ]
		pointIndex += 1
		lastLength = totalLength
		totalLength += abs(firstPoint - secondPoint)
	remainingLength = jitterPosition - lastLength
	pointIndex = pointIndex % len( jitterLoop )
	ultimateJitteredPoint = jitterLoop[pointIndex]
	penultimateJitteredPointIndex = ( pointIndex + len( jitterLoop ) - 1 ) % len( jitterLoop )
	penultimateJitteredPoint = jitterLoop[ penultimateJitteredPointIndex ]
	segment = ultimateJitteredPoint - penultimateJitteredPoint
	segmentLength = abs(segment)
	originalOffsetLoop = euclidean.getAroundLoop( pointIndex, pointIndex, jitterLoop )
	if segmentLength <= 0.0:
		return originalOffsetLoop
	newUltimatePoint = penultimateJitteredPoint + segment * remainingLength / segmentLength
	return [newUltimatePoint] + originalOffsetLoop

def getNewRepository():
	'Get new repository.'
	return JitterRepository()

def isLoopNumberEqual( betweenX, betweenXIndex, loopNumber ):
	'Determine if the loop number is equal.'
	if betweenXIndex >= len( betweenX ):
		return False
	return betweenX[ betweenXIndex ].index == loopNumber

def writeOutput(fileName, shouldAnalyze=True):
	'Jitter a gcode linear move file.'
	skeinforge_craft.writeChainTextWithNounMessage(fileName, 'jitter', shouldAnalyze)


class JitterRepository:
	'A class to handle the jitter settings.'
	def __init__(self):
		'Set the default settings, execute title & settings fileName.'
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.jitter.html', self)
		self.fileNameInput = settings.FileNameInput().getFromFileName( fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Jitter', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Jitter')
		self.activateJitter = settings.BooleanSetting().getFromValue('Activate Jitter', self, False)
		self.jitterOverEdgeWidth = settings.FloatSpin().getFromValue(1.0, 'Jitter Over Perimeter Width (ratio):', self, 3.0, 2.0)
		self.executeTitle = 'Jitter'

	def execute(self):
		'Jitter button has been clicked.'
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class JitterSkein:
	'A class to jitter a skein of extrusions.'
	def __init__(self):
		'Initialize.'
		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.feedRateMinute = None
		self.isLoopPerimeter = False
		self.layerCount = settings.LayerCount()
		self.layerGolden = 0.0
		self.lineIndex = 0
		self.lines = None
		self.loopPath = None
		self.oldLocation = None
		self.operatingFeedRatePerMinute = None
		self.travelFeedRateMinute = None

	def addGcodeFromThreadZ( self, thread, z ):
		'Add a gcode thread to the output.'
		if len(thread) > 0:
			self.addGcodeMovementZ( self.travelFeedRateMinute, thread[0], z )
		else:
			print('zero length vertex positions array which was skipped over, this should never happen.')
		if len(thread) < 2:
			return
		self.distanceFeedRate.addLine('M101')
		self.addGcodePathZ( self.feedRateMinute, thread[1 :], z )

	def addGcodeMovementZ(self, feedRateMinute, point, z):
		'Add a movement to the output.'
		if feedRateMinute == None:
			feedRateMinute = self.operatingFeedRatePerMinute
		self.distanceFeedRate.addGcodeMovementZWithFeedRate(feedRateMinute, point, z)

	def addGcodePathZ( self, feedRateMinute, path, z ):
		'Add a gcode path, without modifying the extruder, to the output.'
		for point in path:
			self.addGcodeMovementZ(feedRateMinute, point, z)

	def addTailoredLoopPath(self):
		'Add a clipped and jittered loop path.'
		loop = getJitteredLoop(self.layerJitter, self.loopPath.path[: -1])
		loop = euclidean.getAwayPoints(loop, 0.2 * self.edgeWidth)
		self.addGcodeFromThreadZ(loop + [loop[0]], self.loopPath.z)
		self.loopPath = None

	def getCraftedGcode(self, jitterRepository, gcodeText):
		'Parse gcode text and store the jitter gcode.'
		if jitterRepository.jitterOverEdgeWidth.value == 0.0:
			print('Warning, Jitter Over Perimeter Width is zero so thing will be done.')
			return gcodeText
		self.lines = archive.getTextLines(gcodeText)
		self.parseInitialization(jitterRepository)
		for self.lineIndex in xrange(self.lineIndex, len(self.lines)):
			self.parseLine(self.lines[self.lineIndex])
		return self.distanceFeedRate.output.getvalue()

	def parseInitialization( self, jitterRepository ):
		'Parse gcode initialization and store the parameters.'
		for self.lineIndex in xrange(len(self.lines)):
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			self.distanceFeedRate.parseSplitLine(firstWord, splitLine)
			if firstWord == '(</extruderInitialization>)':
				self.distanceFeedRate.addTagBracketedProcedure('jitter')
				return
			elif firstWord == '(<operatingFeedRatePerSecond>':
				self.operatingFeedRatePerMinute = 60.0 * float(splitLine[1])
			elif firstWord == '(<edgeWidth>':
				self.edgeWidth = float(splitLine[1])
				self.jitter = jitterRepository.jitterOverEdgeWidth.value * self.edgeWidth
			elif firstWord == '(<travelFeedRatePerSecond>':
				self.travelFeedRateMinute = 60.0 * float(splitLine[1])
			self.distanceFeedRate.addLine(line)

	def parseLine(self, line):
		'Parse a gcode line, jitter it and add it to the jitter skein.'
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if firstWord == 'G1':
			self.setFeedRateLocationLoopPath(line, splitLine)
			if self.loopPath != None:
				self.loopPath.path.append(self.oldLocation.dropAxis())
				return
		elif firstWord == 'M101':
			if self.loopPath != None:
				return
		elif firstWord == 'M103':
			self.isLoopPerimeter = False
			if self.loopPath != None:
				self.addTailoredLoopPath()
		elif firstWord == '(<layer>':
			self.layerCount.printProgressIncrement('jitter')
			self.layerGolden = math.fmod(self.layerGolden + 0.61803398874989479, 1.0)
			self.layerJitter = self.jitter * self.layerGolden - 0.5
		elif firstWord == '(<loop>' or firstWord == '(<edge>':
			self.isLoopPerimeter = True
		self.distanceFeedRate.addLine(line)

	def setFeedRateLocationLoopPath(self, line, splitLine):
		'Set the feedRateMinute, oldLocation and loopPath.'
		self.feedRateMinute = gcodec.getFeedRateMinute(self.feedRateMinute, splitLine)
		self.oldLocation = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
		if not self.isLoopPerimeter or self.loopPath != None:
			return
		for afterIndex in xrange(self.lineIndex + 1, len(self.lines)):
			line = self.lines[afterIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			if firstWord == 'G1' or firstWord == 'M103':
				return
			elif firstWord == 'M101':
				self.loopPath = euclidean.PathZ(self.oldLocation.z)
				return


def main():
	'Display the jitter dialog.'
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == '__main__':
	main()
