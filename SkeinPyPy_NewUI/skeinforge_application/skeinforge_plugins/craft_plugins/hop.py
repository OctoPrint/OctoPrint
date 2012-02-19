"""
This page is in the table of contents.
Hop is a script to raise the extruder when it is not extruding.

Note: 

Note: In some cases where you have thin overhang this plugin can help solve the problem object being knocked off by the head

The hop manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Hop

==Operation==
The default 'Activate Hop' checkbox is off.

It is off because Vik and Nophead found better results without hopping.  Numerous users reported better output without this plugin hence it is off by default.  

When activated the extruder will hop when traveling.  When it is off, nothing will be done.

==Settings==
===Hop Over Layer Thickness===
Default is one.

Defines the ratio of the hop height over the layer height, this is the most important hop setting.

===Minimum Hop Angle===
Default is 20 degrees.

Defines the minimum angle that the path of the extruder will be raised.  An angle of ninety means that the extruder will go straight up as soon as it is not extruding and a low angle means the extruder path will gradually rise to the hop height.

==Examples==
The following examples hop the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and hop.py.

> python hop.py
This brings up the hop dialog.

> python hop.py Screw Holder Bottom.stl
The hop tool is parsing the file:
Screw Holder Bottom.stl
..
The hop tool has created the file:
.. Screw Holder Bottom_hop.gcode

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


def getCraftedText( fileName, text, hopRepository = None ):
	"Hop a gcode linear move text."
	return getCraftedTextFromText( archive.getTextIfEmpty(fileName, text), hopRepository )

def getCraftedTextFromText( gcodeText, hopRepository = None ):
	"Hop a gcode linear move text."
	if gcodec.isProcedureDoneOrFileIsEmpty( gcodeText, 'hop'):
		return gcodeText
	if hopRepository == None:
		hopRepository = settings.getReadRepository( HopRepository() )
	if not hopRepository.activateHop.value:
		return gcodeText
	return HopSkein().getCraftedGcode( gcodeText, hopRepository )

def getNewRepository():
	'Get new repository.'
	return HopRepository()

def writeOutput(fileName, shouldAnalyze=True):
	"Hop a gcode linear move file.  Chain hop the gcode if it is not already hopped."
	skeinforge_craft.writeChainTextWithNounMessage(fileName, 'hop', shouldAnalyze)


class HopRepository:
	"A class to handle the hop settings."
	def __init__(self):
		"Set the default settings, execute title & settings fileName."
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.hop.html', self )
		self.fileNameInput = settings.FileNameInput().getFromFileName( fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Hop', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Hop')
		self.activateHop = settings.BooleanSetting().getFromValue('Activate Hop', self, False )
		self.hopOverLayerThickness = settings.FloatSpin().getFromValue( 0.5, 'Hop Over Layer Thickness (ratio):', self, 1.5, 1.0 )
		self.minimumHopAngle = settings.FloatSpin().getFromValue( 20.0, 'Minimum Hop Angle (degrees):', self, 60.0, 30.0 )
		self.executeTitle = 'Hop'

	def execute(self):
		"Hop button has been clicked."
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class HopSkein:
	"A class to hop a skein of extrusions."
	def __init__(self):
		'Initialize'
		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.extruderActive = False
		self.feedRateMinute = 961.0
		self.hopHeight = 0.4
		self.hopDistance = self.hopHeight
		self.justDeactivated = False
		self.layerCount = settings.LayerCount()
		self.lineIndex = 0
		self.lines = None
		self.oldLocation = None

	def getCraftedGcode( self, gcodeText, hopRepository ):
		"Parse gcode text and store the hop gcode."
		self.lines = archive.getTextLines(gcodeText)
		self.minimumSlope = math.tan( math.radians( hopRepository.minimumHopAngle.value ) )
		self.parseInitialization( hopRepository )
		for self.lineIndex in xrange(self.lineIndex, len(self.lines)):
			line = self.lines[self.lineIndex]
			self.parseLine(line)
		return self.distanceFeedRate.output.getvalue()

	def getHopLine(self, line):
		"Get hopped gcode line."
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		self.feedRateMinute = gcodec.getFeedRateMinute( self.feedRateMinute, splitLine )
		if self.extruderActive:
			return line
		location = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
		highestZ = location.z
		if self.oldLocation != None:
			highestZ = max( highestZ, self.oldLocation.z )
		highestZHop = highestZ + self.hopHeight
		locationComplex = location.dropAxis()
		if self.justDeactivated:
			oldLocationComplex = self.oldLocation.dropAxis()
			distance = abs( locationComplex - oldLocationComplex )
			if distance < self.minimumDistance:
				if self.isNextTravel() or distance == 0.0:
					return self.distanceFeedRate.getLineWithZ( line, splitLine, highestZHop )
			alongRatio = min( 0.41666666, self.hopDistance / distance )
			oneMinusAlong = 1.0 - alongRatio
			closeLocation = oldLocationComplex * oneMinusAlong + locationComplex * alongRatio
			self.distanceFeedRate.addLine( self.distanceFeedRate.getLineWithZ( line, splitLine, highestZHop ) )
			if self.isNextTravel():
				return self.distanceFeedRate.getLineWithZ( line, splitLine, highestZHop )
			farLocation = oldLocationComplex * alongRatio + locationComplex * oneMinusAlong
			self.distanceFeedRate.addGcodeMovementZWithFeedRate( self.feedRateMinute, farLocation, highestZHop )
			return line
		if self.isNextTravel():
			return self.distanceFeedRate.getLineWithZ( line, splitLine, highestZHop )
		return line

	def isNextTravel(self):
		"Determine if there is another linear travel before the thread ends."
		for afterIndex in xrange( self.lineIndex + 1, len(self.lines) ):
			line = self.lines[ afterIndex ]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			if firstWord == 'G1':
				return True
			if firstWord == 'M101':
				return False
		return False

	def parseInitialization( self, hopRepository ):
		'Parse gcode initialization and store the parameters.'
		for self.lineIndex in xrange(len(self.lines)):
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			self.distanceFeedRate.parseSplitLine(firstWord, splitLine)
			if firstWord == '(<layerHeight>':
				layerHeight = float(splitLine[1])
				self.hopHeight = hopRepository.hopOverLayerThickness.value * layerHeight
				self.hopDistance = self.hopHeight / self.minimumSlope
				self.minimumDistance = 0.5 * layerHeight
			elif firstWord == '(</extruderInitialization>)':
				self.distanceFeedRate.addTagBracketedProcedure('hop')
				return
			self.distanceFeedRate.addLine(line)

	def parseLine(self, line):
		"Parse a gcode line and add it to the bevel gcode."
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if self.distanceFeedRate.getIsAlteration(line):
			return
		if firstWord == 'G1':
			line = self.getHopLine(line)
			self.oldLocation = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
			self.justDeactivated = False
		elif firstWord == '(<layer>':
			self.layerCount.printProgressIncrement('hop')
		elif firstWord == 'M101':
			self.extruderActive = True
		elif firstWord == 'M103':
			self.extruderActive = False
			self.justDeactivated = True
		self.distanceFeedRate.addLineCheckAlteration(line)


def main():
	"Display the hop dialog."
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == "__main__":
	main()
