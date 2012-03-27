"""
This page is in the table of contents.
Gcode time segment is an export plugin to convert gcode from float position to number of steps.

An export plugin is a script in the export_plugins folder which has the getOutput function, the globalIsReplaceable variable and if it's output is not replaceable, the writeOutput function.  It is meant to be run from the export tool.  To ensure that the plugin works on platforms which do not handle file capitalization properly, give the plugin a lower case name.

The getOutput function of this script takes a gcode text and returns it with the positions converted into number of steps and time.  The writeOutput function of this script takes a gcode text and writes that with the positions converted into number of steps and time.

==Settings==
===Add Space Between Words===
Default is on.

When selected, a space will be added between each gcode word.

===Offset===
====X Offset====
Default is zero.

Defines the X Offset.

====Y Offset====
Default is zero.

Defines the Y Offset.

====Z Offset====
Default is zero.

Defines the Z Offset.

===Step===
===Extrusion Step===
Default is 0.01 mm.

Defines the radius step length.

===Time Step===
Default is 1 microsecond(mcs).

Defines the time step duration.

====X Step====
Default is 0.1 mm.

Defines the X axis step length.

====Y Step====
Default is 0.1 mm.

Defines the Y axis step length.

====Z Step====
Default is 0.01 mm.

Defines the Z axis step length.

"""


from __future__ import absolute_import
import __init__
from fabmetheus_utilities import archive
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import settings
from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
from skeinforge_application.skeinforge_utilities import skeinforge_polyfile
from skeinforge_application.skeinforge_utilities import skeinforge_profile
from struct import Struct
import cStringIO
import os
import sys


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


# This is true if the output is text and false if it is binary."
globalIsReplaceable = True


def getCharacterIntegerString( character, offset, splitLine, step ):
	"Get a character and integer string."
	floatValue = getFloatFromCharacterSplitLine(character, splitLine)
	if floatValue == None:
		return None
	floatValue += offset
	integerValue = int(round(float(floatValue / step)))
	return character + str( integerValue )

def getFloatFromCharacterSplitLine(character, splitLine):
	"Get the float after the first occurence of the character in the split line."
	lineFromCharacter = gcodec.getStringFromCharacterSplitLine(character, splitLine)
	if lineFromCharacter == None:
		return None
	return float(lineFromCharacter)

def getNewRepository():
	'Get new repository.'
	return GcodeTimeSegmentRepository()

def getOutput(gcodeText, repository=None):
	'Get the exported version of a gcode file.'
	if gcodeText == '':
		return ''
	if repository == None:
		repository = GcodeTimeSegmentRepository()
		settings.getReadRepository(repository)
	return GcodeTimeSegmentSkein().getCraftedGcode(gcodeText, repository)

def writeOutput( fileName, gcodeText = ''):
	"Write the exported version of a gcode file."
	gcodeText = gcodec.getGcodeFileText(fileName, gcodeText)
	repository = GcodeTimeSegmentRepository()
	settings.getReadRepository(repository)
	output = getOutput(gcodeText, repository)
	suffixFileName = fileName[ : fileName.rfind('.') ] + '_gcode_time_segment.gcode'
	archive.writeFileText( suffixFileName, output )
	print('The converted file is saved as ' + archive.getSummarizedFileName(suffixFileName) )


class GcodeTimeSegmentRepository:
	"A class to handle the export settings."
	def __init__(self):
		"Set the default settings, execute title & settings fileName."
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.export_plugins.gcode_time.html', self)
		self.addSpaceBetweenWords = settings.BooleanSetting().getFromValue('Add Space Between Words', self, True )
		self.fileNameInput = settings.FileNameInput().getFromFileName( [ ('Gcode text files', '*.gcode') ], 'Open File to be Converted to Gcode Time', self, '')
		self.initialTime = settings.FloatSpin().getFromValue(0.0, 'Initial Time (s)', self, 20.0, 10.0)
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Offset -', self )
		self.xOffset = settings.FloatSpin().getFromValue( - 100.0, 'X Offset (mm)', self, 100.0, 0.0 )
		self.yOffset = settings.FloatSpin().getFromValue( -100.0, 'Y Offset (mm)', self, 100.0, 0.0 )
		self.zOffset = settings.FloatSpin().getFromValue( - 10.0, 'Z Offset (mm)', self, 10.0, 0.0 )
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Step -', self )
		self.extrusionStep = settings.FloatSpin().getFromValue(0.0, 'Extrusion Step (mm)', self, 0.2, 0.01)
		self.timeStep = settings.FloatSpin().getFromValue(0.0, 'Time Step (mcs)', self, 2000.0, 1000.0)
		self.xStep = settings.FloatSpin().getFromValue(0.0, 'X Step (mm)', self, 1.0, 0.1)
		self.yStep = settings.FloatSpin().getFromValue(0.0, 'Y Step (mm)', self, 1.0, 0.1)
		self.zStep = settings.FloatSpin().getFromValue(0.0, 'Z Step (mm)', self, 0.2, 0.01)
		settings.LabelSeparator().getFromRepository(self)
		self.executeTitle = 'Convert to Gcode Time'

	def execute(self):
		"Convert to gcode step button has been clicked."
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode( self.fileNameInput.value, ['.gcode'], self.fileNameInput.wasCancelled )
		for fileName in fileNames:
			writeOutput(fileName)


