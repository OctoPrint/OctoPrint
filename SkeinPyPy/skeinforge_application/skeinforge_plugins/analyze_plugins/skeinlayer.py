"""
This page is in the table of contents.
Skeinlayer is an analyze viewer to display each layer of a gcode file.

The skeinlayer manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Skeinlayer

Skeinlayer is derived from Nophead's preview script.  The extruded lines are in the resistor colors red, orange, yellow, green, blue, purple & brown.  When the extruder is off, the travel line is grey.  Skeinlayer is useful for a detailed view of the extrusion, skeiniso is better to see the orientation of the shape.  To get an initial overview of the skein, when the skeinlayer display window appears, click the Soar button (double right arrow button beside the layer field).

==Operation==
The default 'Activate Skeinlayer' checkbox is on.  When it is on, the functions described below will work when called from the skeinforge toolchain, when it is off, the functions will not be called from the toolchain.  The functions will still be called, whether or not the 'Activate Skeinlayer' checkbox is on, when skeinlayer is run directly.  Skeinlayer has trouble separating the layers when it reads gcode without comments.

==Settings==
===Animation===
====Animation Line Quickening====
Default is one.

The quickness of the tool animation over the quickness of the actual tool.

====Animation Slide Show Rate====
Default is two layers per second.

The rate, in layers per second, at which the layer changes when the soar or dive button is pressed..

===Draw Arrows===
Default is on.

When selected, arrows will be drawn at the end of each line segment.

===Export Menu===
When the submenu in the export menu item in the file menu is clicked, an export canvas dialog will be displayed, which can export the canvas to a file.

===Go Around Extruder Off Travel===
Default is off.

When selected, the display will include the travel when the extruder is off, which means it will include the nozzle wipe path if any.

===Layers===
====Layer====
Default is zero.

On the display window, the Up button increases the 'Layer' by one, and the Down button decreases the layer by one.  When the layer displayed in the layer spin box is changed then <Return> is hit, the layer shown will be set to the spin box, to a mimimum of zero and to a maximum of the highest index layer.The Soar button increases the layer at the 'Animation Slide Show Rate', and the Dive (double left arrow button beside the layer field) button decreases the layer at the slide show rate.

====Layer Extra Span====
Default is zero.

The viewer will draw the layers in the range including the 'Layer' index and the 'Layer' index plus the 'Layer Extra Span'.  If the 'Layer Extra Span' is negative, the layers viewed will start at the 'Layer' index, plus the 'Layer Extra Span', and go up to and include the 'Layer' index.  If the 'Layer Extra Span' is zero, only the 'Layer' index layer will be displayed.  If the 'Layer Extra Span' is positive, the layers viewed will start at the 'Layer' index, and go up to and include the 'Layer' index plus the 'Layer Extra Span'.

===Line===
Default is zero.

The index of the selected line on the layer that is highlighted when the 'Display Line' mouse tool is chosen.  The line spin box up button increases the 'Line' by one.  If the line index of the layer goes over the index of the last line, the layer index will be increased by one and the new line index will be zero.  The down button decreases the line index by one.  If the line index goes below the index of the first line, the layer index will be decreased by one and the new line index will be at the last line.  When the line displayed in the line field is changed then <Return> is hit, the line shown will be set to the line field, to a mimimum of zero and to a maximum of the highest index line.  The Soar button increases the line at the speed at which the extruder would move, times the 'Animation Line Quickening' ratio, and the Dive (double left arrow button beside the line field) button decreases the line at the animation line quickening ratio.

===Mouse Mode===
Default is 'Display Line'.

The mouse tool can be changed from the 'Mouse Mode' menu button or picture button.  The mouse tools listen to the arrow keys when the canvas has the focus.  Clicking in the canvas gives the canvas the focus, and when the canvas has the focus a thick black border is drawn around the canvas.

====Display Line====
The 'Display Line' tool will display the highlight the selected line, and display the file line count, counting from one, and the gcode line itself.  When the 'Display Line' tool is active, clicking the canvas will select the closest line to the mouse click.

====Viewpoint Move====
The 'Viewpoint Move' tool will move the viewpoint in the xy plane when the mouse is clicked and dragged on the canvas.

===Numeric Pointer===
Default is on.

When selected, the distance along the ruler of the arrow pointers will be drawn next to the pointers.

===Scale===
Default is ten.

The scale setting is the scale of the image in pixels per millimeter, the higher the number, the greater the size of the display.

The zoom in mouse tool will zoom in the display at the point where the mouse was clicked, increasing the scale by a factor of two.  The zoom out tool will zoom out the display at the point where the mouse was clicked, decreasing the scale by a factor of two.

===Screen Inset===
====Screen Horizontal Inset====
Default is one hundred.

The "Screen Horizontal Inset" determines how much the canvas will be inset in the horizontal direction from the edge of screen, the higher the number the more it will be inset and the smaller it will be.

====Screen Vertical Inset====
Default is two hundred and twenty.

The "Screen Vertical Inset" determines how much the canvas will be inset in the vertical direction from the edge of screen, the higher the number the more it will be inset and the smaller it will be.

===Width===
The width of each type of thread and of each axis can be changed.  If the width is set to zero, the thread will not be visible.

====Width of Extrusion Thread====
Default is three.

The "Width of Extrusion Thread" sets the width of the extrusion threads.

====Width of Selection Thread====
Default is six.

The "Width of Selection Thread" sets the width of the selected line.

====Width of Travel Thread====
Default is one.

The "Width of Travel Thread" sets the width of the grey extruder off travel threads.

==Icons==
The dive, soar and zoom icons are from Mark James' soarSilk icon set 1.3 at:
http://www.famfamfam.com/lab/icons/silk/

==Gcodes==
An explanation of the gcodes is at:
http://reprap.org/bin/view/Main/Arduino_GCode_Interpreter

and at:
http://reprap.org/bin/view/Main/MCodeReference

A gode example is at:
http://forums.reprap.org/file.php?12,file=565

==Examples==
Below are examples of skeinlayer being used.  These examples are run in a terminal in the folder which contains Screw Holder_penultimate.gcode and skeinlayer.py.

> python skeinlayer.py
This brings up the skeinlayer dialog.

> python skeinlayer.py Screw Holder_penultimate.gcode
This brings up the skeinlayer viewer to view each layer of a gcode file.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_plugins.analyze_plugins.analyze_utilities import display_line
from skeinforge_application.skeinforge_plugins.analyze_plugins.analyze_utilities import tableau
from skeinforge_application.skeinforge_plugins.analyze_plugins.analyze_utilities import view_move
from skeinforge_application.skeinforge_utilities import skeinforge_polyfile
from skeinforge_application.skeinforge_utilities import skeinforge_profile
import os
import sys

__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getNewRepository():
	'Get new repository.'
	return SkeinlayerRepository()

def getRankIndex( rulingSeparationWidthMillimeters, screenOrdinate ):
	"Get rank index."
	return int( round( screenOrdinate / rulingSeparationWidthMillimeters ) )

def getWindowAnalyzeFile(fileName):
	"Display a gcode file in a skeinlayer window."
	gcodeText = archive.getFileText(fileName)
	return getWindowAnalyzeFileGivenText(fileName, gcodeText)

def getWindowAnalyzeFileGivenText( fileName, gcodeText, repository=None):
	"Display a gcode file in a skeinlayer window given the text."
	if gcodeText == '':
		return None
	if repository == None:
		repository = settings.getReadRepository( SkeinlayerRepository() )
	skeinWindow = getWindowGivenTextRepository( fileName, gcodeText, repository )
	skeinWindow.updateDeiconify()
	return skeinWindow

def getWindowGivenTextRepository( fileName, gcodeText, repository ):
	"Display a gcode file in a skeinlayer window given the text and settings."
	skein = SkeinlayerSkein()
	skein.parseGcode( fileName, gcodeText, repository )
	return SkeinWindow( repository, skein )

def writeOutput(fileName, fileNamePenultimate, fileNameSuffix, filePenultimateWritten, gcodeText=''):
	"Display a skeinlayered gcode file for a skeinforge gcode file, if 'Activate Skeinlayer' is selected."
	try:
		import Tkinter
	except:
		print('Warning, skeinlayer will do nothing because Tkinter is not installed.')
		return
	repository = settings.getReadRepository( SkeinlayerRepository() )
	if repository.activateSkeinlayer.value:
		gcodeText = archive.getTextIfEmpty( fileNameSuffix, gcodeText )
		return getWindowAnalyzeFileGivenText( fileNameSuffix, gcodeText, repository )


class SkeinlayerRepository( tableau.TableauRepository ):
	"A class to handle the skeinlayer settings."
	def __init__(self):
		"Set the default settings, execute title & settings fileName."
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.analyze_plugins.skeinlayer.html', self)
		self.baseNameSynonym = 'skeinview.csv'
		self.fileNameInput = settings.FileNameInput().getFromFileName( [ ('Gcode text files', '*.gcode') ], 'Open File for Skeinlayer', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Skeinlayer')
		self.activateSkeinlayer = settings.BooleanSetting().getFromValue('Activate Skeinlayer', self, False )
		self.addAnimation()
		self.drawArrows = settings.BooleanSetting().getFromValue('Draw Arrows', self, True )
		self.goAroundExtruderOffTravel = settings.BooleanSetting().getFromValue('Go Around Extruder Off Travel', self, False )
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Layers -', self )
		self.layer = settings.IntSpinNotOnMenu().getSingleIncrementFromValue( 0, 'Layer (index):', self, 912345678, 0 )
		self.layerExtraSpan = settings.IntSpinUpdate().getSingleIncrementFromValue( - 3, 'Layer Extra Span (integer):', self, 3, 0 )
		settings.LabelSeparator().getFromRepository(self)
		self.line = settings.IntSpinNotOnMenu().getSingleIncrementFromValue( 0, 'Line (index):', self, 912345678, 0 )
		self.mouseMode = settings.MenuButtonDisplay().getFromName('Mouse Mode:', self )
		self.displayLine = settings.MenuRadio().getFromMenuButtonDisplay( self.mouseMode, 'Display Line', self, True )
		self.viewMove = settings.MenuRadio().getFromMenuButtonDisplay( self.mouseMode, 'View Move', self, False )
		self.addScaleScreenSlide()
		self.showPosition = settings.BooleanSetting().getFromValue('Show Position', self, True )
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Width -', self )
		self.widthOfExtrusionThread = settings.IntSpinUpdate().getSingleIncrementFromValue( 0, 'Width of Extrusion Thread (pixels):', self, 5, 3 )
		self.widthOfSelectionThread = settings.IntSpinUpdate().getSingleIncrementFromValue( 0, 'Width of Selection Thread (pixels):', self, 10, 6 )
		self.widthOfTravelThread = settings.IntSpinUpdate().getSingleIncrementFromValue( 0, 'Width of Travel Thread (pixels):', self, 5, 1 )
		self.executeTitle = 'Skeinlayer'

	def execute(self):
		"Write button has been clicked."
		fileNames = skeinforge_polyfile.getFileOrGcodeDirectory( self.fileNameInput.value, self.fileNameInput.wasCancelled )
		for fileName in fileNames:
			getWindowAnalyzeFile(fileName)


class SkeinlayerSkein:
	"A class to write a get a scalable vector graphics text for a gcode skein."
	def __init__(self):
		'Initialize.'
		self.extrusionNumber = 0
		self.feedRateMinute = 960.1
		self.isThereALayerStartWord = False
		self.layerCount = settings.LayerCount()
		self.oldZ = - 999987654321.0
		self.skeinPane = None
		self.skeinPanes = []

	def addToPath( self, line, location ):
		"Add a point to travel and maybe extrusion."
		if self.oldLocation == None:
			return
		colorName = 'gray'
		locationComplex = location.dropAxis()
		oldLocationComplex = self.oldLocation.dropAxis()
		begin = self.getScreenCoordinates( oldLocationComplex )
		end = self.getScreenCoordinates( locationComplex )
		if self.extruderActive:
			colorName = self.colorNames[ self.extrusionNumber % len( self.colorNames ) ]
		displayString = '%s %s' % ( self.lineIndex + 1, line )
		tagString = 'colored_line_index: %s %s' % ( len( self.skeinPane ), len( self.skeinPanes ) - 1 )
		coloredLine = tableau.ColoredLine( begin, colorName, displayString, end, tagString )
		coloredLine.isExtrusionThread = self.extruderActive
		self.skeinPane.append( coloredLine )

	def getModelCoordinates( self, screenCoordinates ):
		"Get the model coordinates."
		modelCoordinates = ( screenCoordinates + self.marginCornerLow ) / self.scale
		return complex( modelCoordinates.real, self.cornerImaginaryTotal - modelCoordinates.imag )

	def getScreenCoordinates( self, pointComplex ):
		"Get the screen coordinates."
		pointComplex = complex( pointComplex.real, self.cornerImaginaryTotal - pointComplex.imag )
		return self.scale * pointComplex - self.marginCornerLow

	def initializeActiveLocation(self):
		"Set variables to default."
		self.extruderActive = False
		self.oldLocation = None

	def linearCorner( self, splitLine ):
		"Update the bounding corners."
		location = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
		if self.extruderActive or self.repository.goAroundExtruderOffTravel.value:
			self.cornerMaximum.maximize(location)
			self.cornerMinimum.minimize(location)
		self.oldLocation = location

	def linearMove( self, line, location ):
		"Get statistics for a linear move."
		if self.skeinPane != None:
			self.addToPath(line, location)

	def parseCorner(self, line):
		"Parse a gcode line and use the location to update the bounding corners."
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if firstWord == 'G1':
			self.linearCorner(splitLine)
		elif firstWord == 'M101':
			self.extruderActive = True
		elif firstWord == 'M103':
			self.extruderActive = False

	def parseGcode( self, fileName, gcodeText, repository ):
		"Parse gcode text and store the vector output."
		self.fileName = fileName
		self.gcodeText = gcodeText
		self.repository = repository
		self.initializeActiveLocation()
		self.cornerMaximum = Vector3(-987654321.0, -987654321.0, -987654321.0)
		self.cornerMinimum = Vector3(987654321.0, 987654321.0, 987654321.0)
		self.lines = archive.getTextLines(gcodeText)
		self.isThereALayerStartWord = (gcodec.getFirstWordIndexReverse('(<layer>', self.lines, 1) > -1)
		self.parseInitialization()
		for line in self.lines[self.lineIndex :]:
			self.parseCorner(line)
		self.cornerMaximumComplex = self.cornerMaximum.dropAxis()
		self.cornerMinimumComplex = self.cornerMinimum.dropAxis()
		self.scale = repository.scale.value
		self.scaleCornerHigh = self.scale * self.cornerMaximumComplex
		self.scaleCornerLow = self.scale * self.cornerMinimumComplex
		self.cornerImaginaryTotal = self.cornerMaximum.y + self.cornerMinimum.y
		self.margin = complex( 10.0, 10.0 )
		self.marginCornerHigh = self.scaleCornerHigh + self.margin
		self.marginCornerLow = self.scaleCornerLow - self.margin
		self.screenSize = self.marginCornerHigh - self.marginCornerLow
		self.initializeActiveLocation()
		self.colorNames = ['brown', 'red', 'orange', 'yellow', 'green', 'blue', 'purple']
		for self.lineIndex in xrange(self.lineIndex, len(self.lines)):
			line = self.lines[self.lineIndex]
			self.parseLine(line)

	def parseInitialization(self):
		'Parse gcode initialization and store the parameters.'
		for self.lineIndex in xrange(len(self.lines)):
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			if firstWord == '(</extruderInitialization>)':
				return
			elif firstWord == '(<operatingFeedRatePerSecond>':
				self.feedRateMinute = 60.0 * float(splitLine[1])
		self.lineIndex = 0

	def parseLine(self, line):
		"Parse a gcode line and add it to the vector output."
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if tableau.getIsLayerStart(firstWord, self, splitLine):
			self.extrusionNumber = 0
			self.layerCount.printProgressIncrement('skeinlayer')
			self.skeinPane = []
			self.skeinPanes.append( self.skeinPane )
		if firstWord == 'G1':
			location = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
			self.linearMove(line, location)
			self.oldLocation = location
		elif firstWord == 'M101':
			self.extruderActive = True
			self.extrusionNumber += 1
		elif firstWord == 'M103':
			self.extruderActive = False
		if firstWord == 'G2' or firstWord == 'G3':
			relativeLocation = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
			relativeLocation.z = 0.0
			location = self.oldLocation + relativeLocation
			self.linearMove(line, location)
			self.oldLocation = location


class SkeinWindow( tableau.TableauWindow ):
	def __init__(self, repository, skein):
		"Initialize the skein window.setWindowNewMouseTool"
		self.addCanvasMenuRootScrollSkein(repository, skein, '_skeinlayer', 'Skeinlayer')
		horizontalRulerBoundingBox = (0, 0, int( skein.screenSize.real ), self.rulingExtent)
		self.horizontalRulerCanvas = settings.Tkinter.Canvas(self.root, width = self.canvasWidth, height = self.rulingExtent, scrollregion=horizontalRulerBoundingBox)
		self.horizontalRulerCanvas.grid(row=1, column=2, columnspan=96, sticky=settings.Tkinter.E+settings.Tkinter.W)
		self.horizontalRulerCanvas['xscrollcommand'] = self.xScrollbar.set
		verticalRulerBoundingBox = (0, 0, self.rulingExtent, int(skein.screenSize.imag))
		self.verticalRulerCanvas = settings.Tkinter.Canvas(self.root, width=self.rulingExtent, height=self.canvasHeight, scrollregion=verticalRulerBoundingBox)
		self.verticalRulerCanvas.grid(row=2, rowspan=96, column=1, sticky=settings.Tkinter.N+settings.Tkinter.S)
		self.verticalRulerCanvas['yscrollcommand'] = self.yScrollbar.set
		self.xStringVar = settings.Tkinter.StringVar(self.root)
		self.xLabel = settings.Tkinter.Label(self.root, textvariable=self.xStringVar)
		self.xLabel.grid(row=0, column=3, sticky=settings.Tkinter.W)
		self.yStringVar = settings.Tkinter.StringVar(self.root)
		self.yLabel = settings.Tkinter.Label(self.root, textvariable=self.yStringVar)
		self.yLabel.grid(row=0, column=4, sticky=settings.Tkinter.W)
		self.setWindowNewMouseTool(display_line.getNewMouseTool, repository.displayLine)
		self.setWindowNewMouseTool(view_move.getNewMouseTool, repository.viewMove)
		repository.showPosition.setUpdateFunction(self.setWindowToDisplaySaveUpdate)
		repository.widthOfExtrusionThread.setUpdateFunction(self.setWindowToDisplaySaveUpdate)
		self.addMouseToolsBind()
		self.createRulers()

	def addHorizontalRulerRuling( self, xMillimeters ):
		"Add a ruling to the horizontal ruler."
		xPixel = self.skein.getScreenCoordinates( complex( xMillimeters, 0.0 ) ).real
		self.createVerticalLine( 0.0, xPixel )
		self.horizontalRulerCanvas.create_text( xPixel + 2, 0, anchor = settings.Tkinter.NW, text = self.getRoundedRulingText( 1, xMillimeters ) )
		cumulativeDistance = xMillimeters
		self.createVerticalLine( self.rulingExtentTiny, self.skein.getScreenCoordinates( complex( xMillimeters + self.separationWidthMillimetersTenth, 0.0 ) ).real )
		for subRulingIndex in xrange(4):
			cumulativeDistance += self.separationWidthMillimetersFifth
			self.createVerticalLine( self.rulingExtentShort, self.skein.getScreenCoordinates( complex( cumulativeDistance, 0.0 ) ).real )
			self.createVerticalLine( self.rulingExtentTiny, self.skein.getScreenCoordinates( complex( cumulativeDistance + self.separationWidthMillimetersTenth, 0.0 ) ).real )

	def addVerticalRulerRuling( self, yMillimeters ):
		"Add a ruling to the vertical ruler."
		fontHeight = 12
		yPixel = self.skein.getScreenCoordinates( complex( 0.0, yMillimeters ) ).imag
		self.createHorizontalLine( 0.0, yPixel )
		yPixel += 2
		roundedRulingText = self.getRoundedRulingText( 1, yMillimeters )
		effectiveRulingTextLength = len( roundedRulingText )
		if roundedRulingText.find('.') != - 1:
			effectiveRulingTextLength -= 1
		cumulativeDistance = yMillimeters
		self.createHorizontalLine( self.rulingExtentTiny, self.skein.getScreenCoordinates( complex( 0.0, yMillimeters + self.separationWidthMillimetersTenth ) ).imag )
		for subRulingIndex in xrange(4):
			cumulativeDistance += self.separationWidthMillimetersFifth
			self.createHorizontalLine( self.rulingExtentShort, self.skein.getScreenCoordinates( complex( 0.0, cumulativeDistance ) ).imag )
			self.createHorizontalLine( self.rulingExtentTiny, self.skein.getScreenCoordinates( complex( 0.0, cumulativeDistance + self.separationWidthMillimetersTenth ) ).imag )
		if effectiveRulingTextLength < 4:
			self.verticalRulerCanvas.create_text( 0, yPixel, anchor = settings.Tkinter.NW, text = roundedRulingText )
			return
		for character in roundedRulingText:
			if character == '.':
				yPixel -= fontHeight * 2 / 3
			self.verticalRulerCanvas.create_text( 0, yPixel, anchor = settings.Tkinter.NW, text = character )
			yPixel += fontHeight

	def createHorizontalLine( self, begin, yPixel ):
		"Create a horizontal line for the horizontal ruler."
		self.verticalRulerCanvas.create_line( begin, yPixel, self.rulingExtent, yPixel, fill = 'black')

	def createRulers(self):
		"Create the rulers.."
		self.rulingExtentShort = 0.382 * self.rulingExtent
		self.rulingExtentTiny = 0.764 * self.rulingExtent
		self.rulingExtentPointer = 0.5 * ( self.rulingExtentShort + self.rulingExtentTiny )
		self.rulingPointerRadius = self.rulingExtent - self.rulingExtentPointer
		self.textBoxHeight = int( 0.8 * self.rulingExtent )
		self.textBoxWidth = int( 2.5 * self.rulingExtent )
		self.separationWidthMillimetersFifth = 0.2 * self.rulingSeparationWidthMillimeters
		self.separationWidthMillimetersTenth = 0.1 * self.rulingSeparationWidthMillimeters
		rulingSeparationWidthPixels = self.getRulingSeparationWidthPixels( self.rank )
		marginOverScale = self.skein.margin / self.skein.scale
		cornerMaximumMargin = self.skein.cornerMaximumComplex + marginOverScale
		cornerMinimumMargin = self.skein.cornerMinimumComplex - marginOverScale
		xRankIndexHigh = getRankIndex( self.rulingSeparationWidthMillimeters, cornerMaximumMargin.real )
		xRankIndexLow = getRankIndex( self.rulingSeparationWidthMillimeters, cornerMinimumMargin.real )
		for xRankIndex in xrange( xRankIndexLow - 2, xRankIndexHigh + 2 ): # 1 is enough, 2 is to be on the safe side
			self.addHorizontalRulerRuling( xRankIndex * self.rulingSeparationWidthMillimeters )
		yRankIndexHigh = getRankIndex( self.rulingSeparationWidthMillimeters, cornerMaximumMargin.imag )
		yRankIndexLow = getRankIndex( self.rulingSeparationWidthMillimeters, cornerMinimumMargin.imag )
		for yRankIndex in xrange( yRankIndexLow - 2, yRankIndexHigh + 2 ): # 1 is enough, 2 is to be on the safe side
			self.addVerticalRulerRuling( yRankIndex * self.rulingSeparationWidthMillimeters )

	def createVerticalLine( self, begin, xPixel ):
		"Create a vertical line for the horizontal ruler."
		self.horizontalRulerCanvas.create_line( xPixel, begin, xPixel, self.rulingExtent, fill = 'black')

	def getColoredLines(self):
		"Get the colored lines from the skein pane."
		return self.skeinPanes[self.repository.layer.value]

	def getCopy(self):
		"Get a copy of this window."
		return SkeinWindow(self.repository, self.skein)

	def getCopyWithNewSkein(self):
		"Get a copy of this window with a new skein."
		return getWindowGivenTextRepository( self.skein.fileName, self.skein.gcodeText, self.repository )

	def getDrawnColoredLine( self, coloredLine, tags, width ):
		"Get the drawn colored line."
		return self.canvas.create_line(
			coloredLine.begin.real,
			coloredLine.begin.imag,
			coloredLine.end.real,
			coloredLine.end.imag,
			fill = coloredLine.colorName,
			arrow = self.arrowType,
			tags = tags,
			width = width )

	def getDrawnColoredLineIfThick( self, coloredLine, width ):
		"Get the drawn colored line if it has a positive thickness."
		if width > 0:
			return self.getDrawnColoredLine( coloredLine, coloredLine.tagString, width )

	def getDrawnSelectedColoredLine(self, coloredLine):
		"Get the drawn selected colored line."
		return self.getDrawnColoredLine(coloredLine, 'selection_line', self.repository.widthOfSelectionThread.value)

	def motion(self, event):
		"The mouse moved."
		self.mouseTool.motion(event)
		xString = ''
		yString = ''
		x = self.canvas.canvasx( event.x )
		y = self.canvas.canvasy( event.y )
		self.horizontalRulerCanvas.delete('pointer')
		self.horizontalRulerCanvas.create_polygon( x - self.rulingPointerRadius, self.rulingExtentPointer, x + self.rulingPointerRadius, self.rulingExtentPointer, x, self.rulingExtent, tag = 'pointer')
		self.verticalRulerCanvas.delete('pointer')
		self.verticalRulerCanvas.create_polygon( self.rulingExtentPointer, y - self.rulingPointerRadius, self.rulingExtentPointer, y + self.rulingPointerRadius, self.rulingExtent, y, tag = 'pointer')
		if self.repository.showPosition.value:
			motionCoordinate = complex(x, y)
			modelCoordinates = self.skein.getModelCoordinates( motionCoordinate )
			roundedXText = self.getRoundedRulingText(3, modelCoordinates.real)
			roundedYText = self.getRoundedRulingText(3, modelCoordinates.imag)
			xString = 'X: ' + roundedXText
			yString = 'Y: ' + roundedYText
		self.xStringVar.set(xString)
		self.yStringVar.set(yString)

	def qqqmotion(self, event):
		"The mouse moved."
		self.mouseTool.motion(event)
		x = self.canvas.canvasx( event.x )
		y = self.canvas.canvasy( event.y )
		self.horizontalRulerCanvas.delete('pointer')
		self.horizontalRulerCanvas.create_polygon( x - self.rulingPointerRadius, self.rulingExtentPointer, x + self.rulingPointerRadius, self.rulingExtentPointer, x, self.rulingExtent, tag = 'pointer')
		self.verticalRulerCanvas.delete('pointer')
		self.verticalRulerCanvas.create_polygon( self.rulingExtentPointer, y - self.rulingPointerRadius, self.rulingExtentPointer, y + self.rulingPointerRadius, self.rulingExtent, y, tag = 'pointer')
		if not self.repository.numericPointer.value:
			return
		motionCoordinate = complex(x, y)
		modelCoordinates = self.skein.getModelCoordinates( motionCoordinate )
		roundedXText = self.getRoundedRulingText( 3, modelCoordinates.real )
		yStart = self.canvas.canvasy( 0 )
		self.canvas.create_rectangle( x - 2, yStart, x + self.textBoxWidth, yStart + self.textBoxHeight + 5, fill = self.canvas['background'], tag = 'pointer')
		self.canvas.create_text( x, yStart + 5, anchor = settings.Tkinter.NW, tag = 'pointer', text = roundedXText )
		roundedYText = self.getRoundedRulingText( 3, modelCoordinates.imag )
		xStart = self.canvas.canvasx( 0 )
		self.canvas.create_rectangle( xStart, y - 2, xStart + self.textBoxWidth + 5, y + self.textBoxHeight, fill = self.canvas['background'], tag = 'pointer')
		self.canvas.create_text( xStart + 5, y, anchor = settings.Tkinter.NW, tag = 'pointer', text = roundedYText )
		xString = ''
		xString = 'X: ' + roundedXText
		self.xStringVar.set(xString)

	def relayXview( self, *args ):
		"Relay xview changes."
		self.canvas.xview( *args )
		self.horizontalRulerCanvas.xview( *args )

	def relayYview( self, *args ):
		"Relay yview changes."
		self.canvas.yview( *args )
		self.verticalRulerCanvas.yview( *args )

	def update(self):
		"Update the window."
		if len( self.skeinPanes ) < 1:
			return
		self.limitIndexSetArrowMouseDeleteCanvas()
		for coloredLines in self.getUpdateSkeinPanes():
			for coloredLine in coloredLines:
				if coloredLine.isExtrusionThread:
					self.getDrawnColoredLineIfThick( coloredLine, self.repository.widthOfExtrusionThread.value )
				else:
					self.getDrawnColoredLineIfThick( coloredLine, self.repository.widthOfTravelThread.value )
		self.setDisplayLayerIndex()


def main():
	"Display the skeinlayer dialog."
	if len(sys.argv) > 1:
		settings.startMainLoopFromWindow(getWindowAnalyzeFile(' '.join(sys.argv[1 :])))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == "__main__":
	main()
