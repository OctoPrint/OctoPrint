"""
Text vertexes.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import lineation
from fabmetheus_utilities.geometry.geometry_tools import path
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import svg_reader


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getGeometryOutput(derivation, elementNode):
	"Get vector3 vertexes from attributes."
	if derivation == None:
		derivation = TextDerivation(elementNode)
	if derivation.textString == '':
		print('Warning, textString is empty in getGeometryOutput in text for:')
		print(elementNode)
		return []
	geometryOutput = []
	for textComplexLoop in svg_reader.getTextComplexLoops(derivation.fontFamily, derivation.fontSize, derivation.textString):
		textComplexLoop.reverse()
		vector3Path = euclidean.getVector3Path(textComplexLoop)
		sideLoop = lineation.SideLoop(vector3Path)
		sideLoop.rotate(elementNode)
		geometryOutput += lineation.getGeometryOutputByManipulation(elementNode, sideLoop)
	return geometryOutput

def getGeometryOutputByArguments(arguments, elementNode):
	"Get vector3 vertexes from attribute dictionary by arguments."
	evaluate.setAttributesByArguments(['text', 'fontSize', 'fontFamily'], arguments, elementNode)
	return getGeometryOutput(None, elementNode)

def getNewDerivation(elementNode):
	'Get new derivation.'
	return TextDerivation(elementNode)

def processElementNode(elementNode):
	"Process the xml element."
	path.convertElementNode(elementNode, getGeometryOutput(None, elementNode))


class TextDerivation:
	"Class to hold text variables."
	def __init__(self, elementNode):
		'Set defaults.'
		self.fontFamily = evaluate.getEvaluatedString('Gentium Basic Regular', elementNode, 'font-family')
		self.fontFamily = evaluate.getEvaluatedString(self.fontFamily, elementNode, 'fontFamily')
		self.fontSize = evaluate.getEvaluatedFloat(12.0, elementNode, 'font-size')
		self.fontSize = evaluate.getEvaluatedFloat(self.fontSize, elementNode, 'fontSize')
		self.textString = elementNode.getTextContent()
		self.textString = evaluate.getEvaluatedString(self.textString, elementNode, 'text')
