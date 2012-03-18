"""
The xml_simple_reader.py script is an xml parser that can parse a line separated xml text.

This xml parser will read a line seperated xml text and produce a tree of the xml with a document element.  Each element can have an attribute table, childNodes, a class name, parentNode, text and a link to the document element.

This example gets an xml tree for the xml file boolean.xml.  This example is run in a terminal in the folder which contains boolean.xml and xml_simple_reader.py.


> python
Python 2.5.1 (r251:54863, Sep 22 2007, 01:43:31)
[GCC 4.2.1 (SUSE Linux)] on linux2
Type "help", "copyright", "credits" or "license" for more information.
>>> fileName = 'boolean.xml'
>>> file = open(fileName, 'r')
>>> xmlText = file.read()
>>> file.close()
>>> from xml_simple_reader import DocumentNode
>>> xmlParser = DocumentNode(fileName, xmlText)
>>> print(xmlParser)
  ?xml, {'version': '1.0'}
  ArtOfIllusion, {'xmlns:bf': '//babelfiche/codec', 'version': '2.0', 'fileversion': '3'}
  Scene, {'bf:id': 'theScene'}
  materials, {'bf:elem-type': 'java.lang.Object', 'bf:list': 'collection', 'bf:id': '1', 'bf:type': 'java.util.Vector'}
..
many more lines of the xml tree
..

"""


from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.geometry_utilities import matrix
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import xml_simple_writer
import cStringIO


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Nophead <http://hydraraptor.blogspot.com/>\nArt of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


globalGetAccessibleAttributeSet = set('getPaths getPreviousVertex getPreviousElementNode getVertexes parentNode'.split())


def createAppendByText(parentNode, xmlText):
	'Create and append the child nodes from the xmlText.'
	monad = OpenMonad(parentNode)
	for character in xmlText:
		monad = monad.getNextMonad(character)

def createAppendByTextb(parentNode, xmlText):
	'Create and append the child nodes from the xmlText.'
	monad = OpenMonad(parentNode)
	for character in xmlText:
		monad = monad.getNextMonad(character)

def getChildElementsByLocalName(childNodes, localName):
	'Get the childNodes which have the given local name.'
	childElementsByLocalName = []
	for childNode in childNodes:
		if localName.lower() == childNode.getNodeName():
			childElementsByLocalName.append(childNode)
	return childElementsByLocalName

def getDocumentNode(fileName):
	'Get the document from the file name.'
	xmlText = getFileText('test.xml')
	return DocumentNode(fileName, xmlText)

def getElementsByLocalName(childNodes, localName):
	'Get the descendents which have the given local name.'
	elementsByLocalName = getChildElementsByLocalName(childNodes, localName)
	for childNode in childNodes:
		if childNode.getNodeType() == 1:
			elementsByLocalName += childNode.getElementsByLocalName(localName)
	return elementsByLocalName

def getFileText(fileName, printWarning=True, readMode='r'):
	'Get the entire text of a file.'
	try:
		file = open(fileName, readMode)
		fileText = file.read()
		file.close()
		return fileText
	except IOError:
		if printWarning:
			print('The file ' + fileName + ' does not exist.')
	return ''


class CDATASectionMonad:
	'A monad to handle a CDATASection node.'
	def __init__(self, input, parentNode):
		'Initialize.'
		self.input = input
		self.parentNode = parentNode

	def getNextMonad(self, character):
		'Get the next monad.'
		self.input.write(character)
		if character == '>':
			inputString = self.input.getvalue()
			if inputString.endswith(']]>'):
				textContent = '<%s\n' % inputString
				self.parentNode.childNodes.append(CDATASectionNode(self.parentNode, textContent))
				return OpenMonad(self.parentNode)
		return self


