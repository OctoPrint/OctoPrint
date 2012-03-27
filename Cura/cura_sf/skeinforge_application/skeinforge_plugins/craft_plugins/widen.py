#! /usr/bin/env python
"""
This page is in the table of contents.
Widen will widen the outside edges away from the inside edges, so that the outsides will be at least two edge widths away from the insides and therefore the outside filaments will not overlap the inside filaments.

For example, if a mug has a very thin wall, widen would widen the outside of the mug so that the wall of the mug would be two edge widths wide, and the outside wall filament would not overlap the inside filament.

For another example, if the outside of the object runs right next to a hole, widen would widen the wall around the hole so that the wall would bulge out around the hole, and the outside filament would not overlap the hole filament.

The widen manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Widen

==Operation==
The default 'Activate Widen' checkbox is off.  When it is on, widen will work, when it is off, nothing will be done.

==Examples==
The following examples widen the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and widen.py.

> python widen.py
This brings up the widen dialog.

> python widen.py Screw Holder Bottom.stl
The widen tool is parsing the file:
Screw Holder Bottom.stl
..
The widen tool has created the file:
.. Screw Holder Bottom_widen.gcode

"""

from __future__ import absolute_import
try:
	import psyco
	psyco.full()
except:
	pass
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
from fabmetheus_utilities.geometry.geometry_utilities import boolean_solid
from fabmetheus_utilities.geometry.solids import triangle_mesh
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
__date__ = '$Date: 2008/28/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCraftedText(fileName, text='', repository=None):
	'Widen the preface file or text.'
	return getCraftedTextFromText(archive.getTextIfEmpty(fileName, text), repository)

def getCraftedTextFromText(gcodeText, repository=None):
	'Widen the preface gcode text.'
	if gcodec.isProcedureDoneOrFileIsEmpty( gcodeText, 'widen'):
		return gcodeText
	if repository == None:
		repository = settings.getReadRepository( WidenRepository() )
	if not repository.activateWiden.value:
		return gcodeText
	return WidenSkein().getCraftedGcode(gcodeText, repository)

def getIntersectingWithinLoops(loop, loopList, outsetLoop):
	'Get the loops which are intersecting or which it is within.'
	intersectingWithinLoops = []
	for otherLoop in loopList:
		if getIsIntersectingWithinLoop(loop, otherLoop, outsetLoop):
			intersectingWithinLoops.append(otherLoop)
	return intersectingWithinLoops

def getIsIntersectingWithinLoop(loop, otherLoop, outsetLoop):
	'Determine if the loop is intersecting or is within the other loop.'
	if euclidean.isLoopIntersectingLoop(loop, otherLoop):
		return True
	return euclidean.isPathInsideLoop(otherLoop, loop) != euclidean.isPathInsideLoop(otherLoop, outsetLoop)

def getIsPointInsideALoop(loops, point):
	'Determine if a point is inside a loop of a loop list.'
	for loop in loops:
		if euclidean.isPointInsideLoop(loop, point):
			return True
	return False

def getNewRepository():
	'Get new repository.'
	return WidenRepository()

def getWidenedLoops(loop, loopList, outsetLoop, radius):
	'Get the widened loop.'
	intersectingWithinLoops = getIntersectingWithinLoops(loop, loopList, outsetLoop)
	if len(intersectingWithinLoops) < 1:
		return [loop]
	loopsUnified = boolean_solid.getLoopsUnion(radius, [[loop], intersectingWithinLoops])
	if len(loopsUnified) < 1:
		return [loop]
	return loopsUnified

def writeOutput(fileName, shouldAnalyze=True):
	'Widen the carving of a gcode file.'
	skeinforge_craft.writeChainTextWithNounMessage(fileName, 'widen', shouldAnalyze)


