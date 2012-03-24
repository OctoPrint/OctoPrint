#! /usr/bin/env python
"""
This page is in the table of contents.
Preface converts the svg slices into gcode extrusion layers, optionally with home, positioning, turn off, and unit commands.

The preface manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Preface

==Settings==
===Meta===
Default is empty.

The 'Meta' field is to add meta tags or a note to all your files.  Whatever is in that field will be added in a meta tagged line to the output.

===Set Positioning to Absolute===
Default is on.

When selected, preface will add the G90 command to set positioning to absolute.

===Set Units to Millimeters===
Default is on.

When selected, preface will add the G21 command to set the units to millimeters.

===Start at Home===
Default is off.

When selected, the G28 go to home gcode will be added at the beginning of the file.

===Turn Extruder Off===
====Turn Extruder Off at Shut Down====
Default is on.

When selected, the M103 turn extruder off gcode will be added at the end of the file.

====Turn Extruder Off at Start Up====
Default is on.

When selected, the M103 turn extruder off gcode will be added at the beginning of the file.

==Examples==
The following examples preface the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and preface.py.

> python preface.py
This brings up the preface dialog.

> python preface.py Screw Holder Bottom.stl
The preface tool is parsing the file:
Screw Holder Bottom.stl
..
The preface tool has created the file:
.. Screw Holder Bottom_preface.gcode

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from datetime import date, datetime
from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
from fabmetheus_utilities.svg_reader import SVGReader
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import intercircle
from fabmetheus_utilities import settings
from fabmetheus_utilities import svg_writer
from skeinforge_application.skeinforge_utilities import skeinforge_craft
from skeinforge_application.skeinforge_utilities import skeinforge_polyfile
from skeinforge_application.skeinforge_utilities import skeinforge_profile
from time import strftime
import os
import sys


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCraftedText( fileName, text='', repository = None ):
	"Preface and convert an svg file or text."
	return getCraftedTextFromText(archive.getTextIfEmpty(fileName, text), repository)

def getCraftedTextFromText( text, repository = None ):
	"Preface and convert an svg text."
	if gcodec.isProcedureDoneOrFileIsEmpty( text, 'preface'):
		return text
	if repository == None:
		repository = settings.getReadRepository(PrefaceRepository())
	return PrefaceSkein().getCraftedGcode(repository, text)

def getNewRepository():
	'Get new repository.'
	return PrefaceRepository()

def writeOutput(fileName, shouldAnalyze=True):
	"Preface the carving of a gcode file."
	skeinforge_craft.writeChainTextWithNounMessage(fileName, 'preface', shouldAnalyze)


class PrefaceRepository:
	"A class to handle the preface settings."
	def __init__(self):
		"Set the default settings, execute title & settings fileName."
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.preface.html', self )
		self.fileNameInput = settings.FileNameInput().getFromFileName( fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Preface', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Preface')
		self.meta = settings.StringSetting().getFromValue('Meta:', self, '')
		self.setPositioningToAbsolute = settings.BooleanSetting().getFromValue('Set Positioning to Absolute', self, True )
		self.setUnitsToMillimeters = settings.BooleanSetting().getFromValue('Set Units to Millimeters', self, True )
		self.startAtHome = settings.BooleanSetting().getFromValue('Start at Home', self, False )
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Turn Extruder Off -', self )
		self.turnExtruderOffAtShutDown = settings.BooleanSetting().getFromValue('Turn Extruder Off at Shut Down', self, True )
		self.turnExtruderOffAtStartUp = settings.BooleanSetting().getFromValue('Turn Extruder Off at Start Up', self, True )
		self.executeTitle = 'Preface'

	def execute(self):
		"Preface button has been clicked."
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class PrefaceSkein:
	"A class to preface a skein of extrusions."
	def __init__(self):
		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.extruderActive = False
		self.lineIndex = 0
		self.oldLocation = None
		self.svgReader = SVGReader()

	def addInitializationToOutput(self):
		"Add initialization gcode to the output."
		self.distanceFeedRate.addTagBracketedLine('format', 'skeinforge gcode')
		absoluteFilePathUntilDot = archive.getUntilDot(archive.getCraftPluginsDirectoryPath('preface.py'))
		dateTodayString = date.today().isoformat().replace('-', '.')[2 :]
		if absoluteFilePathUntilDot == '/home/enrique/Desktop/backup/babbleold/script/reprap/fabmetheus/skeinforge_application/skeinforge_plugins/craft_plugins/preface': #is this script on Enrique's computer?
			archive.writeFileText(archive.getVersionFileName(), dateTodayString)
		versionText = archive.getFileText(archive.getVersionFileName())
		self.distanceFeedRate.addTagBracketedLine('version', versionText)
		dateTimeTuple = datetime.now().timetuple()
		created = dateTodayString + '|%s:%s' % (dateTimeTuple[3], dateTimeTuple[4])
		self.distanceFeedRate.addTagBracketedLine('created', created)
		self.distanceFeedRate.addLine('(<extruderInitialization>)')
		if self.repository.setPositioningToAbsolute.value:
			self.distanceFeedRate.addLine('G90 ;set positioning to absolute') # Set positioning to absolute.
		if self.repository.setUnitsToMillimeters.value:
			self.distanceFeedRate.addLine('G21 ;set units to millimeters') # Set units to millimeters.
		if self.repository.startAtHome.value:
			self.distanceFeedRate.addLine('G28 ;start at home') # Start at home.
		if self.repository.turnExtruderOffAtStartUp.value:
			self.distanceFeedRate.addLine('M103') # Turn extruder off.
		craftTypeName = skeinforge_profile.getCraftTypeName()
		self.distanceFeedRate.addTagBracketedLine('craftTypeName', craftTypeName)
		self.distanceFeedRate.addTagBracketedLine('decimalPlacesCarried', self.distanceFeedRate.decimalPlacesCarried)
		layerHeight = float(self.svgReader.sliceDictionary['layerHeight'])
		self.distanceFeedRate.addTagRoundedLine('layerThickness', layerHeight)
		self.distanceFeedRate.addTagRoundedLine('layerHeight', layerHeight)
		if self.repository.meta.value:
			self.distanceFeedRate.addTagBracketedLine('meta', self.repository.meta.value)
		edgeWidth = float(self.svgReader.sliceDictionary['edgeWidth'])
		self.distanceFeedRate.addTagRoundedLine('edgeWidth', edgeWidth)
		self.distanceFeedRate.addTagRoundedLine('perimeterWidth', edgeWidth)
		self.distanceFeedRate.addTagBracketedLine('profileName', skeinforge_profile.getProfileName(craftTypeName))
		self.distanceFeedRate.addLine('(<settings>)')
		pluginFileNames = skeinforge_craft.getPluginFileNames()
		for pluginFileName in pluginFileNames:
			self.addToolSettingLines(pluginFileName)
		self.distanceFeedRate.addLine('(</settings>)')
		self.distanceFeedRate.addTagBracketedLine('timeStampPreface', strftime('%Y%m%d_%H%M%S'))
		procedureNames = self.svgReader.sliceDictionary['procedureName'].replace(',', ' ').split()
		for procedureName in procedureNames:
			self.distanceFeedRate.addTagBracketedProcedure(procedureName)
		self.distanceFeedRate.addTagBracketedProcedure('preface')
		self.distanceFeedRate.addLine('(</extruderInitialization>)') # Initialization is finished, extrusion is starting.
		self.distanceFeedRate.addLine('(<crafting>)') # Initialization is finished, crafting is starting.

	def addPreface( self, loopLayer ):
		"Add preface to the carve layer."
		self.distanceFeedRate.addLine('(<layer> %s )' % loopLayer.z ) # Indicate that a new layer is starting.
		for loop in loopLayer.loops:
			self.distanceFeedRate.addGcodeFromLoop(loop, loopLayer.z)
		self.distanceFeedRate.addLine('(</layer>)')

	def addShutdownToOutput(self):
		"Add shutdown gcode to the output."
		self.distanceFeedRate.addLine('(</crafting>)') # GCode formatted comment
		if self.repository.turnExtruderOffAtShutDown.value:
			self.distanceFeedRate.addLine('M103') # Turn extruder motor off.

	def addToolSettingLines(self, pluginName):
		"Add tool setting lines."
		preferences = skeinforge_craft.getCraftPreferences(pluginName)
		if skeinforge_craft.getCraftValue('Activate %s' % pluginName.capitalize(), preferences) != True:
			return
		for preference in preferences:
			valueWithoutReturn = str(preference.value).replace('\n', ' ').replace('\r', ' ')
			if preference.name != 'WindowPosition' and not preference.name.startswith('Open File'):
				line = '%s %s %s' % (pluginName, preference.name.replace(' ', '_'), valueWithoutReturn)
				self.distanceFeedRate.addTagBracketedLine('setting', line)

	def getCraftedGcode( self, repository, gcodeText ):
		"Parse gcode text and store the bevel gcode."
		self.repository = repository
		self.svgReader.parseSVG('', gcodeText)
		if self.svgReader.sliceDictionary == None:
			print('Warning, nothing will be done because the sliceDictionary could not be found getCraftedGcode in preface.')
			return ''
		self.distanceFeedRate.decimalPlacesCarried = int(self.svgReader.sliceDictionary['decimalPlacesCarried'])
		self.addInitializationToOutput()
		for loopLayerIndex, loopLayer in enumerate(self.svgReader.loopLayers):
			settings.printProgressByNumber(loopLayerIndex, len(self.svgReader.loopLayers), 'preface')
			self.addPreface( loopLayer )
		self.addShutdownToOutput()
		return self.distanceFeedRate.output.getvalue()


def main():
	"Display the preface dialog."
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == "__main__":
	main()
