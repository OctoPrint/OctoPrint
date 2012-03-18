"""
Evaluate expressions.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.geometry_utilities.evaluate_elements import setting
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import settings
import math
import os
import sys
import traceback


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


globalModuleFunctionsDictionary = {}


def addPrefixDictionary(dictionary, keys, value):
	'Add prefixed key values to dictionary.'
	for key in keys:
		dictionary[key.lstrip('_')] = value

def addQuoteWord(evaluatorWords, word):
	'Add quote word and remainder if the word starts with a quote character or dollar sign, otherwise add the word.'
	if len(word) < 2:
		evaluatorWords.append(word)
		return
	firstCharacter = word[0]
	if firstCharacter == '$':
		dotIndex = word.find('.', 1)
		if dotIndex > -1:
			evaluatorWords.append(word[: dotIndex])
			evaluatorWords.append(word[dotIndex :])
			return
	if firstCharacter != '"' and firstCharacter != "'":
		evaluatorWords.append(word)
		return
	nextQuoteIndex = word.find(firstCharacter, 1)
	if nextQuoteIndex < 0 or nextQuoteIndex == len(word) - 1:
		evaluatorWords.append(word)
		return
	nextQuoteIndex += 1
	evaluatorWords.append(word[: nextQuoteIndex])
	evaluatorWords.append(word[nextQuoteIndex :])

def addToPathsRecursively(paths, vector3Lists):
	'Add to vector3 paths recursively.'
	if vector3Lists.__class__ == Vector3 or vector3Lists.__class__ .__name__ == 'Vector3Index':
		paths.append([ vector3Lists ])
		return
	path = []
	for vector3List in vector3Lists:
		if vector3List.__class__ == list:
			addToPathsRecursively(paths, vector3List)
		elif vector3List.__class__ == Vector3:
			path.append(vector3List)
	if len(path) > 0:
		paths.append(path)

def addValueToEvaluatedDictionary(elementNode, evaluatedDictionary, key):
	'Get the evaluated dictionary.'
	value = getEvaluatedValueObliviously(elementNode, key)
	if value == None:
		valueString = str(elementNode.attributes[key])
		print('Warning, addValueToEvaluatedDictionary in evaluate can not get a value for:')
		print(valueString)
		evaluatedDictionary[key + '__Warning__'] = 'Can not evaluate: ' + valueString.replace('"', ' ').replace( "'", ' ')
	else:
		evaluatedDictionary[key] = value

def addVector3ToElementNode(elementNode, key, vector3):
	'Add vector3 to xml element.'
	elementNode.attributes[key] = '[%s,%s,%s]' % (vector3.x, vector3.y, vector3.z)

def compareExecutionOrderAscending(module, otherModule):
	'Get comparison in order to sort modules in ascending execution order.'
	if module.globalExecutionOrder < otherModule.globalExecutionOrder:
		return -1
	if module.globalExecutionOrder > otherModule.globalExecutionOrder:
		return 1
	if module.__name__ < otherModule.__name__:
		return -1
	return int(module.__name__ > otherModule.__name__)

def convertToPaths(dictionary):
	'Recursively convert any ElementNodes to paths.'
	if dictionary.__class__ == Vector3 or dictionary.__class__.__name__ == 'Vector3Index':
		return
	keys = getKeys(dictionary)
	if keys == None:
		return
	for key in keys:
		value = dictionary[key]
		if value.__class__.__name__ == 'ElementNode':
			if value.xmlObject != None:
				dictionary[key] = getFloatListListsByPaths(value.xmlObject.getPaths())
		else:
			convertToPaths(dictionary[key])

def convertToTransformedPaths(dictionary):
	'Recursively convert any ElementNodes to paths.'
	if dictionary.__class__ == Vector3 or dictionary.__class__.__name__ == 'Vector3Index':
		return
	keys = getKeys(dictionary)
	if keys == None:
		return
	for key in keys:
		value = dictionary[key]
		if value.__class__.__name__ == 'ElementNode':
			if value.xmlObject != None:
				dictionary[key] = value.xmlObject.getTransformedPaths()
		else:
			convertToTransformedPaths(dictionary[key])

def executeLeftOperations( evaluators, operationLevel ):
	'Evaluate the expression value from the numeric and operation evaluators.'
	for negativeIndex in xrange( - len(evaluators), - 1 ):
		evaluatorIndex = negativeIndex + len(evaluators)
		evaluators[evaluatorIndex].executeLeftOperation( evaluators, evaluatorIndex, operationLevel )

def executeNextEvaluatorArguments(evaluator, evaluators, evaluatorIndex, nextEvaluator):
	'Execute the nextEvaluator arguments.'
	if evaluator.value == None:
		print('Warning, executeNextEvaluatorArguments in evaluate can not get a evaluator.value for:')
		print(evaluatorIndex)
		print(evaluators)
		print(evaluator)
		return
	nextEvaluator.value = evaluator.value(*nextEvaluator.arguments)
	del evaluators[evaluatorIndex]

def executePairOperations(evaluators, operationLevel):
	'Evaluate the expression value from the numeric and operation evaluators.'
	for negativeIndex in xrange(1 - len(evaluators), - 1):
		evaluatorIndex = negativeIndex + len(evaluators)
		evaluators[evaluatorIndex].executePairOperation(evaluators, evaluatorIndex, operationLevel)

def getBracketEvaluators(bracketBeginIndex, bracketEndIndex, evaluators):
	'Get the bracket evaluators.'
	return getEvaluatedExpressionValueEvaluators(evaluators[bracketBeginIndex + 1 : bracketEndIndex])

def getBracketsExist(evaluators):
	'Evaluate the expression value.'
	bracketBeginIndex = None
	for negativeIndex in xrange( - len(evaluators), 0 ):
		bracketEndIndex = negativeIndex + len(evaluators)
		evaluatorEnd = evaluators[ bracketEndIndex ]
		evaluatorWord = evaluatorEnd.word
		if evaluatorWord in ['(', '[', '{']:
			bracketBeginIndex = bracketEndIndex
		elif evaluatorWord in [')', ']', '}']:
			if bracketBeginIndex == None:
				print('Warning, bracketBeginIndex in evaluateBrackets in evaluate is None.')
				print('This may be because the brackets are not balanced.')
				print(evaluators)
				del evaluators[ bracketEndIndex ]
				return
			evaluators[ bracketBeginIndex ].executeBracket(bracketBeginIndex, bracketEndIndex, evaluators)
			evaluators[ bracketBeginIndex ].word = None
			return True
	return False

def getBracketValuesDeleteEvaluator(bracketBeginIndex, bracketEndIndex, evaluators):
	'Get the bracket values and delete the evaluator.'
	evaluatedExpressionValueEvaluators = getBracketEvaluators(bracketBeginIndex, bracketEndIndex, evaluators)
	bracketValues = []
	for evaluatedExpressionValueEvaluator in evaluatedExpressionValueEvaluators:
		bracketValues.append( evaluatedExpressionValueEvaluator.value )
	del evaluators[ bracketBeginIndex + 1: bracketEndIndex + 1 ]
	return bracketValues

def getCapitalizedSuffixKey(prefix, suffix):
	'Get key with capitalized suffix.'
	if prefix == '' or prefix.endswith('.'):
		return prefix + suffix
	return prefix + suffix[:1].upper()+suffix[1:]

def getDictionarySplitWords(dictionary, value):
	'Get split line for evaluators.'
	if getIsQuoted(value):
		return [value]
	for dictionaryKey in dictionary.keys():
		value = value.replace(dictionaryKey, ' ' + dictionaryKey + ' ')
	dictionarySplitWords = []
	for word in value.split():
		dictionarySplitWords.append(word)
	return dictionarySplitWords

def getElementNodeByKey(elementNode, key):
	'Get the xml element by key.'
	if key not in elementNode.attributes:
		return None
	word = str(elementNode.attributes[key]).strip()
	evaluatedLinkValue = getEvaluatedLinkValue(elementNode, word)
	if evaluatedLinkValue.__class__.__name__ == 'ElementNode':
		return evaluatedLinkValue
	print('Warning, could not get ElementNode in getElementNodeByKey in evaluate for:')
	print(key)
	print(evaluatedLinkValue)
	print(elementNode)
	return None

def getElementNodeObject(evaluatedLinkValue):
	'Get ElementNodeObject.'
	if evaluatedLinkValue.__class__.__name__ != 'ElementNode':
		print('Warning, could not get ElementNode in getElementNodeObject in evaluate for:')
		print(evaluatedLinkValue.__class__.__name__)
		print(evaluatedLinkValue)
		return None
	if evaluatedLinkValue.xmlObject == None:
		print('Warning, evaluatedLinkValue.xmlObject is None in getElementNodeObject in evaluate for:')
		print(evaluatedLinkValue)
		return None
	return evaluatedLinkValue.xmlObject

def getElementNodesByKey(elementNode, key):
	'Get the xml elements by key.'
	if key not in elementNode.attributes:
		return []
	word = str(elementNode.attributes[key]).strip()
	evaluatedLinkValue = getEvaluatedLinkValue(elementNode, word)
	if evaluatedLinkValue.__class__.__name__ == 'ElementNode':
		return [evaluatedLinkValue]
	if evaluatedLinkValue.__class__ == list:
		return evaluatedLinkValue
	print('Warning, could not get ElementNodes in getElementNodesByKey in evaluate for:')
	print(key)
	print(evaluatedLinkValue)
	print(elementNode)
	return []

def getEndIndexConvertEquationValue( bracketEndIndex, evaluatorIndex, evaluators ):
	'Get the bracket end index and convert the equation value evaluators into a string.'
	evaluator = evaluators[evaluatorIndex]
	if evaluator.__class__ != EvaluatorValue:
		return bracketEndIndex
	if not evaluator.word.startswith('equation.'):
		return bracketEndIndex
	if evaluators[ evaluatorIndex + 1 ].word != ':':
		return bracketEndIndex
	valueBeginIndex = evaluatorIndex + 2
	equationValueString = ''
	for valueEvaluatorIndex in xrange( valueBeginIndex, len(evaluators) ):
		valueEvaluator = evaluators[ valueEvaluatorIndex ]
		if valueEvaluator.word == ',' or valueEvaluator.word == '}':
			if equationValueString == '':
				return bracketEndIndex
			else:
				evaluators[ valueBeginIndex ] = EvaluatorValue( equationValueString )
				valueDeleteIndex = valueBeginIndex + 1
				del evaluators[ valueDeleteIndex : valueEvaluatorIndex ]
			return bracketEndIndex - valueEvaluatorIndex + valueDeleteIndex
		equationValueString += valueEvaluator.word
	return bracketEndIndex

def getEvaluatedBoolean(defaultValue, elementNode, key):
	'Get the evaluated boolean.'
	if elementNode == None:
		return defaultValue
	if key in elementNode.attributes:
		return euclidean.getBooleanFromValue(getEvaluatedValueObliviously(elementNode, key))
	return defaultValue

def getEvaluatedDictionaryByCopyKeys(copyKeys, elementNode):
	'Get the evaluated dictionary by copyKeys.'
	evaluatedDictionary = {}
	for key in elementNode.attributes.keys():
		if key in copyKeys:
			evaluatedDictionary[key] = elementNode.attributes[key]
		else:
			addValueToEvaluatedDictionary(elementNode, evaluatedDictionary, key)
	return evaluatedDictionary

def getEvaluatedDictionaryByEvaluationKeys(elementNode, evaluationKeys):
	'Get the evaluated dictionary.'
	evaluatedDictionary = {}
	for key in elementNode.attributes.keys():
		if key in evaluationKeys:
			addValueToEvaluatedDictionary(elementNode, evaluatedDictionary, key)
	return evaluatedDictionary

def getEvaluatedExpressionValue(elementNode, value):
	'Evaluate the expression value.'
	try:
		return getEvaluatedExpressionValueBySplitLine(elementNode, getEvaluatorSplitWords(value))
	except:
		print('Warning, in getEvaluatedExpressionValue in evaluate could not get a value for:')
		print(value)
		traceback.print_exc(file=sys.stdout)
		return None

def getEvaluatedExpressionValueBySplitLine(elementNode, words):
	'Evaluate the expression value.'
	evaluators = []
	for wordIndex, word in enumerate(words):
		nextWord = ''
		nextWordIndex = wordIndex + 1
		if nextWordIndex < len(words):
			nextWord = words[nextWordIndex]
		evaluator = getEvaluator(elementNode, evaluators, nextWord, word)
		if evaluator != None:
			evaluators.append(evaluator)
	while getBracketsExist(evaluators):
		pass
	evaluatedExpressionValueEvaluators = getEvaluatedExpressionValueEvaluators(evaluators)
	if len( evaluatedExpressionValueEvaluators ) > 0:
		return evaluatedExpressionValueEvaluators[0].value
	return None

def getEvaluatedExpressionValueEvaluators(evaluators):
	'Evaluate the expression value from the numeric and operation evaluators.'
	for evaluatorIndex, evaluator in enumerate(evaluators):
		evaluator.executeCenterOperation(evaluators, evaluatorIndex)
	for negativeIndex in xrange(1 - len(evaluators), 0):
		evaluatorIndex = negativeIndex + len(evaluators)
		evaluators[evaluatorIndex].executeRightOperation(evaluators, evaluatorIndex)
	executeLeftOperations(evaluators, 200)
	for operationLevel in [80, 60, 40, 20, 15]:
		executePairOperations(evaluators, operationLevel)
	executeLeftOperations(evaluators, 13)
	executePairOperations(evaluators, 12)
	for negativeIndex in xrange(-len(evaluators), 0):
		evaluatorIndex = negativeIndex + len(evaluators)
		evaluators[evaluatorIndex].executePairOperation(evaluators, evaluatorIndex, 10)
	for evaluatorIndex in xrange(len(evaluators) - 1, -1, -1):
		evaluators[evaluatorIndex].executePairOperation(evaluators, evaluatorIndex, 0)
	return evaluators

def getEvaluatedFloat(defaultValue, elementNode, key):
	'Get the evaluated float.'
	if elementNode == None:
		return defaultValue
	if key in elementNode.attributes:
		return euclidean.getFloatFromValue(getEvaluatedValueObliviously(elementNode, key))
	return defaultValue

def getEvaluatedInt(defaultValue, elementNode, key):
	'Get the evaluated int.'
	if elementNode == None:
		return None
	if key in elementNode.attributes:
		try:
			return getIntFromFloatString(getEvaluatedValueObliviously(elementNode, key))
		except:
			print('Warning, could not evaluate the int.')
			print(key)
			print(elementNode.attributes[key])
	return defaultValue

def getEvaluatedIntByKeys(defaultValue, elementNode, keys):
	'Get the evaluated int by keys.'
	for key in keys:
		defaultValue = getEvaluatedInt(defaultValue, elementNode, key)
	return defaultValue

def getEvaluatedLinkValue(elementNode, word):
	'Get the evaluated link value.'
	if word == '':
		return ''
	if getStartsWithCurlyEqualRoundSquare(word):
		return getEvaluatedExpressionValue(elementNode, word)
	return word

def getEvaluatedString(defaultValue, elementNode, key):
	'Get the evaluated string.'
	if elementNode == None:
		return defaultValue
	if key in elementNode.attributes:
		return str(getEvaluatedValueObliviously(elementNode, key))
	return defaultValue

def getEvaluatedValue(defaultValue, elementNode, key):
	'Get the evaluated value.'
	if elementNode == None:
		return defaultValue
	if key in elementNode.attributes:
		return getEvaluatedValueObliviously(elementNode, key)
	return defaultValue

def getEvaluatedValueObliviously(elementNode, key):
	'Get the evaluated value.'
	value = str(elementNode.attributes[key]).strip()
	if key == 'id' or key == 'name' or key == 'tags':
		return value
	return getEvaluatedLinkValue(elementNode, value)

def getEvaluator(elementNode, evaluators, nextWord, word):
	'Get the evaluator.'
	if word in globalSplitDictionary:
		return globalSplitDictionary[word](elementNode, word)
	firstCharacter = word[: 1]
	if firstCharacter == "'" or firstCharacter == '"':
		if len(word) > 1:
			if firstCharacter == word[-1]:
				return EvaluatorValue(word[1 : -1])
	if firstCharacter == '$':
		return EvaluatorValue(word[1 :])
	dotIndex = word.find('.')
	functions = elementNode.getXMLProcessor().functions
	if dotIndex > -1 and len(word) > 1:
		if dotIndex == 0 and word[1].isalpha():
			return EvaluatorAttribute(elementNode, word)
		if dotIndex > 0:
			untilDot = word[: dotIndex]
			if untilDot in globalModuleEvaluatorDictionary:
				return globalModuleEvaluatorDictionary[untilDot](elementNode, word)
		if len(functions) > 0:
			if untilDot in functions[-1].localDictionary:
				return EvaluatorLocal(elementNode, word)
	if firstCharacter.isalpha() or firstCharacter == '_':
		if len(functions) > 0:
			if word in functions[-1].localDictionary:
				return EvaluatorLocal(elementNode, word)
		wordElement = elementNode.getElementNodeByID(word)
		if wordElement != None:
			if wordElement.getNodeName() == 'class':
				return EvaluatorClass(wordElement, word)
			if wordElement.getNodeName() == 'function':
				return EvaluatorFunction(wordElement, word)
		return EvaluatorValue(word)
	return EvaluatorNumeric(elementNode, word)

def getEvaluatorSplitWords(value):
	'Get split words for evaluators.'
	if value.startswith('='):
		value = value[len('=') :]
	if len(value) < 1:
		return []
	global globalDictionaryOperatorBegin
	uniqueQuoteIndex = 0
	word = ''
	quoteString = None
	quoteDictionary = {}
	for characterIndex in xrange(len(value)):
		character = value[characterIndex]
		if character == '"' or character == "'":
			if quoteString == None:
				quoteString = ''
			elif quoteString != None:
				if character == quoteString[: 1]:
					uniqueQuoteIndex = getUniqueQuoteIndex(uniqueQuoteIndex, value)
					uniqueToken = getTokenByNumber(uniqueQuoteIndex)
					quoteDictionary[uniqueToken] = quoteString + character
					character = uniqueToken
					quoteString = None
		if quoteString == None:
			word += character
		else:
			quoteString += character
	beginSplitWords = getDictionarySplitWords(globalDictionaryOperatorBegin, word)
	global globalSplitDictionaryOperator
	evaluatorSplitWords = []
	for beginSplitWord in beginSplitWords:
		if beginSplitWord in globalDictionaryOperatorBegin:
			evaluatorSplitWords.append(beginSplitWord)
		else:
			evaluatorSplitWords += getDictionarySplitWords(globalSplitDictionaryOperator, beginSplitWord)
	for evaluatorSplitWordIndex, evaluatorSplitWord in enumerate(evaluatorSplitWords):
		for quoteDictionaryKey in quoteDictionary.keys():
			if quoteDictionaryKey in evaluatorSplitWord:
				evaluatorSplitWords[evaluatorSplitWordIndex] = evaluatorSplitWord.replace(quoteDictionaryKey, quoteDictionary[quoteDictionaryKey])
	evaluatorTransitionWords = []
	for evaluatorSplitWord in evaluatorSplitWords:
		addQuoteWord(evaluatorTransitionWords, evaluatorSplitWord)
	return evaluatorTransitionWords

def getFloatListFromBracketedString( bracketedString ):
	'Get list from a bracketed string.'
	if not getIsBracketed( bracketedString ):
		return None
	bracketedString = bracketedString.strip().replace('[', '').replace(']', '').replace('(', '').replace(')', '')
	if len( bracketedString ) < 1:
		return []
	splitLine = bracketedString.split(',')
	floatList = []
	for word in splitLine:
		evaluatedFloat = euclidean.getFloatFromValue(word)
		if evaluatedFloat != None:
			floatList.append( evaluatedFloat )
	return floatList

def getFloatListListsByPaths(paths):
	'Get float lists by paths.'
	floatListLists = []
	for path in paths:
		floatListList = []
		for point in path:
			floatListList.append( point.getFloatList() )
	return floatListLists

def getIntFromFloatString(value):
	'Get the int from the string.'
	floatString = str(value).strip()
	if floatString == '':
		return None
	dotIndex = floatString.find('.')
	if dotIndex < 0:
		return int(value)
	return int( round( float(floatString) ) )

def getIsBracketed(word):
	'Determine if the word is bracketed.'
	if len(word) < 2:
		return False
	firstCharacter = word[0]
	lastCharacter = word[-1]
	if firstCharacter == '(' and lastCharacter == ')':
		return True
	return firstCharacter == '[' and lastCharacter == ']'

def getIsQuoted(word):
	'Determine if the word is quoted.'
	if len(word) < 2:
		return False
	firstCharacter = word[0]
	lastCharacter = word[-1]
	if firstCharacter == '"' and lastCharacter == '"':
		return True
	return firstCharacter == "'" and lastCharacter == "'"

def getKeys(repository):
	'Get keys for repository.'
	repositoryClass = repository.__class__
	if repositoryClass == list or repositoryClass == tuple:
		return range(len(repository))
	if repositoryClass == dict:
		return repository.keys()
	return None

def getLocalAttributeValueString(key, valueString):
	'Get the local attribute value string with augmented assignment.'
	augmentedStatements = '+= -= *= /= %= **='.split()
	for augmentedStatement in augmentedStatements:
		if valueString.startswith(augmentedStatement):
			return key + augmentedStatement[: -1] + valueString[len(augmentedStatement) :]
	return valueString

def getMatchingPlugins(elementNode, namePathDictionary):
	'Get the plugins whose names are in the attribute dictionary.'
	matchingPlugins = []
	namePathDictionaryCopy = namePathDictionary.copy()
	for key in elementNode.attributes:
		dotIndex = key.find('.')
		if dotIndex > - 1:
			keyUntilDot = key[: dotIndex]
			if keyUntilDot in namePathDictionaryCopy:
				pluginModule = archive.getModuleWithPath( namePathDictionaryCopy[ keyUntilDot ] )
				del namePathDictionaryCopy[ keyUntilDot ]
				if pluginModule != None:
					matchingPlugins.append( pluginModule )
	return matchingPlugins

def getNextChildIndex(elementNode):
	'Get the next childNode index.'
	for childNodeIndex, childNode in enumerate( elementNode.parentNode.childNodes ):
		if childNode == elementNode:
			return childNodeIndex + 1
	return len( elementNode.parentNode.childNodes )

def getPathByKey(defaultPath, elementNode, key):
	'Get path from prefix and xml element.'
	if key not in elementNode.attributes:
		return defaultPath
	word = str(elementNode.attributes[key]).strip()
	evaluatedLinkValue = getEvaluatedLinkValue(elementNode, word)
	if evaluatedLinkValue.__class__ == list:
		return getPathByList(evaluatedLinkValue)
	elementNodeObject = getElementNodeObject(evaluatedLinkValue)
	if elementNodeObject == None:
		return defaultPath
	return elementNodeObject.getPaths()[0]

def getPathByList(vertexList):
	'Get the paths by list.'
	if len(vertexList) < 1:
		return Vector3()
	if vertexList[0].__class__ != list:
		vertexList = [vertexList]
	path = []
	for floatList in vertexList:
		vector3 = getVector3ByFloatList(floatList, Vector3())
		path.append(vector3)
	return path

def getPathByPrefix(elementNode, path, prefix):
	'Get path from prefix and xml element.'
	if len(path) < 2:
		print('Warning, bug, path is too small in evaluate in setPathByPrefix.')
		return
	pathByKey = getPathByKey([], elementNode, getCapitalizedSuffixKey(prefix, 'path'))
	if len( pathByKey ) < len(path):
		for pointIndex in xrange( len( pathByKey ) ):
			path[pointIndex] = pathByKey[pointIndex]
	else:
		path = pathByKey
	path[0] = getVector3ByPrefix(path[0], elementNode, getCapitalizedSuffixKey(prefix, 'pathStart'))
	path[-1] = getVector3ByPrefix(path[-1], elementNode, getCapitalizedSuffixKey(prefix, 'pathEnd'))
	return path

def getPathsByKey(defaultPaths, elementNode, key):
	'Get paths by key.'
	if key not in elementNode.attributes:
		return defaultPaths
	word = str(elementNode.attributes[key]).strip()
	evaluatedLinkValue = getEvaluatedLinkValue(elementNode, word)
	if evaluatedLinkValue.__class__ == dict or evaluatedLinkValue.__class__ == list:
		convertToPaths(evaluatedLinkValue)
		return getPathsByLists(evaluatedLinkValue)
	elementNodeObject = getElementNodeObject(evaluatedLinkValue)
	if elementNodeObject == None:
		return defaultPaths
	return elementNodeObject.getPaths()

def getPathsByLists(vertexLists):
	'Get paths by lists.'
	vector3Lists = getVector3ListsRecursively(vertexLists)
	paths = []
	addToPathsRecursively(paths, vector3Lists)
	return paths

def getRadiusArealizedBasedOnAreaRadius(elementNode, radius, sides):
	'Get the areal radius from the radius, number of sides and cascade radiusAreal.'
	if elementNode.getCascadeBoolean(False, 'radiusAreal'):
		return radius
	return radius * euclidean.getRadiusArealizedMultiplier(sides)

def getSidesBasedOnPrecision(elementNode, radius):
	'Get the number of polygon sides.'
	return int(math.ceil(math.sqrt(0.5 * radius / setting.getPrecision(elementNode)) * math.pi))

def getSidesMinimumThreeBasedOnPrecision(elementNode, radius):
	'Get the number of polygon sides, with a minimum of three.'
	return max(getSidesBasedOnPrecision(elementNode, radius), 3)

def getSidesMinimumThreeBasedOnPrecisionSides(elementNode, radius):
	'Get the number of polygon sides, with a minimum of three.'
	sides = getSidesMinimumThreeBasedOnPrecision(elementNode, radius)
	return getEvaluatedFloat(sides, elementNode, 'sides')

def getSplitDictionary():
	'Get split dictionary.'
	global globalSplitDictionaryOperator
	splitDictionary = globalSplitDictionaryOperator.copy()
	global globalDictionaryOperatorBegin
	splitDictionary.update( globalDictionaryOperatorBegin )
	splitDictionary['and'] = EvaluatorAnd
	splitDictionary['false'] = EvaluatorFalse
	splitDictionary['False'] = EvaluatorFalse
	splitDictionary['or'] = EvaluatorOr
	splitDictionary['not'] = EvaluatorNot
	splitDictionary['true'] = EvaluatorTrue
	splitDictionary['True'] = EvaluatorTrue
	splitDictionary['none'] = EvaluatorNone
	splitDictionary['None'] = EvaluatorNone
	return splitDictionary

def getStartsWithCurlyEqualRoundSquare(word):
	'Determine if the word starts with round or square brackets.'
	return word.startswith('{') or word.startswith('=') or word.startswith('(') or word.startswith('[')

def getTokenByNumber(number):
	'Get token by number.'
	return '_%s_' % number

def getTransformedPathByKey(defaultTransformedPath, elementNode, key):
	'Get transformed path from prefix and xml element.'
	if key not in elementNode.attributes:
		return defaultTransformedPath
	value = elementNode.attributes[key]
	if value.__class__ == list:
		return value
	word = str(value).strip()
	evaluatedLinkValue = getEvaluatedLinkValue(elementNode, word)
	if evaluatedLinkValue.__class__ == list:
		return getPathByList(evaluatedLinkValue)
	elementNodeObject = getElementNodeObject(evaluatedLinkValueClass)
	if elementNodeObject == None:
		return defaultTransformedPath
	return elementNodeObject.getTransformedPaths()[0]

def getTransformedPathByPrefix(elementNode, path, prefix):
	'Get path from prefix and xml element.'
	if len(path) < 2:
		print('Warning, bug, path is too small in evaluate in setPathByPrefix.')
		return
	pathByKey = getTransformedPathByKey([], elementNode, getCapitalizedSuffixKey(prefix, 'path'))
	if len( pathByKey ) < len(path):
		for pointIndex in xrange( len( pathByKey ) ):
			path[pointIndex] = pathByKey[pointIndex]
	else:
		path = pathByKey
	path[0] = getVector3ByPrefix(path[0], elementNode, getCapitalizedSuffixKey(prefix, 'pathStart'))
	path[-1] = getVector3ByPrefix(path[-1], elementNode, getCapitalizedSuffixKey(prefix, 'pathEnd'))
	return path

def getTransformedPathsByKey(defaultTransformedPaths, elementNode, key):
	'Get transformed paths by key.'
	if key not in elementNode.attributes:
		return defaultTransformedPaths
	value = elementNode.attributes[key]
	if value.__class__ == list:
		return getPathsByLists(value)
	word = str(value).strip()
	evaluatedLinkValue = getEvaluatedLinkValue(elementNode, word)
	if evaluatedLinkValue.__class__ == dict or evaluatedLinkValue.__class__ == list:
		convertToTransformedPaths(evaluatedLinkValue)
		return getPathsByLists(evaluatedLinkValue)
	elementNodeObject = getElementNodeObject(evaluatedLinkValue)
	if elementNodeObject == None:
		return defaultTransformedPaths
	return elementNodeObject.getTransformedPaths()

def getUniqueQuoteIndex( uniqueQuoteIndex, word ):
	'Get uniqueQuoteIndex.'
	uniqueQuoteIndex += 1
	while getTokenByNumber(uniqueQuoteIndex) in word:
		uniqueQuoteIndex += 1
	return uniqueQuoteIndex

def getUniqueToken(word):
	'Get unique token.'
	uniqueString = '@#!'
	for character in uniqueString:
		if character not in word:
			return character
	uniqueNumber = 0
	while True:
		for character in uniqueString:
			uniqueToken = character + str(uniqueNumber)
			if uniqueToken not in word:
				return uniqueToken
			uniqueNumber += 1

def getVector3ByDictionary( dictionary, vector3 ):
	'Get vector3 by dictionary.'
	if 'x' in dictionary:
		vector3 = getVector3IfNone(vector3)
		vector3.x = euclidean.getFloatFromValue(dictionary['x'])
	if 'y' in dictionary:
		vector3 = getVector3IfNone(vector3)
		vector3.y = euclidean.getFloatFromValue(dictionary['y'])
	if 'z' in dictionary:
		vector3 = getVector3IfNone(vector3)
		vector3.z = euclidean.getFloatFromValue( dictionary['z'] )
	return vector3

def getVector3ByDictionaryListValue(value, vector3):
	'Get vector3 by dictionary, list or value.'
	if value.__class__ == Vector3 or value.__class__.__name__ == 'Vector3Index':
		return value
	if value.__class__ == dict:
		return getVector3ByDictionary(value, vector3)
	if value.__class__ == list:
		return getVector3ByFloatList(value, vector3)
	floatFromValue = euclidean.getFloatFromValue(value)
	if floatFromValue ==  None:
		return vector3
	vector3.setToXYZ(floatFromValue, floatFromValue, floatFromValue)
	return vector3

def getVector3ByFloatList(floatList, vector3):
	'Get vector3 by float list.'
	if len(floatList) > 0:
		vector3 = getVector3IfNone(vector3)
		vector3.x = euclidean.getFloatFromValue(floatList[0])
	if len(floatList) > 1:
		vector3 = getVector3IfNone(vector3)
		vector3.y = euclidean.getFloatFromValue(floatList[1])
	if len(floatList) > 2:
		vector3 = getVector3IfNone(vector3)
		vector3.z = euclidean.getFloatFromValue(floatList[2])
	return vector3

def getVector3ByMultiplierPrefix( elementNode, multiplier, prefix, vector3 ):
	'Get vector3 from multiplier, prefix and xml element.'
	if multiplier == 0.0:
		return vector3
	oldMultipliedValueVector3 = vector3 * multiplier
	vector3ByPrefix = getVector3ByPrefix(oldMultipliedValueVector3.copy(), elementNode, prefix)
	if vector3ByPrefix == oldMultipliedValueVector3:
		return vector3
	return vector3ByPrefix / multiplier

def getVector3ByMultiplierPrefixes( elementNode, multiplier, prefixes, vector3 ):
	'Get vector3 from multiplier, prefixes and xml element.'
	for prefix in prefixes:
		vector3 = getVector3ByMultiplierPrefix( elementNode, multiplier, prefix, vector3 )
	return vector3

def getVector3ByPrefix(defaultVector3, elementNode, prefix):
	'Get vector3 from prefix and xml element.'
	value = getEvaluatedValue(None, elementNode, prefix)
	if value != None:
		defaultVector3 = getVector3ByDictionaryListValue(value, defaultVector3)
	prefix = archive.getUntilDot(prefix)
	x = getEvaluatedFloat(None, elementNode, prefix + '.x')
	if x != None:
		defaultVector3 = getVector3IfNone(defaultVector3)
		defaultVector3.x = x
	y = getEvaluatedFloat(None, elementNode, prefix + '.y')
	if y != None:
		defaultVector3 = getVector3IfNone(defaultVector3)
		defaultVector3.y = y
	z = getEvaluatedFloat(None, elementNode, prefix + '.z')
	if z != None:
		defaultVector3 = getVector3IfNone(defaultVector3)
		defaultVector3.z = z
	return defaultVector3

def getVector3ByPrefixes( elementNode, prefixes, vector3 ):
	'Get vector3 from prefixes and xml element.'
	for prefix in prefixes:
		vector3 = getVector3ByPrefix(vector3, elementNode, prefix)
	return vector3

def getVector3FromElementNode(elementNode):
	'Get vector3 from xml element.'
	vector3 = Vector3(
		getEvaluatedFloat(0.0, elementNode, 'x'),
		getEvaluatedFloat(0.0, elementNode, 'y'),
		getEvaluatedFloat(0.0, elementNode, 'z'))
	return getVector3ByPrefix(vector3, elementNode, 'cartesian')

def getVector3IfNone(vector3):
	'Get new vector3 if the original vector3 is none.'
	if vector3 == None:
		return Vector3()
	return vector3

def getVector3ListsRecursively(floatLists):
	'Get vector3 lists recursively.'
	if len(floatLists) < 1:
		return Vector3()
	firstElement = floatLists[0]
	if firstElement.__class__ == Vector3:
		return floatLists
	if firstElement.__class__ != list:
		return getVector3ByFloatList(floatLists, Vector3())
	vector3ListsRecursively = []
	for floatList in floatLists:
		vector3ListsRecursively.append(getVector3ListsRecursively(floatList))
	return vector3ListsRecursively

def getVisibleObjects(archivableObjects):
	'Get the visible objects.'
	visibleObjects = []
	for archivableObject in archivableObjects:
		if archivableObject.getVisible():
			visibleObjects.append(archivableObject)
	return visibleObjects

def processArchivable(archivableClass, elementNode):
	'Get any new elements and process the archivable.'
	if elementNode == None:
		return
	elementNode.xmlObject = archivableClass()
	elementNode.xmlObject.setToElementNode(elementNode)
	elementNode.getXMLProcessor().processChildNodes(elementNode)

def processCondition(elementNode):
	'Process the xml element condition.'
	xmlProcessor = elementNode.getXMLProcessor()
	if elementNode.xmlObject == None:
		elementNode.xmlObject = ModuleElementNode(elementNode)
	if elementNode.xmlObject.conditionSplitWords == None:
		return
	if len(xmlProcessor.functions ) < 1:
		print('Warning, the (in) element is not in a function in processCondition in evaluate for:')
		print(elementNode)
		return
	if int(getEvaluatedExpressionValueBySplitLine(elementNode, elementNode.xmlObject.conditionSplitWords)) > 0:
		xmlProcessor.functions[-1].processChildNodes(elementNode)
	else:
		elementNode.xmlObject.processElse(elementNode)

def removeIdentifiersFromDictionary(dictionary):
	'Remove the identifier elements from a dictionary.'
	euclidean.removeElementsFromDictionary(dictionary, ['id', 'name', 'tags'])
	return dictionary

def setAttributesByArguments(argumentNames, arguments, elementNode):
	'Set the attribute dictionary to the arguments.'
	for argumentIndex, argument in enumerate(arguments):
		elementNode.attributes[argumentNames[argumentIndex]] = argument

def setFunctionLocalDictionary(arguments, function):
	'Evaluate the function statement and delete the evaluators.'
	function.localDictionary = {'_arguments' : arguments}
	if len(arguments) > 0:
		firstArgument = arguments[0]
		if firstArgument.__class__ == dict:
			function.localDictionary = firstArgument
			return
	if 'parameters' not in function.elementNode.attributes:
		return
	parameters = function.elementNode.attributes['parameters'].strip()
	if parameters == '':
		return
	parameterWords = parameters.split(',')
	for parameterWordIndex, parameterWord in enumerate(parameterWords):
		strippedWord = parameterWord.strip()
		keyValue = KeyValue().getByEqual(strippedWord)
		if parameterWordIndex < len(arguments):
			function.localDictionary[keyValue.key] = arguments[parameterWordIndex]
		else:
			strippedValue = keyValue.value
			if strippedValue == None:
				print('Warning there is no default parameter in getParameterValue for:')
				print(strippedWord)
				print(parameterWords)
				print(arguments)
				print(function.elementNode.attributes)
			else:
				strippedValue = strippedValue.strip()
			function.localDictionary[keyValue.key.strip()] = strippedValue
	if len(arguments) > len(parameterWords):
		print('Warning there are too many initializeFunction parameters for:')
		print(function.elementNode.attributes)
		print(parameterWords)
		print(arguments)

def setLocalAttribute(elementNode):
	'Set the local attribute if any.'
	if elementNode.xmlObject != None:
		return
	for key in elementNode.attributes:
		if key[: 1].isalpha():
			value = getEvaluatorSplitWords(getLocalAttributeValueString(key, elementNode.attributes[key].strip()))
			elementNode.xmlObject = KeyValue(key, value)
			return
	elementNode.xmlObject = KeyValue()


class BaseFunction:
	'Class to get equation results.'
	def __init__(self, elementNode):
		'Initialize.'
		self.elementNode = elementNode
		self.localDictionary = {}
		self.xmlProcessor = elementNode.getXMLProcessor()

	def __repr__(self):
		'Get the string representation of this Class.'
		return str(self.__dict__)

	def getReturnValue(self):
		'Get return value.'
		self.getReturnValueWithoutDeletion()
		del self.xmlProcessor.functions[-1]
		return self.returnValue

	def processChildNodes(self, elementNode):
		'Process childNodes if shouldReturn is false.'
		for childNode in elementNode.childNodes:
			if self.shouldReturn:
				return
			self.xmlProcessor.processElementNode(childNode)


class ClassFunction(BaseFunction):
	'Class to get class results.'
	def getReturnValueByArguments(self, *arguments):
		'Get return value by arguments.'
		setFunctionLocalDictionary(arguments, self)
		return self.getReturnValue()

	def getReturnValueWithoutDeletion(self):
		'Get return value without deleting last function.'
		self.returnValue = None
		self.shouldReturn = False
		self.xmlProcessor.functions.append(self)
		self.processChildNodes(self.elementNode)
		return self.returnValue


class ClassObject:
	'Class to hold class attributes and functions.'
	def __init__(self, elementNode):
		'Initialize.'
		self.functionDictionary = elementNode.xmlObject.functionDictionary
		self.selfDictionary = {}
		for variable in elementNode.xmlObject.variables:
			self.selfDictionary[variable] = None

	def __repr__(self):
		'Get the string representation of this Class.'
		return str(self.__dict__)

	def _getAccessibleAttribute(self, attributeName):
		'Get the accessible attribute.'
		if attributeName in self.selfDictionary:
			return self.selfDictionary[attributeName]
		if attributeName in self.functionDictionary:
			function = self.functionDictionary[attributeName]
			function.classObject = self
			return function.getReturnValueByArguments
		return None

	def _setAccessibleAttribute(self, attributeName, value):
		'Set the accessible attribute.'
		if attributeName in self.selfDictionary:
			self.selfDictionary[attributeName] = value


class EmptyObject:
	'An empty object.'
	def __init__(self):
		'Do nothing.'
		pass


class Evaluator:
	'Base evaluator class.'
	def __init__(self, elementNode, word):
		'Set value to none.'
		self.value = None
		self.word = word

	def __repr__(self):
		'Get the string representation of this Class.'
		return str(self.__dict__)

	def executeBracket( self, bracketBeginIndex, bracketEndIndex, evaluators ):
		'Execute the bracket.'
		pass

	def executeCenterOperation(self, evaluators, evaluatorIndex):
		'Execute operator which acts on the center.'
		pass

	def executeDictionary(self, dictionary, evaluators, keys, evaluatorIndex, nextEvaluator):
		'Execute the dictionary.'
		del evaluators[evaluatorIndex]
		enumeratorKeys = euclidean.getEnumeratorKeys(dictionary, keys)
		if enumeratorKeys.__class__ == list:
			nextEvaluator.value = []
			for enumeratorKey in enumeratorKeys:
				if enumeratorKey in dictionary:
					nextEvaluator.value.append(dictionary[enumeratorKey])
				else:
					print('Warning, key in executeKey in Evaluator in evaluate is not in for:')
					print(enumeratorKey)
					print(dictionary)
			return
		if enumeratorKeys in dictionary:
			nextEvaluator.value = dictionary[enumeratorKeys]
		else:
			print('Warning, key in executeKey in Evaluator in evaluate is not in for:')
			print(enumeratorKeys)
			print(dictionary)

	def executeFunction(self, evaluators, evaluatorIndex, nextEvaluator):
		'Execute the function.'
		pass

	def executeKey(self, evaluators, keys, evaluatorIndex, nextEvaluator):
		'Execute the key index.'
		if self.value.__class__ == str:
			self.executeString(evaluators, keys, evaluatorIndex, nextEvaluator)
			return
		if self.value.__class__ == list:
			self.executeList(evaluators, keys, evaluatorIndex, nextEvaluator)
			return
		if self.value.__class__ == dict:
			self.executeDictionary(self.value, evaluators, keys, evaluatorIndex, nextEvaluator)
			return
		getAccessibleDictionaryFunction = getattr(self.value, '_getAccessibleDictionary', None)
		if getAccessibleDictionaryFunction != None:
			self.executeDictionary(getAccessibleDictionaryFunction(), evaluators, keys, evaluatorIndex, nextEvaluator)
			return
		if self.value.__class__.__name__ != 'ElementNode':
			return
		del evaluators[evaluatorIndex]
		enumeratorKeys = euclidean.getEnumeratorKeys(self.value.attributes, keys)
		if enumeratorKeys.__class__ == list:
			nextEvaluator.value = []
			for enumeratorKey in enumeratorKeys:
				if enumeratorKey in self.value.attributes:
					nextEvaluator.value.append(getEvaluatedExpressionValue(self.value, self.value.attributes[enumeratorKey]))
				else:
					print('Warning, key in executeKey in Evaluator in evaluate is not in for:')
					print(enumeratorKey)
					print(self.value.attributes)
			return
		if enumeratorKeys in self.value.attributes:
			nextEvaluator.value = getEvaluatedExpressionValue(self.value, self.value.attributes[enumeratorKeys])
		else:
			print('Warning, key in executeKey in Evaluator in evaluate is not in for:')
			print(enumeratorKeys)
			print(self.value.attributes)

	def executeLeftOperation(self, evaluators, evaluatorIndex, operationLevel):
		'Execute operator which acts from the left.'
		pass

	def executeList(self, evaluators, keys, evaluatorIndex, nextEvaluator):
		'Execute the key index.'
		del evaluators[evaluatorIndex]
		enumeratorKeys = euclidean.getEnumeratorKeys(self.value, keys)
		if enumeratorKeys.__class__ == list:
			nextEvaluator.value = []
			for enumeratorKey in enumeratorKeys:
				intKey = euclidean.getIntFromValue(enumeratorKey)
				if self.getIsInRange(intKey):
					nextEvaluator.value.append(self.value[intKey])
				else:
					print('Warning, key in executeList in Evaluator in evaluate is not in for:')
					print(enumeratorKey)
					print(self.value)
			return
		intKey = euclidean.getIntFromValue(enumeratorKeys)
		if self.getIsInRange(intKey):
			nextEvaluator.value = self.value[intKey]
		else:
			print('Warning, key in executeList in Evaluator in evaluate is not in for:')
			print(enumeratorKeys)
			print(self.value)

	def executePairOperation(self, evaluators, evaluatorIndex, operationLevel):
		'Operate on two evaluators.'
		pass

	def executeRightOperation( self, evaluators, evaluatorIndex ):
		'Execute operator which acts from the right.'
		pass

	def executeString(self, evaluators, keys, evaluatorIndex, nextEvaluator):
		'Execute the string.'
		del evaluators[evaluatorIndex]
		enumeratorKeys = euclidean.getEnumeratorKeys(self.value, keys)
		if enumeratorKeys.__class__ == list:
			nextEvaluator.value = ''
			for enumeratorKey in enumeratorKeys:
				intKey = euclidean.getIntFromValue(enumeratorKey)
				if self.getIsInRange(intKey):
					nextEvaluator.value += self.value[intKey]
				else:
					print('Warning, key in executeString in Evaluator in evaluate is not in for:')
					print(enumeratorKey)
					print(self.value)
			return
		intKey = euclidean.getIntFromValue(enumeratorKeys)
		if self.getIsInRange(intKey):
			nextEvaluator.value = self.value[intKey]
		else:
			print('Warning, key in executeString in Evaluator in evaluate is not in for:')
			print(enumeratorKeys)
			print(self.value)

	def getIsInRange(self, keyIndex):
		'Determine if the keyIndex is in range.'
		if keyIndex == None:
			return False
		return keyIndex >= -len(self.value) and keyIndex < len(self.value)


class EvaluatorAddition(Evaluator):
	'Class to add two evaluators.'
	def executePair( self, evaluators, evaluatorIndex ):
		'Add two evaluators.'
		leftIndex = evaluatorIndex - 1
		rightIndex = evaluatorIndex + 1
		if leftIndex < 0:
			print('Warning, no leftKey in executePair in EvaluatorAddition for:')
			print(evaluators)
			print(evaluatorIndex)
			print(self)
			del evaluators[evaluatorIndex]
			return
		if rightIndex >= len(evaluators):
			print('Warning, no rightKey in executePair in EvaluatorAddition for:')
			print(evaluators)
			print(evaluatorIndex)
			print(self)
			del evaluators[evaluatorIndex]
			return
		rightValue = evaluators[rightIndex].value
		evaluators[leftIndex].value = self.getOperationValue(evaluators[leftIndex].value, evaluators[rightIndex].value)
		del evaluators[ evaluatorIndex : evaluatorIndex + 2 ]

	def executePairOperation(self, evaluators, evaluatorIndex, operationLevel):
		'Operate on two evaluators.'
		if operationLevel == 20:
			self.executePair(evaluators, evaluatorIndex)

	def getEvaluatedValues(self, enumerable, keys, value):
		'Get evaluatedValues.'
		if enumerable.__class__ == dict:
			evaluatedValues = {}
			for key in keys:
				evaluatedValues[key] = self.getOperationValue(value, enumerable[key])
			return evaluatedValues
		evaluatedValues = []
		for key in keys:
			evaluatedValues.append(self.getOperationValue(value, enumerable[key]))
		return evaluatedValues

	def getOperationValue(self, leftValue, rightValue):
		'Get operation value.'
		leftKeys = getKeys(leftValue)
		rightKeys = getKeys(rightValue)
		if leftKeys == None and rightKeys == None:
			return self.getValueFromValuePair(leftValue, rightValue)
		if leftKeys == None:
			return self.getEvaluatedValues(rightValue, rightKeys, leftValue)
		if rightKeys == None:
			return self.getEvaluatedValues(leftValue, leftKeys, rightValue)
		leftKeys.sort(reverse=True)
		rightKeys.sort(reverse=True)
		if leftKeys != rightKeys:
			print('Warning, the leftKeys are different from the rightKeys in getOperationValue in EvaluatorAddition for:')
			print('leftValue')
			print(leftValue)
			print(leftKeys)
			print('rightValue')
			print(rightValue)
			print(rightKeys)
			print(self)
			return None
		if leftValue.__class__ == dict or rightValue.__class__ == dict:
			evaluatedValues = {}
			for leftKey in leftKeys:
				evaluatedValues[leftKey] = self.getOperationValue(leftValue[leftKey], rightValue[leftKey])
			return evaluatedValues
		evaluatedValues = []
		for leftKey in leftKeys:
			evaluatedValues.append(self.getOperationValue(leftValue[leftKey], rightValue[leftKey]))
		return evaluatedValues

	def getValueFromValuePair(self, leftValue, rightValue):
		'Add two values.'
		return leftValue + rightValue


class EvaluatorEqual(EvaluatorAddition):
	'Class to compare two evaluators.'
	def executePairOperation(self, evaluators, evaluatorIndex, operationLevel):
		'Operate on two evaluators.'
		if operationLevel == 15:
			self.executePair(evaluators, evaluatorIndex)

	def getBooleanFromValuePair(self, leftValue, rightValue):
		'Compare two values.'
		return leftValue == rightValue

	def getValueFromValuePair(self, leftValue, rightValue):
		'Get value from comparison.'
		return self.getBooleanFromValuePair(leftValue, rightValue)


class EvaluatorSubtraction(EvaluatorAddition):
	'Class to subtract two evaluators.'
	def executeLeft( self, evaluators, evaluatorIndex ):
		'Minus the value to the right.'
		leftIndex = evaluatorIndex - 1
		rightIndex = evaluatorIndex + 1
		leftValue = None
		if leftIndex >= 0:
			leftValue = evaluators[leftIndex].value
		if leftValue != None:
			return
		rightValue = evaluators[rightIndex].value
		if rightValue == None:
			print('Warning, can not minus.')
			print(evaluators[rightIndex].word)
		else:
			evaluators[rightIndex].value = self.getNegativeValue(rightValue)
		del evaluators[evaluatorIndex]

	def executeLeftOperation(self, evaluators, evaluatorIndex, operationLevel):
		'Minus the value to the right.'
		if operationLevel == 200:
			self.executeLeft(evaluators, evaluatorIndex)

	def getNegativeValue( self, value ):
		'Get the negative value.'
		keys = getKeys(value)
		if keys == None:
			return self.getValueFromSingleValue(value)
		for key in keys:
			value[key] = self.getNegativeValue(value[key])
		return value

	def getValueFromSingleValue( self, value ):
		'Minus value.'
		return -value

	def getValueFromValuePair(self, leftValue, rightValue):
		'Subtract two values.'
		return leftValue - rightValue


class EvaluatorAnd(EvaluatorAddition):
	'Class to compare two evaluators.'
	def executePairOperation(self, evaluators, evaluatorIndex, operationLevel):
		'Operate on two evaluators.'
		if operationLevel == 12:
			self.executePair(evaluators, evaluatorIndex)

	def getBooleanFromValuePair(self, leftValue, rightValue):
		'And two values.'
		return leftValue and rightValue

	def getValueFromValuePair(self, leftValue, rightValue):
		'Get value from comparison.'
		return self.getBooleanFromValuePair(leftValue, rightValue)


class EvaluatorAttribute(Evaluator):
	'Class to handle an attribute.'
	def executeFunction(self, evaluators, evaluatorIndex, nextEvaluator):
		'Execute the function.'
		executeNextEvaluatorArguments(self, evaluators, evaluatorIndex, nextEvaluator)

	def executeRightOperation( self, evaluators, evaluatorIndex ):
		'Execute operator which acts from the right.'
		attributeName = self.word[1 :]
		previousIndex = evaluatorIndex - 1
		previousEvaluator = evaluators[previousIndex]
		if previousEvaluator.value.__class__ == dict:
			from fabmetheus_utilities.geometry.geometry_utilities.evaluate_enumerables import dictionary_attribute
			self.value = dictionary_attribute._getAccessibleAttribute(attributeName, previousEvaluator.value)
		elif previousEvaluator.value.__class__ == list:
			from fabmetheus_utilities.geometry.geometry_utilities.evaluate_enumerables import list_attribute
			self.value = list_attribute._getAccessibleAttribute(attributeName, previousEvaluator.value)
		elif previousEvaluator.value.__class__ == str:
			from fabmetheus_utilities.geometry.geometry_utilities.evaluate_enumerables import string_attribute
			self.value = string_attribute._getAccessibleAttribute(attributeName, previousEvaluator.value)
		else:
			attributeKeywords = attributeName.split('.')
			self.value = previousEvaluator.value
			for attributeKeyword in attributeKeywords:
				self.value = getattr(self.value, '_getAccessibleAttribute', None)(attributeKeyword)
		if self.value == None:
			print('Warning, EvaluatorAttribute in evaluate can not get a getAccessibleAttributeFunction for:')
			print(attributeName)
			print(previousEvaluator.value)
			print(self)
			return
		del evaluators[previousIndex]


class EvaluatorBracketCurly(Evaluator):
	'Class to evaluate a string.'
	def executeBracket(self, bracketBeginIndex, bracketEndIndex, evaluators):
		'Execute the bracket.'
		for evaluatorIndex in xrange(bracketEndIndex - 3, bracketBeginIndex, - 1):
			bracketEndIndex = getEndIndexConvertEquationValue(bracketEndIndex, evaluatorIndex, evaluators)
		evaluatedExpressionValueEvaluators = getBracketEvaluators(bracketBeginIndex, bracketEndIndex, evaluators)
		self.value = {}
		for evaluatedExpressionValueEvaluator in evaluatedExpressionValueEvaluators:
			keyValue = evaluatedExpressionValueEvaluator.value
			self.value[keyValue.key] = keyValue.value
		del evaluators[bracketBeginIndex + 1: bracketEndIndex + 1]


class EvaluatorBracketRound(Evaluator):
	'Class to evaluate a string.'
	def __init__(self, elementNode, word):
		'Set value to none.'
		self.arguments = []
		self.value = None
		self.word = word

	def executeBracket( self, bracketBeginIndex, bracketEndIndex, evaluators ):
		'Execute the bracket.'
		self.arguments = getBracketValuesDeleteEvaluator(bracketBeginIndex, bracketEndIndex, evaluators)
		if len( self.arguments ) < 1:
			return
		if len( self.arguments ) > 1:
			self.value = self.arguments
		else:
			self.value = self.arguments[0]

	def executeRightOperation( self, evaluators, evaluatorIndex ):
		'Evaluate the statement and delete the evaluators.'
		previousIndex = evaluatorIndex - 1
		if previousIndex < 0:
			return
		evaluators[ previousIndex ].executeFunction( evaluators, previousIndex, self )


class EvaluatorBracketSquare(Evaluator):
	'Class to evaluate a string.'
	def executeBracket( self, bracketBeginIndex, bracketEndIndex, evaluators ):
		'Execute the bracket.'
		self.value = getBracketValuesDeleteEvaluator(bracketBeginIndex, bracketEndIndex, evaluators)

	def executeRightOperation( self, evaluators, evaluatorIndex ):
		'Evaluate the statement and delete the evaluators.'
		previousIndex = evaluatorIndex - 1
		if previousIndex < 0:
			return
		if self.value.__class__ != list:
			return
		evaluators[ previousIndex ].executeKey( evaluators, self.value, previousIndex, self )


class EvaluatorClass(Evaluator):
	'Class evaluator class.'
	def __init__(self, elementNode, word):
		'Set value to none.'
		self.elementNode = elementNode
		self.value = None
		self.word = word

	def executeFunction(self, evaluators, evaluatorIndex, nextEvaluator):
		'Execute the function.'
		if self.elementNode.xmlObject == None:
			self.elementNode.xmlObject = FunctionVariable(self.elementNode)
		nextEvaluator.value = ClassObject(self.elementNode)
		initializeFunction = None
		if '_init' in self.elementNode.xmlObject.functionDictionary:
			function = self.elementNode.xmlObject.functionDictionary['_init']
			function.classObject = nextEvaluator.value
			setFunctionLocalDictionary(nextEvaluator.arguments, function)
			function.getReturnValue()
		del evaluators[evaluatorIndex]


class EvaluatorComma(Evaluator):
	'Class to join two evaluators.'
	def executePairOperation(self, evaluators, evaluatorIndex, operationLevel):
		'Operate on two evaluators.'
		if operationLevel != 0:
			return
		previousIndex = evaluatorIndex - 1
		if previousIndex < 0:
			evaluators[evaluatorIndex].value = None
			return
		if evaluators[previousIndex].word == ',':
			evaluators[evaluatorIndex].value = None
			return
		del evaluators[evaluatorIndex]


class EvaluatorConcatenate(Evaluator):
	'Class to join two evaluators.'
	def executePairOperation(self, evaluators, evaluatorIndex, operationLevel):
		'Operate on two evaluators.'
		if operationLevel != 80:
			return
		leftIndex = evaluatorIndex - 1
		if leftIndex < 0:
			del evaluators[evaluatorIndex]
			return
		rightIndex = evaluatorIndex + 1
		if rightIndex >= len(evaluators):
			del evaluators[ leftIndex : rightIndex ]
			return
		leftValue = evaluators[leftIndex].value
		rightValue = evaluators[rightIndex].value
		if leftValue.__class__ == rightValue.__class__ and (leftValue.__class__ == list or rightValue.__class__ == str):
			evaluators[leftIndex].value = leftValue + rightValue
			del evaluators[ evaluatorIndex : evaluatorIndex + 2 ]
			return
		if leftValue.__class__ == list and rightValue.__class__ == int:
			if rightValue > 0:
				originalList = leftValue[:]
				for copyIndex in xrange( rightValue - 1 ):
					leftValue += originalList
				evaluators[leftIndex].value = leftValue
				del evaluators[ evaluatorIndex : evaluatorIndex + 2 ]
			return
		if leftValue.__class__ == dict and rightValue.__class__ == dict:
			leftValue.update(rightValue)
			evaluators[leftIndex].value = leftValue
			del evaluators[ evaluatorIndex : evaluatorIndex + 2 ]
			return
		del evaluators[ leftIndex : evaluatorIndex + 2 ]


class EvaluatorDictionary(Evaluator):
	'Class to join two evaluators.'
	def executePairOperation(self, evaluators, evaluatorIndex, operationLevel):
		'Operate on two evaluators.'
		if operationLevel != 10:
			return
		leftEvaluatorIndex = evaluatorIndex - 1
		if leftEvaluatorIndex < 0:
			print('Warning, leftEvaluatorIndex is less than zero in EvaluatorDictionary for:')
			print(self)
			print(evaluators)
			return
		rightEvaluatorIndex = evaluatorIndex + 1
		if rightEvaluatorIndex >= len(evaluators):
			print('Warning, rightEvaluatorIndex too high in EvaluatorDictionary for:')
			print(rightEvaluatorIndex)
			print(self)
			print(evaluators)
			return
		evaluators[rightEvaluatorIndex].value = KeyValue(evaluators[leftEvaluatorIndex].value, evaluators[rightEvaluatorIndex].value)
		del evaluators[ leftEvaluatorIndex : rightEvaluatorIndex ]


class EvaluatorDivision(EvaluatorAddition):
	'Class to divide two evaluators.'
	def executePairOperation(self, evaluators, evaluatorIndex, operationLevel):
		'Operate on two evaluators.'
		if operationLevel == 40:
			self.executePair(evaluators, evaluatorIndex)

	def getValueFromValuePair(self, leftValue, rightValue):
		'Divide two values.'
		return leftValue / rightValue


class EvaluatorElement(Evaluator):
	'Element evaluator class.'
	def __init__(self, elementNode, word):
		'Set value to none.'
		self.elementNode = elementNode
		self.value = None
		self.word = word

	def executeCenterOperation(self, evaluators, evaluatorIndex):
		'Execute operator which acts on the center.'
		dotIndex = self.word.find('.')
		if dotIndex < 0:
			print('Warning, EvaluatorElement in evaluate can not find the dot for:')
			print(functionName)
			print(self)
			return
		attributeName = self.word[dotIndex + 1 :]
		moduleName = self.word[: dotIndex]
		if moduleName in globalModuleFunctionsDictionary:
			self.value = globalModuleFunctionsDictionary[moduleName](attributeName, self.elementNode)
			return
		pluginModule = None
		if moduleName in globalElementNameSet:
			pluginModule = archive.getModuleWithPath(archive.getElementsPath(moduleName))
		if pluginModule == None:
			print('Warning, EvaluatorElement in evaluate can not get a pluginModule for:')
			print(moduleName)
			print(self)
			return
		getAccessibleAttributeFunction = pluginModule._getAccessibleAttribute
		globalModuleFunctionsDictionary[moduleName] = getAccessibleAttributeFunction
		self.value = getAccessibleAttributeFunction(attributeName, self.elementNode)

	def executeFunction(self, evaluators, evaluatorIndex, nextEvaluator):
		'Execute the function.'
		executeNextEvaluatorArguments(self, evaluators, evaluatorIndex, nextEvaluator)


class EvaluatorFalse(Evaluator):
	'Class to evaluate a string.'
	def __init__(self, elementNode, word):
		'Set value to zero.'
		self.value = False
		self.word = word


class EvaluatorFunction(Evaluator):
	'Function evaluator class.'
	def __init__(self, elementNode, word):
		'Set value to none.'
		self.elementNode = elementNode
		self.value = None
		self.word = word

	def executeFunction(self, evaluators, evaluatorIndex, nextEvaluator):
		'Execute the function.'
		if self.elementNode.xmlObject == None:
			if 'return' in self.elementNode.attributes:
				value = self.elementNode.attributes['return']
				self.elementNode.xmlObject = getEvaluatorSplitWords(value)
			else:
				self.elementNode.xmlObject = []
		self.function = Function(self.elementNode )
		setFunctionLocalDictionary(nextEvaluator.arguments, self.function)
		nextEvaluator.value = self.function.getReturnValue()
		del evaluators[evaluatorIndex]


class EvaluatorFundamental(Evaluator):
	'Fundamental evaluator class.'
	def executeCenterOperation(self, evaluators, evaluatorIndex):
		'Execute operator which acts on the center.'
		dotIndex = self.word.find('.')
		if dotIndex < 0:
			print('Warning, EvaluatorFundamental in evaluate can not find the dot for:')
			print(functionName)
			print(self)
			return
		attributeName = self.word[dotIndex + 1 :]
		moduleName = self.word[: dotIndex]
		if moduleName in globalModuleFunctionsDictionary:
			self.value = globalModuleFunctionsDictionary[moduleName](attributeName)
			return
		pluginModule = None
		if moduleName in globalFundamentalNameSet:
			pluginModule = archive.getModuleWithPath(archive.getFundamentalsPath(moduleName))
		else:
			underscoredName = '_' + moduleName
			if underscoredName in globalFundamentalNameSet:
				pluginModule = archive.getModuleWithPath(archive.getFundamentalsPath(underscoredName))
		if pluginModule == None:
			print('Warning, EvaluatorFundamental in evaluate can not get a pluginModule for:')
			print(moduleName)
			print(self)
			return
		getAccessibleAttributeFunction = pluginModule._getAccessibleAttribute
		globalModuleFunctionsDictionary[moduleName] = getAccessibleAttributeFunction
		self.value = getAccessibleAttributeFunction(attributeName)

	def executeFunction(self, evaluators, evaluatorIndex, nextEvaluator):
		'Execute the function.'
		executeNextEvaluatorArguments(self, evaluators, evaluatorIndex, nextEvaluator)


class EvaluatorGreaterEqual( EvaluatorEqual ):
	'Class to compare two evaluators.'
	def getBooleanFromValuePair(self, leftValue, rightValue):
		'Compare two values.'
		return leftValue >= rightValue


class EvaluatorGreater( EvaluatorEqual ):
	'Class to compare two evaluators.'
	def getBooleanFromValuePair(self, leftValue, rightValue):
		'Compare two values.'
		return leftValue > rightValue


class EvaluatorLessEqual( EvaluatorEqual ):
	'Class to compare two evaluators.'
	def getBooleanFromValuePair(self, leftValue, rightValue):
		'Compare two values.'
		return leftValue <= rightValue


class EvaluatorLess( EvaluatorEqual ):
	'Class to compare two evaluators.'
	def getBooleanFromValuePair(self, leftValue, rightValue):
		'Compare two values.'
		return leftValue < rightValue


class EvaluatorLocal(EvaluatorElement):
	'Class to get a local variable.'
	def executeCenterOperation(self, evaluators, evaluatorIndex):
		'Execute operator which acts on the center.'
		functions = self.elementNode.getXMLProcessor().functions
		if len(functions) < 1:
			print('Warning, there are no functions in EvaluatorLocal in evaluate for:')
			print(self.word)
			return
		attributeKeywords = self.word.split('.')
		self.value = functions[-1].localDictionary[attributeKeywords[0]]
		for attributeKeyword in attributeKeywords[1 :]:
			self.value = self.value._getAccessibleAttribute(attributeKeyword)


class EvaluatorModulo( EvaluatorDivision ):
	'Class to modulo two evaluators.'
	def getValueFromValuePair(self, leftValue, rightValue):
		'Modulo two values.'
		return leftValue % rightValue


class EvaluatorMultiplication( EvaluatorDivision ):
	'Class to multiply two evaluators.'
	def getValueFromValuePair(self, leftValue, rightValue):
		'Multiply two values.'
		return leftValue * rightValue


class EvaluatorNone(Evaluator):
	'Class to evaluate None.'
	def __init__(self, elementNode, word):
		'Set value to none.'
		self.value = None
		self.word = str(word)


class EvaluatorNot(EvaluatorSubtraction):
	'Class to compare two evaluators.'
	def executeLeftOperation(self, evaluators, evaluatorIndex, operationLevel):
		'Minus the value to the right.'
		if operationLevel == 13:
			self.executeLeft(evaluators, evaluatorIndex)

	def getValueFromSingleValue( self, value ):
		'Minus value.'
		return not value


class EvaluatorNotEqual( EvaluatorEqual ):
	'Class to compare two evaluators.'
	def getBooleanFromValuePair(self, leftValue, rightValue):
		'Compare two values.'
		return leftValue != rightValue


class EvaluatorNumeric(Evaluator):
	'Class to evaluate a string.'
	def __init__(self, elementNode, word):
		'Set value.'
		self.value = None
		self.word = word
		try:
			if '.' in word:
				self.value = float(word)
			else:
				self.value = int(word)
		except:
			print('Warning, EvaluatorNumeric in evaluate could not get a numeric value for:')
			print(word)
			print(elementNode)


class EvaluatorOr( EvaluatorAnd ):
	'Class to compare two evaluators.'
	def getBooleanFromValuePair(self, leftValue, rightValue):
		'Or two values.'
		return leftValue or rightValue


class EvaluatorPower(EvaluatorAddition):
	'Class to power two evaluators.'
	def executePairOperation(self, evaluators, evaluatorIndex, operationLevel):
		'Operate on two evaluators.'
		if operationLevel == 60:
			self.executePair(evaluators, evaluatorIndex)

	def getValueFromValuePair(self, leftValue, rightValue):
		'Power of two values.'
		return leftValue ** rightValue


class EvaluatorSelf(EvaluatorElement):
	'Class to handle self.'
	def executeCenterOperation(self, evaluators, evaluatorIndex):
		'Execute operator which acts on the center.'
		functions = self.elementNode.getXMLProcessor().functions
		if len(functions) < 1:
			print('Warning, there are no functions in executeCenterOperation in EvaluatorSelf in evaluate for:')
			print(self.elementNode)
			return
		function = functions[-1]
		attributeKeywords = self.word.split('.')
		self.value = function.classObject
		for attributeKeyword in attributeKeywords[1 :]:
			self.value = self.value._getAccessibleAttribute(attributeKeyword)


class EvaluatorTrue(Evaluator):
	'Class to evaluate a string.'
	def __init__(self, elementNode, word):
		'Set value to true.'
		self.value = True
		self.word = word


class EvaluatorValue(Evaluator):
	'Class to evaluate a string.'
	def __init__(self, word):
		'Set value to none.'
		self.value = word
		self.word = str(word)


class Function(BaseFunction):
	'Class to get equation results.'
	def __init__(self, elementNode):
		'Initialize.'
		self.elementNode = elementNode
		self.evaluatorSplitLine = elementNode.xmlObject
		self.localDictionary = {}
		self.xmlProcessor = elementNode.getXMLProcessor()

	def getReturnValueWithoutDeletion(self):
		'Get return value without deleting last function.'
		self.returnValue = None
		self.xmlProcessor.functions.append(self)
		if len(self.evaluatorSplitLine) < 1:
			self.shouldReturn = False
			self.processChildNodes(self.elementNode)
		else:
			self.returnValue = getEvaluatedExpressionValueBySplitLine(self.elementNode, self.evaluatorSplitLine)
		return self.returnValue


class FunctionVariable:
	'Class to hold class functions and variable set.'
	def __init__(self, elementNode):
		'Initialize.'
		self.functionDictionary = {}
		self.variables = []
		self.processClass(elementNode)

	def addToVariableSet(self, elementNode):
		'Add to variables.'
		setLocalAttribute(elementNode)
		keySplitLine = elementNode.xmlObject.key.split('.')
		if len(keySplitLine) == 2:
			if keySplitLine[0] == 'self':
				variable = keySplitLine[1]
				if variable not in self.variables:
					self.variables.append(variable)

	def processClass(self, elementNode):
		'Add class to FunctionVariable.'
		for childNode in elementNode.childNodes:
			self.processFunction(childNode)
		if 'parentNode' in elementNode.attributes:
			self.processClass(elementNode.getElementNodeByID(elementNode.attributes['parentNode']))

	def processFunction(self, elementNode):
		'Add function to function dictionary.'
		if elementNode.getNodeName() != 'function':
			return
		idKey = elementNode.attributes['id']
		if idKey in self.functionDictionary:
			return
		self.functionDictionary[idKey] = ClassFunction(elementNode)
		for childNode in elementNode.childNodes:
			self.processStatement(childNode)

	def processStatement(self, elementNode):
		'Add self statement to variables.'
		if elementNode.getNodeName() == 'statement':
			self.addToVariableSet(elementNode)
		for childNode in elementNode.childNodes:
			self.processStatement(childNode)


class KeyValue:
	'Class to hold a key value.'
	def __init__(self, key=None, value=None):
		'Get key value.'
		self.key = key
		self.value = value

	def __repr__(self):
		'Get the string representation of this KeyValue.'
		return str(self.__dict__)

	def getByCharacter( self, character, line ):
		'Get by character.'
		dotIndex = line.find( character )
		if dotIndex < 0:
			self.key = line
			self.value = None
			return self
		self.key = line[: dotIndex]
		self.value = line[dotIndex + 1 :]
		return self

	def getByDot(self, line):
		'Get by dot.'
		return self.getByCharacter('.', line )

	def getByEqual(self, line):
		'Get by dot.'
		return self.getByCharacter('=', line )


class ModuleElementNode:
	'Class to get the in attribute, the index name and the value name.'
	def __init__( self, elementNode):
		'Initialize.'
		self.conditionSplitWords = None
		self.elseElement = None
		if 'condition' in elementNode.attributes:
			self.conditionSplitWords = getEvaluatorSplitWords( elementNode.attributes['condition'] )
		else:
			print('Warning, could not find the condition attribute in ModuleElementNode in evaluate for:')
			print(elementNode)
			return
		if len( self.conditionSplitWords ) < 1:
			self.conditionSplitWords = None
			print('Warning, could not get split words for the condition attribute in ModuleElementNode in evaluate for:')
			print(elementNode)
		nextIndex = getNextChildIndex(elementNode)
		if nextIndex >= len( elementNode.parentNode.childNodes ):
			return
		nextElementNode = elementNode.parentNode.childNodes[ nextIndex ]
		lowerLocalName = nextElementNode.getNodeName().lower()
		if lowerLocalName != 'else' and lowerLocalName != 'elif':
			return
		xmlProcessor = elementNode.getXMLProcessor()
		if lowerLocalName not in xmlProcessor.namePathDictionary:
			return
		self.pluginModule = archive.getModuleWithPath( xmlProcessor.namePathDictionary[ lowerLocalName ] )
		if self.pluginModule == None:
			return
		self.elseElement = nextElementNode

	def processElse(self, elementNode):
		'Process the else statement.'
		if self.elseElement != None:
			self.pluginModule.processElse( self.elseElement)


globalCreationDictionary = archive.getGeometryDictionary('creation')
globalDictionaryOperatorBegin = {
	'||' : EvaluatorConcatenate,
	'==' : EvaluatorEqual,
	'>=' : EvaluatorGreaterEqual,
	'<=' : EvaluatorLessEqual,
	'!=' : EvaluatorNotEqual,
	'**' : EvaluatorPower }
globalModuleEvaluatorDictionary = {}
globalFundamentalNameSet = set(archive.getPluginFileNamesFromDirectoryPath(archive.getFundamentalsPath()))
addPrefixDictionary(globalModuleEvaluatorDictionary, globalFundamentalNameSet, EvaluatorFundamental)
globalElementNameSet = set(archive.getPluginFileNamesFromDirectoryPath(archive.getElementsPath()))
addPrefixDictionary(globalModuleEvaluatorDictionary, globalElementNameSet, EvaluatorElement)
globalModuleEvaluatorDictionary['self'] = EvaluatorSelf
globalSplitDictionaryOperator = {
	'+' : EvaluatorAddition,
	'{' : EvaluatorBracketCurly,
	'}' : Evaluator,
	'(' : EvaluatorBracketRound,
	')' : Evaluator,
	'[' : EvaluatorBracketSquare,
	']' : Evaluator,
	',' : EvaluatorComma,
	':' : EvaluatorDictionary,
	'/' : EvaluatorDivision,
	'>' : EvaluatorGreater,
	'<' : EvaluatorLess,
	'%' : EvaluatorModulo,
	'*' : EvaluatorMultiplication,
	'-' : EvaluatorSubtraction }
globalSplitDictionary = getSplitDictionary() # must be after globalSplitDictionaryOperator
