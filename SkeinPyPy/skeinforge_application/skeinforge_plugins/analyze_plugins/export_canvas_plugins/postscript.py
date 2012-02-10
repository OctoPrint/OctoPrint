"""
This page is in the table of contents.
Postscript is an export canvas plugin to export the canvas to a postscript file.

When the export menu item in the file menu in an analyze viewer tool, like skeinlayer or skeiniso is clicked, the postscript dialog will be displayed.  When the 'Export to Postscript' button on that dialog is clicked, the canvas will be exported as a postscript file.  If the 'Postscript Program' is set to a program name, the postscript file will be sent to that program to be opened.  The default is gimp, the Gnu Image Manipulation Program (Gimp), which is open source, can open postscript and save in a variety of formats.  It is available at:
http://www.gimp.org/

If furthermore the 'File Extension' is set to a file extension, the postscript file will be sent to the program, along with the file extension for the converted output.  The default is blank because some systems do not have an image conversion program; if you have or will install an image conversion program, a common 'File Extension' is png.  A good open source conversion program is Image Magick, which is available at:
http://www.imagemagick.org/script/index.php

An export canvas plugin is a script in the export_canvas_plugins folder which has the function getNewRepository, and which has a repository class with the functions setCanvasFileNameSuffix to set variables and execute to save the file.  It is meant to be run from an analyze viewer tool, like skeinlayer or skeiniso.  To ensure that the plugin works on platforms which do not handle file capitalization properly, give the plugin a lower case name.

"""


from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities import archive
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_utilities import skeinforge_profile
import cStringIO
import os
import sys


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getNewRepository():
	'Get new repository.'
	return PostscriptRepository()


class PostscriptRepository:
	"A class to handle the export settings."
	def __init__(self):
		"Set the default settings, execute title & settings fileName."
		skeinforge_profile.addListsToCraftTypeRepository(
			'skeinforge_application.skeinforge_plugins.analyze_plugins.export_canvas_plugins.postscript.html', self)
		self.fileExtension = settings.StringSetting().getFromValue('File Extension:', self, '')
		self.postscriptProgram = settings.StringSetting().getFromValue('Postscript Program:', self, 'gimp')

	def execute(self):
		"Convert to postscript button has been clicked. Export the canvas as a postscript file."
		postscriptFileName = archive.getFilePathWithUnderscoredBasename( self.fileName, self.suffix )
		boundingBox = self.canvas.bbox( settings.Tkinter.ALL ) # tuple (w, n, e, s)
		boxW = boundingBox[0]
		boxN = boundingBox[1]
		boxWidth = boundingBox[2] - boxW
		boxHeight = boundingBox[3] - boxN
		print('Exported postscript file saved as ' + postscriptFileName )
		self.canvas.postscript( file = postscriptFileName, height = boxHeight, width = boxWidth, pageheight = boxHeight, pagewidth = boxWidth, x = boxW, y = boxN )
		fileExtension = self.fileExtension.value
		postscriptProgram = self.postscriptProgram.value
		if postscriptProgram == '':
			return
		postscriptFilePath = '"' + os.path.normpath( postscriptFileName ) + '"' # " to send in file name with spaces
		shellCommand = postscriptProgram
		print('')
		if fileExtension == '':
			shellCommand += ' ' + postscriptFilePath
			print('Sending the shell command:')
			print(shellCommand)
			commandResult = os.system(shellCommand)
			if commandResult != 0:
				print('It may be that the system could not find the %s program.' % postscriptProgram )
				print('If so, try installing the %s program or look for another one, like the Gnu Image Manipulation Program (Gimp) which can be found at:' % postscriptProgram )
				print('http://www.gimp.org/')
			return
		shellCommand += ' ' + archive.getFilePathWithUnderscoredBasename( postscriptFilePath, '.' + fileExtension + '"')
		print('Sending the shell command:')
		print(shellCommand)
		commandResult = os.system(shellCommand)
		if commandResult != 0:
			print('The %s program could not convert the postscript to the %s file format.' % ( postscriptProgram, fileExtension ) )
			print('Try installing the %s program or look for another one, like Image Magick which can be found at:' % postscriptProgram )
			print('http://www.imagemagick.org/script/index.php')

	def setCanvasFileNameSuffix( self, canvas, fileName, suffix ):
		"Set the canvas and initialize the execute title."
		self.canvas = canvas
		self.executeTitle = 'Export to Postscript'
		self.fileName = fileName
		self.suffix = suffix + '.ps'


def main():
	"Display the file or directory dialog."
	settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == "__main__":
	main()
