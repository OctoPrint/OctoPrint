"""
Vector3 is a three dimensional vector class.

Below are examples of Vector3 use.

>>> from vector3 import Vector3
>>> origin = Vector3()
>>> origin
0.0, 0.0, 0.0
>>> pythagoras = Vector3( 3, 4, 0 )
>>> pythagoras
3.0, 4.0, 0.0
>>> pythagoras.magnitude()
5.0
>>> pythagoras.magnitudeSquared()
25
>>> triplePythagoras = pythagoras * 3.0
>>> triplePythagoras
9.0, 12.0, 0.0
>>> plane = pythagoras.dropAxis()
>>> plane
(3+4j)
"""

from __future__ import absolute_import
try:
	import psyco
	psyco.full()
except:
	pass
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities import xml_simple_writer
import math
import operator


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Nophead <http://forums.reprap.org/profile.php?12,28>\nArt of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


class Vector3Index:
	'A three dimensional vector index class.'
	__slots__ = ['index', 'x', 'y', 'z']

	def __init__( self, index, x = 0.0, y = 0.0, z = 0.0 ):
		self.index = index
		self.x = x
		self.y = y
		self.z = z

	def __abs__(self):
		'Get the magnitude of the Vector3.'
		return math.sqrt( self.x * self.x + self.y * self.y + self.z * self.z )

	magnitude = __abs__

	def __add__(self, other):
		'Get the sum of this Vector3 and other one.'
		return Vector3Index( self.index, self.x + other.x, self.y + other.y, self.z + other.z )

	def __copy__(self):
		'Get the copy of this Vector3.'
		return Vector3Index( self.index, self.x, self.y, self.z )

	__pos__ = __copy__

	copy = __copy__

	def __div__(self, other):
		'Get a new Vector3 by dividing each component of this one.'
		return Vector3Index( self.index, self.x / other, self.y / other, self.z / other )

	def __eq__(self, other):
		'Determine whether this vector is identical to other one.'
		if other == None:
			return False
		if other.__class__ != self.__class__:
			return False
		return self.x == other.x and self.y == other.y and self.z == other.z

	def __floordiv__(self, other):
		'Get a new Vector3 by floor dividing each component of this one.'
		return Vector3Index( self.index, self.x // other, self.y // other, self.z // other )

	def __hash__(self):
		'Determine whether this vector is identical to other one.'
		return self.__repr__().__hash__()

	def __iadd__(self, other):
		'Add other Vector3 to this one.'
		self.x += other.x
		self.y += other.y
		self.z += other.z
		return self

	def __idiv__(self, other):
		'Divide each component of this Vector3.'
		self.x /= other
		self.y /= other
		self.z /= other
		return self

	def __ifloordiv__(self, other):
		'Floor divide each component of this Vector3.'
		self.x //= other
		self.y //= other
		self.z //= other
		return self

	def __imul__(self, other):
		'Multiply each component of this Vector3.'
		self.x *= other
		self.y *= other
		self.z *= other
		return self

	def __isub__(self, other):
		'Subtract other Vector3 from this one.'
		self.x -= other.x
		self.y -= other.y
		self.z -= other.z
		return self

	def __itruediv__(self, other):
		'True divide each component of this Vector3.'
		self.x = operator.truediv( self.x, other )
		self.y = operator.truediv( self.y, other )
		self.z = operator.truediv( self.z, other )
		return self

	def __mul__(self, other):
		'Get a new Vector3 by multiplying each component of this one.'
		return Vector3Index( self.index, self.x * other, self.y * other, self.z * other )

	def __ne__(self, other):
		'Determine whether this vector is not identical to other one.'
		return not self.__eq__(other)

	def __neg__(self):
		return Vector3Index( self.index, - self.x, - self.y, - self.z )

	def __nonzero__(self):
		return self.x != 0 or self.y != 0 or self.z != 0

	def __rdiv__(self, other):
		'Get a new Vector3 by dividing each component of this one.'
		return Vector3Index( self.index, other / self.x, other / self.y, other / self.z )

	def __repr__(self):
		'Get the string representation of this Vector3 index.'
		return '(%s, %s, %s, %s)' % (self.index, self.x, self.y, self.z)

	def __rfloordiv__(self, other):
		'Get a new Vector3 by floor dividing each component of this one.'
		return Vector3Index( self.index, other // self.x, other // self.y, other // self.z )

	def __rmul__(self, other):
		'Get a new Vector3 by multiplying each component of this one.'
		return Vector3Index( self.index, self.x * other, self.y * other, self.z * other )

	def __rtruediv__(self, other):
		'Get a new Vector3 by true dividing each component of this one.'
		return Vector3Index( self.index, operator.truediv( other , self.x ), operator.truediv( other, self.y ), operator.truediv( other, self.z ) )

	def __sub__(self, other):
		'Get the difference between the Vector3 and other one.'
		return Vector3Index( self.index, self.x - other.x, self.y - other.y, self.z - other.z )

	def __truediv__(self, other):
		'Get a new Vector3 by true dividing each component of this one.'
		return Vector3Index( self.index, operator.truediv( self.x, other ), operator.truediv( self.y, other ), operator.truediv( self.z, other ) )

	def _getAccessibleAttribute(self, attributeName):
		'Get the accessible attribute.'
		global globalGetAccessibleAttributeSet
		if attributeName in globalGetAccessibleAttributeSet:
			return getattr(self, attributeName, None)
		return None

	def _setAccessibleAttribute(self, attributeName, value):
		'Set the accessible attribute.'
		if attributeName in globalSetAccessibleAttributeSet:
			setattr(self, attributeName, value)

	def cross(self, other):
		'Calculate the cross product of this vector with other one.'
		return Vector3Index( self.index, self.y * other.z - self.z * other.y, - self.x * other.z + self.z * other.x, self.x * other.y - self.y * other.x )

	def distance(self, other):
		'Get the Euclidean distance between this vector and other one.'
		return math.sqrt( self.distanceSquared(other) )

	def distanceSquared(self, other):
		'Get the square of the Euclidean distance between this vector and other one.'
		separationX = self.x - other.x
		separationY = self.y - other.y
		separationZ = self.z - other.z
		return separationX * separationX + separationY * separationY + separationZ * separationZ

	def dot(self, other):
		'Calculate the dot product of this vector with other one.'
		return self.x * other.x + self.y * other.y + self.z * other.z

	def dropAxis( self, which = 2 ):
		'Get a complex by removing one axis of the vector3.'
		if which == 0:
			return complex( self.y, self.z )
		if which == 1:
			return complex( self.x, self.z )
		if which == 2:
			return complex( self.x, self.y )

	def getFloatList(self):
		'Get the vector as a list of floats.'
		return [ float( self.x ), float( self.y ), float( self.z ) ]

	def getIsDefault(self):
		'Determine if this is the zero vector.'
		if self.x != 0.0:
			return False
		if self.y != 0.0:
			return False
		return self.z == 0.0

	def getNormalized(self):
		'Get the normalized Vector3.'
		magnitude = abs(self)
		if magnitude == 0.0:
			return self.copy()
		return self / magnitude

	def magnitudeSquared(self):
		'Get the square of the magnitude of the Vector3.'
		return self.x * self.x + self.y * self.y + self.z * self.z

	def maximize(self, other):
		'Maximize the Vector3.'
		self.x = max(other.x, self.x)
		self.y = max(other.y, self.y)
		self.z = max(other.z, self.z)

	def minimize(self, other):
		'Minimize the Vector3.'
		self.x = min(other.x, self.x)
		self.y = min(other.y, self.y)
		self.z = min(other.z, self.z)

	def normalize(self):
		'Scale each component of this Vector3 so that it has a magnitude of 1. If this Vector3 has a magnitude of 0, this method has no effect.'
		magnitude = abs(self)
		if magnitude != 0.0:
			self /= magnitude

	def reflect( self, normal ):
		'Reflect the Vector3 across the normal, which is assumed to be normalized.'
		distance = 2 * ( self.x * normal.x + self.y * normal.y + self.z * normal.z )
		return Vector3Index( self.index, self.x - distance * normal.x, self.y - distance * normal.y, self.z - distance * normal.z )

	def setToVector3(self, other):
		'Set this Vector3 to be identical to other one.'
		self.x = other.x
		self.y = other.y
		self.z = other.z

	def setToXYZ( self, x, y, z ):
		'Set the x, y, and z components of this Vector3.'
		self.x = x
		self.y = y
		self.z = z


globalGetAccessibleAttributeSet = 'x y z'.split()
globalSetAccessibleAttributeSet = globalGetAccessibleAttributeSet
