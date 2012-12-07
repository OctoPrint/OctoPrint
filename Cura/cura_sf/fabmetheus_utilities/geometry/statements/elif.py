"""
Polygon path.

"""

from __future__ import absolute_import

from fabmetheus_utilities.geometry.geometry_utilities import evaluate


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def processElementNode(elementNode):
	"Process the xml element."
	pass

def processElse(elementNode):
	"Process the else statement."
	evaluate.processCondition(elementNode)
