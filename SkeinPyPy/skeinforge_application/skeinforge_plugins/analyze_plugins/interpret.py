"""
This page is in the table of contents.
Interpret is an analyze plugin to interpret a file, turning a 2D file into svg and a 3D file into constructive solid geometry xml.

The comment manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Interpret

==Operation==
The default 'Activate Interpret' checkbox is off.  When it is on, the functions described below will work when called from the skeinforge toolchain, when it is off, the functions will not be called from the tool chain.  The functions will still be called, whether or not the 'Activate Interpret' checkbox is on, when interpret is run directly.

==Settings==
===Print Interpretion===
Default is off.

When selected, the xml text will be printed to the console.

===Text Program===
Default is webbrowser.

If the 'Text Program' is set the default 'webbrowser', the XML file will be sent to the default browser to be opened.  If the 'Text Program' is set to a program name, the XML file will be sent to that program to be opened.

==Examples==
Below are examples of interpret being used.  These examples are run in a terminal in the folder which contains Screw_Holder.stl and interpret.py.

> python interpret.py
This brings up the interpret dialog.

> python interpret.py Screw_Holder.stl
The comment file is saved as Screw_Holder_interpret.xml

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities import settings
from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
import sys


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getNewRepository():
	'Get new repository.'
	return fabmetheus_interpret.InterpretRepository()

def writeOutput(fileName, fileNamePenultimate, fileNameSuffix, filePenultimateWritten, gcodeText=''):
	"Write file interpretation, if activate interpret is selected."
	repository = settings.getReadRepository(getNewRepository())
	if repository.activateInterpret.value:
		fabmetheus_interpret.getWindowAnalyzeFile(fileName)


def main():
	"Display the interpret dialog."
	if len(sys.argv) > 1:
		fabmetheus_interpret.getWindowAnalyzeFile(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == "__main__":
	main()
