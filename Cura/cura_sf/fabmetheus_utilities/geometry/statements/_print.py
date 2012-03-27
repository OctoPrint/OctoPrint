"""
Print statement.

There is also the print attribute in geometry_utilities/evaluate_fundamentals/print.py

The model is xml_models/geometry_utilities/evaluate_fundamentals/print.xml

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.geometry_utilities import evaluate


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getLocalDictionary( attributesKey, elementNode):
	"Get the local dictionary."
	xmlProcessor = elementNode.getXMLProcessor()
	if len( xmlProcessor.functions ) < 1:
		return None
	return xmlProcessor.functions[-1].localDictionary

def printAttributesKey( attributesKey, elementNode):
	"Print the attributesKey."
	if attributesKey.lower() == '_localdictionary':
		localDictionary = getLocalDictionary( attributesKey, elementNode)
		if localDictionary != None:
			localDictionaryKeys = localDictionary.keys()
			attributeValue = elementNode.attributes[attributesKey]
			if attributeValue != '':
				attributeValue = ' - ' + attributeValue
			print('Local Dictionary Variables' + attributeValue )
			localDictionaryKeys.sort()
			for localDictionaryKey in localDictionaryKeys:
				print('%s: %s' % ( localDictionaryKey, localDictionary[ localDictionaryKey ] ) )
			return
	value = elementNode.attributes[attributesKey]
	evaluatedValue = None
	if value == '':
		evaluatedValue = evaluate.getEvaluatedExpressionValue(elementNode, attributesKey)
	else:
		evaluatedValue = evaluate.getEvaluatedExpressionValue(elementNode, value)
	print('%s: %s' % ( attributesKey, evaluatedValue ) )

def processElementNode(elementNode):
	"Process the xml element."
	if len(elementNode.getTextContent()) > 1:
		print(elementNode.getTextContent())
		return
	attributesKeys = elementNode.attributes.keys()
	if len( attributesKeys ) < 1:
		print('')
		return
	attributesKeys.sort()
	for attributesKey in attributesKeys:
		printAttributesKey( attributesKey, elementNode)