class CDATASectionNode:
	'A CDATASection node.'
	def __init__(self, parentNode, textContent=''):
		'Initialize.'
		self.parentNode = parentNode
		self.textContent = textContent

	def __repr__(self):
		'Get the string representation of this CDATASection node.'
		return self.textContent

	def addToIdentifierDictionaries(self):
		'Add the element to the owner document identifier dictionaries.'
		pass

	def addXML(self, depth, output):
		'Add xml for this CDATASection node.'
		output.write(self.textContent)

	def appendSelfToParent(self):
		'Append self to the parentNode.'
		self.parentNode.appendChild(self)

	def copyXMLChildNodes(self, idSuffix, parentNode):
		'Copy the xml childNodes.'
		pass

	def getAttributes(self):
		'Get the attributes.'
		return {}

	def getChildNodes(self):
		'Get the empty set.'
		return []

	def getCopy(self, idSuffix, parentNode):
		'Copy the xml element, set its dictionary and add it to the parentNode.'
		copy = self.getCopyShallow()
		copy.parentNode = parentNode
		copy.appendSelfToParent()
		return copy

	def getCopyShallow(self, attributes=None):
		'Copy the node and set its parentNode.'
		return CDATASectionNode(self.parentNode, self.textContent)

	def getNodeName(self):
		'Get the node name.'
		return '#cdata-section'

	def getNodeType(self):
		'Get the node type.'
		return 4

	def getOwnerDocument(self):
		'Get the owner document.'
		return self.parentNode.getOwnerDocument()

	def getTextContent(self):
		'Get the text content.'
		return self.textContent

	def removeChildNodesFromIDNameParent(self):
		'Remove the childNodes from the id and name dictionaries and the childNodes.'
		pass

	def removeFromIDNameParent(self):
		'Remove this from the id and name dictionaries and the childNodes of the parentNode.'
		if self.parentNode != None:
			self.parentNode.childNodes.remove(self)

	def setParentAddToChildNodes(self, parentNode):
		'Set the parentNode and add this to its childNodes.'
		self.parentNode = parentNode
		if self.parentNode != None:
			self.parentNode.childNodes.append(self)

	attributes = property(getAttributes)
	childNodes = property(getChildNodes)
	nodeName = property(getNodeName)
	nodeType = property(getNodeType)
	ownerDocument = property(getOwnerDocument)


class CommentMonad(CDATASectionMonad):
	'A monad to handle a comment node.'
	def getNextMonad(self, character):
		'Get the next monad.'
		self.input.write(character)
		if character == '>':
			inputString = self.input.getvalue()
			if inputString.endswith('-->'):
				textContent = '<%s\n' % inputString
				self.parentNode.childNodes.append(CommentNode(self.parentNode, textContent))
				return OpenMonad(self.parentNode)
		return self


class CommentNode(CDATASectionNode):
	'A comment node.'
	def getCopyShallow(self, attributes=None):
		'Copy the node and set its parentNode.'
		return CommentNode(self.parentNode, self.textContent)

	def getNodeName(self):
		'Get the node name.'
		return '#comment'

	def getNodeType(self):
		'Get the node type.'
		return 8

	nodeName = property(getNodeName)
	nodeType = property(getNodeType)


class DocumentNode:
	'A class to parse an xml text and store the elements.'
	def __init__(self, fileName, xmlText):
		'Initialize.'
		self.childNodes = []
		self.fileName = fileName
		self.idDictionary = {}
		self.nameDictionary = {}
		self.parentNode = None
		self.tagDictionary = {}
		self.xmlText = xmlText
		createAppendByText(self, xmlText)

	def __repr__(self):
		'Get the string representation of this xml document.'
		output = cStringIO.StringIO()
		for childNode in self.childNodes:
			childNode.addXML(0, output)
		return output.getvalue()

	def appendChild(self, elementNode):
		'Append child elementNode to the child nodes.'
		self.childNodes.append(elementNode)
		elementNode.addToIdentifierDictionaries()
		return elementNode

	def getAttributes(self):
		'Get the attributes.'
		return {}

	def getCascadeBoolean(self, defaultBoolean, key):
		'Get the cascade boolean.'
		return defaultBoolean

	def getCascadeFloat(self, defaultFloat, key):
		'Get the cascade float.'
		return defaultFloat

	def getDocumentElement(self):
		'Get the document element.'
		if len(self.childNodes) == 0:
			return None
		return self.childNodes[-1]

	def getElementsByLocalName(self, localName):
		'Get the descendents which have the given local name.'
		return getElementsByLocalName(self.childNodes, localName)

	def getImportNameChain(self, suffix=''):
		'Get the import name chain with the suffix at the end.'
		return suffix

	def getNodeName(self):
		'Get the node name.'
		return '#document'

	def getNodeType(self):
		'Get the node type.'
		return 9

	def getOriginalRoot(self):
		'Get the original reparsed document element.'
		if evaluate.getEvaluatedBoolean(True, self.documentElement, 'getOriginalRoot'):
			return DocumentNode(self.fileName, self.xmlText).documentElement
		return None

	def getOwnerDocument(self):
		'Get the owner document.'
		return self

	attributes = property(getAttributes)
	documentElement = property(getDocumentElement)
	nodeName = property(getNodeName)
	nodeType = property(getNodeType)
	ownerDocument = property(getOwnerDocument)


