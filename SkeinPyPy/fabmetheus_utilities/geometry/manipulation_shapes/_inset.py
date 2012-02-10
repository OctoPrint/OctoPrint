"""
Create inset.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import lineation
from fabmetheus_utilities.geometry.creation import solid
from fabmetheus_utilities.geometry.geometry_utilities.evaluate_elements import setting
from fabmetheus_utilities.geometry.geometry_utilities import boolean_solid
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.geometry_utilities import matrix
from fabmetheus_utilities.geometry.solids import triangle_mesh
from fabmetheus_utilities.vector3index import Vector3Index
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import intercircle
import math


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


globalExecutionOrder = 80


def getManipulatedGeometryOutput(elementNode, geometryOutput, prefix):
	'Get inset geometryOutput.'
	derivation = InsetDerivation(elementNode, prefix)
	if derivation.radius == 0.0:
		return geometryOutput
	halfLayerHeight = 0.5 * derivation.radius
	importRadius = 0.5 * derivation.radius * setting.getImportCoarseness(elementNode)
	loopLayers = solid.getLoopLayersSetCopy(elementNode, geometryOutput, importRadius, derivation.radius)
	triangleAltitude = math.sqrt(0.75) * derivation.radius
	loops = []
	vertexes = []
	for loopLayerIndex in xrange(1, len(loopLayers), 2):
		loopLayer = loopLayers[loopLayerIndex]
		loopLayer.loops[0] = intercircle.getLargestInsetLoopFromLoop(loopLayer.loops[0], triangleAltitude)
	for loopLayerIndex in xrange(0, len(loopLayers), 2):
		loopLayer = loopLayers[loopLayerIndex]
		loopLists = [[solid.getLoopOrEmpty(loopLayerIndex - 2, loopLayers)]]
		loopLists.append([solid.getLoopOrEmpty(loopLayerIndex - 1, loopLayers)])
		loopLists.append([intercircle.getLargestInsetLoopFromLoop(loopLayer.loops[0], derivation.radius)])
		if evaluate.getEvaluatedBoolean(True, elementNode, prefix + 'insetTop'):
			loopLists.append([solid.getLoopOrEmpty(loopLayerIndex + 1, loopLayers)])
			loopLists.append([solid.getLoopOrEmpty(loopLayerIndex + 2, loopLayers)])
		largestLoop = euclidean.getLargestLoop(boolean_solid.getLoopsIntersection(importRadius, loopLists))
		triangle_mesh.addVector3Loop(largestLoop, loops, vertexes, loopLayer.z)
	if evaluate.getEvaluatedBoolean(False, elementNode, prefix + 'addExtraTopLayer') and len(loops) > 0:
		topLoop = loops[-1]
		vector3Loop = []
		loops.append(vector3Loop)
		z = topLoop[0].z + derivation.radius
		for point in topLoop:
			vector3Index = Vector3Index(len(vertexes), point.x, point.y, z)
			vector3Loop.append(vector3Index)
			vertexes.append(vector3Index)
	return triangle_mesh.getMeldedPillarOutput(loops)

def getManipulatedPaths(close, elementNode, loop, prefix, sideLength):
	"Get inset path."
	derivation = InsetDerivation(elementNode, prefix)
	return intercircle.getInsetLoopsFromVector3Loop(loop, derivation.radius)

def getNewDerivation(elementNode, prefix, sideLength):
	'Get new derivation.'
	return OutsetDerivation(elementNode, prefix)

def processElementNode(elementNode):
	'Process the xml element.'
	solid.processElementNodeByFunctionPair(elementNode, getManipulatedGeometryOutput, getManipulatedPaths)


class InsetDerivation:
	"Class to hold inset variables."
	def __init__(self, elementNode, prefix):
		'Set defaults.'
		self.radius = evaluate.getEvaluatedFloat(2.0 * setting.getEdgeWidth(elementNode), elementNode, prefix + 'radius')
