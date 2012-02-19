"""
Svg reader.

"""


from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.solids import triangle_mesh
from fabmetheus_utilities.xml_simple_reader import DocumentNode
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import intercircle
from fabmetheus_utilities import settings
from fabmetheus_utilities import svg_writer
import math
import os
import sys
import traceback


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Nophead <http://hydraraptor.blogspot.com/>\nArt of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


globalNumberOfCornerPoints = 11
globalNumberOfBezierPoints = globalNumberOfCornerPoints + globalNumberOfCornerPoints
globalNumberOfCirclePoints = 4 * globalNumberOfCornerPoints


def addFunctionsToDictionary( dictionary, functions, prefix ):
	"Add functions to dictionary."
	for function in functions:
		dictionary[ function.__name__[ len( prefix ) : ] ] = function

def getArcComplexes(begin, end, largeArcFlag, radius, sweepFlag, xAxisRotation):
	'Get the arc complexes, procedure at http://www.w3.org/TR/SVG/implnote.html#ArcImplementationNotes'
	if begin == end:
		print('Warning, begin equals end in getArcComplexes in svgReader')
		print(begin)
		print(end)
		return []
	if radius.imag < 0.0:
		print('Warning, radius.imag is less than zero in getArcComplexes in svgReader')
		print(radius)
		radius = complex(radius.real, abs(radius.imag))
	if radius.real < 0.0:
		print('Warning, radius.real is less than zero in getArcComplexes in svgReader')
		print(radius)
		radius = complex(abs(radius.real), radius.imag)
	if radius.imag <= 0.0:
		print('Warning, radius.imag is too small for getArcComplexes in svgReader')
		print(radius)
		return [end]
	if radius.real <= 0.0:
		print('Warning, radius.real is too small for getArcComplexes in svgReader')
		print(radius)
		return [end]
	xAxisRotationComplex = euclidean.getWiddershinsUnitPolar(xAxisRotation)
	reverseXAxisRotationComplex = complex(xAxisRotationComplex.real, -xAxisRotationComplex.imag)
	beginRotated = begin * reverseXAxisRotationComplex
	endRotated = end * reverseXAxisRotationComplex
	beginTransformed = complex(beginRotated.real / radius.real, beginRotated.imag / radius.imag)
	endTransformed = complex(endRotated.real / radius.real, endRotated.imag / radius.imag)
	midpointTransformed = 0.5 * (beginTransformed + endTransformed)
	midMinusBeginTransformed = midpointTransformed - beginTransformed
	midMinusBeginTransformedLength = abs(midMinusBeginTransformed)
	if midMinusBeginTransformedLength > 1.0:
		print('The ellipse radius is too small for getArcComplexes in svgReader.')
		print('So the ellipse will be scaled to fit, according to the formulas in "Step 3: Ensure radii are large enough" of:')
		print('http://www.w3.org/TR/SVG/implnote.html#ArcCorrectionOutOfRangeRadii')
		print('')
		radius *= midMinusBeginTransformedLength
		beginTransformed /= midMinusBeginTransformedLength
		endTransformed /= midMinusBeginTransformedLength
		midpointTransformed /= midMinusBeginTransformedLength
		midMinusBeginTransformed /= midMinusBeginTransformedLength
		midMinusBeginTransformedLength = 1.0
	midWiddershinsTransformed = complex(-midMinusBeginTransformed.imag, midMinusBeginTransformed.real)
	midWiddershinsLengthSquared = 1.0 - midMinusBeginTransformedLength * midMinusBeginTransformedLength
	if midWiddershinsLengthSquared < 0.0:
		midWiddershinsLengthSquared = 0.0
	midWiddershinsLength = math.sqrt(midWiddershinsLengthSquared)
	midWiddershinsTransformed *= midWiddershinsLength / abs(midWiddershinsTransformed)
	centerTransformed = midpointTransformed
	if largeArcFlag == sweepFlag:
		centerTransformed -= midWiddershinsTransformed
	else:
		centerTransformed += midWiddershinsTransformed
	beginMinusCenterTransformed = beginTransformed - centerTransformed
	beginMinusCenterTransformedLength = abs(beginMinusCenterTransformed)
	if beginMinusCenterTransformedLength <= 0.0:
		return end
	beginAngle = math.atan2(beginMinusCenterTransformed.imag, beginMinusCenterTransformed.real)
	endMinusCenterTransformed = endTransformed - centerTransformed
	angleDifference = euclidean.getAngleDifferenceByComplex(endMinusCenterTransformed, beginMinusCenterTransformed)
	if sweepFlag:
		if angleDifference < 0.0:
			angleDifference += 2.0 * math.pi
	else:
		if angleDifference > 0.0:
			angleDifference -= 2.0 * math.pi
	global globalSideAngle
	sides = int(math.ceil(abs(angleDifference) / globalSideAngle))
	sideAngle = angleDifference / float(sides)
	arcComplexes = []
	center = complex(centerTransformed.real * radius.real, centerTransformed.imag * radius.imag) * xAxisRotationComplex
	for side in xrange(1, sides):
		unitPolar = euclidean.getWiddershinsUnitPolar(beginAngle + float(side) * sideAngle)
		circumferential = complex(unitPolar.real * radius.real, unitPolar.imag * radius.imag) * beginMinusCenterTransformedLength
		point = center + circumferential * xAxisRotationComplex
		arcComplexes.append(point)
	arcComplexes.append(end)
	return arcComplexes

