"""
Boolean geometry write.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.geometry_utilities import matrix
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
import os

__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getNewDerivation(elementNode):
	'Get new derivation.'
	return WriteDerivation(elementNode)

def processElementNode(elementNode):
	"Process the xml element."
	processElementNodeByDerivation(None, elementNode)

def processElementNodeByDerivation(derivation, elementNode):
	'Process the xml element by derivation.'
	if derivation == None:
		derivation = WriteDerivation(elementNode)
	if len(derivation.targets) < 1:
		print('Warning, processElementNode in write could not get targets for:')
		print(elementNode)
		return
	fileNames = []
	for target in derivation.targets:
		writeElementNode(derivation, fileNames, target)

def writeElementNode(derivation, fileNames, target):
	"Write a quantity of the target."
	xmlObject = target.xmlObject
	if xmlObject == None:
		print('Warning, writeTarget in write could not get xmlObject for:')
		print(target)
		print(derivation.elementNode)
		return
	parserDirectory = os.path.dirname(derivation.elementNode.getOwnerDocument().fileName)
	absoluteFolderDirectory = os.path.abspath(os.path.join(parserDirectory, derivation.folderName))
	if '/models' not in absoluteFolderDirectory:
		print('Warning, models/ was not in the absolute file path, so for security nothing will be done for:')
		print(derivation.elementNode)
		print('For which the absolute folder path is:')
		print(absoluteFolderDirectory)
		print('The write tool can only write a file which has models/ in the file path.')
		print('To write the file, move the file into a folder called model/ or a subfolder which is inside the model folder tree.')
		return
	quantity = evaluate.getEvaluatedInt(1, target, 'quantity')
	for itemIndex in xrange(quantity):
		writeXMLObject(absoluteFolderDirectory, derivation, fileNames, target, xmlObject)

def writeXMLObject(absoluteFolderDirectory, derivation, fileNames, target, xmlObject):
	"Write one instance of the xmlObject."
	extension = evaluate.getEvaluatedString(xmlObject.getFabricationExtension(), derivation.elementNode, 'extension')
	fileNameRoot = derivation.fileName
	if fileNameRoot == '':
		fileNameRoot = evaluate.getEvaluatedString('', target, 'name')
		fileNameRoot = evaluate.getEvaluatedString(fileNameRoot, target, 'id')
		fileNameRoot += derivation.suffix
	fileName = '%s.%s' % (fileNameRoot, extension)
	suffixIndex = 2
	while fileName in fileNames:
		fileName = '%s_%s.%s' % (fileNameRoot, suffixIndex, extension)
		suffixIndex += 1
	absoluteFileName = os.path.join(absoluteFolderDirectory, fileName)
	fileNames.append(fileName)
	archive.makeDirectory(absoluteFolderDirectory)
	if not derivation.writeMatrix:
		xmlObject.matrix4X4 = matrix.Matrix()
	print('The write tool generated the file:')
	print(absoluteFileName)
	archive.writeFileText(absoluteFileName, xmlObject.getFabricationText(derivation.addLayerTemplate))


class WriteDerivation:
	"Class to hold write variables."
	def __init__(self, elementNode):
		'Set defaults.'
		self.addLayerTemplate = evaluate.getEvaluatedBoolean(False, elementNode, 'addLayerTemplate')
		self.elementNode = elementNode
		self.fileName = evaluate.getEvaluatedString('', elementNode, 'file')
		self.folderName = evaluate.getEvaluatedString('', elementNode, 'folder')
		self.suffix = evaluate.getEvaluatedString('', elementNode, 'suffix')
		self.targets = evaluate.getElementNodesByKey(elementNode, 'target')
		self.writeMatrix = evaluate.getEvaluatedBoolean(True, elementNode, 'writeMatrix')
