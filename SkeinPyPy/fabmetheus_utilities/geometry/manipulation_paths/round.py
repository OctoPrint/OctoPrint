"""
Add material to support overhang or remove material at the overhang angle.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import lineation
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import euclidean
import math


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


globalExecutionOrder = 40


def getManipulatedPaths(close, elementNode, loop, prefix, sideLength):
	"Get round loop."
	if len(loop) < 3:
		return [loop]
	derivation = RoundDerivation(elementNode, prefix, sideLength)
	if derivation.radius == 0.0:
		return loop
	roundLoop = []
	sidesPerRadian = 0.5 / math.pi * evaluate.getSidesMinimumThreeBasedOnPrecision(elementNode, sideLength)
	for pointIndex in xrange(len(loop)):
		begin = loop[(pointIndex + len(loop) - 1) % len(loop)]
		center = loop[pointIndex]
		end = loop[(pointIndex + 1) % len(loop)]
		roundLoop += getRoundPath(begin, center, close, end, derivation.radius, sidesPerRadian)
	return [euclidean.getLoopWithoutCloseSequentialPoints(close, roundLoop)]

def getNewDerivation(elementNode, prefix, sideLength):
	'Get new derivation.'
	return RoundDerivation(elementNode, prefix, sideLength)

def getRoundPath( begin, center, close, end, radius, sidesPerRadian ):
	"Get round path."
	beginComplex = begin.dropAxis()
	centerComplex = center.dropAxis()
	endComplex = end.dropAxis()
	beginComplexSegmentLength = abs( centerComplex - beginComplex )
	endComplexSegmentLength = abs( centerComplex - endComplex )
	minimumRadius = lineation.getMinimumRadius( beginComplexSegmentLength, endComplexSegmentLength, radius )
	if minimumRadius <= close:
		return [ center ]
	beginBevel = center + minimumRadius / beginComplexSegmentLength * ( begin - center )
	endBevel = center + minimumRadius / endComplexSegmentLength * ( end - center )
	beginBevelComplex = beginBevel.dropAxis()
	endBevelComplex = endBevel.dropAxis()
	midpointComplex = 0.5 * ( beginBevelComplex + endBevelComplex )
	if radius < 0.0:
		centerComplex = midpointComplex + midpointComplex - centerComplex
	midpointMinusCenterComplex = midpointComplex - centerComplex
	midpointCenterLength = abs( midpointMinusCenterComplex )
	midpointEndLength = abs( midpointComplex - endBevelComplex )
	midpointCircleCenterLength = midpointEndLength * midpointEndLength / midpointCenterLength
	circleRadius = math.sqrt( midpointCircleCenterLength * midpointCircleCenterLength + midpointEndLength * midpointEndLength )
	circleCenterComplex = midpointComplex + midpointMinusCenterComplex * midpointCircleCenterLength / midpointCenterLength
	circleCenter = Vector3( circleCenterComplex.real, circleCenterComplex.imag, center.z )
	endMinusCircleCenterComplex = endBevelComplex - circleCenterComplex
	beginMinusCircleCenter = beginBevel - circleCenter
	beginMinusCircleCenterComplex = beginMinusCircleCenter.dropAxis()
	angleDifference = euclidean.getAngleDifferenceByComplex( endMinusCircleCenterComplex, beginMinusCircleCenterComplex )
	steps = int( math.ceil( abs( angleDifference ) * sidesPerRadian ) )
	stepPlaneAngle = euclidean.getWiddershinsUnitPolar( angleDifference / float( steps ) )
	deltaZStep = ( end.z - begin.z ) / float( steps )
	roundPath = [ beginBevel ]
	for step in xrange( 1, steps ):
		beginMinusCircleCenterComplex = beginMinusCircleCenterComplex * stepPlaneAngle
		arcPointComplex = circleCenterComplex + beginMinusCircleCenterComplex
		arcPoint = Vector3( arcPointComplex.real, arcPointComplex.imag, begin.z + deltaZStep * step )
		roundPath.append( arcPoint )
	return roundPath + [ endBevel ]

def processElementNode(elementNode):
	"Process the xml element."
	lineation.processElementNodeByFunction(elementNode, getManipulatedPaths)


class RoundDerivation:
	"Class to hold round variables."
	def __init__(self, elementNode, prefix, sideLength):
		'Set defaults.'
		self.radius = lineation.getFloatByPrefixSide(0.0, elementNode, prefix + 'radius', sideLength)
