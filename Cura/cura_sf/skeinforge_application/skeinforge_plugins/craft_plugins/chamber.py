"""
This page is in the table of contents.
Some filaments contract too much and warp the extruded object.  To prevent this you have to print the object in a temperature regulated chamber and/or on a temperature regulated bed. The chamber tool allows you to control the bed and chamber temperature and the holding pressure.

The chamber gcodes are also described at:

http://reprap.org/wiki/Mendel_User_Manual:_RepRapGCodes

The chamber manual page is at:

http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Chamber

==Operation==
The default 'Activate Chamber' checkbox is on.  When it is on, the functions described below will work, when it is off, nothing will be done.

==Settings==
===Bed===
The initial bed temperature is defined by 'Bed Temperature'.  If the 'Bed Temperature End Change Height' is greater or equal to the 'Bed Temperature Begin Change Height' and the 'Bed Temperature Begin Change Height' is greater or equal to zero, then the temperature will be ramped toward the 'Bed Temperature End'.  The ramp will start once the extruder reaches the 'Bed Temperature Begin Change Height', then the bed temperature will approach the 'Bed Temperature End' as the extruder reaches the 'Bed Temperature End Change Height', finally the bed temperature will stay at the 'Bed Temperature End' for the remainder of the build.

The idea is described at:
http://www.makerbot.com/blog/2011/03/17/if-you-cant-stand-the-heat/

====Bed Temperature====
Default: 60C

Defines the initial print bed temperature in Celcius by adding an M140 command.

====Bed Temperature Begin Change Height====
Default: -1 mm

Defines the height of the beginning of the temperature ramp.  If the 'Bed Temperature End Change Height' is less than zero, the bed temperature will remain at the initial 'Bed Temperature'.

====Bed Temperature End Change Height====
Default: -1 mm

Defines the height of the end of the temperature ramp.  If the 'Bed Temperature End Change Height' is less than zero or less than the 'Bed Temperature Begin Change Height', the bed temperature will remain at the initial 'Bed Temperature'.

====Bed Temperature End====
Default: 20C

Defines the end bed temperature if there is a temperature ramp.

===Chamber Temperature===
Default: 30C

Defines the chamber temperature in Celcius by adding an M141 command.

===Holding Force===
Default: 0

Defines the holding pressure of a mechanism, like a vacuum table or electromagnet, to hold the bed surface or object, by adding an M142 command.  The holding pressure is in bars. For hardware which only has on/off holding, when the holding pressure is zero, turn off holding, when the holding pressure is greater than zero, turn on holding. 

==Heated Beds==
===Bothacker===
A resistor heated aluminum plate by Bothacker:

http://bothacker.com

with an article at:

http://bothacker.com/2009/12/18/heated-build-platform/

===Domingo===
A heated copper build plate by Domingo:

http://casainho-emcrepstrap.blogspot.com/

with articles at:

http://casainho-emcrepstrap.blogspot.com/2010/01/first-time-with-pla-testing-it-also-on.html

http://casainho-emcrepstrap.blogspot.com/2010/01/call-for-helpideas-to-develop-heated.html

http://casainho-emcrepstrap.blogspot.com/2010/01/new-heated-build-platform.html

http://casainho-emcrepstrap.blogspot.com/2010/01/no-acrylic-and-instead-kapton-tape-on.html

http://casainho-emcrepstrap.blogspot.com/2010/01/problems-with-heated-build-platform-and.html

http://casainho-emcrepstrap.blogspot.com/2010/01/perfect-build-platform.html

http://casainho-emcrepstrap.blogspot.com/2009/12/almost-no-warp.html

http://casainho-emcrepstrap.blogspot.com/2009/12/heated-base-plate.html

===Jmil===
A heated build stage by jmil, over at:

http://www.hive76.org

with articles at:

http://www.hive76.org/handling-hot-build-surfaces

http://www.hive76.org/heated-build-stage-success

===Metalab===
A heated base by the Metalab folks:

http://reprap.soup.io

with information at:

http://reprap.soup.io/?search=heated%20base

===Nophead===
A resistor heated aluminum bed by Nophead:

http://hydraraptor.blogspot.com

with articles at:

http://hydraraptor.blogspot.com/2010/01/will-it-stick.html

http://hydraraptor.blogspot.com/2010/01/hot-metal-and-serendipity.html

http://hydraraptor.blogspot.com/2010/01/new-year-new-plastic.html

http://hydraraptor.blogspot.com/2010/01/hot-bed.html

===Prusajr===
A resistive wire heated plexiglass plate by prusajr:

http://prusadjs.cz/

with articles at:

http://prusadjs.cz/2010/01/heated-reprap-print-bed-mk2/

http://prusadjs.cz/2009/11/look-ma-no-warping-heated-reprap-print-bed/

===Zaggo===
A resistor heated aluminum plate by Zaggo at Pleasant Software:

http://pleasantsoftware.com/developer/3d/

with articles at:

http://pleasantsoftware.com/developer/3d/2009/12/05/raftless/

http://pleasantsoftware.com/developer/3d/2009/11/15/living-in-times-of-warp-free-printing/

http://pleasantsoftware.com/developer/3d/2009/11/12/canned-heat/

==Examples==
The following examples chamber the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and chamber.py.

> python chamber.py
This brings up the chamber dialog.

> python chamber.py Screw Holder Bottom.stl
The chamber tool is parsing the file:
Screw Holder Bottom.stl
..
The chamber tool has created the file:
Screw Holder Bottom_chamber.gcode

"""


