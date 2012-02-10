"""
Add material to support overhang or remove material at the overhang angle.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import solid
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.geometry_utilities import matrix
from fabmetheus_utilities.vector3 import Vector3


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


globalExecutionOrder = 200


# http://www.opengl.org/discussion_boards/ubbthreads.php?ubb=showflat&Number=269576
# http://www.opengl.org/resources/code/samples/sig99/advanced99/notes/node159.html
#	m.a00 = -2 * norm.x * norm.x + 1;
#	m.a10 = -2 * norm.y * norm.x;
#	m.a20 = -2 * norm.z * norm.x;
#	m.a30 = 0;

#	m.a01 = -2 * norm.x * norm.y;
#	m.a11 = -2 * norm.y * norm.y + 1;
#	m.a21 = -2 * norm.z * norm.y;
#	m.a31 = 0;

#	m.a02 =	-2 * norm.x * norm.z;
#	m.a12 = -2 * norm.y * norm.z;
#	m.a22 = -2 * norm.z * norm.z + 1;
#	m.a32 = 0;

#	m.a03 = -2 * norm.x * d;
#	m.a13 = -2 * norm.y * d;
#	m.a23 = -2 * norm.z * d;
#	m.a33 = 1;

# normal = unit_vector(normal[:3])
# M = numpy.identity(4)
# M[:3, :3] -= 2.0 * numpy.outer(normal, normal)
# M[:3, 3] = (2.0 * numpy.dot(point[:3], normal)) * normal
# return M
def flipPoints(elementNode, points, prefix):
	'Flip the points.'
	derivation = FlipDerivation(elementNode, prefix)
	for point in points:
		point.setToVector3(point - 2.0 * derivation.axis.dot(point - derivation.origin) * derivation.axis)

def getFlippedLoop(elementNode, loop, prefix):
	'Get flipped loop.'
	flipPoints(elementNode, loop, prefix)
	if getShouldReverse(elementNode, prefix):
		loop.reverse()
	return loop

def getManipulatedGeometryOutput(elementNode, geometryOutput, prefix):
	'Get equated geometryOutput.'
	flipPoints(elementNode, matrix.getVertexes(geometryOutput), prefix)
	return geometryOutput

def getManipulatedPaths(close, elementNode, loop, prefix, sideLength):
	'Get flipped paths.'
	return [getFlippedLoop(elementNode, loop, prefix)]

def getNewDerivation(elementNode, prefix, sideLength):
	'Get new derivation.'
	return FlipDerivation(elementNode, prefix)

def getShouldReverse(elementNode, prefix):
	'Determine if the loop should be reversed.'
	return evaluate.getEvaluatedBoolean(True, elementNode, prefix + 'reverse')

def processElementNode(elementNode):
	'Process the xml element.'
	solid.processElementNodeByFunctionPair(elementNode, getManipulatedGeometryOutput, getManipulatedPaths)


class FlipDerivation:
	"Class to hold flip variables."
	def __init__(self, elementNode, prefix):
		'Set defaults.'
		self.origin = evaluate.getVector3ByPrefix(Vector3(), elementNode, prefix + 'origin')
		self.axis = evaluate.getVector3ByPrefix(Vector3(1.0, 0.0, 0.0), elementNode, prefix + 'axis').getNormalized()
