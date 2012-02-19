"""
Boolean geometry utilities.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def _getAccessibleAttribute(attributeName, elementNode):
	'Get the accessible attribute.'
	if attributeName in globalGetAccessibleAttributeSet:
		return getattr(Document(elementNode), attributeName, None)
	return None


class Document:
	'Class to handle elementNodes in a document.'
	def __init__(self, elementNode):
		'Initialize.'
		self.elementNode = elementNode

	def __repr__(self):
		'Get the string representation of this Document.'
		return self.elementNode

	def getCascadeBoolean(self, defaultBoolean, key):
		'Get cascade boolean.'
		return self.elementNode.getCascadeBoolean(defaultBoolean, key)

	def getCascadeFloat(self, defaultFloat, key):
		'Get cascade float.'
		return self.elementNode.getCascadeFloat(defaultFloat, key)

	def getDocumentElement(self):
		'Get document element element.'
		return self.elementNode.getDocumentElement()

	def getElementByID(self, idKey):
		'Get element by id.'
		elementByID = self.elementNode.getElementNodeByID(idKey)
		if elementByID == None:
			print('Warning, could not get elementByID in getElementByID in document for:')
			print(idKey)
			print(self.elementNode)
		return elementByID

	def getElementsByName(self, nameKey):
		'Get element by name.'
		elementsByName = self.elementNode.getElementNodesByName(nameKey)
		if elementsByName == None:
			print('Warning, could not get elementsByName in getElementsByName in document for:')
			print(nameKey)
			print(self.elementNode)
		return elementsByName

	def getElementsByTag(self, tagKey):
		'Get element by tag.'
		elementsByTag = self.elementNode.getElementNodesByTag(tagKey)
		if elementsByTag == None:
			print('Warning, could not get elementsByTag in getElementsByTag in document for:')
			print(tagKey)
			print(self.elementNode)
		return elementsByTag

	def getParentNode(self):
		'Get parentNode element.'
		return self.elementNode.parentNode

	def getPrevious(self):
		'Get previous element.'
		return self.getPreviousElement()

	def getPreviousElement(self):
		'Get previous element.'
		return self.elementNode.getPreviousElementNode()

	def getPreviousVertex(self):
		'Get previous element.'
		return self.elementNode.getPreviousVertex()

	def getSelfElement(self):
		'Get self element.'
		return self.elementNode


globalAccessibleAttributeDictionary = 'getCascadeBoolean getCascadeFloat getDocumentElement getElementByID getElementsByName'.split()
globalAccessibleAttributeDictionary += 'getElementsByTag getParentNode getPrevious getPreviousElement getPreviousVertex'.split()
globalAccessibleAttributeDictionary += 'getSelfElement'.split()
globalGetAccessibleAttributeSet = set(globalAccessibleAttributeDictionary)
