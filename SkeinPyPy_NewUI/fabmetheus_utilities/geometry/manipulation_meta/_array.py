"""
Boolean geometry array.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.geometry_tools import vertex
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.geometry_utilities import matrix
from fabmetheus_utilities import euclidean
import math


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def addPathToGroup(derivation, groupDictionaryCopy, path, targetMatrix, totalIndex):
	'Add path to the array group.'
	for pointIndex, point in enumerate(path):
		arrayElement = derivation.target.getCopy(derivation.elementNode.getIDSuffix(totalIndex), derivation.elementNode)
		arrayDictionary = arrayElement.attributes
		arrayDictionary['visible'] = str(derivation.visible).lower()
		arrayDictionary.update(groupDictionaryCopy)
		euclidean.removeTrueFromDictionary(arrayDictionary, 'visible')
		vertexMatrix = matrix.Matrix(matrix.getTranslateTetragridByTranslation(point))
		zAngle = totalIndex * 50.0
		rotationMatrix = getRotationMatrix(arrayDictionary, derivation, path, point, pointIndex)
		arrayElementMatrix = vertexMatrix.getSelfTimesOther(rotationMatrix.getSelfTimesOther(targetMatrix.tetragrid).tetragrid)
		arrayDictionary.update(arrayElementMatrix.getAttributes('matrix.'))
		arrayDictionary['_arrayIndex'] = totalIndex
		arrayDictionary['_arrayPoint'] = point
		totalIndex += 1

def getNewDerivation(elementNode):
	'Get new derivation.'
	return ArrayDerivation(elementNode)

def getRotationMatrix(arrayDictionary, derivation, path, point, pointIndex):
	'Get rotationMatrix.'
	if len(path) < 2 or not derivation.track:
		return matrix.Matrix()
	point = point.dropAxis()
	begin = path[(pointIndex + len(path) - 1) % len(path)].dropAxis()
	end = path[(pointIndex + 1) % len(path)].dropAxis()
	pointMinusBegin = point - begin
	pointMinusBeginLength = abs(pointMinusBegin)
	endMinusPoint = end - point
	endMinusPointLength = abs(endMinusPoint)
	if not derivation.closed:
		if pointIndex == 0 and endMinusPointLength > 0.0:
			return getRotationMatrixByPolar(arrayDictionary, endMinusPoint, endMinusPointLength)
		elif pointIndex == len(path) - 1 and pointMinusBeginLength > 0.0:
			return getRotationMatrixByPolar(arrayDictionary, pointMinusBegin, pointMinusBeginLength)
	if pointMinusBeginLength <= 0.0:
		print('Warning, point equals previous point in getRotationMatrix in array for:')
		print(path)
		print(pointIndex)
		print(derivation.elementNode)
		return matrix.Matrix()
	pointMinusBegin /= pointMinusBeginLength
	if endMinusPointLength <= 0.0:
		print('Warning, point equals next point in getRotationMatrix in array for:')
		print(path)
		print(pointIndex)
		print(derivation.elementNode)
		return matrix.Matrix()
	endMinusPoint /= endMinusPointLength
	averagePolar = pointMinusBegin + endMinusPoint
	averagePolarLength = abs(averagePolar)
	if averagePolarLength <= 0.0:
		print('Warning, averagePolarLength is zero in getRotationMatrix in array for:')
		print(path)
		print(pointIndex)
		print(derivation.elementNode)
		return matrix.Matrix()
	return getRotationMatrixByPolar(arrayDictionary, averagePolar, averagePolarLength)

def getRotationMatrixByPolar(arrayDictionary, polar, polarLength):
	'Get rotationMatrix by polar and polarLength.'
	polar /= polarLength
	arrayDictionary['_arrayRotation'] = math.degrees(math.atan2(polar.imag, polar.real))
	return matrix.Matrix(matrix.getDiagonalSwitchedTetragridByPolar([0, 1], polar))

def processElementNode(elementNode):
	"Process the xml element."
	processElementNodeByDerivation(None, elementNode)

def processElementNodeByDerivation(derivation, elementNode):
	'Process the xml element by derivation.'
	if derivation == None:
		derivation = ArrayDerivation(elementNode)
	if derivation.target == None:
		print('Warning, array could not get target for:')
		print(elementNode)
		return
	if len(derivation.paths) < 1:
		print('Warning, array could not get paths for:')
		print(elementNode)
		return
	groupDictionaryCopy = elementNode.attributes.copy()
	euclidean.removeElementsFromDictionary(groupDictionaryCopy, ['closed', 'paths', 'target', 'track', 'vertexes'])
	evaluate.removeIdentifiersFromDictionary(groupDictionaryCopy)
	targetMatrix = matrix.getBranchMatrixSetElementNode(derivation.target)
	elementNode.localName = 'group'
	totalIndex = 0
	for path in derivation.paths:
		addPathToGroup(derivation, groupDictionaryCopy, path, targetMatrix, totalIndex)
	elementNode.getXMLProcessor().processElementNode(elementNode)


class ArrayDerivation:
	"Class to hold array variables."
	def __init__(self, elementNode):
		'Set defaults.'
		self.closed = evaluate.getEvaluatedBoolean(True, elementNode, 'closed')
		self.elementNode = elementNode
		self.paths = evaluate.getTransformedPathsByKey([], elementNode, 'paths')
		vertexTargets = evaluate.getElementNodesByKey(elementNode, 'vertexes')
		for vertexTarget in vertexTargets:
			self.paths.append(vertexTarget.getVertexes())
		self.target = evaluate.getElementNodeByKey(elementNode, 'target')
		self.track = evaluate.getEvaluatedBoolean(True, elementNode, 'track')
		self.visible = evaluate.getEvaluatedBoolean(True, elementNode, 'visible')
