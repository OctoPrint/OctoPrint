"""
List object attributes.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities import euclidean


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def _getAccessibleAttribute(attributeName, listObject):
	'Get the accessible attribute.'
	if attributeName in globalNativeFunctionSet:
		return getattr(listObject, attributeName, None)
	if attributeName in globalGetAccessibleAttributeSet:
		stringAttribute = ListAttribute(listObject)
		return getattr(stringAttribute, attributeName, None)
	return None


class ListAttribute:
	'Class to handle a list.'
	def __init__(self, listObject):
		'Initialize.'
		self.listObject = listObject

	def __repr__(self):
		"Get the list representation of this ListAttribute."
		return str(self.listObject)

	def add(self, value):
		'Get the concatenation, same as append.'
		return self.listObject + [value]

	def copy(self):
		'Get the copy.'
		return self.listObject[:]

	def delete(self, arguments):
		'Get the delete list.'
		deleteList = []
		enumeratorSet = set(euclidean.getEnumeratorKeysAlwaysList(self.listObject, arguments))
		for elementIndex, element in enumerate(self.listObject):
			if elementIndex not in enumeratorSet:
				deleteList.append(element)
		return deleteList

	def get(self, itemIndex):
		'Get value by index'
		return self.listObject[itemIndex]

	def getExpansion(self, items):
		'Get the concatenated copies.'
		expansion = []
		for itemIndex in xrange(items):
			expansion += self.listObject[:]
		return expansion

	def getIsIn(self, value):
		'Determine if the value is in.'
		return value in self.listObject

	def getIsNotIn(self, value):
		'Determine if the value is in.'
		return not(value in self.listObject)

	def getLength(self):
		'Get the length.'
		return len(self.listObject)

	def getMax(self):
		'Get the max.'
		return max(self.listObject)

	def getMin(self):
		'Get the min.'
		return min(self.listObject)

	def insert(self, insertIndex, value):
		'Get the insert list.'
		if insertIndex < 0:
			insertIndex += len(self.listObject)
		insertIndex = max(0, insertIndex)
		return self.listObject[: insertIndex] + [value] + self.listObject[insertIndex :]

	def keys(self):
		'Get the keys.'
		return range(len(self.listObject))

	def length(self):
		'Get the length.'
		return len(self.listObject)

	def rindex(self, value):
		'Get the rindex element.'
		for elementIndex, element in enumerate(self.listObject):
			if element == value:
				return elementIndex
		raise ValueError('Value (%s) not found in rindex in ListAttribute for (%s).' % (value, self.listObject))

	def set(self, itemIndex, value):
		'Set value.'
		self.listObject[itemIndex] = value
		return self.listObject

	def values(self, arguments=None):
		'Get the values.'
		return self.listObject


globalAccessibleAttributeDictionary = 'add copy count delete get getExpansion getIsIn getIsNotIn getLength getMax getMin'.split()
globalAccessibleAttributeDictionary += 'insert keys length rindex set values'.split()
globalGetAccessibleAttributeSet = set(globalAccessibleAttributeDictionary)
globalNativeFunctions = 'append extend index pop remove reverse sort'.split()
globalNativeFunctionSet = set(globalNativeFunctions)
