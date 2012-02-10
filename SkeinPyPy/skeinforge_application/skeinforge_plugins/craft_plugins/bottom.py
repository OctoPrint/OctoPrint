#! /usr/bin/env python
"""
This page is in the table of contents.
Bottom sets the bottom of the carving to the defined altitude.

The bottom manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Bottom

==Operation==
The default 'Activate Bottom' checkbox is on.  When it is on, the functions described below will work, when it is off, the functions will not be called.

==Settings==
===Additional Height over Layer Thickness===
Default is half.

The layers will start at the altitude plus the 'Additional Height over Layer Thickness' times the layer height.  The default value of half means that the bottom layer is at the height of the bottom slice, because each slice is made through the middle of each layer.  Raft expects the layers to start at an additional half layer height.  You should only change 'Additional Height over Layer Thickness' if you are manipulating the skeinforge output with your own program which does not use the raft tool.

===Altitude===
Default is zero.

Defines the altitude of the bottom of the model.  The bottom slice has a z of the altitude plus the 'Additional Height over Layer Thickness' times the layer height.

===SVG Viewer===
Default is webbrowser.

If the 'SVG Viewer' is set to the default 'webbrowser', the scalable vector graphics file will be sent to the default browser to be opened.  If the 'SVG Viewer' is set to a program name, the scalable vector graphics file will be sent to that program to be opened.

==Examples==
The following examples bottom the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and bottom.py.

> python bottom.py
This brings up the bottom dialog.

> python bottom.py Screw Holder Bottom.stl
The bottom tool is parsing the file:
Screw Holder Bottom.stl
..
The bottom tool has created the file:
.. Screw Holder Bottom_bottom.gcode

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
	"Bottom and convert an svg file or svgText."
	return getCraftedTextFromText(fileName, archive.getTextIfEmpty(fileName, svgText), repository)

def getCraftedTextFromText(fileName, svgText, repository=None):
	"Bottom and convert an svgText."
	if gcodec.isProcedureDoneOrFileIsEmpty(svgText, 'bottom'):
		return svgText
	if repository == None:
		repository = settings.getReadRepository(BottomRepository())
	if not repository.activateBottom.value:
		return svgText
	return BottomSkein().getCraftedGcode(fileName, repository, svgText)

def getNewRepository():
	'Get new repository.'
	return BottomRepository()

def writeOutput(fileName, shouldAnalyze=True):
	'Bottom the carving.'
	skeinforge_craft.writeSVGTextWithNounMessage(fileName, BottomRepository(), shouldAnalyze)


class BottomRepository:
	"A class to handle the bottom settings."
	def __init__(self):
		"Set the default settings, execute title & settings fileName."
		skeinforge_profile.addListsToCraftTypeRepository(
			'skeinforge_application.skeinforge_plugins.craft_plugins.bottom.html', self)
		self.fileNameInput = settings.FileNameInput().getFromFileName(
			fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Bottom', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Bottom')
		self.activateBottom = settings.BooleanSetting().getFromValue('Activate Bottom', self, True)
		self.additionalHeightOverLayerThickness = settings.FloatSpin().getFromValue(
			0.0, 'Additional Height over Layer Thickness (ratio):', self, 1.0, 0.5)
		self.altitude = settings.FloatSpin().getFromValue(-1.0, 'Altitude (mm):', self, 1.0, 0.0)
		self.svgViewer = settings.StringSetting().getFromValue('SVG Viewer:', self, 'webbrowser')
		self.executeTitle = 'Bottom'

	def execute(self):
		"Bottom button has been clicked."
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class BottomSkein:
	"A class to bottom a skein of extrusions."
	def getCraftedGcode(self, fileName, repository, svgText):
		"Parse svgText and store the bottom svgText."
		svgReader = SVGReader()
		svgReader.parseSVG('', svgText)
		if svgReader.sliceDictionary == None:
			print('Warning, nothing will be done because the sliceDictionary could not be found getCraftedGcode in preface.')
			return ''
		decimalPlacesCarried = int(svgReader.sliceDictionary['decimalPlacesCarried'])
		edgeWidth = float(svgReader.sliceDictionary['edgeWidth'])
		layerHeight = float(svgReader.sliceDictionary['layerHeight'])
		loopLayers = svgReader.loopLayers
		zMinimum = 987654321.0
		for loopLayer in loopLayers:
			zMinimum = min(loopLayer.z, zMinimum)
		deltaZ = repository.altitude.value + repository.additionalHeightOverLayerThickness.value * layerHeight - zMinimum
		for loopLayer in loopLayers:
			loopLayer.z += deltaZ
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
		procedureNameString = svgReader.sliceDictionary['procedureName'] + ',bottom'
		return svgWriter.getReplacedSVGTemplate(fileName, loopLayers, procedureNameString, commentElement)


def main():
	"Display the bottom dialog."
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == "__main__":
	main()