class GcodeTimeSegmentSkein:
	"A class to convert gcode into time segments."
	def __init__(self):
		'Initialize.'
		self.feedRateMinute = None
		self.isExtruderActive = False
		self.oldFeedRateString = None
		self.oldLocation = None
		self.oldZString = None
		self.operatingFlowRate = None
		self.output = cStringIO.StringIO()

	def addCharacterInteger(self, character, lineStringIO, offset, splitLine, step):
		"Add a character and integer to line string."
		characterIntegerString = getCharacterIntegerString(character, offset, splitLine, step)
		self.addStringToLine(lineStringIO, characterIntegerString)

	def addLine(self, line):
		"Add a line of text and a newline to the output."
		self.output.write(line + '\n')

	def addStringToLine( self, lineStringIO, wordString ):
		"Add a character and integer to line string."
		if wordString == None:
			return
		if self.repository.addSpaceBetweenWords.value:
			lineStringIO.write(' ')
		lineStringIO.write( wordString )

	def getCraftedGcode(self, gcodeText, repository):
		"Parse gcode text and store the gcode."
		self.repository = repository
		lines = archive.getTextLines(gcodeText)
		for line in lines:
			self.parseLine(line)
		return self.output.getvalue()

	def parseLine(self, line):
		"Parse a gcode line."
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		firstWord = gcodec.getFirstWord(splitLine)
		if len(firstWord) < 1:
			return
		firstLetter = firstWord[0]
		if firstWord == '(<operatingFeedRatePerSecond>':
			self.feedRateMinute = 60.0 * float(splitLine[1])
		elif firstWord == '(<operatingFlowRate>':
			self.operatingFlowRate = float(splitLine[1])
			self.flowRate = self.operatingFlowRate
		if firstLetter == '(':
			return
		if firstWord == 'M101':
			self.isExtruderActive = True
		elif firstWord == 'M103':
			self.isExtruderActive = False
		elif firstWord == 'M108':
			self.flowRate = float(splitLine[1][1 :])
		if firstWord != 'G1' and firstWord != 'G2' and firstWord != 'G3':
			self.addLine(line)
			return
		self.feedRateMinute = gcodec.getFeedRateMinute(self.feedRateMinute, splitLine)
		lineStringIO = cStringIO.StringIO()
		lineStringIO.write(firstWord)
		location = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
		self.addCharacterInteger('X', lineStringIO, self.repository.xOffset.value, splitLine, self.repository.xStep.value )
		self.addCharacterInteger('Y', lineStringIO, self.repository.yOffset.value, splitLine, self.repository.yStep.value )
		zString = getCharacterIntegerString('Z', self.repository.zOffset.value, splitLine, self.repository.zStep.value )
		if zString == None:
			zString = self.oldZString
		self.addStringToLine(lineStringIO, zString)
		duration = self.repository.initialTime.value
		if self.oldLocation != None:
			distance = abs(location - self.oldLocation)
			duration = 60.0 / self.feedRateMinute * distance
		extrusionDistance = 0.0
		if self.isExtruderActive:
			extrusionDistance = self.flowRate * duration
		self.addStringToLine(lineStringIO, 'E%s' % int(round(extrusionDistance / self.repository.extrusionStep.value)))
		self.addStringToLine(lineStringIO, 'D%s' % int(round(duration * 1000000.0 / self.repository.timeStep.value)))
		self.addLine(lineStringIO.getvalue())
		self.oldLocation = location
		self.oldZString = zString


def main():
	"Display the export dialog."
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == "__main__":
	main()