def getChainMatrixSVG(elementNode, matrixSVG):
	"Get chain matrixSVG by svgElement."
	matrixSVG = matrixSVG.getOtherTimesSelf(getMatrixSVG(elementNode).tricomplex)
	if elementNode.parentNode != None:
		matrixSVG = getChainMatrixSVG(elementNode.parentNode, matrixSVG)
	return matrixSVG

def getChainMatrixSVGIfNecessary(elementNode, yAxisPointingUpward):
	"Get chain matrixSVG by svgElement and yAxisPointingUpward."
	matrixSVG = MatrixSVG()
	if yAxisPointingUpward:
		return matrixSVG
	return getChainMatrixSVG(elementNode, matrixSVG)

def getCubicPoint( along, begin, controlPoints, end ):
	'Get the cubic point.'
	segmentBegin = getQuadraticPoint( along, begin, controlPoints[0], controlPoints[1] )
	segmentEnd = getQuadraticPoint( along, controlPoints[0], controlPoints[1], end )
	return ( 1.0 - along ) * segmentBegin + along * segmentEnd

def getCubicPoints( begin, controlPoints, end, numberOfBezierPoints=globalNumberOfBezierPoints):
	'Get the cubic points.'
	bezierPortion = 1.0 / float(numberOfBezierPoints)
	cubicPoints = []
	for bezierIndex in xrange( 1, numberOfBezierPoints + 1 ):
		cubicPoints.append(getCubicPoint(bezierPortion * bezierIndex, begin, controlPoints, end))
	return cubicPoints

def getFontReader(fontFamily):
	'Get the font reader for the fontFamily.'
	fontLower = fontFamily.lower().replace(' ', '_')
	global globalFontReaderDictionary
	if fontLower in globalFontReaderDictionary:
		return globalFontReaderDictionary[fontLower]
	global globalFontFileNames
	if globalFontFileNames == None:
		globalFontFileNames = archive.getFileNamesByFilePaths(archive.getFilePathsByDirectory(getFontsDirectoryPath()))
	if fontLower not in globalFontFileNames:
		print('Warning, the %s font was not found in the fabmetheus_utilities/fonts folder, so Gentium Basic Regular will be substituted.' % fontFamily)
		print('The available fonts are:')
		globalFontFileNames.sort()
		print(globalFontFileNames)
		print('')
		fontLower = 'gentium_basic_regular'
	fontReader = FontReader(fontLower)
	globalFontReaderDictionary[fontLower] = fontReader
	return fontReader

def getFontsDirectoryPath():
	"Get the fonts directory path."
	return archive.getFabmetheusUtilitiesPath('fonts')

def getLabelString(dictionary):
	"Get the label string for the dictionary."
	for key in dictionary:
		labelIndex = key.find('label')
		if labelIndex >= 0:
			return dictionary[key]
	return ''

def getMatrixSVG(elementNode):
	"Get matrixSVG by svgElement."
	matrixSVG = MatrixSVG()
	if 'transform' not in elementNode.attributes:
		return matrixSVG
	transformWords = []
	for transformWord in elementNode.attributes['transform'].replace(')', '(').split('('):
		transformWordStrip = transformWord.strip()
		if transformWordStrip != '': # workaround for split(character) bug which leaves an extra empty element
			transformWords.append(transformWordStrip)
	global globalGetTricomplexDictionary
	getTricomplexDictionaryKeys = globalGetTricomplexDictionary.keys()
	for transformWordIndex, transformWord in enumerate(transformWords):
		if transformWord in getTricomplexDictionaryKeys:
			transformString = transformWords[transformWordIndex + 1].replace(',', ' ')
			matrixSVG = matrixSVG.getSelfTimesOther(globalGetTricomplexDictionary[ transformWord ](transformString.split()))
	return matrixSVG

def getQuadraticPoint( along, begin, controlPoint, end ):
	'Get the quadratic point.'
	oneMinusAlong = 1.0 - along
	segmentBegin = oneMinusAlong * begin + along * controlPoint
	segmentEnd = oneMinusAlong * controlPoint + along * end
	return oneMinusAlong * segmentBegin + along * segmentEnd

def getQuadraticPoints(begin, controlPoint, end, numberOfBezierPoints=globalNumberOfBezierPoints):
	'Get the quadratic points.'
	bezierPortion = 1.0 / float(numberOfBezierPoints)
	quadraticPoints = []
	for bezierIndex in xrange(1, numberOfBezierPoints + 1):
		quadraticPoints.append(getQuadraticPoint(bezierPortion * bezierIndex, begin, controlPoint, end))
	return quadraticPoints

def getRightStripAlphabetPercent(word):
	"Get word with alphabet characters and the percent sign stripped from the right."
	word = word.strip()
	for characterIndex in xrange(len(word) - 1, -1, -1):
		character = word[characterIndex]
		if not character.isalpha() and not character == '%':
			return float(word[: characterIndex + 1])
	return None

def getRightStripMinusSplit(lineString):
	"Get string with spaces after the minus sign stripped."
	oldLineStringLength = -1
	while oldLineStringLength < len(lineString):
		oldLineStringLength = len(lineString)
		lineString = lineString.replace('- ', '-')
	return lineString.split()

def getStrokeRadius(elementNode):
	"Get the stroke radius."
	return 0.5 * getRightStripAlphabetPercent(getStyleValue('1.0', elementNode, 'stroke-width'))

