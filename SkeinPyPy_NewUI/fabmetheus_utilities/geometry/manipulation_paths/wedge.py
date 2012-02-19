"""
Add material to support overhang or remove material at the overhang angle.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import lineation
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.vector3 import Vector3


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


globalExecutionOrder = -200


def getManipulatedPaths(close, elementNode, loop, prefix, sideLength):
	"Get wedge loop."
	derivation = WedgeDerivation(elementNode, prefix)
	loop.append(derivation.center)
	return [loop]

def getNewDerivation(elementNode, prefix, sideLength):
	'Get new derivation.'
	return WedgeDerivation(elementNode, prefix)

def processElementNode(elementNode):
	"Process the xml element."
	lineation.processElementNodeByFunction(elementNode, getManipulatedPaths)


class WedgeDerivation:
	"Class to hold wedge variables."
	def __init__(self, elementNode, prefix):
		'Set defaults.'
		self.center = evaluate.getVector3ByPrefix(Vector3(), elementNode, prefix + 'center')
