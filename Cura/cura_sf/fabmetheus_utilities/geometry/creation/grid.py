"""
Grid path points.

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
import random


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def addGridRow(diameter, gridPath, loopsComplex, maximumComplex, rowIndex, x, y, zigzag):
	'Add grid row.'
	row = []
	while x < maximumComplex.real:
		point = complex(x, y)
		if euclidean.getIsInFilledRegion(loopsComplex, point):
			row.append(point)
		x += diameter.real
	if zigzag and rowIndex % 2 == 1:
		row.reverse()
	gridPath += row

def getGeometryOutput(elementNode):
	'Get vector3 vertexes from attribute dictionary.'
	derivation = GridDerivation(elementNode)
	diameter = derivation.radius + derivation.radius
	typeStringTwoCharacters = derivation.typeString.lower()[: 2]
	typeStringFirstCharacter = typeStringTwoCharacters[: 1]
	topRight = complex(derivation.demiwidth, derivation.demiheight)
	loopsComplex = [euclidean.getSquareLoopWiddershins(-topRight, topRight)]
	if len(derivation.target) > 0:
		loopsComplex = euclidean.getComplexPaths(derivation.target)
	maximumComplex = euclidean.getMaximumByComplexPaths(loopsComplex)
	minimumComplex = euclidean.getMinimumByComplexPaths(loopsComplex)
	gridPath = None
	if typeStringTwoCharacters == 'he':
		gridPath = getHexagonalGrid(diameter, loopsComplex, maximumComplex, minimumComplex, derivation.zigzag)
	elif typeStringTwoCharacters == 'ra' or typeStringFirstCharacter == 'a':
		gridPath = getRandomGrid(derivation, diameter, elementNode, loopsComplex, maximumComplex, minimumComplex)
	elif typeStringTwoCharacters == 're' or typeStringFirstCharacter == 'e':
		gridPath = getRectangularGrid(diameter, loopsComplex, maximumComplex, minimumComplex, derivation.zigzag)
	if gridPath == None:
		print('Warning, the step type was not one of (hexagonal, random or rectangular) in getGeometryOutput in grid for:')
		print(derivation.typeString)
		print(elementNode)
		return []
	loop = euclidean.getVector3Path(gridPath)
	elementNode.attributes['closed'] = 'false'
	return lineation.getGeometryOutputByLoop(elementNode, lineation.SideLoop(loop, 0.5 * math.pi))

def getGeometryOutputByArguments(arguments, elementNode):
	'Get vector3 vertexes from attribute dictionary by arguments.'
	if len(arguments) < 1:
		return getGeometryOutput(elementNode)
	inradius = 0.5 * euclidean.getFloatFromValue(arguments[0])
	elementNode.attributes['inradius.x'] = str(inradius)
	if len(arguments) > 1:
		inradius = 0.5 * euclidean.getFloatFromValue(arguments[1])
	elementNode.attributes['inradius.y'] = str(inradius)
	return getGeometryOutput(elementNode)

def getHexagonalGrid(diameter, loopsComplex, maximumComplex, minimumComplex, zigzag):
	'Get hexagonal grid.'
	diameter = complex(diameter.real, math.sqrt(0.75) * diameter.imag)
	demiradius = 0.25 * diameter
	xRadius = 0.5 * diameter.real
	xStart = minimumComplex.real - demiradius.real
	y = minimumComplex.imag - demiradius.imag
	gridPath = []
	rowIndex = 0
	while y < maximumComplex.imag:
		x = xStart
		if rowIndex % 2 == 1:
			x -= xRadius
		addGridRow(diameter, gridPath, loopsComplex, maximumComplex, rowIndex, x, y, zigzag)
		y += diameter.imag
		rowIndex += 1
	return gridPath

def getIsPointInsideZoneAwayOthers(diameterReciprocal, loopsComplex, point, pixelDictionary):
	'Determine if the point is inside the loops zone and and away from the other points.'
	if not euclidean.getIsInFilledRegion(loopsComplex, point):
		return False
	pointOverDiameter = complex(point.real * diameterReciprocal.real, point.imag * diameterReciprocal.imag)
	squareValues = euclidean.getSquareValuesFromPoint(pixelDictionary, pointOverDiameter)
	for squareValue in squareValues:
		if abs(squareValue - pointOverDiameter) < 1.0:
			return False
	euclidean.addElementToPixelListFromPoint(pointOverDiameter, pixelDictionary, pointOverDiameter)
	return True

def getNewDerivation(elementNode):
	'Get new derivation.'
	return GridDerivation(elementNode)

def getRandomGrid(derivation, diameter, elementNode, loopsComplex, maximumComplex, minimumComplex):
	'Get rectangular grid.'
	gridPath = []
	diameterReciprocal = complex(1.0 / diameter.real, 1.0 / diameter.imag)
	diameterSquared = diameter.real * diameter.real + diameter.imag * diameter.imag
	elements = int(math.ceil(derivation.density * euclidean.getAreaLoops(loopsComplex) / diameterSquared / math.sqrt(0.75)))
	elements = evaluate.getEvaluatedInt(elements, elementNode, 'elements')
	failedPlacementAttempts = 0
	pixelDictionary = {}
	if derivation.seed != None:
		random.seed(derivation.seed)
	successfulPlacementAttempts = 0
	while failedPlacementAttempts < 100:
		point = euclidean.getRandomComplex(minimumComplex, maximumComplex)
		if getIsPointInsideZoneAwayOthers(diameterReciprocal, loopsComplex, point, pixelDictionary):
			gridPath.append(point)
			euclidean.addElementToPixelListFromPoint(point, pixelDictionary, point)
			successfulPlacementAttempts += 1
		else:
			failedPlacementAttempts += 1
		if successfulPlacementAttempts >= elements:
			return gridPath
	return gridPath

def getRectangularGrid(diameter, loopsComplex, maximumComplex, minimumComplex, zigzag):
	'Get rectangular grid.'
	demiradius = 0.25 * diameter
	xStart = minimumComplex.real - demiradius.real
	y = minimumComplex.imag - demiradius.imag
	gridPath = []
	rowIndex = 0
	while y < maximumComplex.imag:
		addGridRow(diameter, gridPath, loopsComplex, maximumComplex, rowIndex, xStart, y, zigzag)
		y += diameter.imag
		rowIndex += 1
	return gridPath

def processElementNode(elementNode):
	'Process the xml element.'
	path.convertElementNode(elementNode, getGeometryOutput(elementNode))


class GridDerivation:
	'Class to hold grid variables.'
	def __init__(self, elementNode):
		'Set defaults.'
		self.inradius = lineation.getInradius(complex(10.0, 10.0), elementNode)
		self.demiwidth = lineation.getFloatByPrefixBeginEnd(elementNode, 'demiwidth', 'width', self.inradius.real)
		self.demiheight = lineation.getFloatByPrefixBeginEnd(elementNode, 'demiheight', 'height', self.inradius.imag)
		self.density = evaluate.getEvaluatedFloat(0.2, elementNode, 'density')
		self.radius = lineation.getComplexByPrefixBeginEnd(elementNode, 'elementRadius', 'elementDiameter', complex(1.0, 1.0))
		self.radius = lineation.getComplexByPrefixBeginEnd(elementNode, 'radius', 'diameter', self.radius)
		self.seed = evaluate.getEvaluatedInt(None, elementNode, 'seed')
		self.target = evaluate.getTransformedPathsByKey([], elementNode, 'target')
		self.typeMenuRadioStrings = 'hexagonal random rectangular'.split()
		self.typeString = evaluate.getEvaluatedString('rectangular', elementNode, 'type')
		self.zigzag = evaluate.getEvaluatedBoolean(True, elementNode, 'zigzag')
