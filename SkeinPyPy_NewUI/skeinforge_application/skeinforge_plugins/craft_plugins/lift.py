"""
This page is in the table of contents.
Lift will change the altitude of the cutting tool when it is on so that it will cut through the slab at the correct altitude.  It will also lift the gcode when the tool is off so that the cutting tool will clear the top of the slab.

==Operation==
The default 'Activate Lift' checkbox is on.  When it is on, the functions described below will work, when it is off, the functions will not be called.

==Settings==
===Cutting Lift over Layer Step===
Default is minus 0.5, because the end mill is the more common tool.

Defines the ratio of the amount the cutting tool will be lifted over the layer step.  If whittle is off the layer step will be the layer height, if it is on, it will be the layer step from the whittle gcode.  If the cutting tool is like an end mill, where the cutting happens until the end of the tool, then the 'Cutting Lift over Layer Step' should be minus 0.5, so that the end mill cuts to the bottom of the slab.  If the cutting tool is like a laser, where the cutting happens around the focal point. the 'Cutting Lift over Layer Step' should be zero, so that the cutting action will be focused in the middle of the slab.

===Clearance above Top===
Default is 5 millimeters.

Defines the distance above the top of the slab the cutting tool will be lifted when will tool is off so that the cutting tool will clear the top of the slab.

==Examples==
The following examples lift the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and lift.py.

> python lift.py
This brings up the lift dialog.

> python lift.py Screw Holder Bottom.stl
The lift tool is parsing the file:
Screw Holder Bottom.stl
..
The lift tool has created the file:
.. Screw Holder Bottom_lift.gcode

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
from fabmetheus_utilities import archive
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_utilities import skeinforge_craft
from skeinforge_application.skeinforge_utilities import skeinforge_polyfile
from skeinforge_application.skeinforge_utilities import skeinforge_profile
import sys


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCraftedText( fileName, text='', liftRepository = None ):
	"Lift the preface file or text."
	return getCraftedTextFromText( archive.getTextIfEmpty(fileName, text), liftRepository )

def getCraftedTextFromText( gcodeText, liftRepository = None ):
	"Lift the preface gcode text."
	if gcodec.isProcedureDoneOrFileIsEmpty( gcodeText, 'lift'):
		return gcodeText
	if liftRepository == None:
		liftRepository = settings.getReadRepository( LiftRepository() )
	if not liftRepository.activateLift.value:
		return gcodeText
	return LiftSkein().getCraftedGcode( liftRepository, gcodeText )

def getNewRepository():
	'Get new repository.'
	return LiftRepository()

def writeOutput(fileName, shouldAnalyze=True):
	"Lift the carving of a gcode file."
	skeinforge_craft.writeChainTextWithNounMessage(fileName, 'lift', shouldAnalyze)


class LiftRepository:
	"A class to handle the lift settings."
	def __init__(self):
		"Set the default settings, execute title & settings fileName."
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.lift.html', self )
		self.fileNameInput = settings.FileNameInput().getFromFileName( fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File to be Lifted', self, '')
		self.activateLift = settings.BooleanSetting().getFromValue('Activate Lift', self, True )
		self.cuttingLiftOverLayerStep = settings.FloatSpin().getFromValue( - 1.0, 'Cutting Lift over Layer Step (ratio):', self, 1.0, - 0.5 )
		self.clearanceAboveTop = settings.FloatSpin().getFromValue( 0.0, 'Clearance above Top (mm):', self, 10.0, 5.0 )
		self.executeTitle = 'Lift'

	def execute(self):
		"Lift button has been clicked."
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class LiftSkein:
	"A class to lift a skein of extrusions."
	def __init__(self):
		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.extruderActive = False
		self.layerStep = None
		self.layerHeight = 0.3333333333
		self.lineIndex = 0
		self.maximumZ = - 912345678.0
		self.oldLocation = None
		self.previousActiveMovementLine = None
		self.previousInactiveMovementLine = None

	def addPreviousInactiveMovementLineIfNecessary(self):
		"Add the previous inactive movement line if necessary."
		if self.previousInactiveMovementLine != None:
			self.distanceFeedRate.addLine( self.previousInactiveMovementLine )
			self.previousInactiveMovementLine = None

	def getCraftedGcode( self, liftRepository, gcodeText ):
		"Parse gcode text and store the lift gcode."
		self.liftRepository = liftRepository
		self.lines = archive.getTextLines(gcodeText)
		self.parseInitialization()
		self.oldLocation = None
		if self.layerStep == None:
			self.layerStep = self.layerHeight
		self.cuttingLift = self.layerStep * liftRepository.cuttingLiftOverLayerStep.value
		self.setMaximumZ()
		self.travelZ = self.maximumZ + 0.5 * self.layerStep + liftRepository.clearanceAboveTop.value
		for line in self.lines[self.lineIndex :]:
			self.parseLine(line)
		return self.distanceFeedRate.output.getvalue()

	def getLinearMove( self, line, location, splitLine ):
		"Get the linear move."
		if self.extruderActive:
			z = location.z + self.cuttingLift
			return self.distanceFeedRate.getLineWithZ( line, splitLine, z )
		if self.previousActiveMovementLine != None:
			previousActiveMovementLineSplit = self.previousActiveMovementLine.split()
			self.distanceFeedRate.addLine( self.distanceFeedRate.getLineWithZ( self.previousActiveMovementLine, previousActiveMovementLineSplit, self.travelZ ) )
			self.previousActiveMovementLine = None
		self.distanceFeedRate.addLine( self.distanceFeedRate.getLineWithZ( line, splitLine, self.travelZ ) )
		self.previousInactiveMovementLine = line
		return ''

	def parseInitialization(self):
		'Parse gcode initialization and store the parameters.'
		for self.lineIndex in xrange(len(self.lines)):
			line = self.lines[self.lineIndex].lstrip()
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			self.distanceFeedRate.parseSplitLine(firstWord, splitLine)
			if firstWord == '(</extruderInitialization>)':
				self.distanceFeedRate.addTagBracketedProcedure('lift')
				return
			elif firstWord == '(<layerHeight>':
				self.layerHeight = float(splitLine[1])
			elif firstWord == '(<layerStep>':
				self.layerStep = float(splitLine[1])
			self.distanceFeedRate.addLine(line)

	def parseLine(self, line):
		"Parse a gcode line and add it to the lift skein."
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if firstWord == 'G1':
			location = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
			line = self.getLinearMove( line, location, splitLine )
			self.previousActiveMovementLine = line
			self.oldLocation = location
		elif firstWord == 'M101':
			self.addPreviousInactiveMovementLineIfNecessary()
			self.extruderActive = True
		elif firstWord == 'M103':
			self.extruderActive = False
		self.distanceFeedRate.addLine(line)

	def setMaximumZ(self):
		"Set maximum  z."
		localOldLocation = None
		for line in self.lines[self.lineIndex :]:
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			if firstWord == 'G1':
				location = gcodec.getLocationFromSplitLine( localOldLocation, splitLine )
				self.maximumZ = max( self.maximumZ, location.z )
				localOldLocation = location


def main():
	"Display the lift dialog."
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == "__main__":
	main()
