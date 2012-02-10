"""
This page is in the table of contents.
Clairvoyance is an analyze plugin to open the gcode file with an outside program.

The clairvoyance manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Clairvoyance

==Operation==
The default 'Activate Clairvoyance' checkbox is off.  When it is on, the functions described below will work when called from the skeinforge toolchain, when it is off, the functions will not be called from the toolchain.  The functions will still be called, whether or not the 'Activate Clairvoyance' checkbox is on, when clairvoyance is run directly.

==Settings==
===Gcode Program===
Default is webbrowser.

If the 'Gcode Program' is set to webbrowser, the gcode file will be sent to the default browser to be opened.  If the 'Gcode Program' is set to a program name, the gcode file will be sent to that program to be opened.  A good gcode viewer is Pleasant3D, at:
http://www.pleasantsoftware.com/developer/pleasant3d/index.shtml

==Examples==
Below are examples of clairvoyance being used.  These examples are run in a terminal in the folder which contains Screw Holder_penultimate.gcode and clairvoyance.py.

> python clairvoyance.py
This brings up the clairvoyance dialog.

> python clairvoyance.py Screw Holder_penultimate.gcode
The file is opened by an outside program

"""


from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities import archive
from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_utilities import skeinforge_polyfile
from skeinforge_application.skeinforge_utilities import skeinforge_profile
import subprocess
import sys
import traceback


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getNewRepository():
	'Get new repository.'
	return ClairvoyanceRepository()

def getWindowAnalyzeFile(fileName, repository=None):
	'Open penultimate file with outside program.'
	print('')
	if repository == None:
		repository = settings.getReadRepository(ClairvoyanceRepository())
	gcodeProgram = repository.gcodeProgram.value
	if gcodeProgram == '':
		print('Warning, nothing will be done in getWindowAnalyzeFile in clairvoyance because the Gcode Program field is empty.')
		print('')
		return
	if gcodeProgram == 'webbrowser':
		print('Clairvoyance will use a web browser to open the file:')
		print(archive.getSummarizedFileName(fileName))
		settings.openWebPage(fileName)
		return
	try:
		subprocess.Popen([gcodeProgram, fileName])
		print('Clairvoyance has opened the file:')
		print(archive.getSummarizedFileName(fileName))
		print('with the gcode program:')
		print(gcodeProgram)
	except:
		print('Warning, getWindowAnalyzeFile in clairvoyance could not open the file:')
		print(fileName)
		print('with the gcode program:')
		print(gcodeProgram)
		print('Error traceback is the following:')
		traceback.print_exc(file=sys.stdout)
		print('')

def writeOutput(fileName, fileNamePenultimate, fileNameSuffix, filePenultimateWritten, gcodeText=''):
	'Open penultimate file with outside program given text.'
	repository = settings.getReadRepository(ClairvoyanceRepository())
	if repository.activateClairvoyance.value:
		if not filePenultimateWritten:
			archive.writeFileText(fileNamePenultimate, gcodeText)
		getWindowAnalyzeFile(fileNamePenultimate, repository)


class ClairvoyanceRepository:
	'A class to handle the clairvoyance settings.'
	def __init__(self):
		'Set the default settings, execute title & settings fileName.'
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.analyze_plugins.clairvoyance.html', self)
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Clairvoyance')
		self.activateClairvoyance = settings.BooleanSetting().getFromValue('Activate Clairvoyance', self, False)
		settings.LabelSeparator().getFromRepository(self)
		self.fileNameInput = settings.FileNameInput().getFromFileName([('Gcode text files', '*.gcode')], 'Open File to Generate Clairvoyances for', self, '')
		self.gcodeProgram = settings.StringSetting().getFromValue('Gcode Program:', self, 'webbrowser')
		self.executeTitle = 'Clairvoyance'

	def execute(self):
		'Write button has been clicked.'
		fileNames = skeinforge_polyfile.getFileOrGcodeDirectory( self.fileNameInput.value, self.fileNameInput.wasCancelled, ['_comment'] )
		for fileName in fileNames:
			getWindowAnalyzeFile(fileName)


def main():
	'Display the clairvoyance dialog.'
	if len(sys.argv) > 1:
		getWindowAnalyzeFile(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == '__main__':
	main()
