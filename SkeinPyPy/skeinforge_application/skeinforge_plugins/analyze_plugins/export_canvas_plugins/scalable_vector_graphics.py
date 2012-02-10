"""
This page is in the table of contents.
Scalable vector graphics is an export canvas plugin to export the canvas to a scalable vector graphics (.svg) file.

When the export menu item in the file menu in an analyze viewer tool, like skeinlayer or skeiniso is clicked, the postscript dialog will be displayed.  When the 'Export to Scalable Vector Graphics' button on that dialog is clicked, the canvas will be exported as a scalable vector graphics file.  If the 'Scalable Vector Graphics Program' is set to the default 'webbrowser', the scalable vector graphics file will be sent to the default browser to be opened.  If the 'Scalable Vector Graphics Program' is set to a program name, the scalable vector graphics file will be sent to that program to be opened.

If furthermore the 'File Extension' is set to a file extension, the scalable vector graphics file will be sent to the program, along with the file extension for the converted output.  The default is blank because some systems do not have an image conversion program; if you have or will install an image conversion program, a common 'File Extension' is png.  A good open source conversion program is Image Magick, which is available at:
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
	return ScalableVectorGraphicsRepository()

def parseLineReplace( firstWordTable, line, output ):
	"Parse the line and replace it if the first word of the line is in the first word table."
	firstWord = gcodec.getFirstWordFromLine(line)
	if firstWord in firstWordTable:
		line = firstWordTable[ firstWord ]
	gcodec.addLineAndNewlineIfNecessary( line, output )


class ScalableVectorGraphicsRepository:
	"A class to handle the export settings."
	def __init__(self):
		"Set the default settings, execute title & settings fileName."
		skeinforge_profile.addListsToCraftTypeRepository(
			'skeinforge_application.skeinforge_plugins.analyze_plugins.export_canvas_plugins.scalable_vector_graphics.html', self)
		self.fileExtension = settings.StringSetting().getFromValue('File Extension:', self, '')
		self.svgViewer = settings.StringSetting().getFromValue('SVG Viewer:', self, 'webbrowser')

	def addCanvasLineToOutput( self, canvasLinesOutput, objectIDNumber ):
		"Add the canvas line to the output."
		coordinates = self.canvas.coords( objectIDNumber )
		xBegin = coordinates[0] - self.boxW
		xEnd = coordinates[2] - self.boxW
		yBegin = coordinates[1] - self.boxN
		yEnd = coordinates[3] - self.boxN
		west = self.boxW
		color = self.canvas.itemcget( objectIDNumber, 'fill')
		width = self.canvas.itemcget( objectIDNumber, 'width')
		line = '<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%spx"/>\n' % ( xBegin, yBegin, xEnd, yEnd, color, width )
		canvasLinesOutput.write(line + '\n')

	def execute(self):
		"Export the canvas as an svg file."
		svgFileName = archive.getFilePathWithUnderscoredBasename( self.fileName, self.suffix )
		boundingBox = self.canvas.bbox( settings.Tkinter.ALL ) # tuple (w, n, e, s)
		self.boxW = boundingBox[0]
		self.boxN = boundingBox[1]
		boxWidth = boundingBox[2] - self.boxW
		boxHeight = boundingBox[3] - self.boxN
		print('Exported svg file saved as ' + svgFileName )
		svgTemplateText = archive.getFileText(archive.getTemplatesPath('canvas_template.svg'))
		output = cStringIO.StringIO()
		lines = archive.getTextLines( svgTemplateText )
		firstWordTable = {}
		firstWordTable['height="999px"'] = '		height="%spx"' % int( round( boxHeight ) )
		firstWordTable['<!--replaceLineWith_coloredLines-->'] = self.getCanvasLinesOutput()
		firstWordTable['replaceLineWithTitle'] = archive.getSummarizedFileName( self.fileName )
		firstWordTable['width="999px"'] = '		width="%spx"' % int( round( boxWidth ) )
		for line in lines:
			parseLineReplace( firstWordTable, line, output )
		archive.writeFileText( svgFileName, output.getvalue() )
		fileExtension = self.fileExtension.value
		svgViewer = self.svgViewer.value
		if svgViewer == '':
			return
		if svgViewer == 'webbrowser':
			settings.openWebPage( svgFileName )
			return
		svgFilePath = '"' + os.path.normpath( svgFileName ) + '"' # " to send in file name with spaces
		shellCommand = svgViewer
		print('')
		if fileExtension == '':
			shellCommand += ' ' + svgFilePath
			print('Sending the shell command:')
			print(shellCommand)
			commandResult = os.system(shellCommand)
			if commandResult != 0:
				print('It may be that the system could not find the %s program.' % svgViewer )
				print('If so, try installing the %s program or look for another svg viewer, like Netscape which can be found at:' % svgViewer )
				print('http://www.netscape.org/')
			return
		shellCommand += ' ' + archive.getFilePathWithUnderscoredBasename( svgFilePath, '.' + fileExtension + '"')
		print('Sending the shell command:')
		print(shellCommand)
		commandResult = os.system(shellCommand)
		if commandResult != 0:
			print('The %s program could not convert the svg to the %s file format.' % ( svgViewer, fileExtension ) )
			print('Try installing the %s program or look for another one, like Image Magick which can be found at:' % svgViewer )
			print('http://www.imagemagick.org/script/index.php')

	def getCanvasLinesOutput(self):
		"Add the canvas line to the output."
		canvasLinesOutput = cStringIO.StringIO()
		objectIDNumbers = self.canvas.find_all()
		for objectIDNumber in objectIDNumbers:
			if self.canvas.type( objectIDNumber ) == 'line':
				self.addCanvasLineToOutput( canvasLinesOutput, objectIDNumber )
		return canvasLinesOutput.getvalue()

	def setCanvasFileNameSuffix( self, canvas, fileName, suffix ):
		"Set the canvas and initialize the execute title."
		self.canvas = canvas
		self.executeTitle = 'Convert to Scalable Vector Graphics'
		self.fileName = fileName
		self.suffix = suffix + '.svg'


def main():
	"Display the file or directory dialog."
	settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == "__main__":
	main()
