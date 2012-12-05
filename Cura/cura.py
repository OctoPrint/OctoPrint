#!/usr/bin/python
"""
This page is in the table of contents.
==Overview==
===Introduction===
Cura is a GPL tool chain to forge a gcode skein for a model. Based on Skeinforge.

The slicing code is the same as Skeinforge. But the UI has been revamped to be... sane.

"""
from __future__ import absolute_import

from optparse import OptionParser

from util import profile

__author__ = 'Daid'
__credits__ = """
David Braam (daid303@gmail.com)
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
Ilya Kulakov (kulakov.ilya@gmail.com)

Organizations:
Ultimaker <http://www.ultimaker.com>
Art of Illusion <http://www.artofillusion.org/>"""

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

def main():
	parser = OptionParser(usage="usage: %prog [options] <filename>.stl")
	parser.add_option("-i", "--ini", action="store", type="string", dest="profileini",
		help="Load settings from a profile ini file")
	parser.add_option("-P", "--project", action="store_true", dest="openprojectplanner",
		help="Open the project planner")
	parser.add_option("-F", "--flat", action="store_true", dest="openflatslicer",
		help="Open the 2D SVG slicer (unfinished)")
	parser.add_option("-r", "--print", action="store", type="string", dest="printfile",
		help="Open the printing interface, instead of the normal cura interface.")
	parser.add_option("-p", "--profile", action="store", type="string", dest="profile",
		help="Internal option, do not use!")
	parser.add_option("-s", "--slice", action="store_true", dest="slice",
		help="Slice the given files instead of opening them in Cura")
	(options, args) = parser.parse_args()
	if options.profile != None:
		profile.loadGlobalProfileFromString(options.profile)
	if options.profileini != None:
		profile.loadGlobalProfile(options.profileini)
	if options.openprojectplanner != None:
		from gui import projectPlanner

		projectPlanner.main()
		return
	if options.openflatslicer != None:
		from gui import flatSlicerWindow

		flatSlicerWindow.main()
		return
	if options.printfile != None:
		from gui import printWindow

		printWindow.startPrintInterface(options.printfile)
		return

	if options.slice != None:
		from util import sliceRun

		sliceRun.runSlice(args)
	else:
		if len(args) > 0:
			profile.putPreference('lastFile', ';'.join(args))
		from gui import splashScreen

		splashScreen.showSplash(mainWindowRunCallback)


def mainWindowRunCallback(splash):
	from gui import mainWindow

	mainWindow.main(splash)

if __name__ == '__main__':
	main()
