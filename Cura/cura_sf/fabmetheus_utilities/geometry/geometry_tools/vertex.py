"""
Vertex of a triangle mesh.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities import xml_simple_reader


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def addGeometryList(elementNode, vertexes):
	"Add vertex elements to an xml element."
	for vertex in vertexes:
		vertexElement = getUnboundVertexElement(vertex)
		vertexElement.parentNode = elementNode
		elementNode.childNodes.append( vertexElement )

def addVertexToAttributes(attributes, vertex):
	"Add to the attribute dictionary."
	if vertex.x != 0.0:
		attributes['x'] = str(vertex.x)
	if vertex.y != 0.0:
		attributes['y'] = str(vertex.y)
	if vertex.z != 0.0:
		attributes['z'] = str(vertex.z)

def getUnboundVertexElement(vertex):
	"Add vertex element to an xml element."
	vertexElement = xml_simple_reader.ElementNode()
	addVertexToAttributes(vertexElement.attributes, vertex)
	vertexElement.localName = 'vertex'
	return vertexElement

def processElementNode(elementNode):
	"Process the xml element."
	elementNode.parentNode.xmlObject.vertexes.append(evaluate.getVector3FromElementNode(elementNode))
