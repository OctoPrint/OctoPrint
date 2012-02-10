"""
This page is in the table of contents.
Zoom out is a mouse tool to zoom out the display at the point where the mouse was clicked, decreasing the scale by a factor of two.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from skeinforge_application.skeinforge_plugins.analyze_plugins.analyze_utilities import zoom_in
from fabmetheus_utilities import settings


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getNewMouseTool():
	"Get a new mouse tool."
	return ZoomOut()


class ZoomOut( zoom_in.ZoomIn ):
	"The zoom out mouse tool."
	def getMultiplier(self):
		"Get the scale multiplier."
		return 0.5
