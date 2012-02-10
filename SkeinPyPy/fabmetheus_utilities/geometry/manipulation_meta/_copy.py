"""
Boolean geometry copy.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import lineation
from fabmetheus_utilities.geometry.creation import solid
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.geometry_utilities import matrix
from fabmetheus_utilities import euclidean


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getNewDerivation(elementNode):
	'Get new derivation.'
	return CopyDerivation(elementNode)

def processElementNode(elementNode):
	'Process the xml element.'
	processElementNodeByDerivation(None, elementNode)

def processElementNodeByDerivation(derivation, elementNode):
	'Process the xml element by derivation.'
	if derivation == None:
		derivation = CopyDerivation(elementNode)
	if derivation.target == None:
		print('Warning, copy could not get target for:')
		print(elementNode)
		return
	del elementNode.attributes['target']
	copyMatrix = matrix.getBranchMatrixSetElementNode(elementNode)
	targetMatrix = matrix.getBranchMatrixSetElementNode(derivation.target)
	targetDictionaryCopy = evaluate.removeIdentifiersFromDictionary(derivation.target.attributes.copy())
	targetDictionaryCopy.update(elementNode.attributes)
	elementNode.attributes = targetDictionaryCopy
	euclidean.removeTrueFromDictionary(elementNode.attributes, 'visible')
	elementNode.localName = derivation.target.localName
	derivation.target.copyXMLChildNodes(elementNode.getIDSuffix(), elementNode)
	elementNode.getXMLProcessor().processElementNode(elementNode)
	if copyMatrix != None and targetMatrix != None:
		elementNode.xmlObject.matrix4X4 = copyMatrix.getSelfTimesOther(targetMatrix.tetragrid)
	if elementNode.xmlObject == None:
		return
	if len(elementNode.xmlObject.getPaths()) > 0:
		lineation.processElementNode(elementNode)
		return
	geometryOutput = elementNode.xmlObject.getGeometryOutput()
	if geometryOutput == None:
		return
	solidMatchingPlugins = solid.getSolidMatchingPlugins(elementNode)
	if len(solidMatchingPlugins) == 0:
		return
	geometryOutput = solid.getGeometryOutputByManipulation(elementNode, geometryOutput)
	elementNode.xmlObject.transformGeometryOutput(geometryOutput)
	lineation.removeChildNodesFromElementObject(elementNode)
	elementNode.getXMLProcessor().convertElementNode(elementNode, geometryOutput)


class CopyDerivation:
	"Class to hold copy variables."
	def __init__(self, elementNode):
		'Set defaults.'
		self.target = evaluate.getElementNodeByKey(elementNode, 'target')