def getStyleValue(defaultValue, elementNode, key):
	"Get the stroke value string."
	if 'style' in elementNode.attributes:
		line = elementNode.attributes['style']
		strokeIndex = line.find(key)
		if strokeIndex > -1:
			words = line[strokeIndex :].replace(':', ' ').replace(';', ' ').split()
			if len(words) > 1:
				return words[1]
	if key in elementNode.attributes:
		return elementNode.attributes[key]
	if elementNode.parentNode == None:
		return defaultValue
	return getStyleValue(defaultValue, elementNode.parentNode, key)

def getTextComplexLoops(fontFamily, fontSize, text, yAxisPointingUpward=True):
	"Get text as complex loops."
	textComplexLoops = []
	fontReader = getFontReader(fontFamily)
	horizontalAdvanceX = 0.0
	for character in text:
		glyph = fontReader.getGlyph(character, yAxisPointingUpward)
		textComplexLoops += glyph.getSizedAdvancedLoops(fontSize, horizontalAdvanceX, yAxisPointingUpward)
		horizontalAdvanceX += glyph.horizontalAdvanceX
	return textComplexLoops

def getTransformedFillOutline(elementNode, loop, yAxisPointingUpward):
	"Get the loops if fill is on, otherwise get the outlines."
	fillOutlineLoops = None
	if getStyleValue('none', elementNode, 'fill').lower() == 'none':
		fillOutlineLoops = intercircle.getAroundsFromLoop(loop, getStrokeRadius(elementNode))
	else:
		fillOutlineLoops = [loop]
	return getChainMatrixSVGIfNecessary(elementNode, yAxisPointingUpward).getTransformedPaths(fillOutlineLoops)

def getTransformedOutlineByPath(elementNode, path, yAxisPointingUpward):
	"Get the outline from the path."
	aroundsFromPath = intercircle.getAroundsFromPath(path, getStrokeRadius(elementNode))
	return getChainMatrixSVGIfNecessary(elementNode, yAxisPointingUpward).getTransformedPaths(aroundsFromPath)

def getTransformedOutlineByPaths(elementNode, paths, yAxisPointingUpward):
	"Get the outline from the paths."
	aroundsFromPaths = intercircle.getAroundsFromPaths(paths, getStrokeRadius(elementNode))
	return getChainMatrixSVGIfNecessary(elementNode, yAxisPointingUpward).getTransformedPaths(aroundsFromPaths)

def getTricomplexmatrix(transformWords):
	"Get matrixSVG by transformWords."
	tricomplex = [euclidean.getComplexByWords(transformWords)]
	tricomplex.append(euclidean.getComplexByWords(transformWords, 2))
	tricomplex.append(euclidean.getComplexByWords(transformWords, 4))
	return tricomplex

def getTricomplexrotate(transformWords):
	"Get matrixSVG by transformWords."
	rotate = euclidean.getWiddershinsUnitPolar(math.radians(float(transformWords[0])))
	return [rotate, complex(-rotate.imag,rotate.real), complex()]

def getTricomplexscale(transformWords):
	"Get matrixSVG by transformWords."
	scale = euclidean.getComplexByWords(transformWords)
	return [complex(scale.real,0.0), complex(0.0,scale.imag), complex()]

def getTricomplexskewX(transformWords):
	"Get matrixSVG by transformWords."
	skewX = math.tan(math.radians(float(transformWords[0])))
	return [complex(1.0, 0.0), complex(skewX, 1.0), complex()]

def getTricomplexskewY(transformWords):
	"Get matrixSVG by transformWords."
	skewY = math.tan(math.radians(float(transformWords[0])))
	return [complex(1.0, skewY), complex(0.0, 1.0), complex()]

def getTricomplexTimesColumn(firstTricomplex, otherColumn):
	"Get this matrix multiplied by the otherColumn."
	dotProductX = firstTricomplex[0].real * otherColumn.real + firstTricomplex[1].real * otherColumn.imag
	dotProductY = firstTricomplex[0].imag * otherColumn.real + firstTricomplex[1].imag * otherColumn.imag
	return complex(dotProductX, dotProductY)

def getTricomplexTimesOther(firstTricomplex, otherTricomplex):
	"Get the first tricomplex multiplied by the other tricomplex."
	#A down, B right from http://en.wikipedia.org/wiki/Matrix_multiplication
	tricomplexTimesOther = [getTricomplexTimesColumn(firstTricomplex, otherTricomplex[0])]
	tricomplexTimesOther.append(getTricomplexTimesColumn(firstTricomplex, otherTricomplex[1]))
	tricomplexTimesOther.append(getTricomplexTimesColumn(firstTricomplex, otherTricomplex[2]) + firstTricomplex[2])
	return tricomplexTimesOther

def getTricomplextranslate(transformWords):
	"Get matrixSVG by transformWords."
	translate = euclidean.getComplexByWords(transformWords)
	return [complex(1.0, 0.0), complex(0.0, 1.0), translate]

def processSVGElementcircle( elementNode, svgReader ):
	"Process elementNode by svgReader."
	attributes = elementNode.attributes
	center = euclidean.getComplexDefaultByDictionaryKeys( complex(), attributes, 'cx', 'cy')
	radius = euclidean.getFloatDefaultByDictionary( 0.0, attributes, 'r')
	if radius == 0.0:
		print('Warning, in processSVGElementcircle in svgReader radius is zero in:')
		print(attributes)
		return
	global globalNumberOfCirclePoints
	global globalSideAngle
	loop = []
	loopLayer = svgReader.getLoopLayer()
	for side in xrange( globalNumberOfCirclePoints ):
		unitPolar = euclidean.getWiddershinsUnitPolar( float(side) * globalSideAngle )
		loop.append( center + radius * unitPolar )
	loopLayer.loops += getTransformedFillOutline(elementNode, loop, svgReader.yAxisPointingUpward)

