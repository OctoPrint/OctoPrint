"""
This page is in the table of contents.
Cool is a craft tool to cool the shape.

Cool works well with a stepper extruder, it does not work well with a DC motor extruder.

If enabled, before each layer that takes less then "Minimum Layer Time" to print the tool head will orbit around the printed area for 'Minimum Layer Time' minus 'the time it takes to print the layer' before it starts printing the layer. This is great way to let layers with smaller area cool before you start printing on top of them (so you do not overheat the area). 

The cool manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Cool

Allan Ecker aka The Masked Retriever's has written the "Skeinforge Quicktip: Cool" at:
http://blog.thingiverse.com/2009/07/28/skeinforge-quicktip-cool/

==Operation==
The default 'Activate Cool' checkbox is on.  When it is on, the functions described below will work, when it is off, the functions will not be called.

==Settings==
===Bridge Cool===
Default is one degree Celcius.

If the layer is a bridge layer, then cool will lower the temperature by 'Bridge Cool' degrees Celcius.

===Cool Type===
Default is 'Slow Down'.

====Orbit====
When selected, cool will add orbits with the extruder off to give the layer time to cool, so that the next layer is not extruded on a molten base.  The orbits will be around the largest island on that layer.  Orbit should only be chosen if you can not upgrade to a stepper extruder.

====Slow Down====
When selected, cool will slow down the extruder so that it will take the minimum layer time to extrude the layer.  DC motors do not operate properly at slow flow rates, so if you have a DC motor extruder, you should upgrade to a stepper extruder, but if you can't do that, you can try using the 'Orbit' option.

===Maximum Cool===
Default is 2 degrees Celcius.

If it takes less time to extrude the layer than the minimum layer time, then cool will lower the temperature by the 'Maximum Cool' setting times the layer time over the minimum layer time.

===Minimum Layer Time===
Default is 60 seconds.

Defines the minimum amount of time the extruder will spend on a layer, this is an important setting.

===Minimum Orbital Radius===
Default is 10 millimeters.

When the orbit cool type is selected, if the area of the largest island is as large as the square of the "Minimum Orbital Radius" then the orbits will be just within the island.  If the island is smaller, then the orbits will be in a square of the "Minimum Orbital Radius" around the center of the island.  This is so that the hot extruder does not stay too close to small islands.

===Name of Alteration Files===
Cool looks for alteration files in the alterations folder in the .skeinforge folder in the home directory.  Cool does not care if the text file names are capitalized, but some file systems do not handle file name cases properly, so to be on the safe side you should give them lower case names.  If it doesn't find the file it then looks in the alterations folder in the skeinforge_plugins folder.  The cool start and end text idea is from:
http://makerhahn.blogspot.com/2008/10/yay-minimug.html

====Name of Cool End File====
Default is cool_end.gcode.

If there is a file with the name of the "Name of Cool End File" setting, it will be added to the end of the orbits.

====Name of Cool Start File====
Default is cool_start.gcode.

If there is a file with the name of the "Name of Cool Start File" setting, it will be added to the start of the orbits.

===Orbital Outset===
Default is 2 millimeters.

When the orbit cool type is selected, the orbits will be outset around the largest island by 'Orbital Outset' millimeters.  If 'Orbital Outset' is negative, the orbits will be inset instead.

===Turn Fan On at Beginning===
Default is on.

When selected, cool will turn the fan on at the beginning of the fabrication by adding the M106 command.

===Turn Fan Off at Ending===
Default is on.

When selected, cool will turn the fan off at the ending of the fabrication by adding the M107 command.

==Examples==
The following examples cool the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and cool.py.

> python cool.py
This brings up the cool dialog.

> python cool.py Screw Holder Bottom.stl
The cool tool is parsing the file:
Screw Holder Bottom.stl
..
The cool tool has created the file:
.. Screw Holder Bottom_cool.gcode

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
import os
import sys


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCraftedText(fileName, text, repository=None):
	'Cool a gcode linear move text.'
	return getCraftedTextFromText(archive.getTextIfEmpty(fileName, text), repository)

def getCraftedTextFromText(gcodeText, repository=None):
	'Cool a gcode linear move text.'
	if gcodec.isProcedureDoneOrFileIsEmpty(gcodeText, 'cool'):
		return gcodeText
	if repository == None:
		repository = settings.getReadRepository(CoolRepository())
	if not repository.activateCool.value:
		return gcodeText
	return CoolSkein().getCraftedGcode(gcodeText, repository)

def getNewRepository():
	'Get new repository.'
	return CoolRepository()

def writeOutput(fileName, shouldAnalyze=True):
	'Cool a gcode linear move file.  Chain cool the gcode if it is not already cooled.'
	skeinforge_craft.writeChainTextWithNounMessage(fileName, 'cool', shouldAnalyze)


class CoolRepository:
	'A class to handle the cool settings.'
	def __init__(self):
		'Set the default settings, execute title & settings fileName.'
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.cool.html', self )
		self.fileNameInput = settings.FileNameInput().getFromFileName(
			fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Cool', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute(
			'http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Cool')
		self.activateCool = settings.BooleanSetting().getFromValue('Activate Cool', self, True)
		self.bridgeCool = settings.FloatSpin().getFromValue(0.0, 'Bridge Cool (Celcius):', self, 10.0, 1.0)
		self.coolType = settings.MenuButtonDisplay().getFromName('Cool Type:', self)
		self.orbit = settings.MenuRadio().getFromMenuButtonDisplay(self.coolType, 'Orbit', self, False)
		self.slowDown = settings.MenuRadio().getFromMenuButtonDisplay(self.coolType, 'Slow Down', self, True)
		self.maximumCool = settings.FloatSpin().getFromValue(0.0, 'Maximum Cool (Celcius):', self, 10.0, 2.0)
		self.minimumLayerTime = settings.FloatSpin().getFromValue(0.0, 'Minimum Layer Time (seconds):', self, 120.0, 10.0)
		self.minimumOrbitalRadius = settings.FloatSpin().getFromValue(
			0.0, 'Minimum Orbital Radius (millimeters):', self, 20.0, 10.0)
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Name of Alteration Files -', self )
		self.nameOfCoolEndFile = settings.StringSetting().getFromValue('Name of Cool End File:', self, 'cool_end.gcode')
		self.nameOfCoolStartFile = settings.StringSetting().getFromValue('Name of Cool Start File:', self, 'cool_start.gcode')
		settings.LabelSeparator().getFromRepository(self)
		self.orbitalOutset = settings.FloatSpin().getFromValue(1.0, 'Orbital Outset (millimeters):', self, 5.0, 2.0)
		self.turnFanOnAtBeginning = settings.BooleanSetting().getFromValue('Turn Fan On at Beginning', self, True)
		self.turnFanOffAtEnding = settings.BooleanSetting().getFromValue('Turn Fan Off at Ending', self, True)
		self.executeTitle = 'Cool'
		
		self.minimumFeedRate = settings.FloatSpin().getFromValue(0.0, 'Minimum feed rate (mm/s):', self, 10.0, 5.0)
		self.fanTurnOnLayerNr = settings.IntSpin().getFromValue(0, 'Fan on at layer:', self, 100, 0)
		self.fanSpeed = settings.IntSpin().getFromValue(0, 'Fan speed (%):', self, 100, 100)

	def execute(self):
		'Cool button has been clicked.'
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(
			self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class CoolSkein:
	'A class to cool a skein of extrusions.'
	def __init__(self):
		self.boundaryLayer = None
		self.coolTemperature = None
		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.feedRateMinute = 960.0
		self.highestZ = 1.0
		self.isBridgeLayer = False
		self.isExtruderActive = False
		self.layerCount = settings.LayerCount()
		self.lineIndex = 0
		self.lines = None
		self.multiplier = 1.0
		self.oldFlowRate = None
		self.oldFlowRateString = None
		self.oldLocation = None
		self.oldTemperature = None
		self.minFeedrate = 0

	def addCoolOrbits(self, remainingOrbitTime):
		'Add the minimum radius cool orbits.'
		if len(self.boundaryLayer.loops) < 1:
			return
		insetBoundaryLoops = self.boundaryLayer.loops
		if abs(self.repository.orbitalOutset.value) > 0.1 * abs(self.edgeWidth):
			insetBoundaryLoops = intercircle.getInsetLoopsFromLoops(self.boundaryLayer.loops, -self.repository.orbitalOutset.value)
		if len(insetBoundaryLoops) < 1:
			insetBoundaryLoops = self.boundaryLayer.loops
		largestLoop = euclidean.getLargestLoop(insetBoundaryLoops)
		loopArea = euclidean.getAreaLoopAbsolute(largestLoop)
		if loopArea < self.minimumArea:
			center = 0.5 * (euclidean.getMaximumByComplexPath(largestLoop) + euclidean.getMinimumByComplexPath(largestLoop))
			centerXBounded = max(center.real, self.boundingRectangle.cornerMinimum.real)
			centerXBounded = min(centerXBounded, self.boundingRectangle.cornerMaximum.real)
			centerYBounded = max(center.imag, self.boundingRectangle.cornerMinimum.imag)
			centerYBounded = min(centerYBounded, self.boundingRectangle.cornerMaximum.imag)
			center = complex(centerXBounded, centerYBounded)
			maximumCorner = center + self.halfCorner
			minimumCorner = center - self.halfCorner
			largestLoop = euclidean.getSquareLoopWiddershins(minimumCorner, maximumCorner)
		pointComplex = euclidean.getXYComplexFromVector3(self.oldLocation)
		if pointComplex != None:
			largestLoop = euclidean.getLoopStartingClosest(self.edgeWidth, pointComplex, largestLoop)
		intercircle.addOrbitsIfLarge(
			self.distanceFeedRate, largestLoop, self.orbitalFeedRatePerSecond, remainingOrbitTime, self.highestZ)

	def addCoolTemperature(self, remainingOrbitTime):
		'Parse a gcode line and add it to the cool skein.'
		if self.repository.minimumLayerTime.value < 0.0001:
			return
		layerCool = self.repository.maximumCool.value * remainingOrbitTime / self.repository.minimumLayerTime.value
		if self.isBridgeLayer:
			layerCool = max(self.repository.bridgeCool.value, layerCool)
		if self.oldTemperature != None and layerCool != 0.0:
			self.coolTemperature = self.oldTemperature - layerCool
			self.addTemperature(self.coolTemperature)

	def addFlowRate(self, flowRate):
		'Add a multipled line of flow rate if different.'
		if flowRate != None:
			self.distanceFeedRate.addLine('M108 S' + euclidean.getFourSignificantFigures(flowRate))

	def addGcodeFromFeedRateMovementZ(self, feedRateMinute, point, z):
		'Add a movement to the output.'
		self.distanceFeedRate.addLine(self.distanceFeedRate.getLinearGcodeMovementWithFeedRate(feedRateMinute, point, z))

	def addOrbitsIfNecessary(self, remainingOrbitTime):
		'Parse a gcode line and add it to the cool skein.'
		if remainingOrbitTime > 0.0 and self.boundaryLayer != None:
			self.addCoolOrbits(remainingOrbitTime)

	def addTemperature(self, temperature):
		'Add a line of temperature.'
		self.distanceFeedRate.addLine('M104 S' + euclidean.getRoundedToThreePlaces(temperature))

	def getCoolMove(self, line, location, splitLine):
		'Get cool line according to time spent on layer.'
		self.feedRateMinute = gcodec.getFeedRateMinute(self.feedRateMinute, splitLine)
		return self.distanceFeedRate.getLineWithFeedRate(max(self.minFeedrate, self.multiplier * self.feedRateMinute), line, splitLine)

	def getCraftedGcode(self, gcodeText, repository):
		'Parse gcode text and store the cool gcode.'
		self.repository = repository
		self.coolEndLines = settings.getAlterationFileLines(repository.nameOfCoolEndFile.value)
		self.coolStartLines = settings.getAlterationFileLines(repository.nameOfCoolStartFile.value)
		self.halfCorner = complex(repository.minimumOrbitalRadius.value, repository.minimumOrbitalRadius.value)
		self.lines = archive.getTextLines(gcodeText)
		self.minimumArea = 4.0 * repository.minimumOrbitalRadius.value * repository.minimumOrbitalRadius.value
		self.minFeedrate = repository.minimumFeedRate.value * 60
		self.parseInitialization()
		self.boundingRectangle = gcodec.BoundingRectangle().getFromGcodeLines(self.lines[self.lineIndex :], 0.5 * self.edgeWidth)
		margin = 0.2 * self.edgeWidth
		halfCornerMargin = self.halfCorner + complex(margin, margin)
		self.boundingRectangle.cornerMaximum -= halfCornerMargin
		self.boundingRectangle.cornerMinimum += halfCornerMargin
		for self.lineIndex in xrange(self.lineIndex, len(self.lines)):
			line = self.lines[self.lineIndex]
			self.parseLine(line)
		if repository.turnFanOffAtEnding.value:
			self.distanceFeedRate.addLine('M107')
		return gcodec.getGcodeWithoutDuplication('M108', self.distanceFeedRate.output.getvalue())

	def getLayerTime(self):
		'Get the time the extruder spends on the layer.'
		feedRateMinute = self.feedRateMinute
		layerTime = 0.0
		lastThreadLocation = self.oldLocation
		for lineIndex in xrange(self.lineIndex, len(self.lines)):
			line = self.lines[lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			if firstWord == 'G1':
				location = gcodec.getLocationFromSplitLine(lastThreadLocation, splitLine)
				feedRateMinute = gcodec.getFeedRateMinute(feedRateMinute, splitLine)
				if lastThreadLocation != None:
					feedRateSecond = feedRateMinute / 60.0
					layerTime += location.distance(lastThreadLocation) / feedRateSecond
				lastThreadLocation = location
			elif firstWord == '(<bridgeRotation>':
				self.isBridgeLayer = True
			elif firstWord == '(</layer>)':
				return layerTime
		return layerTime

	def getLayerTimeActive(self):
		'Get the time the extruder spends on the layer while active.'
		feedRateMinute = self.feedRateMinute
		isExtruderActive = self.isExtruderActive
		layerTime = 0.0
		lastThreadLocation = self.oldLocation
		for lineIndex in xrange(self.lineIndex, len(self.lines)):
			line = self.lines[lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			if firstWord == 'G1':
				location = gcodec.getLocationFromSplitLine(lastThreadLocation, splitLine)
				feedRateMinute = gcodec.getFeedRateMinute(feedRateMinute, splitLine)
				if lastThreadLocation != None and isExtruderActive:
					feedRateSecond = feedRateMinute / 60.0
					layerTime += location.distance(lastThreadLocation) / feedRateSecond
				lastThreadLocation = location
			elif firstWord == 'M101':
				isExtruderActive = True
			elif firstWord == 'M103':
				isExtruderActive = False
			elif firstWord == '(<bridgeRotation>':
				self.isBridgeLayer = True
			elif firstWord == '(</layer>)':
				return layerTime
		return layerTime

	def parseInitialization(self):
		'Parse gcode initialization and store the parameters.'
		for self.lineIndex in xrange(len(self.lines)):
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			self.distanceFeedRate.parseSplitLine(firstWord, splitLine)
			if firstWord == 'M108':
				self.oldFlowRate = float(splitLine[1][1 :])
			elif firstWord == '(<edgeWidth>':
				self.edgeWidth = float(splitLine[1])
			elif firstWord == '(</extruderInitialization>)':
				self.distanceFeedRate.addTagBracketedProcedure('cool')
				return
			elif firstWord == '(<operatingFlowRate>':
				self.oldFlowRate = float(splitLine[1])
			elif firstWord == '(<orbitalFeedRatePerSecond>':
				self.orbitalFeedRatePerSecond = float(splitLine[1])
			self.distanceFeedRate.addLine(line)

	def parseLine(self, line):
		'Parse a gcode line and add it to the cool skein.'
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if firstWord == 'G1':
			location = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
			self.highestZ = max(location.z, self.highestZ)
			if self.isExtruderActive:
				line = self.getCoolMove(line, location, splitLine)
			self.oldLocation = location
		elif firstWord == 'M101':
			self.isExtruderActive = True
		elif firstWord == 'M103':
			self.isExtruderActive = False
		elif firstWord == 'M104':
			self.oldTemperature = gcodec.getDoubleAfterFirstLetter(splitLine[1])
		elif firstWord == 'M108':
			self.oldFlowRate = float(splitLine[1][1 :])
			self.addFlowRate(self.multiplier * self.oldFlowRate)
			return
		elif firstWord == '(<boundaryPoint>':
			self.boundaryLoop.append(gcodec.getLocationFromSplitLine(None, splitLine).dropAxis())
		elif firstWord == '(<layer>':
			self.layerCount.printProgressIncrement('cool')
			self.distanceFeedRate.addLine(line)
			if self.repository.turnFanOnAtBeginning.value and self.repository.fanTurnOnLayerNr.value == self.layerCount.layerIndex:
				self.distanceFeedRate.addLine('M106 S%d' % (self.repository.fanSpeed.value * 255 / 100))
			self.distanceFeedRate.addLinesSetAbsoluteDistanceMode(self.coolStartLines)
			layerTime = self.getLayerTime()
			remainingOrbitTime = max(self.repository.minimumLayerTime.value - layerTime, 0.0)
			self.addCoolTemperature(remainingOrbitTime)
			if self.repository.orbit.value:
				self.addOrbitsIfNecessary(remainingOrbitTime)
			else:
				self.setMultiplier(remainingOrbitTime)
				if self.oldFlowRate != None:
					self.addFlowRate(self.multiplier * self.oldFlowRate)
			z = float(splitLine[1])
			self.boundaryLayer = euclidean.LoopLayer(z)
			self.highestZ = max(z, self.highestZ)
			self.distanceFeedRate.addLinesSetAbsoluteDistanceMode(self.coolEndLines)
			return
		elif firstWord == '(</layer>)':
			self.isBridgeLayer = False
			self.multiplier = 1.0
			if self.coolTemperature != None:
				self.addTemperature(self.oldTemperature)
				self.coolTemperature = None
			if self.oldFlowRate != None:
				self.addFlowRate(self.oldFlowRate)
		elif firstWord == '(<nestedRing>)':
			self.boundaryLoop = []
			self.boundaryLayer.loops.append(self.boundaryLoop)
		self.distanceFeedRate.addLine(line)

	def setMultiplier(self, remainingOrbitTime):
		'Set the feed and flow rate multiplier.'
		layerTimeActive = self.getLayerTimeActive()
		self.multiplier = min(1.0, layerTimeActive / (remainingOrbitTime + layerTimeActive))
		


def main():
	'Display the cool dialog.'
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == '__main__':
	main()
