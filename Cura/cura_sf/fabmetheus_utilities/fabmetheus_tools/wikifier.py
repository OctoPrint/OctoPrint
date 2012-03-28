"""
Wikifier is a script to add spaces to the pydoc files and move them to the documentation folder.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities import archive
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import settings
import cStringIO
import os


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


globalWikiLinkStart = '[<a href='


def addToHeadings(headingLineTable, headings, line):
	'Add the line to the headings.'
	for depth in xrange(4, -1, -1):
		equalSymbolLength = depth + 2
		if line[: equalSymbolLength] == '=' * equalSymbolLength:
			headings.append(Heading(depth).getFromLine(headingLineTable, line))
			return

def getLinkLine(line):
	'Get the link line with the wiki style link converted into a hypertext link.'
	linkStartIndex = line.find(globalWikiLinkStart)
	squareEndBracketIndex = line.find(']', linkStartIndex)
	greaterThanIndex = line.find('>', linkStartIndex, squareEndBracketIndex)
	greaterThanIndexPlusOne = greaterThanIndex + 1
	closeATagIndex = line.find('</a>', greaterThanIndexPlusOne, squareEndBracketIndex)
	linkText = line[closeATagIndex + len('</a>') + 1: squareEndBracketIndex]
	linkLine = line[: linkStartIndex] + line[linkStartIndex + 1: greaterThanIndexPlusOne] + linkText + '</a>' + line[squareEndBracketIndex + 1 :]
	return linkLine

def getNavigationHypertext(fileText, transferredFileNameIndex, transferredFileNames):
	'Get the hypertext help with navigation lines.'
	helpTextEnd = fileText.find('</p>')
	helpTextStart = fileText.find('<p>')
	helpText = fileText[helpTextStart : helpTextEnd]
	lines = archive.getTextLines(helpText)
	headings = []
	headingLineTable = {}
	for line in lines:
		addToHeadings(headingLineTable, headings, line)
	headingsToBeenAdded = True
	output = cStringIO.StringIO()
	for line in lines:
		if line[: 2] == '==':
			if headingsToBeenAdded:
				output.write('<br />\n')
				for heading in headings:
					heading.addToOutput(output)
				output.write('<br />\n')
				headingsToBeenAdded = False
			if line in headingLineTable:
				line = headingLineTable[line]
		if '&lt;a href=' in line:
			line = line.replace('&lt;', '<').replace('&gt;', '>')
		while globalWikiLinkStart in line and ']' in line:
			line = getLinkLine(line)
		output.write(line + '\n')
	helpText = output.getvalue()
	previousFileName = 'contents.html'
	previousIndex = transferredFileNameIndex - 1
	if previousIndex >= 0:
		previousFileName = transferredFileNames[previousIndex]
	previousLinkText = '<a href="%s">Previous</a>' % previousFileName
	nextLinkText = getNextLinkText(transferredFileNames, transferredFileNameIndex + 1)
	navigationLine = getNavigationLine('<a href="contents.html">Contents</a>', previousLinkText, nextLinkText)
	helpText = navigationLine + helpText + '<br />\n<br />\n' + navigationLine + '<hr>\n'
	return fileText[: helpTextStart] + helpText + fileText[helpTextEnd :]

def getNavigationLine(contentsLinkText, previousLinkText, nextLinkText):
	'Get the wrapped pydoc hypertext help.'
	return '<p>\n%s / %s / %s\n</p>\n' % (previousLinkText, nextLinkText, contentsLinkText)

def getNextLinkText(hypertextFiles, nextIndex):
	'Get the next link text.'
	nextFileName = 'contents.html'
	if nextIndex < len(hypertextFiles):
		nextFileName = hypertextFiles[nextIndex]
	return '<a href="%s">Next</a>' % nextFileName

def getWrappedHypertext(fileText, hypertextFileIndex, hypertextFiles):
	'Get the wrapped pydoc hypertext help.'
	helpTextEnd = fileText.find('</p>')
	if helpTextEnd < 0:
		print('Failed to find the helpTextEnd in getWrappedHypertext in docwrap.')
	helpTextStart = fileText.find('<p>')
	if helpTextStart < 0:
		print('Failed to find the helpTextStart in getWrappedHypertext in docwrap.')
	helpText = fileText[helpTextStart : helpTextEnd]
	helpText = helpText.replace('&nbsp;', ' ')
	return fileText[: helpTextStart] + helpText + fileText[helpTextEnd :]

def readWriteDeleteHypertextHelp(documentDirectoryPath, hypertextFileIndex, hypertextFiles, transferredFileNames):
	'Read the pydoc hypertext help documents, write them in the documentation folder then delete the originals.'
	fileName = os.path.basename(hypertextFiles[hypertextFileIndex])
	print('readWriteDeleteHypertextHelp ' + fileName)
	filePath = os.path.join(documentDirectoryPath, fileName)
	fileText = archive.getFileText(fileName)
	fileText = getWrappedHypertext(fileText, hypertextFileIndex, hypertextFiles)
	if fileText.find('This page is in the table of contents.') > - 1:
		fileText = fileText.replace('This page is in the table of contents.', '')
		transferredFileNames.append(fileName)
	archive.writeFileText(filePath, fileText)
	os.remove(fileName)

def readWriteNavigationHelp(documentDirectoryPath, transferredFileNameIndex, transferredFileNames):
	'Read the hypertext help documents, and add the navigation lines to them.'
	fileName = os.path.basename(transferredFileNames[transferredFileNameIndex])
	print('readWriteNavigationHelp ' + fileName)
	filePath = os.path.join(documentDirectoryPath, fileName)
	fileText = archive.getFileText(filePath)
	fileText = getNavigationHypertext(fileText, transferredFileNameIndex, transferredFileNames)
	archive.writeFileText(filePath, fileText)

def removeFilesInDirectory(directoryPath):
	'Remove all the files in a directory.'
	fileNames = os.listdir(directoryPath)
	for fileName in fileNames:
		filePath = os.path.join(directoryPath, fileName)
		os.remove(filePath)

def writeContentsFile(documentDirectoryPath, hypertextFiles):
	'Write the contents file.'
	output = cStringIO.StringIO()
	output.write('<html>\n  <head>\n    <title>Contents</title>\n  </head>\n  <body>\n')
	navigationLine = getNavigationLine('Contents', 'Previous', getNextLinkText(hypertextFiles, 0))
	output.write(navigationLine)
	for hypertextFile in hypertextFiles:
		writeContentsLine(hypertextFile, output)
	output.write(navigationLine)
	output.write('  </body>\n</html>\n')
	filePath = os.path.join( documentDirectoryPath, 'contents.html')
	archive.writeFileText(filePath, output.getvalue())

def writeContentsLine(hypertextFile, output):
	'Write a line of the contents file.'
	summarizedFileName = hypertextFile[: hypertextFile.rfind('.')]
	numberOfDots = summarizedFileName.count('.')
	prefixSpaces = '&nbsp;&nbsp;' * numberOfDots
	if numberOfDots > 0:
		summarizedFileName = summarizedFileName[summarizedFileName.rfind('.') + 1 :]
	capitalizedSummarizedFileName = settings.getEachWordCapitalized(summarizedFileName)
	output.write('%s<a href="%s">%s</a><br>\n' % (prefixSpaces, hypertextFile, capitalizedSummarizedFileName))

def writeHypertext():
	'Run pydoc, then read, write and delete each of the files.'
	shellCommand = 'pydoc -w ./'
	commandResult = os.system(shellCommand)
	if commandResult != 0:
		print('Failed to execute the following command in writeHypertext in docwrap.')
		print(shellCommand)
	hypertextFiles = archive.getFilesWithFileTypeWithoutWords('html')
	if len( hypertextFiles ) <= 0:
		print('Failed to find any help files in writeHypertext in docwrap.')
		return
	documentDirectoryPath = archive.getAbsoluteFolderPath( hypertextFiles[0], 'documentation')
	removeFilesInDirectory(documentDirectoryPath)
	sortedReplaceFiles = []
	for hypertextFile in hypertextFiles:
		sortedReplaceFiles.append(hypertextFile.replace('.html', '. html'))
	sortedReplaceFiles.sort()
	hypertextFiles = []
	for sortedReplaceFile in sortedReplaceFiles:
		hypertextFiles.append(sortedReplaceFile.replace('. html', '.html'))
	transferredFileNames = []
	for hypertextFileIndex in xrange(len(hypertextFiles)):
		readWriteDeleteHypertextHelp(documentDirectoryPath, hypertextFileIndex, hypertextFiles, transferredFileNames)
	for transferredFileNameIndex in xrange(len(transferredFileNames)):
		readWriteNavigationHelp(documentDirectoryPath, transferredFileNameIndex, transferredFileNames)
	writeContentsFile(documentDirectoryPath, transferredFileNames)
	print('%s files were wrapped.' % len(transferredFileNames))


class Heading:
	'A class to hold the heading and subheadings.'
	def __init__(self, depth=0):
		'Initialize.'
		self.depth = depth

	def addToOutput(self, output):
		'Add to the output.'
		line = '&nbsp;&nbsp;' * self.depth + '<a href="#%s">%s</a><br />\n' % (self.name, self.name)
		output.write(line)

	def getFromLine(self, headingLineTable, line):
		'Get the heading from a line.'
		heading = 'h%s' % (self.depth + 2)
		nextLine = '\n<hr>\n'
		if self.depth > 0:
			nextLine = '\n'
		self.name = line.replace('=', '').replace('<br>', '')
		name = self.name
		headingLine = '<a name="%s" id="%s"></a><%s>%s</%s>%s' % (name, name, heading, name, heading, nextLine)
		headingLineTable[line] = headingLine
		return self


def main():
	'Display the craft dialog.'
	writeHypertext()

if __name__ == '__main__':
	main()
