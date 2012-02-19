"""
This page is in the table of contents.
The obj.py script is an import translator plugin to get a carving from an obj file.

An example obj file is box.obj in the models folder.

An import plugin is a script in the interpret_plugins folder which has the function getCarving.  It is meant to be run from the interpret tool.  To ensure that the plugin works on platforms which do not handle file capitalization properly, give the plugin a lower case name.

The getCarving function takes the file name of an obj file and returns the carving.

From wikipedia, OBJ (or .OBJ) is a geometry definition file format first developed by Wavefront Technologies for its Advanced Visualizer animation package:
http://en.wikipedia.org/wiki/Obj

The Object File specification is at:
http://local.wasp.uwa.edu.au/~pbourke/dataformats/obj/

An excellent link page about obj files is at:
http://people.sc.fsu.edu/~burkardt/data/obj/obj.html

"""


from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.geometry_tools import face
from fabmetheus_utilities.geometry.solids import triangle_mesh
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import archive
from fabmetheus_utilities import gcodec
from struct import unpack

__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Nophead <http://hydraraptor.blogspot.com/>\nArt of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def addFacesGivenText( objText, triangleMesh ):
	"Add faces given obj text."
	lines = archive.getTextLines( objText )
	for line in lines:
		splitLine = line.split()
		firstWord = gcodec.getFirstWord(splitLine)
		if firstWord == 'v':
			triangleMesh.vertexes.append( getVertexGivenLine(line) )
		elif firstWord == 'f':
			triangleMesh.faces.append( getFaceGivenLine( line, triangleMesh ) )

def getCarving(fileName=''):
	"Get the triangle mesh for the obj file."
	if fileName == '':
		return None
	objText = archive.getFileText(fileName, True, 'rb')
	if objText == '':
		return None
	triangleMesh = triangle_mesh.TriangleMesh()
	addFacesGivenText(objText, triangleMesh)
	return triangleMesh

def getFaceGivenLine( line, triangleMesh ):
	"Add face given line index and lines."
	faceGivenLine = face.Face()
	faceGivenLine.index = len( triangleMesh.faces )
	splitLine = line.split()
	for vertexStringIndex in xrange( 1, 4 ):
		vertexString = splitLine[ vertexStringIndex ]
		vertexStringWithSpaces = vertexString.replace('/', ' ')
		vertexStringSplit = vertexStringWithSpaces.split()
		vertexIndex = int( vertexStringSplit[0] ) - 1
		faceGivenLine.vertexIndexes.append(vertexIndex)
	return faceGivenLine

def getVertexGivenLine(line):
	"Get vertex given obj vertex line."
	splitLine = line.split()
	return Vector3( float(splitLine[1]), float( splitLine[2] ), float( splitLine[3] ) )
