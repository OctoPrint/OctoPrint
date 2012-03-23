"""
Svg_writer is a class and collection of utilities to read from and write to an svg file.

Svg_writer uses the layer_template.svg file in the templates folder in the same folder as svg_writer, to output an svg file.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities.xml_simple_reader import DocumentNode
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import xml_simple_reader
from fabmetheus_utilities import xml_simple_writer
import cStringIO
import math
import os


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


globalOriginalTextString = '<!-- Original XML Text:\n'


def getCarving(fileName):
	'Get a carving for the file using an import plugin.'
	pluginModule = fabmetheus_interpret.getInterpretPlugin(fileName)
	if pluginModule == None:
		return None
	return pluginModule.getCarving(fileName)

def getCommentElement(elementNode):
	'Get a carving for the file using an import plugin.'
	for childNode in elementNode.childNodes:
		if childNode.getNodeName() == '#comment':
			if childNode.getTextContent().startswith(globalOriginalTextString):
				return childNode
	return None

def getSliceDictionary(elementNode):
	'Get the metadata slice attribute dictionary.'
	for metadataElement in elementNode.getChildElementsByLocalName('metadata'):
		for childNode in metadataElement.childNodes:
			if childNode.getNodeName().lower() == 'slice:layers':
				return childNode.attributes
	return {}

def getSliceElementNodes(elementNode):
	'Get the slice elements.'
	gElementNodes = elementNode.getElementsByLocalName('g')
	sliceElementNodes = []
	for gElementNode in gElementNodes:
		if 'id' in gElementNode.attributes:
			idValue = gElementNode.attributes['id'].strip()
			if idValue.startswith('z:'):
				sliceElementNodes.append(gElementNode)
	return sliceElementNodes

def getSVGByLoopLayers(addLayerTemplateToSVG, carving, loopLayers):
	'Get the svg text.'
	if len(loopLayers) < 1:
		return ''
	decimalPlacesCarried = max(0, 2 - int(math.floor(math.log10(carving.layerHeight))))
	svgWriter = SVGWriter(
		addLayerTemplateToSVG,
		carving.getCarveCornerMaximum(),
		carving.getCarveCornerMinimum(),
		decimalPlacesCarried,
		carving.getCarveLayerHeight())
	return svgWriter.getReplacedSVGTemplate(carving.fileName, loopLayers, 'basic', carving.getFabmetheusXML())

def getTruncatedRotatedBoundaryLayers(loopLayers, repository):
	'Get the truncated rotated boundary layers.'
	return loopLayers[repository.layersFrom.value : repository.layersTo.value]

def setSVGCarvingCorners(cornerMaximum, cornerMinimum, layerHeight, loopLayers):
	'Parse SVG text and store the layers.'
	for loopLayer in loopLayers:
		for loop in loopLayer.loops:
			for point in loop:
				pointVector3 = Vector3(point.real, point.imag, loopLayer.z)
				cornerMaximum.maximize(pointVector3)
				cornerMinimum.minimize(pointVector3)
	halfLayerThickness = 0.5 * layerHeight
	cornerMaximum.z += halfLayerThickness
	cornerMinimum.z -= halfLayerThickness


class SVGWriter:
	'A base class to get an svg skein from a carving.'
	def __init__(self,
			addLayerTemplateToSVG,
			cornerMaximum,
			cornerMinimum,
			decimalPlacesCarried,
			layerHeight,
			edgeWidth=None):
		'Initialize.'
		self.addLayerTemplateToSVG = addLayerTemplateToSVG
		self.cornerMaximum = cornerMaximum
		self.cornerMinimum = cornerMinimum
		self.decimalPlacesCarried = decimalPlacesCarried
		self.edgeWidth = edgeWidth
		self.layerHeight = layerHeight
		self.textHeight = 22.5
		self.unitScale = 3.7

	def addLayerBegin(self, layerIndex, loopLayer):
		'Add the start lines for the layer.'
		zRounded = self.getRounded(loopLayer.z)
		self.graphicsCopy = self.graphicsElementNode.getCopy(zRounded, self.graphicsElementNode.parentNode)
		if self.addLayerTemplateToSVG:
			translateXRounded = self.getRounded(self.controlBoxWidth + self.margin + self.margin)
			layerTranslateY = self.marginTop
			layerTranslateY += layerIndex * self.textHeight + (layerIndex + 1) * (self.extent.y * self.unitScale + self.margin)
			translateYRounded = self.getRounded(layerTranslateY)
			self.graphicsCopy.attributes['transform'] = 'translate(%s, %s)' % (translateXRounded, translateYRounded)
			layerString = 'Layer %s, z:%s' % (layerIndex, zRounded)
			self.graphicsCopy.getFirstChildByLocalName('text').setTextContent(layerString)
			self.graphicsCopy.attributes['inkscape:groupmode'] = 'layer'
			self.graphicsCopy.attributes['inkscape:label'] = layerString
		self.pathElementNode = self.graphicsCopy.getFirstChildByLocalName('path')
		self.pathDictionary = self.pathElementNode.attributes

	def addLoopLayersToOutput(self, loopLayers):
		'Add rotated boundary layers to the output.'
		for loopLayerIndex, loopLayer in enumerate(loopLayers):
			self.addLoopLayerToOutput(loopLayerIndex, loopLayer)

	def addLoopLayerToOutput(self, layerIndex, loopLayer):
		'Add rotated boundary layer to the output.'
		self.addLayerBegin(layerIndex, loopLayer)
		if self.addLayerTemplateToSVG:
			self.pathDictionary['transform'] = self.getTransformString()
		else:
			del self.pathDictionary['transform']
		self.pathDictionary['d'] = self.getSVGStringForLoops(loopLayer.loops)

	def addOriginalAsComment(self, elementNode):
		'Add original elementNode as a comment.'
		if elementNode == None:
			return
		if elementNode.getNodeName() == '#comment':
			elementNode.setParentAddToChildNodes(self.svgElement)
			return
		elementNodeOutput = cStringIO.StringIO()
		elementNode.addXML(0, elementNodeOutput)
		textLines = archive.getTextLines(elementNodeOutput.getvalue())
		commentNodeOutput = cStringIO.StringIO()
		isComment = False
		for textLine in textLines:
			lineStripped = textLine.strip()
			if lineStripped[: len('<!--')] == '<!--':
				isComment = True
			if not isComment:
				if len(textLine) > 0:
					commentNodeOutput.write(textLine + '\n')
			if '-->' in lineStripped:
				isComment = False
		xml_simple_reader.CommentNode(self.svgElement, '%s%s-->\n' % (globalOriginalTextString, commentNodeOutput.getvalue())).appendSelfToParent()

	def getReplacedSVGTemplate(self, fileName, loopLayers, procedureName, elementNode=None):
		'Get the lines of text from the layer_template.svg file.'
		self.extent = self.cornerMaximum - self.cornerMinimum
		svgTemplateText = archive.getFileText(archive.getTemplatesPath('layer_template.svg'))
		documentNode = DocumentNode(fileName, svgTemplateText)
		self.svgElement = documentNode.getDocumentElement()
		svgElementDictionary = self.svgElement.attributes
		self.sliceDictionary = getSliceDictionary(self.svgElement)
		self.controlBoxHeight = float(self.sliceDictionary['controlBoxHeight'])
		self.controlBoxWidth = float(self.sliceDictionary['controlBoxWidth'])
		self.margin = float(self.sliceDictionary['margin'])
		self.marginTop = float(self.sliceDictionary['marginTop'])
		self.textHeight = float(self.sliceDictionary['textHeight'])
		self.unitScale = float(self.sliceDictionary['unitScale'])
		svgMinWidth = float(self.sliceDictionary['svgMinWidth'])
		self.controlBoxHeightMargin = self.controlBoxHeight + self.marginTop
		if not self.addLayerTemplateToSVG:
			self.svgElement.getElementNodeByID('layerTextTemplate').removeFromIDNameParent()
			del self.svgElement.getElementNodeByID('sliceElementTemplate').attributes['transform']
		self.graphicsElementNode = self.svgElement.getElementNodeByID('sliceElementTemplate')
		self.graphicsElementNode.attributes['id'] = 'z:'
		self.addLoopLayersToOutput(loopLayers)
		self.setMetadataNoscriptElement('layerHeight', 'Layer Height: ', self.layerHeight)
		self.setMetadataNoscriptElement('maxX', 'X: ', self.cornerMaximum.x)
		self.setMetadataNoscriptElement('minX', 'X: ', self.cornerMinimum.x)
		self.setMetadataNoscriptElement('maxY', 'Y: ', self.cornerMaximum.y)
		self.setMetadataNoscriptElement('minY', 'Y: ', self.cornerMinimum.y)
		self.setMetadataNoscriptElement('maxZ', 'Z: ', self.cornerMaximum.z)
		self.setMetadataNoscriptElement('minZ', 'Z: ', self.cornerMinimum.z)
		self.textHeight = float( self.sliceDictionary['textHeight'] )
		controlTop = len(loopLayers) * (self.margin + self.extent.y * self.unitScale + self.textHeight) + self.marginTop + self.textHeight
		self.svgElement.getFirstChildByLocalName('title').setTextContent(os.path.basename(fileName) + ' - Slice Layers')
		svgElementDictionary['height'] = '%spx' % self.getRounded(max(controlTop, self.controlBoxHeightMargin))
		width = max(self.extent.x * self.unitScale, svgMinWidth)
		svgElementDictionary['width'] = '%spx' % self.getRounded( width )
		self.sliceDictionary['decimalPlacesCarried'] = str( self.decimalPlacesCarried )
		if self.edgeWidth != None:
			self.sliceDictionary['edgeWidth'] = self.getRounded( self.edgeWidth )
		self.sliceDictionary['yAxisPointingUpward'] = 'true'
		self.sliceDictionary['procedureName'] = procedureName
		self.setDimensionTexts('dimX', 'X: ' + self.getRounded(self.extent.x))
		self.setDimensionTexts('dimY', 'Y: ' + self.getRounded(self.extent.y))
		self.setDimensionTexts('dimZ', 'Z: ' + self.getRounded(self.extent.z))
		self.setTexts('numberOfLayers', 'Number of Layers: %s' % len(loopLayers))
		volume = 0.0
		for loopLayer in loopLayers:
			volume += euclidean.getAreaLoops(loopLayer.loops)
		volume *= 0.001 * self.layerHeight
		self.setTexts('volume', 'Volume: %s cm3' % self.getRounded(volume))
		if not self.addLayerTemplateToSVG:
			self.svgElement.getFirstChildByLocalName('script').removeFromIDNameParent()
			self.svgElement.getElementNodeByID('controls').removeFromIDNameParent()
		self.graphicsElementNode.removeFromIDNameParent()
		self.addOriginalAsComment(elementNode)
		return documentNode.__repr__()

	def getRounded(self, number):
		'Get number rounded to the number of carried decimal places as a string.'
		return euclidean.getRoundedToPlacesString(self.decimalPlacesCarried, number)

	def getRoundedComplexString(self, point):
		'Get the rounded complex string.'
		return self.getRounded( point.real ) + ' ' + self.getRounded( point.imag )

	def getSVGStringForLoop( self, loop ):
		'Get the svg loop string.'
		if len(loop) < 1:
			return ''
		return self.getSVGStringForPath(loop) + ' z'

	def getSVGStringForLoops( self, loops ):
		'Get the svg loops string.'
		loopString = ''
		if len(loops) > 0:
			loopString += self.getSVGStringForLoop( loops[0] )
		for loop in loops[1 :]:
			loopString += ' ' + self.getSVGStringForLoop(loop)
		return loopString

	def getSVGStringForPath( self, path ):
		'Get the svg path string.'
		svgLoopString = ''
		for point in path:
			stringBeginning = 'M '
			if len( svgLoopString ) > 0:
				stringBeginning = ' L '
			svgLoopString += stringBeginning + self.getRoundedComplexString(point)
		return svgLoopString

	def getTransformString(self):
		'Get the svg transform string.'
		cornerMinimumXString = self.getRounded(-self.cornerMinimum.x)
		cornerMinimumYString = self.getRounded(-self.cornerMinimum.y)
		return 'scale(%s, %s) translate(%s, %s)' % (self.unitScale, - self.unitScale, cornerMinimumXString, cornerMinimumYString)

	def setDimensionTexts(self, key, valueString):
		'Set the texts to the valueString followed by mm.'
		self.setTexts(key, valueString + ' mm')

	def setMetadataNoscriptElement(self, key, prefix, value):
		'Set the metadata value and the text.'
		valueString = self.getRounded(value)
		self.sliceDictionary[key] = valueString
		self.setDimensionTexts(key, prefix + valueString)

	def setTexts(self, key, valueString):
		'Set the texts to the valueString.'
		self.svgElement.getElementNodeByID(key + 'Iso').setTextContent(valueString)
		self.svgElement.getElementNodeByID(key + 'Layer').setTextContent(valueString)
		self.svgElement.getElementNodeByID(key + 'Scroll').setTextContent(valueString)
