"""
This page is in the table of contents.
Drill is a script to drill down small holes.

==Operation==
The default 'Activate Drill' checkbox is on.  When it is on, the functions described below will work, when it is off, the functions will not be called.

==Settings==
===Drilling Margin===
The drill script will move the tool from the top of the hole plus the 'Drilling Margin on Top', to the bottom of the hole minus the 'Drilling Margin on Bottom'.

===Drilling Margin on Top===
Default is three millimeters.

===Drilling Margin on Bottom===
Default is one millimeter.

==Examples==
The following examples drill the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and drill.py.

> python drill.py
This brings up the drill dialog.

> python drill.py Screw Holder Bottom.stl
The drill tool is parsing the file:
Screw Holder Bottom.stl
..
The drill tool has created the file:
.. Screw Holder Bottom_drill.gcode

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import intercircle
from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_utilities import skeinforge_craft
from skeinforge_application.skeinforge_utilities import skeinforge_polyfile
from skeinforge_application.skeinforge_utilities import skeinforge_profile
import sys


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

def getCraftedText( fileName, text, repository=None):
	"Drill a gcode linear move file or text."
	return getCraftedTextFromText(archive.getTextIfEmpty(fileName, text), repository)

def getCraftedTextFromText(gcodeText, repository=None):
	"Drill a gcode linear move text."
	if gcodec.isProcedureDoneOrFileIsEmpty( gcodeText, 'drill'):
		return gcodeText
	if repository == None:
		repository = settings.getReadRepository( DrillRepository() )
	if not repository.activateDrill.value:
		return gcodeText
	return DrillSkein().getCraftedGcode(gcodeText, repository)

def getNewRepository():
	'Get new repository.'
	return DrillRepository()

def getPolygonCenter( polygon ):
	"Get the centroid of a polygon."
	pointSum = complex()
	areaSum = 0.0
	for pointIndex in xrange( len( polygon ) ):
		pointBegin = polygon[pointIndex]
		pointEnd  = polygon[ (pointIndex + 1) % len( polygon ) ]
		area = pointBegin.real * pointEnd.imag - pointBegin.imag * pointEnd.real
		areaSum += area
		pointSum += complex( pointBegin.real + pointEnd.real, pointBegin.imag + pointEnd.imag ) * area
	return pointSum / 3.0 / areaSum

def writeOutput(fileName, shouldAnalyze=True):
	"Drill a gcode linear move file."
	skeinforge_craft.writeChainTextWithNounMessage(fileName, 'drill', shouldAnalyze)


class ThreadLayer:
	"A layer of loops and paths."
	def __init__( self, z ):
		"Thread layer constructor."
		self.points = []
		self.z = z

	def __repr__(self):
		"Get the string representation of this thread layer."
		return '%s, %s' % ( self.z, self.points )


class DrillRepository:
	"A class to handle the drill settings."
	def __init__(self):
		"Set the default settings, execute title & settings fileName."
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.drill.html', self )
		self.fileNameInput = settings.FileNameInput().getFromFileName( fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Drill', self, '')
		self.activateDrill = settings.BooleanSetting().getFromValue('Activate Drill', self, True )
		self.drillingMarginOnBottom = settings.FloatSpin().getFromValue( 0.0, 'Drilling Margin on Bottom (millimeters):', self, 5.0, 1.0 )
		self.drillingMarginOnTop = settings.FloatSpin().getFromValue( 0.0, 'Drilling Margin on Top (millimeters):', self, 20.0, 3.0 )
		self.executeTitle = 'Drill'

	def execute(self):
		"Drill button has been clicked."
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class DrillSkein:
	"A class to drill a skein of extrusions."
	def __init__(self):
		self.boundary = None
		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.extruderActive = False
		self.halfLayerThickness = 0.4
		self.isDrilled = False
		self.lineIndex = 0
		self.lines = None
		self.maximumDistance = 0.06
		self.oldLocation = None
		self.threadLayer = None
		self.threadLayers = []

	def addDrillHoles(self):
		"Parse a gcode line."
		self.isDrilled = True
		if len( self.threadLayers ) < 1:
			return
		topThreadLayer = self.threadLayers[0]
		drillPoints = topThreadLayer.points
		for drillPoint in drillPoints:
			zTop = topThreadLayer.z + self.halfLayerThickness + self.repository.drillingMarginOnTop.value
			drillingCenterDepth = self.getDrillingCenterDepth( topThreadLayer.z, drillPoint )
			zBottom = drillingCenterDepth - self.halfLayerThickness - self.repository.drillingMarginOnBottom.value
			self.addGcodeFromVerticalThread( drillPoint, zTop, zBottom )

	def addGcodeFromVerticalThread( self, point, zBegin, zEnd ):
		"Add a thread to the output."
		self.distanceFeedRate.addGcodeMovementZ( point, zBegin )
		self.distanceFeedRate.addLine('M101') # Turn extruder on.
		self.distanceFeedRate.addGcodeMovementZ( point, zEnd )
		self.distanceFeedRate.addLine('M103') # Turn extruder off.

	def addThreadLayerIfNone(self):
		"Add a thread layer if it is none."
		if self.threadLayer != None:
			return
		self.threadLayer = ThreadLayer( self.layerZ )
		self.threadLayers.append( self.threadLayer )

	def getCraftedGcode(self, gcodeText, repository):
		"Parse gcode text and store the drill gcode."
		self.lines = archive.getTextLines(gcodeText)
		self.repository = repository
		self.parseInitialization()
		for line in self.lines[self.lineIndex :]:
			self.parseNestedRing(line)
		for line in self.lines[self.lineIndex :]:
			self.parseLine(line)
		return self.distanceFeedRate.output.getvalue()

	def getDrillingCenterDepth( self, drillingCenterDepth, drillPoint ):
		"Get the drilling center depth."
		for threadLayer in self.threadLayers[1 :]:
			if self.isPointClose( drillPoint, threadLayer.points ):
				drillingCenterDepth = threadLayer.z
			else:
				return drillingCenterDepth
		return drillingCenterDepth

	def isPointClose( self, drillPoint, points ):
		"Determine if a point on the thread layer is close."
		for point in points:
			if abs( point - drillPoint ) < self.maximumDistance:
				return True
		return False

	def linearMove( self, splitLine ):
		"Add a linear move to the loop."
		self.addThreadLayerIfNone()
		location = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
		if self.extruderActive:
			self.boundary = None
		self.oldLocation = location

	def parseInitialization(self):
		'Parse gcode initialization and store the parameters.'
		for self.lineIndex in xrange(len(self.lines)):
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			self.distanceFeedRate.parseSplitLine(firstWord, splitLine)
			if firstWord == '(</extruderInitialization>)':
				self.distanceFeedRate.addTagBracketedProcedure('drill')
				return
			elif firstWord == '(<layerHeight>':
				self.halfLayerThickness = 0.5 * float(splitLine[1])
			elif firstWord == '(<edgeWidth>':
				self.maximumDistance = 0.1 * float(splitLine[1])
			self.distanceFeedRate.addLine(line)

	def parseLine(self, line):
		"Parse a gcode line."
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		self.distanceFeedRate.addLine(line)
		if firstWord == '(<layer>':
			if not self.isDrilled:
				self.addDrillHoles()

	def parseNestedRing(self, line):
		"Parse a nested ring."
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if firstWord == 'G1':
			self.linearMove(splitLine)
		if firstWord == 'M101':
			self.extruderActive = True
		elif firstWord == 'M103':
			self.extruderActive = False
		elif firstWord == '(<boundaryPoint>':
			location = gcodec.getLocationFromSplitLine(None, splitLine)
			if self.boundary == None:
				self.boundary = []
			self.boundary.append(location.dropAxis())
		elif firstWord == '(<layer>':
			self.layerZ = float(splitLine[1])
			self.threadLayer = None
		elif firstWord == '(<boundaryPerimeter>)':
			self.addThreadLayerIfNone()
		elif firstWord == '(</boundaryPerimeter>)':
			if self.boundary != None:
				self.threadLayer.points.append( getPolygonCenter( self.boundary ) )
				self.boundary = None


def main():
	"Display the drill dialog."
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == "__main__":
	main()
