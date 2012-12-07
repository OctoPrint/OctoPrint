"""
Create outline.

"""

from __future__ import absolute_import

from fabmetheus_utilities.geometry.creation import lineation
from fabmetheus_utilities.geometry.geometry_utilities.evaluate_elements import setting
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import intercircle


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


globalExecutionOrder = 80


def getManipulatedPaths(close, elementNode, loop, prefix, sideLength):
	"Get path with outline."
	if len(loop) < 2:
		return [loop]
	derivation = OutlineDerivation(elementNode, prefix, sideLength)
	loopComplex = euclidean.getComplexPath(loop)
	if derivation.isClosed:
		loopComplexes = intercircle.getAroundsFromLoop(loopComplex, derivation.radius)
	else:
		loopComplexes = intercircle.getAroundsFromPath(loopComplex, derivation.radius)
	return euclidean.getVector3Paths(loopComplexes, loop[0].z)

def getNewDerivation(elementNode, prefix, sideLength):
	'Get new derivation.'
	return OutlineDerivation(elementNode, prefix, sideLength)

def processElementNode(elementNode):
	"Process the xml element."
	lineation.processElementNodeByFunction(elementNode, getManipulatedPaths)


class OutlineDerivation(object):
	"Class to hold outline variables."
	def __init__(self, elementNode, prefix, sideLength):
		'Set defaults.'
		self.isClosed = evaluate.getEvaluatedBoolean(False, elementNode, prefix + 'closed')
		self.radius = evaluate.getEvaluatedFloat(setting.getEdgeWidth(elementNode), elementNode, prefix + 'radius')
