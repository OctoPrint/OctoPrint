"""
Boolean geometry bottom.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import solid
from fabmetheus_utilities.geometry.geometry_utilities.evaluate_elements import setting
from fabmetheus_utilities.geometry.geometry_utilities import boolean_geometry
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.geometry_utilities import matrix
from fabmetheus_utilities import euclidean


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


globalExecutionOrder = 400


def bottomElementNode(derivation, target):
	"Bottom target."
	xmlObject = target.xmlObject
	if xmlObject == None:
		print('Warning, bottomTarget in bottom could not get xmlObject for:')
		print(target)
		print(derivation.elementNode)
		return
	targetMatrix = matrix.getBranchMatrixSetElementNode(target)
	lift = derivation.altitude
	transformedPaths = xmlObject.getTransformedPaths()
	if len(transformedPaths) > 0:
		lift += derivation.getAdditionalPathLift() - euclidean.getBottomByPaths(transformedPaths)
	else:
		lift -= boolean_geometry.getMinimumZ(xmlObject)
	targetMatrix.tetragrid = matrix.getIdentityTetragrid(targetMatrix.tetragrid)
	targetMatrix.tetragrid[2][3] += lift
	matrix.setElementNodeDictionaryMatrix(target, targetMatrix)

def getManipulatedGeometryOutput(elementNode, geometryOutput, prefix):
	'Get bottomed geometryOutput.'
	derivation = BottomDerivation(elementNode, prefix)
	copyShallow = elementNode.getCopyShallow()
	solid.processElementNodeByGeometry(copyShallow, geometryOutput)
	targetMatrix = matrix.getBranchMatrixSetElementNode(elementNode)
	matrix.setElementNodeDictionaryMatrix(copyShallow, targetMatrix)
	minimumZ = boolean_geometry.getMinimumZ(copyShallow.xmlObject)
	copyShallow.parentNode.xmlObject.archivableObjects.remove(copyShallow.xmlObject)
	lift = derivation.altitude - minimumZ
	vertexes = matrix.getVertexes(geometryOutput)
	for vertex in vertexes:
		vertex.z += lift
	return geometryOutput

def getManipulatedPaths(close, elementNode, loop, prefix, sideLength):
	'Get flipped paths.'
	if len(loop) < 1:
		return [[]]
	derivation = BottomDerivation(elementNode, prefix)
	targetMatrix = matrix.getBranchMatrixSetElementNode(elementNode)
	transformedLoop = matrix.getTransformedVector3s(matrix.getIdentityTetragrid(targetMatrix.tetragrid), loop)
	lift = derivation.altitude + derivation.getAdditionalPathLift() - euclidean.getBottomByPath(transformedLoop)
	for point in loop:
		point.z += lift
	return [loop]

def getNewDerivation(elementNode, prefix, sideLength):
	'Get new derivation.'
	return BottomDerivation(elementNode, '')

def processElementNode(elementNode):
	"Process the xml element."
	processElementNodeByDerivation(None, elementNode)

def processElementNodeByDerivation(derivation, elementNode):
	'Process the xml element by derivation.'
	if derivation == None:
		derivation = BottomDerivation(elementNode, '')
	targets = evaluate.getElementNodesByKey(elementNode, 'target')
	if len(targets) < 1:
		print('Warning, processElementNode in bottom could not get targets for:')
		print(elementNode)
		return
	for target in targets:
		bottomElementNode(derivation, target)


class BottomDerivation:
	"Class to hold bottom variables."
	def __init__(self, elementNode, prefix):
		'Set defaults.'
		self.altitude = evaluate.getEvaluatedFloat(0.0, elementNode, prefix + 'altitude')
		self.elementNode = elementNode
		self.liftPath = evaluate.getEvaluatedBoolean(True, elementNode, prefix + 'liftPath')

	def getAdditionalPathLift(self):
		"Get path lift."
		return 0.5 * setting.getLayerHeight(self.elementNode) * float(self.liftPath)
