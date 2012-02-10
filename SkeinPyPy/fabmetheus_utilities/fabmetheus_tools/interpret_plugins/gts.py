"""
This page is in the table of contents.
The gts.py script is an import translator plugin to get a carving from an gts file.

An import plugin is a script in the interpret_plugins folder which has the function getCarving.  It is meant to be run from the interpret tool.  To ensure that the plugin works on platforms which do not handle file capitalization properly, give the plugin a lower case name.

The getCarving function takes the file name of an gts file and returns the carving.

The GNU Triangulated Surface (.gts) format is described at:
http://gts.sourceforge.net/reference/gts-surfaces.html#GTS-SURFACE-WRITE

Quoted from http://gts.sourceforge.net/reference/gts-surfaces.html#GTS-SURFACE-WRITE
"All the lines beginning with GTS_COMMENTS (#!) are ignored. The first line contains three unsigned integers separated by spaces. The first integer is the number of vertexes, nv, the second is the number of edges, ne and the third is the number of faces, nf.

Follows nv lines containing the x, y and z coordinates of the vertexes. Follows ne lines containing the two indices (starting from one) of the vertexes of each edge. Follows nf lines containing the three ordered indices (also starting from one) of the edges of each face.

The format described above is the least common denominator to all GTS files. Consistent with an object-oriented approach, the GTS file format is extensible. Each of the lines of the file can be extended with user-specific attributes accessible through the read() and write() virtual methods of each of the objects written (surface, vertexes, edges or faces). When read with different object classes, these extra attributes are just ignored."

"""


from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.geometry_tools import face
from fabmetheus_utilities.geometry.solids import triangle_mesh
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import archive
from fabmetheus_utilities import gcodec

__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Nophead <http://hydraraptor.blogspot.com/>\nArt of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCarving(fileName):
	"Get the carving for the gts file."
	return getFromGNUTriangulatedSurfaceText( archive.getFileText(fileName), triangle_mesh.TriangleMesh() )

def getFromGNUTriangulatedSurfaceText( gnuTriangulatedSurfaceText, triangleMesh ):
	"Initialize from a GNU Triangulated Surface Text."
	if gnuTriangulatedSurfaceText == '':
		return None
	lines = archive.getTextLines( gnuTriangulatedSurfaceText )
	linesWithoutComments = []
	for line in lines:
		if len(line) > 0:
			firstCharacter = line[0]
			if firstCharacter != '#' and firstCharacter != '!':
				linesWithoutComments.append(line)
	splitLine = linesWithoutComments[0].split()
	numberOfVertexes = int( splitLine[0] )
	numberOfEdges = int(splitLine[1])
	numberOfFaces = int( splitLine[2] )
	faceTriples = []
	for vertexIndex in xrange( numberOfVertexes ):
		line = linesWithoutComments[ vertexIndex + 1 ]
		splitLine = line.split()
		vertex = Vector3( float( splitLine[0] ), float(splitLine[1]), float( splitLine[2] ) )
		triangleMesh.vertexes.append(vertex)
	edgeStart = numberOfVertexes + 1
	for edgeIndex in xrange( numberOfEdges ):
		line = linesWithoutComments[ edgeIndex + edgeStart ]
		splitLine = line.split()
		vertexIndexes = []
		for word in splitLine[ : 2 ]:
			vertexIndexes.append( int(word) - 1 )
		edge = face.Edge().getFromVertexIndexes( edgeIndex, vertexIndexes )
		triangleMesh.edges.append( edge )
	faceStart = edgeStart + numberOfEdges
	for faceIndex in xrange( numberOfFaces ):
		line = linesWithoutComments[ faceIndex + faceStart ]
		splitLine = line.split()
		edgeIndexes = []
		for word in splitLine[ : 3 ]:
			edgeIndexes.append( int(word) - 1 )
		triangleMesh.faces.append( face.Face().getFromEdgeIndexes( edgeIndexes, triangleMesh.edges, faceIndex ) )
	return triangleMesh
