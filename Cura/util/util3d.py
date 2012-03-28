
import math

class Vector3():
	def __init__(self, x=0.0, y=0.0, z=0.0):
		self.x = x
		self.y = y
		self.z = z

	def __copy__(self):
		return Vector3(self.x, self.y, self.z)

	def copy(self):
		return Vector3(self.x, self.y, self.z)

	def __repr__(self):
		return '%s, %s, %s' % ( self.x, self.y, self.z )

	def __add__(self, v):
		return Vector3( self.x + v.x, self.y + v.y, self.z + v.z )

	def __sub__(self, v):
		return Vector3( self.x - v.x, self.y - v.y, self.z - v.z )

	def __mul__(self, v):
		return Vector3( self.x * v, self.y * v, self.z * v )

	def __div__(self, v):
		return Vector3( self.x / v, self.y / v, self.z / v )

	def __neg__(self):
		return Vector3( - self.x, - self.y, - self.z )

	def __iadd__(self, v):
		self.x += v.x
		self.y += v.x
		self.z += v.x
		return self

	def __isub__(self, v):
		self.x += v.x
		self.y += v.x
		self.z += v.x
		return self

	def __imul__(self, v):
		self.x *= v
		self.y *= v
		self.z *= v
		return self

	def __idiv__(self, v):
		self.x /= v
		self.y /= v
		self.z /= v
		return self

	def cross(self, v):
		return Vector3(self.y * v.z - self.z * v.y, -self.x * v.z + self.z * v.x, self.x * v.y - self.y * v.x)

	def vsize(self):
		return math.sqrt( self.x * self.x + self.y * self.y + self.z * self.z )

	def normalize(self):
		f = self.vsize()
		if f != 0.0:
			self.x /= f
			self.y /= f
			self.z /= f

