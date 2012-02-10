"""
Boolean geometry extrusion.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import lineation
from fabmetheus_utilities.geometry.creation import solid
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.solids import triangle_mesh
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import euclidean
import math


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

def addLoopByComplex(derivation, endMultiplier, loopLists, path, pointComplex, vertexes):
	"Add an indexed loop to the vertexes."
	loops = loopLists[-1]
	loop = []
	loops.append(loop)
	for point in path:
		pointMinusBegin = point - derivation.axisStart
		dotVector3 = derivation.axisProjectiveSpace.getDotVector3(pointMinusBegin)
		dotVector3Complex = dotVector3.dropAxis()
		dotPointComplex = pointComplex * dotVector3Complex
		dotPoint = Vector3(dotPointComplex.real, dotPointComplex.imag, dotVector3.z)
		projectedVector3 = derivation.axisProjectiveSpace.getVector3ByPoint(dotPoint) + derivation.axisStart
		loop.append(projectedVector3)

def addNegatives(derivation, negatives, paths):
	"Add pillars output to negatives."
	for path in paths:
		loopListsByPath = getLoopListsByPath(derivation, 1.000001, path)
		geometryOutput = triangle_mesh.getPillarsOutput(loopListsByPath)
		negatives.append(geometryOutput)

def addNegativesPositives(derivation, negatives, paths, positives):
	"Add pillars output to negatives and positives."
	for path in paths:
		endMultiplier = None
		normal = euclidean.getNormalByPath(path)
		if normal.dot(derivation.normal) < 0.0:
			endMultiplier = 1.000001
		loopListsByPath = getLoopListsByPath(derivation, endMultiplier, path)
		geometryOutput = triangle_mesh.getPillarsOutput(loopListsByPath)
		if endMultiplier == None:
			positives.append(geometryOutput)
		else:
			negatives.append(geometryOutput)

def addOffsetAddToLists( loop, offset, vector3Index, vertexes ):
	"Add an indexed loop to the vertexes."
	vector3Index += offset
	loop.append( vector3Index )
	vertexes.append( vector3Index )

def addPositives(derivation, paths, positives):
	"Add pillars output to positives."
	for path in paths:
		loopListsByPath = getLoopListsByPath(derivation, None, path)
		geometryOutput = triangle_mesh.getPillarsOutput(loopListsByPath)
		positives.append(geometryOutput)

def getGeometryOutput(derivation, elementNode):
	"Get triangle mesh from attribute dictionary."
	if derivation == None:
		derivation = LatheDerivation(elementNode)
	if len(euclidean.getConcatenatedList(derivation.target)) == 0:
		print('Warning, in lathe there are no paths.')
		print(elementNode.attributes)
		return None
	negatives = []
	positives = []
	addNegativesPositives(derivation, negatives, derivation.target, positives)
	return getGeometryOutputByNegativesPositives(derivation, elementNode, negatives, positives)

def getGeometryOutputByArguments(arguments, elementNode):
	"Get triangle mesh from attribute dictionary by arguments."
	return getGeometryOutput(None, elementNode)

def getGeometryOutputByNegativesPositives(derivation, elementNode, negatives, positives):
	"Get triangle mesh from derivation, elementNode, negatives and positives."
	positiveOutput = triangle_mesh.getUnifiedOutput(positives)
	if len(negatives) < 1:
		return solid.getGeometryOutputByManipulation(elementNode, positiveOutput)
	return solid.getGeometryOutputByManipulation(elementNode, {'difference' : {'shapes' : [positiveOutput] + negatives}})

def getLoopListsByPath(derivation, endMultiplier, path):
	"Get loop lists from path."
	vertexes = []
	loopLists = [[]]
	if len(derivation.loop) < 2:
		return loopLists
	for pointIndex, pointComplex in enumerate(derivation.loop):
		if endMultiplier != None and not derivation.isEndCloseToStart:
			if pointIndex == 0:
				nextPoint = derivation.loop[1]
				pointComplex = endMultiplier * (pointComplex - nextPoint) + nextPoint
			elif pointIndex == len(derivation.loop) - 1:
				previousPoint = derivation.loop[pointIndex - 1]
				pointComplex = endMultiplier * (pointComplex - previousPoint) + previousPoint
		addLoopByComplex(derivation, endMultiplier, loopLists, path, pointComplex, vertexes)
	if derivation.isEndCloseToStart:
		loopLists[-1].append([])
	return loopLists

def getNewDerivation(elementNode):
	'Get new derivation.'
	return LatheDerivation(elementNode)

def processElementNode(elementNode):
	"Process the xml element."
	solid.processElementNodeByGeometry(elementNode, getGeometryOutput(None, elementNode))


class LatheDerivation:
	"Class to hold lathe variables."
	def __init__(self, elementNode):
		'Set defaults.'
		self.axisEnd = evaluate.getVector3ByPrefix(None, elementNode, 'axisEnd')
		self.axisStart = evaluate.getVector3ByPrefix(None, elementNode, 'axisStart')
		self.end = evaluate.getEvaluatedFloat(360.0, elementNode, 'end')
		self.loop = evaluate.getTransformedPathByKey([], elementNode, 'loop')
		self.sides = evaluate.getEvaluatedInt(None, elementNode, 'sides')
		self.start = evaluate.getEvaluatedFloat(0.0, elementNode, 'start')
		self.target = evaluate.getTransformedPathsByKey([], elementNode, 'target')
		if len(self.target) < 1:
			print('Warning, no target in derive in lathe for:')
			print(elementNode)
			return
		firstPath = self.target[0]
		if len(firstPath) < 3:
			print('Warning, firstPath length is less than three in derive in lathe for:')
			print(elementNode)
			self.target = []
			return
		if self.axisStart == None:
			if self.axisEnd == None:
				self.axisStart = firstPath[0]
				self.axisEnd = firstPath[-1]
			else:
				self.axisStart = Vector3()
		self.axis = self.axisEnd - self.axisStart
		axisLength = abs(self.axis)
		if axisLength <= 0.0:
			print('Warning, axisLength is zero in derive in lathe for:')
			print(elementNode)
			self.target = []
			return
		self.axis /= axisLength
		firstVector3 = firstPath[1] - self.axisStart
		firstVector3Length = abs(firstVector3)
		if firstVector3Length <= 0.0:
			print('Warning, firstVector3Length is zero in derive in lathe for:')
			print(elementNode)
			self.target = []
			return
		firstVector3 /= firstVector3Length
		self.axisProjectiveSpace = euclidean.ProjectiveSpace().getByBasisZFirst(self.axis, firstVector3)
		if self.sides == None:
			distanceToLine = euclidean.getDistanceToLineByPaths(self.axisStart, self.axisEnd, self.target)
			self.sides = evaluate.getSidesMinimumThreeBasedOnPrecisionSides(elementNode, distanceToLine)
		endRadian = math.radians(self.end)
		startRadian = math.radians(self.start)
		self.isEndCloseToStart = euclidean.getIsRadianClose(endRadian, startRadian)
		if len(self.loop) < 1:
			self.loop = euclidean.getComplexPolygonByStartEnd(endRadian, 1.0, self.sides, startRadian)
		self.normal = euclidean.getNormalByPath(firstPath)
