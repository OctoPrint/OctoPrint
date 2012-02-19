"""
Fabmetheus interpret is a fabmetheus utility to interpret a file, turning it into fabmetheus constructive solid geometry xml.

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
import time


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCarving(fileName):
	"Get carving."
	pluginModule = getInterpretPlugin(fileName)
	if pluginModule == None:
		return None
	return pluginModule.getCarving(fileName)

def getGNUTranslatorFilesUnmodified():
	"Get the file types from the translators in the import plugins folder."
	return archive.getFilesWithFileTypesWithoutWords(getImportPluginFileNames())

def getGNUTranslatorGcodeFileTypeTuples():
	"Get the file type tuples from the translators in the import plugins folder plus gcode."
	fileTypeTuples = getTranslatorFileTypeTuples()
	fileTypeTuples.append( ('Gcode text files', '*.gcode') )
	fileTypeTuples.sort()
	return fileTypeTuples

def getImportPluginFileNames():
	"Get interpret plugin fileNames."
	return archive.getPluginFileNamesFromDirectoryPath( getPluginsDirectoryPath() )

def getInterpretPlugin(fileName):
	"Get the interpret plugin for the file."
	importPluginFileNames = getImportPluginFileNames()
	for importPluginFileName in importPluginFileNames:
		fileTypeDot = '.' + importPluginFileName
		if fileName[ - len(fileTypeDot) : ].lower() == fileTypeDot:
			importPluginsDirectoryPath = getPluginsDirectoryPath()
			pluginModule = archive.getModuleWithDirectoryPath( importPluginsDirectoryPath, importPluginFileName )
			if pluginModule != None:
				return pluginModule
	print('Could not find plugin to handle ' + fileName )
	return None

def getNewRepository():
	'Get new repository.'
	return InterpretRepository()

def getPluginsDirectoryPath():
	"Get the plugins directory path."
	return archive.getInterpretPluginsPath()

def getTranslatorFileTypeTuples():
	"Get the file types from the translators in the import plugins folder."
	importPluginFileNames = getImportPluginFileNames()
	fileTypeTuples = []
	for importPluginFileName in importPluginFileNames:
		fileTypeTitle = importPluginFileName.upper() + ' files'
		fileType = ( fileTypeTitle, '*.' + importPluginFileName )
		fileTypeTuples.append( fileType )
	fileTypeTuples.sort()
	return fileTypeTuples

def getWindowAnalyzeFile(fileName):
	"Get file interpretion."
	startTime = time.time()
	carving = getCarving(fileName)
	if carving == None:
		return None
	interpretGcode = str( carving )
	if interpretGcode == '':
		return None
	repository = settings.getReadRepository( InterpretRepository() )
	if repository.printInterpretion.value:
		print(interpretGcode)
	suffixFileName = fileName[ : fileName.rfind('.') ] + '_interpret.' + carving.getInterpretationSuffix()
	suffixDirectoryName = os.path.dirname(suffixFileName)
	suffixReplacedBaseName = os.path.basename(suffixFileName).replace(' ', '_')
	suffixFileName = os.path.join( suffixDirectoryName, suffixReplacedBaseName )
	archive.writeFileText( suffixFileName, interpretGcode )
	print('The interpret file is saved as ' + archive.getSummarizedFileName(suffixFileName) )
	print('It took %s to interpret the file.' % euclidean.getDurationString( time.time() - startTime ) )
	textProgram = repository.textProgram.value
	if textProgram == '':
		return None
	if textProgram == 'webbrowser':
		settings.openWebPage(suffixFileName)
		return None
	textFilePath = '"' + os.path.normpath(suffixFileName) + '"' # " to send in file name with spaces
	shellCommand = textProgram + ' ' + textFilePath
	print('Sending the shell command:')
	print(shellCommand)
	commandResult = os.system(shellCommand)
	if commandResult != 0:
		print('It may be that the system could not find the %s program.' % textProgram )
		print('If so, try installing the %s program or look for another one, like Open Office which can be found at:' % textProgram )
		print('http://www.openoffice.org/')
		print('Open office writer can then be started from the command line with the command "soffice -writer".')


class InterpretRepository:
	"A class to handle the interpret settings."
	def __init__(self):
		"Set the default settings, execute title & settings fileName."
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.analyze_plugins.interpret.html', self)
		self.fileNameInput = settings.FileNameInput().getFromFileName( getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Interpret', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Interpret')
		self.activateInterpret = settings.BooleanSetting().getFromValue('Activate Interpret', self, False )
		self.printInterpretion = settings.BooleanSetting().getFromValue('Print Interpretion', self, False )
		self.textProgram = settings.StringSetting().getFromValue('Text Program:', self, 'webbrowser')
		self.executeTitle = 'Interpret'

	def execute(self):
		"Write button has been clicked."
		fileNames = skeinforge_polyfile.getFileOrGcodeDirectory( self.fileNameInput.value, self.fileNameInput.wasCancelled )
		for fileName in fileNames:
			getWindowAnalyzeFile(fileName)