def processSVGElementellipse( elementNode, svgReader ):
	"Process elementNode by svgReader."
	attributes = elementNode.attributes
	center = euclidean.getComplexDefaultByDictionaryKeys( complex(), attributes, 'cx', 'cy')
	radius = euclidean.getComplexDefaultByDictionaryKeys( complex(), attributes, 'rx', 'ry')
	if radius.real == 0.0 or radius.imag == 0.0:
		print('Warning, in processSVGElementellipse in svgReader radius is zero in:')
		print(attributes)
		return
	global globalNumberOfCirclePoints
	global globalSideAngle
	loop = []
	loopLayer = svgReader.getLoopLayer()
	for side in xrange( globalNumberOfCirclePoints ):
		unitPolar = euclidean.getWiddershinsUnitPolar( float(side) * globalSideAngle )
		loop.append( center + complex( unitPolar.real * radius.real, unitPolar.imag * radius.imag ) )
	loopLayer.loops += getTransformedFillOutline(elementNode, loop, svgReader.yAxisPointingUpward)

def processSVGElementg(elementNode, svgReader):
	'Process elementNode by svgReader.'
	if 'id' not in elementNode.attributes:
		return
	idString = elementNode.attributes['id']
	if 'beginningOfControlSection' in elementNode.attributes:
		if elementNode.attributes['beginningOfControlSection'].lower()[: 1] == 't':
			svgReader.stopProcessing = True
		return
	idStringLower = idString.lower()
	zIndex = idStringLower.find('z:')
	if zIndex < 0:
		idStringLower = getLabelString(elementNode.attributes)
		zIndex = idStringLower.find('z:')
	if zIndex < 0:
		return
	floatFromValue = euclidean.getFloatFromValue(idStringLower[zIndex + len('z:') :].strip())
	if floatFromValue != None:
		svgReader.z = floatFromValue

def processSVGElementline(elementNode, svgReader):
	"Process elementNode by svgReader."
	begin = euclidean.getComplexDefaultByDictionaryKeys(complex(), elementNode.attributes, 'x1', 'y1')
	end = euclidean.getComplexDefaultByDictionaryKeys(complex(), elementNode.attributes, 'x2', 'y2')
	loopLayer = svgReader.getLoopLayer()
	loopLayer.loops += getTransformedOutlineByPath(elementNode, [begin, end], svgReader.yAxisPointingUpward)

def processSVGElementpath( elementNode, svgReader ):
	"Process elementNode by svgReader."
	if 'd' not in elementNode.attributes:
		print('Warning, in processSVGElementpath in svgReader can not get a value for d in:')
		print(elementNode.attributes)
		return
	loopLayer = svgReader.getLoopLayer()
	PathReader(elementNode, loopLayer.loops, svgReader.yAxisPointingUpward)

def processSVGElementpolygon( elementNode, svgReader ):
	"Process elementNode by svgReader."
	if 'points' not in elementNode.attributes:
		print('Warning, in processSVGElementpolygon in svgReader can not get a value for d in:')
		print(elementNode.attributes)
		return
	loopLayer = svgReader.getLoopLayer()
	words = getRightStripMinusSplit(elementNode.attributes['points'].replace(',', ' '))
	loop = []
	for wordIndex in xrange( 0, len(words), 2 ):
		loop.append(euclidean.getComplexByWords(words[wordIndex :]))
	loopLayer.loops += getTransformedFillOutline(elementNode, loop, svgReader.yAxisPointingUpward)

def processSVGElementpolyline(elementNode, svgReader):
	"Process elementNode by svgReader."
	if 'points' not in elementNode.attributes:
		print('Warning, in processSVGElementpolyline in svgReader can not get a value for d in:')
		print(elementNode.attributes)
		return
	loopLayer = svgReader.getLoopLayer()
	words = getRightStripMinusSplit(elementNode.attributes['points'].replace(',', ' '))
	path = []
	for wordIndex in xrange(0, len(words), 2):
		path.append(euclidean.getComplexByWords(words[wordIndex :]))
	loopLayer.loops += getTransformedOutlineByPath(elementNode, path, svgReader.yAxisPointingUpward)

