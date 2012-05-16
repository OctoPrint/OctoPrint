"""
This page is in the table of contents.
The Joris plugin makes the perimiter slowly increase in Z over the layer. This will make vases/cups without a z blob.

==Operation==
The default 'Activate Joris' checkbox is off.  When it is on, the Joris plugin will do it's work.

==Settings==
===Layers From===
Default: 1

Defines which layer of the print the joris process starts from.

==Tips==

==Examples==

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
import sys


__author__ = 'Daid (daid303@gmail.com'
__date__ = '$Date: 2012/24/01 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCraftedText(fileName, gcodeText, repository=None):
	'Joris a gcode linear move text.'
	return getCraftedTextFromText(archive.getTextIfEmpty(fileName, gcodeText), repository)

def getCraftedTextFromText(gcodeText, repository=None):
	'Joris a gcode linear move text.'
	if gcodec.isProcedureDoneOrFileIsEmpty(gcodeText, 'Joris'):
		return gcodeText
	if repository == None:
		repository = settings.getReadRepository(JorisRepository())
	if not repository.activateJoris.value:
		return gcodeText
	return JorisSkein().getCraftedGcode(gcodeText, repository)

def getIsMinimumSides(loops, sides=3):
	'Determine if all the loops have at least the given number of sides.'
	for loop in loops:
		if len(loop) < sides:
			return False
	return True

def getNewRepository():
	'Get new repository.'
	return JorisRepository()

def writeOutput(fileName, shouldAnalyze=True):
	'Joris a gcode linear move file.  Chain Joris the gcode if it is not already Jorised.'
	skeinforge_craft.writeChainTextWithNounMessage(fileName, 'joris', shouldAnalyze)


class JorisRepository:
	'A class to handle the Joris settings.'
	def __init__(self):
		'Set the default settings, execute title & settings fileName.'
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.joris.html', self )
		self.fileNameInput = settings.FileNameInput().getFromFileName( fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Joris', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Joris')
		self.activateJoris = settings.BooleanSetting().getFromValue('Activate Joris', self, False)
		settings.LabelSeparator().getFromRepository(self)
		self.layersFrom = settings.IntSpin().getSingleIncrementFromValue(0, 'Layers From (index):', self, 912345678, 1)
		self.executeTitle = 'Joris'

	def execute(self):
		'Joris button has been clicked.'
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class JorisSkein:
	'A class to Joris a skein of extrusions.'
	def __init__(self):
		'Initialize.'
		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.lines = None
		self.layerIndex = -1
		self.feedRateMinute = 959.0
		self.travelFeedRateMinute = 957.0
		self.perimeter = None
		self.oldLocation = None
		self.doJoris = False
		self.firstLayer = True
	
	def getCraftedGcode( self, gcodeText, repository ):
		'Parse gcode text and store the joris gcode.'
		self.lines = archive.getTextLines(gcodeText)
		self.repository = repository
		self.layersFromBottom = repository.layersFrom.value
		self.parseInitialization()
		for self.lineIndex in xrange(self.lineIndex, len(self.lines)):
			line = self.lines[self.lineIndex]
			self.parseLine(line)
		return gcodec.getGcodeWithoutDuplication('M108', self.distanceFeedRate.output.getvalue())
		
	def parseInitialization(self):
		'Parse gcode initialization and store the parameters.'
		for self.lineIndex in xrange(len(self.lines)):
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			self.distanceFeedRate.parseSplitLine(firstWord, splitLine)
			if firstWord == '(<layerThickness>':
				self.layerThickness = float(splitLine[1])
			elif firstWord == '(</extruderInitialization>)':
				self.distanceFeedRate.addTagBracketedProcedure('joris')
				return
			elif firstWord == '(<travelFeedRatePerSecond>':
				self.travelFeedRateMinute = 60.0 * float(splitLine[1])
			self.distanceFeedRate.addLine(line)
			
	def parseLine(self, line):
		'Parse a gcode line and add it to the joris skein.'
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if firstWord == 'G1' and self.doJoris:
			self.feedRateMinute = gcodec.getFeedRateMinute(self.feedRateMinute, splitLine)
			location = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
			self.oldLocation = location
			if self.perimeter != None:
				self.perimeter.append(location.dropAxis())
				return
		elif firstWord == '(<layer>':
			self.layerIndex += 1
			settings.printProgress(self.layerIndex, 'joris')
		elif firstWord == 'M108':
			self.oldFlowRate = gcodec.getDoubleAfterFirstLetter(splitLine[1])
		elif firstWord == '(<edge>':
			if self.layerIndex >= self.layersFromBottom:
				self.doJoris = True
		elif firstWord == 'M101' and self.doJoris:
			self.perimeter = []
			return
		elif firstWord == 'M103' and self.doJoris:
			self.addJorisedPerimeter()
			return
		elif firstWord == '(</edge>)':
			self.doJoris = False
		self.distanceFeedRate.addLine(line)
		
	def addJorisedPerimeter(self):
		'Add jorised perimeter.'
		if self.perimeter == None:
			return
		#Calculate the total length of the perimeter.
		p = self.oldLocation.dropAxis()
		perimeterLength = 0;
		for point in self.perimeter:
			perimeterLength += abs( point - p );
			p = point
		
		#Build the perimeter with an increasing Z over the length.
		if self.firstLayer:
			#On the first layer, we need to create an extra jorised perimeter, else we create a gap at the end of the perimeter.
			print "*************"
			p = self.oldLocation.dropAxis()
			length = 0;
			self.distanceFeedRate.addLine('M101') # Turn extruder on.
			for point in self.perimeter:
				length += abs( point - p );
				p = point
				self.distanceFeedRate.addGcodeMovementZWithFeedRate(self.feedRateMinute, point, self.oldLocation.z - self.layerThickness + self.layerThickness * length / perimeterLength)
			self.distanceFeedRate.addLine('M103') # Turn extruder off.
			self.firstLayer = False

		p = self.oldLocation.dropAxis()
		length = 0;
		self.distanceFeedRate.addLine('M101') # Turn extruder on.
		for point in self.perimeter:
			length += abs( point - p );
			p = point
			self.distanceFeedRate.addGcodeMovementZWithFeedRate(self.feedRateMinute, point, self.oldLocation.z + self.layerThickness * length / perimeterLength)
		self.distanceFeedRate.addLine('M103') # Turn extruder off.
		self.perimeter = None

