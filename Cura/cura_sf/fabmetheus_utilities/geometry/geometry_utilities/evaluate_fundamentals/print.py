"""
Boolean geometry utilities.

"""

from __future__ import absolute_import

import sys


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def _getAccessibleAttribute(attributeName):
	'Get the accessible attribute.'
	if attributeName in globalAccessibleAttributeDictionary:
		return globalAccessibleAttributeDictionary[attributeName]
	return None

def continuous(valueString):
	'Print continuous.'
	sys.stdout.write(str(valueString))
	return valueString

def line(valueString):
	'Print line.'
	print(valueString)
	return valueString


globalAccessibleAttributeDictionary = {'continuous' : continuous, 'line' : line}
