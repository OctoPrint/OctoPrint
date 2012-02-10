"""
This page is in the table of contents.
The xml.py script is an import translator plugin to get a carving from an Art of Illusion xml file.

An import plugin is a script in the interpret_plugins folder which has the function getCarving.  It is meant to be run from the interpret tool.  To ensure that the plugin works on platforms which do not handle file capitalization properly, give the plugin a lower case name.

The getCarving function takes the file name of an xml file and returns the carving.

An xml file can be exported from Art of Illusion by going to the "File" menu, then going into the "Export" menu item, then picking the XML choice.  This will bring up the XML file chooser window, choose a place to save the file then click "OK".  Leave the "compressFile" checkbox unchecked.  All the objects from the scene will be exported, this plugin will ignore the light and camera.  If you want to fabricate more than one object at a time, you can have multiple objects in the Art of Illusion scene and they will all be carved, then fabricated together.

"""


from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.geometry_tools import face
from fabmetheus_utilities.geometry.geometry_utilities import boolean_geometry
from fabmetheus_utilities.geometry.geometry_utilities import boolean_solid
from fabmetheus_utilities.geometry.geometry_utilities import matrix
from fabmetheus_utilities.geometry.solids import cube
from fabmetheus_utilities.geometry.solids import cylinder
from fabmetheus_utilities.geometry.solids import group
from fabmetheus_utilities.geometry.solids import sphere
from fabmetheus_utilities.geometry.solids import triangle_mesh
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import euclidean


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Nophead <http://hydraraptor.blogspot.com/>\nArt of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCarvableObject(elementNode, globalObject, object):
	"Get new carvable object info."
	object.xmlObject = globalObject()
	object.xmlObject.elementNode = object
	object.attributes['id'] = elementNode.getFirstChildByLocalName('name').getTextContent()
	coords = elementNode.getFirstChildByLocalName('coords')
	transformElementNode = getTransformElementNode(coords, 'transformFrom')
	if len(transformElementNode.attributes) < 16:
		transformElementNode = getTransformElementNode(coords, 'transformTo')
	matrix.setElementNodeDictionaryMatrix(object, object.xmlObject.matrix4X4.getFromElementNode(transformElementNode, ''))
	return object.xmlObject

def getCarvingFromParser( xmlParser ):
	"Get the carving for the parser."
	booleanGeometry = boolean_geometry.BooleanGeometry()
	artOfIllusionElement = xmlParser.getDocumentElement()
	artOfIllusionElement.xmlObject = booleanGeometry
	euclidean.removeElementsFromDictionary( artOfIllusionElement.attributes, ['fileversion', 'xmlns:bf'] )
	sceneElement = artOfIllusionElement.getFirstChildByLocalName('Scene')
	elementNodes = sceneElement.getFirstChildByLocalName('objects').getChildElementsByLocalName('bf:Elem')
	for elementNode in elementNodes:
		processAppendElementNode(booleanGeometry.archivableObjects, elementNode, artOfIllusionElement)
	return booleanGeometry

def getTransformElementNode( coords, transformName ):
	"Get the transform attributes."
	transformElementNode = coords.getFirstChildByLocalName( transformName )
	if len( transformElementNode.attributes ) < 16:
		if 'bf:ref' in transformElementNode.attributes:
			idReference = transformElementNode.attributes['bf:ref']
			return coords.getDocumentElement().getSubChildWithID( idReference )
	return transformElementNode

def processAppendElementNode(archivableObjects, elementNode, parentNode):
	"Add the object info if it is carvable."
	if elementNode == None:
		return
	object = elementNode.getFirstChildByLocalName('object')
	if 'bf:type' not in object.attributes:
		return
	shapeType = object.attributes['bf:type']
	if shapeType not in globalCarvableClassObjectTable:
		return
	carvableClassObject = globalCarvableClassObjectTable[ shapeType ]
	archivableObject = getCarvableObject(elementNode, carvableClassObject, object)
	archivableObject.elementNode.attributes['visible'] = elementNode.attributes['visible']
	archivableObject.setToArtOfIllusionDictionary()
	archivableObject.elementNode.parentNode = parentNode
	archivableObjects.append(archivableObject)

def processElementNode(elementNode):
	"Process the xml element."
	evaluate.processArchivable(group.Group, elementNode)

def removeListArtOfIllusionFromDictionary( dictionary, scrubKeys ):
	"Remove the list and art of illusion keys from the dictionary."
	euclidean.removeElementsFromDictionary( dictionary, ['bf:id', 'bf:type'] )
	euclidean.removeElementsFromDictionary( dictionary, scrubKeys )


class BooleanSolid( boolean_solid.BooleanSolid ):
	"An Art of Illusion CSG object info."
	def setToArtOfIllusionDictionary(self):
		"Set the shape of this carvable object info."
		processAppendElementNode(self.archivableObjects, self.elementNode.getFirstChildByLocalName('obj1'), self.elementNode)
		processAppendElementNode(self.archivableObjects, self.elementNode.getFirstChildByLocalName('obj2'), self.elementNode)
		operationString = self.elementNode.attributes['operation']
		self.operationFunction = { '0': self.getUnion, '1': self.getIntersection, '2': self.getDifference, '3': self.getDifference }[ operationString ]
		if operationString == '3':
			self.archivableObjects.reverse()
		removeListArtOfIllusionFromDictionary( self.elementNode.attributes, ['operation'] )


