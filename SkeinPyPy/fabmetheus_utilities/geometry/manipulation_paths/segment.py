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

__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


globalExecutionOrder = 60


def getManipulatedPaths(close, elementNode, loop, prefix, sideLength):
	"Get segment loop."
	if len(loop) < 3:
		return [loop]
	derivation = SegmentDerivation(elementNode, prefix)
	if derivation.path == getSegmentPathDefault():
		return [loop]
	path = getXNormalizedVector3Path(derivation.path)
	if euclidean.getIsWiddershinsByVector3(loop):
		path = path[: : -1]
		for point in path:
			point.x = 1.0 - point.x
			if derivation.center == None:
				point.y = - point.y
	segmentLoop = []
	startEnd = StartEnd(elementNode, len(loop), prefix)
	for pointIndex in xrange(len(loop)):
		if pointIndex >= startEnd.start and pointIndex < startEnd.end:
			segmentLoop += getSegmentPath(derivation.center, loop, path, pointIndex)
		else:
			segmentLoop.append(loop[pointIndex])
	return [euclidean.getLoopWithoutCloseSequentialPoints( close, segmentLoop)]

def getNewDerivation(elementNode, prefix, sideLength):
	'Get new derivation.'
	return SegmentDerivation(elementNode, prefix)

def getRadialPath(begin, center, end, path):
	"Get radial path."
	beginComplex = begin.dropAxis()
	endComplex = end.dropAxis()
	centerComplex = center.dropAxis()
	beginMinusCenterComplex = beginComplex - centerComplex
	endMinusCenterComplex = endComplex - centerComplex
	beginMinusCenterComplexRadius = abs( beginMinusCenterComplex )
	endMinusCenterComplexRadius = abs( endMinusCenterComplex )
	if beginMinusCenterComplexRadius == 0.0 or endMinusCenterComplexRadius == 0.0:
		return [ begin ]
	beginMinusCenterComplex /= beginMinusCenterComplexRadius
	endMinusCenterComplex /= endMinusCenterComplexRadius
	angleDifference = euclidean.getAngleDifferenceByComplex( endMinusCenterComplex, beginMinusCenterComplex )
	radialPath = []
	for point in path:
		weightEnd = point.x
		weightBegin = 1.0 - weightEnd
		weightedRadius = beginMinusCenterComplexRadius * weightBegin + endMinusCenterComplexRadius * weightEnd * ( 1.0 + point.y )
		radialComplex = weightedRadius * euclidean.getWiddershinsUnitPolar( angleDifference * point.x ) * beginMinusCenterComplex
		polygonPoint = center + Vector3( radialComplex.real, radialComplex.imag, point.z )
		radialPath.append( polygonPoint )
	return radialPath

def getSegmentPath(center, loop, path, pointIndex):
	"Get segment path."
	centerBegin = loop[pointIndex]
	centerEnd = loop[(pointIndex + 1) % len(loop)]
	centerEndMinusBegin = centerEnd - centerBegin
	if abs( centerEndMinusBegin ) <= 0.0:
		return [ centerBegin ]
	if center != None:
		return getRadialPath(centerBegin, center, centerEnd, path)
	begin = loop[(pointIndex + len(loop) - 1) % len(loop)]
	end = loop[(pointIndex + 2) % len(loop)]
	return getWedgePath(begin, centerBegin, centerEnd, centerEndMinusBegin, end, path)

def getSegmentPathDefault():
	"Get segment path default."
	return [Vector3(), Vector3(0.0, 1.0)]

def getWedgePath( begin, centerBegin, centerEnd, centerEndMinusBegin, end, path ):
	"Get segment path."
	beginComplex = begin.dropAxis()
	centerBeginComplex = centerBegin.dropAxis()
	centerEndComplex = centerEnd.dropAxis()
	endComplex = end.dropAxis()
	wedgePath = []
	centerBeginMinusBeginComplex = euclidean.getNormalized( centerBeginComplex - beginComplex )
	centerEndMinusCenterBeginComplexOriginal = centerEndComplex - centerBeginComplex
	centerEndMinusCenterBeginComplexLength = abs( centerEndMinusCenterBeginComplexOriginal )
	if centerEndMinusCenterBeginComplexLength <= 0.0:
		return [ centerBegin ]
	centerEndMinusCenterBeginComplex = centerEndMinusCenterBeginComplexOriginal / centerEndMinusCenterBeginComplexLength
	endMinusCenterEndComplex = euclidean.getNormalized( endComplex - centerEndComplex )
	widdershinsBegin = getWiddershinsAverageByVector3( centerBeginMinusBeginComplex, centerEndMinusCenterBeginComplex )
	widdershinsEnd = getWiddershinsAverageByVector3( centerEndMinusCenterBeginComplex, endMinusCenterEndComplex )
	for point in path:
		weightEnd = point.x
		weightBegin = 1.0 - weightEnd
		polygonPoint = centerBegin + centerEndMinusBegin * point.x
		weightedWiddershins = widdershinsBegin * weightBegin + widdershinsEnd * weightEnd
		polygonPoint += weightedWiddershins * point.y * centerEndMinusCenterBeginComplexLength
		polygonPoint.z += point.z
		wedgePath.append( polygonPoint )
	return wedgePath

def getWiddershinsAverageByVector3( centerMinusBeginComplex, endMinusCenterComplex ):
	"Get the normalized average of the widdershins vectors."
	centerMinusBeginWiddershins = Vector3( - centerMinusBeginComplex.imag, centerMinusBeginComplex.real )
	endMinusCenterWiddershins = Vector3( - endMinusCenterComplex.imag, endMinusCenterComplex.real )
	return ( centerMinusBeginWiddershins + endMinusCenterWiddershins ).getNormalized()

def getXNormalizedVector3Path(path):
	"Get path where the x ranges from 0 to 1."
	if len(path) < 1:
		return path
	minimumX = path[0].x
	for point in path[1 :]:
		minimumX = min( minimumX, point.x )
	for point in path:
		point.x -= minimumX
	maximumX = path[0].x
	for point in path[1 :]:
		maximumX = max( maximumX, point.x )
	for point in path:
		point.x /= maximumX
	return path

def processElementNode(elementNode):
	"Process the xml element."
	lineation.processElementNodeByFunction(elementNode, getManipulatedPaths)


class SegmentDerivation:
	"Class to hold segment variables."
	def __init__(self, elementNode, prefix):
		'Set defaults.'
		self.center = evaluate.getVector3ByPrefix(None, elementNode, prefix + 'center')
		self.path = evaluate.getPathByPrefix(elementNode, getSegmentPathDefault(), prefix)


class StartEnd:
	'Class to get a start through end range.'
	def __init__(self, elementNode, modulo, prefix):
		"Initialize."
		self.start = evaluate.getEvaluatedInt(0, elementNode, prefix + 'start')
		self.extent = evaluate.getEvaluatedInt(modulo - self.start, elementNode, prefix + 'extent')
		self.end = evaluate.getEvaluatedInt(self.start + self.extent, elementNode, prefix + 'end')
		self.revolutions = evaluate.getEvaluatedInt(1, elementNode, prefix + 'revolutions')
		if self.revolutions > 1:
			self.end += modulo * (self.revolutions - 1)

	def __repr__(self):
		"Get the string representation of this StartEnd."
		return '%s, %s, %s' % (self.start, self.end, self.revolutions)
