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


def processElementNode(elementNode):
	"Process the xml element."
	if elementNode.xmlObject == None:
		if 'condition' in elementNode.attributes:
			value = elementNode.attributes['condition']
			elementNode.xmlObject = evaluate.getEvaluatorSplitWords(value)
		else:
			elementNode.xmlObject = []
	if len( elementNode.xmlObject ) < 1:
		return
	xmlProcessor = elementNode.getXMLProcessor()
	if len( xmlProcessor.functions ) < 1:
		return
	function = xmlProcessor.functions[-1]
	while evaluate.getEvaluatedExpressionValueBySplitLine(elementNode, elementNode.xmlObject) > 0:
		function.processChildNodes(elementNode)
