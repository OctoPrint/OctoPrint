"""
Linear bearing cage.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import extrude
from fabmetheus_utilities.geometry.creation import lineation
from fabmetheus_utilities.geometry.creation import peg
from fabmetheus_utilities.geometry.creation import solid
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.geometry_utilities import matrix
from fabmetheus_utilities.geometry.manipulation_matrix import translate
from fabmetheus_utilities.geometry.solids import cylinder
from fabmetheus_utilities.geometry.solids import sphere
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import euclidean
import math


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def addAssemblyCage(derivation, negatives, positives):
	'Add assembly linear bearing cage.'
	addCageGroove(derivation, negatives, positives)
	for pegCenterX in derivation.pegCenterXs:
		addPositivePeg(derivation, positives, pegCenterX, -derivation.pegY)
		addPositivePeg(derivation, positives, pegCenterX, derivation.pegY)
	translate.translateNegativesPositives(negatives, positives, Vector3(0.0, -derivation.halfSeparationWidth))
	femaleNegatives = []
	femalePositives = []
	addCageGroove(derivation, femaleNegatives, femalePositives)
	for pegCenterX in derivation.pegCenterXs:
		addNegativePeg(derivation, femaleNegatives, pegCenterX, -derivation.pegY)
		addNegativePeg(derivation, femaleNegatives, pegCenterX, derivation.pegY)
	translate.translateNegativesPositives(femaleNegatives, femalePositives, Vector3(0.0, derivation.halfSeparationWidth))
	negatives += femaleNegatives
	positives += femalePositives

def addCage(derivation, height, negatives, positives):
	'Add linear bearing cage.'
	copyShallow = derivation.elementNode.getCopyShallow()
	copyShallow.attributes['path'] = [Vector3(), Vector3(0.0, 0.0, height)]
	extrudeDerivation = extrude.ExtrudeDerivation(copyShallow)
	roundedExtendedRectangle = getRoundedExtendedRectangle(derivation.demiwidth, derivation.rectangleCenterX, 14)
	outsidePath = euclidean.getVector3Path(roundedExtendedRectangle)
	extrude.addPositives(extrudeDerivation, [outsidePath], positives)
	for bearingCenterX in derivation.bearingCenterXs:
		addNegativeSphere(derivation, negatives, bearingCenterX)

def addCageGroove(derivation, negatives, positives):
	'Add cage and groove.'
	addCage(derivation, derivation.demiheight, negatives, positives)
	addGroove(derivation, negatives)

def addGroove(derivation, negatives):
	'Add groove on each side of cage.'
	copyShallow = derivation.elementNode.getCopyShallow()
	extrude.setElementNodeToEndStart(copyShallow, Vector3(-derivation.demilength), Vector3(derivation.demilength))
	extrudeDerivation = extrude.ExtrudeDerivation(copyShallow)
	bottom = derivation.demiheight - 0.5 * derivation.grooveWidth
	outside = derivation.demiwidth
	top = derivation.demiheight
	leftGroove = [
		complex(-outside, bottom),
		complex(-derivation.innerDemiwidth, derivation.demiheight),
		complex(-outside, top)]
	rightGroove = [
		complex(outside, top),
		complex(derivation.innerDemiwidth, derivation.demiheight),
		complex(outside, bottom)]
	extrude.addNegatives(extrudeDerivation, negatives, euclidean.getVector3Paths([leftGroove, rightGroove]))

def addNegativePeg(derivation, negatives, x, y):
	'Add negative cylinder at x and y.'
	negativePegRadius = derivation.pegRadiusArealized + derivation.halfPegClearance
	inradius = complex(negativePegRadius, negativePegRadius)
	copyShallow = derivation.elementNode.getCopyShallow()
	start = Vector3(x, y, derivation.height)
	sides = evaluate.getSidesMinimumThreeBasedOnPrecision(copyShallow, negativePegRadius)
	cylinder.addCylinderOutputByEndStart(0.0, inradius, negatives, sides, start, derivation.topOverBottom)

def addNegativeSphere(derivation, negatives, x):
	'Add negative sphere at x.'
	radius = Vector3(derivation.radiusPlusClearance, derivation.radiusPlusClearance, derivation.radiusPlusClearance)
	sphereOutput = sphere.getGeometryOutput(derivation.elementNode.getCopyShallow(), radius)
	euclidean.translateVector3Path(matrix.getVertexes(sphereOutput), Vector3(x, 0.0, derivation.demiheight))
	negatives.append(sphereOutput)

def addPositivePeg(derivation, positives, x, y):
	'Add positive cylinder at x and y.'
	positivePegRadius = derivation.pegRadiusArealized - derivation.halfPegClearance
	radiusArealized = complex(positivePegRadius, positivePegRadius)
	copyShallow = derivation.elementNode.getCopyShallow()
	start = Vector3(x, y, derivation.demiheight)
	endZ = derivation.height
	peg.addPegOutput(derivation.pegBevel, endZ, positives, radiusArealized, derivation.sides, start, derivation.topOverBottom)

def getBearingCenterXs(bearingCenterX, numberOfSteps, stepX):
	'Get the bearing center x list.'
	bearingCenterXs = []
	for stepIndex in xrange(numberOfSteps + 1):
		bearingCenterXs.append(bearingCenterX)
		bearingCenterX += stepX
	return bearingCenterXs

def getGeometryOutput(elementNode):
	'Get vector3 vertexes from attribute dictionary.'
	derivation = LinearBearingCageDerivation(elementNode)
	negatives = []
	positives = []
	if derivation.typeStringFirstCharacter == 'a':
		addAssemblyCage(derivation, negatives, positives)
	else:
		addCage(derivation, derivation.height, negatives, positives)
	return extrude.getGeometryOutputByNegativesPositives(elementNode, negatives, positives)

def getGeometryOutputByArguments(arguments, elementNode):
	'Get vector3 vertexes from attribute dictionary by arguments.'
	evaluate.setAttributesByArguments(['length', 'radius'], arguments, elementNode)
	return getGeometryOutput(elementNode)

def getNewDerivation(elementNode):
	'Get new derivation.'
	return LinearBearingCageDerivation(elementNode)

def getPegCenterXs(numberOfSteps, pegCenterX, stepX):
	'Get the peg center x list.'
	pegCenterXs = []
	for stepIndex in xrange(numberOfSteps):
		pegCenterXs.append(pegCenterX)
		pegCenterX += stepX
	return pegCenterXs

def getRoundedExtendedRectangle(radius, rectangleCenterX, sides):
	'Get the rounded extended rectangle.'
	roundedExtendedRectangle = []
	halfSides = int(sides / 2)
	halfSidesPlusOne = abs(halfSides + 1)
	sideAngle = math.pi / float(halfSides)
	extensionMultiplier = 1.0 / math.cos(0.5 * sideAngle)
	center = complex(rectangleCenterX, 0.0)
	startAngle = 0.5 * math.pi
	for halfSide in xrange(halfSidesPlusOne):
		unitPolar = euclidean.getWiddershinsUnitPolar(startAngle)
		unitPolarExtended = complex(unitPolar.real * extensionMultiplier, unitPolar.imag)
		roundedExtendedRectangle.append(unitPolarExtended * radius + center)
		startAngle += sideAngle
	center = complex(-rectangleCenterX, 0.0)
	startAngle = -0.5 * math.pi
	for halfSide in xrange(halfSidesPlusOne):
		unitPolar = euclidean.getWiddershinsUnitPolar(startAngle)
		unitPolarExtended = complex(unitPolar.real * extensionMultiplier, unitPolar.imag)
		roundedExtendedRectangle.append(unitPolarExtended * radius + center)
		startAngle += sideAngle
	return roundedExtendedRectangle

def processElementNode(elementNode):
	'Process the xml element.'
	solid.processElementNodeByGeometry(elementNode, getGeometryOutput(elementNode))


class LinearBearingCageDerivation:
	'Class to hold linear bearing cage variables.'
	def __init__(self, elementNode):
		'Set defaults.'
		self.length = evaluate.getEvaluatedFloat(50.0, elementNode, 'length')
		self.demilength = 0.5 * self.length
		self.elementNode = elementNode
		self.radius = lineation.getFloatByPrefixBeginEnd(elementNode, 'radius', 'diameter', 5.0)
		self.cageClearanceOverRadius = evaluate.getEvaluatedFloat(0.05, elementNode, 'cageClearanceOverRadius')
		self.cageClearance = self.cageClearanceOverRadius * self.radius
		self.cageClearance = evaluate.getEvaluatedFloat(self.cageClearance, elementNode, 'cageClearance')
		self.racewayClearanceOverRadius = evaluate.getEvaluatedFloat(0.1, elementNode, 'racewayClearanceOverRadius')
		self.racewayClearance = self.racewayClearanceOverRadius * self.radius
		self.racewayClearance = evaluate.getEvaluatedFloat(self.racewayClearance, elementNode, 'racewayClearance')
		self.typeMenuRadioStrings = 'assembly integral'.split()
		self.typeString = evaluate.getEvaluatedString('assembly', elementNode, 'type')
		self.typeStringFirstCharacter = self.typeString[: 1 ].lower()
		self.wallThicknessOverRadius = evaluate.getEvaluatedFloat(0.5, elementNode, 'wallThicknessOverRadius')
		self.wallThickness = self.wallThicknessOverRadius * self.radius
		self.wallThickness = evaluate.getEvaluatedFloat(self.wallThickness, elementNode, 'wallThickness')
		self.zenithAngle = evaluate.getEvaluatedFloat(45.0, elementNode, 'zenithAngle')
		self.zenithRadian = math.radians(self.zenithAngle)
		self.demiheight = self.radius * math.cos(self.zenithRadian) - self.racewayClearance
		self.height = self.demiheight + self.demiheight
		self.radiusPlusClearance = self.radius + self.cageClearance
		self.cageRadius = self.radiusPlusClearance + self.wallThickness
		self.demiwidth = self.cageRadius
		self.bearingCenterX = self.cageRadius - self.demilength
		separation = self.cageRadius + self.radiusPlusClearance
		bearingLength = -self.bearingCenterX - self.bearingCenterX
		self.numberOfSteps = int(math.floor(bearingLength / separation))
		self.stepX = bearingLength / float(self.numberOfSteps)
		self.bearingCenterXs = getBearingCenterXs(self.bearingCenterX, self.numberOfSteps, self.stepX)
		if self.typeStringFirstCharacter == 'a':
			self.setAssemblyCage()
		self.rectangleCenterX = self.demiwidth - self.demilength

	def setAssemblyCage(self):
		'Set two piece assembly parameters.'
		self.grooveDepthOverRadius = evaluate.getEvaluatedFloat(0.15, self.elementNode, 'grooveDepthOverRadius')
		self.grooveDepth = self.grooveDepthOverRadius * self.radius
		self.grooveDepth = evaluate.getEvaluatedFloat(self.grooveDepth, self.elementNode, 'grooveDepth')
		self.grooveWidthOverRadius = evaluate.getEvaluatedFloat(0.6, self.elementNode, 'grooveWidthOverRadius')
		self.grooveWidth = self.grooveWidthOverRadius * self.radius
		self.grooveWidth = evaluate.getEvaluatedFloat(self.grooveWidth, self.elementNode, 'grooveWidth')
		self.pegClearanceOverRadius = evaluate.getEvaluatedFloat(0.0, self.elementNode, 'pegClearanceOverRadius')
		self.pegClearance = self.pegClearanceOverRadius * self.radius
		self.pegClearance = evaluate.getEvaluatedFloat(self.pegClearance, self.elementNode, 'pegClearance')
		self.halfPegClearance = 0.5 * self.pegClearance
		self.pegRadiusOverRadius = evaluate.getEvaluatedFloat(0.5, self.elementNode, 'pegRadiusOverRadius')
		self.pegRadius = self.pegRadiusOverRadius * self.radius
		self.pegRadius = evaluate.getEvaluatedFloat(self.pegRadius, self.elementNode, 'pegRadius')
		self.sides = evaluate.getSidesMinimumThreeBasedOnPrecision(self.elementNode, self.pegRadius)
		self.pegRadiusArealized = evaluate.getRadiusArealizedBasedOnAreaRadius(self.elementNode, self.pegRadius, self.sides)
		self.pegBevelOverPegRadius = evaluate.getEvaluatedFloat(0.25, self.elementNode, 'pegBevelOverPegRadius')
		self.pegBevel = self.pegBevelOverPegRadius * self.pegRadiusArealized
		self.pegBevel = evaluate.getEvaluatedFloat(self.pegBevel, self.elementNode, 'pegBevel')
		self.pegMaximumRadius = self.pegRadiusArealized + abs(self.halfPegClearance)
		self.separationOverRadius = evaluate.getEvaluatedFloat(0.5, self.elementNode, 'separationOverRadius')
		self.separation = self.separationOverRadius * self.radius
		self.separation = evaluate.getEvaluatedFloat(self.separation, self.elementNode, 'separation')
		self.topOverBottom = evaluate.getEvaluatedFloat(0.8, self.elementNode, 'topOverBottom')
		peg.setTopOverBottomByRadius(self, 0.0, self.pegRadiusArealized, self.height)
		self.quarterHeight = 0.5 * self.demiheight
		self.pegY = 0.5 * self.wallThickness + self.pegMaximumRadius
		cagePegRadius = self.cageRadius + self.pegMaximumRadius
		halfStepX = 0.5 * self.stepX
		pegHypotenuse = math.sqrt(self.pegY * self.pegY + halfStepX * halfStepX)
		if cagePegRadius > pegHypotenuse:
			self.pegY = math.sqrt(cagePegRadius * cagePegRadius - halfStepX * halfStepX)
		self.demiwidth = max(self.pegY + self.pegMaximumRadius + self.wallThickness, self.demiwidth)
		self.innerDemiwidth = self.demiwidth
		self.demiwidth += self.grooveDepth
		self.halfSeparationWidth = self.demiwidth + 0.5 * self.separation
		if self.pegRadiusArealized <= 0.0:
			self.pegCenterXs = []
		else:
			self.pegCenterXs = getPegCenterXs(self.numberOfSteps, self.bearingCenterX + halfStepX, self.stepX)