class DocumentTypeMonad(CDATASectionMonad):
	'A monad to handle a document type node.'
	def getNextMonad(self, character):
		'Get the next monad.'
		self.input.write(character)
		if character == '>':
			inputString = self.input.getvalue()
			if inputString.endswith('?>'):
				textContent = '%s\n' % inputString
				self.parentNode.childNodes.append(DocumentTypeNode(self.parentNode, textContent))
				return OpenMonad(self.parentNode)
		return self


class DocumentTypeNode(CDATASectionNode):
	'A document type node.'
	def getCopyShallow(self, attributes=None):
		'Copy the node and set its parentNode.'
		return DocumentTypeNode(self.parentNode, self.textContent)

	def getNodeName(self):
		'Get the node name.'
		return '#forNowDocumentType'

	def getNodeType(self):
		'Get the node type.'
		return 10

	nodeName = property(getNodeName)
	nodeType = property(getNodeType)


class ElementEndMonad:
	'A monad to look for the end of an ElementNode tag.'
	def __init__(self, parentNode):
		'Initialize.'
		self.parentNode = parentNode

	def getNextMonad(self, character):
		'Get the next monad.'
		if character == '>':
			return TextMonad(self.parentNode)
		return self


class ElementLocalNameMonad:
	'A monad to set the local name of an ElementNode.'
	def __init__(self, character, parentNode):
		'Initialize.'
		self.input = cStringIO.StringIO()
		self.input.write(character)
		self.parentNode = parentNode

	def getNextMonad(self, character):
		'Get the next monad.'
		if character == '[':
			if (self.input.getvalue() + character).startswith('![CDATA['):
				self.input.write(character)
				return CDATASectionMonad(self.input, self.parentNode)
		if character == '-':
			if (self.input.getvalue() + character).startswith('!--'):
				self.input.write(character)
				return CommentMonad(self.input, self.parentNode)
		if character.isspace():
			self.setLocalName()
			return ElementReadMonad(self.elementNode)
		if character == '/':
			self.setLocalName()
			self.elementNode.appendSelfToParent()
			return ElementEndMonad(self.elementNode.parentNode)
		if character == '>':
			self.setLocalName()
			self.elementNode.appendSelfToParent()
			return TextMonad(self.elementNode)
		self.input.write(character)
		return self

	def setLocalName(self):
		'Set the class name.'
		self.elementNode = ElementNode(self.parentNode)
		self.elementNode.localName = self.input.getvalue().lower().strip()


