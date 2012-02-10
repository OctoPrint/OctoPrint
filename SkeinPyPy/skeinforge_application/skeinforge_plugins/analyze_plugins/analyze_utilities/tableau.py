"""
Tableau has a couple of base classes for analyze viewers.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_plugins.analyze_plugins.analyze_utilities import zoom_in
from skeinforge_application.skeinforge_plugins.analyze_plugins.analyze_utilities import zoom_out
import math
import os

__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getGeometricDifference( first, second ):
	'Get the geometric difference of the two numbers.'
	return max( first, second ) / min( first, second )

def getGridHorizontalFrame(gridPosition):
	'Get the grid horizontal object with a frame from the grid position.'
	gridHorizontal = settings.GridHorizontal( 0, 0 )
	gridHorizontal.master = settings.Tkinter.Frame( gridPosition.master, borderwidth = 1, padx = 3, relief = 'raised')
	gridHorizontal.master.grid( row = gridPosition.row, column = gridPosition.column, sticky = settings.Tkinter.E )
	return gridHorizontal

def getIsLayerStart(firstWord, skein, splitLine):
	'Determine if the line is the start of a layer.'
	if skein.isThereALayerStartWord:
		return firstWord == '(<layer>'
	if firstWord != 'G1' and firstWord != 'G2' and firstWord != 'G3':
		return False
	location = gcodec.getLocationFromSplitLine(skein.oldLocation, splitLine)
	if location.z - skein.oldZ > 0.1:
		skein.oldZ = location.z
		return True
	return False

def getLengthMinusOneMinimumOne( elementList ):
	'Get the length of the length minus one, minimum one.'
	return max( 1, len( elementList ) - 1 )

def getPluginsDirectoryPath():
	'Get the plugins directory path.'
	return archive.getAnalyzePluginsDirectoryPath('export_canvas_plugins')

def getScrollbarCanvasPortion( scrollbar ):
	'Get the canvas portion of the scrollbar.'
	scrollbarBeginEnd = scrollbar.get()
	return scrollbarBeginEnd[1] - scrollbarBeginEnd[0]

def setStateNormalDisabled( active, widget ):
	'Set the state of the widget to normal if active and disabled if inactive.'
	if active:
		widget.config( state = settings.Tkinter.NORMAL )
	else:
		widget.config( state = settings.Tkinter.DISABLED )


class ColoredLine:
	'A colored index line.'
	def __init__( self, begin, colorName, displayString, end, tagString ):
		'Set the color name and corners.'
		self.begin = begin
		self.colorName = colorName
		self.displayString = displayString
		self.end = end
		self.tagString = tagString
	
	def __repr__(self):
		'Get the string representation of this colored index line.'
		return '%s, %s, %s, %s' % ( self.colorName, self.begin, self.end, self.tagString )


class ExportCanvasDialog:
	'A class to display the export canvas repository dialog.'
	def addPluginToMenu( self, canvas, fileName, menu, name, suffix ):
		'Add the display command to the menu.'
		self.canvas = canvas
		self.fileName = fileName
		self.name = name
		self.suffix = suffix
		menu.add_command( label = settings.getEachWordCapitalized( self.name ), command = self.display )

	def display(self):
		'Display the export canvas repository dialog.'
		for repositoryDialog in settings.globalRepositoryDialogListTable:
			if repositoryDialog.repository.lowerName == self.name:
				repositoryDialog.setCanvasFileNameSuffix(self.canvas, self.skein.fileName, self.suffix)
				settings.liftRepositoryDialogs(settings.globalRepositoryDialogListTable[repositoryDialog])
				return
		pluginModule = archive.getModuleWithDirectoryPath(getPluginsDirectoryPath(), self.name)
		if pluginModule == None:
			return None
		pluginRepository = pluginModule.getNewRepository()
		pluginRepository.setCanvasFileNameSuffix(self.canvas, self.fileName, self.suffix)
		settings.getDisplayedDialogFromConstructor(pluginRepository)


class TableauRepository:
	'The viewer base repository class.'
	def addAnimation(self):
		'Add the animation settings.'
		self.frameList = settings.FrameList().getFromValue('Frame List', self, [] )
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Animation -', self )
		self.animationLineQuickening = settings.FloatSpinUpdate().getFromValue( 0.5, 'Animation Line Quickening (ratio):', self, 4.5, 1.0 )
		self.animationSlideShowRate = settings.FloatSpinUpdate().getFromValue( 1.0, 'Animation Slide Show Rate (layers/second):', self, 5.0, 2.0 )
		settings.LabelSeparator().getFromRepository(self)

	def addScaleScreenSlide(self):
		'Add the scale, screen and slide show settings.'
		self.scale = settings.FloatSpinNotOnMenu().getFromValue( 10.0, 'Scale (pixels per millimeter):', self, 50.0, 15.0 )
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Screen Inset -', self )
		self.screenHorizontalInset = settings.IntSpin().getFromValue( 80, 'Screen Horizontal Inset (pixels):', self, 1000, 100 )
		self.screenVerticalInset = settings.IntSpin().getFromValue( 120, 'Screen Vertical Inset (pixels):', self, 1000, 220 )
		settings.LabelSeparator().getFromRepository(self)
		self.showGcode = settings.BooleanSetting().getFromValue('Show Gcode', self, True)

	def setToDisplaySave(self, event=None):
		'Set the setting values to the display, save the new values.'
		for menuEntity in self.menuEntities:
			if menuEntity in self.preferences:
				menuEntity.setToDisplay()
		settings.writeSettings(self)


class TableauWindow:
	def activateMouseModeTool(self):
		'Activate the mouse mode tool.'
		self.repository.setToDisplaySave()
		self.canvas.focus_set()
		self.createMouseModeTool()
		self.mouseTool.update()

	def addCanvasMenuRootScrollSkein(self, repository, skein, suffix, title):
		'Add the canvas, menu bar, scroll bar, skein panes, tableau repository, root and skein.'
		self.imagesDirectoryPath = archive.getFabmetheusUtilitiesPath('images')
		self.movementTextID = None
		self.mouseInstantButtons = []
		self.photoImages = {}
		self.repository = repository
		self.root = settings.Tkinter.Tk()
		self.gridPosition = settings.GridVertical(0, 1)
		self.gridPosition.master = self.root
		self.highlightThickness = 3
		self.root.title(os.path.basename(skein.fileName) + ' - ' + title)
		self.rulingExtent = 24
		self.rulingTargetSeparation = 150.0
		self.screenSize = skein.screenSize
		self.skein = skein
		self.skeinPanes = skein.skeinPanes
		self.suffix = suffix
		self.timerID = None
		repository.animationSlideShowRate.value = max(repository.animationSlideShowRate.value, 0.01)
		repository.animationSlideShowRate.value = min(repository.animationSlideShowRate.value, 85.0)
		repository.drawArrows.setUpdateFunction(self.setWindowToDisplaySaveUpdate)
		repository.goAroundExtruderOffTravel.setUpdateFunction(self.setWindowToDisplaySavePhoenixUpdate)
		repository.layerExtraSpan.setUpdateFunction(self.setWindowToDisplaySaveUpdate)
		repository.showGcode.setUpdateFunction(self.setWindowToDisplaySaveUpdate)
		repository.widthOfSelectionThread.setUpdateFunction(self.setWindowToDisplaySaveUpdate)
		repository.widthOfTravelThread.setUpdateFunction(self.setWindowToDisplaySaveUpdate)
		repository.window = self
		for menuRadio in repository.mouseMode.menuRadios:
			fileName = menuRadio.name.lower()
			fileName = fileName.replace(' ', '_') + '.ppm'
			menuRadio.mouseButton = self.getPhotoButtonGridIncrement(menuRadio.invoke, fileName, self.gridPosition)
		self.gridPosition = settings.GridHorizontal(2, 99)
		self.gridPosition.master = self.root
		self.gcodeStringVar = settings.Tkinter.StringVar(self.root)
		self.gcodeLabel = settings.Tkinter.Label(self.root, anchor = settings.Tkinter.W, textvariable = self.gcodeStringVar)
		self.gcodeLabel.grid(row = 0, column = 5, columnspan = 93, sticky = settings.Tkinter.W)
		from fabmetheus_utilities.hidden_scrollbar import HiddenScrollbar
		self.xScrollbar = HiddenScrollbar(self.root, orient = settings.Tkinter.HORIZONTAL)
		self.xScrollbar.grid(row = 98, column = 2, columnspan = 96, sticky = settings.Tkinter.E + settings.Tkinter.W)
		self.yScrollbar = HiddenScrollbar(self.root)
		self.yScrollbar.grid(row = 2, rowspan = 96, column = 99, sticky = settings.Tkinter.N + settings.Tkinter.S)
		self.canvasHeight = self.root.winfo_screenheight() - repository.screenVerticalInset.value
		self.canvasWidth = self.root.winfo_screenwidth() - repository.screenHorizontalInset.value
		scrollRegionBoundingBox = (0, 0, int(skein.screenSize.real), int(skein.screenSize.imag))
		self.canvas = settings.Tkinter.Canvas(self.root, highlightthickness = self.highlightThickness, width = self.canvasWidth, height = self.canvasHeight, scrollregion = scrollRegionBoundingBox)
		self.canvas.grid(row = 2, rowspan = 96, column = 2, columnspan = 96, sticky = settings.Tkinter.E + settings.Tkinter.W + settings.Tkinter.N + settings.Tkinter.S)
		self.fileHelpMenuBar = settings.FileHelpMenuBar(self.root)
		self.exportMenu = settings.Tkinter.Menu(self.fileHelpMenuBar.fileMenu, tearoff = 0)
		self.fileHelpMenuBar.fileMenu.add_cascade(label = 'Export', menu = self.exportMenu, underline = 0)
		exportCanvasPluginFileNames = archive.getPluginFileNamesFromDirectoryPath(getPluginsDirectoryPath())
		for exportCanvasPluginFileName in exportCanvasPluginFileNames:
			ExportCanvasDialog().addPluginToMenu(self.canvas, skein.fileName, self.exportMenu, exportCanvasPluginFileName, suffix)
		self.fileHelpMenuBar.fileMenu.add_separator()
		self.fileHelpMenuBar.completeMenu(self.close, repository, self.save, self)

	def addLayer( self, gridPosition ):
		'Add the layer frame items.'
		self.diveButton = self.getPhotoButtonGridIncrement( self.dive, 'dive.ppm', gridPosition )
		self.soarButton = self.getPhotoButtonGridIncrement( self.soar, 'soar.ppm', gridPosition )
		gridPosition.increment()
		settings.Tkinter.Label( gridPosition.master, text = 'Layer:').grid( row = gridPosition.row, column = gridPosition.column, sticky = settings.Tkinter.W )
		gridPosition.increment()
		self.limitIndex()
		self.layerEntry = settings.Tkinter.Spinbox( gridPosition.master, command = self.layerEntryReturnPressed, from_ = 0, increment = 1, to = getLengthMinusOneMinimumOne( self.skeinPanes ) )
		self.layerEntry.bind('<Return>', self.layerEntryReturnPressed )
		self.layerEntry.grid( row = gridPosition.row, column = gridPosition.column, sticky = settings.Tkinter.W )

	def addLine( self, gridPosition ):
		'Add the line frame items.'
		self.lineDiveButton = self.getPhotoButtonGridIncrement( self.lineDive, 'dive.ppm', gridPosition )
		self.lineSoarButton = self.getPhotoButtonGridIncrement( self.lineSoar, 'soar.ppm', gridPosition )
		gridPosition.increment()
		settings.Tkinter.Label( gridPosition.master, text = 'Line:').grid( row = gridPosition.row, column = gridPosition.column, sticky = settings.Tkinter.W )
		gridPosition.increment()
		self.lineEntry = settings.Tkinter.Spinbox( gridPosition.master, command = self.lineEntryReturnPressed, from_ = 0, increment = 1, to = getLengthMinusOneMinimumOne( self.getColoredLines() ) )
		self.lineEntry.bind('<Return>', self.lineEntryReturnPressed )
		self.lineEntry.grid( row = gridPosition.row, column = gridPosition.column, sticky = settings.Tkinter.W )

	def addMouseInstantTool( self, fileName, gridPosition, mouseInstantTool ):
		'Add the mouse instant tool and derived photo button.'
		mouseInstantTool.getReset(self)
		photoButton = self.getPhotoButtonGridIncrement( mouseInstantTool.click, fileName, gridPosition )
		mouseInstantTool.mouseButton = photoButton
		self.mouseInstantButtons.append( photoButton )

	def addMouseToolsBind(self):
		'Add the mouse tool and bind button one clicked, button one released and motion.'
		self.xScrollbar.config( command = self.relayXview )
		self.yScrollbar.config( command = self.relayYview )
		self.canvas['xscrollcommand'] = self.xScrollbar.set
		self.canvas['yscrollcommand'] = self.yScrollbar.set
		settings.CloseListener( self, self.destroyAllDialogWindows ).listenToWidget( self.canvas )
		self.canvasScreenCenter = 0.5 * complex( float( self.canvasWidth ) / float( self.screenSize.real ), float( self.canvasHeight ) / float( self.screenSize.imag ) )
		self.addPhotoImage('stop.ppm', self.gridPosition )
		self.gridPosition.increment()
		self.addLayer( getGridHorizontalFrame( self.gridPosition ) )
		self.gridPosition.increment()
		self.addLine( getGridHorizontalFrame( self.gridPosition ) )
		self.gridPosition.increment()
		self.addScale( getGridHorizontalFrame( self.gridPosition ) )
		self.gridPosition = settings.GridVertical( self.gridPosition.columnStart + 1, self.gridPosition.row )
		self.gridPosition.master = self.root
		for name in self.repository.frameList.value:
			entity = self.getEntityFromName( name )
			if entity != None:
				self.gridPosition.incrementGivenNumberOfColumns(3)
				entity.addToDialog( getGridHorizontalFrame( self.gridPosition ) )
		for menuRadio in self.repository.mouseMode.menuRadios:
			menuRadio.mouseTool = menuRadio.getNewMouseToolFunction().getReset(self)
			self.mouseTool = menuRadio.mouseTool
		self.createMouseModeTool()
		self.canvas.bind('<Button-1>', self.button1)
		self.canvas.bind('<ButtonRelease-1>', self.buttonRelease1)
		self.canvas.bind('<Configure>', self.setInsetToCanvas)
		self.canvas.bind('<KeyPress-Down>', self.keyPressDown)
		self.canvas.bind('<KeyPress-Left>', self.keyPressLeft)
		self.canvas.bind('<KeyPress-Right>', self.keyPressRight)
		self.canvas.bind('<KeyPress-Up>', self.keyPressUp)
		self.canvas.bind('<Motion>', self.motion)
		self.canvas.bind('<Return>', self.keyPressReturn)
		self.canvas.bind('<Shift-ButtonRelease-1>', self.shiftButtonRelease1)
		self.canvas.bind('<Shift-Motion>', self.shiftMotion)
		self.layerEntry.bind('<Destroy>', self.cancelTimer)
		self.root.grid_columnconfigure(44, weight = 1)
		self.root.grid_rowconfigure(44, weight = 1)
		self.resetPeriodicButtonsText()
		self.repository.animationLineQuickening.setUpdateFunction( self.repository.setToDisplaySave )
		self.repository.animationSlideShowRate.setUpdateFunction( self.repository.setToDisplaySave )
		self.repository.screenHorizontalInset.setUpdateFunction( self.redisplayWindowUpdate )
		self.repository.screenVerticalInset.setUpdateFunction( self.redisplayWindowUpdate )
		rankZeroSeperation = self.getRulingSeparationWidthPixels( 0 )
		zoom = self.rulingTargetSeparation / rankZeroSeperation
		self.rank = euclidean.getRank( zoom )
		rankTop = self.rank + 1
		seperationBottom = self.getRulingSeparationWidthPixels( self.rank )
		seperationTop = self.getRulingSeparationWidthPixels( rankTop )
		bottomDifference = getGeometricDifference( self.rulingTargetSeparation, seperationBottom )
		topDifference = getGeometricDifference( self.rulingTargetSeparation, seperationTop )
		if topDifference < bottomDifference:
			self.rank = rankTop
		self.rulingSeparationWidthMillimeters = euclidean.getIncrementFromRank( self.rank )
		self.canvas.focus_set()

	def addPhotoImage( self, fileName, gridPosition ):
		'Get a PhotoImage button, grid the button and increment the grid position.'
		photoImage = None
		try:
			photoImage = settings.Tkinter.PhotoImage( file = os.path.join( self.imagesDirectoryPath, fileName ), master = gridPosition.master )
		except:
			print('Image %s was not found in the images directory, so a text button will be substituted.' % fileName )
		untilDotFileName = archive.getUntilDot(fileName)
		self.photoImages[ untilDotFileName ] = photoImage
		return untilDotFileName

	def addScale( self, gridPosition ):
		'Add the line frame items.'
		self.addMouseInstantTool('zoom_out.ppm', gridPosition, zoom_out.getNewMouseTool() )
		self.addMouseInstantTool('zoom_in.ppm', gridPosition, zoom_in.getNewMouseTool() )
		gridPosition.increment()
		settings.Tkinter.Label( gridPosition.master, text = 'Scale:').grid( row = gridPosition.row, column = gridPosition.column, sticky = settings.Tkinter.W )
		gridPosition.increment()
		self.scaleEntry = settings.Tkinter.Spinbox( gridPosition.master, command = self.scaleEntryReturnPressed, from_ = 10.0, increment = 5.0, to = 100.0 )
		self.scaleEntry.bind('<Return>', self.scaleEntryReturnPressed )
		self.scaleEntry.grid( row = gridPosition.row, column = gridPosition.column, sticky = settings.Tkinter.W )

	def addSettingsMenuSetWindowGeometry( self, center ):
		'Add the settings menu, center the scroll region, update, and set the window geometry.'
		self.settingsMenu = settings.Tkinter.Menu( self.fileHelpMenuBar.menuBar, tearoff = 0 )
		self.fileHelpMenuBar.addMenuToMenuBar( 'Settings', self.settingsMenu )
		settings.addMenuEntitiesToMenuFrameable( self.settingsMenu, self.repository.menuEntities )
		self.relayXview( settings.Tkinter.MOVETO, center.real - self.canvasScreenCenter.real )
		self.relayYview( settings.Tkinter.MOVETO, center.imag - self.canvasScreenCenter.imag )
		self.root.withdraw()
		self.root.update_idletasks()
		movedGeometryString = '%sx%s+%s' % ( self.root.winfo_reqwidth(), self.root.winfo_reqheight(), '0+0')
		self.root.geometry( movedGeometryString )

	def button1(self, event):
		'The button was clicked.'
		self.mouseTool.button1(event)

	def buttonRelease1(self, event):
		'The button was released.'
		self.mouseTool.buttonRelease1(event)

	def cancel(self, event=None):
		'Set all entities to their saved state.'
		settings.cancelRepository(self.repository)

	def cancelTimer(self, event=None):
		'Cancel the timer and set it to none.'
		if self.timerID != None:
			self.canvas.after_cancel(self.timerID)
			self.timerID = None

	def cancelTimerResetButtons(self):
		'Cancel the timer and set it to none.'
		self.cancelTimer()
		self.resetPeriodicButtonsText()

	def close(self, event=None):
		'The dialog was closed.'
		try:
			self.root.after( 1, self.root.destroy ) # to get around 'Font Helvetica -12 still in cache.' segmentation bug, instead of simply calling self.root.destroy()
		except:
			pass

	def createMouseModeTool(self):
		'Create the mouse mode tool.'
		self.destroyMouseToolRaiseMouseButtons()
		for menuRadio in self.repository.mouseMode.menuRadios:
			if menuRadio.value:
				self.mouseTool = menuRadio.mouseTool
				menuRadio.mouseButton['relief'] = settings.Tkinter.SUNKEN

	def destroyAllDialogWindows(self):
		'Destroy all the dialog windows.'
		settings.writeSettings(self.repository)
		return
		for menuEntity in self.repository.menuEntities:
			lowerName = menuEntity.name.lower()
			if lowerName in settings.globalRepositoryDialogListTable:
				globalRepositoryDialogValues = settings.globalRepositoryDialogListTable[ lowerName ]
				for globalRepositoryDialogValue in globalRepositoryDialogValues:
					settings.quitWindow( globalRepositoryDialogValue.root )

	def destroyMouseToolRaiseMouseButtons(self):
		'Destroy the mouse tool and raise the mouse buttons.'
		self.mouseTool.destroyEverything()
		for menuRadio in self.repository.mouseMode.menuRadios:
			menuRadio.mouseButton['relief'] = settings.Tkinter.RAISED
		for mouseInstantButton in self.mouseInstantButtons:
			mouseInstantButton['relief'] = settings.Tkinter.RAISED

	def dive(self):
		'Dive, go down periodically.'
		oldDiveButtonText = self.diveButton['text']
		self.cancelTimerResetButtons()
		if oldDiveButtonText == 'stop':
			return
		self.diveCycle()

	def diveCycle(self):
		'Start the dive cycle.'
		self.setLayerIndex(self.repository.layer.value - 1)
		if self.repository.layer.value < 1:
			self.resetPeriodicButtonsText()
			return
		self.setButtonImageText( self.diveButton, 'stop')
		self.timerID = self.canvas.after( self.getSlideShowDelay(), self.diveCycle )

	def getAnimationLineDelay( self, coloredLine ):
		'Get the animation line delay in milliseconds.'
#		maybe later, add animation along line
#		nextLayerIndex = self.repository.layer.value
#		nextLineIndex = self.repository.line.value + 1
#		coloredLinesLength = len( self.getColoredLines() )
#		self.skein.feedRateMinute
#		if nextLineIndex >= coloredLinesLength:
#			if nextLayerIndex + 1 < len( self.skeinPanes ):
#				nextLayerIndex += 1
#				nextLineIndex = 0
#			else:
#				nextLineIndex = self.repository.line.value
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon( coloredLine.displayString )
		self.skein.feedRateMinute = gcodec.getFeedRateMinute( self.skein.feedRateMinute, splitLine )
		feedRateSecond = self.skein.feedRateMinute / 60.0
		coloredLineLength = abs( coloredLine.end - coloredLine.begin ) / self.repository.scale.value
		duration = coloredLineLength / feedRateSecond
		animationLineDelay = int( round( 1000.0 * duration / self.repository.animationLineQuickening.value ) )
		return max( animationLineDelay, 1 )

	def getDrawnLineText( self, location, tags, text ):
		'Get the line text drawn on the canvas.'
		if not self.repository.showGcode.value:
			return
		anchorTowardCenter = settings.Tkinter.N
		if location.imag > float( self.canvasHeight ) * 0.1:
			anchorTowardCenter = settings.Tkinter.S
		if location.real > float( self.canvasWidth ) * 0.7:
			anchorTowardCenter += settings.Tkinter.E
		else:
			anchorTowardCenter += settings.Tkinter.W
		return self.canvas.create_text( int( location.real ), int( location.imag ), anchor = anchorTowardCenter, tags = tags, text = text )

	def getEntityFromName(self, name):
		'Get the entity of the given name.'
		for entity in self.repository.displayEntities:
			if entity.name == name:
				return entity
		return None

	def getPhotoButtonGridIncrement( self, commandFunction, fileName, gridPosition ):
		'Get a PhotoImage button, grid the button and increment the grid position.'
		gridPosition.increment()
		untilDotFileName = self.addPhotoImage( fileName, gridPosition )
		photoImage = self.photoImages[ untilDotFileName ]
		photoButton = settings.Tkinter.Button( gridPosition.master, activebackground = 'black', activeforeground = 'white', command = commandFunction, text = untilDotFileName )
		if photoImage != None:
			photoButton['image'] = photoImage
		photoButton.grid( row = gridPosition.row, column = gridPosition.column, sticky = settings.Tkinter.W )
		return photoButton

	def getRoundedRulingText( self, extraDecimalPlaces, number ):
		'Get the rounded ruling text.'
		rulingText = euclidean.getRoundedToPlacesString( extraDecimalPlaces - math.floor( math.log10( self.rulingSeparationWidthMillimeters ) ), number )
		if self.rulingSeparationWidthMillimeters < .99:
			return rulingText
		if rulingText[ - len('.0') : ] == '.0':
			return rulingText[ : - len('.0') ]
		return rulingText

	def getRulingSeparationWidthPixels( self, rank ):
		'Get the separation width in pixels.'
		return euclidean.getIncrementFromRank( rank ) * self.skein.scale

	def getScrollPaneCenter(self):
		'Get the center of the scroll pane.'
		return self.getScrollPaneFraction() + self.canvasScreenCenter

	def getScrollPaneFraction(self):
		'Get the scroll pane top left.'
		return complex( self.xScrollbar.get()[0], self.yScrollbar.get()[0] )

	def getSlideShowDelay(self):
		'Get the slide show delay in milliseconds.'
		slideShowDelay = int( round( 1000.0 / self.repository.animationSlideShowRate.value ) )
		return max( slideShowDelay, 1 )

	def getUpdateSkeinPanes(self):
		'Get the update skein panes.'
		layerPlusExtraSpan = self.repository.layer.value + self.repository.layerExtraSpan.value
		layersFrom = max( 0, min( self.repository.layer.value, layerPlusExtraSpan ) )
		layersTo = min( len( self.skeinPanes ), max( self.repository.layer.value, layerPlusExtraSpan ) + 1 )
		return self.skeinPanes[ layersFrom : layersTo ]

	def isLineBelowZeroSetLayer(self):
		'Determine if the line index is below zero, and if so set the layer index.'
		if self.repository.line.value >= 0:
			return False
		self.repository.line.value = 0
		if self.repository.layer.value > 0:
			self.setLayerIndex( self.repository.layer.value - 1 )
			return True
		return False

	def isLineBeyondListSetLayer(self):
		'Determine if the line index is beyond the end of the list, and if so set the layer index.'
		coloredLinesLength = len( self.getColoredLines() )
		if self.repository.line.value < coloredLinesLength:
			return False
		self.repository.line.value = coloredLinesLength - 1
		if self.repository.layer.value < len( self.skeinPanes ) - 1:
			self.setLayerIndex( self.repository.layer.value + 1 )
			return True
		return False

	def keyPressDown(self, event):
		'The down arrow was pressed.'
		self.mouseTool.keyPressDown(event)

	def keyPressLeft(self, event):
		'The left arrow was pressed.'
		self.mouseTool.keyPressLeft(event)

	def keyPressReturn(self, event):
		'The return key was pressed.'
		self.mouseTool.keyPressReturn(event)

	def keyPressRight(self, event):
		'The right arrow was pressed.'
		self.mouseTool.keyPressRight(event)

	def keyPressUp(self, event):
		'The up arrow was pressed.'
		self.mouseTool.keyPressUp(event)

	def layerEntryReturnPressed(self, event=None):
		'The layer index entry return was pressed.'
		self.setLayerIndex( int( self.layerEntry.get() ) )

	def limitIndex(self):
		'Limit the index so it is not below zero or above the top.'
		self.repository.layer.value = max( 0, self.repository.layer.value )
		self.repository.layer.value = min( len( self.skeinPanes ) - 1, self.repository.layer.value )

	def limitIndexSetArrowMouseDeleteCanvas(self):
		'Limit the index, set the arrow type, and delete all the canvas items.'
		self.limitIndex()
		self.arrowType = None
		if self.repository.drawArrows.value:
			self.arrowType = 'last'
		self.canvas.delete( settings.Tkinter.ALL )

	def lineDive(self):
		'Line dive, go down periodically.'
		oldLineDiveButtonText = self.lineDiveButton['text']
		self.cancelTimerResetButtons()
		if oldLineDiveButtonText == 'stop':
			return
		self.lineDiveCycle()

	def lineDiveCycle(self):
		'Start the line dive cycle.'
		self.cancelTimer()
		self.repository.line.value -= 1
		if self.repository.line.value < 0:
			self.repository.line.value = 0
			if self.repository.layer.value == 0:
				self.resetPeriodicButtonsText()
				self.setLineButtonsState()
				return
			self.setLayerIndex( self.repository.layer.value - 1 )
		else:
			self.updateMouseToolIfSelection()
		self.setLineButtonsState()
		self.setButtonImageText( self.lineDiveButton, 'stop')
		coloredLine = self.getColoredLines()[ self.repository.line.value ]
		self.timerID = self.canvas.after( self.getAnimationLineDelay( coloredLine ), self.lineDiveCycle )

	def lineEntryReturnPressed(self, event=None):
		'The line index entry return was pressed.'
		self.repository.line.value = int( self.lineEntry.get() )
		if self.isLineBelowZeroSetLayer():
			return
		if self.isLineBeyondListSetLayer():
			return
		self.cancelTimerResetButtons()
		self.updateMouseToolIfSelection()
		self.setLineButtonsState()

	def lineSoar(self):
		'Line soar, go up periodically.'
		oldLineSoarButtonText = self.lineSoarButton['text']
		self.cancelTimerResetButtons()
		if oldLineSoarButtonText == 'stop':
			return
		self.lineSoarCycle()

	def lineSoarCycle(self):
		'Start the line soar cycle.'
		self.cancelTimer()
		self.repository.line.value += 1
		coloredLinesLength = len( self.getColoredLines() )
		if self.repository.line.value >= coloredLinesLength:
			self.repository.line.value = coloredLinesLength - 1
			if self.repository.layer.value > len( self.skeinPanes ) - 2:
				self.resetPeriodicButtonsText()
				self.setLineButtonsState()
				return
			self.setLayerIndex( self.repository.layer.value + 1 )
		else:
			self.updateMouseToolIfSelection()
		self.setLineButtonsState()
		self.setButtonImageText( self.lineSoarButton, 'stop')
		coloredLine = self.getColoredLines()[ self.repository.line.value ]
		self.timerID = self.canvas.after( self.getAnimationLineDelay( coloredLine ), self.lineSoarCycle )

	def motion(self, event):
		'The mouse moved.'
		self.mouseTool.motion(event)

	def phoenixUpdate(self):
		'Update the skein, and deiconify a new window and destroy the old.'
		self.updateNewDestroyOld( self.getScrollPaneCenter() )

	def redisplayWindowUpdate(self, event=None):
		'Deiconify a new window and destroy the old.'
		self.repository.setToDisplaySave()
		self.getCopy().updateDeiconify( self.getScrollPaneCenter() )
		self.root.after( 1, self.root.destroy ) # to get around 'Font Helvetica -12 still in cache.' segmentation bug, instead of simply calling self.root.destroy()

	def relayXview( self, *args ):
		'Relay xview changes.'
		self.canvas.xview( *args )

	def relayYview( self, *args ):
		'Relay yview changes.'
		self.canvas.yview( *args )

	def resetPeriodicButtonsText(self):
		'Reset the text of the periodic buttons.'
		self.setButtonImageText( self.diveButton, 'dive')
		self.setButtonImageText( self.soarButton, 'soar')
		self.setButtonImageText( self.lineDiveButton, 'dive')
		self.setButtonImageText( self.lineSoarButton, 'soar')

	def save(self):
		'Set the setting values to the display, save the new values.'
		for menuEntity in self.repository.menuEntities:
			if menuEntity in self.repository.preferences:
				menuEntity.setToDisplay()
		settings.writeSettings(self.repository)

	def scaleEntryReturnPressed(self, event=None):
		'The scale entry return was pressed.'
		self.repository.scale.value = float( self.scaleEntry.get() )
		self.phoenixUpdate()

	def setButtonImageText( self, button, text ):
		'Set the text of the e periodic buttons.'
		photoImage = self.photoImages[ text ]
		if photoImage != None:
			button['image'] = photoImage
		button['text'] = text

	def setDisplayLayerIndex(self):
		'Set the display of the layer index entry field and buttons.'
		coloredLines = self.getColoredLines()
		isAboveFloor = self.repository.layer.value > 0
		isBelowCeiling = self.repository.layer.value < len( self.skeinPanes ) - 1
		setStateNormalDisabled( isAboveFloor, self.diveButton )
		setStateNormalDisabled( isBelowCeiling, self.soarButton )
		self.setLineButtonsState()
		settings.setEntryText( self.layerEntry, self.repository.layer.value )
		settings.setEntryText( self.lineEntry, self.repository.line.value )
		settings.setEntryText( self.scaleEntry, self.repository.scale.value )
		self.mouseTool.update()

	def setInsetToCanvas(self, event=None):
		'Set the repository insets to the canvas.'
		if self.root.state() != 'normal':
			return
		excessExtent = self.highlightThickness + self.highlightThickness
		screenHorizontalInset = self.repository.screenHorizontalInset
		screenVerticalInset = self.repository.screenVerticalInset
		oldHorizontalValue = screenHorizontalInset.value
		oldVerticalValue = screenVerticalInset.value
		screenHorizontalInset.value = self.root.winfo_screenwidth() - self.canvas.winfo_width() + excessExtent
		if not self.yScrollbar.visible:
			screenHorizontalInset.value += self.yScrollbar.winfo_reqwidth()
		screenHorizontalInset.setStateToValue()
		screenVerticalInset.value = self.root.winfo_screenheight() - self.canvas.winfo_height() + excessExtent
		if not self.xScrollbar.visible:
			screenVerticalInset.value += self.xScrollbar.winfo_reqheight()
		screenVerticalInset.setStateToValue()
		if oldHorizontalValue != screenHorizontalInset.value or oldVerticalValue != screenVerticalInset.value:
			self.repository.setToDisplaySave()

	def setLayerIndex( self, layerIndex ):
		'Set the layer index.'
		self.cancelTimerResetButtons()
		oldLayerIndex = self.repository.layer.value
		self.repository.layer.value = layerIndex
		self.limitIndex()
		coloredLines = self.getColoredLines()
		if self.repository.layer.value < oldLayerIndex:
			self.repository.line.value = len( coloredLines ) - 1
			self.lineEntry['to'] = getLengthMinusOneMinimumOne( coloredLines )
		if self.repository.layer.value > oldLayerIndex:
			self.repository.line.value = 0
			self.lineEntry['to'] = getLengthMinusOneMinimumOne( coloredLines )
		self.update()

	def setLineButtonsState(self):
		'Set the state of the line buttons.'
		coloredLines = self.getColoredLines()
		if len(coloredLines) < 1:
			print('Warning, there are no coloredLines in setLineButtonsState in tableau for the layer:')
			print(self.repository.layer.value)
			return
		isAboveFloor = self.repository.layer.value > 0
		isBelowCeiling = self.repository.layer.value < len( self.skeinPanes ) - 1
		setStateNormalDisabled( isAboveFloor or self.repository.line.value > 0, self.lineDiveButton )
		setStateNormalDisabled( isBelowCeiling or self.repository.line.value < len( coloredLines ) - 1, self.lineSoarButton )
		self.repository.line.value = max(self.repository.line.value, 0)
		self.repository.line.value = min(self.repository.line.value, len(coloredLines) - 1)
		gcodeString = ''
		if self.repository.showGcode.value:
			gcodeString = 'Gcode: ' + coloredLines[self.repository.line.value].displayString
		self.gcodeStringVar.set(gcodeString)
		self.canvas.delete('selection_line')
		self.getDrawnSelectedColoredLine(coloredLines[self.repository.line.value])
		settings.setEntryText(self.lineEntry, self.repository.line.value)

	def setWindowNewMouseTool( self, getNewMouseToolFunction, mouseTool ):
		'Set the getNewMouseTool function and the update function.'
		mouseTool.getNewMouseToolFunction = getNewMouseToolFunction
		mouseTool.setUpdateFunction( self.activateMouseModeTool )

	def setWindowToDisplaySavePhoenixUpdate(self, event=None):
		'Set the setting values to the display, save the new values, then call the update function.'
		self.repository.setToDisplaySave()
		self.phoenixUpdate()

	def setWindowToDisplaySaveUpdate(self, event=None):
		'Set the setting values to the display, save the new values, then call the update function.'
		self.repository.setToDisplaySave()
		self.update()

	def shiftButtonRelease1(self, event):
		'The button was released while the shift key was pressed.'
		self.mouseTool.buttonRelease1( event, True )

	def shiftMotion(self, event):
		'The mouse moved.'
		self.mouseTool.motion( event, True )

	def soar(self):
		'Soar, go up periodically.'
		oldSoarButtonText = self.soarButton['text']
		self.cancelTimerResetButtons()
		if oldSoarButtonText == 'stop':
			return
		self.soarCycle()

	def soarCycle(self):
		'Start the soar cycle.'
		self.setLayerIndex(self.repository.layer.value + 1)
		if self.repository.layer.value > len( self.skeinPanes ) - 2:
			self.resetPeriodicButtonsText()
			return
		self.setButtonImageText( self.soarButton, 'stop')
		self.timerID = self.canvas.after( self.getSlideShowDelay(), self.soarCycle )

	def updateDeiconify( self, center = complex( 0.5, 0.5 ) ):
		'Update and deiconify the window.'
		self.addSettingsMenuSetWindowGeometry( center )
		self.update()
		self.root.deiconify()

	def updateMouseToolIfSelection(self):
		'Update the mouse tool if it is a selection tool.'
		if self.mouseTool == None:
			return
		if self.mouseTool.isSelectionTool():
			self.mouseTool.update()

	def updateNewDestroyOld( self, scrollPaneCenter ):
		'Update and deiconify a window and destroy the old.'
		self.getCopyWithNewSkein().updateDeiconify( scrollPaneCenter )
		self.root.after(1, self.root.destroy) # to get around 'Font Helvetica -12 still in cache.' segmentation bug, instead of simply calling self.root.destroy()