from __future__ import absolute_import

from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_utilities import skeinforge_craft
from skeinforge_application.skeinforge_utilities import skeinforge_polyfile
from skeinforge_application.skeinforge_utilities import skeinforge_profile
import sys

__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCraftedText(fileName, text='', repository=None):
	"Chamber the file or text."
	return getCraftedTextFromText(archive.getTextIfEmpty(fileName, text), repository)

def getCraftedTextFromText(gcodeText, repository=None):
	"Chamber a gcode linear move text."
	if gcodec.isProcedureDoneOrFileIsEmpty( gcodeText, 'chamber'):
		return gcodeText
	if repository == None:
		repository = settings.getReadRepository(ChamberRepository())
	if not repository.activateChamber.value:
		return gcodeText
	return ChamberSkein().getCraftedGcode(gcodeText, repository)

def getNewRepository():
	'Get new repository.'
	return ChamberRepository()

def writeOutput(fileName, shouldAnalyze=True):
	"Chamber a gcode linear move file."
	skeinforge_craft.writeChainTextWithNounMessage(fileName, 'chamber', shouldAnalyze)


class ChamberRepository:
	"A class to handle the chamber settings."
	def __init__(self):
		"Set the default settings, execute title & settings fileName."
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.chamber.html', self )
		self.fileNameInput = settings.FileNameInput().getFromFileName( fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Chamber', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Chamber')
		self.activateChamber = settings.BooleanSetting().getFromValue('Activate Chamber', self, False )
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Bed -', self )
		self.bedTemperature = settings.FloatSpin().getFromValue(20.0, 'Bed Temperature (Celcius):', self, 90.0, 60.0)
		self.bedTemperatureBeginChangeHeight = settings.FloatSpin().getFromValue(-1.0, 'Bed Temperature Begin Change Height (mm):', self, 20.0, -1.0)
		self.bedTemperatureEndChangeHeight = settings.FloatSpin().getFromValue(-1.0, 'Bed Temperature End Change Height (mm):', self, 40.0, -1.0)
		self.bedTemperatureEnd = settings.FloatSpin().getFromValue(20.0, 'Bed Temperature End (Celcius):', self, 90.0, 20.0)
		settings.LabelSeparator().getFromRepository(self)
		self.chamberTemperature = settings.FloatSpin().getFromValue( 20.0, 'Chamber Temperature (Celcius):', self, 90.0, 30.0 )
		self.holdingForce = settings.FloatSpin().getFromValue( 0.0, 'Holding Force (bar):', self, 100.0, 0.0 )
		self.executeTitle = 'Chamber'

	def execute(self):
		"Chamber button has been clicked."
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)



class ChamberSkein:
	"A class to chamber a skein of extrusions."
	def __init__(self):
		'Initialize.'
		self.changeWidth = None
		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.lineIndex = 0
		self.lines = None
		self.oldBedTemperature = None

	def addBedTemperature(self, bedTemperature):
		'Add bed temperature if it is different from the old.'
		if bedTemperature != self.oldBedTemperature:
			self.distanceFeedRate.addParameter('M140', bedTemperature)
			self.oldBedTemperature = bedTemperature

	def getCraftedGcode(self, gcodeText, repository):
		"Parse gcode text and store the chamber gcode."
		endAtLeastBegin = repository.bedTemperatureEndChangeHeight.value >= repository.bedTemperatureBeginChangeHeight.value
		if endAtLeastBegin and repository.bedTemperatureBeginChangeHeight.value >= 0.0:
			self.changeWidth = repository.bedTemperatureEndChangeHeight.value - repository.bedTemperatureBeginChangeHeight.value
		self.repository = repository
		self.lines = archive.getTextLines(gcodeText)
		self.parseInitialization()
		for line in self.lines[self.lineIndex :]:
			self.parseLine(line)
		return self.distanceFeedRate.output.getvalue()

	def parseInitialization(self):
		'Parse gcode initialization and store the parameters.'
		for self.lineIndex in xrange(len(self.lines)):
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			self.distanceFeedRate.parseSplitLine(firstWord, splitLine)
			if firstWord == '(</extruderInitialization>)':
				self.distanceFeedRate.addTagBracketedProcedure('chamber')
				return
			self.distanceFeedRate.addLine(line)

	def parseLine(self, line):
		"Parse a gcode line and add it to the chamber skein."
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if firstWord == '(<crafting>)':
			self.distanceFeedRate.addLine(line)
			self.addBedTemperature(self.repository.bedTemperature.value)
			self.distanceFeedRate.addParameter('M141', self.repository.chamberTemperature.value) # Set chamber temperature.
			self.distanceFeedRate.addParameter('M142', self.repository.holdingForce.value) # Set holding pressure.
			return
		self.distanceFeedRate.addLine(line)
		if firstWord == '(<layer>' and self.changeWidth != None:
			z = float(splitLine[1])
			if z >= self.repository.bedTemperatureEndChangeHeight.value:
				self.addBedTemperature(self.repository.bedTemperatureEnd.value)
				return
			if z <= self.repository.bedTemperatureBeginChangeHeight.value:
				return
			along = (z - self.repository.bedTemperatureBeginChangeHeight.value) / self.changeWidth
			self.addBedTemperature(self.repository.bedTemperature.value * (1 - along) + self.repository.bedTemperatureEnd.value * along)


def main():
	"Display the chamber dialog."
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == "__main__":
	main()
