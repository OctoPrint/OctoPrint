"""
This page is in the table of contents.
Synopsis is an analyze plugin to export the profile from a skeinforge gcode file as a csv or zip file.

The synopsis manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Synopsis

==Operation==
The default 'Activate Synopsis' checkbox is off.  When it is on, the functions described below will work when called from the skeinforge toolchain, when it is off, the functions will not be called from the toolchain.  The functions will still be called, whether or not the 'Activate Synopsis' checkbox is on, when synopsis is run directly.

==Settings==
===Export Profile As CSV File===
Default is on.

If 'Export Profile As CSV File' is selected, the profile from a skeinforge gcode file with comments will be exported as a csv (comma separated values) file.

===Export Profile As Zip File===
Default is off.

If 'Export Profile As Zip File' is selected, the profile from a skeinforge gcode file with comments will be exported as a zip file.

==Examples==
Below are examples of synopsis being used.  These examples are run in a terminal in the folder which contains Screw Holder_penultimate.gcode and synopsis.py.

> python synopsis.py
This brings up the synopsis dialog.

> python synopsis.py Screw Holder_penultimate.gcode
The synopsis file is saved as Screw_Holder_penultimate_synopsis.csv

"""


from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_utilities import skeinforge_polyfile
from skeinforge_application.skeinforge_utilities import skeinforge_profile
import os
import sys
import time
import zipfile


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Gary Hodgson <http://garyhodgson.com/reprap/2011/06/hacking-skeinforge-export-module/>'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def addAbridgedSettings(abridgedSettings, repositoryWriter):
	'Add the abridged settings to a repository writer.'
	for abridgedSetting in abridgedSettings:
		repositoryWriter.write('%s\n' % abridgedSetting.__repr__())

def exportProfileAsCSVFile(abridgedSettings, suffixFileNameWithoutExtension):
	'Export the profile from the gcode text as a csv file.'
	if len(abridgedSettings) < 1:
		print('Warning, the synopsis csv file could not be generated because there are no setting comments in the file.')
		return
	repositoryWriter = settings.getRepositoryWriter('profile')
	suffixFileName = suffixFileNameWithoutExtension + 'csv'
	addAbridgedSettings(abridgedSettings, repositoryWriter)
	archive.writeFileText(suffixFileName, repositoryWriter.getvalue())
	print('The synopsis csv file is saved as ' + archive.getSummarizedFileName(suffixFileName))

def exportProfileAsZipFile(abridgedSettings, suffixDirectoryPath, suffixFileNameWithoutExtension):
	'Export the profile from the gcode text as a zip file.'
	if len(abridgedSettings) < 1:
		print('Warning, the synopsis zip file could not be generated because there are no setting comments in the file.')
		return
	suffixFileName =  suffixFileNameWithoutExtension + 'zip'
	abridgedSettingsDictionary = {}
	for abridgedSetting in abridgedSettings:
		euclidean.addElementToListDictionary(abridgedSetting, abridgedSetting.procedure, abridgedSettingsDictionary)
	abridgedSettingFileNamePaths = []
	for abridgedSettingsKey in abridgedSettingsDictionary:
		abridgedSettings = abridgedSettingsDictionary[abridgedSettingsKey]
		repositoryWriter = settings.getRepositoryWriter(abridgedSettingsKey)
		addAbridgedSettings(abridgedSettings, repositoryWriter)
		abridgedSettingFileNamePath = FileNamePath(suffixDirectoryPath, abridgedSettingsKey + '.csv')
		abridgedSettingFileNamePaths.append(abridgedSettingFileNamePath)
		archive.writeFileText(abridgedSettingFileNamePath.path, repositoryWriter.getvalue())
	time.sleep(0.2) # the sleep is so that the file system is sure to be consistent
	zipArchive = zipfile.ZipFile(suffixFileName, 'w', compression=zipfile.ZIP_DEFLATED)
	for abridgedSettingFileNamePath in abridgedSettingFileNamePaths:
		zipArchive.write(abridgedSettingFileNamePath.path, abridgedSettingFileNamePath.fileName)
	zipArchive.close()
	time.sleep(0.2) # the sleep is so that the file system is sure to be consistent
	for abridgedSettingFileNamePath in abridgedSettingFileNamePaths:
		os.remove(abridgedSettingFileNamePath.path)
	print('The synopsis zip file is saved as ' + archive.getSummarizedFileName(suffixFileName))

