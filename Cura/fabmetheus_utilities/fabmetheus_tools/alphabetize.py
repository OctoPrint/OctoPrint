"""
Alphabetize is a script to alphabetize functions and signatures.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities import archive
import cStringIO
import os


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def addTogetherList(functionList, togetherLists):
	'Add the togetherList to the togetherLists is the sorted is different.'
	sortedList = functionList[:]
	sortedList.sort(compareFunctionName)
	togetherList = None
	for functionIndex in xrange(len(functionList)):
		function = functionList[functionIndex]
		sorted = sortedList[functionIndex]
		if function != sorted:
			together = (function, sorted)
			if togetherList == None:
				togetherList = []
				togetherLists.append(togetherList)
			togetherList.append(together)

def compareFunctionName(first, second):
	'Compare the function names.'
	first = getConvertedName(first)
	second = getConvertedName(second)
	if first < second:
		return -1
	return first < second

def getConvertedName(name):
	'Get converted name with init at the beginning and main at the endCompare the function names.'
	if name == 'def __init__':
		return 'def !__init__'
	if name == 'def main':
		return 'def |main'
	return name.lower()

def getFunctionLists(fileName):
	'Get the function lists in the file.'
	fileText = archive.getFileText(fileName)
	functionList = []
	functionLists = [functionList]
	lines = archive.getTextLines(fileText)
	for line in lines:
		lineStripped = line.strip()
		if lineStripped.startswith('def '):
			bracketIndex = lineStripped.find('(')
			if bracketIndex > -1:
				lineStripped = lineStripped[: bracketIndex]
			functionList.append(lineStripped)
		elif line.startswith('class'):
			functionList = []
			functionLists.append(functionList)
	return functionLists

def getFunctionsWithStringByFileName(fileName, searchString):
	'Get the functions with the search string in the file.'
	fileText = archive.getFileText(fileName)
	functions = []
	lines = archive.getTextLines(fileText)
	for line in lines:
		lineStripped = line.strip()
#		if lineStripped.startswith('def ') and searchString in lineStripped and '=' in lineStripped:
		if lineStripped.startswith('def ') and searchString in lineStripped:
			if '(self, ' not in lineStripped or lineStripped.count(',') > 1:
				functions.append(lineStripped[len('def ') :].strip())
	functions.sort()
	return functions

def getFunctionsWithStringByFileNames(fileNames, searchString):
	'Get the functions with the search string in the files.'
	functions = []
	for fileName in fileNames:
		functions += getFunctionsWithStringByFileName(fileName, searchString)
	functions.sort()
	return functions

def getParameterSequence(functionName):
	'Get the parameter sequence.'
	parameterDictionary = {}
	parameterSequence = []
	parameterText = functionName[functionName.find('(') + 1 :].replace('xmlElement', 'elementNode')
	snippet = Snippet(0, parameterText)
	strippedParameters = []
	for parameter in snippet.parameters:
		strippedParameter = parameter.strip()
		if strippedParameter != 'self':
			strippedParameters.append(strippedParameter)
	for parameterIndex, parameter in enumerate(strippedParameters):
		parameterDictionary[parameter] = parameterIndex
	sortedParameters = strippedParameters[:]
	sortedParameters.sort()
	for sortedParameter in sortedParameters:
		parameterSequence.append(parameterDictionary[sortedParameter])
	return parameterSequence

def getSnippetsByFileName(fileName, functionName):
	'Get the function signature snippets by the file name.'
	fileText = archive.getFileText(fileName)
	snippets = []
	functionStart = functionName[: functionName.find('(') + 1]
	tokenEnd = getTokenEnd(0, fileText, functionStart)
	while tokenEnd != -1:
		snippet = Snippet(tokenEnd, fileText)
		snippets.append(snippet)
		tokenEnd = getTokenEnd(snippet.characterIndex, fileText, functionStart)
	return snippets

def getTogetherLists(fileName):
	'Get the lists of the unsorted and sorted functions in the file.'
	functionLists = getFunctionLists(fileName)
	togetherLists = []
	for functionList in functionLists:
		addTogetherList(functionList, togetherLists)
	return togetherLists

def getTokenEnd(characterIndex, fileText, token):
	'Get the token end index for the file text and token.'
	tokenIndex = fileText.find(token, characterIndex)
	if tokenIndex == -1:
		return -1
	return tokenIndex + len(token)

def printTogetherListsByFileNames(fileNames):
	'Print the together lists of the file names, if the file name has a together list.'
	for fileName in fileNames:
		togetherLists = getTogetherLists(fileName)
		if len(togetherLists) > 0:
			for togetherList in togetherLists:
				for together in togetherList:
					function = together[0]
					sorted = together[1]
			return


class EndCharacterMonad:
	'A monad to return the parent monad when it encounters the end character.'
	def __init__(self, endCharacter, parentMonad):
		'Initialize.'
		self.endCharacter = endCharacter
		self.parentMonad = parentMonad

	def getNextMonad(self, character):
		'Get the next monad.'
		self.getSnippet().input.write(character)
		if character == self.endCharacter:
			return self.parentMonad
		return self

	def getSnippet(self):
		'Get the snippet.'
		return self.parentMonad.getSnippet()


class ParameterMonad:
	'A monad to handle parameters.'
	def __init__(self, snippet):
		'Initialize.'
		self.snippet = snippet

	def addParameter(self):
		'Add parameter to the snippet.'
		parameterString = self.snippet.input.getvalue()
		if len(parameterString) != 0:
			self.snippet.input = cStringIO.StringIO()
			self.snippet.parameters.append(parameterString)

	def getNextMonad(self, character):
		'Get the next monad.'
		if character == '"':
			self.snippet.input.write(character)
			return EndCharacterMonad('"', self)
		if character == '"':
			self.snippet.input.write(character)
			return EndCharacterMonad('"', self)
		if character == '(':
			self.snippet.input.write(character)
			return EndCharacterMonad(')', self)
		if character == ')':
			self.addParameter()
			return None
		if character == ',':
			self.addParameter()
			return self
		self.snippet.input.write(character)
		return self

	def getSnippet(self):
		'Get the snippet.'
		return self.snippet


class Snippet:
	'A class to get the variables for a function.'
	def __init__(self, characterIndex, fileText):
		'Initialize.'
		self.characterIndex = characterIndex
		self.input = cStringIO.StringIO()
		self.parameters = []
		monad = ParameterMonad(self)
		for characterIndex in xrange(self.characterIndex, len(fileText)):
			character = fileText[characterIndex]
			monad = monad.getNextMonad(character)
			if monad == None:
				return

	def __repr__(self):
		'Get the string representation of this Snippet.'
		return '%s %s' % (self.characterIndex, self.parameters)


def main():
	'Run main function.'
#	printTogetherListsByFileNames(archive.getPythonFileNamesExceptInitRecursively('/home/enrique/Desktop/fabmetheus'))
	functions = getFunctionsWithStringByFileNames(archive.getPythonFileNamesExceptInitRecursively('/home/enrique/Desktop/fabmetheus'), ', xmlElement')
	print(functions)

if __name__ == "__main__":
	main()
