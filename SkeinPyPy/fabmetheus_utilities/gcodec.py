"""
Gcodec is a collection of utilities to decode and encode gcode.

To run gcodec, install python 2.x on your machine, which is avaliable from http://www.python.org/download/

Then in the folder which gcodec is in, type 'python' in a shell to run the python interpreter.  Finally type 'from gcodec import *' to import this program.

Below is an example of gcodec use.  This example is run in a terminal in the folder which contains gcodec and Screw Holder Bottom_export.gcode.

>>> from gcodec import *
>>> getFileText('Screw Holder Bottom_export.gcode')
'G90\nG21\nM103\nM105\nM106\nM110 S60.0\nM111 S30.0\nM108 S210.0\nM104 S235.0\nG1 X0.37 Y-4.07 Z1.9 F60.0\nM101\n
..
many lines of text
..

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
import cStringIO
import math
import os
import sys
import traceback


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def addLineAndNewlineIfNecessary(line, output):
	'Add the line and if the line does not end with a newline add a newline.'
	output.write(line)
	if len(line) < 1:
		return
	if not line.endswith('\n'):
		output.write('\n')

def addLinesToCString(cString, lines):
	'Add lines which have something to cStringIO.'
	for line in lines:
		if line != '':
			cString.write(line + '\n')

def getArcDistance(relativeLocation, splitLine):
	'Get arc distance.'
	halfPlaneLineDistance = 0.5 * abs(relativeLocation.dropAxis())
	radius = getDoubleFromCharacterSplitLine('R', splitLine)
	if radius == None:
		iFloat = getDoubleFromCharacterSplitLine('I', splitLine)
		jFloat = getDoubleFromCharacterSplitLine('J', splitLine)
		radius = abs(complex(iFloat, jFloat))
	angle = 0.0
	if radius > 0.0:
		halfPlaneLineDistanceOverRadius = halfPlaneLineDistance / radius
		if halfPlaneLineDistance < radius:
			angle = 2.0 * math.asin(halfPlaneLineDistanceOverRadius)
		else:
			angle = math.pi * halfPlaneLineDistanceOverRadius
	return abs(complex(angle * radius, relativeLocation.z))

def getDoubleAfterFirstLetter(word):
	'Get the double value of the word after the first letter.'
	return float(word[1 :])

def getDoubleForLetter(letter, splitLine):
	'Get the double value of the word after the first occurence of the letter in the split line.'
	return getDoubleAfterFirstLetter(splitLine[getIndexOfStartingWithSecond(letter, splitLine)])

def getDoubleFromCharacterSplitLine(character, splitLine):
	'Get the double value of the string after the first occurence of the character in the split line.'
	indexOfCharacter = getIndexOfStartingWithSecond(character, splitLine)
	if indexOfCharacter < 0:
		return None
	floatString = splitLine[indexOfCharacter][1 :]
	try:
		return float(floatString)
	except ValueError:
		return None

def getDoubleFromCharacterSplitLineValue(character, splitLine, value):
	'Get the double value of the string after the first occurence of the character in the split line, if it does not exist return the value.'
	splitLineFloat = getDoubleFromCharacterSplitLine(character, splitLine)
	if splitLineFloat == None:
		return value
	return splitLineFloat

def getFeedRateMinute(feedRateMinute, splitLine):
	'Get the feed rate per minute if the split line has a feed rate.'
	indexOfF = getIndexOfStartingWithSecond('F', splitLine)
	if indexOfF > 0:
		return getDoubleAfterFirstLetter( splitLine[indexOfF] )
	return feedRateMinute

def getFirstWord(splitLine):
	'Get the first word of a split line.'
	if len(splitLine) > 0:
		return splitLine[0]
	return ''

def getFirstWordFromLine(line):
	'Get the first word of a line.'
	return getFirstWord(line.split())

def getFirstWordIndexReverse(firstWord, lines, startIndex):
	'Parse gcode in reverse order until the first word if there is one, otherwise return -1.'
	for lineIndex in xrange(len(lines) - 1, startIndex - 1, -1):
		if firstWord == getFirstWord(getSplitLineBeforeBracketSemicolon(lines[lineIndex])):
			return lineIndex
	return -1

def getGcodeFileText(fileName, gcodeText):
	'Get the gcode text from a file if it the gcode text is empty and if the file is a gcode file.'
	if gcodeText != '':
		return gcodeText
	if fileName.endswith('.gcode'):
		return archive.getFileText(fileName)
	return ''

def getGcodeWithoutDuplication(duplicateWord, gcodeText):
	'Get gcode text without duplicate first words.'
	lines = archive.getTextLines(gcodeText)
	oldWrittenLine = None
	output = cStringIO.StringIO()
	for line in lines:
		firstWord = getFirstWordFromLine(line)
		if firstWord == duplicateWord:
			if line != oldWrittenLine:
				output.write(line + '\n')
				oldWrittenLine = line
		else:
			if len(line) > 0:
				output.write(line + '\n')
	return output.getvalue()

def getIndexOfStartingWithSecond(letter, splitLine):
	'Get index of the first occurence of the given letter in the split line, starting with the second word.  Return - 1 if letter is not found'
	for wordIndex in xrange( 1, len(splitLine) ):
		word = splitLine[ wordIndex ]
		firstLetter = word[0]
		if firstLetter == letter:
			return wordIndex
	return - 1

def getLineWithValueString(character, line, splitLine, valueString):
	'Get the line with a valueString.'
	roundedValueString = character + valueString
	indexOfValue = getIndexOfStartingWithSecond(character, splitLine)
	if indexOfValue == -1:
		return line + ' ' + roundedValueString
	word = splitLine[indexOfValue]
	return line.replace(word, roundedValueString)

def getLocationFromSplitLine(oldLocation, splitLine):
	'Get the location from the split line.'
	if oldLocation == None:
		oldLocation = Vector3()
	return Vector3(
		getDoubleFromCharacterSplitLineValue('X', splitLine, oldLocation.x),
		getDoubleFromCharacterSplitLineValue('Y', splitLine, oldLocation.y),
		getDoubleFromCharacterSplitLineValue('Z', splitLine, oldLocation.z))

def getRotationBySplitLine(splitLine):
	'Get the complex rotation from the split gcode line.'
	return complex(splitLine[1].replace('(', '').replace(')', ''))

def getSplitLineBeforeBracketSemicolon(line):
	'Get the split line before a bracket or semicolon.'
	if ';' in line:
		line = line[: line.find(';')]
	bracketIndex = line.find('(')
	if bracketIndex > 0:
		return line[: bracketIndex].split()
	return line.split()

def getStringFromCharacterSplitLine(character, splitLine):
	'Get the string after the first occurence of the character in the split line.'
	indexOfCharacter = getIndexOfStartingWithSecond(character, splitLine)
	if indexOfCharacter < 0:
		return None
	return splitLine[indexOfCharacter][1 :]

def getTagBracketedLine(tagName, value):
	'Get line with a begin tag, value and end tag.'
	return '(<%s> %s </%s>)' % (tagName, value, tagName)

def getTagBracketedProcedure(procedure):
	'Get line with a begin procedure tag, procedure and end procedure tag.'
	return getTagBracketedLine('procedureName', procedure)

def isProcedureDone(gcodeText, procedure):
	'Determine if the procedure has been done on the gcode text.'
	if gcodeText == '':
		return False
	extruderInitializationIndex = gcodeText.find('(</extruderInitialization>)')
	if extruderInitializationIndex == -1:
		metadataBeginIndex = gcodeText.find('<metadata>')
		metadataEndIndex = gcodeText.find('</metadata>')
		if metadataBeginIndex != -1 and metadataEndIndex != -1:
			attributeString = "procedureName='%s'" % procedure
			return gcodeText.find(attributeString, metadataBeginIndex, metadataEndIndex) != -1
		return False
	return gcodeText.find(getTagBracketedProcedure(procedure), 0, extruderInitializationIndex) != -1

def isProcedureDoneOrFileIsEmpty(gcodeText, procedure):
	'Determine if the procedure has been done on the gcode text or the file is empty.'
	if gcodeText == '':
		return True
	return isProcedureDone(gcodeText, procedure)

def isThereAFirstWord(firstWord, lines, startIndex):
	'Parse gcode until the first word if there is one.'
	for lineIndex in xrange(startIndex, len(lines)):
		line = lines[lineIndex]
		splitLine = getSplitLineBeforeBracketSemicolon(line)
		if firstWord == getFirstWord(splitLine):
			return True
	return False


class BoundingRectangle:
	'A class to get the corners of a gcode text.'
	def getFromGcodeLines(self, lines, radius):
		'Parse gcode text and get the minimum and maximum corners.'
		self.cornerMaximum = complex(-987654321.0, -987654321.0)
		self.cornerMinimum = complex(987654321.0, 987654321.0)
		self.oldLocation = None
		self.cornerRadius = complex(radius, radius)
		for line in lines:
			self.parseCorner(line)
		return self

	def isPointInside(self, point):
		'Determine if the point is inside the bounding rectangle.'
		return point.imag >= self.cornerMinimum.imag and point.imag <= self.cornerMaximum.imag and point.real >= self.cornerMinimum.real and point.real <= self.cornerMaximum.real

	def parseCorner(self, line):
		'Parse a gcode line and use the location to update the bounding corners.'
		splitLine = getSplitLineBeforeBracketSemicolon(line)
		firstWord = getFirstWord(splitLine)
		if firstWord == '(<boundaryPoint>':
			locationComplex = getLocationFromSplitLine(None, splitLine).dropAxis()
			self.cornerMaximum = euclidean.getMaximum(self.cornerMaximum, locationComplex)
			self.cornerMinimum = euclidean.getMinimum(self.cornerMinimum, locationComplex)
		elif firstWord == 'G1':
			location = getLocationFromSplitLine(self.oldLocation, splitLine)
			locationComplex = location.dropAxis()
			self.cornerMaximum = euclidean.getMaximum(self.cornerMaximum, locationComplex + self.cornerRadius)
			self.cornerMinimum = euclidean.getMinimum(self.cornerMinimum, locationComplex - self.cornerRadius)
			self.oldLocation = location


class DistanceFeedRate:
	'A class to limit the z feed rate and round values.'
	def __init__(self):
		'Initialize.'
		self.isAlteration = False
		self.decimalPlacesCarried = 3
		self.output = cStringIO.StringIO()

	def addFlowRateLine(self, flowRate):
		'Add a flow rate line.'
		self.output.write('M108 S%s\n' % euclidean.getFourSignificantFigures(flowRate))

	def addGcodeFromFeedRateThreadZ(self, feedRateMinute, thread, travelFeedRateMinute, z):
		'Add a thread to the output.'
		if len(thread) > 0:
			self.addGcodeMovementZWithFeedRate(travelFeedRateMinute, thread[0], z)
		else:
			print('zero length vertex positions array which was skipped over, this should never happen.')
		if len(thread) < 2:
			print('thread of only one point in addGcodeFromFeedRateThreadZ in gcodec, this should never happen.')
			print(thread)
			return
		self.output.write('M101\n') # Turn extruder on.
		for point in thread[1 :]:
			self.addGcodeMovementZWithFeedRate(feedRateMinute, point, z)
		self.output.write('M103\n') # Turn extruder off.

	def addGcodeFromLoop(self, loop, z):
		'Add the gcode loop.'
		euclidean.addNestedRingBeginning(self, loop, z)
		self.addPerimeterBlock(loop, z)
		self.addLine('(</boundaryPerimeter>)')
		self.addLine('(</nestedRing>)')

	def addGcodeFromThreadZ(self, thread, z):
		'Add a thread to the output.'
		if len(thread) > 0:
			self.addGcodeMovementZ(thread[0], z)
		else:
			print('zero length vertex positions array which was skipped over, this should never happen.')
		if len(thread) < 2:
			print('thread of only one point in addGcodeFromThreadZ in gcodec, this should never happen.')
			print(thread)
			return
		self.output.write('M101\n') # Turn extruder on.
		for point in thread[1 :]:
			self.addGcodeMovementZ(point, z)
		self.output.write('M103\n') # Turn extruder off.

	def addGcodeMovementZ(self, point, z):
		'Add a movement to the output.'
		self.output.write(self.getLinearGcodeMovement(point, z) + '\n')

	def addGcodeMovementZWithFeedRate(self, feedRateMinute, point, z):
		'Add a movement to the output.'
		self.output.write(self.getLinearGcodeMovementWithFeedRate(feedRateMinute, point, z) + '\n')

	def addGcodeMovementZWithFeedRateVector3(self, feedRateMinute, vector3):
		'Add a movement to the output by Vector3.'
		xRounded = self.getRounded(vector3.x)
		yRounded = self.getRounded(vector3.y)
		self.output.write('G1 X%s Y%s Z%s F%s\n' % (xRounded, yRounded, self.getRounded(vector3.z), self.getRounded(feedRateMinute)))

	def addLine(self, line):
		'Add a line of text and a newline to the output.'
		if len(line) > 0:
			self.output.write(line + '\n')

	def addLineCheckAlteration(self, line):
		'Add a line of text and a newline to the output and check to see if it is an alteration line.'
		firstWord = getFirstWord(getSplitLineBeforeBracketSemicolon(line))
		if firstWord == '(<alteration>)':
			self.isAlteration = True
		elif firstWord == '(</alteration>)':
			self.isAlteration = False
		if len(line) > 0:
			self.output.write(line + '\n')

	def addLines(self, lines):
		'Add lines of text to the output.'
		addLinesToCString(self.output, lines)

	def addLinesSetAbsoluteDistanceMode(self, lines):
		'Add lines of text to the output and ensure the absolute mode is set.'
		if len(lines) < 1:
			return
		if len(lines[0]) < 1:
			return
		absoluteDistanceMode = True
		self.addLine('(<alteration>)')
		for line in lines:
			splitLine = getSplitLineBeforeBracketSemicolon(line)
			firstWord = getFirstWord(splitLine)
			if firstWord == 'G90':
				absoluteDistanceMode = True
			elif firstWord == 'G91':
				absoluteDistanceMode = False
			self.addLine('(<alterationDeleteThisPrefix/>)' + line)
		if not absoluteDistanceMode:
			self.addLine('G90')
		self.addLine('(</alteration>)')

	def addParameter(self, firstWord, parameter):
		'Add the parameter.'
		self.addLine(firstWord + ' S' + euclidean.getRoundedToThreePlaces(parameter))

	def addPerimeterBlock(self, loop, z):
		'Add the edge gcode block for the loop.'
		if len(loop) < 2:
			return
		if euclidean.isWiddershins(loop): # Indicate that an edge is beginning.
			self.addLine('(<edge> outer )')
		else:
			self.addLine('(<edge> inner )')
		self.addGcodeFromThreadZ(loop + [loop[0]], z)
		self.addLine('(</edge>)') # Indicate that an edge is beginning.

	def addTagBracketedLine(self, tagName, value):
		'Add a begin tag, value and end tag.'
		self.addLine(getTagBracketedLine(tagName, value))

	def addTagRoundedLine(self, tagName, value):
		'Add a begin tag, rounded value and end tag.'
		self.addLine('(<%s> %s </%s>)' % (tagName, self.getRounded(value), tagName))

	def addTagBracketedProcedure(self, procedure):
		'Add a begin procedure tag, procedure and end procedure tag.'
		self.addLine(getTagBracketedProcedure(procedure))

	def getBoundaryLine(self, location):
		'Get boundary gcode line.'
		return '(<boundaryPoint> X%s Y%s Z%s </boundaryPoint>)' % (self.getRounded(location.x), self.getRounded(location.y), self.getRounded(location.z))

	def getFirstWordMovement(self, firstWord, location):
		'Get the start of the arc line.'
		return '%s X%s Y%s Z%s' % (firstWord, self.getRounded(location.x), self.getRounded(location.y), self.getRounded(location.z))

	def getInfillBoundaryLine(self, location):
		'Get infill boundary gcode line.'
		return '(<infillPoint> X%s Y%s Z%s </infillPoint>)' % (self.getRounded(location.x), self.getRounded(location.y), self.getRounded(location.z))

	def getIsAlteration(self, line):
		'Determine if it is an alteration.'
		if self.isAlteration:
			self.addLineCheckAlteration(line)
			return True
		return False

	def getLinearGcodeMovement(self, point, z):
		'Get a linear gcode movement.'
		return 'G1 X%s Y%s Z%s' % (self.getRounded(point.real), self.getRounded(point.imag), self.getRounded(z))

	def getLinearGcodeMovementWithFeedRate(self, feedRateMinute, point, z):
		'Get a z limited gcode movement.'
		linearGcodeMovement = self.getLinearGcodeMovement(point, z)
		if feedRateMinute == None:
			return linearGcodeMovement
		return linearGcodeMovement + ' F' + self.getRounded(feedRateMinute)

	def getLineWithFeedRate(self, feedRateMinute, line, splitLine):
		'Get the line with a feed rate.'
		return getLineWithValueString('F', line, splitLine, self.getRounded(feedRateMinute))

	def getLineWithX(self, line, splitLine, x):
		'Get the line with an x.'
		return getLineWithValueString('X', line, splitLine, self.getRounded(x))

	def getLineWithY(self, line, splitLine, y):
		'Get the line with a y.'
		return getLineWithValueString('Y', line, splitLine, self.getRounded(y))

	def getLineWithZ(self, line, splitLine, z):
		'Get the line with a z.'
		return getLineWithValueString('Z', line, splitLine, self.getRounded(z))

	def getRounded(self, number):
		'Get number rounded to the number of carried decimal places as a string.'
		return euclidean.getRoundedToPlacesString(self.decimalPlacesCarried, number)

	def parseSplitLine(self, firstWord, splitLine):
		'Parse gcode split line and store the parameters.'
		if firstWord == '(<decimalPlacesCarried>':
			self.decimalPlacesCarried = int(splitLine[1])
