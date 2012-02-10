"""
Polygon path.

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
		derivation = CircleDerivation(elementNode)
	angleTotal = math.radians(derivation.start)
	loop = []
	sidesCeiling = int(math.ceil(abs(derivation.sides) * derivation.extent / 360.0))
	sideAngle = math.radians(derivation.extent) / sidesCeiling
	if derivation.sides < 0.0:
		sideAngle = -sideAngle
	spiral = lineation.Spiral(derivation.spiral, 0.5 * sideAngle / math.pi)
	for side in xrange(sidesCeiling + 1):
		unitPolar = euclidean.getWiddershinsUnitPolar(angleTotal)
		x = unitPolar.real * derivation.radiusArealized.real
		y = unitPolar.imag * derivation.radiusArealized.imag
		vertex = spiral.getSpiralPoint(unitPolar, Vector3(x, y))
		angleTotal += sideAngle
		loop.append(vertex)
	radiusMaximum = 0.000001 * max(derivation.radiusArealized.real, derivation.radiusArealized.imag)
	loop = euclidean.getLoopWithoutCloseEnds(radiusMaximum, loop)
	lineation.setClosedAttribute(elementNode, derivation.revolutions)
	return lineation.getGeometryOutputByLoop(elementNode, lineation.SideLoop(loop, sideAngle))

def getGeometryOutputByArguments(arguments, elementNode):
	"Get vector3 vertexes from attribute dictionary by arguments."
	evaluate.setAttributesByArguments(['radius', 'start', 'end', 'revolutions'], arguments, elementNode)
	return getGeometryOutput(None, elementNode)

def getNewDerivation(elementNode):
	'Get new derivation.'
	return CircleDerivation(elementNode)

def processElementNode(elementNode):
	"Process the xml element."
	path.convertElementNode(elementNode, getGeometryOutput(None, elementNode))


class CircleDerivation:
	"Class to hold circle variables."
	def __init__(self, elementNode):
		'Set defaults.'
		self.radius = lineation.getRadiusComplex(elementNode, complex(1.0, 1.0))
		self.sides = evaluate.getEvaluatedFloat(None, elementNode, 'sides')
		if self.sides == None:
			radiusMaximum = max(self.radius.real, self.radius.imag)
			self.sides = evaluate.getSidesMinimumThreeBasedOnPrecisionSides(elementNode, radiusMaximum)
		self.radiusArealized = evaluate.getRadiusArealizedBasedOnAreaRadius(elementNode, self.radius, self.sides)
		self.start = evaluate.getEvaluatedFloat(0.0, elementNode, 'start')
		end = evaluate.getEvaluatedFloat(360.0, elementNode, 'end')
		self.revolutions = evaluate.getEvaluatedFloat(1.0, elementNode, 'revolutions')
		self.extent = evaluate.getEvaluatedFloat(end - self.start, elementNode, 'extent')
		self.extent += 360.0 * (self.revolutions - 1.0)
		self.spiral = evaluate.getVector3ByPrefix(None, elementNode, 'spiral')