class WidenRepository:
	'A class to handle the widen settings.'
	def __init__(self):
		'Set the default settings, execute title & settings fileName.'
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.widen.html', self)
		self.fileNameInput = settings.FileNameInput().getFromFileName(
			fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Widen', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute(
			'http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Widen')
		self.activateWiden = settings.BooleanSetting().getFromValue('Activate Widen', self, False)
		self.widenWidthOverEdgeWidth = settings.IntSpin().getFromValue(2, 'Widen Width over Edge Width (ratio):', self, 4, 2)
		self.executeTitle = 'Widen'

	def execute(self):
		'Widen button has been clicked.'
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(
			self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class WidenSkein:
	'A class to widen a skein of extrusions.'
	def __init__(self):
		self.boundary = None
		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.layerCount = settings.LayerCount()
		self.lineIndex = 0
		self.loopLayer = None

	def addWiden(self, loopLayer):
		'Add widen to the layer.'
		triangle_mesh.sortLoopsInOrderOfArea(False, loopLayer.loops)
		widdershinsLoops = []
		clockwiseInsetLoops = []
		for loopIndex in xrange(len(loopLayer.loops)):
			loop = loopLayer.loops[loopIndex]
			if euclidean.isWiddershins(loop):
				otherLoops = loopLayer.loops[: loopIndex] + loopLayer.loops[loopIndex + 1 :]
				leftPoint = euclidean.getLeftPoint(loop)
				if getIsPointInsideALoop(otherLoops, leftPoint):
					self.distanceFeedRate.addGcodeFromLoop(loop, loopLayer.z)
				else:
					widdershinsLoops.append(loop)
			else:
#				clockwiseInsetLoop = intercircle.getLargestInsetLoopFromLoop(loop, self.widenEdgeWidth)
#				clockwiseInsetLoop.reverse()
#				clockwiseInsetLoops.append(clockwiseInsetLoop)
				clockwiseInsetLoops += intercircle.getInsetLoopsFromLoop(loop, self.widenEdgeWidth)
				self.distanceFeedRate.addGcodeFromLoop(loop, loopLayer.z)
		for widdershinsLoop in widdershinsLoops:
			outsetLoop = intercircle.getLargestInsetLoopFromLoop(widdershinsLoop, -self.widenEdgeWidth)
			for widenedLoop in getWidenedLoops(widdershinsLoop, clockwiseInsetLoops, outsetLoop, self.lessThanHalfEdgeWidth):
				self.distanceFeedRate.addGcodeFromLoop(widenedLoop, loopLayer.z)

	def getCraftedGcode(self, gcodeText, repository):
		'Parse gcode text and store the widen gcode.'
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
				self.distanceFeedRate.addTagBracketedProcedure('widen')
			elif firstWord == '(<crafting>)':
				self.distanceFeedRate.addLine(line)
				return
			elif firstWord == '(<edgeWidth>':
				self.edgeWidth = float(splitLine[1])
				self.widenEdgeWidth = float(self.repository.widenWidthOverEdgeWidth.value) * self.edgeWidth
				self.lessThanHalfEdgeWidth = 0.49 * self.edgeWidth
			self.distanceFeedRate.addLine(line)

	def parseLine(self, line):
		'Parse a gcode line and add it to the widen skein.'
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if firstWord == '(<boundaryPoint>':
			location = gcodec.getLocationFromSplitLine(None, splitLine)
			self.boundary.append(location.dropAxis())
		elif firstWord == '(<layer>':
			self.layerCount.printProgressIncrement('widen')
			self.loopLayer = euclidean.LoopLayer(float(splitLine[1]))
			self.distanceFeedRate.addLine(line)
		elif firstWord == '(</layer>)':
			self.addWiden( self.loopLayer )
			self.loopLayer = None
		elif firstWord == '(<nestedRing>)':
			self.boundary = []
			self.loopLayer.loops.append( self.boundary )
		if self.loopLayer == None:
			self.distanceFeedRate.addLine(line)


def main():
	'Display the widen dialog.'
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == '__main__':
	main()
