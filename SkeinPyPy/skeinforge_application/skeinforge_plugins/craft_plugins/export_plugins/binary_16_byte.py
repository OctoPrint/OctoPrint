"""
This page is in the table of contents.
Binary 16 byte is an export plugin to convert gcode into 16 byte binary segments.

An export plugin is a script in the export_plugins folder which has the getOutput function, the globalIsReplaceable variable and if it's output is not replaceable, the writeOutput function.  It is meant to be run from the export tool.  To ensure that the plugin works on platforms which do not handle file capitalization properly, give the plugin a lower case name.

The getOutput function of this script takes a gcode text and returns that text converted into 16 byte segments.  The writeOutput function of this script takes a gcode text and writes that in a binary format converted into 16 byte segments.

This plugin is just a starter to make a real binary converter.

==Settings==
===Feed Rate Step Length===
Default is 0.1 millimeters/second.

Defines the feed rate step length.

===File Extension===
Default is bin.

Defines the file extension suffix.

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

===Step Length===
====X Step Length====
Default is 0.1 millimeters.

Defines the X axis step length.

====Y Step Length====
Default is 0.1 millimeters.

Defines the Y axis step length.

====Z Step Length====
Default is 0.01 millimeters.

Defines the Z axis step length.

==Record structure==
BinArray(0) = AscW(Inst_Code_Letter)
BinArray(1) = cInst_Code

X Data
sInt32_to_Hbytes(iXdim_1)
BinArray(2) = lsb 'short lsb
BinArray(3) = msb 'short msb

Y Data
sInt32_to_Hbytes(iYdim_2)
BinArray(4) = lsb 'short lsb
BinArray(5) = msb 'short msb

Z Data
sInt32_to_Hbytes(iZdim_3)
BinArray(6) = lsb 'short lsb
BinArray(7) = msb 'short msb

I Data
sInt32_to_Hbytes(iIdim_4)
BinArray(8) = lsb 'short lsb
BinArray(9) = msb 'short msb

J Data
sInt32_to_Hbytes(iJdim_5)
BinArray(10) = lsb 'short lsb
BinArray(11) = msb 'short msb

BinArray(12) = FP_Char
sInt32_to_Hbytes(iFP_Num)
BinArray(13) = lsb 'short lsb

BinArray(14) = bActiveFlags

BinArray(15) = AscW("#")End of record filler

Byte 14 is worth a few extra notes, this byte is used to define which of the axes are active, its used to get round the problem of say a line of code with no mention of z. This would be put into the file as z = 0 as the space for this data is reserved, if we did nothing, this would instruct the machine to go to z = 0. If we use the active flag to define the z axis as inactive the z = 0 is ignored and the value set to the last saved value of z, i.e it does not move.  If the z data is actually set to z = 0 then the axis would be set to active and the move takes place.

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
globalIsReplaceable = False


def getIntegerFlagFromCharacterSplitLine(character, splitLine):
	"Get the integer flag after the first occurence of the character in the split line."
	lineFromCharacter = gcodec.getStringFromCharacterSplitLine(character, splitLine)
	if lineFromCharacter == None:
		return 0
	return 1

def getIntegerFromCharacterLengthLineOffset( character, offset, splitLine, stepLength ):
	"Get the integer after the first occurence of the character in the split line."
	lineFromCharacter = gcodec.getStringFromCharacterSplitLine(character, splitLine)
	if lineFromCharacter == None:
		return 0
	floatValue = ( float( lineFromCharacter ) + offset ) / stepLength
	return int( round( floatValue ) )

def getNewRepository():
	'Get new repository.'
	return Binary16ByteRepository()

def getOutput( gcodeText, binary16ByteRepository = None ):
	'Get the exported version of a gcode file.'
	if gcodeText == '':
		return ''
	if binary16ByteRepository == None:
		binary16ByteRepository = Binary16ByteRepository()
		settings.getReadRepository( binary16ByteRepository )
	return Binary16ByteSkein().getCraftedGcode( gcodeText, binary16ByteRepository )

def writeOutput( fileName, gcodeText = ''):
	"Write the exported version of a gcode file."
	binary16ByteRepository = Binary16ByteRepository()
	settings.getReadRepository( binary16ByteRepository )
	gcodeText = gcodec.getGcodeFileText(fileName, gcodeText)
	skeinOutput = getOutput( gcodeText, binary16ByteRepository )
	suffixFileName = fileName[ : fileName.rfind('.') ] + '.' + binary16ByteRepository.fileExtension.value
	archive.writeFileText( suffixFileName, skeinOutput )
	print('The converted file is saved as ' + archive.getSummarizedFileName(suffixFileName) )


class Binary16ByteRepository:
	"A class to handle the export settings."
	def __init__(self):
		"Set the default settings, execute title & settings fileName."
		#Set the default settings.
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.export_plugins.binary_16_byte.html', self)
		self.fileNameInput = settings.FileNameInput().getFromFileName( [ ('Gcode text files', '*.gcode') ], 'Open File to be Converted to Binary 16 Byte', self, '')
		self.feedRateStepLength = settings.FloatSpin().getFromValue( 0.0, 'Feed Rate Step Length (millimeters/second)', self, 1.0, 0.1 )
		self.fileExtension = settings.StringSetting().getFromValue('File Extension:', self, 'bin')
		settings.LabelDisplay().getFromName('Offset:', self )
		self.xOffset = settings.FloatSpin().getFromValue( - 100.0, 'X Offset (millimeters)', self, 100.0, 0.0 )
		self.yOffset = settings.FloatSpin().getFromValue( -100.0, 'Y Offset (millimeters)', self, 100.0, 0.0 )
		self.zOffset = settings.FloatSpin().getFromValue( - 10.0, 'Z Offset (millimeters)', self, 10.0, 0.0 )
		settings.LabelDisplay().getFromName('Step Length:', self )
		self.xStepLength = settings.FloatSpin().getFromValue( 0.0, 'X Step Length (millimeters)', self, 1.0, 0.1 )
		self.yStepLength = settings.FloatSpin().getFromValue( 0.0, 'Y Step Length (millimeters)', self, 1.0, 0.1 )
		self.zStepLength = settings.FloatSpin().getFromValue( 0.0, 'Z Step Length (millimeters)', self, 0.2, 0.01 )
		self.executeTitle = 'Convert to Binary 16 Byte'

	def execute(self):
		"Convert to binary 16 byte button has been clicked."
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode( self.fileNameInput.value, ['.gcode'], self.fileNameInput.wasCancelled )
		for fileName in fileNames:
			writeOutput(fileName)


class Binary16ByteSkein:
	"A class to convert gcode into 16 byte binary segments."
	def __init__(self):
		self.output = cStringIO.StringIO()

	def getCraftedGcode( self, gcodeText, binary16ByteRepository ):
		"Parse gcode text and store the gcode."
		self.binary16ByteRepository = binary16ByteRepository
		lines = archive.getTextLines(gcodeText)
		for line in lines:
			self.parseLine(line)
		return self.output.getvalue()

	def parseLine(self, line):
		"Parse a gcode line."
		binary16ByteRepository = self.binary16ByteRepository
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		firstWord = gcodec.getFirstWord(splitLine)
		if len(firstWord) < 1:
			return
		firstLetter = firstWord[0]
		if firstLetter == '(':
			return
		feedRateInteger = getIntegerFromCharacterLengthLineOffset('F', 0.0, splitLine, binary16ByteRepository.feedRateStepLength.value )
		iInteger = getIntegerFromCharacterLengthLineOffset('I', 0.0, splitLine, binary16ByteRepository.xStepLength.value )
		jInteger = getIntegerFromCharacterLengthLineOffset('J', 0.0, splitLine, binary16ByteRepository.yStepLength.value )
		xInteger = getIntegerFromCharacterLengthLineOffset('X', binary16ByteRepository.xOffset.value, splitLine, binary16ByteRepository.xStepLength.value )
		yInteger = getIntegerFromCharacterLengthLineOffset('Y', binary16ByteRepository.yOffset.value, splitLine, binary16ByteRepository.yStepLength.value )
		zInteger = getIntegerFromCharacterLengthLineOffset('Z', binary16ByteRepository.zOffset.value, splitLine, binary16ByteRepository.zStepLength.value )
		sixteenByteStruct = Struct('cBhhhhhhBc')
		flagInteger = getIntegerFlagFromCharacterSplitLine('X', splitLine )
		flagInteger += 2 * getIntegerFlagFromCharacterSplitLine('Y', splitLine )
		flagInteger += 4 * getIntegerFlagFromCharacterSplitLine('Z', splitLine )
		flagInteger += 8 * getIntegerFlagFromCharacterSplitLine('I', splitLine )
		flagInteger += 16 * getIntegerFlagFromCharacterSplitLine('J', splitLine )
		flagInteger += 32 * getIntegerFlagFromCharacterSplitLine('F', splitLine )
		packedString = sixteenByteStruct.pack( firstLetter, int( firstWord[1 :] ), xInteger, yInteger, zInteger, iInteger, jInteger, feedRateInteger, flagInteger, '#')
		self.output.write( packedString )


def main():
	"Display the export dialog."
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == "__main__":
	main()