class ElementNode:
	'An xml element.'
	def __init__(self, parentNode=None):
		'Initialize.'
		self.attributes = {}
		self.childNodes = []
		self.localName = ''
		self.parentNode = parentNode
		self.xmlObject = None

	def __repr__(self):
		'Get the string representation of this xml document.'
		return '%s\n%s\n%s' % (self.localName, self.attributes, self.getTextContent())

	def _getAccessibleAttribute(self, attributeName):
		'Get the accessible attribute.'
		global globalGetAccessibleAttributeSet
		if attributeName in globalGetAccessibleAttributeSet:
			return getattr(self, attributeName, None)
		return None

	def addSuffixToID(self, idSuffix):
		'Add the suffix to the id.'
		if 'id' in self.attributes:
			self.attributes['id'] += idSuffix

	def addToIdentifierDictionaries(self):
		'Add the element to the owner document identifier dictionaries.'
		ownerDocument = self.getOwnerDocument()
		importNameChain = self.getImportNameChain()
		idKey = self.getStrippedAttributesValue('id')
		if idKey != None:
			ownerDocument.idDictionary[importNameChain + idKey] = self
		nameKey = self.getStrippedAttributesValue('name')
		if nameKey != None:
			euclidean.addElementToListDictionaryIfNotThere(self, importNameChain + nameKey, ownerDocument.nameDictionary)
		for tagKey in self.getTagKeys():
			euclidean.addElementToListDictionaryIfNotThere(self, tagKey, ownerDocument.tagDictionary)

	def addXML(self, depth, output):
		'Add xml for this elementNode.'
		innerOutput = cStringIO.StringIO()
		xml_simple_writer.addXMLFromObjects(depth + 1, self.childNodes, innerOutput)
		innerText = innerOutput.getvalue()
		xml_simple_writer.addBeginEndInnerXMLTag(self.attributes, depth, innerText, self.localName, output, self.getTextContent())

	def appendChild(self, elementNode):
		'Append child elementNode to the child nodes.'
		self.childNodes.append(elementNode)
		elementNode.addToIdentifierDictionaries()
		return elementNode

	def appendSelfToParent(self):
		'Append self to the parentNode.'
		self.parentNode.appendChild(self)

	def copyXMLChildNodes(self, idSuffix, parentNode):
		'Copy the xml childNodes.'
		for childNode in self.childNodes:
			childNode.getCopy(idSuffix, parentNode)

	def getCascadeBoolean(self, defaultBoolean, key):
		'Get the cascade boolean.'
		if key in self.attributes:
			value = evaluate.getEvaluatedBoolean(None, self, key)
			if value != None:
				return value
		return self.parentNode.getCascadeBoolean(defaultBoolean, key)

	def getCascadeFloat(self, defaultFloat, key):
		'Get the cascade float.'
		if key in self.attributes:
			value = evaluate.getEvaluatedFloat(None, self, key)
			if value != None:
				return value
		return self.parentNode.getCascadeFloat(defaultFloat, key)

	def getChildElementsByLocalName(self, localName):
		'Get the childNodes which have the given local name.'
		return getChildElementsByLocalName(self.childNodes, localName)

	def getCopy(self, idSuffix, parentNode):
		'Copy the xml element, set its dictionary and add it to the parentNode.'
		matrix4X4 = matrix.getBranchMatrixSetElementNode(self)
		attributesCopy = self.attributes.copy()
		attributesCopy.update(matrix4X4.getAttributes('matrix.'))
		copy = self.getCopyShallow(attributesCopy)
		copy.setParentAddToChildNodes(parentNode)
		copy.addSuffixToID(idSuffix)
		copy.addToIdentifierDictionaries()
		self.copyXMLChildNodes(idSuffix, copy)
		return copy

	def getCopyShallow(self, attributes=None):
		'Copy the xml element and set its dictionary and parentNode.'
		if attributes == None: # to evade default initialization bug where a dictionary is initialized to the last dictionary
			attributes = {}
		copyShallow = ElementNode(self.parentNode)
		copyShallow.attributes = attributes
		copyShallow.localName = self.localName
		return copyShallow

	def getDocumentElement(self):
		'Get the document element.'
		return self.getOwnerDocument().getDocumentElement()

	def getElementNodeByID(self, idKey):
		'Get the xml element by id.'
		idDictionary = self.getOwnerDocument().idDictionary
		idKey = self.getImportNameChain() + idKey
		if idKey in idDictionary:
			return idDictionary[idKey]
		return None

	def getElementNodesByName(self, nameKey):
		'Get the xml elements by name.'
		nameDictionary = self.getOwnerDocument().nameDictionary
		nameKey = self.getImportNameChain() + nameKey
		if nameKey in nameDictionary:
			return nameDictionary[nameKey]
		return None

	def getElementNodesByTag(self, tagKey):
		'Get the xml elements by tag.'
		tagDictionary = self.getOwnerDocument().tagDictionary
		if tagKey in tagDictionary:
			return tagDictionary[tagKey]
		return None

	def getElementsByLocalName(self, localName):
		'Get the descendents which have the given local name.'
		return getElementsByLocalName(self.childNodes, localName)

	def getFirstChildByLocalName(self, localName):
		'Get the first childNode which has the given class name.'
		for childNode in self.childNodes:
			if localName.lower() == childNode.getNodeName():
				return childNode
		return None

	def getIDSuffix(self, elementIndex=None):
		'Get the id suffix from the dictionary.'
		suffix = self.localName
		if 'id' in self.attributes:
			suffix = self.attributes['id']
		if elementIndex == None:
			return '_%s' % suffix
		return '_%s_%s' % (suffix, elementIndex)

	def getImportNameChain(self, suffix=''):
		'Get the import name chain with the suffix at the end.'
		importName = self.getStrippedAttributesValue('_importName')
		if importName != None:
			suffix = '%s.%s' % (importName, suffix)
		return self.parentNode.getImportNameChain(suffix)

	def getNodeName(self):
		'Get the node name.'
		return self.localName

	def getNodeType(self):
		'Get the node type.'
		return 1

	def getOwnerDocument(self):
		'Get the owner document.'
		return self.parentNode.getOwnerDocument()

	def getParser(self):
		'Get the parser.'
		return self.getOwnerDocument()

	def getPaths(self):
		'Get all paths.'
		if self.xmlObject == None:
			return []
		return self.xmlObject.getPaths()

	def getPreviousElementNode(self):
		'Get previous ElementNode if it exists.'
		if self.parentNode == None:
			return None
		previousElementNodeIndex = self.parentNode.childNodes.index(self) - 1
		if previousElementNodeIndex < 0:
			return None
		return self.parentNode.childNodes[previousElementNodeIndex]

	def getPreviousVertex(self, defaultVector3=None):
		'Get previous vertex if it exists.'
		if self.parentNode == None:
			return defaultVector3
		if self.parentNode.xmlObject == None:
			return defaultVector3
		if len(self.parentNode.xmlObject.vertexes) < 1:
			return defaultVector3
		return self.parentNode.xmlObject.vertexes[-1]

	def getStrippedAttributesValue(self, keyString):
		'Get the stripped attribute value if the length is at least one, otherwise return None.'
		if keyString in self.attributes:
			strippedAttributesValue = self.attributes[keyString].strip()
			if len(strippedAttributesValue) > 0:
				return strippedAttributesValue
		return None

	def getSubChildWithID( self, idReference ):
		'Get the childNode which has the idReference.'
		for childNode in self.childNodes:
			if 'bf:id' in childNode.attributes:
				if childNode.attributes['bf:id'] == idReference:
					return childNode
			subChildWithID = childNode.getSubChildWithID( idReference )
			if subChildWithID != None:
				return subChildWithID
		return None

	def getTagKeys(self):
		'Get stripped tag keys.'
		if 'tags' not in self.attributes:
			return []
		tagKeys = []
		tagString = self.attributes['tags']
		if tagString.startswith('='):
			tagString = tagString[1 :]
		if tagString.startswith('['):
			tagString = tagString[1 :]
		if tagString.endswith(']'):
			tagString = tagString[: -1]
		for tagWord in tagString.split(','):
			tagKey = tagWord.strip()
			if tagKey != '':
				tagKeys.append(tagKey)
		return tagKeys

	def getTextContent(self):
		'Get the text from the child nodes.'
		if len(self.childNodes) == 0:
			return ''
		firstNode = self.childNodes[0]
		if firstNode.nodeType == 3:
			return firstNode.textContent
		return ''

	def getValueByKey( self, key ):
		'Get value by the key.'
		if key in evaluate.globalElementValueDictionary:
			return evaluate.globalElementValueDictionary[key](self)
		if key in self.attributes:
			return evaluate.getEvaluatedLinkValue(self, self.attributes[key])
		return None

	def getVertexes(self):
		'Get the vertexes.'
		if self.xmlObject == None:
			return []
		return self.xmlObject.getVertexes()

	def getXMLProcessor(self):
		'Get the xmlProcessor.'
		return self.getDocumentElement().xmlProcessor

	def linkObject(self, xmlObject):
		'Link self to xmlObject and add xmlObject to archivableObjects.'
		self.xmlObject = xmlObject
		self.xmlObject.elementNode = self
		self.parentNode.xmlObject.archivableObjects.append(self.xmlObject)

	def printAllVariables(self):
		'Print all variables.'
		print('attributes')
		print(self.attributes)
		print('childNodes')
		print(self.childNodes)
		print('localName')
		print(self.localName)
		print('parentNode')
		print(self.parentNode.getNodeName())
		print('text')
		print(self.getTextContent())
		print('xmlObject')
		print(self.xmlObject)
		print('')

	def printAllVariablesRoot(self):
		'Print all variables and the document element variables.'
		self.printAllVariables()
		documentElement = self.getDocumentElement()
		if documentElement != None:
			print('')
			print('Root variables:')
			documentElement.printAllVariables()

	def removeChildNodesFromIDNameParent(self):
		'Remove the childNodes from the id and name dictionaries and the childNodes.'
		childNodesCopy = self.childNodes[:]
		for childNode in childNodesCopy:
			childNode.removeFromIDNameParent()

	def removeFromIDNameParent(self):
		'Remove this from the id and name dictionaries and the childNodes of the parentNode.'
		self.removeChildNodesFromIDNameParent()
		idKey = self.getStrippedAttributesValue('id')
		if idKey != None:
			idDictionary = self.getOwnerDocument().idDictionary
			idKey = self.getImportNameChain() + idKey
			if idKey in idDictionary:
				del idDictionary[idKey]
		nameKey = self.getStrippedAttributesValue('name')
		if nameKey != None:
			euclidean.removeElementFromListTable(self, self.getImportNameChain() + nameKey, self.getOwnerDocument().nameDictionary)
		for tagKey in self.getTagKeys():
			euclidean.removeElementFromListTable(self, tagKey, self.getOwnerDocument().tagDictionary)
		if self.parentNode != None:
			self.parentNode.childNodes.remove(self)

	def setParentAddToChildNodes(self, parentNode):
		'Set the parentNode and add this to its childNodes.'
		self.parentNode = parentNode
		if self.parentNode != None:
			self.parentNode.childNodes.append(self)

	def setTextContent(self, textContent=''):
		'Get the text from the child nodes.'
		if len(self.childNodes) == 0:
			self.childNodes.append(TextNode(self, textContent))
			return
		firstNode = self.childNodes[0]
		if firstNode.nodeType == 3:
			firstNode.textContent = textContent
		self.childNodes.append(TextNode(self, textContent))

	nodeName = property(getNodeName)
	nodeType = property(getNodeType)
	ownerDocument = property(getOwnerDocument)
	textContent = property(getTextContent)


