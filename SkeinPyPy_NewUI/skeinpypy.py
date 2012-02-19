#!/usr/bin/python
"""
This page is in the table of contents.
==Overview==
===Introduction===
SkeinPyPy is a GPL tool chain to forge a gcode skein for a model. Based on Skeinforge.

The slicing code is the same as Skeinforge. But the UI has been revamped to be... sane.

"""

from __future__ import absolute_import

from optparse import OptionParser
from skeinforge_application.skeinforge_utilities import skeinforge_craft
from newui import mainWindow
import os
import sys
import platform
import subprocess

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

def getPyPyExe():
	"Return the path to the pypy executable if we can find it. Else return False"
	if platform.system() == "Windows":
		pypyExe = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../pypy/pypy.exe"));
	else:
		pypyExe = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../pypy/bin/pypy"));
	if os.path.exists(pypyExe):
		return pypyExe
	pypyExe = "/bin/pypy";
	if os.path.exists(pypyExe):
		return pypyExe
	pypyExe = "/usr/bin/pypy";
	if os.path.exists(pypyExe):
		return pypyExe
	pypyExe = "/usr/local/bin/pypy";
	if os.path.exists(pypyExe):
		return pypyExe
	return False

def runSkein(fileNames):
	"Run the slicer on the files. If we are running with PyPy then just do the slicing action. If we are running as Python, try to find pypy."
	pypyExe = getPyPyExe()
	for fileName in fileNames:
		if platform.python_implementation() == "PyPy":
			skeinforge_craft.writeOutput(fileName)
		elif pypyExe == False:
			print "************************************************"
			print "* Failed to find pypy, so slicing with python! *"
			print "************************************************"
			skeinforge_craft.writeOutput(fileName)
			print "************************************************"
			print "* Failed to find pypy, so sliced with python!  *"
			print "************************************************"
		else:
			subprocess.call([pypyExe, __file__, fileName])

def main():
	parser = OptionParser()
	(options, args) = parser.parse_args()
	sys.argv = [sys.argv[0]] + args
	if len( args ) > 0:
		runSkein(args)
	else:
		mainWindow.main()

if __name__ == '__main__':
	main()

