#! /usr/bin/env python
"""
This page is in the table of contents.
Scale scales the carving to compensate for shrinkage after the extrusion has cooled.

The scale manual page is at:

http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Scale

It is best to only change the XY Plane Scale, because that does not affect other variables.  If you choose to change the Z Axis Scale, that increases the layer height so you must increase the feed rate in speed by the same amount and maybe some other variables which depend on layer height.

==Operation==
The default 'Activate Scale' checkbox is off.  When it is on, the functions described below will work, when it is off, nothing will be done.

==Settings==
===XY Plane Scale===
Default is 1.01.

Defines the amount the xy plane of the carving will be scaled.  The xy coordinates will be scaled, but the edge width is not changed, so this can be changed without affecting other variables.

===Z Axis Scale===
Default is one.

Defines the amount the z axis of the carving will be scaled.  The default is one because changing this changes many variables related to the layer height.  For example, the feedRate should be multiplied by the Z Axis Scale because the layers would be farther apart.

===SVG Viewer===
Default is webbrowser.

If the 'SVG Viewer' is set to the default 'webbrowser', the scalable vector graphics file will be sent to the default browser to be opened.  If the 'SVG Viewer' is set to a program name, the scalable vector graphics file will be sent to that program to be opened.

==Examples==
The following examples scale the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and scale.py.

> python scale.py
This brings up the scale dialog.

> python scale.py Screw Holder Bottom.stl
The scale tool is parsing the file:
Screw Holder Bottom.stl
..
The scale tool has created the file:
.. Screw Holder Bottom_scale.gcode

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from datetime import date
from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
from fabmetheus_utilities.svg_reader import SVGReader
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import settings
from fabmetheus_utilities import svg_writer
from fabmetheus_utilities import xml_simple_writer
from skeinforge_application.skeinforge_utilities import skeinforge_craft
from skeinforge_application.skeinforge_utilities import skeinforge_polyfile
from skeinforge_application.skeinforge_utilities import skeinforge_profile
import cStringIO
import os
import sys
import time


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCraftedText(fileName, svgText='', repository=None):
	"Scale and convert an svg file or svgText."
	return getCraftedTextFromText(fileName, archive.getTextIfEmpty(fileName, svgText), repository)

def getCraftedTextFromText(fileName, svgText, repository=None):
	"Scale and convert an svgText."
	if gcodec.isProcedureDoneOrFileIsEmpty(svgText, 'scale'):
		return svgText
	if repository == None:
		repository = settings.getReadRepository(ScaleRepository())
	if repository.activateScale.value:
		return ScaleSkein().getCraftedGcode(fileName, repository, svgText)
	return svgText

def getNewRepository():
	'Get new repository.'
	return ScaleRepository()

def setLoopLayerScale(loopLayer, xyPlaneScale, zAxisScale):
	"Set the slice element scale."
	for loop in loopLayer.loops:
		for pointIndex in xrange(len(loop)):
			loop[pointIndex] *= xyPlaneScale
	loopLayer.z *= zAxisScale

def writeOutput(fileName, shouldAnalyze=True):
	'Scale the carving.'
	skeinforge_craft.writeSVGTextWithNounMessage(fileName, ScaleRepository(), shouldAnalyze)


class ScaleRepository:
	"A class to handle the scale settings."
	def __init__(self):
		"Set the default settings, execute title & settings fileName."
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.scale.html', self )
		self.fileNameInput = settings.FileNameInput().getFromFileName(fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Scale', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Scale')
		self.activateScale = settings.BooleanSetting().getFromValue('Activate Scale', self, False)
		self.xyPlaneScale = settings.FloatSpin().getFromValue(0.99, 'XY Plane Scale (ratio):', self, 1.03, 1.01)
		self.zAxisScale = settings.FloatSpin().getFromValue(0.99, 'Z Axis Scale (ratio):', self, 1.02, 1.0)
		self.svgViewer = settings.StringSetting().getFromValue('SVG Viewer:', self, 'webbrowser')
		self.executeTitle = 'Scale'

	def execute(self):
		"Scale button has been clicked."
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class ScaleSkein:
	"A class to scale a skein of extrusions."
	def getCraftedGcode(self, fileName, repository, svgText):
		"Parse svgText and store the scale svgText."
		svgReader = SVGReader()
		svgReader.parseSVG('', svgText)
		if svgReader.sliceDictionary == None:
			print('Warning, nothing will be done because the sliceDictionary could not be found getCraftedGcode in preface.')
			return ''
		xyPlaneScale = repository.xyPlaneScale.value
		zAxisScale = repository.zAxisScale.value
		decimalPlacesCarried = int(svgReader.sliceDictionary['decimalPlacesCarried'])
		layerHeight = zAxisScale * float(svgReader.sliceDictionary['layerHeight'])
		edgeWidth = float(svgReader.sliceDictionary['edgeWidth'])
		loopLayers = svgReader.loopLayers
		for loopLayer in loopLayers:
			setLoopLayerScale(loopLayer, xyPlaneScale, zAxisScale)
		cornerMaximum = Vector3(-912345678.0, -912345678.0, -912345678.0)
		cornerMinimum = Vector3(912345678.0, 912345678.0, 912345678.0)
		svg_writer.setSVGCarvingCorners(cornerMaximum, cornerMinimum, layerHeight, loopLayers)
		svgWriter = svg_writer.SVGWriter(
			True,
			cornerMaximum,
			cornerMinimum,
			decimalPlacesCarried,
			layerHeight,
			edgeWidth)
		commentElement = svg_writer.getCommentElement(svgReader.documentElement)
		procedureNameString = svgReader.sliceDictionary['procedureName'] + ',scale'
		return svgWriter.getReplacedSVGTemplate(fileName, loopLayers, procedureNameString, commentElement)


def main():
	"Display the scale dialog."
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == "__main__":
	main()