def processSVGElementrect( elementNode, svgReader ):
	"Process elementNode by svgReader."
	attributes = elementNode.attributes
	height = euclidean.getFloatDefaultByDictionary( 0.0, attributes, 'height')
	if height == 0.0:
		print('Warning, in processSVGElementrect in svgReader height is zero in:')
		print(attributes)
		return
	width = euclidean.getFloatDefaultByDictionary( 0.0, attributes, 'width')
	if width == 0.0:
		print('Warning, in processSVGElementrect in svgReader width is zero in:')
		print(attributes)
		return
	center = euclidean.getComplexDefaultByDictionaryKeys(complex(), attributes, 'x', 'y')
	inradius = 0.5 * complex( width, height )
	cornerRadius = euclidean.getComplexDefaultByDictionaryKeys( complex(), attributes, 'rx', 'ry')
	loopLayer = svgReader.getLoopLayer()
	if cornerRadius.real == 0.0 and cornerRadius.imag == 0.0:
		inradiusMinusX = complex( - inradius.real, inradius.imag )
		loop = [center + inradius, center + inradiusMinusX, center - inradius, center - inradiusMinusX]
		loopLayer.loops += getTransformedFillOutline(elementNode, loop, svgReader.yAxisPointingUpward)
		return
	if cornerRadius.real == 0.0:
		cornerRadius = complex( cornerRadius.imag, cornerRadius.imag )
	elif cornerRadius.imag == 0.0:
		cornerRadius = complex( cornerRadius.real, cornerRadius.real )
	cornerRadius = complex( min( cornerRadius.real, inradius.real ), min( cornerRadius.imag, inradius.imag ) )
	ellipsePath = [ complex( cornerRadius.real, 0.0 ) ]
	inradiusMinusCorner = inradius - cornerRadius
	loop = []
	global globalNumberOfCornerPoints
	global globalSideAngle
	for side in xrange( 1, globalNumberOfCornerPoints ):
		unitPolar = euclidean.getWiddershinsUnitPolar( float(side) * globalSideAngle )
		ellipsePath.append( complex( unitPolar.real * cornerRadius.real, unitPolar.imag * cornerRadius.imag ) )
	ellipsePath.append( complex( 0.0, cornerRadius.imag ) )
	cornerPoints = []
	for point in ellipsePath:
		cornerPoints.append( point + inradiusMinusCorner )
	cornerPointsReversed = cornerPoints[: : -1]
	for cornerPoint in cornerPoints:
		loop.append( center + cornerPoint )
	for cornerPoint in cornerPointsReversed:
		loop.append( center + complex( - cornerPoint.real, cornerPoint.imag ) )
	for cornerPoint in cornerPoints:
		loop.append( center - cornerPoint )
	for cornerPoint in cornerPointsReversed:
		loop.append( center + complex( cornerPoint.real, - cornerPoint.imag ) )
	loop = euclidean.getLoopWithoutCloseSequentialPoints( 0.0001 * abs(inradius), loop )
	loopLayer.loops += getTransformedFillOutline(elementNode, loop, svgReader.yAxisPointingUpward)

def processSVGElementtext(elementNode, svgReader):
	"Process elementNode by svgReader."
	if svgReader.yAxisPointingUpward:
		return
	fontFamily = getStyleValue('Gentium Basic Regular', elementNode, 'font-family')
	fontSize = getRightStripAlphabetPercent(getStyleValue('12.0', elementNode, 'font-size'))
	matrixSVG = getChainMatrixSVGIfNecessary(elementNode, svgReader.yAxisPointingUpward)
	loopLayer = svgReader.getLoopLayer()
	translate = euclidean.getComplexDefaultByDictionaryKeys(complex(), elementNode.attributes, 'x', 'y')
	for textComplexLoop in getTextComplexLoops(fontFamily, fontSize, elementNode.getTextContent(), svgReader.yAxisPointingUpward):
		translatedLoop = []
		for textComplexPoint in textComplexLoop:
			translatedLoop.append(textComplexPoint + translate )
		loopLayer.loops.append(matrixSVG.getTransformedPath(translatedLoop))


class FontReader:
	"Class to read a font in the fonts folder."
	def __init__(self, fontFamily):
		"Initialize."
		self.fontFamily = fontFamily
		self.glyphDictionary = {}
		self.glyphElementNodeDictionary = {}
		self.missingGlyph = None
		fileName = os.path.join(getFontsDirectoryPath(), fontFamily + '.svg')
		documentElement = DocumentNode(fileName, archive.getFileText(fileName)).getDocumentElement()
		self.fontElementNode = documentElement.getFirstChildByLocalName('defs').getFirstChildByLocalName('font')
		self.fontFaceElementNode = self.fontElementNode.getFirstChildByLocalName('font-face')
		self.unitsPerEM = float(self.fontFaceElementNode.attributes['units-per-em'])
		glyphElementNodes = self.fontElementNode.getChildElementsByLocalName('glyph')
		for glyphElementNode in glyphElementNodes:
			self.glyphElementNodeDictionary[glyphElementNode.attributes['unicode']] = glyphElementNode

	def getGlyph(self, character, yAxisPointingUpward):
		"Get the glyph for the character."
		if character not in self.glyphElementNodeDictionary:
			if self.missingGlyph == None:
				missingGlyphElementNode = self.fontElementNode.getFirstChildByLocalName('missing-glyph')
				self.missingGlyph = Glyph(missingGlyphElementNode, self.unitsPerEM, yAxisPointingUpward)
			return self.missingGlyph
		if character not in self.glyphDictionary:
			self.glyphDictionary[character] = Glyph(self.glyphElementNodeDictionary[character], self.unitsPerEM, yAxisPointingUpward)
		return self.glyphDictionary[character]


class Glyph:
	"Class to handle a glyph."
	def __init__(self, elementNode, unitsPerEM, yAxisPointingUpward):
		"Initialize."
		self.horizontalAdvanceX = float(elementNode.attributes['horiz-adv-x'])
		self.loops = []
		self.unitsPerEM = unitsPerEM
		elementNode.attributes['fill'] = ''
		if 'd' not in elementNode.attributes:
			return
		PathReader(elementNode, self.loops, yAxisPointingUpward)

	def getSizedAdvancedLoops(self, fontSize, horizontalAdvanceX, yAxisPointingUpward=True):
		"Get loops for font size, advanced horizontally."
		multiplierX = fontSize / self.unitsPerEM
		multiplierY = multiplierX
		if not yAxisPointingUpward:
			multiplierY = -multiplierY
		sizedLoops = []
		for loop in self.loops:
			sizedLoop = []
			sizedLoops.append(sizedLoop)
			for point in loop:
				sizedLoop.append( complex(multiplierX * (point.real + horizontalAdvanceX), multiplierY * point.imag))
		return sizedLoops


