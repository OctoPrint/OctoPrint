#!/usr/bin/python
"""
This page is in the table of contents.
==Overview==
===Introduction===
Cura is a GPL tool chain to forge a gcode skein for a model. Based on Skeinforge.

The slicing code is the same as Skeinforge. But the UI has been revamped to be... sane.

"""
from __future__ import absolute_import

import sys
import warnings
from optparse import OptionParser

from Cura.util import profile

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

	if options.profile is not None:
		profile.loadGlobalProfileFromString(options.profile)
	if options.profileini is not None:
		profile.loadGlobalProfile(options.profileini)

	if options.openprojectplanner is not None:
		from Cura.gui import projectPlanner
		projectPlanner.main()
	elif options.openflatslicer is not None:
		from Cura.gui import flatSlicerWindow
		flatSlicerWindow.main()
	elif options.printfile is not None:
		from Cura.gui import printWindow
		printWindow.startPrintInterface(options.printfile)
	elif options.slice is not None:
		from Cura.util import sliceRun
		sliceRun.runSlice(args)
	else:
		if len(args) > 0:
			profile.putPreference('lastFile', ';'.join(args))

		import wx._core
		from Cura.gui import splashScreen

		class CuraApp(wx.App):
			def MacOpenFile(self, path):
				try:
					pass
				except Exception as e:
					warnings.warn("File at {p} cannot be read: {e}".format(p=path, e=str(e)))

		def mainWindowRunCallback(splash):
			from Cura.gui import mainWindow
			if splash is not None:
				splash.Show(False)
			mainWindow.main()

		app = CuraApp(False)
		# Apple discourages usage of splash screens on a mac.
		if sys.platform.startswith('darwin'):
			mainWindowRunCallback(None)
		else:
			splashScreen.splashScreen(mainWindowRunCallback)
		app.MainLoop()

if __name__ == '__main__':
	main()
