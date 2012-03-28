"""
Dictionary object attributes.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities import euclidean


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def _getAccessibleAttribute(attributeName, dictionaryObject):
	'Get the accessible attribute.'
	if attributeName in globalNativeFunctionSet:
		return getattr(dictionaryObject, attributeName, None)
	if attributeName in globalGetAccessibleAttributeSet:
		stringAttribute = DictionaryAttribute(dictionaryObject)
		return getattr(stringAttribute, attributeName, None)
	return None


class DictionaryAttribute:
	'Class to handle a dictionary.'
	def __init__(self, dictionaryObject):
		'Initialize.'
		self.dictionaryObject = dictionaryObject

	def __repr__(self):
		"Get the dictionary representation of this DictionaryAttribute."
		return str(self.dictionaryObject)

	def count(self, value):
		'Get the count.'
		countTotal = 0
		for key, iteratorValue in self.dictionaryObject.iteritems():
			if iteratorValue == value:
				countTotal += 1
		return countTotal

	def delete(self, arguments):
		'Get the delete dictionary.'
		if arguments.__class__ != list:
			del self.dictionaryObject[arguments]
			return self.dictionaryObject
		if len(arguments) == 0:
			self.dictionaryObject.clear()
			return self.dictionaryObject
		if len(arguments) == 1:
			del self.dictionaryObject[arguments[0]]
			return self.dictionaryObject
		for enumeratorKey in euclidean.getEnumeratorKeysAlwaysList(self.dictionaryObject, arguments):
			del self.dictionaryObject[enumeratorKey]
		return self.dictionaryObject

	def getIsIn(self, value):
		'Determine if the value is in.'
		return value in self.dictionaryObject

	def getIsNotIn(self, value):
		'Determine if the value is in.'
		return not(value in self.dictionaryObject)

	def getLength(self):
		'Get the length.'
		return len(self.dictionaryObject)

	def getMax(self):
		'Get the max.'
		return max(self.dictionaryObject)

	def getMin(self):
		'Get the min.'
		return min(self.dictionaryObject)

	def index(self, value):
		'Get the index element.'
		for key, iteratorValue in self.dictionaryObject.iteritems():
			if iteratorValue == value:
				return key
		raise ValueError('Value (%s) not found in index in DictionaryAttribute for (%s).' % (value, self.dictionaryObject))

	def length(self):
		'Get the length.'
		return len(self.dictionaryObject)

	def set(self, itemIndex, value):
		'Set value.'
		self.dictionaryObject[itemIndex] = value
		return self.dictionaryObject


globalAccessibleAttributeDictionary = 'count delete getIsIn getIsNotIn getLength getMax getMin index length set'.split()
globalGetAccessibleAttributeSet = set(globalAccessibleAttributeDictionary)
globalNativeFunctions = 'clear copy fromkeys get items keys pop popitem remove setdefault update values'.split()
globalNativeFunctionSet = set(globalNativeFunctions)
