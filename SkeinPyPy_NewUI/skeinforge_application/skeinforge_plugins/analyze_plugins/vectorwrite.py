"""
This page is in the table of contents.
Vectorwrite is a very interesting analyze plugin that will create an SVG vector image for each layer that you can then use in some other printing system. 

The Scalable Vector Graphics file can be opened by an SVG viewer or an SVG capable browser like Mozilla:
http://www.mozilla.com/firefox/

The vectorwrite manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Vectorwrite

==Operation==
The default 'Activate Vectorwrite' checkbox is off.  When it is on, the functions described below will work when called from the skeinforge toolchain, when it is off, the functions will not be called from the toolchain.  The functions will still be called, whether or not the 'Activate Vectorwrite' checkbox is on, when vectorwrite is run directly.

==Settings==
===Add Loops===
Default is on.

If 'Add Loops' is selected, the loops will be added in yellow to the the scalable vector graphics output.

===Add Paths===
Default is on.

If 'Add Paths' is selected, the paths will be added in pink to the the scalable vector graphics output.

===Add Perimeters===
Default is on.

If 'Add Perimeters' is selected, the edges will be added to the the scalable vector graphics output.  The outer edges will be red and the inner edges will be orange.

===Layers===
====Layers From====
Default is zero.

The "Layers From" is the index of the bottom layer that will be displayed.  If the layer from is the default zero, the display will start from the lowest layer.  If the the layer from index is negative, then the display will start from the layer from index below the top layer.

====Layers To====
Default is a huge number, which will be limited to the highest index layer.

The "Layers To" is the index of the top layer that will be displayed.  If the layer to index is a huge number like the default, the display will go to the top of the model, at least until we model habitats:)  If the layer to index is negative, then the display will go to the layer to index below the top layer.  The layer from until layer to index is a python slice.

===SVG Viewer===
Default is webbrowser.

If the 'SVG Viewer' is set to the default 'webbrowser', the scalable vector graphics file will be sent to the default browser to be opened.  If the 'SVG Viewer' is set to a program name, the scalable vector graphics file will be sent to that program to be opened.

==Examples==
Below are examples of vectorwrite being used.  These examples are run in a terminal in the folder which contains Screw Holder_penultimate.gcode and vectorwrite.py.

> python vectorwrite.py
This brings up the vectorwrite dialog.

> python vectorwrite.py Screw Holder_penultimate.gcode
The vectorwrite file is saved as Screw_Holder_penultimate_vectorwrite.svg

"""


from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import settings
from fabmetheus_utilities import svg_writer
from skeinforge_application.skeinforge_utilities import skeinforge_polyfile
from skeinforge_application.skeinforge_utilities import skeinforge_profile
import cStringIO
import os
import sys
import time

__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Nophead <http://hydraraptor.blogspot.com/>'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getNewRepository():
	'Get new repository.'
	return VectorwriteRepository()

def getWindowAnalyzeFile(fileName):
	'Write scalable vector graphics for a gcode file.'
	gcodeText = archive.getFileText(fileName)
	return getWindowAnalyzeFileGivenText(fileName, gcodeText)

def getWindowAnalyzeFileGivenText( fileName, gcodeText, repository=None):
	'Write scalable vector graphics for a gcode file given the settings.'
	if gcodeText == '':
		return None
	if repository == None:
		repository = settings.getReadRepository( VectorwriteRepository() )
	startTime = time.time()
	vectorwriteGcode = VectorwriteSkein().getCarvedSVG( fileName, gcodeText, repository )
	if vectorwriteGcode == '':
		return None
	suffixFileName = fileName[ : fileName.rfind('.') ] + '_vectorwrite.svg'
	suffixDirectoryName = os.path.dirname(suffixFileName)
	suffixReplacedBaseName = os.path.basename(suffixFileName).replace(' ', '_')
	suffixFileName = os.path.join( suffixDirectoryName, suffixReplacedBaseName )
	archive.writeFileText( suffixFileName, vectorwriteGcode )
	print('The vectorwrite file is saved as ' + archive.getSummarizedFileName(suffixFileName) )
	print('It took %s to vectorwrite the file.' % euclidean.getDurationString( time.time() - startTime ) )
	settings.openSVGPage( suffixFileName, repository.svgViewer.value )

def writeOutput(fileName, fileNamePenultimate, fileNameSuffix, filePenultimateWritten, gcodeText=''):
	'Write scalable vector graphics for a skeinforge gcode file, if activate vectorwrite is selected.'
	repository = settings.getReadRepository( VectorwriteRepository() )
	if not repository.activateVectorwrite.value:
		return
	gcodeText = archive.getTextIfEmpty( fileNameSuffix, gcodeText )
	getWindowAnalyzeFileGivenText( fileNameSuffix, gcodeText, repository )


