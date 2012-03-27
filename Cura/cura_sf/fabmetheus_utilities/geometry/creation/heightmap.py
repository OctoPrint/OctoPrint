"""
Heightmap.
http://www.cs.otago.ac.nz/graphics/Mirage/node59.html
http://en.wikipedia.org/wiki/Heightmap
http://en.wikipedia.org/wiki/Netpbm_format

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import lineation
from fabmetheus_utilities.geometry.creation import solid
from fabmetheus_utilities.geometry.geometry_tools import path
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.solids import triangle_mesh
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities.vector3index import Vector3Index
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
import math
import random


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def addHeightsByBitmap(heights, textLines):
	'Add heights by bitmap.'
	for line in textLines[3:]:
		for integerWord in line.split():
			heights.append(float(integerWord))

def addHeightsByGraymap(heights, textLines):
	'Add heights by graymap.'
	divisor = float(textLines[3])
	for line in textLines[4:]:
		for integerWord in line.split():
			heights.append(float(integerWord) / divisor)

def getAddIndexedHeightGrid(heightGrid, minimumXY, step, top, vertexes):
	'Get and add an indexed heightGrid.'
	indexedHeightGrid = []
	for rowIndex, row in enumerate(heightGrid):
		indexedRow = []
		indexedHeightGrid.append(indexedRow)
		rowOffset = step.imag * float(rowIndex) + minimumXY.imag
		for columnIndex, element in enumerate(row):
			columnOffset = step.real * float(columnIndex) + minimumXY.real
			vector3index = Vector3Index(len(vertexes), columnOffset, rowOffset, top * element)
			indexedRow.append(vector3index)
			vertexes.append(vector3index)
	return indexedHeightGrid

def getAddIndexedSegmentedPerimeter(heightGrid, maximumXY, minimumXY, step, vertexes, z=0.0):
	'Get and add an indexed segmented perimeter.'
	indexedSegmentedPerimeter = []
	firstRow = heightGrid[0]
	columnOffset = minimumXY.real
	numberOfRowsMinusTwo = len(heightGrid) - 2
	for column in firstRow:
		vector3index = Vector3Index(len(vertexes), columnOffset, minimumXY.imag, z)
		vertexes.append(vector3index)
		indexedSegmentedPerimeter.append(vector3index)
		columnOffset += step.real
	rowOffset = minimumXY.imag
	for rowIndex in xrange(numberOfRowsMinusTwo):
		rowOffset += step.imag
		vector3index = Vector3Index(len(vertexes), maximumXY.real, rowOffset, z)
		vertexes.append(vector3index)
		indexedSegmentedPerimeter.append(vector3index)
	columnOffset = maximumXY.real
	for column in firstRow:
		vector3index = Vector3Index(len(vertexes), columnOffset, maximumXY.imag, z)
		vertexes.append(vector3index)
		indexedSegmentedPerimeter.append(vector3index)
		columnOffset -= step.real
	rowOffset = maximumXY.imag
	for rowIndex in xrange(numberOfRowsMinusTwo):
		rowOffset -= step.imag
		vector3index = Vector3Index(len(vertexes), minimumXY.real, rowOffset, z)
		vertexes.append(vector3index)
		indexedSegmentedPerimeter.append(vector3index)
	return indexedSegmentedPerimeter

def getGeometryOutput(elementNode):
	'Get vector3 vertexes from attribute dictionary.'
	derivation = HeightmapDerivation(elementNode)
	heightGrid = derivation.heightGrid
	if derivation.fileName != '':
		heightGrid = getHeightGrid(archive.getAbsoluteFolderPath(elementNode.getOwnerDocument().fileName, derivation.fileName))
	return getGeometryOutputByHeightGrid(derivation, elementNode, heightGrid)

def getGeometryOutputByArguments(arguments, elementNode):
	'Get vector3 vertexes from attribute dictionary by arguments.'
	evaluate.setAttributesByArguments(['file', 'start'], arguments, elementNode)
	return getGeometryOutput(elementNode)

def getGeometryOutputByHeightGrid(derivation, elementNode, heightGrid):
	'Get vector3 vertexes from attribute dictionary.'
	numberOfColumns = len(heightGrid)
	if numberOfColumns < 2:
		print('Warning, in getGeometryOutputByHeightGrid in heightmap there are fewer than two rows for:')
		print(heightGrid)
		print(elementNode)
		return None
	numberOfRows = len(heightGrid[0])
	if numberOfRows < 2:
		print('Warning, in getGeometryOutputByHeightGrid in heightmap there are fewer than two columns for:')
		print(heightGrid)
		print(elementNode)
		return None
	for row in heightGrid:
		if len(row) != numberOfRows:
			print('Warning, in getGeometryOutputByHeightGrid in heightmap the heightgrid is not rectangular for:')
			print(heightGrid)
			print(elementNode)
			return None
	inradiusComplex = derivation.inradius.dropAxis()
	minimumXY = -inradiusComplex
	step = complex(derivation.inradius.x / float(numberOfRows - 1), derivation.inradius.y / float(numberOfColumns - 1))
	step += step
	faces = []
	heightGrid = getRaisedHeightGrid(heightGrid, derivation.start)
	top = derivation.inradius.z + derivation.inradius.z
	vertexes = []
	indexedBottomLoop = getAddIndexedSegmentedPerimeter(heightGrid, inradiusComplex, minimumXY, step, vertexes)
	indexedLoops = [indexedBottomLoop]
	indexedGridTop = getAddIndexedHeightGrid(heightGrid, minimumXY, step, top, vertexes)
	indexedLoops.append(triangle_mesh.getIndexedLoopFromIndexedGrid(indexedGridTop))
	vertexes = triangle_mesh.getUniqueVertexes(indexedLoops + indexedGridTop)
	triangle_mesh.addPillarFromConvexLoopsGridTop(faces, indexedGridTop, indexedLoops)
	return triangle_mesh.getGeometryOutputByFacesVertexes(faces, vertexes)

def getHeightGrid(fileName):
	'Get heightGrid by fileName.'
	if 'models/' not in fileName:
		print('Warning, models/ was not in the absolute file path, so for security nothing will be done for:')
		print(fileName)
		print('The heightmap tool can only read a file which has models/ in the file path.')
		print('To import the file, move the file into a folder called model/ or a subfolder which is inside the model folder tree.')
		return
	pgmText = archive.getFileText(fileName)
	textLines = archive.getTextLines(pgmText)
	format = textLines[0].lower()
	sizeWords = textLines[2].split()
	numberOfColumns = int(sizeWords[0])
	numberOfRows = int(sizeWords[1])
	heights = []
	if format == 'p1':
		addHeightsByBitmap(heights, textLines)
	elif format == 'p2':
		addHeightsByGraymap(heights, textLines)
	else:
		print('Warning, the file format was not recognized for:')
		print(fileName)
		print('Heightmap can only read the Netpbm Portable bitmap format and the Netpbm Portable graymap format.')
		print('The Netpbm formats are described at:')
		print('http://en.wikipedia.org/wiki/Netpbm_format')
		return []
	heightGrid = []
	heightIndex = 0
	for rowIndex in xrange(numberOfRows):
		row = []
		heightGrid.append(row)
		for columnIndex in xrange(numberOfColumns):
			row.append(heights[heightIndex])
			heightIndex += 1
	return heightGrid

def getNewDerivation(elementNode):
	'Get new derivation.'
	return HeightmapDerivation(elementNode)

def getRaisedHeightGrid(heightGrid, start):
	'Get heightGrid raised above start.'
	raisedHeightGrid = []
	remainingHeight = 1.0 - start
	for row in heightGrid:
		raisedRow = []
		raisedHeightGrid.append(raisedRow)
		for element in row:
			raisedElement = remainingHeight * element + start
			raisedRow.append(raisedElement)
	return raisedHeightGrid

def processElementNode(elementNode):
	'Process the xml element.'
	solid.processElementNodeByGeometry(elementNode, getGeometryOutput(elementNode))


class HeightmapDerivation:
	'Class to hold heightmap variables.'
	def __init__(self, elementNode):
		'Set defaults.'
		self.fileName = evaluate.getEvaluatedString('', elementNode, 'file')
		self.heightGrid = evaluate.getEvaluatedValue([], elementNode, 'heightGrid')
		self.inradius = evaluate.getVector3ByPrefixes(elementNode, ['demisize', 'inradius'], Vector3(10.0, 10.0, 5.0))
		self.inradius = evaluate.getVector3ByMultiplierPrefix(elementNode, 2.0, 'size', self.inradius)
		self.start = evaluate.getEvaluatedFloat(0.0, elementNode, 'start')

	def __repr__(self):
		'Get the string representation of this HeightmapDerivation.'
		return euclidean.getDictionaryString(self.__dict__)
