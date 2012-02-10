"""
This page is in the table of contents.
Display line is a mouse tool to select and display information about the line.

When a line is clicked, the line will be selected and information about the line will be displayed.  If a gcode line is clicked, the information will be file line count of the line clicked, counting from one, and the line itself.

When the display line tool is chosen and the canvas has the focus, display line will listen to the arrow keys.  Clicking in the canvas gives the canvas the focus, and when the canvas has the focus a thick black border is drawn around the canvas.  When the right arrow key is pressed, display line will increase the line index of the layer by one, and change the selection accordingly.  If the line index of the layer goes over the index of the last line, the layer index will be increased by one and the new line index will be zero.  When the left arrow key is pressed, the index will be decreased.  If the line index goes below the index of the first line, the layer index will be decreased by one and the new line index will be at the last line.  The up arrow key increases the layer index by one and the down arow key decreases the line index.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from skeinforge_application.skeinforge_plugins.analyze_plugins.analyze_utilities.mouse_tool_base import MouseToolBase
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import settings

__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getNewMouseTool():
	"Get a new mouse tool."
	return DisplayLine()


class DisplayLine( MouseToolBase ):
	"Display the line when it is clicked."
	def button1( self, event, shift = False ):
		"Print line text and connection line."
		self.destroyEverythingGetFocus()
		x = self.canvas.canvasx(event.x)
		y = self.canvas.canvasy(event.y)
		tags = self.getTagsGivenXY(x, y)
		if tags == '':
			return
		if tags.startswith('colored_line_index:'):
			splitLine = tags.split()
			coloredLineIndex = int(splitLine[1])
			self.repository.line.value = coloredLineIndex
			tags = self.getSelectedColoredLine().displayString
		self.drawLineText( complex( float(x), float(y) ), tags )

	def destroyEverything(self):
		"Destroy items."
		self.canvas.delete('mouse_item')
		self.canvas.delete('selection_line')

	def drawLineText( self, location, tags ):
		"Draw the line text."
		self.window.getDrawnLineText( location, 'mouse_item', tags )

	def drawSelectedColoredLineText(self):
		"Draw the selected line and text."
		selectedColoredLine = self.getSelectedColoredLine()
		if len( self.canvas.find_withtag('selection_line') ) < 1 or selectedColoredLine == None:
			return
		tags = selectedColoredLine.displayString
		lineCoordinates = self.canvas.coords( self.canvas.find_withtag('selection_line')[-1] )
		begin = complex( lineCoordinates[0], lineCoordinates[1] )
		end = complex( lineCoordinates[2], lineCoordinates[3] )
		segment = end - begin
		segmentLength = abs(segment)
		if segmentLength <= 0.0:
			return
		towardEnd = 0.75 * segment
		segmentClockwise = 20.0 * complex( segment.imag, - segment.real ) / segmentLength
		location = begin + towardEnd + segmentClockwise
		self.drawLineText( location, tags )

	def getSelectedColoredLine(self):
		"Draw the selected line, add it to the items and return the colored line."
		self.window.cancelTimerResetButtons()
		coloredLines = self.window.getColoredLines()
		self.repository.line.value = max(0, self.repository.line.value)
		if len(coloredLines) < 1:
			return None
		self.repository.line.value = min(len(coloredLines) - 1, self.repository.line.value)
		self.window.setLineButtonsState()
		coloredLine = coloredLines[self.repository.line.value]
		lineCoordinates = self.canvas.coords(self.window.getDrawnSelectedColoredLine(coloredLine))
		end = complex(lineCoordinates[2], lineCoordinates[3])
		radiusComplex = complex(16.0, 16.0)
		upperLeft = end - radiusComplex
		lowerRight = end + radiusComplex
		self.canvas.create_oval (int(upperLeft.real), int(upperLeft.imag), int(lowerRight.real), int(lowerRight.imag), tags = 'mouse_item')
		return coloredLine

	def isSelectionTool(self):
		"Return if this mouse tool is a selection tool."
		return True

	def keyPressDown(self, event):
		"The down arrow was pressed."
		self.destroyEverything()
		self.window.setLayerIndex( self.repository.layer.value - 1 )

	def keyPressLeft(self, event):
		"The left arrow was pressed."
		self.destroyEverything()
		self.repository.line.value -= 1
		if self.window.isLineBelowZeroSetLayer():
			return
		self.drawSelectedColoredLineText()

	def keyPressRight(self, event):
		"The right arrow was pressed."
		self.destroyEverything()
		self.repository.line.value += 1
		if self.window.isLineBeyondListSetLayer():
			return
		self.drawSelectedColoredLineText()

	def keyPressUp(self, event):
		"The up arrow was pressed."
		self.destroyEverything()
		self.window.setLayerIndex( self.repository.layer.value + 1 )

	def update(self):
		"Update the mouse tool."
		self.destroyEverything()
		self.drawSelectedColoredLineText()
