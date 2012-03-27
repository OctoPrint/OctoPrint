"""
This page is in the table of contents.
Analyze is a script to access the plugins which analyze a gcode file.

The plugin buttons which are commonly used are bolded and the ones which are rarely used have normal font weight.

==Gcodes==
An explanation of the gcodes is at:
http://reprap.org/bin/view/Main/Arduino_GCode_Interpreter

and at:
http://reprap.org/bin/view/Main/MCodeReference

A gode example is at:
http://forums.reprap.org/file.php?12,file=565

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities import archive
from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_utilities import skeinforge_analyze
import sys


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def addToMenu(master, menu, repository, window):
	"Add a tool plugin menu."
	analyzeFilePath = archive.getSkeinforgePluginsPath('analyze.py')
	pluginsDirectoryPath = skeinforge_analyze.getPluginsDirectoryPath()
	settings.addPluginsParentToMenu(pluginsDirectoryPath, menu, analyzeFilePath, skeinforge_analyze.getPluginFileNames())

def getNewRepository():
	'Get new repository.'
	return skeinforge_analyze.AnalyzeRepository()

def writeOutput(fileName):
	"Analyze a gcode file."
	repository = getNewRepository()
	repository.fileNameInput.value = fileName
	repository.execute()
	settings.startMainLoopFromConstructor(repository)


def main():
	"Display the analyze dialog."
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == "__main__":
	main()
