#! /usr/bin/env python
"""
This page is in the table of contents.
The alteration plugin adds the start and end files to the gcode.

This plugin also removes the alteration prefix tokens from the alteration lines.  Alteration lines have a prefix token so they can go through the craft plugins without being modified.  However, the tokens are not recognized by the firmware so they have to be removed before export. The alteration token is:
(<alterationDeleteThisPrefix/>)

The alteration manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Alteration

==Operation==
The default 'Activate Alteration' checkbox is on.  When it is on, the functions described below will work, when it is off, nothing will be done.

==Settings==
Alteration looks for alteration files in the alterations folder in the .skeinforge folder in the home directory.  Alteration does not care if the text file names are capitalized, but some file systems do not handle file name cases properly, so to be on the safe side you should give them lower case names.  If it doesn't find the file it then looks in the alterations folder in the skeinforge_plugins folder.

===Name of End File===
Default is 'end.gcode'.

If there is a file with the name of the "Name of End File" setting, it will be added to the very end of the gcode.

===Name of Start File===
Default is 'start.gcode'.

If there is a file with the name of the "Name of Start File" setting, it will be added to the very beginning of the gcode.

===Remove Redundant Mcode===
Default: True

If 'Remove Redundant Mcode' is selected then M104 and M108 lines which are followed by a different value before there is a movement will be removed.  For example, if there is something like:
M113 S1.0
M104 S60.0
(<layer> 0.72 )
M104 S200.0
(<skirt>)

with Remove Redundant Mcode selected, that snippet would become:
M113 S1.0
M104 S200.0
(<layer> 0.72 )
(<skirt>)

This is a relatively safe procedure, the only reason it is optional is because someone might make an alteration file which, for some unknown reason, requires the redundant mcode.

===Replace Variable with Setting===
Default: True

If 'Replace Variable with Setting' is selected and there is an alteration line with a setting token, the token will be replaced by the value.

For example, if there is an alteration line like:

M140 S<setting.chamber.BedTemperature>

the token would be replaced with the value and assuming the bed chamber was 60.0, the output would be:

M140 S60.0

==Examples==
The following examples add the alteration information to the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and alteration.py.

> python alteration.py
This brings up the alteration dialog.

> python alteration.py Screw Holder Bottom.stl
The alteration tool is parsing the file:
Screw Holder Bottom.stl
..
The alteration tool has created the file:
.. Screw Holder Bottom_alteration.gcode

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
from fabmetheus_utilities import archive
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_utilities import skeinforge_craft
from skeinforge_application.skeinforge_utilities import skeinforge_polyfile
from skeinforge_application.skeinforge_utilities import skeinforge_profile
import cStringIO
import sys


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCraftedText(fileName, text='', repository=None):
	'Alteration a gcode linear move text.'
	return getCraftedTextFromText(archive.getTextIfEmpty(fileName, text), repository)

def getCraftedTextFromText(gcodeText, repository=None):
	'Alteration a gcode linear move text.'
	if gcodec.isProcedureDoneOrFileIsEmpty(gcodeText, 'alteration'):
		return gcodeText
	if repository == None:
		repository = settings.getReadRepository(AlterationRepository())
	if not repository.activateAlteration.value:
		return gcodeText
	return AlterationSkein().getCraftedGcode(gcodeText, repository)

def getGcodeTextWithoutRedundantMcode(gcodeText):
	'Get gcode text without redundant M104 and M108.'
	lines = archive.getTextLines(gcodeText)
	lines = getLinesWithoutRedundancy('M104', lines)
	lines = getLinesWithoutRedundancy('M108', lines)
	output = cStringIO.StringIO()
	gcodec.addLinesToCString(output, lines)
	return output.getvalue()

def getLinesWithoutRedundancy(duplicateWord, lines):
	'Get gcode lines without redundant first words.'
	oldDuplicationIndex = None
	for lineIndex, line in enumerate(lines):
		firstWord = gcodec.getFirstWordFromLine(line)
		if firstWord == duplicateWord:
			if oldDuplicationIndex == None:
				oldDuplicationIndex = lineIndex
			else:
				lines[oldDuplicationIndex] = line
				lines[lineIndex] = ''
		elif firstWord.startswith('G') or firstWord == 'M101' or firstWord == 'M103':
			oldDuplicationIndex = None
	return lines

def getNewRepository():
	'Get new repository.'
	return AlterationRepository()

def writeOutput(fileName, shouldAnalyze=True):
	'Alteration a gcode linear move file.  Chain alteration the gcode if the alteration procedure has not been done.'
	skeinforge_craft.writeChainTextWithNounMessage(fileName, 'alteration', shouldAnalyze)


class AlterationRepository:
	"A class to handle the alteration settings."
	def __init__(self):
		"Set the default settings, execute title & settings fileName."
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.alteration.html', self )
		self.baseNameSynonym = 'bookend.csv'
		self.fileNameInput = settings.FileNameInput().getFromFileName(fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Alteration', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Alteration')
		self.activateAlteration = settings.BooleanSetting().getFromValue('Activate Alteration', self, True)
		self.nameOfEndFile = settings.StringSetting().getFromValue('Name of End File:', self, 'end.gcode')
		self.nameOfStartFile = settings.StringSetting().getFromValue('Name of Start File:', self, 'start.gcode')
		self.removeRedundantMcode = settings.BooleanSetting().getFromValue('Remove Redundant Mcode', self, True)
		self.replaceVariableWithSetting = settings.BooleanSetting().getFromValue('Replace Variable with Setting', self, True)
		self.executeTitle = 'Alteration'

	def execute(self):
		'Alteration button has been clicked.'
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class AlterationSkein:
	"A class to alteration a skein of extrusions."
	def __init__(self):
		'Initialize.'
 		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.lineIndex = 0
		self.settingDictionary = None

	def addFromUpperLowerFile(self, fileName):
		"Add lines of text from the fileName or the lowercase fileName, if there is no file by the original fileName in the directory."
		alterationFileLines = settings.getAlterationFileLines(fileName)
		self.distanceFeedRate.addLinesSetAbsoluteDistanceMode(alterationFileLines)

	def getCraftedGcode(self, gcodeText, repository):
		"Parse gcode text and store the bevel gcode."
		self.lines = archive.getTextLines(gcodeText)
		if repository.replaceVariableWithSetting.value:
			self.setSettingDictionary()
		self.addFromUpperLowerFile(repository.nameOfStartFile.value) # Add a start file if it exists.
		self.parseInitialization()
		for self.lineIndex in xrange(self.lineIndex, len(self.lines)):
			line = self.lines[self.lineIndex]
			self.distanceFeedRate.addLine(line)
		self.addFromUpperLowerFile(repository.nameOfEndFile.value) # Add an end file if it exists.
		gcodeText = self.getReplacedAlterationText()
		if repository.removeRedundantMcode.value:
			gcodeText = getGcodeTextWithoutRedundantMcode(gcodeText)
		return gcodeText

	def getReplacedAlterationLine(self, alterationFileLine, searchIndex=0):
		'Get the alteration file line with variables replaced with the settings.'
		settingIndex = alterationFileLine.find('setting.', searchIndex)
		beginIndex = settingIndex - 1
		if beginIndex < 0:
			return alterationFileLine
		endBracketIndex = alterationFileLine.find('>', settingIndex)
		if alterationFileLine[beginIndex] != '<' or endBracketIndex == -1:
			return alterationFileLine
		endIndex = endBracketIndex + 1
		innerToken = alterationFileLine[settingIndex + len('setting.'): endIndex].replace('>', '').replace(' ', '').replace('_', '').lower()
		if innerToken in self.settingDictionary:
			replacedSetting = self.settingDictionary[innerToken]
			replacedAlterationLine = alterationFileLine[: beginIndex] + replacedSetting + alterationFileLine[endIndex :]
			return self.getReplacedAlterationLine(replacedAlterationLine, beginIndex + len(replacedSetting))
		return alterationFileLine

	def getReplacedAlterationText(self):
		'Replace the alteration lines if there are settings.'
		if self.settingDictionary == None:
			return self.distanceFeedRate.output.getvalue().replace('(<alterationDeleteThisPrefix/>)', '')
		lines = archive.getTextLines(self.distanceFeedRate.output.getvalue())
 		distanceFeedRate = gcodec.DistanceFeedRate()
		for line in lines:
			if line.startswith('(<alterationDeleteThisPrefix/>)'):
				line = self.getReplacedAlterationLine(line[len('(<alterationDeleteThisPrefix/>)') :])
			distanceFeedRate.addLine(line)
		return distanceFeedRate.output.getvalue()

	def parseInitialization(self):
		'Parse gcode initialization and store the parameters.'
		for self.lineIndex in xrange(len(self.lines)):
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			self.distanceFeedRate.parseSplitLine(firstWord, splitLine)
			if firstWord == '(</extruderInitialization>)':
				self.distanceFeedRate.addTagBracketedProcedure('alteration')
				return
			self.distanceFeedRate.addLine(line)

	def setSettingDictionary(self):
		'Set the setting dictionary from the gcode text.'
		for line in self.lines:
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			if firstWord == '(<setting>' and self.settingDictionary != None:
				if len(splitLine) > 4:
					procedure = splitLine[1]
					name = splitLine[2].replace('_', ' ').replace(' ', '')
					if '(' in name:
						name = name[: name.find('(')]
					value = ' '.join(splitLine[3 : -1])
					self.settingDictionary[(procedure + '.' + name).lower()] = value
			elif firstWord == '(<settings>)':
				self.settingDictionary = {}
			elif firstWord == '(</settings>)':
				return


def main():
	"Display the alteration dialog."
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == "__main__":
	main()
