"""
Boolean geometry group of solids.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.geometry_tools import dictionary
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.geometry_utilities import matrix
from fabmetheus_utilities import euclidean


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def convertContainerElementNode(elementNode, geometryOutput, xmlObject):
	"Convert the xml element to a group xml element."
	elementNode.linkObject(xmlObject)
	matrix.getBranchMatrixSetElementNode(elementNode)
	elementNode.getXMLProcessor().createChildNodes(geometryOutput['shapes'], elementNode)

def convertElementNode(elementNode, geometryOutput):
	"Convert the xml element to a group xml element."
	convertContainerElementNode(elementNode, geometryOutput, Group())

def getNewDerivation(elementNode):
	'Get new derivation.'
	return evaluate.EmptyObject(elementNode)

def processElementNode(elementNode):
	"Process the xml element."
	evaluate.processArchivable(Group, elementNode)


class Group(dictionary.Dictionary):
	"A group."
	def __init__(self):
		"Add empty lists."
		dictionary.Dictionary.__init__(self)
		self.matrix4X4 = matrix.Matrix()

	def addXMLInnerSection(self, depth, output):
		"Add xml inner section for this object."
		if self.matrix4X4 != None:
			self.matrix4X4.addXML(depth, output)
		self.addXMLSection(depth, output)

	def addXMLSection(self, depth, output):
		"Add the xml section for this object."
		pass

	def getLoops(self, importRadius, z):
		"Get loops sliced through shape."
		visibleObjects = evaluate.getVisibleObjects(self.archivableObjects)
		loops = []
		for visibleObject in visibleObjects:
			loops += visibleObject.getLoops(importRadius, z)
		return loops

	def getMatrix4X4(self):
		"Get the matrix4X4."
		return self.matrix4X4

	def getMatrixChainTetragrid(self):
		"Get the matrix chain tetragrid."
		return matrix.getTetragridTimesOther(self.elementNode.parentNode.xmlObject.getMatrixChainTetragrid(), self.matrix4X4.tetragrid)

	def getVisible(self):
		"Get visible."
		return euclidean.getBooleanFromDictionary(True, self.getAttributes(), 'visible')

	def setToElementNode(self, elementNode):
		'Set to elementNode.'
		self.elementNode = elementNode
		elementNode.parentNode.xmlObject.archivableObjects.append(self)
		matrix.getBranchMatrixSetElementNode(elementNode)
