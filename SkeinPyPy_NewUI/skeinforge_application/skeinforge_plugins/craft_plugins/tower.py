"""
This page is in the table of contents.
Tower commands the fabricator to extrude a disconnected region for a few layers, then go to another disconnected region and extrude there.  Its purpose is to reduce the number of stringers between a shape and reduce extruder travel.

The tower manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Tower

==Operation==
The default 'Activate Tower' checkbox is off.  The default is off because tower could result in the extruder colliding with an already extruded part of the shape and because extruding in one region for more than one layer could result in the shape melting.  When it is on, the functions described below will work, when it is off, nothing will be done.

==Settings==
===Maximum Tower Height===
Default: 5

Defines the maximum number of layers that the extruder will extrude in one region before going to another.  This is the most important value for tower.

===Extruder Possible Collision Cone Angle===
Default: 60 degrees

Tower works by looking for islands in each layer and if it finds another island in the layer above, it goes to the next layer above instead of going across to other regions on the original layer.  It checks for collision with shapes already extruded within a cone from the nozzle tip.  The 'Extruder Possible Collision Cone Angle' setting is the angle of that cone.  Realistic values for the cone angle range between zero and ninety.  The higher the angle, the less likely a collision with the rest of the shape is, generally the extruder will stay in the region for only a few layers before a collision is detected with the wide cone.

===Tower Start Layer===
Default: 1

Defines the layer index which the script starts extruding towers, after the last raft layer which does not have support material.  It is best to not tower at least the first layer because the temperature of the first layer is sometimes different than that of the other layers.

==Examples==
The following examples tower the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and tower.py.

> python tower.py
This brings up the tower dialog.

> python tower.py Screw Holder Bottom.stl
The tower tool is parsing the file:
Screw Holder Bottom.stl
..
The tower tool has created the file:
.. Screw Holder Bottom_tower.gcode

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import intercircle
from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_utilities import skeinforge_craft
from skeinforge_application.skeinforge_utilities import skeinforge_polyfile
from skeinforge_application.skeinforge_utilities import skeinforge_profile
import math
import sys


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

def getCraftedText( fileName, text, towerRepository = None ):
	"Tower a gcode linear move file or text."
	return getCraftedTextFromText( archive.getTextIfEmpty(fileName, text), towerRepository )

def getCraftedTextFromText( gcodeText, towerRepository = None ):
	"Tower a gcode linear move text."
	if gcodec.isProcedureDoneOrFileIsEmpty( gcodeText, 'tower'):
		return gcodeText
	if towerRepository == None:
		towerRepository = settings.getReadRepository( TowerRepository() )
	if not towerRepository.activateTower.value:
		return gcodeText
	return TowerSkein().getCraftedGcode( gcodeText, towerRepository )

def getNewRepository():
	'Get new repository.'
	return TowerRepository()

def writeOutput(fileName, shouldAnalyze=True):
	"Tower a gcode linear move file."
	skeinforge_craft.writeChainTextWithNounMessage(fileName, 'tower', shouldAnalyze)


class Island:
	"A class to hold the boundary and lines."
	def __init__(self):
		self.boundary = []
		self.boundingLoop = None
		self.lines = []

	def addToBoundary( self, splitLine ):
		"Add to the boundary if it is not complete."
		if self.boundingLoop == None:
			location = gcodec.getLocationFromSplitLine(None, splitLine)
			self.boundary.append(location.dropAxis())
			self.z = location.z

	def createBoundingLoop(self):
		"Create the bounding loop if it is not already created."
		if self.boundingLoop == None:
			self.boundingLoop = intercircle.BoundingLoop().getFromLoop( self.boundary )


class ThreadLayer:
	"A layer of loops and paths."
	def __init__(self):
		"Thread layer constructor."
		self.afterExtrusionLines = []
		self.beforeExtrusionLines = []
		self.islands = []

	def __repr__(self):
		"Get the string representation of this thread layer."
		return '%s' % self.islands


class TowerRepository:
	"A class to handle the tower settings."
	def __init__(self):
		"Set the default settings, execute title & settings fileName."
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.tower.html', self )
		self.fileNameInput = settings.FileNameInput().getFromFileName( fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Tower', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Tower')
		self.activateTower = settings.BooleanSetting().getFromValue('Activate Tower', self, False )
		self.extruderPossibleCollisionConeAngle = settings.FloatSpin().getFromValue( 40.0, 'Extruder Possible Collision Cone Angle (degrees):', self, 80.0, 60.0 )
		self.maximumTowerHeight = settings.IntSpin().getFromValue( 2, 'Maximum Tower Height (layers):', self, 10, 5 )
		self.towerStartLayer = settings.IntSpin().getFromValue( 1, 'Tower Start Layer (integer):', self, 5, 1 )
		self.executeTitle = 'Tower'

	def execute(self):
		"Tower button has been clicked."
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class TowerSkein:
	"A class to tower a skein of extrusions."
	def __init__(self):
		self.afterExtrusionLines = []
		self.beforeExtrusionLines = []
		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.edgeWidth = 0.6
		self.highestZ = - 987654321.0
		self.island = None
		self.layerIndex = 0
		self.lineIndex = 0
		self.lines = None
		self.minimumBelow = 0.1
		self.oldLayerIndex = None
		self.oldLocation = None
		self.oldOrderedLocation = Vector3()
		self.shutdownLineIndex = sys.maxint
		self.nestedRingCount = 0
		self.threadLayer = None
		self.threadLayers = []
		self.travelFeedRateMinute = None

	def addEntireLayer( self, threadLayer ):
		"Add entire thread layer."
		self.distanceFeedRate.addLines( threadLayer.beforeExtrusionLines )
		for island in threadLayer.islands:
			self.distanceFeedRate.addLines( island.lines )
		self.distanceFeedRate.addLines( threadLayer.afterExtrusionLines )

	def addHighThread(self, location):
		"Add thread with a high move if necessary to clear the previous extrusion."
		if self.oldLocation != None:
			if self.oldLocation.z + self.minimumBelow < self.highestZ:
				self.distanceFeedRate.addGcodeMovementZWithFeedRate( self.travelFeedRateMinute, self.oldLocation.dropAxis(), self.highestZ )
		if location.z + self.minimumBelow < self.highestZ:
			self.distanceFeedRate.addGcodeMovementZWithFeedRate( self.travelFeedRateMinute, location.dropAxis(), self.highestZ )

	def addThreadLayerIfNone(self):
		"Add a thread layer if it is none."
		if self.threadLayer != None:
			return
		self.threadLayer = ThreadLayer()
		self.threadLayers.append( self.threadLayer )
		self.threadLayer.beforeExtrusionLines = self.beforeExtrusionLines
		self.beforeExtrusionLines = []

	def addTowers(self):
		"Add towers."
		bottomLayerIndex = self.getBottomLayerIndex()
		if bottomLayerIndex == None:
			return
		removedIsland = self.getRemovedIslandAddLayerLinesIfDifferent( self.threadLayers[ bottomLayerIndex ].islands, bottomLayerIndex )
		while 1:
			self.climbTower( removedIsland )
			bottomLayerIndex = self.getBottomLayerIndex()
			if bottomLayerIndex == None:
				return
			removedIsland = self.getRemovedIslandAddLayerLinesIfDifferent( self.threadLayers[ bottomLayerIndex ].islands, bottomLayerIndex )

	def climbTower( self, removedIsland ):
		"Climb up the island to any islands directly above."
		outsetDistance = 1.5 * self.edgeWidth
		for step in xrange( self.towerRepository.maximumTowerHeight.value ):
			aboveIndex = self.oldLayerIndex + 1
			if aboveIndex >= len( self.threadLayers ):
				return
			outsetRemovedLoop = removedIsland.boundingLoop.getOutsetBoundingLoop( outsetDistance )
			islandsWithin = []
			for island in self.threadLayers[ aboveIndex ].islands:
				if self.isInsideRemovedOutsideCone( island, outsetRemovedLoop, aboveIndex ):
					islandsWithin.append( island )
			if len( islandsWithin ) < 1:
				return
			removedIsland = self.getRemovedIslandAddLayerLinesIfDifferent( islandsWithin, aboveIndex )
			self.threadLayers[ aboveIndex ].islands.remove( removedIsland )

	def getBottomLayerIndex(self):
		"Get the index of the first island layer which has islands."
		for islandLayerIndex in xrange( len( self.threadLayers ) ):
			if len( self.threadLayers[ islandLayerIndex ].islands ) > 0:
				return islandLayerIndex
		return None

	def getCraftedGcode( self, gcodeText, towerRepository ):
		"Parse gcode text and store the tower gcode."
		self.lines = archive.getTextLines(gcodeText)
		self.towerRepository = towerRepository
		self.parseInitialization()
		self.parseIfWordUntilWord('(<operatingLayerEnd>')
		self.parseIfWordUntilWord('(</skirt>)')
		for lineIndex in xrange(self.lineIndex, len(self.lines)):
			self.parseLine( lineIndex )
		concatenateEndIndex = min( len( self.threadLayers ), towerRepository.towerStartLayer.value )
		for threadLayer in self.threadLayers[ : concatenateEndIndex ]:
			self.addEntireLayer( threadLayer )
		self.threadLayers = self.threadLayers[ concatenateEndIndex : ]
		self.addTowers()
		self.distanceFeedRate.addLines( self.lines[ self.shutdownLineIndex : ] )
		return self.distanceFeedRate.output.getvalue()

	def getRemovedIslandAddLayerLinesIfDifferent( self, islands, layerIndex ):
		"Add gcode lines for the layer if it is different than the old bottom layer index."
		threadLayer = None
		if layerIndex != self.oldLayerIndex:
			self.oldLayerIndex = layerIndex
			threadLayer = self.threadLayers[layerIndex]
			self.distanceFeedRate.addLines( threadLayer.beforeExtrusionLines )
		removedIsland = self.getTransferClosestNestedRingLines( self.oldOrderedLocation, islands )
		if threadLayer != None:
			self.distanceFeedRate.addLines( threadLayer.afterExtrusionLines )
		return removedIsland

	def getTransferClosestNestedRingLines( self, oldOrderedLocation, remainingNestedRings ):
		"Get and transfer the closest remaining nested ring."
		if len( remainingNestedRings ) > 0:
			oldOrderedLocation.z = remainingNestedRings[0].z
		closestDistance = 999999999987654321.0
		closestNestedRing = None
		for remainingNestedRing in remainingNestedRings:
			distance = euclidean.getClosestDistanceIndexToLine(oldOrderedLocation.dropAxis(), remainingNestedRing.boundary).distance
			if distance < closestDistance:
				closestDistance = distance
				closestNestedRing = remainingNestedRing
		remainingNestedRings.remove(closestNestedRing)
		hasTravelledHighRoad = False
		for line in closestNestedRing.lines:
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			if firstWord == 'G1':
				location = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
				if not hasTravelledHighRoad:
					hasTravelledHighRoad = True
					self.addHighThread(location)
				if location.z > self.highestZ:
					self.highestZ = location.z
				self.oldLocation = location
			self.distanceFeedRate.addLine(line)
		return closestNestedRing

	def isInsideRemovedOutsideCone( self, island, removedBoundingLoop, untilLayerIndex ):
		"Determine if the island is entirely inside the removed bounding loop and outside the collision cone of the remaining islands."
		if not island.boundingLoop.isEntirelyInsideAnother( removedBoundingLoop ):
			return False
		bottomLayerIndex = self.getBottomLayerIndex()
		coneAngleTangent = math.tan( math.radians( self.towerRepository.extruderPossibleCollisionConeAngle.value ) )
		for layerIndex in xrange( bottomLayerIndex, untilLayerIndex ):
			islands = self.threadLayers[layerIndex].islands
			outsetDistance = self.edgeWidth * ( untilLayerIndex - layerIndex ) * coneAngleTangent + 0.5 * self.edgeWidth
			for belowIsland in self.threadLayers[layerIndex].islands:
				outsetIslandLoop = belowIsland.boundingLoop.getOutsetBoundingLoop( outsetDistance )
				if island.boundingLoop.isOverlappingAnother( outsetIslandLoop ):
					return False
		return True

	def parseIfWordUntilWord(self, word):
		"Parse gcode if there is a word until the word is reached."
		for self.lineIndex in xrange(self.lineIndex, gcodec.getFirstWordIndexReverse(word, self.lines, self.lineIndex)):
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			self.distanceFeedRate.addLine(line)
			if firstWord == 'G1':
				self.oldLocation = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
				if self.oldLocation.z > self.highestZ:
					self.highestZ = self.oldLocation.z

	def parseInitialization(self):
		'Parse gcode initialization and store the parameters.'
		for self.lineIndex in xrange(len(self.lines)):
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			self.distanceFeedRate.parseSplitLine(firstWord, splitLine)
			if firstWord == '(</extruderInitialization>)':
				self.distanceFeedRate.addTagBracketedProcedure('tower')
			elif firstWord == '(<layer>':
				return
			elif firstWord == '(<layerHeight>':
				self.minimumBelow = 0.1 * float(splitLine[1])
			elif firstWord == '(<edgeWidth>':
				self.edgeWidth = float(splitLine[1])
			elif firstWord == '(<travelFeedRatePerSecond>':
				self.travelFeedRateMinute = 60.0 * float(splitLine[1])
			self.distanceFeedRate.addLine(line)

	def parseLine( self, lineIndex ):
		"Parse a gcode line."
		line = self.lines[lineIndex]
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		self.afterExtrusionLines.append(line)
		if firstWord == 'M103':
			self.afterExtrusionLines = []
		elif firstWord == '(</boundaryPerimeter>)':
			self.island.createBoundingLoop()
		elif firstWord == '(<boundaryPoint>':
			self.island.addToBoundary(splitLine)
		elif firstWord == '(</crafting>)':
			self.shutdownLineIndex = lineIndex
		elif firstWord == '(<layer>':
			self.beforeExtrusionLines = [ line ]
			self.island = None
			self.nestedRingCount = 0
			self.threadLayer = None
			return
		elif firstWord == '(</layer>)':
			if self.threadLayer != None:
				self.threadLayer.afterExtrusionLines = self.afterExtrusionLines
			self.afterExtrusionLines = []
		elif firstWord == '(</loop>)':
			self.afterExtrusionLines = []
		elif firstWord == '(<nestedRing>)':
			self.nestedRingCount += 1
			if self.island == None:
				self.island = Island()
				self.addThreadLayerIfNone()
				self.threadLayer.islands.append( self.island )
		elif firstWord == '(</edge>)':
			self.afterExtrusionLines = []
		if self.island != None:
			self.island.lines.append(line)
		if firstWord == '(</nestedRing>)':
			self.afterExtrusionLines = []
			self.nestedRingCount -= 1
			if self.nestedRingCount == 0:
				self.island = None
		if len( self.beforeExtrusionLines ) > 0:
			self.beforeExtrusionLines.append(line)


def main():
	"Display the tower dialog."
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == "__main__":
	main()
