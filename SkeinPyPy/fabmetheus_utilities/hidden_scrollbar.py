"""
Hidden scrollbar is in its own file so that even if Tkinter is not installed, settings can still be imported.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__
try:
	import Tkinter
	class HiddenScrollbar(Tkinter.Scrollbar):
		'A class to hide the scrollbar if it is not needed.'
		def set(self, lo, hi):
			'Add to grid is needed, remove if not.'
			if float(lo) <= 0.0 and float(hi) >= 1.0:
				self.grid_remove()
				self.visible = False
			else:
				self.grid()
				self.visible = True
			Tkinter.Scrollbar.set(self, lo, hi)
except:
	pass


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/23/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