class ElementReadMonad:
	'A monad to read the attributes of the ElementNode tag.'
	def __init__(self, elementNode):
		'Initialize.'
		self.elementNode = elementNode

	def getNextMonad(self, character):
		'Get the next monad.'
		if character.isspace():
			return self
		if character == '/':
			self.elementNode.appendSelfToParent()
			return ElementEndMonad(self.elementNode.parentNode)
		if character == '>':
			self.elementNode.appendSelfToParent()
			return TextMonad(self.elementNode)
		return KeyMonad(character, self.elementNode)


class KeyMonad:
	'A monad to set the key of an attribute of an ElementNode.'
	def __init__(self, character, elementNode):
		'Initialize.'
		self.input = cStringIO.StringIO()
		self.input.write(character)
		self.elementNode = elementNode

	def getNextMonad(self, character):
		'Get the next monad.'
		if character == '=':
			return ValueMonad(self.elementNode, self.input.getvalue().strip())
		self.input.write(character)
		return self


class OpenChooseMonad(ElementEndMonad):
	'A monad to choose the next monad.'
	def getNextMonad(self, character):
		'Get the next monad.'
		if character.isspace():
			return self
		if character == '?':
			input = cStringIO.StringIO()
			input.write('<?')
			return DocumentTypeMonad(input, self.parentNode)
		if character == '/':
			return ElementEndMonad(self.parentNode.parentNode)
		return ElementLocalNameMonad(character, self.parentNode)


