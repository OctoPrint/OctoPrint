"""
Boolean geometry utilities.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities.vector3index import Vector3Index
from fabmetheus_utilities import euclidean
import math


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def _getAccessibleAttribute(attributeName):
	'Get the accessible attribute.'
	if attributeName in globalAccessibleAttributeDictionary:
		return globalAccessibleAttributeDictionary[attributeName]
	return None

def getComplex(x=0.0, y=0.0):
	'Get the complex.'
	return complex(x, y)

def getCylindrical(azimuthDegrees, radius=1.0, z=0.0):
	'Get the cylindrical vector3 by degrees.'
	return getCylindricalByRadians(math.radians(azimuthDegrees), radius, z)

def getCylindricalByRadians(azimuthRadians, radius=1.0, z=0.0):
	'Get the cylindrical vector3 by radians.'
	polar = radius * euclidean.getWiddershinsUnitPolar(azimuthRadians)
	return Vector3(polar.real, polar.imag, z)

def getNestedVectorTestExample(x=0.0, y=0.0, z=0.0):
	'Get the NestedVectorTestExample.'
	return NestedVectorTestExample(Vector3(x, y, z))

def getPolar(angleDegrees, radius=1.0):
	'Get the complex polar by degrees.'
	return radius * euclidean.getWiddershinsUnitPolar(math.radians(angleDegrees))

def getPolarByRadians(angleRadians, radius=1.0):
	'Get the complex polar by radians.'
	return radius * euclidean.getWiddershinsUnitPolar(angleRadians)

def getSpherical(azimuthDegrees, elevationDegrees, radius=1.0):
	'Get the spherical vector3 unit by degrees.'
	return getSphericalByRadians(math.radians(azimuthDegrees), math.radians(elevationDegrees), radius)

def getSphericalByRadians(azimuthRadians, elevationRadians, radius=1.0):
	'Get the spherical vector3 unit by radians.'
	elevationComplex = euclidean.getWiddershinsUnitPolar(elevationRadians)
	azimuthComplex = euclidean.getWiddershinsUnitPolar(azimuthRadians) * elevationComplex.real
	return Vector3(azimuthComplex.real, azimuthComplex.imag, elevationComplex.imag) * radius

def getVector3(x=0.0, y=0.0, z=0.0):
	'Get the vector3.'
	return Vector3(x, y, z)

def getVector3Index(index=0, x=0.0, y=0.0, z=0.0):
	'Get the vector3.'
	return Vector3Index(index, x, y, z)


class NestedVectorTestExample:
	'Class to test local attribute.'
	def __init__(self, vector3):
		'Get the accessible attribute.'
		self.vector3 = vector3

	def _getAccessibleAttribute(self, attributeName):
		"Get the accessible attribute."
		if attributeName == 'vector3':
			return getattr(self, attributeName, None)
		return None


globalAccessibleAttributeDictionary = {
	'complex' : getComplex,
	'getCylindrical' : getCylindrical,
	'getCylindricalByRadians' : getCylindricalByRadians,
	'getPolar' : getPolar,
	'getPolarByRadians' : getPolarByRadians,
	'getSpherical' : getSpherical,
	'getSphericalByRadians' : getSphericalByRadians,
	'NestedVectorTestExample' : getNestedVectorTestExample,
	'Vector3' : getVector3,
	'Vector3Index' : getVector3Index}
