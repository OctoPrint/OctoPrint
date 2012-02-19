"""
Boolean geometry cylinder.

"""


from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import lineation
from fabmetheus_utilities.geometry.creation import solid
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.geometry_utilities import matrix
from fabmetheus_utilities.geometry.solids import cube
from fabmetheus_utilities.geometry.solids import triangle_mesh
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import euclidean
import math

__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Nophead <http://hydraraptor.blogspot.com/>\nArt of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def addCylinder(faces, inradius, sides, topOverBottom, vertexes):
	'Add cylinder by inradius.'
	polygonBottom = euclidean.getComplexPolygonByComplexRadius(complex(inradius.x, inradius.y), sides)
	polygonTop = polygonBottom
	if topOverBottom <= 0.0:
		polygonTop = [complex()]
	elif topOverBottom != 1.0:
		polygonTop = euclidean.getComplexPathByMultiplier(topOverBottom, polygonTop)
	bottomTopPolygon = [
		triangle_mesh.getAddIndexedLoop(polygonBottom, vertexes, -inradius.z),
		triangle_mesh.getAddIndexedLoop(polygonTop, vertexes, inradius.z)]
	triangle_mesh.addPillarByLoops(faces, bottomTopPolygon)

def addCylinderOutputByEndStart(endZ, inradiusComplex, outputs, sides, start, topOverBottom=1.0):
	'Add cylinder triangle mesh by endZ, inradius and start.'
	inradius = Vector3(inradiusComplex.real, inradiusComplex.imag, 0.5 * abs(endZ - start.z))
	cylinderOutput = getGeometryOutput(inradius, sides, topOverBottom)
	vertexes = matrix.getVertexes(cylinderOutput)
	if endZ < start.z:
		for vertex in vertexes:
			vertex.z = -vertex.z
	translation = Vector3(start.x, start.y, inradius.z + min(start.z, endZ))
	euclidean.translateVector3Path(vertexes, translation)
	outputs.append(cylinderOutput)

def getGeometryOutput(inradius, sides, topOverBottom):
	'Get cylinder triangle mesh by inradius.'
	faces = []
	vertexes = []
	addCylinder(faces, inradius, sides, topOverBottom, vertexes)
	return {'trianglemesh' : {'vertex' : vertexes, 'face' : faces}}

def getNewDerivation(elementNode):
	'Get new derivation.'
	return CylinderDerivation(elementNode)

def getTopOverBottom(angle, endZ, inradiusComplex, startZ):
	'Get topOverBottom by angle in radians, endZ, inradius and start.'
	return max(1.0 - abs(endZ - startZ) * math.tan(angle) / lineation.getRadiusAverage(inradiusComplex), 0.0)

def processElementNode(elementNode):
	'Process the xml element.'
	evaluate.processArchivable(Cylinder, elementNode)


class Cylinder( cube.Cube ):
	'A cylinder object.'
	def __init__(self):
		'Add empty lists.'
		cube.Cube.__init__(self)

	def createShape(self):
		'Create the shape.'
		sides = evaluate.getSidesMinimumThreeBasedOnPrecision(self.elementNode, max(self.inradius.x, self.inradius.y))
		if self.elementNode.getCascadeBoolean(False, 'radiusAreal'):
			radiusArealizedMultiplier = euclidean.getRadiusArealizedMultiplier(sides)
			self.inradius.x *= radiusArealizedMultiplier
			self.inradius.y *= radiusArealizedMultiplier
		addCylinder(self.faces, self.inradius, sides, self.topOverBottom, self.vertexes)

	def setToElementNode(self, elementNode):
		'Set to elementNode.'
		attributes = elementNode.attributes
		self.elementNode = elementNode
		derivation = CylinderDerivation(elementNode)
		self.inradius = derivation.inradius
		self.topOverBottom = derivation.topOverBottom
		if 'inradius' in attributes:
			del attributes['inradius']
		attributes['height'] = self.inradius.z + self.inradius.z
		attributes['radius.x'] = self.inradius.x
		attributes['radius.y'] = self.inradius.y
		attributes['topOverBottom'] = self.topOverBottom
		self.createShape()
		solid.processArchiveRemoveSolid(elementNode, self.getGeometryOutput())


class CylinderDerivation:
	"Class to hold cylinder variables."
	def __init__(self, elementNode):
		'Set defaults.'
		self.inradius = evaluate.getVector3ByPrefixes(elementNode, ['demisize', 'inradius', 'radius'], Vector3(1.0, 1.0, 1.0))
		self.inradius = evaluate.getVector3ByMultiplierPrefixes(elementNode, 2.0, ['diameter', 'size'], self.inradius)
		self.inradius.z = 0.5 * evaluate.getEvaluatedFloat(self.inradius.z + self.inradius.z, elementNode, 'height')
		self.topOverBottom = evaluate.getEvaluatedFloat(1.0, elementNode, 'topOverBottom')
