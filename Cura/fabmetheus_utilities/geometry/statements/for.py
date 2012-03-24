"""
Polygon path.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.geometry_utilities import evaluate


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def processChildNodesByIndexValue( elementNode, function, index, indexValue, value ):
	"Process childNodes by index value."
	if indexValue.indexName != '':
		function.localDictionary[ indexValue.indexName ] = index
	if indexValue.valueName != '':
		function.localDictionary[ indexValue.valueName ] = value
	function.processChildNodes(elementNode)

def processElementNode(elementNode):
	"Process the xml element."
	if elementNode.xmlObject == None:
		elementNode.xmlObject = IndexValue(elementNode)
	if elementNode.xmlObject.inSplitWords == None:
		return
	xmlProcessor = elementNode.getXMLProcessor()
	if len( xmlProcessor.functions ) < 1:
		print('Warning, "for" element is not in a function in processElementNode in for.py for:')
		print(elementNode)
		return
	function = xmlProcessor.functions[-1]
	inValue = evaluate.getEvaluatedExpressionValueBySplitLine(elementNode, elementNode.xmlObject.inSplitWords)
	if inValue.__class__ == list or inValue.__class__ == str:
		for index, value in enumerate( inValue ):
			processChildNodesByIndexValue( elementNode, function, index, elementNode.xmlObject, value )
		return
	if inValue.__class__ == dict:
		inKeys = inValue.keys()
		inKeys.sort()
		for inKey in inKeys:
			processChildNodesByIndexValue( elementNode, function, inKey, elementNode.xmlObject, inValue[ inKey ] )


class IndexValue:
	"Class to get the in attribute, the index name and the value name."
	def __init__(self, elementNode):
		"Initialize."
		self.inSplitWords = None
		self.indexName = ''
		if 'index' in elementNode.attributes:
			self.indexName = elementNode.attributes['index']
		self.valueName = ''
		if 'value' in elementNode.attributes:
			self.valueName = elementNode.attributes['value']
		if 'in' in elementNode.attributes:
			self.inSplitWords = evaluate.getEvaluatorSplitWords( elementNode.attributes['in'] )
		else:
			print('Warning, could not find the "in" attribute in IndexValue in for.py for:')
			print(elementNode)
			return
		if len( self.inSplitWords ) < 1:
			self.inSplitWords = None
			print('Warning, could not get split words for the "in" attribute in IndexValue in for.py for:')
			print(elementNode)

