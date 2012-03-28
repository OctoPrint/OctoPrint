"""
This page is in the table of contents.
Chop is a script to chop a shape into svg slice layers.

==Settings==
===Add Layer Template to SVG===
Default is on.

When selected, the layer template will be added to the svg output, which adds javascript control boxes.  So 'Add Layer Template to SVG' should be selected when the svg will be viewed in a browser.

When off, no controls will be added, the svg output will only include the fabrication paths.  So 'Add Layer Template to SVG' should be deselected when the svg will be used by other software, like Inkscape.

===Add Extra Top Layer if Necessary===
Default is on.

When selected, chop will add an extra layer at the very top of the object if the top of the object is more than half the layer height above the first slice.  This is so the cutting tool doesn't cut too deeply through the top of the object on its first pass.

===Extra Decimal Places===
Default is two.

Defines the number of extra decimal places export will output compared to the number of decimal places in the layer height.  The higher the 'Extra Decimal Places', the more significant figures the output numbers will have.

===Import Coarseness===
Default is one.

When a triangle mesh has holes in it, the triangle mesh slicer switches over to a slow algorithm that spans gaps in the mesh.  The higher the 'Import Coarseness' setting, the wider the gaps in the mesh it will span.  An import coarseness of one means it will span gaps of the edge width.

===Layer Height===
Default is 0.4 mm.

Defines the height of the layer, this is the most important chop setting.

===Layers===
Chop slices from top to bottom.  To get only the bottom layer, set the "Layers From" to minus one.  The 'Layers From' until 'Layers To' range is a python slice.

====Layers From====
Default is zero.

Defines the index of the top layer that will be chopped.  If the 'Layers From' is the default zero, the carving will start from the top layer.  If the 'Layers From' index is negative, then the carving will start from the 'Layers From' index above the bottom layer.

====Layers To====
Default is a huge number, which will be limited to the highest index number.

Defines the index of the bottom layer that will be chopped.  If the 'Layers To' index is a huge number like the default, the carving will go to the bottom of the model.  If the 'Layers To' index is negative, then the carving will go to the 'Layers To' index above the bottom layer.

===Mesh Type===
Default is 'Correct Mesh'.

====Correct Mesh====
When selected, the mesh will be accurately chopped, and if a hole is found, chop will switch over to the algorithm that spans gaps.

====Unproven Mesh====
When selected, chop will use the gap spanning algorithm from the start.  The problem with the gap spanning algothm is that it will span gaps, even if there is not actually a gap in the model.

===Perimeter Width===
Default is 2 mm.

Defines the width of the edge.

===SVG Viewer===
Default is webbrowser.

If the 'SVG Viewer' is set to the default 'webbrowser', the scalable vector graphics file will be sent to the default browser to be opened.  If the 'SVG Viewer' is set to a program name, the scalable vector graphics file will be sent to that program to be opened.

==Examples==
The following examples chop the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and chop.py.

> python chop.py
This brings up the chop dialog.

> python chop.py Screw Holder Bottom.stl
The chop tool is parsing the file:
Screw Holder Bottom.stl
..
The chop tool has created the file:
.. Screw Holder Bottom_chop.svg

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
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import settings
from fabmetheus_utilities import svg_writer
from skeinforge_application.skeinforge_utilities import skeinforge_polyfile
from skeinforge_application.skeinforge_utilities import skeinforge_profile
import math
import os
import sys
import time


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCraftedText( fileName, gcodeText = '', repository=None):
	"Get chopped text."
	if fileName.endswith('.svg'):
		gcodeText = archive.getTextIfEmpty(fileName, gcodeText)
		if gcodec.isProcedureDoneOrFileIsEmpty( gcodeText, 'chop'):
			return gcodeText
	carving = svg_writer.getCarving(fileName)
	if carving == None:
		return ''
	if repository == None:
		repository = ChopRepository()
		settings.getReadRepository(repository)
	return ChopSkein().getCarvedSVG( carving, fileName, repository )

def getNewRepository():
	'Get new repository.'
	return ChopRepository()

def writeOutput(fileName, shouldAnalyze=True):
	"Chop a GNU Triangulated Surface file.  If no fileName is specified, chop the first GNU Triangulated Surface file in this folder."
	startTime = time.time()
	print('File ' + archive.getSummarizedFileName(fileName) + ' is being chopped.')
	repository = ChopRepository()
	settings.getReadRepository(repository)
	chopGcode = getCraftedText( fileName, '', repository )
	if chopGcode == '':
		return
	suffixFileName = fileName[ : fileName.rfind('.') ] + '_chop.svg'
	suffixDirectoryName = os.path.dirname(suffixFileName)
	suffixReplacedBaseName = os.path.basename(suffixFileName).replace(' ', '_')
	suffixFileName = os.path.join( suffixDirectoryName, suffixReplacedBaseName )
	archive.writeFileText( suffixFileName, chopGcode )
	print('The chopped file is saved as ' + archive.getSummarizedFileName(suffixFileName) )
	print('It took %s to chop the file.' % euclidean.getDurationString( time.time() - startTime ) )
	if shouldAnalyze:
		settings.openSVGPage( suffixFileName, repository.svgViewer.value )


class ChopRepository:
	"A class to handle the chop settings."
	def __init__(self):
		"Set the default settings, execute title & settings fileName."
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.chop.html', self )
		self.fileNameInput = settings.FileNameInput().getFromFileName( fabmetheus_interpret.getTranslatorFileTypeTuples(), 'Open File to be Chopped', self, '')
		self.addExtraTopLayerIfNecessary = settings.BooleanSetting().getFromValue('Add Extra Top Layer if Necessary', self, True )
		self.addLayerTemplateToSVG = settings.BooleanSetting().getFromValue('Add Layer Template to SVG', self, True)
		self.edgeWidth = settings.FloatSpin().getFromValue( 0.4, 'Edge Width (mm):', self, 4.0, 2.0 )
		self.extraDecimalPlaces = settings.FloatSpin().getFromValue(0.0, 'Extra Decimal Places (float):', self, 3.0, 2.0)
		self.importCoarseness = settings.FloatSpin().getFromValue( 0.5, 'Import Coarseness (ratio):', self, 2.0, 1.0 )
		self.layerHeight = settings.FloatSpin().getFromValue( 0.1, 'Layer Height (mm):', self, 1.0, 0.4 )
		self.layersFrom = settings.IntSpin().getFromValue( 0, 'Layers From (index):', self, 20, 0 )
		self.layersTo = settings.IntSpin().getSingleIncrementFromValue( 0, 'Layers To (index):', self, 912345678, 912345678 )
		self.meshTypeLabel = settings.LabelDisplay().getFromName('Mesh Type: ', self, )
		importLatentStringVar = settings.LatentStringVar()
		self.correctMesh = settings.Radio().getFromRadio( importLatentStringVar, 'Correct Mesh', self, True )
		self.unprovenMesh = settings.Radio().getFromRadio( importLatentStringVar, 'Unproven Mesh', self, False )
		self.svgViewer = settings.StringSetting().getFromValue('SVG Viewer:', self, 'webbrowser')
		settings.LabelSeparator().getFromRepository(self)
		self.executeTitle = 'Chop'

	def execute(self):
		"Chop button has been clicked."
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypes(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class ChopSkein:
	"A class to chop a carving."
	def addExtraTopLayerIfNecessary( self, carving, layerHeight, loopLayers ):
		"Add extra top layer if necessary."
		topRotatedBoundaryLayer = loopLayers[-1]
		cuttingSafeHeight = topRotatedBoundaryLayer.z + 0.5001 * layerHeight
		if cuttingSafeHeight > carving.getCarveCornerMaximum().z:
			return
		extraTopRotatedBoundaryLayer = topRotatedBoundaryLayer.getCopyAtZ( topRotatedBoundaryLayer.z + layerHeight )
		loopLayers.append( extraTopRotatedBoundaryLayer )

	def getCarvedSVG( self, carving, fileName, repository ):
		"Parse gnu triangulated surface text and store the chopped gcode."
		layerHeight = repository.layerHeight.value
		edgeWidth = repository.edgeWidth.value
		carving.setCarveLayerHeight( layerHeight )
		importRadius = 0.5 * repository.importCoarseness.value * abs(edgeWidth)
		carving.setCarveImportRadius(max(importRadius, 0.001 * layerHeight))
		carving.setCarveIsCorrectMesh( repository.correctMesh.value )
		loopLayers = carving.getCarveBoundaryLayers()
		if len( loopLayers ) < 1:
			print('Warning, there are no slices for the model, this could be because the model is too small for the Layer Height.')
			return ''
		if repository.addExtraTopLayerIfNecessary.value:
			self.addExtraTopLayerIfNecessary( carving, layerHeight, loopLayers )
		loopLayers.reverse()
		layerHeight = carving.getCarveLayerHeight()
		decimalPlacesCarried = euclidean.getDecimalPlacesCarried(repository.extraDecimalPlaces.value, layerHeight)
		svgWriter = svg_writer.SVGWriter(
			repository.addLayerTemplateToSVG.value,
			carving.getCarveCornerMaximum(),
			carving.getCarveCornerMinimum(),
			decimalPlacesCarried,
			carving.getCarveLayerHeight(),
			edgeWidth)
		truncatedRotatedBoundaryLayers = svg_writer.getTruncatedRotatedBoundaryLayers(loopLayers, repository)
		return svgWriter.getReplacedSVGTemplate( fileName, truncatedRotatedBoundaryLayers, 'chop', carving.getFabmetheusXML())


def main():
	"Display the chop dialog."
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == "__main__":
	main()