def getAbridgedSettings(gcodeText):
	'Get the abridged settings from the gcode text.'
	abridgedSettings = []
	lines = archive.getTextLines(gcodeText)
	settingsStart = False
	for line in lines:
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		firstWord = gcodec.getFirstWord(splitLine)
		if firstWord == '(<setting>' and settingsStart:
			if len(splitLine) > 4:
				abridgedSettings.append(AbridgedSetting(splitLine))
		elif firstWord == '(<settings>)':
			settingsStart = True
		elif firstWord == '(</settings>)':
			return abridgedSettings
	return []

def getNewRepository():
	'Get new repository.'
	return SynopsisRepository()

def getWindowAnalyzeFile(fileName):
	'Write scalable vector graphics for a gcode file.'
	gcodeText = archive.getFileText(fileName)
	return getWindowAnalyzeFileGivenText(fileName, gcodeText)

def getWindowAnalyzeFileGivenText(fileName, gcodeText, repository=None):
	'Write scalable vector graphics for a gcode file given the settings.'
	if gcodeText == '':
		return None
	if repository == None:
		repository = settings.getReadRepository(SynopsisRepository())
	startTime = time.time()
	suffixFileNameWithoutExtension = fileName[: fileName.rfind('.')] + '_synopsis.'
	suffixDirectoryPath = os.path.dirname(suffixFileNameWithoutExtension)
	suffixReplacedBaseNameWithoutExtension = os.path.basename(suffixFileNameWithoutExtension).replace(' ', '_')
	suffixFileNameWithoutExtension = os.path.join(suffixDirectoryPath, suffixReplacedBaseNameWithoutExtension)
	abridgedSettings = getAbridgedSettings(gcodeText)
	if repository.exportProfileAsCSVFile.value:
		exportProfileAsCSVFile(abridgedSettings, suffixFileNameWithoutExtension)
	if repository.exportProfileAsZipFile.value:
		exportProfileAsZipFile(abridgedSettings, suffixDirectoryPath, suffixFileNameWithoutExtension)
	print('It took %s for synopsis to analyze the file.' % euclidean.getDurationString(time.time() - startTime))

def writeOutput(fileName, fileNamePenultimate, fileNameSuffix, filePenultimateWritten, gcodeText=''):
	'Write scalable vector graphics for a skeinforge gcode file, if activate synopsis is selected.'
	repository = settings.getReadRepository( SynopsisRepository() )
	if not repository.activateSynopsis.value:
		return
	gcodeText = archive.getTextIfEmpty( fileNameSuffix, gcodeText )
	getWindowAnalyzeFileGivenText( fileNameSuffix, gcodeText, repository )


class AbridgedSetting:
	'A class to handle an abridged setting.'
	def __init__(self, splitLine):
		'Initialize.'
		self.procedure = splitLine[1]
		self.name = splitLine[2].replace('_', ' ')
		self.value = ' '.join(splitLine[3 : -1])

	def __repr__(self):
		'Get the tab separated representation of this AbridgedSetting.'
		return '%s\t%s\t%s' % (self.procedure, self.name, self.value)


class FileNamePath:
	'A class to handle a file name and path.'
	def __init__(self, directoryName, fileName):
		'Initialize.'
		self.fileName = fileName
		self.path = os.path.join(directoryName, fileName)

	def __repr__(self):
		'Get the tab separated representation of this FileNamePath.'
		return '%s\t%s' % (self.fileName, self.path)


class SynopsisRepository:
	'A class to handle the synopsis settings.'
	def __init__(self):
		'Set the default settings, execute title & settings fileName.'
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.analyze_plugins.synopsis.html', self )
		self.activateSynopsis = settings.BooleanSetting().getFromValue('Activate Synopsis', self, False )
		self.fileNameInput = settings.FileNameInput().getFromFileName( [ ('Gcode text files', '*.gcode') ], 'Open File to Write Synopsis for', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Synopsis')
		self.exportProfileAsCSVFile = settings.BooleanSetting().getFromValue('Export Profile As CSV File', self, True)
		self.exportProfileAsZipFile = settings.BooleanSetting().getFromValue('Export Profile As Zip File', self, False)
		self.executeTitle = 'Synopsis'

	def execute(self):
		'Write button has been clicked.'
		fileNames = skeinforge_polyfile.getFileOrGcodeDirectory( self.fileNameInput.value, self.fileNameInput.wasCancelled )
		for fileName in fileNames:
			getWindowAnalyzeFile(fileName)


def main():
	'Display the synopsis dialog.'
	if len(sys.argv) > 1:
		getWindowAnalyzeFile(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == '__main__':
	main()
