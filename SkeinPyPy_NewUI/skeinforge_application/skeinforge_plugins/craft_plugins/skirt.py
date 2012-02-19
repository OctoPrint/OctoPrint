"""
This page is in the table of contents.
Skirt is a plugin to give the extruder some extra time to begin extruding properly before beginning the object, and to put a baffle around the model in order to keep the extrusion warm.

The skirt manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Skirt

It is loosely based on Lenbook's outline plugin:

http://www.thingiverse.com/thing:4918

it is also loosely based on the outline that Nophead sometimes uses:

http://hydraraptor.blogspot.com/2010/01/hot-metal-and-serendipity.html

and also loosely based on the baffles that Nophead made to keep corners warm:

http://hydraraptor.blogspot.com/2010/09/some-corners-like-it-hot.html

If you want only an outline, set 'Layers To' to one.  This gives the extruder some extra time to begin extruding properly before beginning your object, and gives you an early verification of where your object will be extruded.

If you also want an insulating skirt around the entire object, set 'Layers To' to a huge number, like 912345678.  This will additionally make an insulating baffle around the object; to prevent moving air from cooling the object, which increases warping, especially in corners.

==Operation==
The default 'Activate Skirt' checkbox is off.  When it is on, the functions described below will work, when it is off, nothing will be done.

==Settings==
===Convex===
Default is on.

When selected, the skirt will be convex, going around the model with only convex angles.  If convex is not selected, the skirt will hug the model, going into every nook and cranny.

===Gap over Perimeter Width===
Default is three.

Defines the ratio of the gap between the object and the skirt over the edge width.  If the ratio is too low, the skirt will connect to the object, if the ratio is too high, the skirt willl not provide much insulation for the object.

===Layers To===
Default is a one.

Defines the number of layers of the skirt.  If you want only an outline, set 'Layers To' to one.  If you want an insulating skirt around the entire object, set 'Layers To' to a huge number, like 912345678.

==Examples==
The following examples skirt the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and skirt.py.

> python skirt.py
This brings up the skirt dialog.

> python skirt.py Screw Holder Bottom.stl
The skirt tool is parsing the file:
Screw Holder Bottom.stl
..
The skirt tool has created the file:
.. Screw Holder Bottom_skirt.gcode

"""


from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
from fabmetheus_utilities.geometry.solids import triangle_mesh
from fabmetheus_utilities.vector3 import Vector3
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


def getCraftedText(fileName, text='', repository=None):
	'Skirt the fill file or text.'
	return getCraftedTextFromText(archive.getTextIfEmpty(fileName, text), repository)

def getCraftedTextFromText(gcodeText, repository=None):
	'Skirt the fill text.'
	if gcodec.isProcedureDoneOrFileIsEmpty(gcodeText, 'skirt'):
		return gcodeText
	if repository == None:
		repository = settings.getReadRepository(SkirtRepository())
	if not repository.activateSkirt.value:
		return gcodeText
	return SkirtSkein().getCraftedGcode(gcodeText, repository)

def getNewRepository():
	'Get new repository.'
	return SkirtRepository()

def getOuterLoops(loops):
	'Get widdershins outer loops.'
	outerLoops = []
	for loop in loops:
		if not euclidean.isPathInsideLoops(outerLoops, loop):
			outerLoops.append(loop)
	intercircle.directLoops(True, outerLoops)
	return outerLoops

def writeOutput(fileName, shouldAnalyze=True):
	'Skirt a gcode linear move file.'
	skeinforge_craft.writeChainTextWithNounMessage(fileName, 'skirt', shouldAnalyze)


class LoopCrossDictionary:
	'Loop with a horizontal and vertical dictionary.'
	def __init__(self):
		'Initialize LoopCrossDictionary.'
		self.loop = []

	def __repr__(self):
		'Get the string representation of this LoopCrossDictionary.'
		return str(self.loop)


