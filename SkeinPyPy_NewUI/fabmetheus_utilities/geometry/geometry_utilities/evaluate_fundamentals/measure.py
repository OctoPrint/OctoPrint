"""
Boolean geometry utilities.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import euclidean
import math


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def _getAccessibleAttribute(attributeName):
	'Get the accessible attribute.'
	if attributeName in globalAccessibleAttributeDictionary:
		return globalAccessibleAttributeDictionary[attributeName]
	return None

def getBoundingBoxByPaths(elementNode):
	'Get bounding box of the transformed paths of the xmlObject of the elementNode.'
	transformedPaths = elementNode.xmlObject.getTransformedPaths()
	maximum = euclidean.getMaximumByVector3Paths(transformedPaths)
	minimum = euclidean.getMinimumByVector3Paths(transformedPaths)
	return [minimum, maximum]

def getCenterByPaths(elementNode):
	'Get center of the transformed paths of the xmlObject of the elementNode.'
	transformedPaths = elementNode.xmlObject.getTransformedPaths()
	return 0.5 * (euclidean.getMaximumByVector3Paths(transformedPaths) + euclidean.getMinimumByVector3Paths(transformedPaths))

def getExtentByPaths(elementNode):
	'Get extent of the transformed paths of the xmlObject of the elementNode.'
	transformedPaths = elementNode.xmlObject.getTransformedPaths()
	return euclidean.getMaximumByVector3Paths(transformedPaths) - euclidean.getMinimumByVector3Paths(transformedPaths)

def getInradiusByPaths(elementNode):
	'Get inradius of the transformed paths of the xmlObject of the elementNode.'
	return 0.5 * getExtentByPaths(elementNode)

def getMinimumByPaths(elementNode):
	'Get minimum of the transformed paths of the xmlObject of the elementNode.'
	return euclidean.getMinimumByVector3Paths(elementNode.xmlObject.getTransformedPaths())

def getMaximumByPaths(elementNode):
	'Get maximum of the transformed paths of the xmlObject of the elementNode.'
	return euclidean.getMaximumByVector3Paths(elementNode.xmlObject.getTransformedPaths())
 

globalAccessibleAttributeDictionary = {
	'getBoundingBoxByPaths' : getBoundingBoxByPaths,
	'getCenterByPaths' : getCenterByPaths,
	'getExtentByPaths' : getExtentByPaths,
	'getInradiusByPaths' : getInradiusByPaths,
	'getMaximumByPaths' : getMaximumByPaths,
	'getMinimumByPaths' : getMinimumByPaths}
