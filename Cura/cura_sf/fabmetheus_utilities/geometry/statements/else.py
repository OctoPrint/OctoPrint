"""
Polygon path.

"""

from __future__ import absolute_import


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def processElementNode(elementNode):
	"Process the xml element."
	pass

def processElse(elementNode):
	"Process the else statement."
	functions = elementNode.getXMLProcessor().functions
	if len(functions) < 1:
		print('Warning, "else" element is not in a function in processElse in else.py for:')
		print(elementNode)
		return
	functions[-1].processChildNodes(elementNode)
