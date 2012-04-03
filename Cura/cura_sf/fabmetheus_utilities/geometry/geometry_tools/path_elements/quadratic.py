"""
Quadratic vertexes.

From:
http://www.w3.org/TR/SVG/paths.html#PathDataQuadraticBezierCommands

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import lineation
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import svg_reader


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getQuadraticPath(elementNode):
	"Get the quadratic path."
	end = evaluate.getVector3FromElementNode(elementNode)
	previousElementNode = elementNode.getPreviousElementNode()
	if previousElementNode == None:
		print('Warning, can not get previousElementNode in getQuadraticPath in quadratic for:')
		print(elementNode)
		return [end]
	begin = elementNode.getPreviousVertex(Vector3())
	controlPoint = evaluate.getVector3ByPrefix(None, elementNode, 'controlPoint')
	if controlPoint == None:
		oldControlPoint = evaluate.getVector3ByPrefixes(previousElementNode, ['controlPoint','controlPoint1'], None)
		if oldControlPoint == None:
			oldControlPoint = end
		controlPoint = begin + begin - oldControlPoint
		evaluate.addVector3ToElementNode(elementNode, 'controlPoint', controlPoint)
	return svg_reader.getQuadraticPoints(begin, controlPoint, end, lineation.getNumberOfBezierPoints(begin, elementNode, end))

def processElementNode(elementNode):
	"Process the xml element."
	elementNode.parentNode.xmlObject.vertexes += getQuadraticPath(elementNode)
