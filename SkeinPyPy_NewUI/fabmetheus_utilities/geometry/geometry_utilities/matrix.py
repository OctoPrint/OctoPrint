"""
Boolean geometry four by four matrix.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import xml_simple_writer
import cStringIO
import math


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


globalExecutionOrder = 300


def addVertexes(geometryOutput, vertexes):
	'Add the vertexes.'
	if geometryOutput.__class__ == list:
		for element in geometryOutput:
			addVertexes(element, vertexes)
		return
	if geometryOutput.__class__ == dict:
		for geometryOutputKey in geometryOutput.keys():
			if geometryOutputKey == 'vertex':
				vertexes += geometryOutput[geometryOutputKey]
			else:
				addVertexes(geometryOutput[geometryOutputKey], vertexes)

def getBranchMatrix(elementNode):
	'Get matrix starting from the object if it exists, otherwise get a matrix starting from stratch.'
	branchMatrix = Matrix()
	matrixChildElement = elementNode.getFirstChildByLocalName('matrix')
	if matrixChildElement != None:
		branchMatrix = branchMatrix.getFromElementNode(matrixChildElement, '')
	branchMatrix = branchMatrix.getFromElementNode(elementNode, 'matrix.')
	if elementNode.xmlObject == None:
		return branchMatrix
	elementNodeMatrix = elementNode.xmlObject.getMatrix4X4()
	if elementNodeMatrix == None:
		return branchMatrix
	return elementNodeMatrix.getOtherTimesSelf(branchMatrix.tetragrid)

def getBranchMatrixSetElementNode(elementNode):
	'Get matrix starting from the object if it exists, otherwise get a matrix starting from stratch.'
	branchMatrix = getBranchMatrix(elementNode)
	setElementNodeDictionaryMatrix(elementNode, branchMatrix)
	return branchMatrix

def getCumulativeVector3Remove(defaultVector3, elementNode, prefix):
	'Get cumulative vector3 and delete the prefixed attributes.'
	if prefix == '':
		defaultVector3.x = evaluate.getEvaluatedFloat(defaultVector3.x, elementNode, 'x')
		defaultVector3.y = evaluate.getEvaluatedFloat(defaultVector3.y, elementNode, 'y')
		defaultVector3.z = evaluate.getEvaluatedFloat(defaultVector3.z, elementNode, 'z')
		euclidean.removeElementsFromDictionary(elementNode.attributes, ['x', 'y', 'z'])
		prefix = 'cartesian'
	defaultVector3 = evaluate.getVector3ByPrefix(defaultVector3, elementNode, prefix)
	euclidean.removePrefixFromDictionary(elementNode.attributes, prefix)
	return defaultVector3

def getDiagonalSwitchedTetragrid(angleDegrees, diagonals):
	'Get the diagonals and switched matrix by degrees.'
	return getDiagonalSwitchedTetragridByRadians(math.radians(angleDegrees), diagonals)

def getDiagonalSwitchedTetragridByPolar(diagonals, unitPolar):
	'Get the diagonals and switched matrix by unitPolar.'
	diagonalSwitchedTetragrid = getIdentityTetragrid()
	for diagonal in diagonals:
		diagonalSwitchedTetragrid[diagonal][diagonal] = unitPolar.real
	diagonalSwitchedTetragrid[diagonals[0]][diagonals[1]] = -unitPolar.imag
	diagonalSwitchedTetragrid[diagonals[1]][diagonals[0]] = unitPolar.imag
	return diagonalSwitchedTetragrid

def getDiagonalSwitchedTetragridByRadians(angleRadians, diagonals):
	'Get the diagonals and switched matrix by radians.'
	return getDiagonalSwitchedTetragridByPolar(diagonals, euclidean.getWiddershinsUnitPolar(angleRadians))

def getIdentityTetragrid(tetragrid=None):
	'Get four by four matrix with diagonal elements set to one.'
	if tetragrid == None:
		return [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]
	return tetragrid

def getIsIdentityTetragrid(tetragrid):
	'Determine if the tetragrid is the identity tetragrid.'
	for column in xrange(4):
		for row in xrange(4):
			if column == row:
				if tetragrid[column][row] != 1.0:
					return False
			elif tetragrid[column][row] != 0.0:
				return False
	return True

def getIsIdentityTetragridOrNone(tetragrid):
	'Determine if the tetragrid is None or if it is the identity tetragrid.'
	if tetragrid == None:
		return True
	return getIsIdentityTetragrid(tetragrid)

def getKeyA(row, column, prefix=''):
	'Get the a format key string from row & column, counting from zero.'
	return '%sa%s%s' % (prefix, row, column)

def getKeyM(row, column, prefix=''):
	'Get the m format key string from row & column, counting from one.'
	return '%sm%s%s' % (prefix, row + 1, column + 1)

def getKeysA(prefix=''):
	'Get the matrix keys, counting from zero.'
	keysA = []
	for row in xrange(4):
		for column in xrange(4):
			key = getKeyA(row, column, prefix)
			keysA.append(key)
	return keysA

def getKeysM(prefix=''):
	'Get the matrix keys, counting from one.'
	keysM = []
	for row in xrange(4):
		for column in xrange(4):
			key = getKeyM(row, column, prefix)
			keysM.append(key)
	return keysM

def getRemovedFloat(defaultFloat, elementNode, key, prefix):
	'Get the float by the key and the prefix.'
	prefixKey = prefix + key
	if prefixKey in elementNode.attributes:
		floatValue = evaluate.getEvaluatedFloat(None, elementNode, prefixKey)
		if floatValue == None:
			print('Warning, evaluated value in getRemovedFloatByKeys in matrix is None for key:')
			print(prefixKey)
			print('for elementNode dictionary value:')
			print(elementNode.attributes[prefixKey])
			print('for elementNode dictionary:')
			print(elementNode.attributes)
		else:
			defaultFloat = floatValue
		del elementNode.attributes[prefixKey]
	return defaultFloat

def getRemovedFloatByKeys(defaultFloat, elementNode, keys, prefix):
	'Get the float by the keys and the prefix.'
	for key in keys:
		defaultFloat = getRemovedFloat(defaultFloat, elementNode, key, prefix)
	return defaultFloat

def getRotateAroundAxisTetragrid(elementNode, prefix):
	'Get rotate around axis tetragrid and delete the axis and angle attributes.'
	angle = getRemovedFloatByKeys(0.0, elementNode, ['angle', 'counterclockwise'], prefix)
	angle -= getRemovedFloat(0.0, elementNode, 'clockwise', prefix)
	if angle == 0.0:
		return None
	angleRadians = math.radians(angle)
	axis = getCumulativeVector3Remove(Vector3(), elementNode, prefix + 'axis')
	axisLength = abs(axis)
	if axisLength <= 0.0:
		print('Warning, axisLength was zero in getRotateAroundAxisTetragrid in matrix so nothing will be done for:')
		print(elementNode)
		return None
	axis /= axisLength
	tetragrid = getIdentityTetragrid()
	cosAngle = math.cos(angleRadians)
	sinAngle = math.sin(angleRadians)
	oneMinusCos = 1.0 - math.cos(angleRadians)
	xx = axis.x * axis.x
	xy = axis.x * axis.y
	xz = axis.x * axis.z
	yy = axis.y * axis.y
	yz = axis.y * axis.z
	zz = axis.z * axis.z
	tetragrid[0] = [cosAngle + xx * oneMinusCos, xy * oneMinusCos - axis.z * sinAngle, xz * oneMinusCos + axis.y * sinAngle, 0.0]
	tetragrid[1] = [xy * oneMinusCos + axis.z * sinAngle, cosAngle + yy * oneMinusCos, yz * oneMinusCos - axis.x * sinAngle, 0.0]
	tetragrid[2] = [xz * oneMinusCos - axis.y * sinAngle, yz * oneMinusCos + axis.x * sinAngle, cosAngle + zz * oneMinusCos, 0.0]
	return tetragrid

def getRotateTetragrid(elementNode, prefix):
	'Get rotate tetragrid and delete the rotate attributes.'
	# http://en.wikipedia.org/wiki/Rotation_matrix
	rotateMatrix = Matrix()
	rotateMatrix.tetragrid = getRotateAroundAxisTetragrid(elementNode, prefix)
	zAngle = getRemovedFloatByKeys(0.0, elementNode, ['axisclockwisez', 'observerclockwisez', 'z'], prefix)
	zAngle -= getRemovedFloatByKeys(0.0, elementNode, ['axiscounterclockwisez', 'observercounterclockwisez'], prefix)
	if zAngle != 0.0:
		rotateMatrix.tetragrid = getTetragridTimesOther(getDiagonalSwitchedTetragrid(-zAngle, [0, 1]), rotateMatrix.tetragrid)
	xAngle = getRemovedFloatByKeys(0.0, elementNode, ['axisclockwisex', 'observerclockwisex', 'x'], prefix)
	xAngle -= getRemovedFloatByKeys(0.0, elementNode, ['axiscounterclockwisex', 'observercounterclockwisex'], prefix)
	if xAngle != 0.0:
		rotateMatrix.tetragrid = getTetragridTimesOther(getDiagonalSwitchedTetragrid(-xAngle, [1, 2]), rotateMatrix.tetragrid)
	yAngle = getRemovedFloatByKeys(0.0, elementNode, ['axiscounterclockwisey', 'observerclockwisey', 'y'], prefix)
	yAngle -= getRemovedFloatByKeys(0.0, elementNode, ['axisclockwisey', 'observercounterclockwisey'], prefix)
	if yAngle != 0.0:
		rotateMatrix.tetragrid = getTetragridTimesOther(getDiagonalSwitchedTetragrid(yAngle, [0, 2]), rotateMatrix.tetragrid)
	return rotateMatrix.tetragrid

def getScaleTetragrid(elementNode, prefix):
	'Get scale matrix and delete the scale attributes.'
	scaleDefaultVector3 = Vector3(1.0, 1.0, 1.0)
	scale = getCumulativeVector3Remove(scaleDefaultVector3.copy(), elementNode, prefix)
	if scale == scaleDefaultVector3:
		return None
	return [[scale.x, 0.0, 0.0, 0.0], [0.0, scale.y, 0.0, 0.0], [0.0, 0.0, scale.z, 0.0], [0.0, 0.0, 0.0, 1.0]]

def getTetragridA(elementNode, prefix, tetragrid):
	'Get the tetragrid from the elementNode letter a values.'
	keysA = getKeysA(prefix)
	evaluatedDictionary = evaluate.getEvaluatedDictionaryByEvaluationKeys(elementNode, keysA)
	if len(evaluatedDictionary.keys()) < 1:
		return tetragrid
	for row in xrange(4):
		for column in xrange(4):
			key = getKeyA(row, column, prefix)
			if key in evaluatedDictionary:
				value = evaluatedDictionary[key]
				if value == None or value == 'None':
					print('Warning, value in getTetragridA in matrix is None for key for dictionary:')
					print(key)
					print(evaluatedDictionary)
				else:
					tetragrid = getIdentityTetragrid(tetragrid)
					tetragrid[row][column] = float(value)
	euclidean.removeElementsFromDictionary(elementNode.attributes, keysA)
	return tetragrid

def getTetragridC(elementNode, prefix, tetragrid):
	'Get the matrix Tetragrid from the elementNode letter c values.'
	columnKeys = 'Pc1 Pc2 Pc3 Pc4'.replace('P', prefix).split()
	evaluatedDictionary = evaluate.getEvaluatedDictionaryByEvaluationKeys(elementNode, columnKeys)
	if len(evaluatedDictionary.keys()) < 1:
		return tetragrid
	for columnKeyIndex, columnKey in enumerate(columnKeys):
		if columnKey in evaluatedDictionary:
			value = evaluatedDictionary[columnKey]
			if value == None or value == 'None':
				print('Warning, value in getTetragridC in matrix is None for columnKey for dictionary:')
				print(columnKey)
				print(evaluatedDictionary)
			else:
				tetragrid = getIdentityTetragrid(tetragrid)
				for elementIndex, element in enumerate(value):
					tetragrid[elementIndex][columnKeyIndex] = element
	euclidean.removeElementsFromDictionary(elementNode.attributes, columnKeys)
	return tetragrid

def getTetragridCopy(tetragrid):
	'Get tetragrid copy.'
	if tetragrid == None:
		return None
	tetragridCopy = []
	for tetragridRow in tetragrid:
		tetragridCopy.append(tetragridRow[:])
	return tetragridCopy

def getTetragridM(elementNode, prefix, tetragrid):
	'Get the tetragrid from the elementNode letter m values.'
	keysM = getKeysM(prefix)
	evaluatedDictionary = evaluate.getEvaluatedDictionaryByEvaluationKeys(elementNode, keysM)
	if len(evaluatedDictionary.keys()) < 1:
		return tetragrid
	for row in xrange(4):
		for column in xrange(4):
			key = getKeyM(row, column, prefix)
			if key in evaluatedDictionary:
				value = evaluatedDictionary[key]
				if value == None or value == 'None':
					print('Warning, value in getTetragridM in matrix is None for key for dictionary:')
					print(key)
					print(evaluatedDictionary)
				else:
					tetragrid = getIdentityTetragrid(tetragrid)
					tetragrid[row][column] = float(value)
	euclidean.removeElementsFromDictionary(elementNode.attributes, keysM)
	return tetragrid

def getTetragridMatrix(elementNode, prefix, tetragrid):
	'Get the tetragrid from the elementNode matrix value.'
	matrixKey = prefix + 'matrix'
	evaluatedDictionary = evaluate.getEvaluatedDictionaryByEvaluationKeys(elementNode, [matrixKey])
	if len(evaluatedDictionary.keys()) < 1:
		return tetragrid
	value = evaluatedDictionary[matrixKey]
	if value == None or value == 'None':
		print('Warning, value in getTetragridMatrix in matrix is None for matrixKey for dictionary:')
		print(matrixKey)
		print(evaluatedDictionary)
	else:
		tetragrid = getIdentityTetragrid(tetragrid)
		for rowIndex, row in enumerate(value):
			for elementIndex, element in enumerate(row):
				tetragrid[rowIndex][elementIndex] = element
	euclidean.removeElementsFromDictionary(elementNode.attributes, [matrixKey])
	return tetragrid

def getTetragridR(elementNode, prefix, tetragrid):
	'Get the tetragrid from the elementNode letter r values.'
	rowKeys = 'Pr1 Pr2 Pr3 Pr4'.replace('P', prefix).split()
	evaluatedDictionary = evaluate.getEvaluatedDictionaryByEvaluationKeys(elementNode, rowKeys)
	if len(evaluatedDictionary.keys()) < 1:
		return tetragrid
	for rowKeyIndex, rowKey in enumerate(rowKeys):
		if rowKey in evaluatedDictionary:
			value = evaluatedDictionary[rowKey]
			if value == None or value == 'None':
				print('Warning, value in getTetragridR in matrix is None for rowKey for dictionary:')
				print(rowKey)
				print(evaluatedDictionary)
			else:
				tetragrid = getIdentityTetragrid(tetragrid)
				for elementIndex, element in enumerate(value):
					tetragrid[rowKeyIndex][elementIndex] = element
	euclidean.removeElementsFromDictionary(elementNode.attributes, rowKeys)
	return tetragrid

def getTetragridTimesOther(firstTetragrid, otherTetragrid ):
	'Get this matrix multiplied by the other matrix.'
	#A down, B right from http://en.wikipedia.org/wiki/Matrix_multiplication
	if firstTetragrid == None:
		return otherTetragrid
	if otherTetragrid == None:
		return firstTetragrid
	tetragridTimesOther = []
	for row in xrange(4):
		matrixRow = firstTetragrid[row]
		tetragridTimesOtherRow = []
		tetragridTimesOther.append(tetragridTimesOtherRow)
		for column in xrange(4):
			dotProduct = 0
			for elementIndex in xrange(4):
				dotProduct += matrixRow[elementIndex] * otherTetragrid[elementIndex][column]
			tetragridTimesOtherRow.append(dotProduct)
	return tetragridTimesOther

def getTransformedByList(floatList, point):
	'Get the point transformed by the array.'
	return floatList[0] * point.x + floatList[1] * point.y + floatList[2] * point.z + floatList[3]

def getTransformedVector3(tetragrid, vector3):
	'Get the vector3 multiplied by a matrix.'
	if getIsIdentityTetragridOrNone(tetragrid):
		return vector3.copy()
	return getTransformedVector3Blindly(tetragrid, vector3)

def getTransformedVector3Blindly(tetragrid, vector3):
	'Get the vector3 multiplied by a tetragrid without checking if the tetragrid exists.'
	return Vector3(
		getTransformedByList(tetragrid[0], vector3),
		getTransformedByList(tetragrid[1], vector3),
		getTransformedByList(tetragrid[2], vector3))

def getTransformedVector3s(tetragrid, vector3s):
	'Get the vector3s multiplied by a matrix.'
	if getIsIdentityTetragridOrNone(tetragrid):
		return euclidean.getPathCopy(vector3s)
	transformedVector3s = []
	for vector3 in vector3s:
		transformedVector3s.append(getTransformedVector3Blindly(tetragrid, vector3))
	return transformedVector3s

def getTransformTetragrid(elementNode, prefix):
	'Get the tetragrid from the elementNode.'
	tetragrid = getTetragridA(elementNode, prefix, None)
	tetragrid = getTetragridC(elementNode, prefix, tetragrid)
	tetragrid = getTetragridM(elementNode, prefix, tetragrid)
	tetragrid = getTetragridMatrix(elementNode, prefix, tetragrid)
	tetragrid = getTetragridR(elementNode, prefix, tetragrid)
	return tetragrid

def getTranslateTetragrid(elementNode, prefix):
	'Get translate matrix and delete the translate attributes.'
	translation = getCumulativeVector3Remove(Vector3(), elementNode, prefix)
	if translation.getIsDefault():
		return None
	return getTranslateTetragridByTranslation(translation)

def getTranslateTetragridByTranslation(translation):
	'Get translate tetragrid by translation.'
	return [[1.0, 0.0, 0.0, translation.x], [0.0, 1.0, 0.0, translation.y], [0.0, 0.0, 1.0, translation.z], [0.0, 0.0, 0.0, 1.0]]

def getVertexes(geometryOutput):
	'Get the vertexes.'
	vertexes = []
	addVertexes(geometryOutput, vertexes)
	return vertexes

def setAttributesToMultipliedTetragrid(elementNode, tetragrid):
	'Set the element attribute dictionary and element matrix to the matrix times the tetragrid.'
	setElementNodeDictionaryMatrix(elementNode, getBranchMatrix(elementNode).getOtherTimesSelf(tetragrid))

def setElementNodeDictionaryMatrix(elementNode, matrix4X4):
	'Set the element attribute dictionary or element matrix to the matrix.'
	if elementNode.xmlObject == None:
		elementNode.attributes.update(matrix4X4.getAttributes('matrix.'))
	else:
		elementNode.xmlObject.matrix4X4 = matrix4X4

def transformVector3Blindly(tetragrid, vector3):
	'Transform the vector3 by a tetragrid without checking to see if it exists.'
	x = getTransformedByList(tetragrid[0], vector3)
	y = getTransformedByList(tetragrid[1], vector3)
	z = getTransformedByList(tetragrid[2], vector3)
	vector3.x = x
	vector3.y = y
	vector3.z = z

def transformVector3ByMatrix(tetragrid, vector3):
	'Transform the vector3 by a matrix.'
	if getIsIdentityTetragridOrNone(tetragrid):
		return
	transformVector3Blindly(tetragrid, vector3)

def transformVector3sByMatrix(tetragrid, vector3s):
	'Transform the vector3s by a matrix.'
	if getIsIdentityTetragridOrNone(tetragrid):
		return
	for vector3 in vector3s:
		transformVector3Blindly(tetragrid, vector3)


class Matrix:
	'A four by four matrix.'
	def __init__(self, tetragrid=None):
		'Add empty lists.'
		self.tetragrid = getTetragridCopy(tetragrid)

	def __eq__(self, other):
		'Determine whether this matrix is identical to other one.'
		if other == None:
			return False
		if other.__class__ != self.__class__:
			return False
		return other.tetragrid == self.tetragrid

	def __ne__(self, other):
		'Determine whether this vector is not identical to other one.'
		return not self.__eq__(other)

	def __repr__(self):
		'Get the string representation of this four by four matrix.'
		output = cStringIO.StringIO()
		self.addXML(0, output)
		return output.getvalue()

	def addXML(self, depth, output):
		'Add xml for this object.'
		attributes = self.getAttributes()
		if len(attributes) > 0:
			xml_simple_writer.addClosedXMLTag(attributes, depth, self.__class__.__name__.lower(), output)

	def getAttributes(self, prefix=''):
		'Get the attributes from row column attribute strings, counting from one.'
		attributes = {}
		if self.tetragrid == None:
			return attributes
		for row in xrange(4):
			for column in xrange(4):
				default = float(column == row)
				value = self.tetragrid[row][column]
				if abs( value - default ) > 0.00000000000001:
					if abs(value) < 0.00000000000001:
						value = 0.0
					attributes[prefix + getKeyM(row, column)] = value
		return attributes

	def getFromElementNode(self, elementNode, prefix):
		'Get the values from row column attribute strings, counting from one.'
		attributes = elementNode.attributes
		if attributes == None:
			return self
		self.tetragrid = getTetragridTimesOther(getTransformTetragrid(elementNode, prefix), self.tetragrid)
		self.tetragrid = getTetragridTimesOther(getScaleTetragrid(elementNode, 'scale.'), self.tetragrid)
		self.tetragrid = getTetragridTimesOther(getRotateTetragrid(elementNode, 'rotate.'), self.tetragrid)
		self.tetragrid = getTetragridTimesOther(getTranslateTetragrid(elementNode, 'translate.'), self.tetragrid)
		return self

	def getOtherTimesSelf(self, otherTetragrid):
		'Get this matrix reverse multiplied by the other matrix.'
		return Matrix(getTetragridTimesOther(otherTetragrid, self.tetragrid))

	def getSelfTimesOther(self, otherTetragrid):
		'Get this matrix multiplied by the other matrix.'
		return Matrix(getTetragridTimesOther(self.tetragrid, otherTetragrid))
