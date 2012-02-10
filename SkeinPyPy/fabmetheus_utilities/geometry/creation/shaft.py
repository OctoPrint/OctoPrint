"""
Shaft path.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import lineation
from fabmetheus_utilities.geometry.geometry_tools import path
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities import euclidean
import math


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getGeometryOutput(derivation, elementNode):
	"Get vector3 vertexes from attribute dictionary."
	if derivation == None:
		derivation = ShaftDerivation(elementNode)
	shaftPath = getShaftPath(derivation.depthBottom, derivation.depthTop, derivation.radius, derivation.sides)
	return lineation.getGeometryOutputByLoop(elementNode, lineation.SideLoop(shaftPath))

def getGeometryOutputByArguments(arguments, elementNode):
	"Get vector3 vertexes from attribute dictionary by arguments."
	evaluate.setAttributesByArguments(['radius', 'sides'], arguments, elementNode)
	return getGeometryOutput(None, elementNode)

def getNewDerivation(elementNode):
	'Get new derivation.'
	return ShaftDerivation(elementNode)

def getShaftPath(depthBottom, depthTop, radius, sides):
	'Get shaft with the option of a flat on the top and/or bottom.'
	if radius <= 0.0:
		return []
	sideAngle = 2.0 * math.pi / float(abs(sides))
	startAngle = 0.5 * sideAngle
	endAngle = math.pi - 0.1 * sideAngle
	shaftProfile = []
	while startAngle < endAngle:
		unitPolar = euclidean.getWiddershinsUnitPolar(startAngle)
		shaftProfile.append(unitPolar * radius)
		startAngle += sideAngle
	if abs(sides) % 2 == 1:
		shaftProfile.append(complex(-radius, 0.0))
	horizontalBegin = radius - depthTop
	horizontalEnd = depthBottom - radius
	shaftProfile = euclidean.getHorizontallyBoundedPath(horizontalBegin, horizontalEnd, shaftProfile)
	for shaftPointIndex, shaftPoint in enumerate(shaftProfile):
		shaftProfile[shaftPointIndex] = complex(shaftPoint.imag, shaftPoint.real)
	shaftPath = euclidean.getVector3Path(euclidean.getMirrorPath(shaftProfile))
	if sides > 0:
		shaftPath.reverse()
	return shaftPath

def processElementNode(elementNode):
	"Process the xml element."
	path.convertElementNode(elementNode, getGeometryOutput(None, elementNode))


class ShaftDerivation:
	"Class to hold shaft variables."
	def __init__(self, elementNode):
		'Set defaults.'
		self.depthBottomOverRadius = evaluate.getEvaluatedFloat(0.0, elementNode, 'depthBottomOverRadius')
		self.depthTopOverRadius = evaluate.getEvaluatedFloat(0.0, elementNode, 'depthOverRadius')
		self.depthTopOverRadius = evaluate.getEvaluatedFloat(
			self.depthTopOverRadius, elementNode, 'depthTopOverRadius')
		self.radius = evaluate.getEvaluatedFloat(1.0, elementNode, 'radius')
		self.sides = evaluate.getEvaluatedInt(4, elementNode, 'sides')
		self.depthBottom = self.radius * self.depthBottomOverRadius
		self.depthBottom = evaluate.getEvaluatedFloat(self.depthBottom, elementNode, 'depthBottom')
		self.depthTop = self.radius * self.depthTopOverRadius
		self.depthTop = evaluate.getEvaluatedFloat(self.depthTop, elementNode, 'depth')
		self.depthTop = evaluate.getEvaluatedFloat(self.depthTop, elementNode, 'depthTop')
