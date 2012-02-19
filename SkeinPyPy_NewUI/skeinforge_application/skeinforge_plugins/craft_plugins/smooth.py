"""
This page is in the table of contents.
This plugin smooths jagged extruder paths.  It takes shortcuts through jagged paths and decreases the feed rate to compensate.

Smooth is based on ideas in Nophead's frequency limit post: 

http://hydraraptor.blogspot.com/2010/12/frequency-limit.html

The smooth manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Smooth

==Operation==
The default 'Activate Smooth' checkbox is off.  When it is on, the functions described below will work, when it is off, nothing will be done.

==Settings==
===Layers From===
Default: 1

Defines which layer of the print the smoothing process starts from.  If this is set this to zero, that might cause the smoothed parts of the bottom edge not to adhere well to the print surface.  However, this is just a potential problem in theory, no bottom adhesion problem has been reported. 

===Maximum Shortening over Width===
Default: 1.2

Defines the maximum shortening of the shortcut compared to the original path.  Smooth goes over the path and if the shortcut between the midpoint of one line and the midpoint of the second line after is not too short compared to the original and the shortcut is not too long, it replaces the jagged original with the shortcut.  If the maximum shortening is too much, smooth will shorten paths which should not of been shortened and will leave blobs and holes in the model.  If the maximum shortening is too little, even jagged paths that could be shortened safely won't be smoothed.

==Examples==
The following examples smooth the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and smooth.py.

> python smooth.py
This brings up the smooth dialog.

> python smooth.py Screw Holder Bottom.stl
The smooth tool is parsing the file:
Screw Holder Bottom.stl
..
The smooth tool has created the file:
.. Screw Holder Bottom_smooth.gcode

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
import sys


__author__ = 'Enrique Perez (perez_enrique aht yahoo.com) & James Blackwell (jim_blag ahht hotmail.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCraftedText(fileName, gcodeText, repository=None):
	'Smooth a gcode linear move text.'
	return getCraftedTextFromText(archive.getTextIfEmpty(fileName, gcodeText), repository)

def getCraftedTextFromText(gcodeText, repository=None):
	'Smooth a gcode linear move text.'
	if gcodec.isProcedureDoneOrFileIsEmpty(gcodeText, 'smooth'):
		return gcodeText
	if repository == None:
		repository = settings.getReadRepository(SmoothRepository())
	if not repository.activateSmooth.value:
		return gcodeText
	return SmoothSkein().getCraftedGcode(gcodeText, repository)

def getNewRepository():
	'Get new repository.'
	return SmoothRepository()

def writeOutput(fileName, shouldAnalyze=True):
	'Smooth a gcode linear move file.  Chain smooth the gcode if it is not already smoothed.'
	skeinforge_craft.writeChainTextWithNounMessage(fileName, 'smooth', shouldAnalyze)


class SmoothRepository:
	'A class to handle the smooth settings.'
	def __init__(self):
		'Set the default settings, execute title & settings fileName.'
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.smooth.html', self )
		self.fileNameInput = settings.FileNameInput().getFromFileName( fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Smooth', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Smooth')
		self.activateSmooth = settings.BooleanSetting().getFromValue('Activate Smooth', self, False)
		self.layersFrom = settings.IntSpin().getSingleIncrementFromValue(0, 'Layers From (index):', self, 912345678, 1)
		self.maximumShorteningOverWidth = settings.FloatSpin().getFromValue(0.2, 'Maximum Shortening over Width (float):', self, 2.0, 1.2)
		self.executeTitle = 'Smooth'

	def execute(self):
		'Smooth button has been clicked.'
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class SmoothSkein:
	'A class to smooth a skein of extrusions.'
	def __init__(self):
		'Initialize.'
 		self.boundaryLayerIndex = -1
		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.feedRateMinute = 959.0
		self.infill = None
		self.layerCount = settings.LayerCount()
		self.lineIndex = 0
		self.lines = None
		self.oldLocation = None
		self.travelFeedRateMinute = 957.0

	def addSmoothedInfill(self):
		'Add smoothed infill.'
		if len(self.infill) < 4:
			self.distanceFeedRate.addGcodeFromFeedRateThreadZ(self.feedRateMinute, self.infill, self.travelFeedRateMinute, self.oldLocation.z)
			return
		self.distanceFeedRate.addGcodeMovementZWithFeedRate(self.travelFeedRateMinute, self.infill[0], self.oldLocation.z)
		self.distanceFeedRate.addLine('M101')
		lengthMinusOne = len(self.infill) - 1
		lengthMinusTwo = lengthMinusOne - 1
		wasOriginalPoint = True
		pointIndex = 0
		while pointIndex < lengthMinusOne:
			nextPoint = self.infill[pointIndex + 1]
			afterNextIndex = pointIndex + 2
			if afterNextIndex < lengthMinusTwo:
				point = self.infill[pointIndex]
				midpoint = 0.5 * (point + nextPoint)
				afterNextPoint = self.infill[afterNextIndex]
				afterNextNextPoint = self.infill[afterNextIndex + 1]
				afterNextMidpoint = 0.5 * (afterNextPoint + afterNextNextPoint)
				shortcutDistance = abs(afterNextMidpoint - midpoint)
				originalDistance = abs(midpoint - point) + abs(afterNextPoint - nextPoint) + abs(afterNextMidpoint - afterNextPoint)
				segment = euclidean.getNormalized(nextPoint - point)
				afterNextSegment = euclidean.getNormalized(afterNextNextPoint - afterNextPoint)
				sameDirection = self.getIsParallelToRotation(segment) and self.getIsParallelToRotation(afterNextSegment)
				if originalDistance - shortcutDistance < self.maximumShortening and shortcutDistance < self.maximumDistance and sameDirection:
					if wasOriginalPoint:
						self.distanceFeedRate.addGcodeMovementZWithFeedRate(self.feedRateMinute, midpoint, self.oldLocation.z)
					feedrate = self.feedRateMinute
					if originalDistance != 0.0:
						feedrate *= shortcutDistance / originalDistance
					self.distanceFeedRate.addGcodeMovementZWithFeedRate(feedrate, afterNextMidpoint, self.oldLocation.z)
					wasOriginalPoint = False
					pointIndex += 1
				else:
					self.distanceFeedRate.addGcodeMovementZWithFeedRate(self.feedRateMinute, nextPoint, self.oldLocation.z)
					wasOriginalPoint = True
			else:
				self.distanceFeedRate.addGcodeMovementZWithFeedRate(self.feedRateMinute, nextPoint, self.oldLocation.z)
				wasOriginalPoint = True
			pointIndex += 1
		self.distanceFeedRate.addLine('M103')

	def getCraftedGcode( self, gcodeText, repository ):
		'Parse gcode text and store the smooth gcode.'
		self.lines = archive.getTextLines(gcodeText)
		self.repository = repository
		self.layersFromBottom = repository.layersFrom.value
		self.parseInitialization()
		for self.lineIndex in xrange(self.lineIndex, len(self.lines)):
			line = self.lines[self.lineIndex]
			self.parseLine(line)
		return self.distanceFeedRate.output.getvalue()

	def getIsParallelToRotation(self, segment):
		'Determine if the segment is parallel to the rotation.'
		return abs(euclidean.getDotProduct(segment, self.rotation)) > 0.99999

	def parseInitialization(self):
		'Parse gcode initialization and store the parameters.'
		for self.lineIndex in xrange(len(self.lines)):
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			self.distanceFeedRate.parseSplitLine(firstWord, splitLine)
			if firstWord == '(</extruderInitialization>)':
				self.distanceFeedRate.addTagBracketedProcedure('smooth')
				return
			elif firstWord == '(<infillWidth>':
				self.infillWidth = float(splitLine[1])
				self.maximumShortening = self.repository.maximumShorteningOverWidth.value * self.infillWidth
				self.maximumDistance = 1.5 * self.maximumShortening
			elif firstWord == '(<travelFeedRatePerSecond>':
				self.travelFeedRateMinute = 60.0 * float(splitLine[1])
			self.distanceFeedRate.addLine(line)

	def parseLine(self, line):
		'Parse a gcode line and add it to the smooth skein.'
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if firstWord == '(<boundaryPerimeter>)':
			if self.boundaryLayerIndex < 0:
				self.boundaryLayerIndex = 0
		elif firstWord == 'G1':
			self.feedRateMinute = gcodec.getFeedRateMinute(self.feedRateMinute, splitLine)
			location = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
			self.oldLocation = location
			if self.infill != None:
				self.infill.append(location.dropAxis())
				return
		elif firstWord == '(<infill>)':
			if self.boundaryLayerIndex >= self.layersFromBottom:
				self.infill = []
		elif firstWord == '(</infill>)':
			self.infill = None
		elif firstWord == '(<layer>':
			self.layerCount.printProgressIncrement('smooth')
			if self.boundaryLayerIndex >= 0:
				self.boundaryLayerIndex += 1
		elif firstWord == 'M101':
			if self.infill != None:
				if len(self.infill) > 1:
					self.infill = [self.infill[0]]
				return
		elif firstWord == 'M103':
			if self.infill != None:
				self.addSmoothedInfill()
				self.infill = []
				return
		elif firstWord == '(<rotation>':
			self.rotation = gcodec.getRotationBySplitLine(splitLine)
		self.distanceFeedRate.addLine(line)


def main():
	'Display the smooth dialog.'
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == '__main__':
	main()
