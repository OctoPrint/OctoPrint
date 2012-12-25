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
	parser.add_option("-r", "--print", action="store", type="string", dest="printfile",
		help="Open the printing interface, instead of the normal cura interface.")
	parser.add_option("-p", "--profile", action="store", type="string", dest="profile",
		help="Internal option, do not use!")
	parser.add_option("-s", "--slice", action="store_true", dest="slice",
		help="Slice the given files instead of opening them in Cura")
	parser.add_option("-w", "--web", action="store_true", dest="webui",
		help="Start the webui instead of the normal Cura UI")
	(options, args) = parser.parse_args()

	if options.profile is not None:
		profile.loadGlobalProfileFromString(options.profile)
	if options.profileini is not None:
		profile.loadGlobalProfile(options.profileini)

	if options.printfile is not None:
		from Cura.gui import printWindow
		printWindow.startPrintInterface(options.printfile)
	elif options.slice is not None:
		from Cura.util import sliceRun
		sliceRun.runSlice(args)
	elif options.webui:
		import Cura.webui as webapp
		webapp.run()
	else:
		#Place any unused arguments as last file, so Cura starts with opening those files.
		if len(args) > 0:
			profile.putPreference('lastFile', ';'.join(args))

		#Do not import anything from Cura.gui before this spot, as the above code also needs to run in pypy.
		from Cura.gui import app
		app.CuraApp().MainLoop()

if __name__ == '__main__':
	main()
