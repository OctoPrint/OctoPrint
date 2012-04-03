"""
Cubic vertexes.

From:
http://www.w3.org/TR/SVG/paths.html#PathDataCubicBezierCommands

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


def getCubicPath(elementNode):
	"Get the cubic path."
	end = evaluate.getVector3FromElementNode(elementNode)
	previousElementNode = elementNode.getPreviousElementNode()
	if previousElementNode == None:
		print('Warning, can not get previousElementNode in getCubicPath in cubic for:')
		print(elementNode)
		return [end]
	begin = elementNode.getPreviousVertex(Vector3())
	evaluatedControlPoints = evaluate.getTransformedPathByKey([], elementNode, 'controlPoints')
	if len(evaluatedControlPoints) > 1:
		return getCubicPathByBeginEnd(begin, evaluatedControlPoints, elementNode, end)
	controlPoint0 = evaluate.getVector3ByPrefix(None, elementNode, 'controlPoint0')
	controlPoint1 = evaluate.getVector3ByPrefix(None, elementNode, 'controlPoint1')
	if len(evaluatedControlPoints) == 1:
		controlPoint1 = evaluatedControlPoints[0]
	if controlPoint0 == None:
		oldControlPoint = evaluate.getVector3ByPrefixes(previousElementNode, ['controlPoint','controlPoint1'], None)
		if oldControlPoint == None:
			oldControlPoints = evaluate.getTransformedPathByKey([], previousElementNode, 'controlPoints')
			if len(oldControlPoints) > 0:
				oldControlPoint = oldControlPoints[-1]
		if oldControlPoint == None:
			oldControlPoint = end
		controlPoint0 = begin + begin - oldControlPoint
	return getCubicPathByBeginEnd(begin, [controlPoint0, controlPoint1], elementNode, end)

def getCubicPathByBeginEnd(begin, controlPoints, elementNode, end):
	"Get the cubic path by begin and end."
	return svg_reader.getCubicPoints(begin, controlPoints, end, lineation.getNumberOfBezierPoints(begin, elementNode, end))

def processElementNode(elementNode):
	"Process the xml element."
	elementNode.parentNode.xmlObject.vertexes += getCubicPath(elementNode)
