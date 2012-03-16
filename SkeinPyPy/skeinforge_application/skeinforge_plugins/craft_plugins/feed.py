"""
This page is in the table of contents.
The feed script sets the maximum feed rate, operating feed rate & travel feed rate.

==Operation==
The default 'Activate Feed' checkbox is on.  When it is on, the functions described below will work, when it is off, the functions will not be called.

==Settings==
===Feed Rate===
Default is 16 millimeters/second.

Defines the feed rate for the shape.

===Maximum Z Drill Feed Rate===
Default is 0.1 millimeters/second.

If your firmware limits the z feed rate, you do not need to set this setting.

Defines the maximum feed that the tool head will move in the z direction while the tool is on.

===Maximum Z Feed Rate===
Default is one millimeter per second.

Defines the maximum speed that the tool head will move in the z direction.

===Travel Feed Rate===
Default is 16 millimeters/second.

Defines the feed rate when the cutter is off.  The travel feed rate could be set as high as the cutter can be moved, it does not have to be limited by the maximum cutter rate.

==Examples==
The following examples feed the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and feed.py.

> python feed.py
This brings up the feed dialog.

> python feed.py Screw Holder Bottom.stl
The feed tool is parsing the file:
Screw Holder Bottom.stl
..
The feed tool has created the file:
.. Screw Holder Bottom_feed.gcode

"""

from __future__ import absolute_import
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


def getCraftedText(fileName, gcodeText='', repository=None):
	"Feed the file or text."
	return getCraftedTextFromText( archive.getTextIfEmpty( fileName, gcodeText ), repository )

def getCraftedTextFromText(gcodeText, repository=None):
	"Feed a gcode linear move text."
	if gcodec.isProcedureDoneOrFileIsEmpty(gcodeText, 'feed'):
		return gcodeText
	if repository == None:
		repository = settings.getReadRepository(FeedRepository())
	if not repository.activateFeed.value:
		return gcodeText
	return FeedSkein().getCraftedGcode(gcodeText, repository)

def getNewRepository():
	'Get new repository.'
	return FeedRepository()

def writeOutput(fileName, shouldAnalyze=True):
	"Feed a gcode linear move file."
	skeinforge_craft.writeChainTextWithNounMessage(fileName, 'feed', shouldAnalyze)


class FeedRepository:
	"A class to handle the feed settings."
	def __init__(self):
		"Set the default settings, execute title & settings fileName."
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.feed.html', self)
		self.fileNameInput = settings.FileNameInput().getFromFileName(fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Feed', self, '')
		self.activateFeed = settings.BooleanSetting().getFromValue('Activate Feed', self, True)
		self.feedRatePerSecond = settings.FloatSpin().getFromValue(2.0, 'Feed Rate (mm/s):', self, 50.0, 16.0)
		self.maximumZDrillFeedRatePerSecond = settings.FloatSpin().getFromValue(0.02, 'Maximum Z Drill Feed Rate (mm/s):', self, 0.5, 0.1)
		self.maximumZFeedRatePerSecond = settings.FloatSpin().getFromValue(0.5, 'Maximum Z Feed Rate (mm/s):', self, 10.0, 1.0)
		self.travelFeedRatePerSecond = settings.FloatSpin().getFromValue(2.0, 'Travel Feed Rate (mm/s):', self, 50.0, 16.0)
		self.executeTitle = 'Feed'

	def execute(self):
		"Feed button has been clicked."
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class FeedSkein:
	"A class to feed a skein of cuttings."
	def __init__(self):
		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.feedRatePerSecond = 16.0
		self.isExtruderActive = False
		self.lineIndex = 0
		self.lines = None
		self.oldFlowrateString = None
		self.oldLocation = None

	def getCraftedGcode(self, gcodeText, repository):
		"Parse gcode text and store the feed gcode."
		self.repository = repository
		self.feedRatePerSecond = repository.feedRatePerSecond.value
		self.travelFeedRateMinute = 60.0 * self.repository.travelFeedRatePerSecond.value
		self.lines = archive.getTextLines(gcodeText)
		self.parseInitialization()
		for line in self.lines[self.lineIndex :]:
			self.parseLine(line)
		return self.distanceFeedRate.output.getvalue()

	def getFeededLine(self, line, splitLine):
		"Get gcode line with feed rate."
		location = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
		self.oldLocation = location
		feedRateMinute = 60.0 * self.feedRatePerSecond
		if not self.isExtruderActive:
			feedRateMinute = self.travelFeedRateMinute
		return self.distanceFeedRate.getLineWithFeedRate(feedRateMinute, line, splitLine)

	def parseInitialization(self):
		'Parse gcode initialization and store the parameters.'
		for self.lineIndex in xrange(len(self.lines)):
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			self.distanceFeedRate.parseSplitLine(firstWord, splitLine)
			if firstWord == '(</extruderInitialization>)':
				self.distanceFeedRate.addTagBracketedProcedure('feed')
				return
			elif firstWord == '(<edgeWidth>':
				self.absoluteEdgeWidth = abs(float(splitLine[1]))
				self.distanceFeedRate.addTagBracketedLine('maximumZDrillFeedRatePerSecond', self.repository.maximumZDrillFeedRatePerSecond.value)
				self.distanceFeedRate.addTagBracketedLine('maximumZFeedRatePerSecond', self.repository.maximumZFeedRatePerSecond.value )
				self.distanceFeedRate.addTagBracketedLine('operatingFeedRatePerSecond', self.feedRatePerSecond)
				self.distanceFeedRate.addTagBracketedLine('travelFeedRatePerSecond', self.repository.travelFeedRatePerSecond.value)
			self.distanceFeedRate.addLine(line)

	def parseLine(self, line):
		"Parse a gcode line and add it to the feed skein."
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if firstWord == 'G1':
			line = self.getFeededLine(line, splitLine)
		elif firstWord == 'M101':
			self.isExtruderActive = True
		elif firstWord == 'M103':
			self.isExtruderActive = False
		self.distanceFeedRate.addLine(line)


def main():
	'Display the feed dialog.'
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == "__main__":
	main()
