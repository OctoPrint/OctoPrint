"""
Create outline.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import lineation
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities import euclidean


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


globalExecutionOrder = 80


def getManipulatedPaths(close, elementNode, loop, prefix, sideLength):
	"Get path with overhangs removed or filled in."
	if len(loop) < 4:
		return [loop]
	loopComplex = euclidean.getComplexPath(loop)
	return euclidean.getVector3Paths([euclidean.getLoopConvex(loopComplex)], loop[0].z)

def getNewDerivation(elementNode, prefix, sideLength):
	'Get new derivation.'
	return evaluate.EmptyObject()

def processElementNode(elementNode):
	"Process the xml element."
	lineation.processElementNodeByFunction(elementNode, getManipulatedPaths)
