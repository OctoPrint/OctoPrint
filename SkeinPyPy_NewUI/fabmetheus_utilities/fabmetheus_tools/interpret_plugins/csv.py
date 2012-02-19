"""
This page is in the table of contents.
The csv.py script is an import translator plugin to get a carving from an csv file.

An import plugin is a script in the interpret_plugins folder which has the function getCarving.  It is meant to be run from the interpret tool.  To ensure that the plugin works on platforms which do not handle file capitalization properly, give the plugin a lower case name.

The getCarving function takes the file name of an csv file and returns the carving.

"""


from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities import archive
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import xml_simple_reader
import sys


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Nophead <http://hydraraptor.blogspot.com/>\nArt of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCarving(fileName=''):
	"Get the carving for the csv file."
	csvText = archive.getFileText(fileName)
	if csvText == '':
		return None
	csvParser = CSVSimpleParser( fileName, None, csvText )
	lowerLocalName = csvParser.getDocumentElement().getNodeName().lower()
	pluginModule = archive.getModuleWithDirectoryPath( getPluginsDirectoryPath(), lowerLocalName )
	if pluginModule == None:
		return None
	return pluginModule.getCarvingFromParser( csvParser )

def getLineDictionary(line):
	"Get the line dictionary."
	lineDictionary = {}
	splitLine = line.split('\t')
	for splitLineIndex in xrange( len(splitLine) ):
		word = splitLine[ splitLineIndex ]
		if word != '':
			lineDictionary[ splitLineIndex ] = word
	return lineDictionary

def getPluginsDirectoryPath():
	"Get the plugins directory path."
	return archive.getInterpretPluginsPath('xml_plugins')


class CSVElement( xml_simple_reader.XMLElement ):
	"A csv element."
	def continueParsingObject( self, line, lineStripped ):
		"Parse replaced line."
		splitLineStripped = lineStripped.split('\t')
		key = splitLineStripped[0]
		value = splitLineStripped[1]
		self.attributes[key] = value
		self.addToIdentifierDictionaries()

	def continueParsingTable( self, line, lineStripped ):
		"Parse replaced line."
		if self.headingDictionary == None:
			self.headingDictionary = getLineDictionary(line)
			return
		csvElement = self
		oldAttributesLength = len( self.attributes )
		if oldAttributesLength > 0:
			csvElement = CSVElement()
		csvElement.parentNode = self.parentNode
		csvElement.localName = self.localName
		lineDictionary = getLineDictionary(line)
		for columnIndex in lineDictionary.keys():
			if columnIndex in self.headingDictionary:
				key = self.headingDictionary[ columnIndex ]
				value = lineDictionary[ columnIndex ]
				csvElement.attributes[key] = value
		csvElement.addToIdentifierDictionaries()
		if len( csvElement.attributes ) == 0 or oldAttributesLength == 0 or self.parentNode == None:
			return
		self.parentNode.childNodes.append( csvElement )

	def getElementFromObject( self, leadingTabCount, lineStripped, oldElement ):
		"Parse replaced line."
		splitLine = lineStripped.split('\t')
		self.localName = splitLine[1]
		if leadingTabCount == 0:
			return self
		self.parentNode = oldElement
		while leadingTabCount <= self.parentNode.getNumberOfParents():
			self.parentNode = self.parentNode.parentNode
		self.parentNode.childNodes.append(self)
		return self

	def getElementFromTable( self, leadingTabCount, lineStripped, oldElement ):
		"Parse replaced line."
		self.headingDictionary = None
		return self.getElementFromObject( leadingTabCount, lineStripped, oldElement )

	def getNumberOfParents(self):
		"Get the number of parent nodes."
		if self.parentNode == None:
			return 0
		return self.parentNode.getNumberOfParents() + 1


class CSVSimpleParser( xml_simple_reader.DocumentNode ):
	"A simple csv parser."
	def __init__( self, parentNode, csvText ):
		"Add empty lists."
		self.continueFunction = None
		self.extraLeadingTabCount = None
		self.lines = archive.getTextLines( csvText )
		self.oldCSVElement = None
		self.documentElement = None
		for line in self.lines:
			self.parseLine(line)

	def getNewCSVElement( self, leadingTabCount, lineStripped ):
		"Get a new csv element."
		if self.documentElement != None and self.extraLeadingTabCount == None:
			self.extraLeadingTabCount = 1 - leadingTabCount
		if self.extraLeadingTabCount != None:
			leadingTabCount += self.extraLeadingTabCount
		if lineStripped[ : len('_table') ] == '_table' or lineStripped[ : len('_t') ] == '_t':
			self.oldCSVElement = CSVElement().getElementFromTable( leadingTabCount, lineStripped, self.oldCSVElement )
			self.continueFunction = self.oldCSVElement.continueParsingTable
			return
		self.oldCSVElement = CSVElement().getElementFromObject( leadingTabCount, lineStripped, self.oldCSVElement )
		self.continueFunction = self.oldCSVElement.continueParsingObject

	def parseLine(self, line):
		"Parse a gcode line and add it to the inset skein."
		lineStripped = line.lstrip()
		if len( lineStripped ) < 1:
			return
		leadingPart = line[ : line.find( lineStripped ) ]
		leadingTabCount = leadingPart.count('\t')
		if lineStripped[ : len('_') ] == '_':
			self.getNewCSVElement( leadingTabCount, lineStripped )
			if self.documentElement == None:
				self.documentElement = self.oldCSVElement
				self.documentElement.document = self
			return
		if self.continueFunction != None:
			self.continueFunction( line, lineStripped )


def main():
	"Display the inset dialog."
	if len(sys.argv) > 1:
		getCarving(' '.join(sys.argv[1 :]))

if __name__ == "__main__":
	main()
