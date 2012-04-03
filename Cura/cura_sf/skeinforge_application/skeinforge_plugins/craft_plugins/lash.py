"""
This page is in the table of contents.
Lash is a script to partially compensate for the backlash of the tool head.

The lash manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Lash

The lash tool is ported from Erik de Bruijn's 3D-to-5D-Gcode php GPL'd script at:
http://objects.reprap.org/wiki/3D-to-5D-Gcode.php

The default values are from the settings in Erik's 3D-to-5D-Gcode, I believe the settings are used on his Darwin reprap.

==Operation==
The default 'Activate Lash' checkbox is off.  When it is on, the functions described below will work, when it is off, nothing will be done.

==Settings==
===X Backlash===
Default is 0.2 millimeters.

Defines the distance the tool head will be lashed in the X direction.

===Y Backlash===
Default is 0.2 millimeters.

Defines the distance the tool head will be lashed in the Y direction.

==Examples==
The following examples lash the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and lash.py.

> python lash.py
This brings up the lash dialog.

> python lash.py Screw Holder Bottom.stl
The lash tool is parsing the file:
Screw Holder Bottom.stl
..
The lash tool has created the file:
.. Screw Holder Bottom_lash.gcode

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
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCraftedText( fileName, text, lashRepository = None ):
	"Get a lashed gcode linear move text."
	return getCraftedTextFromText( archive.getTextIfEmpty(fileName, text), lashRepository )

def getCraftedTextFromText( gcodeText, lashRepository = None ):
	"Get a lashed gcode linear move text from text."
	if gcodec.isProcedureDoneOrFileIsEmpty( gcodeText, 'lash'):
		return gcodeText
	if lashRepository == None:
		lashRepository = settings.getReadRepository( LashRepository() )
	if not lashRepository.activateLash.value:
		return gcodeText
	return LashSkein().getCraftedGcode( gcodeText, lashRepository )

def getNewRepository():
	'Get new repository.'
	return LashRepository()

def writeOutput(fileName, shouldAnalyze=True):
	"Lash a gcode linear move file."
	skeinforge_craft.writeChainTextWithNounMessage(fileName, 'lash', shouldAnalyze)


class LashRepository:
	"A class to handle the lash settings."
	def __init__(self):
		"Set the default settings, execute title & settings fileName."
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.lash.html', self)
		self.fileNameInput = settings.FileNameInput().getFromFileName( fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Lash', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Lash')
		self.activateLash = settings.BooleanSetting().getFromValue('Activate Lash', self, False )
		self.xBacklash = settings.FloatSpin().getFromValue( 0.1, 'X Backlash (mm):', self, 0.5, 0.2 )
		self.yBacklash = settings.FloatSpin().getFromValue( 0.1, 'Y Backlash (mm):', self, 0.5, 0.3 )
		self.executeTitle = 'Lash'

	def execute(self):
		"Lash button has been clicked."
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class LashSkein:
	"A class to lash a skein of extrusions."
	def __init__(self):
		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.feedRateMinute = 958.0
		self.lineIndex = 0
		self.lines = None
		self.oldLocation = None

	def getCraftedGcode( self, gcodeText, lashRepository ):
		"Parse gcode text and store the lash gcode."
		self.lines = archive.getTextLines(gcodeText)
		self.lashRepository = lashRepository
		self.xBacklash = lashRepository.xBacklash.value
		self.yBacklash = lashRepository.yBacklash.value
		self.parseInitialization()
		for self.lineIndex in xrange(self.lineIndex, len(self.lines)):
			line = self.lines[self.lineIndex]
			self.parseLash(line)
		return self.distanceFeedRate.output.getvalue()

	def getLashedLine( self, line, location, splitLine ):
		"Get lashed gcode line."
		if self.oldLocation == None:
			return line
		if location.x > self.oldLocation.x:
			line = self.distanceFeedRate.getLineWithX( line, splitLine, location.x + self.xBacklash )
		else:
			line = self.distanceFeedRate.getLineWithX( line, splitLine, location.x - self.xBacklash )
		if location.y > self.oldLocation.y:
			line = self.distanceFeedRate.getLineWithY( line, splitLine, location.y + self.yBacklash )
		else:
			line = self.distanceFeedRate.getLineWithY( line, splitLine, location.y - self.yBacklash )
		return line

	def parseInitialization(self):
		'Parse gcode initialization and store the parameters.'
		for self.lineIndex in xrange(len(self.lines)):
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			self.distanceFeedRate.parseSplitLine(firstWord, splitLine)
			if firstWord == '(</extruderInitialization>)':
				self.distanceFeedRate.addTagBracketedProcedure('lash')
				return
			self.distanceFeedRate.addLine(line)

	def parseLash(self, line):
		"Parse a gcode line and add it to the lash skein."
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if firstWord == 'G1':
			location = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
			line = self.getLashedLine( line, location, splitLine )
			self.oldLocation = location
		self.distanceFeedRate.addLine(line)


def main():
	"Display the lash dialog."
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == "__main__":
	main()