class Cube( cube.Cube ):
	"An Art of Illusion Cube object."
	def setToArtOfIllusionDictionary(self):
		"Set the shape of this carvable object info."
		self.inradius = Vector3(
			float( self.elementNode.attributes['halfx'] ),
			float( self.elementNode.attributes['halfy'] ),
			float( self.elementNode.attributes['halfz'] ) )
		self.elementNode.attributes['inradius.x'] = self.elementNode.attributes['halfx']
		self.elementNode.attributes['inradius.y'] = self.elementNode.attributes['halfy']
		self.elementNode.attributes['inradius.z'] = self.elementNode.attributes['halfz']
		removeListArtOfIllusionFromDictionary( self.elementNode.attributes, ['halfx', 'halfy', 'halfz'] )
		self.createShape()


class Cylinder(cylinder.Cylinder):
	"An Art of Illusion Cylinder object."
	def setToArtOfIllusionDictionary(self):
		"Set the shape of this carvable object info."
		self.inradius = Vector3()
		self.inradius.x = float(self.elementNode.attributes['rx'])
		self.inradius.y = float(self.elementNode.attributes['rz'])
		self.inradius.z = float(self.elementNode.attributes['height'])
		self.topOverBottom = float(self.elementNode.attributes['ratio'])
		self.elementNode.attributes['radius.x'] = self.elementNode.attributes['rx']
		self.elementNode.attributes['radius.y'] = self.elementNode.attributes['rz']
		self.elementNode.attributes['topOverBottom'] = self.elementNode.attributes['ratio']
		xmlObject = self.elementNode.xmlObject
		xmlObject.matrix4X4 = xmlObject.matrix4X4.getOtherTimesSelf(matrix.getDiagonalSwitchedTetragrid(90.0, [0, 2]))
		removeListArtOfIllusionFromDictionary(self.elementNode.attributes, ['rx', 'rz', 'ratio'])
		self.createShape()


class Group( group.Group ):
	"An Art of Illusion Group object."
	def setToArtOfIllusionDictionary(self):
		"Set the shape of this group."
		childNodesElement = self.elementNode.parentNode.getFirstChildByLocalName('children')
		childNodes = childNodesElement.getChildElementsByLocalName('bf:Elem')
		for childNode in childNodes:
			processAppendElementNode(self.archivableObjects, childNode, self.elementNode)
		removeListArtOfIllusionFromDictionary( self.elementNode.attributes, [] )

class Sphere( sphere.Sphere ):
	"An Art of Illusion Sphere object."
	def setToArtOfIllusionDictionary(self):
		"Set the shape of this carvable object."
		self.radius = Vector3(
			float( self.elementNode.attributes['rx'] ),
			float( self.elementNode.attributes['ry'] ),
			float( self.elementNode.attributes['rz'] ) )
		self.elementNode.attributes['radius.x'] = self.elementNode.attributes['rx']
		self.elementNode.attributes['radius.y'] = self.elementNode.attributes['ry']
		self.elementNode.attributes['radius.z'] = self.elementNode.attributes['rz']
		removeListArtOfIllusionFromDictionary( self.elementNode.attributes, ['rx', 'ry', 'rz'] )
		self.createShape()


class TriangleMesh(triangle_mesh.TriangleMesh):
	"An Art of Illusion triangle mesh object."
	def setToArtOfIllusionDictionary(self):
		"Set the shape of this carvable object info."
		vertexElement = self.elementNode.getFirstChildByLocalName('vertex')
		vertexPointElements = vertexElement.getChildElementsByLocalName('bf:Elem')
		for vertexPointElement in vertexPointElements:
			coordinateElement = vertexPointElement.getFirstChildByLocalName('r')
			vertex = Vector3( float( coordinateElement.attributes['x'] ), float( coordinateElement.attributes['y'] ), float( coordinateElement.attributes['z'] ) )
			self.vertexes.append(vertex)
		edgeElement = self.elementNode.getFirstChildByLocalName('edge')
		edgeSubelements = edgeElement.getChildElementsByLocalName('bf:Elem')
		for edgeSubelementIndex in xrange( len( edgeSubelements ) ):
			edgeSubelement = edgeSubelements[ edgeSubelementIndex ]
			vertexIndexes = [ int( edgeSubelement.attributes['v1'] ), int( edgeSubelement.attributes['v2'] ) ]
			edge = face.Edge().getFromVertexIndexes( edgeSubelementIndex, vertexIndexes )
			self.edges.append( edge )
		faceElement = self.elementNode.getFirstChildByLocalName('face')
		faceSubelements = faceElement.getChildElementsByLocalName('bf:Elem')
		for faceSubelementIndex in xrange( len( faceSubelements ) ):
			faceSubelement = faceSubelements[ faceSubelementIndex ]
			edgeIndexes = [ int( faceSubelement.attributes['e1'] ), int( faceSubelement.attributes['e2'] ), int( faceSubelement.attributes['e3'] ) ]
			self.faces.append( face.Face().getFromEdgeIndexes( edgeIndexes, self.edges, faceSubelementIndex ) )
		removeListArtOfIllusionFromDictionary( self.elementNode.attributes, ['closed', 'smoothingMethod'] )


globalCarvableClassObjectTable = { 'CSGObject' : BooleanSolid, 'Cube' : Cube, 'Cylinder' : Cylinder, 'artofillusion.object.NullObject' : Group, 'Sphere' : Sphere, 'TriangleMesh' : TriangleMesh }