class MatrixSVG:
	"Two by three svg matrix."
	def __init__(self, tricomplex=None):
		"Initialize."
		self.tricomplex = tricomplex

	def __repr__(self):
		"Get the string representation of this two by three svg matrix."
		return str(self.tricomplex)

	def getOtherTimesSelf(self, otherTricomplex):
		"Get the other matrix multiplied by this matrix."
		if otherTricomplex == None:
			return MatrixSVG(self.tricomplex)
		if self.tricomplex == None:
			return MatrixSVG(otherTricomplex)
		return MatrixSVG(getTricomplexTimesOther(otherTricomplex, self.tricomplex))

	def getSelfTimesOther(self, otherTricomplex):
		"Get this matrix multiplied by the other matrix."
		if otherTricomplex == None:
			return MatrixSVG(self.tricomplex)
		if self.tricomplex == None:
			return MatrixSVG(otherTricomplex)
		return MatrixSVG(getTricomplexTimesOther(self.tricomplex, otherTricomplex))

	def getTransformedPath(self, path):
		"Get transformed path."
		if self.tricomplex == None:
			return path
		complexX = self.tricomplex[0]
		complexY = self.tricomplex[1]
		complexTranslation = self.tricomplex[2]
		transformedPath = []
		for point in path:
			x = complexX.real * point.real + complexY.real * point.imag
			y = complexX.imag * point.real + complexY.imag * point.imag
			transformedPath.append(complex(x, y) + complexTranslation)
		return transformedPath

	def getTransformedPaths(self, paths):
		"Get transformed paths."
		if self.tricomplex == None:
			return paths
		transformedPaths = []
		for path in paths:
			transformedPaths.append(self.getTransformedPath(path))
		return transformedPaths


