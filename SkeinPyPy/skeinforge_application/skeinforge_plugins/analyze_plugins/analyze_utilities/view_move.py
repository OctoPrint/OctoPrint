"""
This page is in the table of contents.
Viewpoint move is a mouse tool to move the viewpoint in the xy plane.

When the mouse is clicked and dragged on the canvas, viewpoint move will drag the scroll pane accordingly.  If the shift key is also pressed, the scroll pane will be moved only in the x or y direction, whichever is largest.

When the viewpoint move tool is chosen and the canvas has the focus, viewpoint move will listen to the arrow keys.  Clicking in the canvas gives the canvas the focus, and when the canvas has the focus a thick black border is drawn around the canvas.  When the right arrow key is pressed, viewpoint move will move the scroll pane to the right by a pixel.  When the left arrow key is pressed, the scroll pane will be moved a pixel to the left.  The up arrow key moves the scroll pane a pixel up and the down arow key moves the scroll pane a pixel down.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from skeinforge_application.skeinforge_plugins.analyze_plugins.analyze_utilities.mouse_tool_base import MouseToolBase
from fabmetheus_utilities import settings

__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getNewMouseTool():
	"Get a new mouse tool."
	return ViewpointMove()


class ViewpointMove( MouseToolBase ):
	"Display the line when it is clicked."
	def button1( self, event, shift = False ):
		"Print line text and connection line."
		self.destroyEverythingGetFocus()
		self.buttonOnePressedScreenCoordinate = complex( event.x, event.y )
		self.scrollPaneFraction = self.window.getScrollPaneFraction()

	def buttonRelease1( self, event, shift = False ):
		"The left button was released, <ButtonRelease-1> function."
		self.destroyEverything()

	def destroyEverything(self):
		"Destroy items."
		self.buttonOnePressedScreenCoordinate = None

	def keyPressDown(self, event):
		"The down arrow was pressed."
		self.setScrollPaneMove( complex( 0.0, 1.0 ) )

	def keyPressLeft(self, event):
		"The left arrow was pressed."
		self.setScrollPaneMove( complex( - 1.0, 0.0 ) )

	def keyPressRight(self, event):
		"The right arrow was pressed."
		self.setScrollPaneMove( complex( 1.0, 0.0 ) )

	def keyPressUp(self, event):
		"The up arrow was pressed."
		self.setScrollPaneMove( complex(0.0, -1.0) )

	def motion( self, event, shift = False ):
		"The mouse moved, <Motion> function."
		if self.buttonOnePressedScreenCoordinate == None:
			return
		motionCoordinate = complex( event.x, event.y )
		relativeMotion = motionCoordinate - self.buttonOnePressedScreenCoordinate
		if shift:
			if abs( relativeMotion.real ) > abs( relativeMotion.imag ):
				relativeMotion = complex( relativeMotion.real, 0.0 )
			else:
				relativeMotion = complex( 0.0, relativeMotion.imag )
		self.relativeMove( relativeMotion )

	def relativeMove( self, relativeMotion ):
		"Move the view given the relative motion."
		relativeScreenMotion = complex( relativeMotion.real / float( self.window.screenSize.real ), relativeMotion.imag / float( self.window.screenSize.imag ) )
		moveTo = self.scrollPaneFraction - relativeScreenMotion
		self.window.relayXview( settings.Tkinter.MOVETO, moveTo.real )
		self.window.relayYview( settings.Tkinter.MOVETO, moveTo.imag )

	def setScrollPaneMove( self, relativeMotion ):
		"The up arrow was pressed."
		self.scrollPaneFraction = self.window.getScrollPaneFraction()
		self.relativeMove( relativeMotion )
