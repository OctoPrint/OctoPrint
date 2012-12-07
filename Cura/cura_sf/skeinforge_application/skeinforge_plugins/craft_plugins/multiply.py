"""
This page is in the table of contents.
The multiply plugin will take a single object and create an array of objects.  It is used when you want to print single object multiple times in a single pass.

You can also position any object using this plugin by setting the center X and center Y to the desired coordinates (0,0 for the center of the print_bed) and setting the number of rows and columns to 1 (effectively setting a 1x1 matrix - printing only a single object).

The multiply manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Multiply

Besides using the multiply tool, another way of printing many copies of the model is to duplicate the model in Art of Illusion, however many times you want, with the appropriate offsets.  Then you can either use the Join Objects script in the scripts submenu to create a combined shape or you can export the whole scene as an xml file, which skeinforge can then slice.

==Operation==
The default 'Activate Multiply' checkbox is on.  When it is on, the functions described below will work, when it is off, nothing will be done.

==Settings==
===Center===
Default is the origin.

The center of the shape will be moved to the "Center X" and "Center Y" coordinates.

====Center X====
====Center Y====

===Number of Cells===
====Number of Columns====
Default is one.

Defines the number of columns in the array table.

====Number of Rows====
Default is one.

Defines the number of rows in the table.

===Reverse Sequence every Odd Layer===
Default is off.

When selected the build sequence will be reversed on every odd layer so that the tool will travel less.  The problem is that the builds would be made with different amount of time to cool, so some would be too hot and some too cold, which is why the default is off.

===Separation over Perimeter Width===
Default is fifteen.

Defines the ratio of separation between the shape copies over the edge width.

==Examples==
The following examples multiply the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and multiply.py.

> python multiply.py
This brings up the multiply dialog.

> python multiply.py Screw Holder Bottom.stl
The multiply tool is parsing the file:
Screw Holder Bottom.stl
..
The multiply tool has created the file:
.. Screw Holder Bottom_multiply.gcode

"""


from __future__ import absolute_import

from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
from fabmetheus_utilities.vector3 import Vector3
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
	'Multiply the fill file or text.'
	return getCraftedTextFromText(archive.getTextIfEmpty(fileName, text), repository)

def getCraftedTextFromText(gcodeText, repository=None):
	'Multiply the fill text.'
	if gcodec.isProcedureDoneOrFileIsEmpty(gcodeText, 'multiply'):
		return gcodeText
	if repository == None:
		repository = settings.getReadRepository(MultiplyRepository())
	if not repository.activateMultiply.value:
		return gcodeText
	return MultiplySkein().getCraftedGcode(gcodeText, repository)

def getNewRepository():
	'Get new repository.'
	return MultiplyRepository()

def writeOutput(fileName, shouldAnalyze=True):
	'Multiply a gcode linear move file.'
	skeinforge_craft.writeChainTextWithNounMessage(fileName, 'multiply', shouldAnalyze)


