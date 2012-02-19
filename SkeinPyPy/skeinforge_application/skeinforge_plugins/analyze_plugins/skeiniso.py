"""
This page is in the table of contents.
Skeiniso is an analyze viewer to display a gcode file in an isometric view.

The skeiniso manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Skeiniso

==Operation==
The default 'Activate Skeiniso' checkbox is off.  When it is on, the functions described below will work when called from the skeinforge toolchain, when it is off, the functions will not be called from the toolchain.  The functions will still be called, whether or not the 'Activate Skeiniso' checkbox is on, when skeiniso is run directly.

Skeiniso requires skeinforge comments in the gcode file to distinguish the loops and edges.  If the comments are deleted, all threads will be displayed as generic threads.  To get the penultimate file of the tool chain, just before export deletes the comments, select 'Save Penultimate Gcode' in export, and open the gcode file with the suffix '_penultimate.gcode' with skeiniso.

The viewer is simple, the viewpoint can only be moved in a sphere around the center of the model by changing the viewpoint latitude and longitude.  Different regions of the model can be hidden by setting the width of the thread to zero.  The alternating bands act as contour bands and their brightness and width can be changed.

==Settings==
===Animation===
====Animation Line Quickening====
Default is one.

The quickness of the tool animation over the quickness of the actual tool.

====Animation Slide Show Rate====
Default is two layers per second.

The rate, in layers per second, at which the layer changes when the soar or dive button is pressed..

===Axis Rulings===
Default is on.

When selected, rulings will be drawn on the axis lines.

===Banding===
====Band Height====
Default is five layers.

Defines the height of the band in layers, a pair of bands is twice that height.

====Bottom Band Brightness====
Default is 0.7.

Defines the ratio of the brightness of the bottom band over the brightness of the top band.  The higher it is the brighter the bottom band will be.

====Bottom Layer Brightness====
Default is one.

Defines the ratio of the brightness of the bottom layer over the brightness of the top layer.  With a low bottom layer brightness ratio the bottom of the model will be darker than the top of the model, as if it was being illuminated by a light just above the top.

====Bright Band Start====
Default choice is 'From the Top'.

The button group that determines where the bright band starts from.

=====From the Bottom=====
When selected, the bright bands will start from the bottom.

=====From the Top=====
When selected, the bright bands will start from the top.

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
Default is a huge number.

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

====Viewpoint Rotate====
The 'Viewpoint Rotate' tool will rotate the viewpoint around the origin, when the mouse is clicked and dragged on the canvas, or the arrow keys have been used and <Return> is pressed.  The viewpoint can also be moved by dragging the mouse.  The viewpoint latitude will be increased when the mouse is dragged from the center towards the edge.  The viewpoint longitude will be changed by the amount around the center the mouse is dragged.  This is not very intuitive, but I don't know how to do this the intuitive way and I have other stuff to develop.  If the shift key is pressed; if the latitude is changed more than the longitude, only the latitude will be changed, if the longitude is changed more only the longitude will be changed.

===Number of Fill Layers===
====Number of Fill Bottom Layers====
Default is one.

The "Number of Fill Bottom Layers" is the number of layers at the bottom which will be colored olive.

===Number of Fill Top Layers===
Default is one.

The "Number of Fill Top Layers" is the number of layers at the top which will be colored blue.

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

The "Screen Vertical Inset" determines how much the canvas will be inset in the vertical direction from the edge of screen, the higher the number the more it will be inset and the smaller it will be..

===Viewpoint===
====Viewpoint Latitude====
Default is fifteen degrees.

The "Viewpoint Latitude" is the latitude of the viewpoint, a latitude of zero is the top pole giving a top view, a latitude of ninety gives a side view and a latitude of 180 gives a bottom view.

====Viewpoint Longitude====
Default is 210 degrees.

The "Viewpoint Longitude" is the longitude of the viewpoint.

===Width===
The width of each type of thread and of each axis can be changed.  If the width is set to zero, the thread will not be visible.

====Width of Axis Negative Side====
Default is two.

Defines the width of the negative side of the axis.

====Width of Axis Positive Side====
Default is six.

Defines the width of the positive side of the axis.

====Width of Infill Thread====
Default is one.

The "Width of Infill Thread" sets the width of the green extrusion threads, those threads which are not loops and not part of the raft.

====Width of Fill Bottom Thread====
Default is two.

The "Width of Fill Bottom Thread" sets the width of the olive extrusion threads at the bottom of the model.

====Width of Fill Top Thread====
Default is two.

The "Width of Fill Top Thread" sets the width of the blue extrusion threads at the top of the model.

====Width of Loop Thread====
Default is three.

The "Width of Loop Thread" sets the width of the yellow loop threads, which are not edges.

====Width of Perimeter Inside Thread====
Default is eight.

The "Width of Perimeter Inside Thread" sets the width of the orange inside edge threads.

====Width of Perimeter Outside Thread====
Default is eight.

The "Width of Perimeter Outside Thread" sets the width of the red outside edge threads.

====Width of Raft Thread====
Default is one.

The "Width of Raft Thread" sets the width of the brown raft threads.

====Width of Selection Thread====
Default is six.

The "Width of Selection Thread" sets the width of the selected line.

====Width of Travel Thread====
Default is zero.

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
Below are examples of skeiniso being used.  These examples are run in a terminal in the folder which contains Screw Holder_penultimate.gcode and skeiniso.py.

> python skeiniso.py
This brings up the skeiniso dialog.

> python skeiniso.py Screw Holder_penultimate.gcode
This brings up the skeiniso viewer to view the gcode file.

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
from skeinforge_application.skeinforge_plugins.analyze_plugins.analyze_utilities import view_rotate
from skeinforge_application.skeinforge_utilities import skeinforge_polyfile
from skeinforge_application.skeinforge_utilities import skeinforge_profile
import math
import sys


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def compareLayerSequence( first, second ):
	"Get comparison in order to sort skein panes in ascending order of layer zone index then sequence index."
	if first.layerZoneIndex < second.layerZoneIndex:
		return - 1
	if first.layerZoneIndex > second.layerZoneIndex:
		return 1
	if first.sequenceIndex < second.sequenceIndex:
		return - 1
	return int( first.sequenceIndex > second.sequenceIndex )

def getNewRepository():
	'Get new repository.'
	return SkeinisoRepository()

def getWindowAnalyzeFile(fileName):
	"Skeiniso a gcode file."
	gcodeText = archive.getFileText(fileName)
	return getWindowAnalyzeFileGivenText(fileName, gcodeText)

def getWindowAnalyzeFileGivenText( fileName, gcodeText, repository=None):
	"Display a skeiniso gcode file for a gcode file."
	if gcodeText == '':
		return None
	if repository == None:
		repository = settings.getReadRepository( SkeinisoRepository() )
	skeinWindow = getWindowGivenTextRepository( fileName, gcodeText, repository )
	skeinWindow.updateDeiconify()
	return skeinWindow

def getWindowGivenTextRepository( fileName, gcodeText, repository ):
	"Display the gcode text in a skeiniso viewer."
	skein = SkeinisoSkein()
	skein.parseGcode( fileName, gcodeText, repository )
	return SkeinWindow( repository, skein )

def writeOutput(fileName, fileNamePenultimate, fileNameSuffix, filePenultimateWritten, gcodeText=''):
	"Write a skeinisoed gcode file for a skeinforge gcode file, if 'Activate Skeiniso' is selected."
	try:
		import Tkinter
	except:
		print('Warning, skeiniso will do nothing because Tkinter is not installed.')
		return
	repository = settings.getReadRepository( SkeinisoRepository() )
	if repository.activateSkeiniso.value:
		gcodeText = archive.getTextIfEmpty( fileNameSuffix, gcodeText )
		return getWindowAnalyzeFileGivenText( fileNameSuffix, gcodeText, repository )


class SkeinisoRepository( tableau.TableauRepository ):
	"A class to handle the skeiniso settings."
	def __init__(self):
		"Set the default settings, execute title & settings fileName."
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.analyze_plugins.skeiniso.html', self)
		self.baseNameSynonym = 'behold.csv'
		self.fileNameInput = settings.FileNameInput().getFromFileName( [ ('Gcode text files', '*.gcode') ], 'Open File for Skeiniso', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Skeiniso')
		self.activateSkeiniso = settings.BooleanSetting().getFromValue('Activate Skeiniso', self, False)
		self.addAnimation()
		self.axisRulings = settings.BooleanSetting().getFromValue('Axis Rulings', self, True )
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Banding -', self )
		self.bandHeight = settings.IntSpinUpdate().getFromValue( 0, 'Band Height (layers):', self, 10, 5 )
		self.bottomBandBrightness = settings.FloatSpinUpdate().getFromValue( 0.0, 'Bottom Band Brightness (ratio):', self, 1.0, 0.7 )
		self.bottomLayerBrightness = settings.FloatSpinUpdate().getFromValue( 0.0, 'Bottom Layer Brightness (ratio):', self, 1.0, 1.0 )
		self.brightBandStart = settings.MenuButtonDisplay().getFromName('Bright Band Start:', self )
		self.fromTheBottom = settings.MenuRadio().getFromMenuButtonDisplay( self.brightBandStart, 'From the Bottom', self, False )
		self.fromTheTop = settings.MenuRadio().getFromMenuButtonDisplay( self.brightBandStart, 'From the Top', self, True )
		settings.LabelSeparator().getFromRepository(self)
		self.drawArrows = settings.BooleanSetting().getFromValue('Draw Arrows', self, False )
		self.goAroundExtruderOffTravel = settings.BooleanSetting().getFromValue('Go Around Extruder Off Travel', self, False )
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Layers -', self )
		self.layer = settings.IntSpinNotOnMenu().getSingleIncrementFromValue( 0, 'Layer (index):', self, 912345678, 0 )
		self.layerExtraSpan = settings.IntSpinUpdate().getSingleIncrementFromValue( - 912345678, 'Layer Extra Span (integer):', self, 912345678, 912345678 )
		settings.LabelSeparator().getFromRepository(self)
		self.line = settings.IntSpinNotOnMenu().getSingleIncrementFromValue( 0, 'Line (index):', self, 912345678, 0 )
		self.mouseMode = settings.MenuButtonDisplay().getFromName('Mouse Mode:', self )
		self.displayLine = settings.MenuRadio().getFromMenuButtonDisplay( self.mouseMode, 'Display Line', self, True )
		self.viewMove = settings.MenuRadio().getFromMenuButtonDisplay( self.mouseMode, 'View Move', self, False )
		self.viewRotate = settings.MenuRadio().getFromMenuButtonDisplay( self.mouseMode, 'View Rotate', self, False )
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Number of Fill Layers -', self )
		self.numberOfFillBottomLayers = settings.IntSpinUpdate().getFromValue( 0, 'Number of Fill Bottom Layers (integer):', self, 5, 1 )
		self.numberOfFillTopLayers = settings.IntSpinUpdate().getFromValue( 0, 'Number of Fill Top Layers (integer):', self, 5, 1 )
		settings.LabelSeparator().getFromRepository(self)
		self.addScaleScreenSlide()
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Viewpoint -', self )
		self.viewpointLatitude = settings.FloatSpin().getFromValue( 0.0, 'Viewpoint Latitude (degrees):', self, 180.0, 15.0 )
		self.viewpointLongitude = settings.FloatSpin().getFromValue( 0.0, 'Viewpoint Longitude (degrees):', self, 360.0, 210.0 )
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Width -', self )
		self.widthOfAxisNegativeSide = settings.IntSpinUpdate().getFromValue( 0, 'Width of Axis Negative Side (pixels):', self, 10, 2 )
		self.widthOfAxisPositiveSide = settings.IntSpinUpdate().getFromValue( 0, 'Width of Axis Positive Side (pixels):', self, 10, 6 )
		self.widthOfFillBottomThread = settings.IntSpinUpdate().getFromValue( 0, 'Width of Fill Bottom Thread (pixels):', self, 10, 2 )
		self.widthOfFillTopThread = settings.IntSpinUpdate().getFromValue( 0, 'Width of Fill Top Thread (pixels):', self, 10, 2 )
		self.widthOfInfillThread = settings.IntSpinUpdate().getFromValue( 0, 'Width of Infill Thread (pixels):', self, 10, 1 )
		self.widthOfLoopThread = settings.IntSpinUpdate().getFromValue( 0, 'Width of Loop Thread (pixels):', self, 10, 2 )
		self.widthOfPerimeterInsideThread = settings.IntSpinUpdate().getFromValue( 0, 'Width of Perimeter Inside Thread (pixels):', self, 10, 8 )
		self.widthOfPerimeterOutsideThread = settings.IntSpinUpdate().getFromValue( 0, 'Width of Perimeter Outside Thread (pixels):', self, 10, 8 )
		self.widthOfRaftThread = settings.IntSpinUpdate().getFromValue( 0, 'Width of Raft Thread (pixels):', self, 10, 1 )
		self.widthOfSelectionThread = settings.IntSpinUpdate().getFromValue( 0, 'Width of Selection Thread (pixels):', self, 10, 6 )
		self.widthOfTravelThread = settings.IntSpinUpdate().getFromValue( 0, 'Width of Travel Thread (pixels):', self, 10, 0 )
		self.executeTitle = 'Skeiniso'

	def execute(self):
		"Write button has been clicked."
		fileNames = skeinforge_polyfile.getFileOrGcodeDirectory( self.fileNameInput.value, self.fileNameInput.wasCancelled )
		for fileName in fileNames:
			getWindowAnalyzeFile(fileName)


class SkeinisoSkein:
	"A class to write a get a scalable vector graphics text for a gcode skein."
	def __init__(self):
		self.coloredThread = []
		self.feedRateMinute = 960.1
		self.hasANestedRingBeenReached = False
		self.isEdge = False
		self.isLoop = False
		self.isOuter = False
		self.isThereALayerStartWord = False
		self.layerCount = settings.LayerCount()
		self.layerTops = []
		self.lineIndex = 0
		self.oldLayerZoneIndex = 0
		self.oldZ = - 999987654321.0
		self.skeinPane = None
		self.skeinPanes = []
		self.thirdLayerThickness = 0.133333

	def addToPath( self, line, location ):
		'Add a point to travel and maybe extrusion.'
		if self.oldLocation == None:
			return
		begin = self.scale * self.oldLocation - self.scaleCenterBottom
		end = self.scale * location - self.scaleCenterBottom
		displayString = '%s %s' % ( self.lineIndex + 1, line )
		tagString = 'colored_line_index: %s %s' % ( len( self.skeinPane.coloredLines ), len( self.skeinPanes ) - 1 )
		coloredLine = tableau.ColoredLine( begin, '', displayString, end, tagString )
		coloredLine.z = location.z
		self.skeinPane.coloredLines.append( coloredLine )
		self.coloredThread.append( coloredLine )

	def getLayerTop(self):
		"Get the layer top."
		if len( self.layerTops ) < 1:
			return - 9123456789123.9
		return self.layerTops[-1]

	def getLayerZoneIndex( self, z ):
		"Get the layer zone index."
		if self.layerTops[ self.oldLayerZoneIndex ] > z:
			if self.oldLayerZoneIndex == 0:
				return 0
			elif self.layerTops[ self.oldLayerZoneIndex - 1 ] < z:
				return self.oldLayerZoneIndex
		for layerTopIndex in xrange( len( self.layerTops ) ):
			layerTop = self.layerTops[ layerTopIndex ]
			if layerTop > z:
				self.oldLayerZoneIndex = layerTopIndex
				return layerTopIndex
		self.oldLayerZoneIndex = len( self.layerTops ) - 1
		return self.oldLayerZoneIndex

	def initializeActiveLocation(self):
		"Set variables to default."
		self.extruderActive = False
		self.oldLocation = None

	def linearCorner( self, splitLine ):
		"Update the bounding corners."
		location = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
		if self.extruderActive or self.goAroundExtruderOffTravel:
			self.cornerMaximum.maximize(location)
			self.cornerMinimum.minimize(location)
		self.oldLocation = location

	def linearMove( self, line, location ):
		"Get statistics for a linear move."
		if self.skeinPane == None:
			return
		self.addToPath(line, location)

	def moveColoredThreadToSkeinPane(self):
		'Move a colored thread to the skein pane.'
		if len( self.coloredThread ) <= 0:
			return
		layerZoneIndex = self.getLayerZoneIndex( self.coloredThread[0].z )
		if not self.extruderActive:
			self.setColoredThread( ( 190.0, 190.0, 190.0 ), self.skeinPane.travelLines ) #grey
			return
		self.skeinPane.layerZoneIndex = layerZoneIndex
		if self.isEdge:
			if self.isOuter:
				self.setColoredThread( ( 255.0, 0.0, 0.0 ), self.skeinPane.edgeOutsideLines ) #red
			else:
				self.setColoredThread( ( 255.0, 165.0, 0.0 ), self.skeinPane.edgeInsideLines ) #orange
			return
		if self.isLoop:
			self.setColoredThread( ( 255.0, 255.0, 0.0 ), self.skeinPane.loopLines ) #yellow
			return
		if not self.hasANestedRingBeenReached:
			self.setColoredThread( ( 165.0, 42.0, 42.0 ), self.skeinPane.raftLines ) #brown
			return
		if layerZoneIndex < self.repository.numberOfFillBottomLayers.value:
			self.setColoredThread( ( 128.0, 128.0, 0.0 ), self.skeinPane.fillBottomLines ) #olive
			return
		if layerZoneIndex >= self.firstTopLayer:
			self.setColoredThread( ( 0.0, 0.0, 255.0 ), self.skeinPane.fillTopLines ) #blue
			return
		self.setColoredThread( ( 0.0, 255.0, 0.0 ), self.skeinPane.infillLines ) #green

	def parseCorner(self, line):
		"Parse a gcode line and use the location to update the bounding corners."
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if tableau.getIsLayerStart(firstWord, self, splitLine):
			if firstWord == '(<layer>':
				self.layerTopZ = float(splitLine[1]) + self.thirdLayerThickness
			else:
				self.layerTopZ = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine).z + self.thirdLayerThickness
				self.layerTops.append( self.layerTopZ )
		if firstWord == 'G1':
			self.linearCorner(splitLine)
		elif firstWord == 'M101':
			self.extruderActive = True
		elif firstWord == 'M103':
			self.extruderActive = False
		elif firstWord == '(<layerHeight>':
			self.thirdLayerThickness = 0.33333333333 * float(splitLine[1])
		if firstWord == '(<nestedRing>)':
			if self.layerTopZ > self.getLayerTop():
				self.layerTops.append( self.layerTopZ )

	def parseGcode( self, fileName, gcodeText, repository ):
		"Parse gcode text and store the vector output."
		self.repository = repository
		self.fileName = fileName
		self.gcodeText = gcodeText
		self.initializeActiveLocation()
		self.cornerMaximum = Vector3(-987654321.0, -987654321.0, -987654321.0)
		self.cornerMinimum = Vector3(987654321.0, 987654321.0, 987654321.0)
		self.goAroundExtruderOffTravel = repository.goAroundExtruderOffTravel.value
		self.lines = archive.getTextLines(gcodeText)
		self.isThereALayerStartWord = (gcodec.getFirstWordIndexReverse('(<layer>', self.lines, 1) > -1)
		if self.isThereALayerStartWord:
			self.parseInitialization()
		else:
			print('')
			print('')
			print('')
			print('Warning, there are no skeinforge comments in this text, probably because they have been removed by export.')
			print('So there is no loop information, and therefore the lines will not be colored.')
			print('')
			print('To see the full information in an exported file, either deselect Delete Comments in export, or')
			print('select Save Penultimate Gcode in export, and open the generated file with the suffix _penultimate.gcode.')
			print('')
			print('')
			print('')
		for line in self.lines[self.lineIndex :]:
			self.parseCorner(line)
		self.oldZ = - 999987654321.0
		if len( self.layerTops ) > 0:
			self.layerTops[-1] += 912345678.9
		if len( self.layerTops ) > 1:
			self.oneMinusBrightnessOverTopLayerIndex = ( 1.0 - repository.bottomLayerBrightness.value ) / float( len( self.layerTops ) - 1 )
		self.firstTopLayer = len( self.layerTops ) - self.repository.numberOfFillTopLayers.value
		self.centerComplex = 0.5 * ( self.cornerMaximum.dropAxis() + self.cornerMinimum.dropAxis() )
		self.centerBottom = Vector3( self.centerComplex.real, self.centerComplex.imag, self.cornerMinimum.z )
		self.scale = repository.scale.value
		self.scaleCenterBottom = self.scale * self.centerBottom
		self.scaleCornerHigh = self.scale * self.cornerMaximum.dropAxis()
		self.scaleCornerLow = self.scale * self.cornerMinimum.dropAxis()
		print("The lower left corner of the skeiniso window is at %s, %s" % (self.cornerMinimum.x, self.cornerMinimum.y))
		print("The upper right corner of the skeiniso window is at %s, %s" % (self.cornerMaximum.x, self.cornerMaximum.y))
		self.cornerImaginaryTotal = self.cornerMaximum.y + self.cornerMinimum.y
		margin = complex( 5.0, 5.0 )
		self.marginCornerLow = self.scaleCornerLow - margin
		self.screenSize = margin + 2.0 * ( self.scaleCornerHigh - self.marginCornerLow )
		self.initializeActiveLocation()
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

	def parseLine(self, line):
		"Parse a gcode line and add it to the vector output."
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if tableau.getIsLayerStart(firstWord, self, splitLine):
			self.layerCount.printProgressIncrement('skeiniso')
			self.skeinPane = SkeinPane( len( self.skeinPanes ) )
			self.skeinPanes.append( self.skeinPane )
		if firstWord == 'G1':
			location = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
			self.linearMove(line, location)
			self.oldLocation = location
		elif firstWord == 'M101':
			self.moveColoredThreadToSkeinPane()
			self.extruderActive = True
		elif firstWord == 'M103':
			self.moveColoredThreadToSkeinPane()
			self.extruderActive = False
			self.isEdge = False
			self.isLoop = False
		elif firstWord == '(<loop>':
			self.isLoop = True
		elif firstWord == '(</loop>)':
			self.moveColoredThreadToSkeinPane()
			self.isLoop = False
		elif firstWord == '(<nestedRing>)':
			self.hasANestedRingBeenReached = True
		elif firstWord == '(<edge>':
			self.isEdge = True
			self.isOuter = ( splitLine[1] == 'outer')
		elif firstWord == '(</edge>)':
			self.moveColoredThreadToSkeinPane()
			self.isEdge = False
		if firstWord == 'G2' or firstWord == 'G3':
			relativeLocation = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
			relativeLocation.z = 0.0
			location = self.oldLocation + relativeLocation
			self.linearMove(line, location)
			self.oldLocation = location

	def setColoredLineColor( self, coloredLine, colorTuple ):
		'Set the color and stipple of the colored line.'
		layerZoneIndex = self.getLayerZoneIndex( coloredLine.z )
		multiplier = self.repository.bottomLayerBrightness.value
		if len( self.layerTops ) > 1:
			multiplier += self.oneMinusBrightnessOverTopLayerIndex * float( layerZoneIndex )
		bandIndex = layerZoneIndex / self.repository.bandHeight.value
		if self.repository.fromTheTop.value:
			brightZoneIndex = len( self.layerTops ) - 1 - layerZoneIndex
			bandIndex = brightZoneIndex / self.repository.bandHeight.value + 1
		if bandIndex % 2 == 0:
			multiplier *= self.repository.bottomBandBrightness.value
		red = settings.getWidthHex( int( colorTuple[0] * multiplier ), 2 )
		green = settings.getWidthHex( int( colorTuple[1] * multiplier ), 2 )
		blue = settings.getWidthHex( int( colorTuple[2] * multiplier ), 2 )
		coloredLine.colorName = '#%s%s%s' % ( red, green, blue )

	def setColoredThread( self, colorTuple, lineList ):
		'Set the colored thread, then move it to the line list and stipple of the colored line.'
		for coloredLine in self.coloredThread:
			self.setColoredLineColor( coloredLine, colorTuple )
		lineList += self.coloredThread
		self.coloredThread = []


class SkeinPane:
	"A class to hold the colored lines for a layer."
	def __init__( self, sequenceIndex ):
		"Create empty line lists."
		self.coloredLines = []
		self.edgeInsideLines = []
		self.edgeOutsideLines = []
		self.fillBottomLines = []
		self.fillTopLines = []
		self.index = 0
		self.infillLines = []
		self.layerZoneIndex = 0
		self.loopLines = []
		self.raftLines = []
		self.sequenceIndex = sequenceIndex
		self.travelLines = []


class Ruling:
	def __init__( self, modelDistance, roundedRulingText ):
		"Initialize the ruling."
		self.modelDistance = modelDistance
		self.roundedRulingText = roundedRulingText


class SkeinWindow( tableau.TableauWindow ):
	def __init__( self, repository, skein ):
		"Initialize the skein window."
		self.arrowshape = ( 24, 30, 9 )
		self.addCanvasMenuRootScrollSkein( repository, skein, '_skeiniso', 'Skeiniso')
		self.center = 0.5 * self.screenSize
		self.motionStippleName = 'gray75'
		halfCenter = 0.5 * self.center.real
		negativeHalfCenter = - halfCenter
		self.halfCenterModel = halfCenter / skein.scale
		negativeHalfCenterModel = - self.halfCenterModel
		roundedHalfCenter = euclidean.getThreeSignificantFigures( self.halfCenterModel )
		roundedNegativeHalfCenter = euclidean.getThreeSignificantFigures( negativeHalfCenterModel )
		self.negativeAxisLineX = tableau.ColoredLine( Vector3(), 'darkorange', None, Vector3( negativeHalfCenter ), 'X Negative Axis: Origin -> %s,0,0' % roundedNegativeHalfCenter )
		self.negativeAxisLineY = tableau.ColoredLine( Vector3(), 'gold', None, Vector3( 0.0, negativeHalfCenter ), 'Y Negative Axis: Origin -> 0,%s,0' % roundedNegativeHalfCenter )
		self.negativeAxisLineZ = tableau.ColoredLine( Vector3(), 'skyblue', None, Vector3( 0.0, 0.0, negativeHalfCenter ), 'Z Negative Axis: Origin -> 0,0,%s' % roundedNegativeHalfCenter )
		self.positiveAxisLineX = tableau.ColoredLine( Vector3(), 'darkorange', None, Vector3( halfCenter ), 'X Positive Axis: Origin -> %s,0,0' % roundedHalfCenter )
		self.positiveAxisLineY = tableau.ColoredLine( Vector3(), 'gold', None, Vector3( 0.0, halfCenter ), 'Y Positive Axis: Origin -> 0,%s,0' % roundedHalfCenter )
		self.positiveAxisLineZ = tableau.ColoredLine( Vector3(), 'skyblue', None, Vector3( 0.0, 0.0, halfCenter ), 'Z Positive Axis: Origin -> 0,0,%s' % roundedHalfCenter )
		self.repository.axisRulings.setUpdateFunction( self.setWindowToDisplaySaveUpdate )
		self.repository.bandHeight.setUpdateFunction( self.setWindowToDisplaySavePhoenixUpdate )
		self.repository.bottomBandBrightness.setUpdateFunction( self.setWindowToDisplaySavePhoenixUpdate )
		self.repository.bottomLayerBrightness.setUpdateFunction( self.setWindowToDisplaySavePhoenixUpdate )
		self.repository.fromTheBottom.setUpdateFunction( self.setWindowToDisplaySavePhoenixUpdate )
		self.repository.fromTheTop.setUpdateFunction( self.setWindowToDisplaySavePhoenixUpdate )
		self.setWindowNewMouseTool( display_line.getNewMouseTool, self.repository.displayLine )
		self.setWindowNewMouseTool( view_move.getNewMouseTool, self.repository.viewMove )
		self.setWindowNewMouseTool( view_rotate.getNewMouseTool, self.repository.viewRotate )
		self.repository.numberOfFillBottomLayers.setUpdateFunction( self.setWindowToDisplaySavePhoenixUpdate )
		self.repository.numberOfFillTopLayers.setUpdateFunction( self.setWindowToDisplaySavePhoenixUpdate )
		self.repository.viewpointLatitude.setUpdateFunction( self.setWindowToDisplaySaveUpdate )
		self.repository.viewpointLongitude.setUpdateFunction( self.setWindowToDisplaySaveUpdate )
		self.repository.widthOfAxisNegativeSide.setUpdateFunction( self.setWindowToDisplaySaveUpdate )
		self.repository.widthOfAxisPositiveSide.setUpdateFunction( self.setWindowToDisplaySaveUpdate )
		self.repository.widthOfFillBottomThread.setUpdateFunction( self.setWindowToDisplaySaveUpdate )
		self.repository.widthOfFillTopThread.setUpdateFunction( self.setWindowToDisplaySaveUpdate )
		self.repository.widthOfInfillThread.setUpdateFunction( self.setWindowToDisplaySaveUpdate )
		self.repository.widthOfLoopThread.setUpdateFunction( self.setWindowToDisplaySaveUpdate )
		self.repository.widthOfPerimeterInsideThread.setUpdateFunction( self.setWindowToDisplaySaveUpdate )
		self.repository.widthOfPerimeterOutsideThread.setUpdateFunction( self.setWindowToDisplaySaveUpdate )
		self.repository.widthOfRaftThread.setUpdateFunction( self.setWindowToDisplaySaveUpdate )
		self.addMouseToolsBind()
		self.negativeRulings = []
		self.positiveRulings = []
		for rulingIndex in xrange( 1, int( math.ceil( self.halfCenterModel / self.rulingSeparationWidthMillimeters ) ) ):
			modelDistance = rulingIndex * self.rulingSeparationWidthMillimeters
			self.negativeRulings.append( Ruling( modelDistance, self.getRoundedRulingText( 1, - modelDistance ) ) )
			self.positiveRulings.append( Ruling( modelDistance, self.getRoundedRulingText( 1, modelDistance ) ) )
		self.rulingExtentHalf = 0.5 * self.rulingExtent

	def drawRuling( self, projectiveSpace, relativeRulingEnd, ruling, tags, viewBegin, viewEnd ):
		"Draw ruling."
		alongWay = ruling.modelDistance / self.halfCenterModel
		oneMinusAlongWay = 1.0 - alongWay
		alongScreen = alongWay * viewEnd + oneMinusAlongWay * viewBegin
		alongScreenEnd = alongScreen + relativeRulingEnd
		self.canvas.create_line(
			alongScreen.real,
			alongScreen.imag,
			alongScreenEnd.real,
			alongScreenEnd.imag,
			fill = 'black',
			tags = tags,
			width = 2 )
		self.canvas.create_text( int( alongScreenEnd.real ) + 3, alongScreenEnd.imag, anchor = settings.Tkinter.W, text = ruling.roundedRulingText )

	def drawRulings( self, axisLine, projectiveSpace, rulings ):
		"Draw rulings for the axis line."
		if not self.repository.axisRulings.value:
			return
		viewBegin = self.getScreenView( axisLine.begin, projectiveSpace )
		viewEnd = self.getScreenView( axisLine.end, projectiveSpace )
		viewSegment = viewEnd - viewBegin
		viewSegmentLength = abs( viewSegment )
		if viewSegmentLength < self.rulingExtent:
			return
		normalizedViewSegment = viewSegment / viewSegmentLength
		relativeRulingEnd = complex( - normalizedViewSegment.imag, normalizedViewSegment.real )
		if normalizedViewSegment.imag > 0.0:
			relativeRulingEnd = complex( normalizedViewSegment.imag, - normalizedViewSegment.real )
		for ruling in rulings:
			self.drawRuling( projectiveSpace, relativeRulingEnd * self.rulingExtentHalf, ruling, axisLine.tagString, viewBegin, viewEnd )

	def drawSkeinPane( self, projectiveSpace, skeinPane ):
		"Draw colored lines."
		self.getDrawnColoredLines( skeinPane.raftLines, projectiveSpace, self.repository.widthOfRaftThread.value )
		self.getDrawnColoredLines( skeinPane.travelLines, projectiveSpace, self.repository.widthOfTravelThread.value )
		self.getDrawnColoredLines( skeinPane.fillBottomLines, projectiveSpace, self.repository.widthOfFillBottomThread.value )
		self.getDrawnColoredLines( skeinPane.fillTopLines, projectiveSpace, self.repository.widthOfFillTopThread.value )
		self.getDrawnColoredLines( skeinPane.infillLines, projectiveSpace, self.repository.widthOfInfillThread.value )
		self.getDrawnColoredLines( skeinPane.loopLines, projectiveSpace, self.repository.widthOfLoopThread.value )
		self.getDrawnColoredLines( skeinPane.edgeInsideLines, projectiveSpace, self.repository.widthOfPerimeterInsideThread.value )
		self.getDrawnColoredLines( skeinPane.edgeOutsideLines, projectiveSpace, self.repository.widthOfPerimeterOutsideThread.value )

	def drawXYAxisLines( self, projectiveSpace ):
		"Draw the x and y axis lines."
		if self.repository.widthOfAxisNegativeSide.value > 0:
			self.getDrawnColoredLineWithoutArrow( self.negativeAxisLineX, projectiveSpace, self.negativeAxisLineX.tagString, self.repository.widthOfAxisNegativeSide.value )
			self.getDrawnColoredLineWithoutArrow( self.negativeAxisLineY, projectiveSpace, self.negativeAxisLineY.tagString, self.repository.widthOfAxisNegativeSide.value )
		if self.repository.widthOfAxisPositiveSide.value > 0:
			self.getDrawnColoredLine('last', self.positiveAxisLineX, projectiveSpace, self.positiveAxisLineX.tagString, self.repository.widthOfAxisPositiveSide.value )
			self.getDrawnColoredLine('last', self.positiveAxisLineY, projectiveSpace, self.positiveAxisLineY.tagString, self.repository.widthOfAxisPositiveSide.value )

	def drawZAxisLine( self, projectiveSpace ):
		"Draw the z axis line."
		if self.repository.widthOfAxisNegativeSide.value > 0:
			self.getDrawnColoredLineWithoutArrow( self.negativeAxisLineZ, projectiveSpace, self.negativeAxisLineZ.tagString, self.repository.widthOfAxisNegativeSide.value )
		if self.repository.widthOfAxisPositiveSide.value > 0:
			self.getDrawnColoredLine('last', self.positiveAxisLineZ, projectiveSpace, self.positiveAxisLineZ.tagString, self.repository.widthOfAxisPositiveSide.value )

	def getCanvasRadius(self):
		"Get half of the minimum of the canvas height and width."
		return 0.5 * min( float( self.canvasHeight ), float( self.canvasWidth ) )

	def getCentered( self, coordinate ):
		"Get the centered coordinate."
		relativeToCenter = complex( coordinate.real - self.center.real, self.center.imag - coordinate.imag )
		if abs( relativeToCenter ) < 1.0:
			relativeToCenter = complex( 0.0, 1.0 )
		return relativeToCenter

	def getCenteredScreened( self, coordinate ):
		"Get the normalized centered coordinate."
		return self.getCentered( coordinate ) / self.getCanvasRadius()

	def getColoredLines(self):
		"Get the colored lines from the skein pane."
		if len(self.skeinPanes) == 0:
			return []
		return self.skeinPanes[ self.repository.layer.value ].coloredLines

	def getCopy(self):
		"Get a copy of this window."
		return SkeinWindow( self.repository, self.skein )

	def getCopyWithNewSkein(self):
		"Get a copy of this window with a new skein."
		return getWindowGivenTextRepository( self.skein.fileName, self.skein.gcodeText, self.repository )

	def getDrawnColoredLine( self, arrowType, coloredLine, projectiveSpace, tags, width ):
		"Draw colored line."
		viewBegin = self.getScreenView( coloredLine.begin, projectiveSpace )
		viewEnd = self.getScreenView( coloredLine.end, projectiveSpace )
		return self.canvas.create_line(
			viewBegin.real,
			viewBegin.imag,
			viewEnd.real,
			viewEnd.imag,
			fill = coloredLine.colorName,
			arrow = arrowType,
			tags = tags,
			width = width )

	def getDrawnColoredLineMotion( self, coloredLine, projectiveSpace, width ):
		"Draw colored line with motion stipple and tag."
		viewBegin = self.getScreenView( coloredLine.begin, projectiveSpace )
		viewEnd = self.getScreenView( coloredLine.end, projectiveSpace )
		return self.canvas.create_line(
			viewBegin.real,
			viewBegin.imag,
			viewEnd.real,
			viewEnd.imag,
			fill = coloredLine.colorName,
			arrow = 'last',
			arrowshape = self.arrowshape,
			stipple = self.motionStippleName,
			tags = 'mouse_item',
			width = width + 4 )

	def getDrawnColoredLines( self, coloredLines, projectiveSpace, width ):
		"Draw colored lines."
		if width <= 0:
			return
		drawnColoredLines = []
		for coloredLine in coloredLines:
			drawnColoredLines.append( self.getDrawnColoredLine( self.arrowType, coloredLine, projectiveSpace, coloredLine.tagString, width ) )
		return drawnColoredLines

	def getDrawnColoredLineWithoutArrow( self, coloredLine, projectiveSpace, tags, width ):
		"Draw colored line without an arrow."
		viewBegin = self.getScreenView( coloredLine.begin, projectiveSpace )
		viewEnd = self.getScreenView( coloredLine.end, projectiveSpace )
		return self.canvas.create_line(
			viewBegin.real,
			viewBegin.imag,
			viewEnd.real,
			viewEnd.imag,
			fill = coloredLine.colorName,
			tags = tags,
			width = width )

	def getDrawnSelectedColoredLine( self, coloredLine ):
		"Get the drawn selected colored line."
		projectiveSpace = euclidean.ProjectiveSpace().getByLatitudeLongitude( self.repository.viewpointLatitude.value, self.repository.viewpointLongitude.value )
		return self.getDrawnColoredLine( self.arrowType, coloredLine, projectiveSpace, 'selection_line', self.repository.widthOfSelectionThread.value )

	def getScreenComplex( self, pointComplex ):
		"Get the point in screen perspective."
		return complex( pointComplex.real, - pointComplex.imag ) + self.center

	def getScreenView( self, point, projectiveSpace ):
		"Get the point in screen view perspective."
		return self.getScreenComplex( projectiveSpace.getDotComplex(point) )

	def printHexadecimalColorName(self, name):
		"Print the color name in hexadecimal."
		colorTuple = self.canvas.winfo_rgb( name )
		print('#%s%s%s' % ( settings.getWidthHex( colorTuple[0], 2 ), settings.getWidthHex( colorTuple[1], 2 ), settings.getWidthHex( colorTuple[2], 2 ) ) )

	def update(self):
		"Update the screen."
		if len( self.skeinPanes ) < 1:
			return
		self.limitIndexSetArrowMouseDeleteCanvas()
		self.repository.viewpointLatitude.value = view_rotate.getBoundedLatitude( self.repository.viewpointLatitude.value )
		self.repository.viewpointLongitude.value = round( self.repository.viewpointLongitude.value, 1 )
		projectiveSpace = euclidean.ProjectiveSpace().getByLatitudeLongitude( self.repository.viewpointLatitude.value, self.repository.viewpointLongitude.value )
		skeinPanesCopy = self.getUpdateSkeinPanes()[:]
		skeinPanesCopy.sort( compareLayerSequence )
		if projectiveSpace.basisZ.z > 0.0:
			self.drawXYAxisLines( projectiveSpace )
		else:
			skeinPanesCopy.reverse()
			self.drawZAxisLine( projectiveSpace )
		for skeinPane in skeinPanesCopy:
			self.drawSkeinPane( projectiveSpace, skeinPane )
		if projectiveSpace.basisZ.z > 0.0:
			self.drawZAxisLine( projectiveSpace )
		else:
			self.drawXYAxisLines( projectiveSpace )
		if self.repository.widthOfAxisNegativeSide.value > 0:
			self.drawRulings( self.negativeAxisLineX, projectiveSpace, self.negativeRulings )
			self.drawRulings( self.negativeAxisLineY, projectiveSpace, self.negativeRulings )
			self.drawRulings( self.negativeAxisLineZ, projectiveSpace, self.negativeRulings )
		if self.repository.widthOfAxisPositiveSide.value > 0:
			self.drawRulings( self.positiveAxisLineX, projectiveSpace, self.positiveRulings )
			self.drawRulings( self.positiveAxisLineY, projectiveSpace, self.positiveRulings )
			self.drawRulings( self.positiveAxisLineZ, projectiveSpace, self.positiveRulings )
		self.setDisplayLayerIndex()


def main():
	"Display the skeiniso dialog."
	if len(sys.argv) > 1:
		settings.startMainLoopFromWindow( getWindowAnalyzeFile(' '.join(sys.argv[1 :])) )
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == "__main__":
	main()