class SVGWriterVectorwrite( svg_writer.SVGWriter ):
	'A class to vectorwrite a carving.'
	def addPaths( self, colorName, paths, transformString ):
		'Add paths to the output.'
		pathString = ''
		for path in paths:
			pathString += self.getSVGStringForPath(path) + ' '
		if len( pathString ) < 1:
			return
		pathElementNodeCopy = self.pathElementNode.getCopy('', self.pathElementNode.parentNode )
		pathCopyDictionary = pathElementNodeCopy.attributes
		pathCopyDictionary['d'] = pathString[ : - 1 ]
		pathCopyDictionary['fill'] = 'none'
		pathCopyDictionary['stroke'] = colorName
		pathCopyDictionary['transform'] = transformString

	def addLoopLayerToOutput( self, layerIndex, threadLayer ):
		'Add rotated boundary layer to the output.'
		settings.printProgress(self.layerIndex, 'vectorwrite')
		self.addLayerBegin( layerIndex, threadLayer )
		transformString = self.getTransformString()
		self.pathDictionary['d'] = self.getSVGStringForLoops( threadLayer.boundaryLoops )
		self.pathDictionary['transform'] = transformString
		self.addPaths('#fa0', threadLayer.innerPerimeters, transformString ) #orange
		self.addPaths('#ff0', threadLayer.loops, transformString ) #yellow
		self.addPaths('#f00', threadLayer.outerPerimeters, transformString ) #red
		self.addPaths('#f5c', threadLayer.paths, transformString ) #light violetred


class ThreadLayer:
	'Threads with a z.'
	def __init__( self, z ):
		self.boundaryLoops = []
		self.innerPerimeters = []
		self.loops = []
		self.outerPerimeters = []
		self.paths = []
		self.z = z

	def __repr__(self):
		'Get the string representation of this loop layer.'
		return str(self.__dict__)

	def getTotalNumberOfThreads(self):
		'Get the total number of loops, paths and edges.'
		return len(self.boundaryLoops) + len(self.innerPerimeters) + len(self.loops) + len(self.outerPerimeters) + len(self.paths)

	def maximize(self, vector3):
		'Maximize the vector3 over the loops, paths and edges.'
		pointComplex = vector3.dropAxis()
		pointComplex = euclidean.getMaximum(euclidean.getMaximumByComplexPaths(self.boundaryLoops), pointComplex)
		pointComplex = euclidean.getMaximum(euclidean.getMaximumByComplexPaths(self.innerPerimeters), pointComplex)
		pointComplex = euclidean.getMaximum(euclidean.getMaximumByComplexPaths(self.loops), pointComplex)
		pointComplex = euclidean.getMaximum(euclidean.getMaximumByComplexPaths(self.outerPerimeters), pointComplex)
		pointComplex = euclidean.getMaximum(euclidean.getMaximumByComplexPaths(self.paths), pointComplex)
		vector3.setToXYZ(pointComplex.real, pointComplex.imag, max(self.z, vector3.z))

	def minimize(self, vector3):
		'Minimize the vector3 over the loops, paths and edges.'
		pointComplex = vector3.dropAxis()
		pointComplex = euclidean.getMinimum(euclidean.getMinimumByComplexPaths(self.boundaryLoops), pointComplex)
		pointComplex = euclidean.getMinimum(euclidean.getMinimumByComplexPaths(self.innerPerimeters), pointComplex)
		pointComplex = euclidean.getMinimum(euclidean.getMinimumByComplexPaths(self.loops), pointComplex)
		pointComplex = euclidean.getMinimum(euclidean.getMinimumByComplexPaths(self.outerPerimeters), pointComplex)
		pointComplex = euclidean.getMinimum(euclidean.getMinimumByComplexPaths(self.paths), pointComplex)
		vector3.setToXYZ(pointComplex.real, pointComplex.imag, min(self.z, vector3.z))