class SkirtRepository:
	'A class to handle the skirt settings.'
	def __init__(self):
		'Set the default settings, execute title & settings fileName.'
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.skirt.html', self)
		self.fileNameInput = settings.FileNameInput().getFromFileName(
			fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Skirt', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Skirt')
		self.activateSkirt = settings.BooleanSetting().getFromValue('Activate Skirt', self, False)
		self.convex = settings.BooleanSetting().getFromValue('Convex:', self, True)
		self.gapOverEdgeWidth = settings.FloatSpin().getFromValue(1.0, 'Gap over Perimeter Width (ratio):', self, 5.0, 3.0)
		self.layersTo = settings.IntSpin().getSingleIncrementFromValue(0, 'Layers To (index):', self, 912345678, 1)
		self.executeTitle = 'Skirt'

	def execute(self):
		'Skirt button has been clicked.'
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(
			self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class SkirtSkein:
	'A class to skirt a skein of extrusions.'
	def __init__(self):
		'Initialize variables.'
		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.feedRateMinute = 961.0
		self.isExtruderActive = False
		self.isSupportLayer = False
		self.layerIndex = -1
		self.lineIndex = 0
		self.lines = None
		self.oldFlowRate = None
		self.oldLocation = None
		self.oldTemperatureInput = None
		self.skirtFlowRate = None
		self.skirtTemperature = None
		self.travelFeedRateMinute = 957.0
		self.unifiedLoop = LoopCrossDictionary()

	def addFlowRate(self, flowRate):
		'Add a line of temperature if different.'
		if flowRate != None:
			self.distanceFeedRate.addLine('M108 S' + euclidean.getFourSignificantFigures(flowRate))

	def addSkirt(self, z):
		'At skirt at z to gcode output.'
		self.setSkirtFeedFlowTemperature()
		self.distanceFeedRate.addLine('(<skirt>)')
		oldTemperature = self.oldTemperatureInput
		self.addTemperatureLineIfDifferent(self.skirtTemperature)
		self.addFlowRate(self.skirtFlowRate)
		for outsetLoop in self.outsetLoops:
			closedLoop = outsetLoop + [outsetLoop[0]]
			self.distanceFeedRate.addGcodeFromFeedRateThreadZ(self.feedRateMinute, closedLoop, self.travelFeedRateMinute, z)
		self.addFlowRate(self.oldFlowRate)
		self.addTemperatureLineIfDifferent(oldTemperature)
		self.distanceFeedRate.addLine('(</skirt>)')

	def addTemperatureLineIfDifferent(self, temperature):
		'Add a line of temperature if different.'
		if temperature == None or temperature == self.oldTemperatureInput:
			return
		self.distanceFeedRate.addLine('M104 S' + euclidean.getRoundedToThreePlaces(temperature))
		self.oldTemperatureInput = temperature

	def createSegmentDictionaries(self, loopCrossDictionary):
		'Create horizontal and vertical segment dictionaries.'
		loopCrossDictionary.horizontalDictionary = self.getHorizontalXIntersectionsTable(loopCrossDictionary.loop)
		flippedLoop = euclidean.getDiagonalFlippedLoop(loopCrossDictionary.loop)
		loopCrossDictionary.verticalDictionary = self.getHorizontalXIntersectionsTable(flippedLoop)

	def createSkirtLoops(self):
		'Create the skirt loops.'
		points = euclidean.getPointsByHorizontalDictionary(self.edgeWidth, self.unifiedLoop.horizontalDictionary)
		points += euclidean.getPointsByVerticalDictionary(self.edgeWidth, self.unifiedLoop.verticalDictionary)
		loops = triangle_mesh.getDescendingAreaOrientedLoops(points, points, 2.5 * self.edgeWidth)
		outerLoops = getOuterLoops(loops)
		outsetLoops = intercircle.getInsetSeparateLoopsFromLoops(outerLoops, -self.skirtOutset)
		self.outsetLoops = getOuterLoops(outsetLoops)
		if self.repository.convex.value:
			self.outsetLoops = [euclidean.getLoopConvex(euclidean.getConcatenatedList(self.outsetLoops))]

	def getCraftedGcode(self, gcodeText, repository):
		'Parse gcode text and store the skirt gcode.'
		self.repository = repository
		self.lines = archive.getTextLines(gcodeText)
		self.parseInitialization()
		self.parseBoundaries()
		self.createSkirtLoops()
		for self.lineIndex in xrange(self.lineIndex, len(self.lines)):
			line = self.lines[self.lineIndex]
			self.parseLine(line)
		return gcodec.getGcodeWithoutDuplication('M108', self.distanceFeedRate.output.getvalue())

	def getHorizontalXIntersectionsTable(self, loop):
		'Get the horizontal x intersections table from the loop.'
		horizontalXIntersectionsTable = {}
		euclidean.addXIntersectionsFromLoopForTable(loop, horizontalXIntersectionsTable, self.edgeWidth)
		return horizontalXIntersectionsTable

	def parseBoundaries(self):
		'Parse the boundaries and union them.'
		self.createSegmentDictionaries(self.unifiedLoop)
		if self.repository.layersTo.value < 1:
			return
		loopCrossDictionary = None
		layerIndex = -1
		for line in self.lines[self.lineIndex :]:
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			if firstWord == '(</boundaryPerimeter>)' or firstWord == '(</raftPerimeter>)':
				self.createSegmentDictionaries(loopCrossDictionary)
				self.unifyLayer(loopCrossDictionary)
				loopCrossDictionary = None
			elif firstWord == '(<boundaryPoint>' or firstWord == '(<raftPoint>':
				location = gcodec.getLocationFromSplitLine(None, splitLine)
				if loopCrossDictionary == None:
					loopCrossDictionary = LoopCrossDictionary()
				loopCrossDictionary.loop.append(location.dropAxis())
			elif firstWord == '(<layer>':
				layerIndex += 1
				if layerIndex > self.repository.layersTo.value:
					return
				settings.printProgress(layerIndex, 'skirt')

	def parseInitialization(self):
		'Parse gcode initialization and store the parameters.'
		for self.lineIndex in xrange(len(self.lines)):
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			self.distanceFeedRate.parseSplitLine(firstWord, splitLine)
			if firstWord == '(</extruderInitialization>)':
				self.distanceFeedRate.addTagBracketedProcedure('skirt')
				return
			elif firstWord == '(<objectNextLayersTemperature>':
				self.oldTemperatureInput = float(splitLine[1])
				self.skirtTemperature = self.oldTemperatureInput
			elif firstWord == '(<operatingFeedRatePerSecond>':
				self.feedRateMinute = 60.0 * float(splitLine[1])
			elif firstWord == '(<operatingFlowRate>':
				self.oldFlowRate = float(splitLine[1])
				self.skirtFlowRate = self.oldFlowRate
			elif firstWord == '(<edgeWidth>':
				self.edgeWidth = float(splitLine[1])
				self.skirtOutset = (self.repository.gapOverEdgeWidth.value + 0.5) * self.edgeWidth
				self.distanceFeedRate.addTagRoundedLine('skirtOutset', self.skirtOutset)
			elif firstWord == '(<travelFeedRatePerSecond>':
				self.travelFeedRateMinute = 60.0 * float(splitLine[1])
			self.distanceFeedRate.addLine(line)

	def parseLine(self, line):
		'Parse a gcode line and add it to the skirt skein.'
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if firstWord == '(<raftPerimeter>)' or firstWord == '(</raftPerimeter>)' or firstWord == '(<raftPoint>':
			return
		self.distanceFeedRate.addLine(line)
		if firstWord == 'G1':
			self.feedRateMinute = gcodec.getFeedRateMinute(self.feedRateMinute, splitLine)
		elif firstWord == '(<layer>':
			self.layerIndex += 1
			if self.layerIndex < self.repository.layersTo.value:
				self.addSkirt(float(splitLine[1]))
		elif firstWord == 'M101':
			self.isExtruderActive = True
		elif firstWord == 'M103':
			self.isExtruderActive = False
		elif firstWord == 'M104':
			self.oldTemperatureInput = gcodec.getDoubleAfterFirstLetter(splitLine[1])
			self.skirtTemperature = self.oldTemperatureInput
		elif firstWord == 'M108':
			self.oldFlowRate = gcodec.getDoubleAfterFirstLetter(splitLine[1])
			self.skirtFlowRate = self.oldFlowRate
		elif firstWord == '(<supportLayer>)':
			self.isSupportLayer = True
		elif firstWord == '(</supportLayer>)':
			self.isSupportLayer = False

	def setSkirtFeedFlowTemperature(self):
		'Set the skirt feed rate, flow rate and temperature to that of the next extrusion.'
		isExtruderActive = self.isExtruderActive
		isSupportLayer = self.isSupportLayer
		for lineIndex in xrange(self.lineIndex, len(self.lines)):
			line = self.lines[lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			if firstWord == 'G1':
				self.feedRateMinute = gcodec.getFeedRateMinute(self.feedRateMinute, splitLine)
				if isExtruderActive:
					if not isSupportLayer:
						return
			elif firstWord == 'M101':
				isExtruderActive = True
			elif firstWord == 'M103':
				isExtruderActive = False
			elif firstWord == 'M104':
				self.skirtTemperature = gcodec.getDoubleAfterFirstLetter(splitLine[1])
			elif firstWord == 'M108':
				self.skirtFlowRate = gcodec.getDoubleAfterFirstLetter(splitLine[1])
			elif firstWord == '(<supportLayer>)':
				isSupportLayer = True
			elif firstWord == '(</supportLayer>)':
				isSupportLayer = False

	def unifyLayer(self, loopCrossDictionary):
		'Union the loopCrossDictionary with the unifiedLoop.'
		euclidean.joinXIntersectionsTables(loopCrossDictionary.horizontalDictionary, self.unifiedLoop.horizontalDictionary)
		euclidean.joinXIntersectionsTables(loopCrossDictionary.verticalDictionary, self.unifiedLoop.verticalDictionary)


def main():
	'Display the skirt dialog.'
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == '__main__':
	main()
