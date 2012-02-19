"""
Boolean geometry concatenation.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import lineation
from fabmetheus_utilities.geometry.geometry_tools import path
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import euclidean
import math


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getGeometryOutput(derivation, elementNode):
	'Get triangle mesh from attribute dictionary.'
	if derivation == None:
		derivation = ConcatenateDerivation(elementNode)
	concatenatedList = euclidean.getConcatenatedList(derivation.target)[:]
	if len(concatenatedList) == 0:
		print('Warning, in concatenate there are no paths.')
		print(elementNode.attributes)
		return None
	if 'closed' not in elementNode.attributes:
		elementNode.attributes['closed'] = 'true'
	return lineation.getGeometryOutputByLoop(elementNode, lineation.SideLoop(concatenatedList))

def getGeometryOutputByArguments(arguments, elementNode):
	'Get triangle mesh from attribute dictionary by arguments.'
	return getGeometryOutput(None, elementNode)

def getNewDerivation(elementNode):
	'Get new derivation.'
	return ConcatenateDerivation(elementNode)

def processElementNode(elementNode):
	'Process the xml element.'
	path.convertElementNode(elementNode, getGeometryOutput(None, elementNode))


class ConcatenateDerivation:
	'Class to hold concatenate variables.'
	def __init__(self, elementNode):
		'Initialize.'
		self.target = evaluate.getTransformedPathsByKey([], elementNode, 'target')
