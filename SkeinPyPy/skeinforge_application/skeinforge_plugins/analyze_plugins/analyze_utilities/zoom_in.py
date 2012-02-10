"""
This page is in the table of contents.
Zoom in is a mouse tool to zoom in the display at the point where the mouse was clicked, increasing the scale by a factor of two.

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
	return ZoomIn()


class ZoomIn( MouseToolBase ):
	"The zoom in mouse tool."
	def button1( self, event, shift = False ):
		"Print line text and connection line."
		scaleSetting = self.window.repository.scale
		scaleSetting.value *= self.getMultiplier()
		delta = complex( float(event.x) / float( self.window.screenSize.real ), float(event.y) / float( self.window.screenSize.imag ) ) - self.window.canvasScreenCenter
		delta *= 1.0 - 1.0 / self.getMultiplier()
		scrollPaneCenter = self.window.getScrollPaneCenter() + delta
		self.window.updateNewDestroyOld( scrollPaneCenter )

	def click(self, event=None):
		"Set the window mouse tool to this."
		self.window.destroyMouseToolRaiseMouseButtons()
		self.window.mouseTool = self
		self.mouseButton['relief'] = settings.Tkinter.SUNKEN

	def getMultiplier(self):
		"Get the scale multiplier."
		return 2.0

	def getReset( self, window ):
		"Reset the mouse tool to default."
		self.setWindowItems( window )
		self.mouseButton = None
		return self
