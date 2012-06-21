"""
Boolean geometry utilities.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

import os
import sys
import traceback
import zipfile


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


globalTemporarySettingsPath = os.path.join(os.path.expanduser('~'), '.skeinforge_pypy')


def addToNamePathDictionary(directoryPath, namePathDictionary):
	'Add to the name path dictionary.'
	pluginFileNames = getPluginFileNamesFromDirectoryPath(directoryPath)
	for pluginFileName in pluginFileNames:
		namePathDictionary[pluginFileName.replace('_', '')] = os.path.join(directoryPath, pluginFileName)

def getAbsoluteFolderPath(filePath, folderName=''):
	'Get the absolute folder path.'
	absoluteFolderPath = os.path.dirname(os.path.abspath(filePath))
	if folderName == '':
		return absoluteFolderPath
	return os.path.join(absoluteFolderPath, folderName)

def getAbsoluteFrozenFolderPath(filePath, folderName=''):
	'Get the absolute frozen folder path.'
	if hasattr(sys, 'frozen'):
		if '.py' in filePath:
			filePath = ''.join(filePath.rpartition('\\')[: 2])
		filePath = os.path.join(filePath, 'skeinforge_application')
	return getAbsoluteFolderPath(filePath, folderName)

def getAnalyzePluginsDirectoryPath(subName=''):
	'Get the analyze plugins directory path.'
	return getJoinedPath(getSkeinforgePluginsPath('analyze_plugins'), subName)

def getCraftPluginsDirectoryPath(subName=''):
	'Get the craft plugins directory path.'
	return getJoinedPath(getSkeinforgePluginsPath('craft_plugins'), subName)

def getDocumentationPath(subName=''):
	'Get the documentation file path.'
	return getJoinedPath(getFabmetheusPath('documentation'), subName)

def getElementsPath(subName=''):
	'Get the evaluate_elements directory path.'
	return getJoinedPath(getGeometryUtilitiesPath('evaluate_elements'), subName)

def getEndsWithList(word, wordEndings):
	'Determine if the word ends with a list.'
	for wordEnding in wordEndings:
		if word.endswith(wordEnding):
			return True
	return False

def getFabmetheusPath(subName=''):
	'Get the fabmetheus directory path.'
	fabmetheusFile = None
	if hasattr(sys, 'frozen'):
		fabmetheusFile = unicode(sys.executable, sys.getfilesystemencoding())
	else:
		fabmetheusFile = os.path.dirname(os.path.abspath(__file__))
	return getJoinedPath(os.path.dirname(fabmetheusFile), subName)

def getFabmetheusToolsPath(subName=''):
	'Get the fabmetheus tools directory path.'
	return getJoinedPath(getFabmetheusUtilitiesPath('fabmetheus_tools'), subName)

def getFabmetheusUtilitiesPath(subName=''):
	'Get the fabmetheus utilities directory path.'
	return getJoinedPath(getFabmetheusPath('fabmetheus_utilities'), subName)

def getFileNamesByFilePaths(pluginFilePaths):
	'Get the file names of the plugins by the file paths.'
	fileNames = []
	for pluginFilePath in pluginFilePaths:
		pluginBasename = os.path.basename(pluginFilePath)
		pluginBasename = getUntilDot(pluginBasename)
		fileNames.append(pluginBasename)
	return fileNames

def getFilePaths(fileInDirectory=''):
	'Get the file paths in the directory of the file in directory.'
	directoryName = os.getcwd()
	if fileInDirectory != '':
		directoryName = os.path.dirname(fileInDirectory)
	return getFilePathsByDirectory(directoryName)

def getFilePathsByDirectory(directoryName):
	'Get the file paths in the directory of the file in directory.'
	absoluteDirectoryPath = os.path.abspath(directoryName)
	filePaths = []
	if os.path.isdir(directoryName):
		for fileName in os.listdir(directoryName):
			filePaths.append(os.path.join(absoluteDirectoryPath, fileName))
	elif '.zip/' in directoryName:
		zipfilename = directoryName[:directoryName.rfind('.zip/')+4]
		subpath = directoryName[directoryName.rfind('.zip/')+5:]

		z = zipfile.ZipFile(zipfilename, 'r')
		for name in z.namelist():
			if os.path.dirname(name) == subpath:
				filePaths.append(os.path.join(zipfilename, name))
		z.close()
		print(directoryName, filePaths)
	return filePaths

def getFilePathsRecursively(fileInDirectory=''):
	'Get the file paths in the directory of the file in directory.'
	filePaths = getFilePaths(fileInDirectory)
	filePathsRecursively = filePaths[:]
	for filePath in filePaths:
		if os.path.isdir(filePath):
			directory = os.listdir(filePath)
			if len(directory) > 0:
				filePathsRecursively += getFilePathsRecursively(os.path.join(filePath, directory[0]))
	return filePathsRecursively

def getFilePathWithUnderscoredBasename(fileName, suffix):
	'Get the file path with all spaces in the basename replaced with underscores.'
	suffixFileName = getUntilDot(fileName) + suffix
	suffixDirectoryName = os.path.dirname(suffixFileName)
	suffixReplacedBaseName = os.path.basename(suffixFileName).replace(' ', '_')
	return os.path.join(suffixDirectoryName, suffixReplacedBaseName)

def getFilesWithFileTypesWithoutWords(fileTypes, words = [], fileInDirectory=''):
	'Get files which have a given file type, but with do not contain a word in a list.'
	filesWithFileTypes = []
	for filePath in getFilePaths(fileInDirectory):
		for fileType in fileTypes:
			if isFileWithFileTypeWithoutWords(fileType, filePath, words):
				filesWithFileTypes.append(filePath)
	filesWithFileTypes.sort()
	return filesWithFileTypes

def getFilesWithFileTypesWithoutWordsRecursively(fileTypes, words = [], fileInDirectory=''):
	'Get files recursively which have a given file type, but with do not contain a word in a list.'
	filesWithFileTypesRecursively = []
	for filePath in getFilePathsRecursively(fileInDirectory):
		for fileType in fileTypes:
			if isFileWithFileTypeWithoutWords(fileType, filePath, words):
				filesWithFileTypesRecursively.append(filePath)
	filesWithFileTypesRecursively.sort()
	return filesWithFileTypesRecursively

def getFilesWithFileTypeWithoutWords(fileType, words = [], fileInDirectory=''):
	'Get files which have a given file type, but with do not contain a word in a list.'
	filesWithFileType = []
	for filePath in getFilePaths(fileInDirectory):
		if isFileWithFileTypeWithoutWords(fileType, filePath, words):
			filesWithFileType.append(filePath)
	filesWithFileType.sort()
	return filesWithFileType

def getFileText(fileName, printWarning=True, readMode='r'):
	'Get the entire text of a file.'
	if '.zip/' in fileName:
		zipfilename = fileName[:fileName.rfind('.zip/')+4]
		subpath = fileName[fileName.rfind('.zip/')+5:]

		try:
			z = zipfile.ZipFile(zipfilename, 'r')
			f = z.open(subpath, 'r')
			fileText = f.read()
			f.close()
			z.close()
			return fileText
		except KeyError:
			if printWarning:
				print('The file ' + fileName + ' does not exist.')
			return ''
	try:
		f = open(fileName, readMode)
		fileText = f.read()
		f.close()
		return fileText
	except IOError:
		if printWarning:
			print('The file ' + fileName + ' does not exist.')
	
	return ''

def getFileTextInFileDirectory(fileInDirectory, fileName, readMode='r'):
	'Get the entire text of a file in the directory of the file in directory.'
	absoluteFilePathInFileDirectory = os.path.join(os.path.dirname(fileInDirectory), fileName)
	return getFileText(absoluteFilePathInFileDirectory, True, readMode)

def getFundamentalsPath(subName=''):
	'Get the evaluate_fundamentals directory path.'
	return getJoinedPath(getGeometryUtilitiesPath('evaluate_fundamentals'), subName)

def getGeometryDictionary(folderName):
	'Get to the geometry name path dictionary.'
	geometryDictionary={}
	geometryDirectory = getGeometryPath()
	addToNamePathDictionary(os.path.join(geometryDirectory, folderName), geometryDictionary)
	geometryPluginsDirectory = getFabmetheusUtilitiesPath('geometry_plugins')
	addToNamePathDictionary(os.path.join(geometryPluginsDirectory, folderName), geometryDictionary)
	return geometryDictionary

def getGeometryPath(subName=''):
	'Get the geometry directory path.'
	return getJoinedPath(getFabmetheusUtilitiesPath('geometry'), subName)

def getGeometryToolsPath(subName=''):
	'Get the geometry tools directory path.'
	return getJoinedPath(getGeometryPath('geometry_tools'), subName)

def getGeometryUtilitiesPath(subName=''):
	'Get the geometry_utilities directory path.'
	return getJoinedPath(getGeometryPath('geometry_utilities'), subName)

def getInterpretPluginsPath(subName=''):
	'Get the interpret plugins directory path.'
	return getJoinedPath(getFabmetheusToolsPath('interpret_plugins'), subName)

def getJoinedPath(path, subName=''):
	'Get the joined file path.'
	if subName == '':
		return path
	return os.path.join(path, subName)

def getModuleWithDirectoryPath(directoryPath, fileName):
	'Get the module from the fileName and folder name.'
	if fileName == '':
		print('The file name in getModule in archive was empty.')
		return None
	originalSystemPath = sys.path[:]
	try:
		sys.path.insert(0, directoryPath)
		folderPluginsModule = __import__(fileName)
		sys.path = originalSystemPath
		return folderPluginsModule
	except:
		sys.path = originalSystemPath
		print('')
		print('Exception traceback in getModuleWithDirectoryPath in archive:')
		traceback.print_exc(file=sys.stdout)
		print('')
		print('That error means; could not import a module with the fileName ' + fileName)
		print('and an absolute directory name of ' + directoryPath)
		print('')
	return None

def getModuleWithPath(path):
	'Get the module from the path.'
	return getModuleWithDirectoryPath(os.path.dirname(path), os.path.basename(path))

def getPluginFileNamesFromDirectoryPath(directoryPath):
	'Get the file names of the python plugins in the directory path.'
	fileInDirectory = os.path.join(directoryPath, '__init__.py')
	return getFileNamesByFilePaths(getPythonFileNamesExceptInit(fileInDirectory))

def getProfilesPath(subName=''):
	'Get the profiles directory path, which is the settings directory joined with profiles.'
	return getJoinedPath(getSettingsPath('profiles'), subName)

def getPythonDirectoryNames(directoryName):
	'Get the python directories.'
	pythonDirectoryNames = []
	directory = os.listdir(directoryName)
	for fileName in directory:
		subdirectoryName = os.path.join(directoryName, fileName)
		if os.path.isdir(subdirectoryName):
			if os.path.isfile(os.path.join(subdirectoryName, '__init__.py')):
				pythonDirectoryNames.append(subdirectoryName)
	return pythonDirectoryNames

def getPythonDirectoryNamesRecursively(directoryName=''):
	'Get the python directories recursively.'
	recursivePythonDirectoryNames = []
	if directoryName == '':
		directoryName = os.getcwd()
	if os.path.isfile(os.path.join(directoryName, '__init__.py')):
		recursivePythonDirectoryNames.append(directoryName)
		pythonDirectoryNames = getPythonDirectoryNames(directoryName)
		for pythonDirectoryName in pythonDirectoryNames:
			recursivePythonDirectoryNames += getPythonDirectoryNamesRecursively(pythonDirectoryName)
	else:
		return []
	return recursivePythonDirectoryNames

def getPythonFileNamesExceptInit(fileInDirectory=''):
	'Get the python fileNames of the directory which the fileInDirectory is in, except for the __init__.py file.'
	pythonFileNamesExceptInit = getFilesWithFileTypeWithoutWords('py', ['__init__.py'], fileInDirectory)
	pythonFileNamesExceptInit.sort()
	return pythonFileNamesExceptInit

def getPythonFileNamesExceptInitRecursively(directoryName=''):
	'Get the python fileNames of the directory recursively, except for the __init__.py files.'
	pythonDirectoryNames = getPythonDirectoryNamesRecursively(directoryName)
	pythonFileNamesExceptInitRecursively = []
	for pythonDirectoryName in pythonDirectoryNames:
		pythonFileNamesExceptInitRecursively += getPythonFileNamesExceptInit(os.path.join(pythonDirectoryName, '__init__.py'))
	pythonFileNamesExceptInitRecursively.sort()
	return pythonFileNamesExceptInitRecursively

def getSettingsPath(subName=''):
	'Get the settings directory path, which is the home directory joined with .skeinforge.'
	global globalTemporarySettingsPath
	return getJoinedPath(globalTemporarySettingsPath, subName)

def getSkeinforgePath(subName=''):
	'Get the skeinforge directory path.'
	return getJoinedPath(getFabmetheusPath('skeinforge_application'), subName)

def getSkeinforgePluginsPath(subName=''):
	'Get the skeinforge plugins directory path.'
	return getJoinedPath(getSkeinforgePath('skeinforge_plugins'), subName)

def getSummarizedFileName(fileName):
	'Get the fileName basename if the file is in the current working directory, otherwise return the original full name.'
	if os.getcwd() == os.path.dirname(fileName):
		return os.path.basename(fileName)
	return fileName

def getTemplatesPath(subName=''):
	'Get the templates directory path.'
	return getJoinedPath(getFabmetheusUtilitiesPath('templates'), subName)

def getTextIfEmpty(fileName, text):
	'Get the text from a file if it the text is empty.'
	if text != '':
		return text
	return getFileText(fileName)

def getTextLines(text):
	'Get the all the lines of text of a text.'
	if '\r' in text:
		text = text.replace('\r', '\n').replace('\n\n', '\n')
	textLines = text.split('\n')
	if len(textLines) == 1:
		if textLines[0] == '':
			return []
	return textLines

def getUntilDot(text):
	'Get the text until the last dot, if any.'
	dotIndex = text.rfind('.')
	if dotIndex < 0:
		return text
	return text[: dotIndex]

def getVersionFileName():
	'Get the file name of the version date.getFabmetheusUtilitiesPath(subName='')'
	return getFabmetheusUtilitiesPath('version.txt')

def isFileWithFileTypeWithoutWords(fileType, fileName, words):
	'Determine if file has a given file type, but with does not contain a word in a list.'
	fileName = os.path.basename(fileName)
	fileTypeDot = '.' + fileType
	if not fileName.endswith(fileTypeDot):
		return False
	for word in words:
		if fileName.find(word) >= 0:
			return False
	return True

def makeDirectory(directoryPath):
	'Make a directory if it does not already exist.'
	if os.path.isdir(directoryPath):
		return
	try:
		print('The following directory was made:')
		print(os.path.abspath(directoryPath))
		os.makedirs(directoryPath)
	except OSError:
		print('Skeinforge can not make the directory %s so give it read/write permission for that directory and the containing directory.' % directoryPath)

def removeBackupFilesByType(fileType):
	'Remove backup files by type.'
	backupFilePaths = getFilesWithFileTypesWithoutWordsRecursively([fileType + '~'])
	for backupFilePath in backupFilePaths:
		os.remove(backupFilePath)

def removeBackupFilesByTypes(fileTypes):
	'Remove backup files by types.'
	for fileType in fileTypes:
		removeBackupFilesByType(fileType)

def writeFileMessageEnd(end, fileName, fileText, message):
	'Write to a fileName with a suffix and print a message.'
	suffixFileName = getUntilDot(fileName) + end
	writeFileText(suffixFileName, fileText)
	print(message + getSummarizedFileName(suffixFileName))

def writeFileText(fileName, fileText, writeMode='w+'):
	'Write a text to a file.'
	try:
		file = open(fileName, writeMode)
		file.write(fileText)
		file.close()
	except IOError:
		print('The file ' + fileName + ' can not be written to.')
