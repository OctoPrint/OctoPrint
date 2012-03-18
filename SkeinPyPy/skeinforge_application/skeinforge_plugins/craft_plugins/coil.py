"""
This page is in the table of contents.
Coil is a script to coil wire or filament around an object.

==Operation==
The default 'Activate Coil' checkbox is on.  When it is on, the functions described below will work, when it is off, the functions will not be called.

==Settings==
===Minimum Tool Distance===
Default is twenty millimeters.

Defines the minimum distance between the wire dispenser and the object.  The 'Minimum Tool Distance' should be set to the maximum radius of the wire dispenser, times at least 1.3 to get a reasonable safety margin.

==Examples==
The following examples coil the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and coil.py.

> python coil.py
This brings up the coil dialog.

> python coil.py Screw Holder Bottom.stl
The coil tool is parsing the file:
Screw Holder Bottom.stl
..
The coil tool has created the file:
Screw Holder Bottom_coil.gcode

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
import os
import sys


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCraftedText( fileName, gcodeText = '', repository=None):
	"Coil the file or gcodeText."
	return getCraftedTextFromText( archive.getTextIfEmpty(fileName, gcodeText), repository )

def getCraftedTextFromText(gcodeText, repository=None):
	"Coil a gcode linear move gcodeText."
	if gcodec.isProcedureDoneOrFileIsEmpty( gcodeText, 'coil'):
		return gcodeText
	if repository == None:
		repository = settings.getReadRepository( CoilRepository() )
	if not repository.activateCoil.value:
		return gcodeText
	return CoilSkein().getCraftedGcode(gcodeText, repository)

def getNewRepository():
	'Get new repository.'
	return CoilRepository()

def writeOutput(fileName, shouldAnalyze=True):
	"Coil a gcode linear move file."
	skeinforge_craft.writeChainTextWithNounMessage(fileName, 'coil', shouldAnalyze)


class CoilRepository:
	"A class to handle the coil settings."
	def __init__(self):
		"Set the default settings, execute title & settings fileName."
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.coil.html', self )
		self.fileNameInput = settings.FileNameInput().getFromFileName( fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Coil', self, '')
		self.activateCoil = settings.BooleanSetting().getFromValue('Activate Coil', self, True )
		self.minimumToolDistance = settings.FloatSpin().getFromValue( 10.0, 'Minimum Tool Distance (millimeters):', self, 50.0, 20.0 )
		self.executeTitle = 'Coil'

	def execute(self):
		"Coil button has been clicked."
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)



class CoilSkein:
	"A class to coil a skein of extrusions."
	def __init__(self):
		self.boundaryLayers = []
		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.edgeWidth = 0.6
		self.lineIndex = 0
		self.lines = None
		self.oldLocationComplex = complex()
		self.shutdownLines = []

	def addCoilLayer( self, boundaryLayers, radius, z ):
		"Add a coil layer."
		self.distanceFeedRate.addLine('(<layer> %s )' % z ) # Indicate that a new layer is starting.
		self.distanceFeedRate.addLine('(<nestedRing>)')
		thread = []
		for boundaryLayerIndex in xrange(1, len(boundaryLayers) - 1):
			boundaryLayer = boundaryLayers[boundaryLayerIndex]
			boundaryLayerBegin = boundaryLayers[boundaryLayerIndex - 1]
			boundaryLayerEnd = boundaryLayers[boundaryLayerIndex + 1]
			beginLocation = Vector3(0.0, 0.0, 0.5 * (boundaryLayerBegin.z + boundaryLayer.z))
			outsetLoop = intercircle.getLargestInsetLoopFromLoop(boundaryLayer.loops[0], - radius)
			self.addCoilToThread(beginLocation, 0.5 * (boundaryLayer.z + boundaryLayerEnd.z), outsetLoop, thread)
		self.addGcodeFromThread(thread)
		self.distanceFeedRate.addLine('(</nestedRing>)')
		self.distanceFeedRate.addLine('(</layer>)')

	def addCoilLayers(self):
		"Add the coil layers."
		numberOfLayersFloat = round( self.edgeWidth / self.layerHeight )
		numberOfLayers = int( numberOfLayersFloat )
		halfLayerThickness = 0.5 * self.layerHeight
		startOutset = self.repository.minimumToolDistance.value + halfLayerThickness
		startZ = self.boundaryLayers[0].z + halfLayerThickness
		zRange = self.boundaryLayers[-1].z - self.boundaryLayers[0].z
		zIncrement = 0.0
		if zRange >= 0.0:
			zIncrement = zRange / numberOfLayersFloat
		for layerIndex in xrange( numberOfLayers ):
			settings.printProgressByNumber(layerIndex, numberOfLayers, 'coil')
			boundaryLayers = self.boundaryLayers
			if layerIndex % 2 == 1:
				boundaryLayers = self.boundaryReverseLayers
			radius = startOutset + layerIndex * self.layerHeight
			z = startZ + layerIndex * zIncrement
			self.addCoilLayer( boundaryLayers, radius, z )

	def addCoilToThread(self, beginLocation, endZ, loop, thread):
		"Add a coil to the thread."
		if len(loop) < 1:
			return
		loop = euclidean.getLoopStartingClosest(self.halfEdgeWidth, self.oldLocationComplex, loop)
		length = euclidean.getLoopLength(loop)
		if length <= 0.0:
			return
		oldPoint = loop[0]
		pathLength = 0.0
		for point in loop[1 :]:
			pathLength += abs(point - oldPoint)
			along = pathLength / length
			z = (1.0 - along) * beginLocation.z + along * endZ
			location = Vector3(point.real, point.imag, z)
			thread.append(location)
			oldPoint = point
		self.oldLocationComplex = loop[-1]

	def addGcodeFromThread( self, thread ):
		"Add a thread to the output."
		if len(thread) > 0:
			firstLocation = thread[0]
			self.distanceFeedRate.addGcodeMovementZ( firstLocation.dropAxis(), firstLocation.z )
		else:
			print("zero length vertex positions array which was skipped over, this should never happen")
		if len(thread) < 2:
			print("thread of only one point in addGcodeFromThread in coil, this should never happen")
			print(thread)
			return
		self.distanceFeedRate.addLine('M101') # Turn extruder on.
		for location in thread[1 :]:
			self.distanceFeedRate.addGcodeMovementZ( location.dropAxis(), location.z )
		self.distanceFeedRate.addLine('M103') # Turn extruder off.

	def getCraftedGcode(self, gcodeText, repository):
		"Parse gcode text and store the coil gcode."
		self.repository = repository
		self.lines = archive.getTextLines(gcodeText)
		self.parseInitialization()
		self.parseBoundaries()
		self.parseUntilLayer()
		self.addCoilLayers()
		self.distanceFeedRate.addLines( self.shutdownLines )
		return self.distanceFeedRate.output.getvalue()

	def parseBoundaries(self):
		"Parse the boundaries and add them to the boundary layers."
		boundaryLoop = None
		boundaryLayer = None
		for line in self.lines[self.lineIndex :]:
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			if len( self.shutdownLines ) > 0:
				self.shutdownLines.append(line)
			if firstWord == '(</boundaryPerimeter>)':
				boundaryLoop = None
			elif firstWord == '(<boundaryPoint>':
				location = gcodec.getLocationFromSplitLine(None, splitLine)
				if boundaryLoop == None:
					boundaryLoop = []
					boundaryLayer.loops.append(boundaryLoop)
				boundaryLoop.append(location.dropAxis())
			elif firstWord == '(<layer>':
				boundaryLayer = euclidean.LoopLayer(float(splitLine[1]))
				self.boundaryLayers.append(boundaryLayer)
			elif firstWord == '(</crafting>)':
				self.shutdownLines = [ line ]
		for boundaryLayer in self.boundaryLayers:
			if not euclidean.isWiddershins( boundaryLayer.loops[0] ):
				boundaryLayer.loops[0].reverse()
		self.boundaryReverseLayers = self.boundaryLayers[:]
		self.boundaryReverseLayers.reverse()

	def parseInitialization(self):
		'Parse gcode initialization and store the parameters.'
		for self.lineIndex in xrange(len(self.lines)):
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			self.distanceFeedRate.parseSplitLine(firstWord, splitLine)
			if firstWord == '(</extruderInitialization>)':
				self.distanceFeedRate.addTagBracketedProcedure('coil')
				return
			elif firstWord == '(<layerHeight>':
				self.layerHeight = float(splitLine[1])
			elif firstWord == '(<edgeWidth>':
				self.edgeWidth = float(splitLine[1])
				self.halfEdgeWidth = 0.5 * self.edgeWidth
			self.distanceFeedRate.addLine(line)

	def parseUntilLayer(self):
		"Parse until the layer line and add it to the coil skein."
		for self.lineIndex in xrange(self.lineIndex, len(self.lines)):
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			self.distanceFeedRate.parseSplitLine(firstWord, splitLine)
			if firstWord == '(<layer>':
				return
			self.distanceFeedRate.addLine(line)


def main():
	"Display the coil dialog."
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == "__main__":
	main()
