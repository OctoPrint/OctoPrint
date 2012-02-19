"""
Add material to support overhang or remove material at the overhang angle.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import solid
from fabmetheus_utilities.geometry.geometry_tools import face
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.geometry_utilities import matrix
from fabmetheus_utilities.geometry.manipulation_shapes import flip
from fabmetheus_utilities.geometry.solids import triangle_mesh
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import euclidean


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


globalExecutionOrder = 200


def getManipulatedGeometryOutput(elementNode, geometryOutput, prefix):
	'Get equated geometryOutput.'
	flippedGeometryOutput = triangle_mesh.getGeometryOutputCopy(geometryOutput)
	flip.flipPoints(elementNode, matrix.getVertexes(flippedGeometryOutput), prefix)
	if flip.getShouldReverse(elementNode, prefix):
		flippedFaces = face.getFaces(flippedGeometryOutput)
		for flippedFace in flippedFaces:
			flippedFace.vertexIndexes.reverse()
	return {'union' : {'shapes' : [flippedGeometryOutput, geometryOutput]}}

def getManipulatedPaths(close, elementNode, loop, prefix, sideLength):
	'Get flipped paths.'
	return [loop + flip.getFlippedLoop(elementNode, euclidean.getPathCopy(loop), prefix)]

def getNewDerivation(elementNode, prefix, sideLength):
	'Get new derivation.'
	return evaluate.EmptyObject()

def processElementNode(elementNode):
	'Process the xml element.'
	solid.processElementNodeByFunctionPair(elementNode, getManipulatedGeometryOutput, getManipulatedPaths)
