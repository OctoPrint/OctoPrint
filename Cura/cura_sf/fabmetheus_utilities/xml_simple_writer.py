"""
XML tag writer utilities.

"""


from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

import cStringIO


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Nophead <http://hydraraptor.blogspot.com/>\nArt of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def addBeginEndInnerXMLTag(attributes, depth, innerText, localName, output, text=''):
	'Add the begin and end xml tag and the inner text if any.'
	if len( innerText ) > 0:
		addBeginXMLTag(attributes, depth, localName, output, text)
		output.write( innerText )
		addEndXMLTag(depth, localName, output)
	else:
		addClosedXMLTag(attributes, depth, localName, output, text)

def addBeginXMLTag(attributes, depth, localName, output, text=''):
	'Add the begin xml tag.'
	depthStart = '\t' * depth
	output.write('%s<%s%s>%s\n' % (depthStart, localName, getAttributesString(attributes), text))

def addClosedXMLTag(attributes, depth, localName, output, text=''):
	'Add the closed xml tag.'
	depthStart = '\t' * depth
	attributesString = getAttributesString(attributes)
	if len(text) > 0:
		output.write('%s<%s%s >%s</%s>\n' % (depthStart, localName, attributesString, text, localName))
	else:
		output.write('%s<%s%s />\n' % (depthStart, localName, attributesString))

def addEndXMLTag(depth, localName, output):
	'Add the end xml tag.'
	depthStart = '\t' * depth
	output.write('%s</%s>\n' % (depthStart, localName))

def addXMLFromLoopComplexZ(attributes, depth, loop, output, z):
	'Add xml from loop.'
	addBeginXMLTag(attributes, depth, 'path', output)
	for pointComplexIndex in xrange(len(loop)):
		pointComplex = loop[pointComplexIndex]
		addXMLFromXYZ(depth + 1, pointComplexIndex, output, pointComplex.real, pointComplex.imag, z)
	addEndXMLTag(depth, 'path', output)

def addXMLFromObjects(depth, objects, output):
	'Add xml from objects.'
	for object in objects:
		object.addXML(depth, output)

def addXMLFromVertexes(depth, output, vertexes):
	'Add xml from loop.'
	for vertexIndex in xrange(len(vertexes)):
		vertex = vertexes[vertexIndex]
		addXMLFromXYZ(depth + 1, vertexIndex, output, vertex.x, vertex.y, vertex.z)

def addXMLFromXYZ(depth, index, output, x, y, z):
	'Add xml from x, y & z.'
	attributes = {'index' : str(index)}
	if x != 0.0:
		attributes['x'] = str(x)
	if y != 0.0:
		attributes['y'] = str(y)
	if z != 0.0:
		attributes['z'] = str(z)
	addClosedXMLTag(attributes, depth, 'vertex', output)

def compareAttributeKeyAscending(key, otherKey):
	'Get comparison in order to sort attribute keys in ascending order, with the id key first and name second.'
	if key == 'id':
		return - 1
	if otherKey == 'id':
		return 1
	if key == 'name':
		return - 1
	if otherKey == 'name':
		return 1
	if key < otherKey:
		return - 1
	return int(key > otherKey)

def getAttributesString(attributes):
	'Add the closed xml tag.'
	attributesString = ''
	attributesKeys = attributes.keys()
	attributesKeys.sort(compareAttributeKeyAscending)
	for attributesKey in attributesKeys:
		valueString = str(attributes[attributesKey])
		if "'" in valueString:
			attributesString += ' %s="%s"' % (attributesKey, valueString)
		else:
			attributesString += " %s='%s'" % (attributesKey, valueString)
	return attributesString

def getBeginGeometryXMLOutput(elementNode=None):
	'Get the beginning of the string representation of this boolean geometry object info.'
	output = getBeginXMLOutput()
	attributes = {}
	if elementNode != None:
		documentElement = elementNode.getDocumentElement()
		attributes = documentElement.attributes
	addBeginXMLTag(attributes, 0, 'fabmetheus', output)
	return output

def getBeginXMLOutput():
	'Get the beginning of the string representation of this object info.'
	output = cStringIO.StringIO()
	output.write("<?xml version='1.0' ?>\n")
	return output

def getDictionaryWithoutList(dictionary, withoutList):
	'Get the dictionary without the keys in the list.'
	dictionaryWithoutList = {}
	for key in dictionary:
		if key not in withoutList:
			dictionaryWithoutList[key] = dictionary[key]
	return dictionaryWithoutList

def getEndGeometryXMLString(output):
	'Get the string representation of this object info.'
	addEndXMLTag(0, 'fabmetheus', output)
	return output.getvalue()
