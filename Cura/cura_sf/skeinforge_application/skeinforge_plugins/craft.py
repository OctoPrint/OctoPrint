"""
This page is in the table of contents.
Craft is a script to access the plugins which craft a gcode file.

The plugin buttons which are commonly used are bolded and the ones which are rarely used have normal font weight.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_utilities import skeinforge_craft
from skeinforge_application.skeinforge_utilities import skeinforge_profile
import os
import sys


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def addSubmenus( menu, pluginFileName, pluginFolderPath, pluginPath ):
	"Add a tool plugin menu."
	submenu = settings.Tkinter.Menu( menu, tearoff = 0 )
	menu.add_cascade( label = pluginFileName.capitalize(), menu = submenu )
	settings.ToolDialog().addPluginToMenu( submenu, pluginPath )
	submenu.add_separator()
	submenuFileNames = archive.getPluginFileNamesFromDirectoryPath( pluginFolderPath )
	for submenuFileName in submenuFileNames:
		settings.ToolDialog().addPluginToMenu( submenu, os.path.join( pluginFolderPath, submenuFileName ) )

def addToCraftMenu( menu ):
	"Add a craft plugin menu."
	settings.ToolDialog().addPluginToMenu(menu, archive.getUntilDot(archive.getSkeinforgePluginsPath('craft.py')))
	menu.add_separator()
	directoryPath = skeinforge_craft.getPluginsDirectoryPath()
	directoryFolders = settings.getFolders(directoryPath)
	pluginFileNames = skeinforge_craft.getPluginFileNames()
	for pluginFileName in pluginFileNames:
		pluginFolderName = pluginFileName + '_plugins'
		pluginPath = os.path.join( directoryPath, pluginFileName )
		if pluginFolderName in directoryFolders:
			addSubmenus( menu, pluginFileName, os.path.join( directoryPath, pluginFolderName ), pluginPath )
		else:
			settings.ToolDialog().addPluginToMenu( menu, pluginPath )

def addToMenu( master, menu, repository, window ):
	"Add a tool plugin menu."
	CraftMenuSaveListener( menu, window )

def getNewRepository():
	'Get new repository.'
	return skeinforge_craft.CraftRepository()

def writeOutput(fileName):
	"Craft a gcode file."
	return skeinforge_craft.writeOutput(fileName)


class CraftMenuSaveListener:
	"A class to update a craft menu."
	def __init__( self, menu, window ):
		"Set the menu."
		self.menu = menu
		addToCraftMenu( menu )
		euclidean.addElementToListDictionaryIfNotThere( self, window, settings.globalProfileSaveListenerListTable )

	def save(self):
		"Profile has been saved and profile menu should be updated."
		settings.deleteMenuItems( self.menu )
		addToCraftMenu( self.menu )


class CraftRadioButtonsSaveListener:
	"A class to update the craft radio buttons."
	def addToDialog( self, gridPosition ):
		"Add this to the dialog."
		euclidean.addElementToListDictionaryIfNotThere( self, self.repository.repositoryDialog, settings.globalProfileSaveListenerListTable )
		self.gridPosition = gridPosition.getCopy()
		self.gridPosition.increment()
		self.gridPosition.row = gridPosition.rowStart
		self.setRadioButtons()

	def getFromRadioPlugins( self, radioPlugins, repository ):
		"Initialize."
		self.name = 'CraftRadioButtonsSaveListener'
		self.radioPlugins = radioPlugins
		self.repository = repository
		repository.displayEntities.append(self)
		return self

	def save(self):
		"Profile has been saved and craft radio plugins should be updated."
		self.setRadioButtons()

	def setRadioButtons(self):
		"Profile has been saved and craft radio plugins should be updated."
		craftSequence = skeinforge_profile.getCraftTypePluginModule().getCraftSequence()
		gridPosition = self.gridPosition.getCopy()
		maximumValue = False
		activeRadioPlugins = []
		for radioPlugin in self.radioPlugins:
			if radioPlugin.name in craftSequence:
				activeRadioPlugins.append( radioPlugin )
				radioPlugin.incrementGridPosition(gridPosition)
				maximumValue = max( radioPlugin.value, maximumValue )
			else:
				radioPlugin.radiobutton.grid_remove()
		if not maximumValue:
			selectedRadioPlugin = settings.getSelectedRadioPlugin( self.repository.importantFileNames + [ activeRadioPlugins[0].name ], activeRadioPlugins ).setSelect()
		self.repository.pluginFrame.update()


def main():
	"Display the craft dialog."
	if len(sys.argv) > 1:
		settings.startMainLoopFromWindow(writeOutput(' '.join(sys.argv[1 :])))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == "__main__":
	main()
