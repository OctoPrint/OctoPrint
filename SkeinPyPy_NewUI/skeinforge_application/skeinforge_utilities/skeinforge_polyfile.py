"""
Polyfile is a script to choose whether the skeinforge toolchain will operate on one file or all the files in a directory.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities import archive
from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_utilities import skeinforge_profile


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getFileOrDirectoryTypes( fileName, fileTypes, wasCancelled ):
	"Get the gcode files in the directory the file is in if directory setting is true.  Otherwise, return the file in a list."
	if isEmptyOrCancelled( fileName, wasCancelled ):
		return []
	if isDirectorySetting():
		return archive.getFilesWithFileTypesWithoutWords( fileTypes, [], fileName )
	return [ fileName ]

def getFileOrDirectoryTypesUnmodifiedGcode(fileName, fileTypes, wasCancelled):
	"Get the gcode files in the directory the file is in if directory setting is true.  Otherwise, return the file in a list."
	if isEmptyOrCancelled(fileName, wasCancelled):
		return []
	if isDirectorySetting():
		return archive.getFilesWithFileTypesWithoutWords(fileTypes, [], fileName)
	return [fileName]

def getFileOrGcodeDirectory( fileName, wasCancelled, words = [] ):
	"Get the gcode files in the directory the file is in if directory setting is true.  Otherwise, return the file in a list."
	if isEmptyOrCancelled( fileName, wasCancelled ):
		return []
	if isDirectorySetting():
		dotIndex = fileName.rfind('.')
		if dotIndex < 0:
			print('The file name should have a suffix, like myfile.xml.')
			print('Since the file name does not have a suffix, nothing will be done')
		suffix = fileName[ dotIndex + 1 : ]
		return archive.getFilesWithFileTypeWithoutWords( suffix, words, fileName )
	return [ fileName ]

def getNewRepository():
	'Get new repository.'
	return PolyfileRepository()

def isDirectorySetting():
	"Determine if the directory setting is true."
	return settings.getReadRepository( PolyfileRepository() ).directorySetting.value

def isEmptyOrCancelled( fileName, wasCancelled ):
	"Determine if the fileName is empty or the dialog was cancelled."
	return str(fileName) == '' or str(fileName) == '()' or wasCancelled


class PolyfileRepository:
	"A class to handle the polyfile settings."
	def __init__(self):
		"Set the default settings, execute title & settings fileName."
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_utilities.skeinforge_polyfile.html', self)
		self.directoryOrFileChoiceLabel = settings.LabelDisplay().getFromName('Directory or File Choice: ', self )
		directoryLatentStringVar = settings.LatentStringVar()
		self.directorySetting = settings.Radio().getFromRadio( directoryLatentStringVar, 'Execute All Unmodified Files in a Directory', self, False )
		self.fileSetting = settings.Radio().getFromRadio( directoryLatentStringVar, 'Execute File', self, True )
