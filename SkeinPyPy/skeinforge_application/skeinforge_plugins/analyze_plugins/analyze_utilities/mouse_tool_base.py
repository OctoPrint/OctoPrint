"""
Display line is a mouse tool to display the line index of the line clicked, counting from one, and the line itself.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


class MouseToolBase:
	"The mouse tool base class, which does nothing."
	def button1(self, event):
		"The left button was clicked, <Button-1> function."
		pass

	def buttonRelease1(self, event):
		"The left button was released, <ButtonRelease-1> function."
		pass

	def destroyEverything(self):
		"Destroy items."
		self.canvas.delete('mouse_item')

	def destroyEverythingGetFocus(self):
		"Destroy items and get the focus for the canvas."
		self.destroyEverything()
		self.canvas.focus_set()

	def getReset( self, window ):
		"Reset the mouse tool to default."
		self.setWindowItems( window )
		self.destroyEverything()
		return self

	def getTagsGivenXY( self, x, y ):
		"Get the tag for the x and y."
		tags = self.canvas.itemcget( self.canvas.find_closest(x, y), 'tags')
		currentEnd = ' current'
		if tags.find( currentEnd ) != - 1:
			return tags[ : - len( currentEnd ) ]
		return tags

	def isSelectionTool(self):
		"Return if this mouse tool is a selection tool."
		return False

	def keyPressDown(self, event):
		"The down arrow was pressed."
		pass

	def keyPressLeft(self, event):
		"The left arrow was pressed."
		pass

	def keyPressReturn(self, event):
		"The return key was pressed."
		pass

	def keyPressRight(self, event):
		"The right arrow was pressed."
		pass

	def keyPressUp(self, event):
		"The up arrow was pressed."
		pass

	def motion( self, event, shift = False ):
		"The mouse moved, <Motion> function."
		pass

	def setWindowItems( self, window ):
		"Set the canvas and items."
		self.canvas = window.canvas
		self.repository = window.repository
		self.window = window

	def update(self):
		"Update the mouse tool."
		pass
