"""
This page is in the table of contents.
The slc.py script is an import translator plugin to get a carving from an [http://rapid.lpt.fi/archives/rp-ml-1999/0713.html slc file].

An import plugin is a script in the interpret_plugins folder which has the function getCarving.  It is meant to be run from the interpret tool.  To ensure that the plugin works on platforms which do not handle file capitalization properly, give the plugin a lower case name.

The getCarving function takes the file name of an slc file and returns the carving.

"""


from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import svg_writer
from struct import unpack
import math
import sys


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Nophead <http://hydraraptor.blogspot.com/>\nArt of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCarving(fileName=''):
	"Get the triangle mesh for the slc file."
	carving = SLCCarving()
	carving.readFile(fileName)
	return carving

def getLittleEndianFloatGivenFile( file ):
	"Get little endian float given a file."
	return unpack('<f', file.read(4) )[0]

def getLittleEndianUnsignedLongGivenFile( file ):
	"Get little endian float given a file."
	return unpack('<L', file.read(4) )[0]

def getPointsFromFile( numPoints, file ):
	"Process the vertice points for a given boundary."
	points = []
	for pointIndex in xrange( numPoints ):
		x = getLittleEndianFloatGivenFile( file )
		y = getLittleEndianFloatGivenFile( file )
		points.append( complex(x, y) )
	return points

def readHeader( file ):
	"Read the slc header."
	while ord( file.read( 1 ) ) != 0x1A:
		pass


class SampleTableEntry:
	"Sample table entry."
	def __init__( self, file ):
		"Read in the sampling table section. It contains a table length (byte) and the table entries."
		self.min_z_level = getLittleEndianFloatGivenFile( file )
		self.layer_thickness = getLittleEndianFloatGivenFile( file )
		self.beam_comp = getLittleEndianFloatGivenFile( file )
		getLittleEndianFloatGivenFile( file )

	def __repr__(self):
		"Get the string representation of this sample table entry."
		return '%s, %s, %s' % ( self.min_z_level, self.layer_thickness, self.beam_comp )


class SLCCarving:
	"An slc carving."
	def __init__(self):
		"Add empty lists."
		self.layerHeight = None
		self.loopLayers = []
		self.maximumZ = - 987654321.0
		self.minimumZ = 987654321.0
	
	def __repr__(self):
		"Get the string representation of this carving."
		return self.getCarvedSVG()

	def addXML(self, depth, output):
		"Add xml for this object."
		xml_simple_writer.addXMLFromObjects(depth, self.loopLayers, output)

	def getCarveBoundaryLayers(self):
		"Get the  boundary layers."
		return self.loopLayers

	def getCarveCornerMaximum(self):
		"Get the corner maximum of the vertexes."
		return self.cornerMaximum

	def getCarveCornerMinimum(self):
		"Get the corner minimum of the vertexes."
		return self.cornerMinimum

	def getCarvedSVG(self):
		"Get the carved svg text."
		if len(self.loopLayers) < 1:
			return ''
		decimalPlaces = max(0, 2 - int(math.floor(math.log10(self.layerHeight))))
		self.svgWriter = svg_writer.SVGWriter(True, self.cornerMaximum, self.cornerMinimum, decimalPlaces, self.layerHeight)
		return self.svgWriter.getReplacedSVGTemplate(self.fileName, self.loopLayers, 'basic')

	def getCarveLayerHeight(self):
		"Get the layer height."
		return self.layerHeight

	def getFabmetheusXML(self):
		"Return the fabmetheus XML."
		return None

	def getInterpretationSuffix(self):
		"Return the suffix for a carving."
		return 'svg'

	def processContourLayers( self, file ):
		"Process a contour layer at a time until the top of the part."
		while True:
			minLayer = getLittleEndianFloatGivenFile( file )
			numContours = getLittleEndianUnsignedLongGivenFile( file )
			if numContours == 0xFFFFFFFF:
				return
			loopLayer = euclidean.LoopLayer( minLayer )
			self.loopLayers.append( loopLayer )
			for contourIndex in xrange( numContours ):
				numPoints = getLittleEndianUnsignedLongGivenFile( file )
				numGaps = getLittleEndianUnsignedLongGivenFile( file )
				if numPoints > 2:
					loopLayer.loops.append( getPointsFromFile( numPoints, file ) )

	def readFile( self, fileName ):
		"Read SLC and store the layers."
		self.fileName = fileName
		pslcfile = open( fileName, 'rb')
		readHeader( pslcfile )
		pslcfile.read( 256 ) #Go past the 256 byte 3D Reserved Section.
		self.readTableEntry( pslcfile )
		self.processContourLayers( pslcfile )
		pslcfile.close()
		self.cornerMaximum = Vector3(-987654321.0, -987654321.0, self.maximumZ)
		self.cornerMinimum = Vector3(987654321.0, 987654321.0, self.minimumZ)
		for loopLayer in self.loopLayers:
			for loop in loopLayer.loops:
				for point in loop:
					pointVector3 = Vector3(point.real, point.imag, loopLayer.z)
					self.cornerMaximum.maximize(pointVector3)
					self.cornerMinimum.minimize(pointVector3)
		halfLayerThickness = 0.5 * self.layerHeight
		self.cornerMaximum.z += halfLayerThickness
		self.cornerMinimum.z -= halfLayerThickness

	def readTableEntry( self, file ):
		"Read in the sampling table section. It contains a table length (byte) and the table entries."
		tableEntrySize = ord( file.read( 1 ) )
		if tableEntrySize == 0:
			print("Sampling table size is zero!")
			exit()
		for index in xrange( tableEntrySize ):
			sampleTableEntry = SampleTableEntry( file )
			self.layerHeight = sampleTableEntry.layerHeight

	def setCarveImportRadius( self, importRadius ):
		"Set the import radius."
		pass

	def setCarveIsCorrectMesh( self, isCorrectMesh ):
		"Set the is correct mesh flag."
		pass

	def setCarveLayerHeight( self, layerHeight ):
		"Set the layer height."
		pass


def main():
	"Display the inset dialog."
	if len(sys.argv) > 1:
		getCarving(' '.join(sys.argv[1 :]))

if __name__ == "__main__":
	main()
