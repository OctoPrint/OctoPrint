"""
This page is in the table of contents.
The unpause plugin is based on the Shane Hathaway's patch to speed up a line segment to compensate for the delay of the microprocessor.  The description is at:
http://shane.willowrise.com/archives/delay-compensation-in-firmware/

The unpause manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Unpause

==Operation==
The default 'Activate Unpause' checkbox is off.  When it is on, the functions described below will work, when it is off, nothing will be done.

==Settings==
===Delay===
Default is 28 milliseconds, which Shane found for the Arduino.

Defines the delay on the microprocessor that will be at least partially compensated for.

===Maximum Speed===
Default is 1.3.

Defines the maximum amount that the feed rate will be sped up to, compared to the original feed rate.

==Examples==
The following examples unpause the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and unpause.py.

> python unpause.py
This brings up the unpause dialog.

> python unpause.py Screw Holder Bottom.stl
The unpause tool is parsing the file:
Screw Holder Bottom.stl
..
The unpause tool has created the file:
.. Screw Holder Bottom_unpause.gcode

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import intercircle
from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_utilities import skeinforge_craft
from skeinforge_application.skeinforge_utilities import skeinforge_polyfile
from skeinforge_application.skeinforge_utilities import skeinforge_profile
import math
import sys


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCraftedText( fileName, gcodeText, repository=None):
	"Unpause a gcode linear move file or text."
	return getCraftedTextFromText( archive.getTextIfEmpty( fileName, gcodeText ), repository )

def getCraftedTextFromText(gcodeText, repository=None):
	"Unpause a gcode linear move text."
	if gcodec.isProcedureDoneOrFileIsEmpty( gcodeText, 'unpause'):
		return gcodeText
	if repository == None:
		repository = settings.getReadRepository( UnpauseRepository() )
	if not repository.activateUnpause.value:
		return gcodeText
	return UnpauseSkein().getCraftedGcode(gcodeText, repository)

def getNewRepository():
	'Get new repository.'
	return UnpauseRepository()

def getSelectedPlugin(repository):
	"Get the selected plugin."
	for plugin in repository.unpausePlugins:
		if plugin.value:
			return plugin
	return None

def writeOutput(fileName, shouldAnalyze=True):
	"Unpause a gcode linear move file."
	skeinforge_craft.writeChainTextWithNounMessage(fileName, 'unpause', shouldAnalyze)


class UnpauseRepository:
	"A class to handle the unpause settings."
	def __init__(self):
		"Set the default settings, execute title & settings fileName."
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.unpause.html', self)
		self.fileNameInput = settings.FileNameInput().getFromFileName( fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Unpause', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Unpause')
		self.activateUnpause = settings.BooleanSetting().getFromValue('Activate Unpause', self, False )
		self.delay = settings.FloatSpin().getFromValue( 2.0, 'Delay (milliseconds):', self, 42.0, 28.0 )
		self.maximumSpeed = settings.FloatSpin().getFromValue( 1.1, 'Maximum Speed (ratio):', self, 1.9, 1.3 )
		self.executeTitle = 'Unpause'

	def execute(self):
		"Unpause button has been clicked."
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class UnpauseSkein:
	"A class to unpause a skein of extrusions."
	def __init__(self):
		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.feedRateMinute = 959.0
		self.lineIndex = 0
		self.lines = None
		self.oldLocation = None

	def getCraftedGcode(self, gcodeText, repository):
		"Parse gcode text and store the unpause gcode."
		self.delaySecond = repository.delay.value * 0.001
		self.maximumSpeed = repository.maximumSpeed.value
		self.minimumSpeedUpReciprocal = 1.0 / self.maximumSpeed
		self.repository = repository
		self.lines = archive.getTextLines(gcodeText)
		self.parseInitialization()
		for self.lineIndex in xrange(self.lineIndex, len(self.lines)):
			line = self.lines[self.lineIndex]
			self.parseLine(line)
		return self.distanceFeedRate.output.getvalue()

	def getUnpausedArcMovement( self, line, splitLine ):
		"Get an unpaused arc movement."
		self.feedRateMinute = gcodec.getFeedRateMinute( self.feedRateMinute, splitLine )
		if self.oldLocation == None:
			return line
		relativeLocation = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
		self.oldLocation += relativeLocation
		distance = gcodec.getArcDistance(relativeLocation, splitLine)
		return self.getUnpausedMovement(distance, line, splitLine)

	def getUnpausedLinearMovement( self, line, splitLine ):
		"Get an unpaused linear movement."
		self.feedRateMinute = gcodec.getFeedRateMinute( self.feedRateMinute, splitLine )
		location = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
		if self.oldLocation == None:
			self.oldLocation = location
			return line
		distance = abs(self.oldLocation - location)
		self.oldLocation = location
		return self.getUnpausedMovement(distance, line, splitLine)

	def getUnpausedMovement(self, distance, line, splitLine):
		"Get an unpaused movement."
		if distance <= 0.0:
			return line
		resultantReciprocal = 1.0 - self.delaySecond / distance * self.feedRateMinute / 60.0
		resultantReciprocal = max(self.minimumSpeedUpReciprocal, resultantReciprocal)
		return self.distanceFeedRate.getLineWithFeedRate(self.feedRateMinute / resultantReciprocal, line, splitLine)

	def parseInitialization(self):
		'Parse gcode initialization and store the parameters.'
		for self.lineIndex in xrange(len(self.lines)):
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			self.distanceFeedRate.parseSplitLine(firstWord, splitLine)
			if firstWord == '(</extruderInitialization>)':
				self.distanceFeedRate.addTagBracketedProcedure('unpause')
				return
			self.distanceFeedRate.addLine(line)

	def parseLine(self, line):
		"Parse a gcode line."
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if firstWord == 'G1':
			line = self.getUnpausedLinearMovement( line, splitLine )
		if firstWord == 'G2' or firstWord == 'G3':
			line = self.getUnpausedArcMovement( line, splitLine )
		self.distanceFeedRate.addLine(line)


def main():
	"Display the unpause dialog."
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == "__main__":
	main()