class VectorwriteRepository:
	'A class to handle the vectorwrite settings.'
	def __init__(self):
		'Set the default settings, execute title & settings fileName.'
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.analyze_plugins.vectorwrite.html', self )
		self.activateVectorwrite = settings.BooleanSetting().getFromValue('Activate Vectorwrite', self, False )
		self.fileNameInput = settings.FileNameInput().getFromFileName( [ ('Gcode text files', '*.gcode') ], 'Open File to Write Vector Graphics for', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Vectorwrite')
		self.addLoops = settings.BooleanSetting().getFromValue('Add Loops', self, True)
		self.addPaths = settings.BooleanSetting().getFromValue('Add Paths', self, True)
		self.addPerimeters = settings.BooleanSetting().getFromValue('Add Perimeters', self, True)
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Layers -', self )
		self.layersFrom = settings.IntSpin().getFromValue( 0, 'Layers From (index):', self, 20, 0 )
		self.layersTo = settings.IntSpin().getSingleIncrementFromValue( 0, 'Layers To (index):', self, 912345678, 912345678 )
		settings.LabelSeparator().getFromRepository(self)
		self.svgViewer = settings.StringSetting().getFromValue('SVG Viewer:', self, 'webbrowser')
		settings.LabelSeparator().getFromRepository(self)
		self.executeTitle = 'Vectorwrite'

	def execute(self):
		'Write button has been clicked.'
		fileNames = skeinforge_polyfile.getFileOrGcodeDirectory( self.fileNameInput.value, self.fileNameInput.wasCancelled )
		for fileName in fileNames:
			getWindowAnalyzeFile(fileName)


class VectorwriteSkein:
	'A class to vectorwrite a carving.'
	def __init__(self):
		'Initialize.'
		self.layerCount = settings.LayerCount()

	def addLoopLayer(self, z):
		'Add loop layer.'
		self.layerCount.printProgressIncrement('vectorwrite')
		self.threadLayer = ThreadLayer(z)
		self.threadLayers.append(self.threadLayer)

	def addToLoops(self):
		'Add the thread to the loops.'
		self.isLoop = False
		if len(self.thread) < 1:
			return
		if self.repository.addLoops.value:
			self.threadLayer.loops.append(self.thread)
		self.thread = []

	def addToPerimeters(self):
		'Add the thread to the edges.'
		self.isEdge = False
		if len(self.thread) < 1:
			return
		if self.repository.addPerimeters.value:
			if self.isOuter:
				self.threadLayer.outerPerimeters.append(self.thread)
			else:
				self.threadLayer.innerPerimeters.append(self.thread)
		self.thread = []

	def getCarvedSVG(self, fileName, gcodeText, repository):
		'Parse gnu triangulated surface text and store the vectorwrite gcode.'
		cornerMaximum = Vector3(-987654321.0, -987654321.0, -987654321.0)
		cornerMinimum = Vector3(987654321.0, 987654321.0, 987654321.0)
		self.boundaryLoop = None
		self.extruderActive = False
		self.isEdge = False
		self.isLoop = False
		self.isOuter = False
		self.lines = archive.getTextLines(gcodeText)
		self.oldLocation = None
		self.thread = []
		self.threadLayers = []
		self.repository = repository
		self.parseInitialization()
		for line in self.lines[self.lineIndex :]:
			self.parseLine(line)
		self.removeEmptyLayers()
		for threadLayer in self.threadLayers:
			threadLayer.maximize(cornerMaximum)
			threadLayer.minimize(cornerMinimum)
		halfLayerThickness = 0.5 * self.layerHeight
		cornerMaximum.z += halfLayerThickness
		cornerMinimum.z -= halfLayerThickness
		svgWriter = SVGWriterVectorwrite(
			True, cornerMaximum, cornerMinimum, self.decimalPlacesCarried, self.layerHeight, self.edgeWidth)
		return svgWriter.getReplacedSVGTemplate(fileName, 'vectorwrite', self.threadLayers)

	def getCarveLayerHeight(self):
		'Get the layer height.'
		return self.layerHeight

	def linearMove( self, splitLine ):
		'Get statistics for a linear move.'
		location = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
		if self.extruderActive:
			if len(self.thread) == 0:
				self.thread = [ self.oldLocation.dropAxis() ]
			self.thread.append(location.dropAxis())
		self.oldLocation = location

	def parseInitialization(self):
		'Parse gcode initialization and store the parameters.'
		for self.lineIndex in xrange(len(self.lines)):
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			if firstWord == '(<decimalPlacesCarried>':
				self.decimalPlacesCarried = int(splitLine[1])
			elif firstWord == '(<layerHeight>':
				self.layerHeight = float(splitLine[1])
			elif firstWord == '(<crafting>)':
				return
			elif firstWord == '(<edgeWidth>':
				self.edgeWidth = float(splitLine[1])

	def parseLine(self, line):
		'Parse a gcode line and add it to the outset skein.'
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if firstWord == 'G1':
			self.linearMove(splitLine)
		elif firstWord == 'M101':
			self.extruderActive = True
		elif firstWord == 'M103':
			self.extruderActive = False
			if self.isLoop:
				self.addToLoops()
				return
			if self.isEdge:
				self.addToPerimeters()
				return
			if self.repository.addPaths.value:
				self.threadLayer.paths.append(self.thread)
			self.thread = []
		elif firstWord == '(</boundaryPerimeter>)':
			self.boundaryLoop = None
		elif firstWord == '(<boundaryPoint>':
			location = gcodec.getLocationFromSplitLine(None, splitLine)
			if self.boundaryLoop == None:
				self.boundaryLoop = []
				self.threadLayer.boundaryLoops.append( self.boundaryLoop )
			self.boundaryLoop.append(location.dropAxis())
		elif firstWord == '(<layer>':
			self.addLoopLayer(float(splitLine[1]))
		elif firstWord == '(</loop>)':
			self.addToLoops()
		elif firstWord == '(<loop>':
			self.isLoop = True
		elif firstWord == '(<edge>':
			self.isEdge = True
			self.isOuter = ( splitLine[1] == 'outer')
		elif firstWord == '(</edge>)':
			self.addToPerimeters()

	def removeEmptyLayers(self):
		'Remove empty layers.'
		for threadLayerIndex, threadLayer in enumerate(self.threadLayers):
			if threadLayer.getTotalNumberOfThreads() > 0:
				self.threadLayers = self.threadLayers[threadLayerIndex :]
				return


def main():
	'Display the vectorwrite dialog.'
	if len(sys.argv) > 1:
		getWindowAnalyzeFile(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == '__main__':
	main()
