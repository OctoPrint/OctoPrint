"""
Sponge slice.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import lineation
from fabmetheus_utilities.geometry.geometry_tools import path
from fabmetheus_utilities.geometry.geometry_utilities.evaluate_elements import setting
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import euclidean
import math
import random
import time


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getGeometryOutput(derivation, elementNode):
	"Get vector3 vertexes from attribute dictionary."
	if derivation == None:
		derivation = SpongeSliceDerivation(elementNode)
	awayPoints = []
	vector3Path = euclidean.getVector3Path(euclidean.getSquareLoopWiddershins(-derivation.inradius, derivation.inradius))
	geometryOutput = lineation.SideLoop(vector3Path).getManipulationPluginLoops(elementNode)
	minimumDistanceFromOther = derivation.wallThickness + derivation.minimumRadius + derivation.minimumRadius
	if derivation.inradiusMinusRadiusThickness.real <= 0.0 or derivation.inradiusMinusRadiusThickness.imag <= 0.0:
		return geometryOutput
	for point in derivation.path:
		if abs(point.x) <= derivation.inradiusMinusRadiusThickness.real and abs(point.y) <= derivation.inradiusMinusRadiusThickness.imag:
			awayPoints.append(point)
	awayCircles = []
	for point in awayPoints:
		if getIsPointAway(minimumDistanceFromOther, point, awayCircles):
			awayCircles.append(SpongeCircle(point, derivation.minimumRadius))
	averagePotentialBubbleArea = derivation.potentialBubbleArea / float(len(awayCircles))
	averageBubbleRadius = math.sqrt(averagePotentialBubbleArea / math.pi) - 0.5 * derivation.wallThickness
	sides = -4 * (max(evaluate.getSidesBasedOnPrecision(elementNode, averageBubbleRadius), 4) / 4)
	sideAngle = math.pi / sides
	cosSide = math.cos(sideAngle)
	overlapArealRatio = (1 - cosSide) / cosSide
	for circleIndex, circle in enumerate(awayCircles):
		otherCircles = awayCircles[: circleIndex] + awayCircles[circleIndex + 1 :]
		circle.radius = circle.getRadius(circle.center, derivation, otherCircles, overlapArealRatio)
	if derivation.searchAttempts > 0:
		for circleIndex, circle in enumerate(awayCircles):
			otherCircles = awayCircles[: circleIndex] + awayCircles[circleIndex + 1 :]
			circle.moveCircle(derivation, otherCircles, overlapArealRatio)
	for circle in awayCircles:
		vector3Path = euclidean.getVector3Path(euclidean.getComplexPolygon(circle.center.dropAxis(), circle.radius, sides, sideAngle))
		geometryOutput += lineation.SideLoop(vector3Path).getManipulationPluginLoops(elementNode)
	return geometryOutput

def getGeometryOutputByArguments(arguments, elementNode):
	"Get vector3 vertexes from attribute dictionary by arguments."
	return getGeometryOutput(None, elementNode)

def getIsPointAway(minimumDistance, point, spongeCircles):
	'Determine if the point is at least the minimumDistance away from other points.'
	for otherSpongeCircle in spongeCircles:
		if abs(otherSpongeCircle.center - point) < minimumDistance:
			return False
	return True

def getNewDerivation(elementNode):
	'Get new derivation.'
	return SpongeSliceDerivation(elementNode)

def processElementNode(elementNode):
	"Process the xml element."
	path.convertElementNode(elementNode, getGeometryOutput(None, elementNode))


class SpongeCircle:
	"Class to hold sponge circle."
	def __init__(self, center, radius=0.0):
		'Initialize.'
		self.center = center
		self.radius = radius

	def getRadius(self, center, derivation, otherCircles, overlapArealRatio):
		'Get sponge bubble radius.'
		radius = 987654321.0
		for otherSpongeCircle in otherCircles:
			distance = abs(otherSpongeCircle.center.dropAxis() - center.dropAxis())
			radius = min(distance - derivation.wallThickness - otherSpongeCircle.radius, radius)
		overlapAreal = overlapArealRatio * radius
		radius = min(derivation.inradiusMinusThickness.real + overlapAreal - abs(center.x), radius)
		return min(derivation.inradiusMinusThickness.imag + overlapAreal - abs(center.y), radius)

	def moveCircle(self, derivation, otherCircles, overlapArealRatio):
		'Move circle into an open spot.'
		angle = (abs(self.center) + self.radius) % euclidean.globalTau
		movedCenter = self.center
		searchRadius = derivation.searchRadiusOverRadius * self.radius
		distanceIncrement = searchRadius / float(derivation.searchAttempts)
		distance = 0.0
		greatestRadius = self.radius
		searchCircles = []
		searchCircleDistance = searchRadius + searchRadius + self.radius + derivation.wallThickness
		for otherCircle in otherCircles:
			if abs(self.center - otherCircle.center) <= searchCircleDistance + otherCircle.radius:
				searchCircles.append(otherCircle)
		for attemptIndex in xrange(derivation.searchAttempts):
			angle += euclidean.globalGoldenAngle
			distance += distanceIncrement
			offset = distance * euclidean.getWiddershinsUnitPolar(angle)
			attemptCenter = self.center + Vector3(offset.real, offset.imag)
			radius = self.getRadius(attemptCenter, derivation, searchCircles, overlapArealRatio)
			if radius > greatestRadius:
				greatestRadius = radius
				movedCenter = attemptCenter
		self.center = movedCenter
		self.radius = greatestRadius


class SpongeSliceDerivation:
	"Class to hold sponge slice variables."
	def __init__(self, elementNode):
		'Initialize.'
		elementNode.attributes['closed'] = 'true'
		self.density = evaluate.getEvaluatedFloat(1.0, elementNode, 'density')
		self.minimumRadiusOverThickness = evaluate.getEvaluatedFloat(1.0, elementNode, 'minimumRadiusOverThickness')
		self.mobile = evaluate.getEvaluatedBoolean(False, elementNode, 'mobile')
		self.inradius = lineation.getInradius(complex(10.0, 10.0), elementNode)
		self.path = None
		if 'path' in elementNode.attributes:
			self.path = evaluate.getPathByKey([], elementNode, 'path')
		self.searchAttempts = evaluate.getEvaluatedInt(0, elementNode, 'searchAttempts')
		self.searchRadiusOverRadius = evaluate.getEvaluatedFloat(1.0, elementNode, 'searchRadiusOverRadius')
		self.seed = evaluate.getEvaluatedInt(None, elementNode, 'seed')
		self.wallThickness = evaluate.getEvaluatedFloat(2.0 * setting.getEdgeWidth(elementNode), elementNode, 'wallThickness')
		# Set derived variables.
		self.halfWallThickness = 0.5 * self.wallThickness
		self.inradiusMinusThickness = self.inradius - complex(self.wallThickness, self.wallThickness)
		self.minimumRadius = evaluate.getEvaluatedFloat(self.minimumRadiusOverThickness * self.wallThickness, elementNode, 'minimumRadius')
		self.inradiusMinusRadiusThickness = self.inradiusMinusThickness - complex(self.minimumRadius, self.minimumRadius)
		self.potentialBubbleArea = 4.0 * self.inradiusMinusThickness.real * self.inradiusMinusThickness.imag
		if self.path == None:
			radiusPlusHalfThickness = self.minimumRadius + self.halfWallThickness
			numberOfPoints = int(math.ceil(self.density * self.potentialBubbleArea / math.pi / radiusPlusHalfThickness / radiusPlusHalfThickness))
			self.path = []
			if self.seed == None:
				self.seed = time.time()
				print('Sponge slice seed used was: %s' % self.seed)
			random.seed(self.seed)
			for pointIndex in xrange(numberOfPoints):
				point = euclidean.getRandomComplex(-self.inradiusMinusRadiusThickness, self.inradiusMinusRadiusThickness)
				self.path.append(Vector3(point.real, point.imag))
