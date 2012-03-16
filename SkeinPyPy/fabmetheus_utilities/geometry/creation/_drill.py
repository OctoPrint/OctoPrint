"""
Drill negative solid.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import extrude
from fabmetheus_utilities.geometry.creation import lineation
from fabmetheus_utilities.geometry.creation import solid
from fabmetheus_utilities.geometry.creation import teardrop
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.solids import triangle_mesh
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import euclidean
import math


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getGeometryOutput(derivation, elementNode):
	"Get vector3 vertexes from attribute dictionary."
	if derivation == None:
		derivation = DrillDerivation(elementNode)
	negatives = []
	teardrop.addNegativesByRadius(elementNode, derivation.end, negatives, derivation.radius, derivation.start)
	return solid.getGeometryOutputByManipulation(elementNode, negatives[0])

def getGeometryOutputByArguments(arguments, elementNode):
	"Get vector3 vertexes from attribute dictionary by arguments."
	evaluate.setAttributesByArguments(['radius', 'start', 'end'], arguments, elementNode)
	return getGeometryOutput(None, elementNode)

def getNewDerivation(elementNode):
	'Get new derivation.'
	return DrillDerivation(elementNode)

def processElementNode(elementNode):
	"Process the xml element."
	solid.processElementNodeByGeometry(elementNode, getGeometryOutput(None, elementNode))


class DrillDerivation:
	"Class to hold drill variables."
	def __init__(self, elementNode):
		'Set defaults.'
		self.elementNode = elementNode
		self.end = evaluate.getVector3ByPrefix(Vector3(0.0, 0.0, 1.0), elementNode, 'end')
		self.start = evaluate.getVector3ByPrefix(Vector3(), elementNode, 'start')
		self.radius = lineation.getFloatByPrefixBeginEnd(elementNode, 'radius', 'diameter', 1.0)
		size = evaluate.getEvaluatedFloat(None, elementNode, 'size')
		if size != None:
			self.radius = 0.5 * size