class MultiplyRepository:
	'A class to handle the multiply settings.'
	def __init__(self):
		'Set the default settings, execute title & settings fileName.'
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.multiply.html', self )
		self.fileNameInput = settings.FileNameInput().getFromFileName(
			fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Multiply', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Multiply')
		self.activateMultiply = settings.BooleanSetting().getFromValue('Activate Multiply', self, True)
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Center -', self )
		self.centerX = settings.FloatSpin().getFromValue(-100.0, 'Center X (mm):', self, 100.0, 105.0)
		self.centerY = settings.FloatSpin().getFromValue(-100.0, 'Center Y (mm):', self, 100.0, 105.0)
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Number of Cells -', self)
		self.numberOfColumns = settings.IntSpin().getFromValue(1, 'Number of Columns (integer):', self, 10, 1)
		self.numberOfRows = settings.IntSpin().getFromValue(1, 'Number of Rows (integer):', self, 10, 1)
		settings.LabelSeparator().getFromRepository(self)
		self.reverseSequenceEveryOddLayer = settings.BooleanSetting().getFromValue('Reverse Sequence every Odd Layer', self, False)
		self.separationOverEdgeWidth = settings.FloatSpin().getFromValue(5.0, 'Separation over Perimeter Width (ratio):', self, 25.0, 15.0)
		self.executeTitle = 'Multiply'

	def execute(self):
		'Multiply button has been clicked.'
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(
			self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class MultiplySkein:
	'A class to multiply a skein of extrusions.'
	def __init__(self):
		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.isExtrusionActive = False
		self.layerIndex = 0
		self.layerLines = []
		self.lineIndex = 0
		self.lines = None
		self.oldLocation = None
		self.rowIndex = 0
		self.shouldAccumulate = True

	def addElement(self, offset):
		'Add moved element to the output.'
		for line in self.layerLines:
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			if firstWord == '(<boundaryPoint>':
				movedLocation = self.getMovedLocationSetOldLocation(offset, splitLine)
				line = self.distanceFeedRate.getBoundaryLine(movedLocation)
			elif firstWord == 'G1':
				movedLocation = self.getMovedLocationSetOldLocation(offset, splitLine)
				line = self.distanceFeedRate.getLinearGcodeMovement(movedLocation.dropAxis(), movedLocation.z)
			elif firstWord == '(<infillPoint>':
				movedLocation = self.getMovedLocationSetOldLocation(offset, splitLine)
				line = self.distanceFeedRate.getInfillBoundaryLine(movedLocation)
			self.distanceFeedRate.addLine(line)

	def addLayer(self):
		'Add multiplied layer to the output.'
		self.addRemoveThroughLayer()
		offset = self.centerOffset - self.arrayCenter - self.shapeCenter
		for rowIndex in xrange(self.repository.numberOfRows.value):
			yRowOffset = float(rowIndex) * self.extentPlusSeparation.imag
			if self.layerIndex % 2 == 1 and self.repository.reverseSequenceEveryOddLayer.value:
				yRowOffset = self.arrayExtent.imag - yRowOffset
			for columnIndex in xrange(self.repository.numberOfColumns.value):
				xColumnOffset = float(columnIndex) * self.extentPlusSeparation.real
				if self.rowIndex % 2 == 1:
					xColumnOffset = self.arrayExtent.real - xColumnOffset
				elementOffset = complex(offset.real + xColumnOffset, offset.imag + yRowOffset)
				self.addElement(elementOffset)
			self.rowIndex += 1
		settings.printProgress(self.layerIndex, 'multiply')
		if len(self.layerLines) > 1:
			self.layerIndex += 1
		self.layerLines = []

	def addRemoveThroughLayer(self):
		'Parse gcode initialization and store the parameters.'
		for layerLineIndex in xrange(len(self.layerLines)):
			line = self.layerLines[layerLineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			self.distanceFeedRate.addLine(line)
			if firstWord == '(<layer>':
				self.layerLines = self.layerLines[layerLineIndex + 1 :]
				return

	def getCraftedGcode(self, gcodeText, repository):
		'Parse gcode text and store the multiply gcode.'
		self.centerOffset = complex(repository.centerX.value, repository.centerY.value)
		self.repository = repository
		self.numberOfColumns = repository.numberOfColumns.value
		self.numberOfRows = repository.numberOfRows.value
		self.lines = archive.getTextLines(gcodeText)
		self.parseInitialization()
		self.setCorners()
		for line in self.lines[self.lineIndex :]:
			self.parseLine(line)
		return self.distanceFeedRate.output.getvalue()

	def getMovedLocationSetOldLocation(self, offset, splitLine):
		'Get the moved location and set the old location.'
		location = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
		self.oldLocation = location
		return Vector3(location.x + offset.real, location.y + offset.imag, location.z)

	def parseInitialization(self):
		'Parse gcode initialization and store the parameters.'
		for self.lineIndex in xrange(len(self.lines)):
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			self.distanceFeedRate.parseSplitLine(firstWord, splitLine)
			if firstWord == '(</extruderInitialization>)':
				self.distanceFeedRate.addTagBracketedProcedure('multiply')
				self.distanceFeedRate.addLine(line)
				self.lineIndex += 1
				return
			elif firstWord == '(<edgeWidth>':
				self.absoluteEdgeWidth = abs(float(splitLine[1]))
			self.distanceFeedRate.addLine(line)

	def parseLine(self, line):
		'Parse a gcode line and add it to the multiply skein.'
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if firstWord == '(</layer>)':
			self.addLayer()
			self.distanceFeedRate.addLine(line)
			return
		elif firstWord == '(</crafting>)':
			self.shouldAccumulate = False
		if self.shouldAccumulate:
			self.layerLines.append(line)
			return
		self.distanceFeedRate.addLine(line)

	def setCorners(self):
		'Set maximum and minimum corners and z.'
		cornerMaximumComplex = complex(-987654321.0, -987654321.0)
		cornerMinimumComplex = -cornerMaximumComplex
		for line in self.lines[self.lineIndex :]:
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			if firstWord == 'G1':
				location = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
				if self.isExtrusionActive:
					locationComplex = location.dropAxis()
					cornerMaximumComplex = euclidean.getMaximum(locationComplex,  cornerMaximumComplex)
					cornerMinimumComplex = euclidean.getMinimum(locationComplex,  cornerMinimumComplex)
				self.oldLocation = location
			elif firstWord == 'M101':
				self.isExtrusionActive = True
			elif firstWord == 'M103':
				self.isExtrusionActive = False
		self.extent = cornerMaximumComplex - cornerMinimumComplex
		self.shapeCenter = 0.5 * (cornerMaximumComplex + cornerMinimumComplex)
		self.separation = self.repository.separationOverEdgeWidth.value * self.absoluteEdgeWidth
		self.extentPlusSeparation = self.extent + complex(self.separation, self.separation)
		columnsMinusOne = self.numberOfColumns - 1
		rowsMinusOne = self.numberOfRows - 1
		self.arrayExtent = complex(self.extentPlusSeparation.real * columnsMinusOne, self.extentPlusSeparation.imag * rowsMinusOne)
		self.arrayCenter = 0.5 * self.arrayExtent


def main():
	'Display the multiply dialog.'
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == '__main__':
	main()
