"""
Teardrop path.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import extrude
from fabmetheus_utilities.geometry.creation import lineation
from fabmetheus_utilities.geometry.geometry_tools import path
from fabmetheus_utilities.geometry.geometry_utilities.evaluate_elements import setting
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import euclidean
import math


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def addNegativesByRadius(elementNode, end, negatives, radius, start):
	"Add teardrop drill hole to negatives."
	if radius <= 0.0:
		return
	copyShallow = elementNode.getCopyShallow()
	extrude.setElementNodeToEndStart(copyShallow, end, start)
	extrudeDerivation = extrude.ExtrudeDerivation(copyShallow)
	extrude.addNegatives(extrudeDerivation, negatives, [getTeardropPathByEndStart(elementNode, end, radius, start)])

def getGeometryOutput(derivation, elementNode):
	"Get vector3 vertexes from attribute dictionary."
	if derivation == None:
		derivation = TeardropDerivation(elementNode)
	teardropPath = getTeardropPath(
		derivation.inclination, derivation.overhangRadians, derivation.overhangSpan, derivation.radiusArealized, derivation.sides)
	return lineation.getGeometryOutputByLoop(elementNode, lineation.SideLoop(teardropPath))

def getGeometryOutputByArguments(arguments, elementNode):
	"Get vector3 vertexes from attribute dictionary by arguments."
	evaluate.setAttributesByArguments(['radius', 'inclination'], arguments, elementNode)
	return getGeometryOutput(None, elementNode)

def getInclination(end, start):
	"Get inclination."
	if end == None or start == None:
		return 0.0
	endMinusStart = end - start
	return math.atan2(endMinusStart.z, abs(endMinusStart.dropAxis()))

def getNewDerivation(elementNode):
	'Get new derivation.'
	return TeardropDerivation(elementNode)

def getTeardropPath(inclination, overhangRadians, overhangSpan, radiusArealized, sides):
	"Get vector3 teardrop path."
	sideAngle = 2.0 * math.pi / float(sides)
	overhangPlaneAngle = euclidean.getWiddershinsUnitPolar(overhangRadians)
	overhangRadians = math.atan2(overhangPlaneAngle.imag, overhangPlaneAngle.real * math.cos(inclination))
	tanOverhangAngle = math.tan(overhangRadians)
	beginAngle = overhangRadians
	beginMinusEndAngle = math.pi + overhangRadians + overhangRadians
	withinSides = int(math.ceil(beginMinusEndAngle / sideAngle))
	withinSideAngle = -beginMinusEndAngle / float(withinSides)
	teardropPath = []
	for side in xrange(withinSides + 1):
		unitPolar = euclidean.getWiddershinsUnitPolar(beginAngle)
		teardropPath.append(unitPolar * radiusArealized)
		beginAngle += withinSideAngle
	firstPoint = teardropPath[0]
	if overhangSpan <= 0.0:
		teardropPath.append(complex(0.0, firstPoint.imag + firstPoint.real / tanOverhangAngle))
	else:
		deltaX = (radiusArealized - firstPoint.imag) * tanOverhangAngle
		overhangPoint = complex(firstPoint.real - deltaX, radiusArealized)
		remainingDeltaX = max(0.0, overhangPoint.real - 0.5 * overhangSpan )
		overhangPoint += complex(-remainingDeltaX, remainingDeltaX / tanOverhangAngle)
		teardropPath.append(complex(-overhangPoint.real, overhangPoint.imag))
		teardropPath.append(overhangPoint)
	return euclidean.getVector3Path(teardropPath)

def getTeardropPathByEndStart(elementNode, end, radius, start):
	"Get vector3 teardrop path by end and start."
	inclination = getInclination(end, start)
	sides = evaluate.getSidesMinimumThreeBasedOnPrecisionSides(elementNode, radius)
	radiusArealized = evaluate.getRadiusArealizedBasedOnAreaRadius(elementNoderadius, sides)
	return getTeardropPath(inclination, setting.getOverhangRadians(elementNode), setting.getOverhangSpan(elementNode), radiusArealized, sides)

def processElementNode(elementNode):
	"Process the xml element."
	path.convertElementNode(elementNode, getGeometryOutput(None, elementNode))


class TeardropDerivation:
	"Class to hold teardrop variables."
	def __init__(self, elementNode):
		'Set defaults.'
		end = evaluate.getVector3ByPrefix(None, elementNode, 'end')
		start = evaluate.getVector3ByPrefix(Vector3(), elementNode, 'start')
		inclinationDegree = math.degrees(getInclination(end, start))
		self.elementNode = elementNode
		self.inclination = math.radians(evaluate.getEvaluatedFloat(inclinationDegree, elementNode, 'inclination'))
		self.overhangRadians = setting.getOverhangRadians(elementNode)
		self.overhangSpan = setting.getOverhangSpan(elementNode)
		self.radius = lineation.getFloatByPrefixBeginEnd(elementNode, 'radius', 'diameter', 1.0)
		size = evaluate.getEvaluatedFloat(None, elementNode, 'size')
		if size != None:
			self.radius = 0.5 * size
		self.sides = evaluate.getEvaluatedFloat(None, elementNode, 'sides')
		if self.sides == None:
			self.sides = evaluate.getSidesMinimumThreeBasedOnPrecisionSides(elementNode, self.radius)
		self.radiusArealized = evaluate.getRadiusArealizedBasedOnAreaRadius(elementNode, self.radius, self.sides)
