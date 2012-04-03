"""
This page is in the table of contents.
The flow script sets the flow rate by writing the M108 gcode.

==Operation==
The default 'Activate Flow' checkbox is on.  When it is on, the functions described below will work, when it is off, the functions will not be called.

==Settings==
===Flow Rate===
Default is 210.

Defines the flow rate which will be written following the M108 command.  The flow rate is usually a PWM setting, but could be anything, like the rpm of the tool or the duty cycle of the tool.

==Examples==
The following examples flow the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and flow.py.

> python flow.py
This brings up the flow dialog.

> python flow.py Screw Holder Bottom.stl
The flow tool is parsing the file:
Screw Holder Bottom.stl
..
The flow tool has created the file:
.. Screw Holder Bottom_flow.gcode

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_utilities import skeinforge_craft
from skeinforge_application.skeinforge_utilities import skeinforge_polyfile
from skeinforge_application.skeinforge_utilities import skeinforge_profile
import sys


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCraftedText( fileName, text='', flowRepository = None ):
	"Flow the file or text."
	return getCraftedTextFromText( archive.getTextIfEmpty(fileName, text), flowRepository )

def getCraftedTextFromText( gcodeText, flowRepository = None ):
	"Flow a gcode linear move text."
	if gcodec.isProcedureDoneOrFileIsEmpty( gcodeText, 'flow'):
		return gcodeText
	if flowRepository == None:
		flowRepository = settings.getReadRepository( FlowRepository() )
	if not flowRepository.activateFlow.value:
		return gcodeText
	return FlowSkein().getCraftedGcode( gcodeText, flowRepository )

def getNewRepository():
	'Get new repository.'
	return FlowRepository()

def writeOutput(fileName, shouldAnalyze=True):
	"Flow a gcode linear move file."
	skeinforge_craft.writeChainTextWithNounMessage(fileName, 'flow', shouldAnalyze)


class FlowRepository:
	"A class to handle the flow settings."
	def __init__(self):
		"Set the default settings, execute title & settings fileName."
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.flow.html', self )
		self.fileNameInput = settings.FileNameInput().getFromFileName( fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Flow', self, '')
		self.activateFlow = settings.BooleanSetting().getFromValue('Activate Flow', self, True )
		self.flowRate = settings.FloatSpin().getFromValue( 50.0, 'Flow Rate (arbitrary units):', self, 250.0, 210.0 )
		self.executeTitle = 'Flow'

	def execute(self):
		"Flow button has been clicked."
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class FlowSkein:
	"A class to flow a skein of extrusions."
	def __init__(self):
		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.lineIndex = 0
		self.lines = None
		self.oldFlowRate = None
		self.oldLocation = None

	def addFlowRateLine(self):
		"Add flow rate line."
		flowRate = self.flowRepository.flowRate.value
		if flowRate != self.oldFlowRate:
			self.distanceFeedRate.addLine('M108 S' + euclidean.getFourSignificantFigures(flowRate))
		self.oldFlowRate = flowRate

	def getCraftedGcode( self, gcodeText, flowRepository ):
		"Parse gcode text and store the flow gcode."
		self.flowRepository = flowRepository
		self.lines = archive.getTextLines(gcodeText)
		self.parseInitialization()
		for line in self.lines[self.lineIndex :]:
			self.parseLine(line)
		return self.distanceFeedRate.output.getvalue()

	def parseInitialization(self):
		'Parse gcode initialization and store the parameters.'
		for self.lineIndex in xrange(len(self.lines)):
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			self.distanceFeedRate.parseSplitLine(firstWord, splitLine)
			if firstWord == '(</extruderInitialization>)':
				self.distanceFeedRate.addTagBracketedProcedure('flow')
				return
			self.distanceFeedRate.addLine(line)

	def parseLine(self, line):
		"Parse a gcode line and add it to the flow skein."
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if firstWord == 'G1' or firstWord == '(<layer>':
			self.addFlowRateLine()
		self.distanceFeedRate.addLine(line)


def main():
	"Display the flow dialog."
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == "__main__":
	main()
