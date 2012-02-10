"""
Boolean geometry cube.

"""


from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import solid
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.solids import triangle_mesh
from fabmetheus_utilities.vector3 import Vector3


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Nophead <http://hydraraptor.blogspot.com/>\nArt of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def addCube(elementNode, faces, inradius, vertexes):
	'Add cube by inradius.'
	square = [
		complex(-inradius.x, -inradius.y),
		complex(inradius.x, -inradius.y),
		complex(inradius.x, inradius.y),
		complex(-inradius.x, inradius.y)]
	bottomTopSquare = triangle_mesh.getAddIndexedLoops(square, vertexes, [-inradius.z, inradius.z])
	triangle_mesh.addPillarByLoops(faces, bottomTopSquare)

def getGeometryOutput(elementNode, inradius):
	'Get cube triangle mesh by inradius.'
	faces = []
	vertexes = []
	addCube(elementNode, faces, inradius, vertexes)
	return {'trianglemesh' : {'vertex' : vertexes, 'face' : faces}}

def getNewDerivation(elementNode):
	'Get new derivation.'
	return CubeDerivation(elementNode)

def processElementNode(elementNode):
	'Process the xml element.'
	evaluate.processArchivable(Cube, elementNode)


class Cube(triangle_mesh.TriangleMesh):
	'A cube object.'
	def addXMLSection(self, depth, output):
		'Add the xml section for this object.'
		pass

	def createShape(self):
		'Create the shape.'
		addCube(self.elementNode, self.faces, self.inradius, self.vertexes)

	def setToElementNode(self, elementNode):
		'Set to elementNode.'
		attributes = elementNode.attributes
		self.elementNode = elementNode
		self.inradius = CubeDerivation(elementNode).inradius
		attributes['inradius.x'] = self.inradius.x
		attributes['inradius.y'] = self.inradius.y
		attributes['inradius.z'] = self.inradius.z
		if 'inradius' in attributes:
			del attributes['inradius']
		self.createShape()
		solid.processArchiveRemoveSolid(elementNode, self.getGeometryOutput())


class CubeDerivation:
	"Class to hold cube variables."
	def __init__(self, elementNode):
		'Set defaults.'
		self.inradius = evaluate.getVector3ByPrefixes(elementNode, ['demisize', 'inradius'], Vector3(1.0, 1.0, 1.0))
		self.inradius = evaluate.getVector3ByMultiplierPrefix(elementNode, 2.0, 'size', self.inradius)
