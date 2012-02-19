"""
Mechaslab.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import extrude
from fabmetheus_utilities.geometry.creation import lineation
from fabmetheus_utilities.geometry.creation import peg
from fabmetheus_utilities.geometry.creation import solid
from fabmetheus_utilities.geometry.geometry_utilities.evaluate_elements import setting
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.geometry_utilities import matrix
from fabmetheus_utilities.geometry.manipulation_matrix import translate
from fabmetheus_utilities.geometry.solids import cylinder
from fabmetheus_utilities.geometry.solids import triangle_mesh
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import euclidean
import math


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def addAlongWay(begin, distance, end, loop):
	'Get the beveled rectangle.'
	endMinusBegin = end - begin
	endMinusBeginLength = abs(endMinusBegin)
	if endMinusBeginLength <= 0.0:
		return
	alongWayMultiplier = distance / endMinusBeginLength
	loop.append(begin + alongWayMultiplier * endMinusBegin)

def addGroove(derivation, negatives):
	'Add groove on each side of cage.'
	copyShallow = derivation.elementNode.getCopyShallow()
	extrude.setElementNodeToEndStart(copyShallow, Vector3(-derivation.demilength), Vector3(derivation.demilength))
	extrudeDerivation = extrude.ExtrudeDerivation(copyShallow)
	bottom = derivation.demiheight - 0.5 * derivation.grooveWidth
	outside = derivation.demiwidth
	top = derivation.demiheight
	leftGroove = [
		complex(-outside, bottom),
		complex(-derivation.innerDemiwidth, derivation.demiheight),
		complex(-outside, top)]
	rightGroove = [
		complex(outside, top),
		complex(derivation.innerDemiwidth, derivation.demiheight),
		complex(outside, bottom)]
	groovesComplex = [leftGroove, rightGroove]
	groovesVector3 = euclidean.getVector3Paths(groovesComplex)
	extrude.addPositives(extrudeDerivation, groovesVector3, negatives)

def addHollowPegSocket(derivation, hollowPegSocket, negatives, positives):
	'Add the socket and hollow peg.'
	pegHeight = derivation.pegHeight
	pegRadians = derivation.pegRadians
	pegRadiusComplex = complex(derivation.pegRadiusArealized, derivation.pegRadiusArealized)
	pegTip = 0.8 * derivation.pegRadiusArealized
	sides = derivation.pegSides
	start = Vector3(hollowPegSocket.center.real, hollowPegSocket.center.imag, derivation.height)
	tinyHeight = 0.0001 * pegHeight
	topRadians = 0.25 * math.pi
	boltTop = derivation.height
	if hollowPegSocket.shouldAddPeg:
		boltTop = peg.getTopAddBiconicOutput(
			pegRadians, pegHeight, positives, pegRadiusComplex, sides, start, pegTip, topRadians)
	sides = derivation.socketSides
	socketHeight = 1.05 * derivation.pegHeight
	socketRadiusComplex = complex(derivation.socketRadiusArealized, derivation.socketRadiusArealized)
	socketTip = 0.5 * derivation.overhangSpan
	start = Vector3(hollowPegSocket.center.real, hollowPegSocket.center.imag, -tinyHeight)
	topRadians = derivation.interiorOverhangRadians
	if hollowPegSocket.shouldAddSocket:
		peg.getTopAddBiconicOutput(pegRadians, socketHeight, negatives, socketRadiusComplex, sides, start, socketTip, topRadians)
	if derivation.boltRadius <= 0.0:
		return
	if (not hollowPegSocket.shouldAddPeg) and (not hollowPegSocket.shouldAddSocket):
		return
	boltRadiusComplex = complex(derivation.boltRadius, derivation.boltRadius)
	cylinder.addCylinderOutputByEndStart(boltTop + tinyHeight, boltRadiusComplex, negatives, derivation.boltSides, start)

def addSlab(derivation, positives):
	'Add slab.'
	copyShallow = derivation.elementNode.getCopyShallow()
	copyShallow.attributes['path'] = [Vector3(), Vector3(0.0, 0.0, derivation.height)]
	extrudeDerivation = extrude.ExtrudeDerivation(copyShallow)
	beveledRectangle = getBeveledRectangle(derivation.bevel, -derivation.topRight)
	outsidePath = euclidean.getVector3Path(beveledRectangle)
	extrude.addPositives(extrudeDerivation, [outsidePath], positives)

def addXGroove(derivation, negatives, y):
	'Add x groove.'
	if derivation.topBevel <= 0.0:
		return
	bottom = derivation.height - derivation.topBevel
	top = derivation.height
	groove = [complex(y, bottom), complex(y - derivation.topBevel, top), complex(y + derivation.topBevel, top)]
	triangle_mesh.addSymmetricXPath(negatives, groove, 1.0001 * derivation.topRight.real)

def addYGroove(derivation, negatives, x):
	'Add y groove'
	if derivation.topBevel <= 0.0:
		return
	bottom = derivation.height - derivation.topBevel
	top = derivation.height
	groove = [complex(x, bottom), complex(x - derivation.topBevel, top), complex(x + derivation.topBevel, top)]
	triangle_mesh.addSymmetricYPath(negatives, groove, 1.0001 * derivation.topRight.imag)

def getBeveledRectangle(bevel, bottomLeft):
	'Get the beveled rectangle.'
	bottomRight = complex(-bottomLeft.real, bottomLeft.imag)
	rectangle = [bottomLeft, bottomRight, -bottomLeft, -bottomRight]
	if bevel <= 0.0:
		return rectangle
	beveledRectangle = []
	for pointIndex, point in enumerate(rectangle):
		begin = rectangle[(pointIndex + len(rectangle) - 1) % len(rectangle)]
		end = rectangle[(pointIndex + 1) % len(rectangle)]
		addAlongWay(point, bevel, begin, beveledRectangle)
		addAlongWay(point, bevel, end, beveledRectangle)
	return beveledRectangle

def getGeometryOutput(elementNode):
	'Get vector3 vertexes from attribute dictionary.'
	derivation = MechaslabDerivation(elementNode)
	negatives = []
	positives = []
	addSlab(derivation, positives)
	for hollowPegSocket in derivation.hollowPegSockets:
		addHollowPegSocket(derivation, hollowPegSocket, negatives, positives)
	if 's' in derivation.topBevelPositions:
		addXGroove(derivation, negatives, -derivation.topRight.imag)
	if 'n' in derivation.topBevelPositions:
		addXGroove(derivation, negatives, derivation.topRight.imag)
	if 'w' in derivation.topBevelPositions:
		addYGroove(derivation, negatives, -derivation.topRight.real)
	if 'e' in derivation.topBevelPositions:
		addYGroove(derivation, negatives, derivation.topRight.real)
	return extrude.getGeometryOutputByNegativesPositives(elementNode, negatives, positives)

def getGeometryOutputByArguments(arguments, elementNode):
	'Get vector3 vertexes from attribute dictionary by arguments.'
	evaluate.setAttributesByArguments(['length', 'radius'], arguments, elementNode)
	return getGeometryOutput(elementNode)

def getNewDerivation(elementNode):
	'Get new derivation.'
	return MechaslabDerivation(elementNode)

def processElementNode(elementNode):
	'Process the xml element.'
	solid.processElementNodeByGeometry(elementNode, getGeometryOutput(elementNode))


class CellExistence:
	'Class to determine if a cell exists.'
	def __init__(self, columns, rows, value):
		'Initialize.'
		self.existenceSet = None
		if value == None:
			return
		self.existenceSet = set()
		for element in value:
			if element.__class__ == int:
				columnIndex = (element + columns) % columns
				for rowIndex in xrange(rows):
					keyTuple = (columnIndex, rowIndex)
					self.existenceSet.add(keyTuple)
			else:
				keyTuple = (element[0], element[1])
				self.existenceSet.add(keyTuple)

	def __repr__(self):
		'Get the string representation of this CellExistence.'
		return euclidean.getDictionaryString(self.__dict__)

	def getIsInExistence(self, columnIndex, rowIndex):
		'Detremine if the cell at the column and row exists.'
		if self.existenceSet == None:
			return True
		return (columnIndex, rowIndex) in self.existenceSet


class HollowPegSocket:
	'Class to hold hollow peg socket variables.'
	def __init__(self, center):
		'Initialize.'
		self.center = center
		self.shouldAddPeg = True
		self.shouldAddSocket = True

	def __repr__(self):
		'Get the string representation of this HollowPegSocket.'
		return euclidean.getDictionaryString(self.__dict__)


class MechaslabDerivation:
	'Class to hold mechaslab variables.'
	def __init__(self, elementNode):
		'Set defaults.'
		self.bevelOverRadius = evaluate.getEvaluatedFloat(0.2, elementNode, 'bevelOverRadius')
		self.boltRadiusOverRadius = evaluate.getEvaluatedFloat(0.0, elementNode, 'boltRadiusOverRadius')
		self.columns = evaluate.getEvaluatedInt(2, elementNode, 'columns')
		self.elementNode = elementNode
		self.heightOverRadius = evaluate.getEvaluatedFloat(2.0, elementNode, 'heightOverRadius')
		self.interiorOverhangRadians = setting.getInteriorOverhangRadians(elementNode)
		self.overhangSpan = setting.getOverhangSpan(elementNode)
		self.pegClearanceOverRadius = evaluate.getEvaluatedFloat(0.0, elementNode, 'pegClearanceOverRadius')
		self.pegRadians = math.radians(evaluate.getEvaluatedFloat(2.0, elementNode, 'pegAngle'))
		self.pegHeightOverHeight = evaluate.getEvaluatedFloat(0.4, elementNode, 'pegHeightOverHeight')
		self.pegRadiusOverRadius = evaluate.getEvaluatedFloat(0.7, elementNode, 'pegRadiusOverRadius')
		self.radius = lineation.getFloatByPrefixBeginEnd(elementNode, 'radius', 'width', 5.0)
		self.rows = evaluate.getEvaluatedInt(1, elementNode, 'rows')
		self.topBevelOverRadius = evaluate.getEvaluatedFloat(0.2, elementNode, 'topBevelOverRadius')
		# Set derived values.
		self.bevel = evaluate.getEvaluatedFloat(self.bevelOverRadius * self.radius, elementNode, 'bevel')
		self.boltRadius = evaluate.getEvaluatedFloat(self.boltRadiusOverRadius * self.radius, elementNode, 'boltRadius')
		self.boltSides = evaluate.getSidesMinimumThreeBasedOnPrecision(elementNode, self.boltRadius)
		self.bottomLeftCenter = complex(-float(self.columns - 1), -float(self.rows - 1)) * self.radius
		self.height = evaluate.getEvaluatedFloat(self.heightOverRadius * self.radius, elementNode, 'height')
		self.hollowPegSockets = []
		centerY = self.bottomLeftCenter.imag
		diameter = self.radius + self.radius
		self.pegExistence = CellExistence(self.columns, self.rows, evaluate.getEvaluatedValue(None, elementNode, 'pegs'))
		self.socketExistence = CellExistence(self.columns, self.rows, evaluate.getEvaluatedValue(None, elementNode, 'sockets'))
		for rowIndex in xrange(self.rows):
			centerX = self.bottomLeftCenter.real
			for columnIndex in xrange(self.columns):
				hollowPegSocket = HollowPegSocket(complex(centerX, centerY))
				hollowPegSocket.shouldAddPeg = self.pegExistence.getIsInExistence(columnIndex, rowIndex)
				hollowPegSocket.shouldAddSocket = self.socketExistence.getIsInExistence(columnIndex, rowIndex)
				self.hollowPegSockets.append(hollowPegSocket)
				centerX += diameter
			centerY += diameter
		self.pegClearance = evaluate.getEvaluatedFloat(self.pegClearanceOverRadius * self.radius, elementNode, 'pegClearance')
		halfPegClearance = 0.5 * self.pegClearance
		self.pegHeight = evaluate.getEvaluatedFloat(self.pegHeightOverHeight * self.height, elementNode, 'pegHeight')
		self.pegRadius = evaluate.getEvaluatedFloat(self.pegRadiusOverRadius * self.radius, elementNode, 'pegRadius')
		sides = 24 * max(1, math.floor(evaluate.getSidesBasedOnPrecision(elementNode, self.pegRadius) / 24))
		self.socketRadius = self.pegRadius + halfPegClearance
		self.pegSides = evaluate.getEvaluatedInt(sides, elementNode, 'pegSides')
		self.pegRadius -= halfPegClearance
		self.pegRadiusArealized = evaluate.getRadiusArealizedBasedOnAreaRadius(elementNode, self.pegRadius, self.pegSides)
		self.socketSides = evaluate.getEvaluatedInt(sides, elementNode, 'socketSides')
		self.socketRadiusArealized = evaluate.getRadiusArealizedBasedOnAreaRadius(elementNode, self.socketRadius, self.socketSides)
		self.topBevel = evaluate.getEvaluatedFloat(self.topBevelOverRadius * self.radius, elementNode, 'topBevel')
		self.topBevelPositions = evaluate.getEvaluatedString('nwse', elementNode, 'topBevelPositions').lower()
		self.topRight = complex(float(self.columns), float(self.rows)) * self.radius

	def __repr__(self):
		'Get the string representation of this MechaslabDerivation.'
		return euclidean.getDictionaryString(self.__dict__)
