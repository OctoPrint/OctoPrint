"""
Prepare is a script to remove the generated files, run wikifier, and finally zip the package.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities import archive
from fabmetheus_utilities.fabmetheus_tools import wikifier
import os


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def prepareWikify():
	'Remove generated files, then wikify the file comments.'
	removeGeneratedFiles()
	wikifier.main()
	removeZip()

def removeCSVFile(csvFilePath):
	'Remove csv file.'
	if 'alterations' in csvFilePath and 'example_' not in csvFilePath:
		os.remove(csvFilePath)
		print('removeGeneratedFiles deleted ' + csvFilePath)

def removeGcodeFile(gcodeFilePath):
	'Remove gcode file.'
	if 'alterations' not in gcodeFilePath:
		os.remove(gcodeFilePath)
		print('removeGeneratedFiles deleted ' + gcodeFilePath)
		return
	if 'example_' not in gcodeFilePath:
		os.remove(gcodeFilePath)
		print('removeGeneratedFiles deleted ' + gcodeFilePath)

def removeGeneratedFiles():
	'Remove generated files.'
	csvFilePaths = archive.getFilesWithFileTypesWithoutWordsRecursively(['csv'])
	for csvFilePath in csvFilePaths:
		removeCSVFile(csvFilePath)
	gcodeFilePaths = archive.getFilesWithFileTypesWithoutWordsRecursively(['gcode'])
	for gcodeFilePath in gcodeFilePaths:
		removeGcodeFile(gcodeFilePath)
	svgFilePaths = archive.getFilesWithFileTypesWithoutWordsRecursively(['svg'])
	for svgFilePath in svgFilePaths:
		removeSVGFile(svgFilePath)
	xmlFilePaths = archive.getFilesWithFileTypesWithoutWordsRecursively(['xml'])
	for xmlFilePath in xmlFilePaths:
		removeXMLFile(xmlFilePath)
	archive.removeBackupFilesByTypes(['gcode', 'svg', 'xml'])

def removeSVGFile(svgFilePath):
	'Remove svg file.'
	if archive.getEndsWithList(svgFilePath, ['_bottom.svg', '_carve.svg', '_chop.svg', '_cleave.svg', '_scale.svg', '_vectorwrite.svg']):
		os.remove(svgFilePath)
		print('removeGeneratedFiles deleted ' + svgFilePath)

def removeXMLFile(xmlFilePath):
	'Remove xml file.'
	if archive.getEndsWithList(xmlFilePath, ['_interpret.xml']):
		os.remove(xmlFilePath)
		print('removeGeneratedFiles deleted ' + xmlFilePath)

def removeZip():
	'Remove the zip file, then generate a new one.zip -r reprap_python_beanshell * -x \*.pyc \*~'
	zipName = 'reprap_python_beanshell'
	zipNameExtension = zipName + '.zip'
	if zipNameExtension in os.listdir(os.getcwd()):
		os.remove(zipNameExtension)
	shellCommand = 'zip -r %s * -x \*.pyc \*~' % zipName
	if os.system(shellCommand) != 0:
		print('Failed to execute the following command in removeZip in prepare.')
		print(shellCommand)

def main():
	'Run main function.'
	prepareWikify()

if __name__ == "__main__":
	main()
