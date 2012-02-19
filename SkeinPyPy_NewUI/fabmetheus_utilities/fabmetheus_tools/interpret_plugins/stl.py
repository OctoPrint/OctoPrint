"""
This page is in the table of contents.
The stl.py script is an import translator plugin to get a carving from an stl file.

An import plugin is a script in the interpret_plugins folder which has the function getCarving.  It is meant to be run from the interpret tool.  To ensure that the plugin works on platforms which do not handle file capitalization properly, give the plugin a lower case name.

The getCarving function takes the file name of an stl file and returns the carving.

STL is an inferior triangle surface format, described at:
http://en.wikipedia.org/wiki/STL_(file_format)

A good triangle surface format is the GNU Triangulated Surface format which is described at:
http://gts.sourceforge.net/reference/gts-surfaces.html#GTS-SURFACE-WRITE

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


def addFacesGivenBinary( stlData, triangleMesh, vertexIndexTable ):
	"Add faces given stl binary."
	numberOfVertexes = ( len( stlData ) - 84 ) / 50
	vertexes = []
	for vertexIndex in xrange( numberOfVertexes ):
		byteIndex = 84 + vertexIndex * 50
		vertexes.append( getVertexGivenBinary( byteIndex + 12, stlData ) )
		vertexes.append( getVertexGivenBinary( byteIndex + 24, stlData ) )
		vertexes.append( getVertexGivenBinary( byteIndex + 36, stlData ) )
	addFacesGivenVertexes( triangleMesh, vertexIndexTable, vertexes )

def addFacesGivenText( stlText, triangleMesh, vertexIndexTable ):
	"Add faces given stl text."
	lines = archive.getTextLines( stlText )
	vertexes = []
	for line in lines:
		if line.find('vertex') != - 1:
			vertexes.append( getVertexGivenLine(line) )
	addFacesGivenVertexes( triangleMesh, vertexIndexTable, vertexes )

def addFacesGivenVertexes( triangleMesh, vertexIndexTable, vertexes ):
	"Add faces given stl text."
	for vertexIndex in xrange( 0, len(vertexes), 3 ):
		triangleMesh.faces.append( getFaceGivenLines( triangleMesh, vertexIndex, vertexIndexTable, vertexes ) )

def getCarving(fileName=''):
	"Get the triangle mesh for the stl file."
	if fileName == '':
		return None
	stlData = archive.getFileText(fileName, True, 'rb')
	if stlData == '':
		return None
	triangleMesh = triangle_mesh.TriangleMesh()
	vertexIndexTable = {}
	numberOfVertexStrings = stlData.count('vertex')
	requiredVertexStringsForText = max( 2, len( stlData ) / 8000 )
	if numberOfVertexStrings > requiredVertexStringsForText:
		addFacesGivenText( stlData, triangleMesh, vertexIndexTable )
	else:
#	A binary stl should never start with the word "solid".  Because this error is common the file is been parsed as binary regardless.
		addFacesGivenBinary( stlData, triangleMesh, vertexIndexTable )
	return triangleMesh

def getFaceGivenLines( triangleMesh, vertexStartIndex, vertexIndexTable, vertexes ):
	"Add face given line index and lines."
	faceGivenLines = face.Face()
	faceGivenLines.index = len( triangleMesh.faces )
	for vertexIndex in xrange( vertexStartIndex, vertexStartIndex + 3 ):
		vertex = vertexes[vertexIndex]
		vertexUniqueIndex = len( vertexIndexTable )
		if str(vertex) in vertexIndexTable:
			vertexUniqueIndex = vertexIndexTable[ str(vertex) ]
		else:
			vertexIndexTable[ str(vertex) ] = vertexUniqueIndex
			triangleMesh.vertexes.append(vertex)
		faceGivenLines.vertexIndexes.append( vertexUniqueIndex )
	return faceGivenLines

def getFloat(floatString):
	"Get the float, replacing commas if necessary because an inferior program is using a comma instead of a point for the decimal point."
	try:
		return float(floatString)
	except:
		return float( floatString.replace(',', '.') )

def getFloatGivenBinary( byteIndex, stlData ):
	"Get vertex given stl vertex line."
	return unpack('f', stlData[ byteIndex : byteIndex + 4 ] )[0]

def getVertexGivenBinary( byteIndex, stlData ):
	"Get vertex given stl vertex line."
	return Vector3( getFloatGivenBinary( byteIndex, stlData ), getFloatGivenBinary( byteIndex + 4, stlData ), getFloatGivenBinary( byteIndex + 8, stlData ) )

def getVertexGivenLine(line):
	"Get vertex given stl vertex line."
	splitLine = line.split()
	return Vector3( getFloat(splitLine[1]), getFloat( splitLine[2] ), getFloat( splitLine[3] ) )
