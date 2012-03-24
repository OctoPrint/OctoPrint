"""
Profile is a script to set the craft types setting for the skeinforge chain.

Profile presents the user with a choice of the craft types in the profile_plugins folder.  The chosen craft type is used to determine the craft type profile for the skeinforge chain.  The default craft type is extrusion.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities import archive

def getCraftTypeName():
	return 'extrusion'

def getProfileName(craftTypeName):
	return 'Cura profile:' + craftTypeName

def addListsToCraftTypeRepository(fileNameHelp, repository):
    #print('addListsToCraftTypeRepository:', fileNameHelp, repository)
    repository.name = fileNameHelp.split('.')[-2]
    repository.preferences = []

def getCraftTypePluginModule( craftTypeName = ''):
    "Get the craft type plugin module"
    if craftTypeName == '':
        craftTypeName = getCraftTypeName()
    profilePluginsDirectoryPath = getPluginsDirectoryPath()
    return archive.getModuleWithDirectoryPath( profilePluginsDirectoryPath, craftTypeName )

def getPluginsDirectoryPath():
    "Get the plugins directory path."
    return archive.getSkeinforgePluginsPath('profile_plugins')

