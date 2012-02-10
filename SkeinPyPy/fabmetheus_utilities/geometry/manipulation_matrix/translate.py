"""
Boolean geometry translation.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import solid
from fabmetheus_utilities.geometry.geometry_utilities import matrix
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import euclidean


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


globalExecutionOrder = 380


def getManipulatedGeometryOutput(elementNode, geometryOutput, prefix):
	"Get equated geometryOutput."
	translatePoints(elementNode, matrix.getVertexes(geometryOutput), prefix)
	return geometryOutput

def getManipulatedPaths(close, elementNode, loop, prefix, sideLength):
	"Get equated paths."
	translatePoints(elementNode, loop, prefix)
	return [loop]

def getNewDerivation(elementNode, prefix, sideLength):
	'Get new derivation.'
	return TranslateDerivation(elementNode)

def manipulateElementNode(elementNode, target):
	"Manipulate the xml element."
	derivation = TranslateDerivation(elementNode)
	if derivation.translateTetragrid == None:
		print('Warning, translateTetragrid was None in translate so nothing will be done for:')
		print(elementNode)
		return
	matrix.setAttributesToMultipliedTetragrid(target, derivation.translateTetragrid)

def processElementNode(elementNode):
	"Process the xml element."
	solid.processElementNodeByFunction(elementNode, manipulateElementNode)

def translateNegativesPositives(negatives, positives, translation):
	'Translate the negatives and postives.'
	euclidean.translateVector3Path(matrix.getVertexes(negatives), translation)
	euclidean.translateVector3Path(matrix.getVertexes(positives), translation)

def translatePoints(elementNode, points, prefix):
	"Translate the points."
	translateVector3 = matrix.getCumulativeVector3Remove(Vector3(), elementNode, prefix)
	if abs(translateVector3) > 0.0:
		euclidean.translateVector3Path(points, translateVector3)


class TranslateDerivation:
	"Class to hold translate variables."
	def __init__(self, elementNode):
		'Set defaults.'
		self.translateTetragrid = matrix.getTranslateTetragrid(elementNode, '')
