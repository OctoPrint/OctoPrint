"""
Boolean geometry group of solids.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.solids import group
from fabmetheus_utilities import xml_simple_reader
from fabmetheus_utilities import xml_simple_writer
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import settings
import cStringIO
import os


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def appendAttributes(fromElementNode, toElementNode):
	'Append the attributes from the child nodes of fromElementNode to the attributes of toElementNode.'
	for childNode in fromElementNode.childNodes:
		toElementNode.attributes.update(evaluate.removeIdentifiersFromDictionary(childNode.attributes.copy()))

def getNewDerivation(elementNode):
	'Get new derivation.'
	return ImportDerivation(elementNode)

def getXMLFromCarvingFileName(fileName):
	'Get xml text from xml text.'
	carving = fabmetheus_interpret.getCarving(fileName)
	if carving == None:
		return ''
	output = xml_simple_writer.getBeginGeometryXMLOutput()
	carving.addXML(0, output)
	return xml_simple_writer.getEndGeometryXMLString(output)

def processElementNode(elementNode):
	"Process the xml element."
	processElementNodeByDerivation(None, elementNode)

def processElementNodeByDerivation(derivation, elementNode):
	'Process the xml element by derivation.'
	if derivation == None:
		derivation = ImportDerivation(elementNode)
	if derivation.fileName == None:
		return
	parserFileName = elementNode.getOwnerDocument().fileName
	absoluteFileName = archive.getAbsoluteFolderPath(parserFileName, derivation.fileName)
	if 'models/' not in absoluteFileName:
		print('Warning, models/ was not in the absolute file path, so for security nothing will be done for:')
		print(elementNode)
		print('For which the absolute file path is:')
		print(absoluteFileName)
		print('The import tool can only read a file which has models/ in the file path.')
		print('To import the file, move the file into a folder called model/ or a subfolder which is inside the model folder tree.')
		return
	xmlText = ''
	if derivation.fileName.endswith('.xml'):
		xmlText = archive.getFileText(absoluteFileName)
	else:
		xmlText = getXMLFromCarvingFileName(absoluteFileName)
	print('The import tool is opening the file:')
	print(absoluteFileName)
	if xmlText == '':
		print('The file %s could not be found by processElementNode in import.' % derivation.fileName)
		return
	if derivation.importName == None:
		elementNode.attributes['_importName'] = archive.getUntilDot(derivation.fileName)
		if derivation.basename:
			elementNode.attributes['_importName'] = os.path.basename(elementNode.attributes['_importName'])
	xml_simple_reader.createAppendByText(elementNode, xmlText)
	if derivation.appendDocumentElement:
		appendAttributes(elementNode, elementNode.getDocumentElement())
	if derivation.appendElement:
		appendAttributes(elementNode, elementNode)
	elementNode.localName = 'group'
	evaluate.processArchivable(group.Group, elementNode)


class ImportDerivation:
	"Class to hold import variables."
	def __init__(self, elementNode):
		'Set defaults.'
		self.appendDocumentElement = evaluate.getEvaluatedBoolean(False, elementNode, 'appendDocumentElement')
		self.appendElement = evaluate.getEvaluatedBoolean(False, elementNode, 'appendElement')
		self.basename = evaluate.getEvaluatedBoolean(True, elementNode, 'basename')
		self.elementNode = elementNode
		self.fileName = evaluate.getEvaluatedString('', elementNode, 'file')
		self.importName = evaluate.getEvaluatedString(None, elementNode, '_importName')
