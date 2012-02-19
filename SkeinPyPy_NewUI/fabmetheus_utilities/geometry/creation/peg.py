"""
Peg.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import extrude
from fabmetheus_utilities.geometry.creation import lineation
from fabmetheus_utilities.geometry.creation import solid
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.solids import cylinder
from fabmetheus_utilities.vector3 import Vector3
import math


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'



def addPegOutput(bevel, endZ, outputs, radiusArealized, sides, start, topOverBottom):
	'Add beveled cylinder to outputs given bevel, endZ, radiusArealized and start.'
	height = abs(start.z - endZ)
	bevelStartRatio = max(1.0 - bevel / height, 0.5)
	oneMinusBevelStartRatio = 1.0 - bevelStartRatio
	trunkEndZ = bevelStartRatio * endZ + oneMinusBevelStartRatio * start.z
	trunkTopOverBottom = bevelStartRatio * topOverBottom + oneMinusBevelStartRatio
	cylinder.addCylinderOutputByEndStart(trunkEndZ, radiusArealized, outputs, sides, start, trunkTopOverBottom)
	capRadius = radiusArealized * trunkTopOverBottom
	capStart = bevelStartRatio * Vector3(start.x, start.y, endZ) + oneMinusBevelStartRatio * start
	radiusMaximum = max(radiusArealized.real, radiusArealized.imag)
	endRadiusMaximum = radiusMaximum * topOverBottom - bevel
	trunkRadiusMaximum = radiusMaximum * trunkTopOverBottom
	capTopOverBottom = endRadiusMaximum / trunkRadiusMaximum
	cylinder.addCylinderOutputByEndStart(endZ, capRadius, outputs, sides, capStart, capTopOverBottom)

def getGeometryOutput(derivation, elementNode):
	'Get vector3 vertexes from attribute dictionary.'
	if derivation == None:
		derivation = PegDerivation(elementNode)
	positives = []
	radiusArealized = complex(derivation.radiusArealized, derivation.radiusArealized)
	addPegOutput(derivation.bevel, derivation.endZ, positives, radiusArealized, derivation.sides, derivation.start, derivation.topOverBottom)
	return extrude.getGeometryOutputByNegativesPositives(elementNode, [], positives)

def getGeometryOutputByArguments(arguments, elementNode):
	'Get vector3 vertexes from attribute dictionary by arguments.'
	evaluate.setAttributesByArguments(['radius', 'endZ', 'start'], arguments, elementNode)
	return getGeometryOutput(None, elementNode)

def getNewDerivation(elementNode):
	'Get new derivation.'
	return PegDerivation(elementNode)

def getTopAddBiconicOutput(bottomRadians, height, outputs, radius, sides, start, tipRadius, topRadians):
	'Get top and add biconic cylinder to outputs.'
	radiusMaximum = max(radius.real, radius.imag)
	topRadiusMaximum = radiusMaximum - height * math.tan(bottomRadians)
	trunkEndZ = start.z + height
	trunkTopOverBottom = topRadiusMaximum / radiusMaximum
	topRadiusComplex = trunkTopOverBottom * radius
	cylinder.addCylinderOutputByEndStart(trunkEndZ, radius, outputs, sides, start, trunkTopOverBottom)
	tipOverTop = tipRadius / topRadiusMaximum
	if tipOverTop >= 1.0:
		return trunkEndZ
	capStart = Vector3(start.x, start.y, trunkEndZ)
	capEndZ = trunkEndZ + (topRadiusMaximum - tipRadius) / math.tan(topRadians)
	cylinder.addCylinderOutputByEndStart(capEndZ, topRadiusComplex, outputs, sides, capStart, tipOverTop)
	return capEndZ

def processElementNode(elementNode):
	'Process the xml element.'
	solid.processElementNodeByGeometry(elementNode, getGeometryOutput(None, elementNode))

def setTopOverBottomByRadius(derivation, endZ, radius, startZ):
	'Set the derivation topOverBottom by the angle of the elementNode, the endZ, float radius and startZ.'
	angleDegrees = evaluate.getEvaluatedFloat(None, derivation.elementNode, 'angle')
	if angleDegrees != None:
		derivation.topOverBottom = cylinder.getTopOverBottom(math.radians(angleDegrees), endZ, complex(radius, radius), startZ)


class PegDerivation:
	'Class to hold peg variables.'
	def __init__(self, elementNode):
		'Set defaults.'
		self.bevelOverRadius = evaluate.getEvaluatedFloat(0.25, elementNode, 'bevelOverRadius')
		self.clearanceOverRadius = evaluate.getEvaluatedFloat(0.0, elementNode, 'clearanceOverRadius')
		self.elementNode = elementNode
		self.endZ = evaluate.getEvaluatedFloat(10.0, elementNode, 'endZ')
		self.start = evaluate.getVector3ByPrefix(Vector3(), elementNode, 'start')
		self.radius = lineation.getFloatByPrefixBeginEnd(elementNode, 'radius', 'diameter', 2.0)
		self.sides = evaluate.getSidesMinimumThreeBasedOnPrecision(elementNode, max(self.radius.real, self.radius.imag))
		self.radiusArealized = evaluate.getRadiusArealizedBasedOnAreaRadius(elementNode, self.radius, self.sides)
		self.topOverBottom = evaluate.getEvaluatedFloat(0.8, elementNode, 'topOverBottom')
		setTopOverBottomByRadius(self, self.endZ, self.radiusArealized, self.start.z)
		# Set derived variables.
		self.bevel = evaluate.getEvaluatedFloat(self.bevelOverRadius * self.radiusArealized, elementNode, 'bevel')
		self.clearance = evaluate.getEvaluatedFloat(self.clearanceOverRadius * self.radiusArealized, elementNode, 'clearance')
