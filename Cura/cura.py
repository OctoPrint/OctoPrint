#!/usr/bin/python
"""
This page is in the table of contents.
==Overview==
===Introduction===
Cura is a GPL tool chain to forge a gcode skein for a model. Based on Skeinforge.

The slicing code is the same as Skeinforge. But the UI has been revamped to be... sane.

"""

from __future__ import absolute_import
import __init__

import sys
import platform
from optparse import OptionParser

from util import profile
from util import sliceRun

__author__ = 'Daid'
__credits__ = """
Enrique Perez (perez_enrique@yahoo.com)
Adrian Bowyer <http://forums.reprap.org/profile.php?12,13>
Brendan Erwin <http://forums.reprap.org/profile.php?12,217>
Greenarrow <http://forums.reprap.org/profile.php?12,81>
Ian England <http://forums.reprap.org/profile.php?12,192>
John Gilmore <http://forums.reprap.org/profile.php?12,364>
Jonwise <http://forums.reprap.org/profile.php?12,716>
Kyle Corbitt <http://forums.reprap.org/profile.php?12,90>
Michael Duffin <http://forums.reprap.org/profile.php?12,930>
Marius Kintel <http://reprap.soup.io/>
Nophead <http://www.blogger.com/profile/12801535866788103677>
PJR <http://forums.reprap.org/profile.php?12,757>
Reece.Arnott <http://forums.reprap.org/profile.php?12,152>
Wade <http://forums.reprap.org/profile.php?12,489>
Xsainnz <http://forums.reprap.org/profile.php?12,563>
Zach Hoeken <http://blog.zachhoeken.com/>

Organizations:
Art of Illusion <http://www.artofillusion.org/>"""

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

def main():
	parser = OptionParser(usage="usage: %prog [options] <filename>.stl")
	parser.add_option("-p", "--profile", action="store", type="string", dest="profile", help="Use these profile settings instead of loading current_profile.ini")
	parser.add_option("-r", "--print", action="store", type="string", dest="printfile", help="Open the printing interface, instead of the normal cura interface.")
	(options, args) = parser.parse_args()
	if options.profile != None:
		profile.loadGlobalProfileFromString(options.profile)
	if options.printfile != None:
		from gui import printWindow
		printWindow.startPrintInterface(options.printfile)
		return

	if len( args ) > 0:
		sliceRun.runSlice(args)
	else:
		from gui import mainWindow
		mainWindow.main()

if __name__ == '__main__':
	main()

