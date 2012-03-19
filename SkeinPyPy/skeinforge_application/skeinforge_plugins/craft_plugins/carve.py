"""
This page is in the table of contents.
Carve is the most important plugin to define for your printer.

It carves a shape into svg slice layers.  It also sets the layer height and edge width for the rest of the tool chain.

The carve manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Carve

On the Arcol Blog a method of deriving the layer height is posted.  That article "Machine Calibrating" is at:
http://blog.arcol.hu/?p=157

==Settings==
===Add Layer Template to SVG===
Default is on.

When selected, the layer template will be added to the svg output, which adds javascript control boxes.  So 'Add Layer Template to SVG' should be selected when the svg will be viewed in a browser.

When off, no controls will be added, the svg output will only include the fabrication paths.  So 'Add Layer Template to SVG' should be deselected when the svg will be used by other software, like Inkscape.

===Edge Width over Height===
Default is 1.8.

Defines the ratio of the extrusion edge width to the layer height.  This parameter tells skeinforge how wide the edge wall is expected to be in relation to the layer height.  Default value of 1.8 for the default layer height of 0.4 states that a single filament edge wall should be 0.4 mm * 1.8 = 0.72 mm wide.  The higher the value the more the edge will be inset.  A ratio of one means the extrusion is a circle, the default ratio of 1.8 means the extrusion is a wide oval.

This is an important value because if you are calibrating your machine you need to ensure that the speed of the head and the extrusion rate in combination produce a wall that is 'Layer Height' * 'Edge Width over Height' wide. To start with 'Edge Width over Height' is probably best left at the default of 1.8 and the extrusion rate adjusted to give the correct calculated wall thickness.

Adjustment is in the 'Speed' section with 'Feed Rate' controlling speed of the head in X & Y and 'Flow Rate' controlling the extrusion rate.  Initially it is probably easier to start adjusting the flow rate only a little at a time until you get a single filament of the correct width. If you change too many parameters at once you can get in a right mess.

===Extra Decimal Places===
Default is two.

Defines the number of extra decimal places export will output compared to the number of decimal places in the layer height.  The higher the 'Extra Decimal Places', the more significant figures the output numbers will have.

===Import Coarseness===
Default is one.

When a triangle mesh has holes in it, the triangle mesh slicer switches over to a slow algorithm that spans gaps in the mesh.  The higher the 'Import Coarseness' setting, the wider the gaps in the mesh it will span.  An import coarseness of one means it will span gaps of the edge width.

===Layer Height===
Default is 0.4 mm.

Defines the the height of the layers skeinforge will cut your object into, in the z direction.  This is the most important carve setting, many values in the toolchain are derived from the layer height.

For a 0.5 mm nozzle usable values are 0.3 mm to 0.5 mm.  Note; if you are using thinner layers make sure to adjust the extrusion speed as well.

===Layers===
Carve slices from bottom to top.  To get a single layer, set the "Layers From" to zero and the "Layers To" to one.  The 'Layers From' until 'Layers To' range is a python slice.

====Layers From====
Default is zero.

Defines the index of the bottom layer that will be carved.  If the 'Layers From' is the default zero, the carving will start from the lowest layer.  If the 'Layers From' index is negative, then the carving will start from the 'Layers From' index below the top layer.

For example if your object is 5 mm tall and your layer thicknes is 1 mm if you set layers from to 3 you will ignore the first 3 mm and start from 3 mm.

====Layers To====
Default is a huge number, which will be limited to the highest index layer.

Defines the index of the top layer that will be carved.  If the 'Layers To' index is a huge number like the default, the carving will go to the top of the model.  If the 'Layers To' index is negative, then the carving will go to the 'Layers To' index below the top layer.

This is the same as layers from, only it defines when to end the generation of gcode.

===Mesh Type===
Default is 'Correct Mesh'.

====Correct Mesh====
When selected, the mesh will be accurately carved, and if a hole is found, carve will switch over to the algorithm that spans gaps.

====Unproven Mesh====
When selected, carve will use the gap spanning algorithm from the start.  The problem with the gap spanning algothm is that it will span gaps, even if there is not actually a gap in the model.

===SVG Viewer===
Default is webbrowser.

If the 'SVG Viewer' is set to the default 'webbrowser', the scalable vector graphics file will be sent to the default browser to be opened.  If the 'SVG Viewer' is set to a program name, the scalable vector graphics file will be sent to that program to be opened.

==Examples==
The following examples carve the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and carve.py.

> python carve.py
This brings up the carve dialog.

> python carve.py Screw Holder Bottom.stl
The carve tool is parsing the file:
Screw Holder Bottom.stl
..
The carve tool has created the file:
.. Screw Holder Bottom_carve.svg

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
from fabmetheus_utilities.vector3 import Vector3
import math
import os
import sys
import time
import math


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCraftedText( fileName, gcodeText = '', repository=None):
	"Get carved text."
	if fileName.endswith('.svg'):
		gcodeText = archive.getTextIfEmpty(fileName, gcodeText)
		if gcodec.isProcedureDoneOrFileIsEmpty( gcodeText, 'carve'):
			return gcodeText
	carving = svg_writer.getCarving(fileName)
	if carving == None:
		return ''
	if repository == None:
		repository = CarveRepository()
		settings.getReadRepository(repository)
	return CarveSkein().getCarvedSVG( carving, fileName, repository )

def getNewRepository():
	'Get new repository.'
	return CarveRepository()

def writeOutput(fileName, shouldAnalyze=True):
	"Carve a GNU Triangulated Surface file."
	startTime = time.time()
	print('File ' + archive.getSummarizedFileName(fileName) + ' is being carved.')
	repository = CarveRepository()
	settings.getReadRepository(repository)
	carveGcode = getCraftedText(fileName, '', repository)
	if carveGcode == '':
		return
	suffixFileName = archive.getFilePathWithUnderscoredBasename(fileName, '_carve.svg')
	archive.writeFileText(suffixFileName, carveGcode)
	print('The carved file is saved as ' + archive.getSummarizedFileName(suffixFileName))
	print('It took %s to carve the file.' % euclidean.getDurationString(time.time() - startTime))
	if shouldAnalyze:
		settings.openSVGPage(suffixFileName, repository.svgViewer.value)


class CarveRepository:
	"A class to handle the carve settings."
	def __init__(self):
		"Set the default settings, execute title & settings fileName."
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.carve.html', self )
		self.fileNameInput = settings.FileNameInput().getFromFileName( fabmetheus_interpret.getTranslatorFileTypeTuples(), 'Open File for Carve', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Carve')
		self.addLayerTemplateToSVG = settings.BooleanSetting().getFromValue('Add Layer Template to SVG', self, True)
		self.edgeWidth = settings.FloatSpin().getFromValue( 0.1, 'Edge Width (mm):', self, 2.2, 0.4 )
		self.extraDecimalPlaces = settings.FloatSpin().getFromValue(0.0, 'Extra Decimal Places (float):', self, 3.0, 2.0)
		self.importCoarseness = settings.FloatSpin().getFromValue( 0.5, 'Import Coarseness (ratio):', self, 2.0, 1.0 )
		self.layerHeight = settings.FloatSpin().getFromValue( 0.1, 'Layer Height (mm):', self, 1.0, 0.2 )
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Layers -', self )
		self.layersFrom = settings.IntSpin().getFromValue( 0, 'Layers From (index):', self, 20, 0 )
		self.layersTo = settings.IntSpin().getSingleIncrementFromValue( 0, 'Layers To (index):', self, 912345678, 912345678 )
		settings.LabelSeparator().getFromRepository(self)
		self.meshTypeLabel = settings.LabelDisplay().getFromName('Mesh Type: ', self )
		importLatentStringVar = settings.LatentStringVar()
		self.correctMesh = settings.Radio().getFromRadio( importLatentStringVar, 'Correct Mesh', self, True )
		self.unprovenMesh = settings.Radio().getFromRadio( importLatentStringVar, 'Unproven Mesh', self, False )
		self.svgViewer = settings.StringSetting().getFromValue('SVG Viewer:', self, 'webbrowser')
		settings.LabelSeparator().getFromRepository(self)
		self.executeTitle = 'Carve'

		self.flipX = settings.BooleanSetting().getFromValue('FlipX', self, False)
		self.flipY = settings.BooleanSetting().getFromValue('FlipY', self, False)
		self.flipZ = settings.BooleanSetting().getFromValue('FlipZ', self, False)
		self.scale = settings.FloatSpin().getFromValue( 0.1, 'Scale', self, 10.0, 1.0 )
		self.rotate = settings.FloatSpin().getFromValue( -180.0, 'Rotate', self, 180.0, 0.0 )


	def execute(self):
		"Carve button has been clicked."
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypes(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class CarveSkein:
	"A class to carve a carving."
	def getCarvedSVG(self, carving, fileName, repository):
		"Parse gnu triangulated surface text and store the carved gcode."

		scale = repository.scale.value
		rotate = repository.rotate.value / 180 * math.pi
		scaleX = scale
		scaleY = scale
		scaleZ = scale
		if repository.flipX.value == True:
			scaleX = -scaleX
		if repository.flipY.value == True:
			scaleY = -scaleY
		if repository.flipZ.value == True:
			scaleZ = -scaleZ
		mat00 = math.cos(rotate) * scaleX
		mat01 =-math.sin(rotate) * scaleY
		mat10 = math.sin(rotate) * scaleX
		mat11 = math.cos(rotate) * scaleY

		minZ = carving.getMinimumZ()
		minSize = carving.getCarveCornerMinimum()
		maxSize = carving.getCarveCornerMaximum()
		for v in carving.vertexes:
			v.z -= minZ
			v.x -= minSize.x + (maxSize.x - minSize.x) / 2
			v.y -= minSize.y + (maxSize.y - minSize.y) / 2
			#v.x += self.machineCenter.x
			#v.y += self.machineCenter.y
		
		for i in xrange(0, len(carving.vertexes)):
			carving.vertexes[i] = Vector3(
				carving.vertexes[i].x * mat00 + carving.vertexes[i].y * mat01,
				carving.vertexes[i].x * mat10 + carving.vertexes[i].y * mat11,
				carving.vertexes[i].z * scaleZ)

		layerHeight = repository.layerHeight.value
		edgeWidth = repository.edgeWidth.value
		carving.setCarveLayerHeight(layerHeight)
		importRadius = 0.5 * repository.importCoarseness.value * abs(edgeWidth)
		carving.setCarveImportRadius(max(importRadius, 0.001 * layerHeight))
		carving.setCarveIsCorrectMesh(repository.correctMesh.value)
		loopLayers = carving.getCarveBoundaryLayers()
		if len(loopLayers) < 1:
			print('Warning, there are no slices for the model, this could be because the model is too small for the Layer Height.')
			return ''
		layerHeight = carving.getCarveLayerHeight()
		decimalPlacesCarried = euclidean.getDecimalPlacesCarried(repository.extraDecimalPlaces.value, layerHeight)
		edgeWidth = repository.edgeWidth.value
		svgWriter = svg_writer.SVGWriter(
			repository.addLayerTemplateToSVG.value,
			carving.getCarveCornerMaximum(),
			carving.getCarveCornerMinimum(),
			decimalPlacesCarried,
			carving.getCarveLayerHeight(),
			edgeWidth)
		truncatedRotatedBoundaryLayers = svg_writer.getTruncatedRotatedBoundaryLayers(loopLayers, repository)
		return svgWriter.getReplacedSVGTemplate(fileName, truncatedRotatedBoundaryLayers, 'carve', carving.getFabmetheusXML())


def main():
	"Display the carve dialog."
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == "__main__":
	main()
