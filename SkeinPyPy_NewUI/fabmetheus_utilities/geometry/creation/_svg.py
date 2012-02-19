"""
Svg reader.

"""


from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import lineation
from fabmetheus_utilities.geometry.geometry_tools import path
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import svg_reader


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Nophead <http://hydraraptor.blogspot.com/>\nArt of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getGeometryOutput(derivation, elementNode):
	"Get vector3 vertexes from attribute dictionary."
	if derivation == None:
		derivation = SVGDerivation(elementNode)
	return getGeometryOutputBySVGReader(elementNode, derivation.svgReader)

def getGeometryOutputByArguments(arguments, elementNode):
	"Get vector3 vertexes from attribute dictionary by arguments."
	derivation = SVGDerivation()
	derivation.svgReader.parseSVG('', arguments[0])
	return getGeometryOutput(derivation, elementNode)

def getGeometryOutputBySVGReader(elementNode, svgReader):
	"Get vector3 vertexes from svgReader."
	geometryOutput = []
	for loopLayer in svgReader.loopLayers:
		for loop in loopLayer.loops:
			vector3Path = euclidean.getVector3Path(loop, loopLayer.z)
			sideLoop = lineation.SideLoop(vector3Path)
			sideLoop.rotate(elementNode)
			geometryOutput += lineation.getGeometryOutputByManipulation(elementNode, sideLoop)
	return geometryOutput

def getNewDerivation(elementNode):
	'Get new derivation.'
	return SVGDerivation(elementNode)

def processElementNode(elementNode):
	"Process the xml element."
	path.convertElementNode(elementNode, getGeometryOutput(None, elementNode))


class SVGDerivation:
	"Class to hold svg variables."
	def __init__(self, elementNode):
		'Set defaults.'
		self.svgReader = svg_reader.SVGReader()
		self.svgReader.parseSVGByElementNode(elementNode)