class PathReader:
	"Class to read svg path."
	def __init__(self, elementNode, loops, yAxisPointingUpward):
		"Add to path string to loops."
		self.controlPoints = None
		self.elementNode = elementNode
		self.loops = loops
		self.oldPoint = None
		self.outlinePaths = []
		self.path = []
		self.yAxisPointingUpward = yAxisPointingUpward
		pathString = elementNode.attributes['d'].replace(',', ' ')
		global globalProcessPathWordDictionary
		processPathWordDictionaryKeys = globalProcessPathWordDictionary.keys()
		for processPathWordDictionaryKey in processPathWordDictionaryKeys:
			pathString = pathString.replace( processPathWordDictionaryKey, ' %s ' % processPathWordDictionaryKey )
		self.words = getRightStripMinusSplit(pathString)
		for self.wordIndex in xrange( len( self.words ) ):
			word = self.words[ self.wordIndex ]
			if word in processPathWordDictionaryKeys:
				globalProcessPathWordDictionary[word](self)
		if len(self.path) > 0:
			self.outlinePaths.append(self.path)
		self.loops += getTransformedOutlineByPaths(elementNode, self.outlinePaths, yAxisPointingUpward)

	def addPathArc( self, end ):
		"Add an arc to the path."
		begin = self.getOldPoint()
		self.controlPoints = None
		radius = self.getComplexByExtraIndex(1)
		xAxisRotation = math.radians(float(self.words[self.wordIndex + 3]))
		largeArcFlag = euclidean.getBooleanFromValue(self.words[ self.wordIndex + 4 ])
		sweepFlag = euclidean.getBooleanFromValue(self.words[ self.wordIndex + 5 ])
		self.path += getArcComplexes(begin, end, largeArcFlag, radius, sweepFlag, xAxisRotation)
		self.wordIndex += 8

	def addPathCubic( self, controlPoints, end ):
		"Add a cubic curve to the path."
		begin = self.getOldPoint()
		self.controlPoints = controlPoints
		self.path += getCubicPoints( begin, controlPoints, end )
		self.wordIndex += 7

	def addPathCubicReflected( self, controlPoint, end ):
		"Add a cubic curve to the path from a reflected control point."
		begin = self.getOldPoint()
		controlPointBegin = begin
		if self.controlPoints != None:
			if len(self.controlPoints) == 2:
				controlPointBegin = begin + begin - self.controlPoints[-1]
		self.controlPoints = [controlPointBegin, controlPoint]
		self.path += getCubicPoints(begin, self.controlPoints, end)
		self.wordIndex += 5

	def addPathLine(self, lineFunction, point):
		"Add a line to the path."
		self.controlPoints = None
		self.path.append(point)
		self.wordIndex += 3
		self.addPathLineByFunction(lineFunction)

	def addPathLineAxis(self, point):
		"Add an axis line to the path."
		self.controlPoints = None
		self.path.append(point)
		self.wordIndex += 2

	def addPathLineByFunction( self, lineFunction ):
		"Add a line to the path by line function."
		while 1:
			if self.getFloatByExtraIndex() == None:
				return
			self.path.append(lineFunction())
			self.wordIndex += 2

	def addPathMove( self, lineFunction, point ):
		"Add an axis line to the path."
		self.controlPoints = None
		if len(self.path) > 0:
			self.outlinePaths.append(self.path)
			self.oldPoint = self.path[-1]
		self.path = [point]
		self.wordIndex += 3
		self.addPathLineByFunction(lineFunction)

	def addPathQuadratic( self, controlPoint, end ):
		"Add a quadratic curve to the path."
		begin = self.getOldPoint()
		self.controlPoints = [controlPoint]
		self.path += getQuadraticPoints(begin, controlPoint, end)
		self.wordIndex += 5

	def addPathQuadraticReflected( self, end ):
		"Add a quadratic curve to the path from a reflected control point."
		begin = self.getOldPoint()
		controlPoint = begin
		if self.controlPoints != None:
			if len( self.controlPoints ) == 1:
				controlPoint = begin + begin - self.controlPoints[-1]
		self.controlPoints = [ controlPoint ]
		self.path += getQuadraticPoints(begin, controlPoint, end)
		self.wordIndex += 3

	def getComplexByExtraIndex( self, extraIndex=0 ):
		'Get complex from the extraIndex.'
		return euclidean.getComplexByWords(self.words, self.wordIndex + extraIndex)

	def getComplexRelative(self):
		"Get relative complex."
		return self.getComplexByExtraIndex() + self.getOldPoint()

	def getFloatByExtraIndex( self, extraIndex=0 ):
		'Get float from the extraIndex.'
		totalIndex = self.wordIndex + extraIndex
		if totalIndex >= len(self.words):
			return None
		word = self.words[totalIndex]
		if word[: 1].isalpha():
			return None
		return euclidean.getFloatFromValue(word)

	def getOldPoint(self):
		'Get the old point.'
		if len(self.path) > 0:
			return self.path[-1]
		return self.oldPoint

	def processPathWordA(self):
		'Process path word A.'
		self.addPathArc( self.getComplexByExtraIndex( 6 ) )

	def processPathWorda(self):
		'Process path word a.'
		self.addPathArc(self.getComplexByExtraIndex(6) + self.getOldPoint())

	def processPathWordC(self):
		'Process path word C.'
		end = self.getComplexByExtraIndex( 5 )
		self.addPathCubic( [ self.getComplexByExtraIndex( 1 ), self.getComplexByExtraIndex(3) ], end )

	def processPathWordc(self):
		'Process path word C.'
		begin = self.getOldPoint()
		end = self.getComplexByExtraIndex( 5 )
		self.addPathCubic( [ self.getComplexByExtraIndex( 1 ) + begin, self.getComplexByExtraIndex(3) + begin ], end + begin )

	def processPathWordH(self):
		"Process path word H."
		beginY = self.getOldPoint().imag
		self.addPathLineAxis(complex(float(self.words[self.wordIndex + 1]), beginY))
		while 1:
			floatByExtraIndex = self.getFloatByExtraIndex()
			if floatByExtraIndex == None:
				return
			self.path.append(complex(floatByExtraIndex, beginY))
			self.wordIndex += 1

	def processPathWordh(self):
		"Process path word h."
		begin = self.getOldPoint()
		self.addPathLineAxis(complex(float(self.words[self.wordIndex + 1]) + begin.real, begin.imag))
		while 1:
			floatByExtraIndex = self.getFloatByExtraIndex()
			if floatByExtraIndex == None:
				return
			self.path.append(complex(floatByExtraIndex + self.getOldPoint().real, begin.imag))
			self.wordIndex += 1

	def processPathWordL(self):
		"Process path word L."
		self.addPathLine(self.getComplexByExtraIndex, self.getComplexByExtraIndex( 1 ))

	def processPathWordl(self):
		"Process path word l."
		self.addPathLine(self.getComplexRelative, self.getComplexByExtraIndex(1) + self.getOldPoint())

	def processPathWordM(self):
		"Process path word M."
		self.addPathMove(self.getComplexByExtraIndex, self.getComplexByExtraIndex(1))

	def processPathWordm(self):
		"Process path word m."
		self.addPathMove(self.getComplexRelative, self.getComplexByExtraIndex(1) + self.getOldPoint())

	def processPathWordQ(self):
		'Process path word Q.'
		self.addPathQuadratic( self.getComplexByExtraIndex( 1 ), self.getComplexByExtraIndex(3) )

	def processPathWordq(self):
		'Process path word q.'
		begin = self.getOldPoint()
		self.addPathQuadratic(self.getComplexByExtraIndex(1) + begin, self.getComplexByExtraIndex(3) + begin)

	def processPathWordS(self):
		'Process path word S.'
		self.addPathCubicReflected( self.getComplexByExtraIndex( 1 ), self.getComplexByExtraIndex(3) )

	def processPathWords(self):
		'Process path word s.'
		begin = self.getOldPoint()
		self.addPathCubicReflected(self.getComplexByExtraIndex(1) + begin, self.getComplexByExtraIndex(3) + begin)

	def processPathWordT(self):
		'Process path word T.'
		self.addPathQuadraticReflected( self.getComplexByExtraIndex( 1 ) )

	def processPathWordt(self):
		'Process path word t.'
		self.addPathQuadraticReflected(self.getComplexByExtraIndex(1) + self.getOldPoint())

	def processPathWordV(self):
		"Process path word V."
		beginX = self.getOldPoint().real
		self.addPathLineAxis(complex(beginX, float(self.words[self.wordIndex + 1])))
		while 1:
			floatByExtraIndex = self.getFloatByExtraIndex()
			if floatByExtraIndex == None:
				return
			self.path.append(complex(beginX, floatByExtraIndex))
			self.wordIndex += 1

	def processPathWordv(self):
		"Process path word v."
		begin = self.getOldPoint()
		self.addPathLineAxis(complex(begin.real, float(self.words[self.wordIndex + 1]) + begin.imag))
		while 1:
			floatByExtraIndex = self.getFloatByExtraIndex()
			if floatByExtraIndex == None:
				return
			self.path.append(complex(begin.real, floatByExtraIndex + self.getOldPoint().imag))
			self.wordIndex += 1

	def processPathWordZ(self):
		"Process path word Z."
		self.controlPoints = None
		if len(self.path) < 1:
			return
		self.loops.append(getChainMatrixSVGIfNecessary(self.elementNode, self.yAxisPointingUpward).getTransformedPath(self.path))
		self.oldPoint = self.path[0]
		self.path = []

	def processPathWordz(self):
		"Process path word z."
		self.processPathWordZ()


