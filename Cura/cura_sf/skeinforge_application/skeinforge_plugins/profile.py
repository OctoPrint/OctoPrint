"""
This page is in the table of contents.
Profile is a script to set the craft types setting for the skeinforge chain.

Profile presents the user with a choice of the craft types in the profile_plugins folder.  The chosen craft type is used to determine the craft type profile for the skeinforge chain.  The default craft type is extrusion.

The setting is the selection.  If you hit 'Save and Close' the selection will be saved, if you hit 'Cancel' the selection will not be saved.

To change the profile setting, in a shell in the profile folder type:
> python profile.py

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_utilities import skeinforge_profile
import os


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def addSubmenus( craftTypeName, menu, pluginFileName, pluginPath, profileRadioVar ):
	"Add a tool plugin menu."
	submenu = settings.Tkinter.Menu( menu, tearoff = 0 )
	menu.add_cascade( label = pluginFileName.capitalize(), menu = submenu )
	settings.ToolDialog().addPluginToMenu( submenu, pluginPath )
	submenu.add_separator()
	pluginModule = skeinforge_profile.getCraftTypePluginModule( pluginFileName )
	profilePluginSettings = settings.getReadRepository( pluginModule.getNewRepository() )
	isSelected = ( craftTypeName == pluginFileName )
	for profileName in profilePluginSettings.profileList.value:
		value = isSelected and profileName == profilePluginSettings.profileListbox.value
		ProfileMenuRadio( pluginFileName, submenu, profileName, profileRadioVar, value )

def addToMenu( master, menu, repository, window ):
	"Add a tool plugin menu."
	ProfileMenuSaveListener( menu, window )

def addToProfileMenu( menu ):
	"Add a profile menu."
	settings.ToolDialog().addPluginToMenu(menu, archive.getUntilDot(archive.getSkeinforgePluginsPath('profile.py')))
	menu.add_separator()
	directoryPath = skeinforge_profile.getPluginsDirectoryPath()
	pluginFileNames = skeinforge_profile.getPluginFileNames()
	craftTypeName = skeinforge_profile.getCraftTypeName()
	profileRadioVar = settings.Tkinter.StringVar()
	for pluginFileName in pluginFileNames:
		addSubmenus( craftTypeName, menu, pluginFileName, os.path.join( directoryPath, pluginFileName ), profileRadioVar )

def getNewRepository():
	'Get new repository.'
	return skeinforge_profile.ProfileRepository()


class ProfileMenuRadio:
	"A class to display a profile menu radio button."
	def __init__( self, profilePluginFileName, menu, name, radioVar, value ):
		"Create a profile menu radio."
		self.activate = False
		self.menu = menu
		self.name = name
		self.profileJoinName = profilePluginFileName + '.& /' + name
		self.profilePluginFileName = profilePluginFileName
		self.radioVar = radioVar
		menu.add_radiobutton( label = name.replace('_', ' '), command = self.clickRadio, value = self.profileJoinName, variable = self.radioVar )
		self.menuLength = menu.index( settings.Tkinter.END )
		if value:
			self.radioVar.set( self.profileJoinName )
			self.menu.invoke( self.menuLength )
		self.activate = True

	def clickRadio(self):
		"Workaround for Tkinter bug, invoke and set the value when clicked."
		if not self.activate:
			return
		self.radioVar.set( self.profileJoinName )
		pluginModule = skeinforge_profile.getCraftTypePluginModule( self.profilePluginFileName )
		profilePluginSettings = settings.getReadRepository( pluginModule.getNewRepository() )
		profilePluginSettings.profileListbox.value = self.name
		settings.writeSettings( profilePluginSettings )
		profileSettings = skeinforge_profile.getReadProfileRepository()
		plugins = profileSettings.craftRadios
		for plugin in plugins:
			plugin.value = ( plugin.name == self.profilePluginFileName )
		settings.writeSettings( profileSettings )
		skeinforge_profile.updateProfileSaveListeners()


class ProfileMenuSaveListener:
	"A class to update a profile menu."
	def __init__( self, menu, window ):
		"Set the menu."
		self.menu = menu
		addToProfileMenu( menu )
		euclidean.addElementToListDictionaryIfNotThere( self, window, settings.globalProfileSaveListenerListTable )

	def save(self):
		"Profile has been saved and profile menu should be updated."
		settings.deleteMenuItems( self.menu )
		addToProfileMenu( self.menu )


def main():
	"Display the profile dialog."
	settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == "__main__":
	main()