class OpenMonad(ElementEndMonad):
	'A monad to handle the open tag character.'
	def getNextMonad(self, character):
		'Get the next monad.'
		if character == '<':
			return OpenChooseMonad(self.parentNode)
		return self


class TextMonad:
	'A monad to handle the open tag character and set the text.'
	def __init__(self, parentNode):
		'Initialize.'
		self.input = cStringIO.StringIO()
		self.parentNode = parentNode

	def getNextMonad(self, character):
		'Get the next monad.'
		if character == '<':
			inputString = self.input.getvalue().strip()
			if len(inputString) > 0:
				self.parentNode.childNodes.append(TextNode(self.parentNode, inputString))
			return OpenChooseMonad(self.parentNode)
		self.input.write(character)
		return self


class TextNode(CDATASectionNode):
	'A text node.'
	def addXML(self, depth, output):
		'Add xml for this text node.'
		pass

	def getCopyShallow(self, attributes=None):
		'Copy the node and set its parentNode.'
		return TextNode(self.parentNode, self.textContent)

	def getNodeName(self):
		'Get the node name.'
		return '#text'

	def getNodeType(self):
		'Get the node type.'
		return 3

	nodeName = property(getNodeName)
	nodeType = property(getNodeType)


class ValueMonad:
	'A monad to set the value of an attribute of an ElementNode.'
	def __init__(self, elementNode, key):
		'Initialize.'
		self.elementNode = elementNode
		self.input = cStringIO.StringIO()
		self.key = key
		self.quoteCharacter = None

	def getNextMonad(self, character):
		'Get the next monad.'
		if self.quoteCharacter == None:
			if character == '"' or character == "'":
				self.quoteCharacter = character
			return self
		if self.quoteCharacter == character:
			self.elementNode.attributes[self.key] = self.input.getvalue()
			return ElementReadMonad(self.elementNode)
		self.input.write(character)
		return self