class SVGReader:
	"An svg carving."
	def __init__(self):
		"Add empty lists."
		self.loopLayers = []
		self.sliceDictionary = None
		self.stopProcessing = False
		self.z = 0.0

	def flipDirectLayer(self, loopLayer):
		"Flip the y coordinate of the layer and direct the loops."
		for loop in loopLayer.loops:
			for pointIndex, point in enumerate(loop):
				loop[pointIndex] = complex(point.real, -point.imag)
		triangle_mesh.sortLoopsInOrderOfArea(True, loopLayer.loops)
		for loopIndex, loop in enumerate(loopLayer.loops):
			isInsideLoops = euclidean.getIsInFilledRegion(loopLayer.loops[: loopIndex], euclidean.getLeftPoint(loop))
			intercircle.directLoop((not isInsideLoops), loop)

	def getLoopLayer(self):
		"Return the rotated loop layer."
		if self.z != None:
			loopLayer = euclidean.LoopLayer(self.z)
			self.loopLayers.append(loopLayer)
			self.z = None
		return self.loopLayers[-1]

	def parseSVG(self, fileName, svgText):
		"Parse SVG text and store the layers."
		self.fileName = fileName
		xmlParser = DocumentNode(fileName, svgText)
		self.documentElement = xmlParser.getDocumentElement()
		if self.documentElement == None:
			print('Warning, documentElement was None in parseSVG in SVGReader, so nothing will be done for:')
			print(fileName)
			return
		self.parseSVGByElementNode(self.documentElement)

	def parseSVGByElementNode(self, elementNode):
		"Parse SVG by elementNode."
		self.sliceDictionary = svg_writer.getSliceDictionary(elementNode)
		self.yAxisPointingUpward = euclidean.getBooleanFromDictionary(False, self.sliceDictionary, 'yAxisPointingUpward')
		self.processElementNode(elementNode)
		if not self.yAxisPointingUpward:
			for loopLayer in self.loopLayers:
				self.flipDirectLayer(loopLayer)

	def processElementNode(self, elementNode):
		'Process the xml element.'
		if self.stopProcessing:
			return
		lowerLocalName = elementNode.getNodeName().lower()
		global globalProcessSVGElementDictionary
		if lowerLocalName in globalProcessSVGElementDictionary:
			try:
				globalProcessSVGElementDictionary[lowerLocalName](elementNode, self)
			except:
				print('Warning, in processElementNode in svg_reader, could not process:')
				print(elementNode)
				traceback.print_exc(file=sys.stdout)
		for childNode in elementNode.childNodes:
			self.processElementNode(childNode)


globalFontFileNames = None
globalFontReaderDictionary = {}
globalGetTricomplexDictionary = {}
globalGetTricomplexFunctions = [
	getTricomplexmatrix,
	getTricomplexrotate,
	getTricomplexscale,
	getTricomplexskewX,
	getTricomplexskewY,
	getTricomplextranslate ]
globalProcessPathWordFunctions = [
	PathReader.processPathWordA,
	PathReader.processPathWorda,
	PathReader.processPathWordC,
	PathReader.processPathWordc,
	PathReader.processPathWordH,
	PathReader.processPathWordh,
	PathReader.processPathWordL,
	PathReader.processPathWordl,
	PathReader.processPathWordM,
	PathReader.processPathWordm,
	PathReader.processPathWordQ,
	PathReader.processPathWordq,
	PathReader.processPathWordS,
	PathReader.processPathWords,
	PathReader.processPathWordT,
	PathReader.processPathWordt,
	PathReader.processPathWordV,
	PathReader.processPathWordv,
	PathReader.processPathWordZ,
	PathReader.processPathWordz ]
globalProcessPathWordDictionary = {}
globalProcessSVGElementDictionary = {}
globalProcessSVGElementFunctions = [
	processSVGElementcircle,
	processSVGElementellipse,
	processSVGElementg,
	processSVGElementline,
	processSVGElementpath,
	processSVGElementpolygon,
	processSVGElementpolyline,
	processSVGElementrect,
	processSVGElementtext ]
globalSideAngle = 0.5 * math.pi / float( globalNumberOfCornerPoints )


addFunctionsToDictionary( globalGetTricomplexDictionary, globalGetTricomplexFunctions, 'getTricomplex')
addFunctionsToDictionary( globalProcessPathWordDictionary, globalProcessPathWordFunctions, 'processPathWord')
addFunctionsToDictionary( globalProcessSVGElementDictionary, globalProcessSVGElementFunctions, 'processSVGElement')
