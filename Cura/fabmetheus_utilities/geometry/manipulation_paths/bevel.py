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


globalExecutionOrder = 20


def getBevelPath( begin, center, close, end, radius ):
	"Get bevel path."
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
	if radius > 0.0:
		return [ beginBevel, endBevel ]
	midpointComplex = 0.5 * ( beginBevel.dropAxis() + endBevel.dropAxis() )
	spikeComplex = centerComplex + centerComplex - midpointComplex
	return [ beginBevel, Vector3( spikeComplex.real, spikeComplex.imag, center.z ), endBevel ]

def getManipulatedPaths(close, elementNode, loop, prefix, sideLength):
	"Get bevel loop."
	if len(loop) < 3:
		return [loop]
	derivation = BevelDerivation(elementNode, prefix, sideLength)
	if derivation.radius == 0.0:
		return loop
	bevelLoop = []
	for pointIndex in xrange(len(loop)):
		begin = loop[(pointIndex + len(loop) - 1) % len(loop)]
		center = loop[pointIndex]
		end = loop[(pointIndex + 1) % len(loop)]
		bevelLoop += getBevelPath(begin, center, close, end, derivation.radius)
	return [euclidean.getLoopWithoutCloseSequentialPoints(close, bevelLoop)]

def getNewDerivation(elementNode, prefix, sideLength):
	'Get new derivation.'
	return BevelDerivation(elementNode, prefix, sideLength)

def processElementNode(elementNode):
	"Process the xml element."
	lineation.processElementNodeByFunction(elementNode, getManipulatedPaths)


class BevelDerivation:
	"Class to hold bevel variables."
	def __init__(self, elementNode, prefix, sideLength):
		'Set defaults.'
		self.radius = lineation.getFloatByPrefixSide(0.0, elementNode, prefix + 'radius', sideLength)
