"""
This page is in the table of contents.
The svg.py script is an import translator plugin to get a carving from an svg file.  This script will read an svg file made by skeinforge or by inkscape.

An example inkscape svg file is inkscape_star.svg in the models folder.

An import plugin is a script in the interpret_plugins folder which has the function getCarving.  It is meant to be run from the interpret tool.  To ensure that the plugin works on platforms which do not handle file capitalization properly, give the plugin a lower case name.

The getCarving function takes the file name of an svg file and returns the carving.

"""


from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.svg_reader import SVGReader
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import svg_writer
from fabmetheus_utilities import xml_simple_writer
import math


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Nophead <http://hydraraptor.blogspot.com/>\nArt of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCarving(fileName=''):
	'Get the triangle mesh for the gts file.'
	carving = SVGCarving()
	carving.parseSVG(fileName, archive.getFileText(fileName))
	return carving


class SVGCarving:
	'An svg carving.'
	def __init__(self):
		'Add empty lists.'
		self.layerHeight = 1.0
		self.maximumZ = - 987654321.0
		self.minimumZ = 987654321.0
		self.svgReader = SVGReader()

	def __repr__(self):
		'Get the string representation of this carving.'
		return self.getCarvedSVG()

	def addXML(self, depth, output):
		'Add xml for this object.'
		xml_simple_writer.addXMLFromObjects(depth, self.svgReader.loopLayers, output)

	def getCarveBoundaryLayers(self):
		'Get the  boundary layers.'
		return self.svgReader.loopLayers

	def getCarveCornerMaximum(self):
		'Get the corner maximum of the vertexes.'
		return self.cornerMaximum

	def getCarveCornerMinimum(self):
		'Get the corner minimum of the vertexes.'
		return self.cornerMinimum

	def getCarvedSVG(self):
		'Get the carved svg text.'
		return svg_writer.getSVGByLoopLayers(True, self, self.svgReader.loopLayers)

	def getCarveLayerHeight(self):
		'Get the layer height.'
		return self.layerHeight

	def getFabmetheusXML(self):
		'Return the fabmetheus XML.'
		return None

	def getInterpretationSuffix(self):
		'Return the suffix for a carving.'
		return 'svg'

	def parseSVG(self, fileName, svgText):
		'Parse SVG text and store the layers.'
		if svgText == '':
			return
		self.fileName = fileName
		self.svgReader.parseSVG(fileName, svgText)
		self.layerHeight = euclidean.getFloatDefaultByDictionary(
			self.layerHeight, self.svgReader.sliceDictionary, 'layerHeight')
		self.cornerMaximum = Vector3(-987654321.0, -987654321.0, self.maximumZ)
		self.cornerMinimum = Vector3(987654321.0, 987654321.0, self.minimumZ)
		svg_writer.setSVGCarvingCorners(
			self.cornerMaximum, self.cornerMinimum, self.layerHeight, self.svgReader.loopLayers)

	def setCarveImportRadius(self, importRadius):
		'Set the import radius.'
		pass

	def setCarveIsCorrectMesh(self, isCorrectMesh):
		'Set the is correct mesh flag.'
		pass

	def setCarveLayerHeight(self, layerHeight):
		'Set the layer height.'
		self.layerHeight = layerHeight
