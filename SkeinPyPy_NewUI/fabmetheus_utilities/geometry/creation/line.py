"""
Square path.

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


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getGeometryOutput(derivation, elementNode):
	"Get vector3 vertexes from attribute dictionary."
	if derivation == None:
		derivation = LineDerivation(elementNode)
	endMinusStart = derivation.end - derivation.start
	endMinusStartLength = abs(endMinusStart)
	if endMinusStartLength <= 0.0:
		print('Warning, end is the same as start in getGeometryOutput in line for:')
		print(derivation.start)
		print(derivation.end)
		print(elementNode)
		return None
	typeStringTwoCharacters = derivation.typeString.lower()[: 2]
	elementNode.attributes['closed'] = str(derivation.closed)
	if derivation.step == None and derivation.steps == None:
		return lineation.getGeometryOutputByLoop(elementNode, lineation.SideLoop([derivation.start, derivation.end]))
	loop = [derivation.start]
	if derivation.step != None and derivation.steps != None:
		stepVector = derivation.step / endMinusStartLength * endMinusStart
		derivation.end = derivation.start + stepVector * derivation.steps
		return getGeometryOutputByStep(elementNode, derivation.end, loop, derivation.steps, stepVector)
	if derivation.step == None:
		stepVector = endMinusStart / derivation.steps
		return getGeometryOutputByStep(elementNode, derivation.end, loop, derivation.steps, stepVector)
	endMinusStartLengthOverStep = endMinusStartLength / derivation.step
	if typeStringTwoCharacters == 'av':
		derivation.steps = max(1.0, round(endMinusStartLengthOverStep))
		stepVector = derivation.step / endMinusStartLength * endMinusStart
		derivation.end = derivation.start + stepVector * derivation.steps
		return getGeometryOutputByStep(elementNode, derivation.end, loop, derivation.steps, stepVector)
	if typeStringTwoCharacters == 'ma':
		derivation.steps = math.ceil(endMinusStartLengthOverStep)
		if derivation.steps < 1.0:
			return lineation.getGeometryOutputByLoop(elementNode, lineation.SideLoop([derivation.start, derivation.end]))
		stepVector = endMinusStart / derivation.steps
		return getGeometryOutputByStep(elementNode, derivation.end, loop, derivation.steps, stepVector)
	if typeStringTwoCharacters == 'mi':
		derivation.steps = math.floor(endMinusStartLengthOverStep)
		if derivation.steps < 1.0:
			return lineation.getGeometryOutputByLoop(elementNode, lineation.SideLoop(loop))
		stepVector = endMinusStart / derivation.steps
		return getGeometryOutputByStep(elementNode, derivation.end, loop, derivation.steps, stepVector)
	print('Warning, the step type was not one of (average, maximum or minimum) in getGeometryOutput in line for:')
	print(derivation.typeString)
	print(elementNode)
	loop.append(derivation.end)
	return lineation.getGeometryOutputByLoop(elementNode, lineation.SideLoop(loop))

def getGeometryOutputByArguments(arguments, elementNode):
	"Get vector3 vertexes from attribute dictionary by arguments."
	evaluate.setAttributesByArguments(['start', 'end', 'step'], arguments, elementNode)
	return getGeometryOutput(None, elementNode)

def getGeometryOutputByStep(elementNode, end, loop, steps, stepVector):
	"Get line geometry output by the end, loop, steps and stepVector."
	stepsFloor = int(math.floor(abs(steps)))
	for stepIndex in xrange(1, stepsFloor):
		loop.append(loop[stepIndex - 1] + stepVector)
	loop.append(end)
	return lineation.getGeometryOutputByLoop(elementNode, lineation.SideLoop(loop))

def getNewDerivation(elementNode):
	'Get new derivation.'
	return LineDerivation(elementNode)

def processElementNode(elementNode):
	"Process the xml element."
	path.convertElementNode(elementNode, getGeometryOutput(None, elementNode))


class LineDerivation:
	"Class to hold line variables."
	def __init__(self, elementNode):
		'Set defaults.'
		self.closed = evaluate.getEvaluatedBoolean(False, elementNode, 'closed')
		self.end = evaluate.getVector3ByPrefix(Vector3(), elementNode, 'end')
		self.start = evaluate.getVector3ByPrefix(Vector3(), elementNode, 'start')
		self.step = evaluate.getEvaluatedFloat(None, elementNode, 'step')
		self.steps = evaluate.getEvaluatedFloat(None, elementNode, 'steps')
		self.typeMenuRadioStrings = 'average maximum minimum'.split()
		self.typeString = evaluate.getEvaluatedString('minimum', elementNode, 'type')
