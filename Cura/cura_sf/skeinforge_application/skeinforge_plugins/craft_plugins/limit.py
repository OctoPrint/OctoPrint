#! /usr/bin/env python
"""
This page is in the table of contents.
This plugin limits the feed rate of the tool head, so that the stepper motors are not driven too fast and skip steps.

The limit manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Limit

The maximum z feed rate is defined in speed.

==Operation==
The default 'Activate Limit' checkbox is on.  When it is on, the functions described below will work, when it is off, nothing will be done.

==Settings==
===Maximum Initial Feed Rate===
Default is one millimeter per second.

Defines the maximum speed of the inital tool head move.

==Examples==
The following examples limit the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and limit.py.

> python limit.py
This brings up the limit dialog.

> python limit.py Screw Holder Bottom.stl
The limit tool is parsing the file:
Screw Holder Bottom.stl
..
The limit tool has created the file:
.. Screw Holder Bottom_limit.gcode

"""
from __future__ import absolute_import

from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
from fabmetheus_utilities import archive
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_utilities import skeinforge_craft
from skeinforge_application.skeinforge_utilities import skeinforge_polyfile
from skeinforge_application.skeinforge_utilities import skeinforge_profile
import sys


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/28/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCraftedText(fileName, gcodeText='', repository=None):
	'Limit a gcode file or text.'
	return getCraftedTextFromText( archive.getTextIfEmpty(fileName, gcodeText), repository )

def getCraftedTextFromText(gcodeText, repository=None):
	'Limit a gcode text.'
	if gcodec.isProcedureDoneOrFileIsEmpty(gcodeText, 'limit'):
		return gcodeText
	if repository == None:
		repository = settings.getReadRepository(LimitRepository())
	if not repository.activateLimit.value:
		return gcodeText
	return LimitSkein().getCraftedGcode(gcodeText, repository)

def getNewRepository():
	'Get new repository.'
	return LimitRepository()

def writeOutput(fileName, shouldAnalyze=True):
	'Limit a gcode file.'
	skeinforge_craft.writeChainTextWithNounMessage(fileName, 'limit', shouldAnalyze)


class LimitRepository:
	'A class to handle the limit settings.'
	def __init__(self):
		'Set the default settings, execute title & settings fileName.'
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.limit.html', self )
		self.fileNameInput = settings.FileNameInput().getFromFileName( fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Limit', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Limit')
		self.activateLimit = settings.BooleanSetting().getFromValue('Activate Limit', self, False)
		self.maximumInitialFeedRate = settings.FloatSpin().getFromValue(0.5, 'Maximum Initial Feed Rate (mm/s):', self, 10.0, 1.0)
		self.executeTitle = 'Limit'

	def execute(self):
		'Limit button has been clicked.'
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class LimitSkein:
	'A class to limit a skein of extrusions.'
	def __init__(self):
		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.feedRateMinute = None
		self.lineIndex = 0
		self.maximumZDrillFeedRatePerSecond = 987654321.0
		self.oldLocation = None

	def getCraftedGcode(self, gcodeText, repository):
		'Parse gcode text and store the limit gcode.'
		self.repository = repository
		self.lines = archive.getTextLines(gcodeText)
		self.parseInitialization()
		self.maximumZDrillFeedRatePerSecond = min(self.maximumZDrillFeedRatePerSecond, self.maximumZFeedRatePerSecond)
		self.maximumZCurrentFeedRatePerSecond = self.maximumZFeedRatePerSecond
		for lineIndex in xrange(self.lineIndex, len(self.lines)):
			self.parseLine( lineIndex )
		return self.distanceFeedRate.output.getvalue()

	def getLimitedInitialMovement(self, line, splitLine):
		'Get a limited linear movement.'
		if self.oldLocation == None:
			line = self.distanceFeedRate.getLineWithFeedRate(60.0 * self.repository.maximumInitialFeedRate.value, line, splitLine)
		return line

	def getZLimitedLine(self, deltaZ, distance, line, splitLine):
		'Get a replaced z limited gcode movement line.'
		zFeedRateSecond = self.feedRateMinute * deltaZ / distance / 60.0
		if zFeedRateSecond <= self.maximumZCurrentFeedRatePerSecond:
			return line
		limitedFeedRateMinute = self.feedRateMinute * self.maximumZCurrentFeedRatePerSecond / zFeedRateSecond
		return self.distanceFeedRate.getLineWithFeedRate(limitedFeedRateMinute, line, splitLine)

	def getZLimitedLineArc(self, line, splitLine):
		'Get a replaced z limited gcode arc movement line.'
		self.feedRateMinute = gcodec.getFeedRateMinute(self.feedRateMinute, splitLine)
		if self.feedRateMinute == None or self.oldLocation == None:
			return line
		relativeLocation = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
		self.oldLocation += relativeLocation
		deltaZ = abs(relativeLocation.z)
		distance = gcodec.getArcDistance(relativeLocation, splitLine)
		return self.getZLimitedLine(deltaZ, distance, line, splitLine)

	def getZLimitedLineLinear(self, line, location, splitLine):
		'Get a replaced z limited gcode linear movement line.'
		self.feedRateMinute = gcodec.getFeedRateMinute(self.feedRateMinute, splitLine)
		if location == self.oldLocation:
			return ''
		if self.feedRateMinute == None or self.oldLocation == None:
			return line
		deltaZ = abs(location.z - self.oldLocation.z)
		distance = abs(location - self.oldLocation)
		return self.getZLimitedLine(deltaZ, distance, line, splitLine)

	def parseInitialization(self):
		'Parse gcode initialization and store the parameters.'
		for self.lineIndex in xrange(len(self.lines)):
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			self.distanceFeedRate.parseSplitLine(firstWord, splitLine)
			if firstWord == '(</extruderInitialization>)':
				self.distanceFeedRate.addTagBracketedProcedure('limit')
				return
			elif firstWord == '(<maximumZDrillFeedRatePerSecond>':
				self.maximumZDrillFeedRatePerSecond = float(splitLine[1])
			elif firstWord == '(<maximumZFeedRatePerSecond>':
				self.maximumZFeedRatePerSecond = float(splitLine[1])
			self.distanceFeedRate.addLine(line)

	def parseLine( self, lineIndex ):
		'Parse a gcode line and add it to the limit skein.'
		line = self.lines[lineIndex].lstrip()
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = gcodec.getFirstWord(splitLine)
		if firstWord == 'G1':
			location = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
			line = self.getLimitedInitialMovement(line, splitLine)
			line = self.getZLimitedLineLinear(line, location, splitLine)
			self.oldLocation = location
		elif firstWord == 'G2' or firstWord == 'G3':
			line = self.getZLimitedLineArc(line, splitLine)
		elif firstWord == 'M101':
			self.maximumZCurrentFeedRatePerSecond = self.maximumZDrillFeedRatePerSecond
		elif firstWord == 'M103':
			self.maximumZCurrentFeedRatePerSecond = self.maximumZFeedRatePerSecond
		self.distanceFeedRate.addLine(line)


def main():
	'Display the limit dialog.'
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == '__main__':
	main()
