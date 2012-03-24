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
		derivation = PolygonDerivation(elementNode)
	loop = []
	spiral = lineation.Spiral(derivation.spiral, 0.5 * derivation.sideAngle / math.pi)
	for side in xrange(derivation.start, derivation.start + derivation.extent + 1):
		angle = float(side) * derivation.sideAngle
		unitPolar = euclidean.getWiddershinsUnitPolar(angle)
		vertex = spiral.getSpiralPoint(unitPolar, Vector3(unitPolar.real * derivation.radius.real, unitPolar.imag * derivation.radius.imag))
		loop.append(vertex)
	loop = euclidean.getLoopWithoutCloseEnds(0.000001 * max(derivation.radius.real, derivation.radius.imag), loop)
	lineation.setClosedAttribute(elementNode, derivation.revolutions)
	return lineation.getGeometryOutputByLoop(elementNode, lineation.SideLoop(loop, derivation.sideAngle))

def getGeometryOutputByArguments(arguments, elementNode):
	"Get vector3 vertexes from attribute dictionary by arguments."
	evaluate.setAttributesByArguments(['sides', 'radius'], arguments, elementNode)
	return getGeometryOutput(None, elementNode)

def getNewDerivation(elementNode):
	'Get new derivation.'
	return PolygonDerivation(elementNode)

def processElementNode(elementNode):
	"Process the xml element."
	path.convertElementNode(elementNode, getGeometryOutput(None, elementNode))


class PolygonDerivation:
	"Class to hold polygon variables."
	def __init__(self, elementNode):
		'Set defaults.'
		self.sides = evaluate.getEvaluatedFloat(4.0, elementNode, 'sides')
		self.sideAngle = 2.0 * math.pi / self.sides
		cosSide = math.cos(0.5 * self.sideAngle)
		self.radius = lineation.getComplexByMultiplierPrefixes(elementNode, cosSide, ['apothem', 'inradius'], complex(1.0, 1.0))
		self.radius = lineation.getComplexByPrefixes(elementNode, ['demisize', 'radius'], self.radius)
		self.radius = lineation.getComplexByMultiplierPrefixes(elementNode, 2.0, ['diameter', 'size'], self.radius)
		self.sidesCeiling = int(math.ceil(abs(self.sides)))
		self.start = evaluate.getEvaluatedInt(0, elementNode, 'start')
		end = evaluate.getEvaluatedInt(self.sidesCeiling, elementNode, 'end')
		self.revolutions = evaluate.getEvaluatedInt(1, elementNode, 'revolutions')
		self.extent = evaluate.getEvaluatedInt(end - self.start, elementNode, 'extent')
		self.extent += self.sidesCeiling * (self.revolutions - 1)
		self.spiral = evaluate.getVector3ByPrefix(None, elementNode, 'spiral')
