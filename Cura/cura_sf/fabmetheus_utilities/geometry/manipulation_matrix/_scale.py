"""
Boolean geometry scale.

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


globalExecutionOrder = 340


def getManipulatedGeometryOutput(elementNode, geometryOutput, prefix):
	"Get equated geometryOutput."
	scalePoints( elementNode, matrix.getVertexes(geometryOutput), prefix )
	return geometryOutput

def getManipulatedPaths(close, elementNode, loop, prefix, sideLength):
	"Get equated paths."
	scalePoints( elementNode, loop, prefix )
	return [loop]

def getNewDerivation(elementNode, prefix, sideLength):
	'Get new derivation.'
	return ScaleDerivation(elementNode)

def manipulateElementNode(elementNode, target):
	"Manipulate the xml element."
	derivation = ScaleDerivation(elementNode)
	if derivation.scaleTetragrid == None:
		print('Warning, scaleTetragrid was None in scale so nothing will be done for:')
		print(elementNode)
		return
	matrix.setAttributesToMultipliedTetragrid(target, derivation.scaleTetragrid)

def processElementNode(elementNode):
	"Process the xml element."
	solid.processElementNodeByFunction(elementNode, manipulateElementNode)

def scalePoints(elementNode, points, prefix):
	"Scale the points."
	scaleVector3Default = Vector3(1.0, 1.0, 1.0)
	scaleVector3 = matrix.getCumulativeVector3Remove(scaleVector3Default.copy(), elementNode, prefix)
	if scaleVector3 == scaleVector3Default:
		return
	for point in points:
		point.x *= scaleVector3.x
		point.y *= scaleVector3.y
		point.z *= scaleVector3.z


class ScaleDerivation:
	"Class to hold scale variables."
	def __init__(self, elementNode):
		'Set defaults.'
		self.scaleTetragrid = matrix.getScaleTetragrid(elementNode, '')
