"""
String object attributes.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities import euclidean


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def _getAccessibleAttribute(attributeName, stringObject):
	'Get the accessible attribute.'
	if attributeName in globalNativeFunctionSet:
		return getattr(stringObject, attributeName, None)
	if attributeName in globalGetAccessibleAttributeSet:
		stringAttribute = StringAttribute(stringObject)
		return getattr(stringAttribute, attributeName, None)
	return None


class StringAttribute:
	'Class to handle a string.'
	def __init__(self, stringObject):
		'Initialize.'
		self.stringObject = stringObject

	def __repr__(self):
		"Get the string representation of this StringAttribute."
		return self.stringObject

	def add(self, nextString):
		'Get the add string, same as append.'
		return self.stringObject + nextString

	def append(self, nextString):
		'Get the append string.'
		return self.stringObject + nextString

	def copy(self):
		'Get the copy.'
		return self.stringObject[:]

	def delete(self, arguments):
		'Get the delete string.'
		deleteString = ''
		enumeratorSet = set(euclidean.getEnumeratorKeysAlwaysList(self.stringObject, arguments))
		for characterIndex, character in enumerate(self.stringObject):
			if characterIndex not in enumeratorSet:
				deleteString += character
		return deleteString

	def get(self, itemIndex):
		'Get value by characterIndex'
		return self.stringObject[itemIndex]

	def getExpansion(self, items):
		'Get the concatenated copies.'
		expansion = ''
		for itemIndex in xrange(items):
			expansion += self.stringObject
		return expansion

	def getIsIn(self, value):
		'Determine if the value is in.'
		return value in self.stringObject

	def getIsNotIn(self, value):
		'Determine if the value is in.'
		return not(value in self.stringObject)

	def getLength(self):
		'Get the length.'
		return len(self.stringObject)

	def getMax(self):
		'Get the max.'
		return max(self.stringObject)

	def getMin(self):
		'Get the min.'
		return min(self.stringObject)

	def insert(self, insertIndex, value):
		'Get the insert string.'
		if insertIndex < 0:
			insertIndex += len(self.stringObject)
		insertIndex = max(0, insertIndex)
		return self.stringObject[: insertIndex] + value + self.stringObject[insertIndex :]

	def keys(self):
		'Get the keys.'
		return range(len(self.stringObject))

	def length(self):
		'Get the length.'
		return len(self.stringObject)

	def remove(self, value):
		'Get the remove string.'
		removeIndex = self.stringObject.find(value)
		if removeIndex > -1:
			return self.stringObject[: removeIndex] + self.stringObject[removeIndex + len(value) :]
		return self.stringObject

	def reverse(self):
		'Get the reverse string.'
		return self.stringObject[: : -1]

	def set(self, itemIndex, value):
		'Set value.'
		self.stringObject[itemIndex] = value
		return self.stringObject

	def values(self):
		'Get the values.'
		values = []
		for character in self.stringObject:
			values.append(character)
		return values


globalAccessibleAttributeDictionary = 'add append copy delete get getExpansion getIsIn getIsNotIn getLength getMax getMin'.split()
globalAccessibleAttributeDictionary += 'insert keys length remove reverse set values'.split()
globalGetAccessibleAttributeSet = set(globalAccessibleAttributeDictionary)
globalNativeFunctions = 'capitalize center count decode encode endswith expandtabs find format index isalnum join'.split()
globalNativeFunctions += 'isalpha isdigit islower isspace istitle isupper ljust lower lstrip partition replace rfind rindex'.split()
globalNativeFunctions += 'rjust rpartition rsplit rstrip split splitlines startswith strip swapcase title translate upper zfill'.split()
globalNativeFunctionSet = set(globalNativeFunctions)
