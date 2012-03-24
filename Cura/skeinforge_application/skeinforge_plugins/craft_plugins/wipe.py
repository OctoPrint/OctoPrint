"""
This page is in the table of contents.
At the beginning of a layer, depending on the settings, wipe will move the nozzle with the extruder off to the arrival point, then to the wipe point, then to the departure point, then back to the layer.

The wipe path is machine specific, so you'll probably have to change all the default locations.

The wipe manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Wipe

==Operation==
The default 'Activate Wipe' checkbox is off.  When it is on, the functions described below will work, when it is off, nothing will be done.

==Settings==
===Arrival Location===
====Arrival X====
Default is minus seventy millimeters.

Defines the x coordinate of the arrival location.

====Arrival Y====
Default is minus fifty millimeters.

Defines the y coordinate of the arrival location.

====Arrival Z====
Default is fifty millimeters.

Defines the z coordinate of the arrival location.

===Departure Location===
====Departure X====
Default is minus seventy millimeters.

Defines the x coordinate of the departure location.

====Departure Y====
Default is minus forty millimeters.

Defines the y coordinate of the departure location.

====Departure Z====
Default is fifty millimeters.

Defines the z coordinate of the departure location.

===Wipe Location===
====Wipe X====
Default is minus seventy millimeters.

Defines the x coordinate of the wipe location.

====Wipe Y====
Default is minus seventy millimeters.

Defines the y coordinate of the wipe location.

====Wipe Z====
Default is fifty millimeters.

Defines the z coordinate of the wipe location.

===Wipe Period===
Default is three.

Defines the number of layers between wipes.  Wipe will always wipe just before layer zero, afterwards it will wipe every "Wipe Period" layers.  With the default of three, wipe will wipe just before layer zero, layer three, layer six and so on.

==Examples==
The following examples wipe the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and wipe.py.

> python wipe.py
This brings up the wipe dialog.

> python wipe.py Screw Holder Bottom.stl
The wipe tool is parsing the file:
Screw Holder Bottom.stl
..
The wipe tool has created the file:
.. Screw Holder Bottom_wipe.gcode

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


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCraftedText( fileName, text, wipeRepository = None ):
	"Wipe a gcode linear move text."
	return getCraftedTextFromText( archive.getTextIfEmpty(fileName, text), wipeRepository )

def getCraftedTextFromText( gcodeText, wipeRepository = None ):
	"Wipe a gcode linear move text."
	if gcodec.isProcedureDoneOrFileIsEmpty( gcodeText, 'wipe'):
		return gcodeText
	if wipeRepository == None:
		wipeRepository = settings.getReadRepository( WipeRepository() )
	if not wipeRepository.activateWipe.value:
		return gcodeText
	return WipeSkein().getCraftedGcode( gcodeText, wipeRepository )

def getNewRepository():
	'Get new repository.'
	return WipeRepository()

def writeOutput(fileName, shouldAnalyze=True):
	"Wipe a gcode linear move file."
	skeinforge_craft.writeChainTextWithNounMessage(fileName, 'wipe', shouldAnalyze)


class WipeRepository:
	"A class to handle the wipe settings."
	def __init__(self):
		"Set the default settings, execute title & settings fileName."
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.wipe.html', self)
		self.fileNameInput = settings.FileNameInput().getFromFileName(fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Wipe', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Wipe')
		self.activateWipe = settings.BooleanSetting().getFromValue('Activate Wipe', self, False)
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Arrival Location -', self)
		self.locationArrivalX = settings.FloatSpin().getFromValue(-100.0, 'Arrival X (mm):', self, 100.0, -70.0)
		self.locationArrivalY = settings.FloatSpin().getFromValue(-100.0, 'Arrival Y (mm):', self, 100.0, -50.0)
		self.locationArrivalZ = settings.FloatSpin().getFromValue(-100.0, 'Arrival Z (mm):', self, 100.0, 50.0)
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Departure Location -', self)
		self.locationDepartureX = settings.FloatSpin().getFromValue(-100.0, 'Departure X (mm):', self, 100.0, -70.0)
		self.locationDepartureY = settings.FloatSpin().getFromValue(-100.0, 'Departure Y (mm):', self, 100.0, -40.0)
		self.locationDepartureZ = settings.FloatSpin().getFromValue(-100.0, 'Departure Z (mm):', self, 100.0, 50.0)
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Wipe Location -', self)
		self.locationWipeX = settings.FloatSpin().getFromValue(-100.0, 'Wipe X (mm):', self, 100.0, -70.0)
		self.locationWipeY = settings.FloatSpin().getFromValue(-100.0, 'Wipe Y (mm):', self, 100.0, -70.0)
		self.locationWipeZ = settings.FloatSpin().getFromValue(-100.0, 'Wipe Z (mm):', self, 100.0, 50.0)
		settings.LabelSeparator().getFromRepository(self)
		self.wipePeriod = settings.IntSpin().getFromValue(1, 'Wipe Period (layers):', self, 5, 3)
		self.executeTitle = 'Wipe'

	def execute(self):
		"Wipe button has been clicked."
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class WipeSkein:
	"A class to wipe a skein of extrusions."
	def __init__(self):
		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.extruderActive = False
		self.highestZ = None
		self.layerIndex = -1
		self.lineIndex = 0
		self.lines = None
		self.oldLocation = None
		self.shouldWipe = False
		self.travelFeedRateMinute = 957.0

	def addHop( self, begin, end ):
		"Add hop to highest point."
		beginEndDistance = begin.distance(end)
		if beginEndDistance < 3.0 * self.absoluteEdgeWidth:
			return
		alongWay = self.absoluteEdgeWidth / beginEndDistance
		closeToOldLocation = euclidean.getIntermediateLocation( alongWay, begin, end )
		closeToOldLocation.z = self.highestZ
		self.distanceFeedRate.addLine( self.getLinearMoveWithFeedRate( self.travelFeedRateMinute, closeToOldLocation ) )
		closeToOldArrival = euclidean.getIntermediateLocation( alongWay, end, begin )
		closeToOldArrival.z = self.highestZ
		self.distanceFeedRate.addLine( self.getLinearMoveWithFeedRate( self.travelFeedRateMinute, closeToOldArrival ) )

	def addWipeTravel( self, splitLine ):
		"Add the wipe travel gcode."
		location = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
		self.highestZ = max( self.highestZ, location.z )
		if not self.shouldWipe:
			return
		self.shouldWipe = False
		if self.extruderActive:
			self.distanceFeedRate.addLine('M103')
		if self.oldLocation != None:
			self.addHop( self.oldLocation, self.locationArrival )
		self.distanceFeedRate.addLine( self.getLinearMoveWithFeedRate( self.travelFeedRateMinute, self.locationArrival ) )
		self.distanceFeedRate.addLine( self.getLinearMoveWithFeedRate( self.travelFeedRateMinute, self.locationWipe ) )
		self.distanceFeedRate.addLine( self.getLinearMoveWithFeedRate( self.travelFeedRateMinute, self.locationDeparture ) )
		self.addHop( self.locationDeparture, location )
		if self.extruderActive:
			self.distanceFeedRate.addLine('M101')

	def getCraftedGcode( self, gcodeText, wipeRepository ):
		"Parse gcode text and store the wipe gcode."
		self.lines = archive.getTextLines(gcodeText)
		self.wipePeriod = wipeRepository.wipePeriod.value
		self.parseInitialization( wipeRepository )
		self.locationArrival = Vector3( wipeRepository.locationArrivalX.value, wipeRepository.locationArrivalY.value, wipeRepository.locationArrivalZ.value )
		self.locationDeparture = Vector3( wipeRepository.locationDepartureX.value, wipeRepository.locationDepartureY.value, wipeRepository.locationDepartureZ.value )
		self.locationWipe = Vector3( wipeRepository.locationWipeX.value, wipeRepository.locationWipeY.value, wipeRepository.locationWipeZ.value )
		for self.lineIndex in xrange(self.lineIndex, len(self.lines)):
			line = self.lines[self.lineIndex]
			self.parseLine(line)
		return self.distanceFeedRate.output.getvalue()

	def getLinearMoveWithFeedRate( self, feedRate, location ):
		"Get a linear move line with the feedRate."
		return self.distanceFeedRate.getLinearGcodeMovementWithFeedRate( feedRate, location.dropAxis(), location.z )

	def parseInitialization( self, wipeRepository ):
		'Parse gcode initialization and store the parameters.'
		for self.lineIndex in xrange(len(self.lines)):
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			self.distanceFeedRate.parseSplitLine(firstWord, splitLine)
			if firstWord == '(</extruderInitialization>)':
				self.distanceFeedRate.addTagBracketedProcedure('wipe')
				return
			elif firstWord == '(<edgeWidth>':
				self.absoluteEdgeWidth = abs(float(splitLine[1]))
			elif firstWord == '(<travelFeedRatePerSecond>':
				self.travelFeedRateMinute = 60.0 * float(splitLine[1])
			self.distanceFeedRate.addLine(line)

	def parseLine(self, line):
		"Parse a gcode line and add it to the bevel gcode."
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if firstWord == 'G1':
			self.addWipeTravel(splitLine)
			self.oldLocation = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
		elif firstWord == '(<layer>':
			self.layerIndex += 1
			settings.printProgress(self.layerIndex, 'wipe')
			if self.layerIndex % self.wipePeriod == 0:
				self.shouldWipe = True
		elif firstWord == 'M101':
			self.extruderActive = True
		elif firstWord == 'M103':
			self.extruderActive = False
		self.distanceFeedRate.addLine(line)


def main():
	"Display the wipe dialog."
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == "__main__":
	main()
