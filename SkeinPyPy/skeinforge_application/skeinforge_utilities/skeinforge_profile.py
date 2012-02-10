"""
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
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import settings
import os
import shutil


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def addListsSetCraftProfile( craftSequence, defaultProfile, repository, fileNameHelp ):
	"Set the craft profile repository."
	settings.addListsToRepository(fileNameHelp, repository)
	repository.craftSequenceLabel = settings.LabelDisplay().getFromName('Craft Sequence: ', repository )
	craftToolStrings = []
	for craftTool in craftSequence[ : - 1 ]:
		craftToolStrings.append( settings.getEachWordCapitalized( craftTool ) + '->')
	craftToolStrings.append( settings.getEachWordCapitalized( craftSequence[-1] ) )
	for craftToolStringIndex in xrange( 0, len( craftToolStrings ), 5 ):
		craftLine = ' '.join( craftToolStrings[ craftToolStringIndex : craftToolStringIndex + 5 ] )
		settings.LabelDisplay().getFromName( craftLine, repository )
	settings.LabelDisplay().getFromName('', repository )
	repository.profileList = ProfileList().getFromName('Profile List:', repository )
	repository.profileListbox = ProfileListboxSetting().getFromListSetting( repository.profileList, 'Profile Selection:', repository, defaultProfile )
	repository.addListboxSelection = AddProfile().getFromProfileListboxSettingRepository( repository.profileListbox, repository )
	repository.deleteListboxSelection = DeleteProfile().getFromProfileListboxSettingRepository( repository.profileListbox, repository )
	directoryName = archive.getProfilesPath()
	archive.makeDirectory(directoryName)
	repository.windowPosition.value = '0+400'

def addListsToCraftTypeRepository(fileNameHelp, repository):
	"Add the value to the lists."
	settings.addListsToRepositoryByFunction(fileNameHelp, getProfileDirectory, repository)
	dotsMinusOne = fileNameHelp.count('.') - 1
	x = 0
	xAddition = 400
	for step in xrange(dotsMinusOne):
		x += xAddition
		xAddition /= 2
	repository.windowPosition.value = '%s+0' % x

def cancelAll():
	"Cancel all the dialogs."
	for globalRepositoryDialogValue in settings.getGlobalRepositoryDialogValues():
		globalRepositoryDialogValue.cancel()

def getCraftTypeName(subName=''):
	"Get the craft type from the profile."
	profileSettings = getReadProfileRepository()
	craftTypeName = settings.getSelectedPluginName( profileSettings.craftRadios )
	if subName == '':
		return craftTypeName
	return os.path.join( craftTypeName, subName )

def getCraftTypePluginModule( craftTypeName = ''):
	"Get the craft type plugin module."
	if craftTypeName == '':
		craftTypeName = getCraftTypeName()
	profilePluginsDirectoryPath = getPluginsDirectoryPath()
	return archive.getModuleWithDirectoryPath( profilePluginsDirectoryPath, craftTypeName )

def getNewRepository():
	'Get new repository.'
	return ProfileRepository()

def getPluginFileNames():
	"Get analyze plugin fileNames."
	return archive.getPluginFileNamesFromDirectoryPath( getPluginsDirectoryPath() )

def getPluginsDirectoryPath():
	"Get the plugins directory path."
	return archive.getSkeinforgePluginsPath('profile_plugins')

def getProfileDirectory():
	"Get the profile directory."
	craftTypeName = getCraftTypeName()
	return os.path.join( craftTypeName, getProfileName(craftTypeName) )

def getProfileName(craftTypeName):
	"Get the profile name from the craft type name."
	craftTypeSettings = getCraftTypePluginModule(craftTypeName).getNewRepository()
	settings.getReadRepository(craftTypeSettings)
	return craftTypeSettings.profileListbox.value

def getReadProfileRepository():
	"Get the read profile repository."
	return settings.getReadRepository( ProfileRepository() )

def updateProfileSaveListeners():
	"Call the save function of all the update profile save listeners."
	for globalProfileSaveListener in euclidean.getListTableElements( settings.globalProfileSaveListenerListTable ):
		globalProfileSaveListener.save()
	cancelAll()


class AddProfile:
	"A class to add a profile."
	def addSelection(self):
		"Add the selection of a listbox setting."
		entryText = self.entry.get()
		if entryText == '':
			print('To add to the profiles, enter the material name.')
			return
		self.profileListboxSetting.listSetting.setValueToFolders()
		if entryText in self.profileListboxSetting.listSetting.value:
			print('There is already a profile by the name of %s, so no profile will be added.' % entryText )
			return
		self.entry.delete( 0, settings.Tkinter.END )
		craftTypeProfileDirectory = archive.getProfilesPath( self.profileListboxSetting.listSetting.craftTypeName )
		destinationDirectory = os.path.join( craftTypeProfileDirectory, entryText )
		shutil.copytree( self.profileListboxSetting.getSelectedFolder(), destinationDirectory )
		self.profileListboxSetting.listSetting.setValueToFolders()
		self.profileListboxSetting.value = entryText
		self.profileListboxSetting.setStateToValue()

	def addSelectionWithEvent(self, event):
		"Add the selection of a listbox setting, given an event."
		self.addSelection()

	def addToDialog( self, gridPosition ):
		"Add this to the dialog."
		gridPosition.increment()
		self.entry = settings.Tkinter.Entry( gridPosition.master )
		self.entry.bind('<Return>', self.addSelectionWithEvent )
		self.entry.grid( row = gridPosition.row, column = 1, columnspan = 3, sticky = settings.Tkinter.W )
		self.addButton = settings.Tkinter.Button( gridPosition.master, activebackground = 'black', activeforeground = 'white', text = 'Add Profile', command = self.addSelection )
		self.addButton.grid( row = gridPosition.row, column = 0 )

	def getFromProfileListboxSettingRepository( self, profileListboxSetting, repository ):
		"Initialize."
		self.profileListboxSetting = profileListboxSetting
		self.repository = repository
		repository.displayEntities.append(self)
		return self


class DeleteProfile( AddProfile ):
	"A class to delete the selection of a listbox profile."
	def addToDialog( self, gridPosition ):
		"Add this to the dialog."
		gridPosition.increment()
		self.deleteButton = settings.Tkinter.Button( gridPosition.master, activebackground = 'black', activeforeground = 'white', text = "Delete Profile", command = self.deleteSelection )
		self.deleteButton.grid( row = gridPosition.row, column = 0 )

	def deleteSelection(self):
		"Delete the selection of a listbox setting."
		DeleteProfileDialog( self.profileListboxSetting, settings.Tkinter.Tk() )


class DeleteProfileDialog:
	"A dialog to delete a profile."
	def __init__(self, profileListboxSetting, root):
		"Display a delete dialog."
		self.profileListboxSetting = profileListboxSetting
		self.root = root
		root.title('Delete Warning')
		rowIndex = 0
		self.label = settings.Tkinter.Label(self.root, text = 'Do you want to delete the profile?')
		self.label.grid(row = rowIndex, column = 0, columnspan = 3, sticky = settings.Tkinter.W)
		rowIndex += 1
		columnIndex = 1
		deleteButton = settings.Tkinter.Button(root, activebackground = 'black', activeforeground = 'red', command = self.delete, fg = 'red', text = 'Delete')
		deleteButton.grid(row = rowIndex, column = columnIndex)
		columnIndex += 1
		noButton = settings.Tkinter.Button(root, activebackground = 'black', activeforeground = 'darkgreen', command = self.no, fg = 'darkgreen', text = 'Do Nothing')
		noButton.grid(row = rowIndex, column = columnIndex)

	def delete(self):
		"Delete the selection of a listbox setting."
		self.profileListboxSetting.setToDisplay()
		self.profileListboxSetting.listSetting.setValueToFolders()
		if self.profileListboxSetting.value not in self.profileListboxSetting.listSetting.value:
			return
		lastSelectionIndex = 0
		currentSelectionTuple = self.profileListboxSetting.listbox.curselection()
		if len(currentSelectionTuple) > 0:
			lastSelectionIndex = int(currentSelectionTuple[0])
		else:
			print('No profile is selected, so no profile will be deleted.')
			return
		craftTypeName = self.profileListboxSetting.listSetting.craftTypeName
		settings.deleteDirectory(archive.getProfilesPath(craftTypeName), self.profileListboxSetting.value)
		settings.deleteDirectory(settings.getProfilesDirectoryInAboveDirectory(craftTypeName), self.profileListboxSetting.value)
		self.profileListboxSetting.listSetting.setValueToFolders()
		if len(self.profileListboxSetting.listSetting.value) < 1:
			defaultSettingsDirectory = archive.getProfilesPath(os.path.join(craftTypeName, self.profileListboxSetting.defaultValue))
			archive.makeDirectory(defaultSettingsDirectory)
			self.profileListboxSetting.listSetting.setValueToFolders()
		lastSelectionIndex = min(lastSelectionIndex, len(self.profileListboxSetting.listSetting.value) - 1)
		self.profileListboxSetting.value = self.profileListboxSetting.listSetting.value[lastSelectionIndex]
		self.profileListboxSetting.setStateToValue()
		self.no()

	def no(self):
		"The dialog was closed."
		self.root.destroy()


class ProfileList:
	"A class to list the profiles."
	def getFromName( self, name, repository ):
		"Initialize."
		self.craftTypeName = repository.lowerName
		self.name = name
		self.repository = repository
		self.setValueToFolders()
		return self

	def setValueToFolders(self):
		"Set the value to the folders in the profiles directories."
		self.value = settings.getFolders( archive.getProfilesPath( self.craftTypeName ) )
		defaultFolders = settings.getFolders( settings.getProfilesDirectoryInAboveDirectory( self.craftTypeName ) )
		for defaultFolder in defaultFolders:
			if defaultFolder not in self.value:
				self.value.append( defaultFolder )
		self.value.sort()


class ProfileListboxSetting( settings.StringSetting ):
	"A class to handle the profile listbox."
	def addToDialog( self, gridPosition ):
		"Add this to the dialog."
#http://www.pythonware.com/library/tkinter/introduction/x5453-patterns.htm
		self.root = gridPosition.master
		gridPosition.increment()
		from fabmetheus_utilities.hidden_scrollbar import HiddenScrollbar
		scrollbar = HiddenScrollbar( gridPosition.master )
		self.listbox = settings.Tkinter.Listbox( gridPosition.master, selectmode = settings.Tkinter.SINGLE, yscrollcommand = scrollbar.set )
		self.listbox.bind('<ButtonRelease-1>', self.buttonReleaseOne )
		gridPosition.master.bind('<FocusIn>', self.focusIn )
		scrollbar.config( command = self.listbox.yview )
		self.listbox.grid( row = gridPosition.row, column = 0, sticky = settings.Tkinter.N + settings.Tkinter.S )
		scrollbar.grid( row = gridPosition.row, column = 1, sticky = settings.Tkinter.N + settings.Tkinter.S )
		self.setStateToValue()
		self.repository.saveListenerTable['updateProfileSaveListeners'] = updateProfileSaveListeners

	def buttonReleaseOne(self, event):
		"Button one released."
		self.setValueToIndex( self.listbox.nearest(event.y) )

	def focusIn(self, event):
		"The root has gained focus."
		settings.getReadRepository(self.repository)
		self.setStateToValue()

	def getFromListSetting( self, listSetting, name, repository, value ):
		"Initialize."
		self.getFromValueOnly( name, repository, value )
		self.listSetting = listSetting
		repository.displayEntities.append(self)
		repository.preferences.append(self)
		return self

	def getSelectedFolder(self):
		"Get the selected folder."
		settingProfileSubfolder = settings.getSubfolderWithBasename( self.value, archive.getProfilesPath( self.listSetting.craftTypeName ) )
		if settingProfileSubfolder != None:
			return settingProfileSubfolder
		toolProfileSubfolder = settings.getSubfolderWithBasename( self.value, settings.getProfilesDirectoryInAboveDirectory( self.listSetting.craftTypeName ) )
		return toolProfileSubfolder

	def setStateToValue(self):
		"Set the listbox items to the list setting."
		self.listbox.delete( 0, settings.Tkinter.END )
		for item in self.listSetting.value:
			self.listbox.insert( settings.Tkinter.END, item )
			if self.value == item:
				self.listbox.select_set( settings.Tkinter.END )

	def setToDisplay(self):
		"Set the selection value to the listbox selection."
		currentSelectionTuple = self.listbox.curselection()
		if len( currentSelectionTuple ) > 0:
			self.setValueToIndex( int( currentSelectionTuple[0] ) )

	def setValueToIndex( self, index ):
		"Set the selection value to the index."
		valueString = self.listbox.get( index )
		self.setValueToString( valueString )

	def setValueToString( self, valueString ):
		"Set the value to the value string."
		self.value = valueString
		if self.getSelectedFolder() == None:
			self.value = self.defaultValue
		if self.getSelectedFolder() == None:
			if len( self.listSetting.value ) > 0:
				self.value = self.listSetting.value[0]


class ProfilePluginRadioButtonsSaveListener:
	"A class to update the profile radio buttons."
	def addToDialog( self, gridPosition ):
		"Add this to the dialog."
		euclidean.addElementToListDictionaryIfNotThere( self, self.repository.repositoryDialog, settings.globalProfileSaveListenerListTable )

	def getFromRadioPlugins( self, radioPlugins, repository ):
		"Initialize."
		self.name = 'ProfilePluginRadioButtonsSaveListener'
		self.radioPlugins = radioPlugins
		self.repository = repository
		repository.displayEntities.append(self)
		return self

	def save(self):
		"Profile has been saved and profile radio plugins should be updated."
		craftTypeName = getCraftTypeName()
		for radioPlugin in self.radioPlugins:
			if radioPlugin.name == craftTypeName:
				if radioPlugin.setSelect():
					self.repository.pluginFrame.update()
				return


class ProfileRepository:
	"A class to handle the profile entities."
	def __init__(self):
		"Set the default entities, execute title & repository fileName."
		settings.addListsToRepository('skeinforge_application.skeinforge_utilities.skeinforge_profile.html', self)
		importantFileNames = ['extrusion']
		self.craftRadios = settings.getRadioPluginsAddPluginFrame( getPluginsDirectoryPath(), importantFileNames, getPluginFileNames(), self )
		ProfilePluginRadioButtonsSaveListener().getFromRadioPlugins( self.craftRadios, self )
		for craftRadio in self.craftRadios:
			craftRadio.updateFunction = self.updateRelay
		directoryName = archive.getProfilesPath()
		archive.makeDirectory(directoryName)
		self.windowPosition.value = '0+200'

	def updateRelay(self):
		"Update the plugin frame then the ProfileSaveListeners."
		self.pluginFrame.update()
		updateProfileSaveListeners()


class ProfileSelectionMenuRadio:
	"A class to display a profile selection menu radio button."
	def addToDialog( self, gridPosition ):
		"Add this to the dialog."
		self.activate = False
		self.menuButtonDisplay.setToNameAddToDialog( self.valueName, gridPosition )
		self.menuButtonDisplay.menu.add_radiobutton( label = self.valueName, command = self.clickRadio, value = self.valueName, variable = self.menuButtonDisplay.radioVar )
		self.menuLength = self.menuButtonDisplay.menu.index( settings.Tkinter.END )
		if self.value:
			self.menuButtonDisplay.radioVar.set( self.valueName )
			self.menuButtonDisplay.menu.invoke( self.menuLength )
		euclidean.addElementToListDictionaryIfNotThere( self.repository, self.repository.repositoryDialog, settings.globalProfileSaveListenerListTable )
		self.activate = True

	def clickRadio(self):
		"Workaround for Tkinter bug, invoke and set the value when clicked."
		if not self.activate:
			return
		settings.saveAll()
		self.menuButtonDisplay.radioVar.set( self.valueName )
		pluginModule = getCraftTypePluginModule()
		profilePluginSettings = settings.getReadRepository( pluginModule.getNewRepository() )
		profilePluginSettings.profileListbox.value = self.name
		settings.writeSettings( profilePluginSettings )
		updateProfileSaveListeners()

	def getFromMenuButtonDisplay( self, menuButtonDisplay, name, repository, value ):
		"Initialize."
		self.setToMenuButtonDisplay( menuButtonDisplay, name, repository, value )
		self.valueName = name.replace('_', ' ')
		return self

	def setToMenuButtonDisplay( self, menuButtonDisplay, name, repository, value ):
		"Initialize."
		self.menuButtonDisplay = menuButtonDisplay
		self.menuButtonDisplay.menuRadios.append(self)
		self.name = name
		self.repository = repository
		self.value = value
		repository.displayEntities.append(self)


class ProfileTypeMenuRadio( ProfileSelectionMenuRadio ):
	"A class to display a profile type menu radio button."
	def clickRadio(self):
		"Workaround for Tkinter bug, invoke and set the value when clicked."
		if not self.activate:
			return
		settings.saveAll()
		self.menuButtonDisplay.radioVar.set( self.valueName )
		profileSettings = getReadProfileRepository()
		plugins = profileSettings.craftRadios
		for plugin in plugins:
			plugin.value = ( plugin.name == self.name )
		settings.writeSettings( profileSettings )
		updateProfileSaveListeners()

	def getFromMenuButtonDisplay( self, menuButtonDisplay, name, repository, value ):
		"Initialize."
		self.setToMenuButtonDisplay( menuButtonDisplay, name, repository, value )
		self.valueName = settings.getEachWordCapitalized( name )
		return self
