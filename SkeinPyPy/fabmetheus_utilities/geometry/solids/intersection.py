"""
Boolean geometry intersection of solids.

"""


from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.solids import difference
from fabmetheus_utilities.geometry.solids import group


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Nophead <http://hydraraptor.blogspot.com/>\nArt of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def convertElementNode(elementNode, geometryOutput):
	"Convert the xml element to an intersection xml element."
	group.convertContainerElementNode(elementNode, geometryOutput, Intersection())

def getNewDerivation(elementNode):
	'Get new derivation.'
	return evaluate.EmptyObject(elementNode)

def processElementNode(elementNode):
	"Process the xml element."
	evaluate.processArchivable(Intersection, elementNode)


class Intersection(difference.Difference):
	"An intersection object."
	def getLoopsFromObjectLoopsList(self, importRadius, visibleObjectLoopsList):
		"Get loops from visible object loops list."
		return self.getIntersection(importRadius, visibleObjectLoopsList)
