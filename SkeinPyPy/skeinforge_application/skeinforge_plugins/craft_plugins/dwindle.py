"""
This page is in the table of contents.
Dwindle is a plugin to smooth the surface dwindle of an object by replacing the edge surface with a surface printed at a fraction of the carve
height.  This gives the impression that the object was carved at a much thinner height giving a high-quality finish, but still prints 
in a relatively short time.  The latest process has some similarities with a description at:

The dwindle manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Dwindle

==Operation==
The default 'Activate Dwindle' checkbox is off.  When it is on, the functions described below will work, when it is off, nothing will be done.

==Settings==
====Vertical Divisions====
Default: 2

Defines the number of times the dwindle infill and edges are divided vertically.

==Examples==
The following examples dwindle the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and dwindle.py.

> python dwindle.py
This brings up the dwindle dialog.

> python dwindle.py Screw Holder Bottom.stl
The dwindle tool is parsing the file:
Screw Holder Bottom.stl
..
The dwindle tool has created the file:
.. Screw Holder Bottom_dwindle.gcode

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_utilities import skeinforge_craft
from skeinforge_application.skeinforge_utilities import skeinforge_polyfile
from skeinforge_application.skeinforge_utilities import skeinforge_profile
import math
import sys


__author__ = 'Enrique Perez (perez_enrique aht yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCraftedText(fileName, gcodeText, repository=None):
	'Dwindle a gcode linear move text.'
	return getCraftedTextFromText(archive.getTextIfEmpty(fileName, gcodeText), repository)

def getCraftedTextFromText(gcodeText, repository=None):
	'Dwindle a gcode linear move text.'
	if gcodec.isProcedureDoneOrFileIsEmpty(gcodeText, 'dwindle'):
		return gcodeText
	if repository == None:
		repository = settings.getReadRepository(DwindleRepository())
	if not repository.activateDwindle.value:
		return gcodeText
	return DwindleSkein().getCraftedGcode(gcodeText, repository)

def getNewRepository():
	'Get new repository.'
	return DwindleRepository()

def writeOutput(fileName, shouldAnalyze=True):
	'Dwindle a gcode linear move file.  Chain dwindle the gcode if it is not already dwindle.'
	skeinforge_craft.writeChainTextWithNounMessage(fileName, 'dwindle', shouldAnalyze)


class DwindleRepository:
	'A class to handle the dwindle settings.'
	def __init__(self):
		'Set the default settings, execute title & settings fileName.'
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.dwindle.html', self )
		self.fileNameInput = settings.FileNameInput().getFromFileName( fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Dwindle', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Dwindle')
		self.activateDwindle = settings.BooleanSetting().getFromValue('Activate Dwindle', self, False)
		settings.LabelSeparator().getFromRepository(self)
		self.endRateMultiplier = settings.FloatSpin().getFromValue(0.4, 'End Rate Multiplier (ratio):', self, 0.8, 0.5)
		self.pentUpVolume = settings.FloatSpin().getFromValue(0.1, 'Pent Up Volume (cubic millimeters):', self, 1.0, 0.4)
		self.slowdownSteps = settings.IntSpin().getFromValue(2, 'Slowdown Steps (positive integer):', self, 10, 3)
		self.slowdownVolume = settings.FloatSpin().getFromValue(0.4, 'Slowdown Volume (cubic millimeters):', self, 4.0, 2.0)
		self.executeTitle = 'Dwindle'

	def execute(self):
		'Dwindle button has been clicked.'
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class DwindleSkein:
	'A class to dwindle a skein of extrusions.'
	def __init__(self):
		'Initialize.'
 		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.feedRateMinute = 959.0
		self.isActive = False
		self.layerIndex = -1
		self.lineIndex = 0
		self.lines = None
		self.oldFlowRate = None
		self.oldLocation = None
		self.threadSections = []

	def addThread(self):
		'Add the thread sections to the gcode.'
		if len(self.threadSections) == 0:
			return
		area = self.area
		dwindlePortion = 0.0
		endRateMultiplier = self.repository.endRateMultiplier.value
		halfOverSteps = self.halfOverSteps
		oneOverSteps = self.oneOverSteps
		currentPentUpVolume = self.repository.pentUpVolume.value * self.oldFlowRate / self.operatingFlowRate
		slowdownFlowRateMultiplier = 1.0 - (currentPentUpVolume / self.repository.slowdownVolume.value)
		operatingFeedRateMinute = self.operatingFeedRateMinute
		slowdownVolume = self.repository.slowdownVolume.value
		for threadSectionIndex in xrange(len(self.threadSections) - 1, -1, -1):
			threadSection = self.threadSections[threadSectionIndex]
			dwindlePortion = threadSection.getDwindlePortion(area, dwindlePortion, operatingFeedRateMinute, self.operatingFlowRate, slowdownVolume)
		for threadSection in self.threadSections:
			threadSection.addGcodeThreadSection(self.distanceFeedRate, endRateMultiplier, halfOverSteps, oneOverSteps, slowdownFlowRateMultiplier)
		self.distanceFeedRate.addFlowRateLine(self.oldFlowRate)
		self.threadSections = []

	def getCraftedGcode(self, gcodeText, repository):
		'Parse gcode text and store the dwindle gcode.'
		self.lines = archive.getTextLines(gcodeText)
		self.repository = repository
		self.parseInitialization()
		self.area = self.infillWidth * self.layerHeight
		self.oneOverSteps = 1.0 / float(repository.slowdownSteps.value)
		self.halfOverSteps = 0.5 * self.oneOverSteps
		for self.lineIndex in xrange(self.lineIndex, len(self.lines)):
			line = self.lines[self.lineIndex]
			self.parseLine(line)
		return gcodec.getGcodeWithoutDuplication('M108', self.distanceFeedRate.output.getvalue())

	def parseInitialization(self):
		'Parse gcode initialization and store the parameters.'
		for self.lineIndex in xrange(len(self.lines)):
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			self.distanceFeedRate.parseSplitLine(firstWord, splitLine)
			if firstWord == '(</extruderInitialization>)':
				self.distanceFeedRate.addTagBracketedProcedure('dwindle')
				return
			elif firstWord == '(<infillWidth>':
				self.infillWidth = float(splitLine[1])
			elif firstWord == '(<layerHeight>':
				self.layerHeight = float(splitLine[1])
			elif firstWord == '(<operatingFeedRatePerSecond>':
				self.operatingFeedRateMinute = 60.0 * float(splitLine[1])
			elif firstWord == '(<operatingFlowRate>':
				self.operatingFlowRate = float(splitLine[1])
				self.oldFlowRate = self.operatingFlowRate
			self.distanceFeedRate.addLine(line)

	def parseLine(self, line):
		'Parse a gcode line and add it to the dwindle skein.'
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if firstWord == 'G1':
			self.feedRateMinute = gcodec.getFeedRateMinute(self.feedRateMinute, splitLine)
			location = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
			if self.isActive:
				self.threadSections.append(ThreadSection(self.feedRateMinute, self.oldFlowRate, location, self.oldLocation))
			self.oldLocation = location
		elif firstWord == '(<layer>':
			self.layerIndex += 1
			settings.printProgress(self.layerIndex, 'dwindle')
		elif firstWord == 'M101':
			self.isActive = True
		elif firstWord == 'M103':
			self.isActive = False
			self.addThread()
		elif firstWord == 'M108':
			self.oldFlowRate = gcodec.getDoubleAfterFirstLetter(splitLine[1])
		if len(self.threadSections) == 0:
			self.distanceFeedRate.addLine(line)


class ThreadSection:
	'A class to handle a volumetric section of a thread.'
	def __init__(self, feedRateMinute, flowRate, location, oldLocation):
		'Initialize.'
 		self.feedRateMinute = feedRateMinute
 		self.flowRate = flowRate
 		self.location = location
 		self.oldLocation = oldLocation

	def addGcodeMovementByRate(self, distanceFeedRate, endRateMultiplier, location, rateMultiplier, slowdownFlowRateMultiplier):
		'Add gcode movement by rate multiplier.'
 		flowRate = self.flowRate
		rateMultiplier = rateMultiplier + endRateMultiplier * (1.0 - rateMultiplier)
		if rateMultiplier < 1.0:
			flowRate *= slowdownFlowRateMultiplier
		distanceFeedRate.addFlowRateLine(flowRate * rateMultiplier)
		distanceFeedRate.addGcodeMovementZWithFeedRateVector3(self.feedRateMinute * rateMultiplier, location)

	def addGcodeThreadSection(self, distanceFeedRate, endRateMultiplier, halfOverSteps, oneOverSteps, slowdownFlowRateMultiplier):
		'Add gcode thread section.'
		if self.dwindlePortionEnd > 1.0 - halfOverSteps:
			distanceFeedRate.addFlowRateLine(self.flowRate)
			distanceFeedRate.addGcodeMovementZWithFeedRateVector3(self.feedRateMinute, self.location)
			return
		dwindleDifference = self.dwindlePortionBegin - self.dwindlePortionEnd
		if self.dwindlePortionBegin < 1.0 and dwindleDifference > oneOverSteps:
			numberOfStepsFloat = math.ceil(dwindleDifference / oneOverSteps)
			numberOfSteps = int(numberOfStepsFloat)
			for stepIndex in xrange(numberOfSteps):
				alongBetween = (float(stepIndex) + 0.5) / numberOfStepsFloat
				location = self.getLocation(float(stepIndex + 1) / numberOfStepsFloat)
				rateMultiplier = self.dwindlePortionEnd * alongBetween + self.dwindlePortionBegin * (1.0 - alongBetween)
				self.addGcodeMovementByRate(distanceFeedRate, endRateMultiplier, location, rateMultiplier, slowdownFlowRateMultiplier)
			return
		if self.dwindlePortionBegin > 1.0 and self.dwindlePortionEnd < 1.0:
			alongDwindle = 0.0
			if self.dwindlePortionBegin > 1.0 + halfOverSteps:
				alongDwindle = (self.dwindlePortionBegin - 1.0) / dwindleDifference
				self.addGcodeMovementByRate(distanceFeedRate, endRateMultiplier, self.getLocation(alongDwindle), 1.0, slowdownFlowRateMultiplier)
			alongDwindlePortion = self.dwindlePortionEnd * alongDwindle + self.dwindlePortionBegin * (1.0 - alongDwindle)
			alongDwindleDifference = alongDwindlePortion - self.dwindlePortionEnd
			numberOfStepsFloat = math.ceil(alongDwindleDifference / oneOverSteps)
			numberOfSteps = int(numberOfStepsFloat)
			for stepIndex in xrange(numberOfSteps):
				alongBetween = (float(stepIndex) + 0.5) / numberOfStepsFloat
				alongDwindleLocation = float(stepIndex + 1) / numberOfStepsFloat
				location = self.getLocation(alongDwindleLocation + alongDwindle * (1.0 - alongDwindleLocation))
				rateMultiplier = self.dwindlePortionEnd * alongBetween + alongDwindlePortion * (1.0 - alongBetween)
				self.addGcodeMovementByRate(distanceFeedRate, endRateMultiplier, location, rateMultiplier, slowdownFlowRateMultiplier)
			return
		rateMultiplier = min(0.5 * (self.dwindlePortionBegin + self.dwindlePortionEnd), 1.0)
		self.addGcodeMovementByRate(distanceFeedRate, endRateMultiplier, self.location, rateMultiplier, slowdownFlowRateMultiplier)

	def getDwindlePortion(self, area, dwindlePortion, operatingFeedRateMinute, operatingFlowRate, slowdownVolume):
		'Get cumulative dwindle portion.'
 		self.dwindlePortionEnd = dwindlePortion
 		distance = abs(self.oldLocation - self.location)
 		volume = area * distance
 		self.dwindlePortionBegin = dwindlePortion + volume / slowdownVolume
		return self.dwindlePortionBegin

	def getLocation(self, along):
		'Get location along way.'
		return self.location * along + self.oldLocation * (1.0 - along)


def main():
	'Display the dwindle dialog.'
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == '__main__':
	main()
