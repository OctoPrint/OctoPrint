"""
Square path.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import lineation
from fabmetheus_utilities.geometry.geometry_tools import path
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import euclidean
import math


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getGeometryOutput(derivation, elementNode):
	"Get vector3 vertexes from attribute dictionary."
	if derivation == None:
		derivation = SquareDerivation(elementNode)
	topRight = complex(derivation.topDemiwidth, derivation.demiheight)
	topLeft = complex(-derivation.topDemiwidth, derivation.demiheight)
	bottomLeft = complex(-derivation.bottomDemiwidth, -derivation.demiheight)
	bottomRight = complex(derivation.bottomDemiwidth, -derivation.demiheight)
	if derivation.interiorAngle != 90.0:
		interiorPlaneAngle = euclidean.getWiddershinsUnitPolar(math.radians(derivation.interiorAngle - 90.0))
		topRight = (topRight - bottomRight) * interiorPlaneAngle + bottomRight
		topLeft = (topLeft - bottomLeft) * interiorPlaneAngle + bottomLeft
	lineation.setClosedAttribute(elementNode, derivation.revolutions)
	complexLoop = [topRight, topLeft, bottomLeft, bottomRight]
	originalLoop = complexLoop[:]
	for revolution in xrange(1, derivation.revolutions):
		complexLoop += originalLoop
	spiral = lineation.Spiral(derivation.spiral, 0.25)
	loop = []
	loopCentroid = euclidean.getLoopCentroid(originalLoop)
	for point in complexLoop:
		unitPolar = euclidean.getNormalized(point - loopCentroid)
		loop.append(spiral.getSpiralPoint(unitPolar, Vector3(point.real, point.imag)))
	return lineation.getGeometryOutputByLoop(elementNode, lineation.SideLoop(loop, 0.5 * math.pi))

def getGeometryOutputByArguments(arguments, elementNode):
	"Get vector3 vertexes from attribute dictionary by arguments."
	if len(arguments) < 1:
		return getGeometryOutput(None, elementNode)
	inradius = 0.5 * euclidean.getFloatFromValue(arguments[0])
	elementNode.attributes['inradius.x'] = str(inradius)
	if len(arguments) > 1:
		inradius = 0.5 * euclidean.getFloatFromValue(arguments[1])
	elementNode.attributes['inradius.y'] = str(inradius)
	return getGeometryOutput(None, elementNode)

def getNewDerivation(elementNode):
	'Get new derivation.'
	return SquareDerivation(elementNode)

def processElementNode(elementNode):
	"Process the xml element."
	path.convertElementNode(elementNode, getGeometryOutput(None, elementNode))


class SquareDerivation:
	"Class to hold square variables."
	def __init__(self, elementNode):
		'Set defaults.'
		self.inradius = lineation.getInradius(complex(1.0, 1.0), elementNode)
		self.demiwidth = lineation.getFloatByPrefixBeginEnd(elementNode, 'demiwidth', 'width', self.inradius.real)
		self.demiheight = lineation.getFloatByPrefixBeginEnd(elementNode, 'demiheight', 'height', self.inradius.imag)
		self.bottomDemiwidth = lineation.getFloatByPrefixBeginEnd(elementNode, 'bottomdemiwidth', 'bottomwidth', self.demiwidth)
		self.topDemiwidth = lineation.getFloatByPrefixBeginEnd(elementNode, 'topdemiwidth', 'topwidth', self.demiwidth)
		self.interiorAngle = evaluate.getEvaluatedFloat(90.0, elementNode, 'interiorangle')
		self.revolutions = evaluate.getEvaluatedInt(1, elementNode, 'revolutions')
		self.spiral = evaluate.getVector3ByPrefix(None, elementNode, 'spiral')
