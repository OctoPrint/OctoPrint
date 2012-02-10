"""
Vec3 is a three dimensional vector class.

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

import math
import operator


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Nophead <http://forums.reprap.org/profile.php?12,28>\nArt of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


class Vector3:
	"A three dimensional vector class."
	__slots__ = ['x', 'y', 'z']

	def __init__( self, x = 0.0, y = 0.0, z = 0.0 ):
		self.x = x
		self.y = y
		self.z = z

	def __abs__(self):
		"Get the magnitude of the Vector3."
		return math.sqrt( self.x * self.x + self.y * self.y + self.z * self.z )

	magnitude = __abs__

	def __add__(self, other):
		"Get the sum of this Vector3 and other one."
		return Vector3( self.x + other.x, self.y + other.y, self.z + other.z )

	def __copy__(self):
		"Get the copy of this Vector3."
		return Vector3( self.x, self.y, self.z )

	__pos__ = __copy__

	copy = __copy__

	def __div__(self, other):
		"Get a new Vector3 by dividing each component of this one."
		return Vector3( self.x / other, self.y / other, self.z / other )

	def __eq__(self, other):
		"Determine whether this vector is identical to other one."
		if other == None:
			return False
		return self.x == other.x and self.y == other.y and self.z == other.z

	def __floordiv__(self, other):
		"Get a new Vector3 by floor dividing each component of this one."
		return Vector3( self.x // other, self.y // other, self.z // other )

	def __hash__(self):
		"Determine whether this vector is identical to other one."
		return self.__repr__().__hash__()

	def __iadd__(self, other):
		"Add other Vector3 to this one."
		self.x += other.x
		self.y += other.y
		self.z += other.z
		return self

	def __idiv__(self, other):
		"Divide each component of this Vector3."
		self.x /= other
		self.y /= other
		self.z /= other
		return self

	def __ifloordiv__(self, other):
		"Floor divide each component of this Vector3."
		self.x //= other
		self.y //= other
		self.z //= other
		return self

	def __imul__(self, other):
		"Multiply each component of this Vector3."
		self.x *= other
		self.y *= other
		self.z *= other
		return self

	def __isub__(self, other):
		"Subtract other Vector3 from this one."
		self.x -= other.x
		self.y -= other.y
		self.z -= other.z
		return self

	def __itruediv__(self, other):
		"True divide each component of this Vector3."
		self.x = operator.truediv( self.x, other )
		self.y = operator.truediv( self.y, other )
		self.z = operator.truediv( self.z, other )
		return self

	def __mul__(self, other):
		"Get a new Vector3 by multiplying each component of this one."
		return Vector3( self.x * other, self.y * other, self.z * other )

	def __ne__(self, other):
		"Determine whether this vector is not identical to other one."
		return not self.__eq__(other)

	def __neg__(self):
		return Vector3( - self.x, - self.y, - self.z )

	def __nonzero__(self):
		return self.x != 0 or self.y != 0 or self.z != 0

	def __repr__(self):
		"Get the string representation of this Vector3."
		return '%s, %s, %s' % ( self.x, self.y, self.z )

	def __rdiv__(self, other):
		"Get a new Vector3 by dividing each component of this one."
		return Vector3( other / self.x, other / self.y, other / self.z )

	def __rfloordiv__(self, other):
		"Get a new Vector3 by floor dividing each component of this one."
		return Vector3( other // self.x, other // self.y, other // self.z )

	def __rmul__(self, other):
		"Get a new Vector3 by multiplying each component of this one."
		return Vector3( self.x * other, self.y * other, self.z * other )

	def __rtruediv__(self, other):
		"Get a new Vector3 by true dividing each component of this one."
		return Vector3( operator.truediv( other , self.x ), operator.truediv( other, self.y ), operator.truediv( other, self.z ) )

	def __sub__(self, other):
		"Get the difference between the Vector3 and other one."
		return Vector3( self.x - other.x, self.y - other.y, self.z - other.z )

	def __truediv__(self, other):
		"Get a new Vector3 by true dividing each component of this one."
		return Vector3( operator.truediv( self.x, other ), operator.truediv( self.y, other ), operator.truediv( self.z, other ) )

	def cross(self, other):
		"Calculate the cross product of this vector with other one."
		return Vector3( self.y * other.z - self.z * other.y, - self.x * other.z + self.z * other.x, self.x * other.y - self.y * other.x )

	def distance(self, other):
		"Get the Euclidean distance between this vector and other one."
		return math.sqrt( self.distanceSquared(other) )

	def distanceSquared(self, other):
		"Get the square of the Euclidean distance between this vector and other one."
		separationX = self.x - other.x
		separationY = self.y - other.y
		separationZ = self.z - other.z
		return separationX * separationX + separationY * separationY + separationZ * separationZ

	def dot(self, other):
		"Calculate the dot product of this vector with other one."
		return self.x * other.x + self.y * other.y + self.z * other.z

	def dropAxis( self, which ):
		"""Get a complex by removing one axis of this one.

		Keyword arguments:
		which -- the axis to drop (0=X, 1=Y, 2=Z)"""
		if which == 0:
			return complex( self.y, self.z )
		if which == 1:
			return complex( self.x, self.z )
		if which == 2:
			return complex( self.x, self.y )

	def getNormalized(self, other):
		"Get the normalized Vector3."
		magnitude = abs(self)
		if magnitude == 0.0:
			return self.copy()
		return self / magnitude

	def magnitudeSquared(self):
		"Get the square of the magnitude of the Vector3."
		return self.x * self.x + self.y * self.y + self.z * self.z

	def normalize(self):
		"Scale each component of this Vector3 so that it has a magnitude of 1. If this Vector3 has a magnitude of 0, this method has no effect."
		magnitude = abs(self)
		if magnitude != 0.0:
			self /= magnitude

	def reflect( self, normal ):
		"Reflect the Vector3 across the normal, which is assumed to be normalized."
		distance = 2 * ( self.x * normal.x + self.y * normal.y + self.z * normal.z )
		return Vector3( self.x - distance * normal.x, self.y - distance * normal.y, self.z - distance * normal.z )

	def setToVec3(self, other):
		"Set this Vector3 to be identical to other one."
		self.x = other.x
		self.y = other.y
		self.z = other.z

	def setToXYZ( self, x, y, z ):
		"Set the x, y, and z components of this Vector3."
		self.x = x
		self.y = y
		self.z = z

"""
class Vector3:
	__slots__ = ['x', 'y', 'z']

	def __init__(self, x, y, z):
		self.x = x
		self.y = y
		self.z = z

	def __copy__(self):
		return self.__class__(self.x, self.y, self.z)

	copy = __copy__

	def __repr__(self):
		return 'Vector3(%.2f, %.2f, %.2f)' % (self.x,
											  self.y,
											  self.z)

	def __eq__(self, other):
		if isinstance(other, Vector3):
			return self.x == other.x and \
				   self.y == other.y and \
				   self.z == other.z
		else:
			assert hasattr(other, '__len__') and len(other) == 3
			return self.x == other[0] and \
				   self.y == other[1] and \
				   self.z == other[2]

	def __ne__(self, other):
		return not self.__eq__(other)

	def __nonzero__(self):
		return self.x != 0 or self.y != 0 or self.z != 0

	def __len__(self):
		return 3

	def __getitem__(self, key):
		return (self.x, self.y, self.z)[key]

	def __setitem__(self, key, value):
		l = [self.x, self.y, self.z]
		l[key] = value
		self.x, self.y, self.z = l

	def __iter__(self):
		return iter((self.x, self.y, self.z))

	def __getattr__(self, name):
		try:
			return tuple([(self.x, self.y, self.z)['xyz'.index(c)] \
						  for c in name])
		except ValueError:
			raise AttributeError, name

	if _enable_swizzle_set:
		# This has detrimental performance on ordinary setattr as well
		# if enabled
		def __setattr__(self, name, value):
			if len(name) == 1:
				object.__setattr__(self, name, value)
			else:
				try:
					l = [self.x, self.y, self.z]
					for c, v in map(None, name, value):
						l['xyz'.index(c)] = v
					self.x, self.y, self.z = l
				except ValueError:
					raise AttributeError, name


	def __add__(self, other):
		if isinstance(other, Vector3):
			# Vector + Vector -> Vector
			# Vector + Point -> Point
			# Point + Point -> Vector
			if self.__class__ is other.__class__:
				_class = Vector3
			else:
				_class = Point3
			return _class(self.x + other.x,
						  self.y + other.y,
						  self.z + other.z)
		else:
			assert hasattr(other, '__len__') and len(other) == 3
			return Vector3(self.x + other[0],
						   self.y + other[1],
						   self.z + other[2])
	__radd__ = __add__

	def __iadd__(self, other):
		if isinstance(other, Vector3):
			self.x += other.x
			self.y += other.y
			self.z += other.z
		else:
			self.x += other[0]
			self.y += other[1]
			self.z += other[2]
		return self

	def __sub__(self, other):
		if isinstance(other, Vector3):
			# Vector - Vector -> Vector
			# Vector - Point -> Point
			# Point - Point -> Vector
			if self.__class__ is other.__class__:
				_class = Vector3
			else:
				_class = Point3
			return Vector3(self.x - other.x,
						   self.y - other.y,
						   self.z - other.z)
		else:
			assert hasattr(other, '__len__') and len(other) == 3
			return Vector3(self.x - other[0],
						   self.y - other[1],
						   self.z - other[2])

   
	def __rsub__(self, other):
		if isinstance(other, Vector3):
			return Vector3(other.x - self.x,
						   other.y - self.y,
						   other.z - self.z)
		else:
			assert hasattr(other, '__len__') and len(other) == 3
			return Vector3(other.x - self[0],
						   other.y - self[1],
						   other.z - self[2])

	def __mul__(self, other):
		if isinstance(other, Vector3):
			# TODO component-wise mul/div in-place and on Vector2; docs.
			if self.__class__ is Point3 or other.__class__ is Point3:
				_class = Point3
			else:
				_class = Vector3
			return _class(self.x * other.x,
						  self.y * other.y,
						  self.z * other.z)
		else: 
			assert type(other) in (int, long, float)
			return Vector3(self.x * other,
						   self.y * other,
						   self.z * other)

	__rmul__ = __mul__

	def __imul__(self, other):
		assert type(other) in (int, long, float)
		self.x *= other
		self.y *= other
		self.z *= other
		return self

	def __div__(self, other):
		assert type(other) in (int, long, float)
		return Vector3(operator.div(self.x, other),
					   operator.div(self.y, other),
					   operator.div(self.z, other))


	def __rdiv__(self, other):
		assert type(other) in (int, long, float)
		return Vector3(operator.div(other, self.x),
					   operator.div(other, self.y),
					   operator.div(other, self.z))

	def __floordiv__(self, other):
		assert type(other) in (int, long, float)
		return Vector3(operator.floordiv(self.x, other),
					   operator.floordiv(self.y, other),
					   operator.floordiv(self.z, other))


	def __rfloordiv__(self, other):
		assert type(other) in (int, long, float)
		return Vector3(operator.floordiv(other, self.x),
					   operator.floordiv(other, self.y),
					   operator.floordiv(other, self.z))

	def __truediv__(self, other):
		assert type(other) in (int, long, float)
		return Vector3(operator.truediv(self.x, other),
					   operator.truediv(self.y, other),
					   operator.truediv(self.z, other))


	def __rtruediv__(self, other):
		assert type(other) in (int, long, float)
		return Vector3(operator.truediv(other, self.x),
					   operator.truediv(other, self.y),
					   operator.truediv(other, self.z))
	
	def __neg__(self):
		return Vector3(-self.x,
						-self.y,
						-self.z)

	__pos__ = __copy__
	
	def __abs__(self):
		return math.sqrt(self.x ** 2 + \
						 self.y ** 2 + \
						 self.z ** 2)

	magnitude = __abs__

	def magnitude_squared(self):
		return self.x ** 2 + \
			   self.y ** 2 + \
			   self.z ** 2

	def normalize(self):
		d = self.magnitude()
		if d:
			self.x /= d
			self.y /= d
			self.z /= d
		return self

	def normalized(self):
		d = self.magnitude()
		if d:
			return Vector3(self.x / d, 
						   self.y / d, 
						   self.z / d)
		return self.copy()

	def dot(self, other):
		assert isinstance(other, Vector3)
		return self.x * other.x + \
			   self.y * other.y + \
			   self.z * other.z

	def cross(self, other):
		assert isinstance(other, Vector3)
		return Vector3(self.y * other.z - self.z * other.y,
					   -self.x * other.z + self.z * other.x,
					   self.x * other.y - self.y * other.x)

	def reflect(self, normal):
		# assume normal is normalized
		assert isinstance(normal, Vector3)
		d = 2 * (self.x * normal.x + self.y * normal.y + self.z * normal.z)
		return Vector3(self.x - d * normal.x,
					   self.y - d * normal.y,
					   self.z - d * normal.z)
"""
