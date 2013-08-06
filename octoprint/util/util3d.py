from __future__ import absolute_import

import math
import numpy

class Vector3(object):
	def __init__(self, x=0.0, y=0.0, z=0.0):
		self.x = x
		self.y = y
		self.z = z

	def __copy__(self):
		return Vector3(self.x, self.y, self.z)

	def copy(self):
		return Vector3(self.x, self.y, self.z)

	def __repr__(self):
		return 'V[%s, %s, %s]' % ( self.x, self.y, self.z )

	def __add__(self, v):
		return Vector3( self.x + v.x, self.y + v.y, self.z + v.z )

	def __sub__(self, v):
		return Vector3( self.x - v.x, self.y - v.y, self.z - v.z )

	def __mul__(self, v):
		return Vector3( self.x * v, self.y * v, self.z * v )

	def __div__(self, v):
		return Vector3( self.x / v, self.y / v, self.z / v )
	__truediv__ = __div__

	def __neg__(self):
		return Vector3( - self.x, - self.y, - self.z )

	def __iadd__(self, v):
		self.x += v.x
		self.y += v.y
		self.z += v.z
		return self

	def __isub__(self, v):
		self.x += v.x
		self.y += v.y
		self.z += v.z
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

	def almostEqual(self, v):
		return (abs(self.x - v.x) + abs(self.y - v.y) + abs(self.z - v.z)) < 0.00001
	
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

	def min(self, v):
		return Vector3(min(self.x, v.x), min(self.y, v.y), min(self.z, v.z))

	def max(self, v):
		return Vector3(max(self.x, v.x), max(self.y, v.y), max(self.z, v.z))

	def dist(self, v):
		xx = self.x - v.x
		yy = self.y - v.y
		zz = self.z - v.z
		return math.sqrt(xx * xx + yy * yy + zz * zz)

class AABB(object):
	def __init__(self, vMin, vMax):
		self.vMin = vMin
		self.vMax = vMax
		self.perimeter = numpy.sum(self.vMax - self.vMin)
	
	def combine(self, aabb):
		return AABB(numpy.minimum(self.vMin, aabb.vMin), numpy.maximum(self.vMax, aabb.vMax))
	
	def overlap(self, aabb):
		if aabb.vMin[0] - self.vMax[0] > 0.0 or aabb.vMin[1] - self.vMax[1] > 0.0 or aabb.vMin[2] - self.vMax[2] > 0.0:
			return False
		if self.vMin[0] - aabb.vMax[0] > 0.0 or self.vMin[1] - aabb.vMax[1] > 0.0 or self.vMin[2] - aabb.vMax[2] > 0.0:
			return False
		return True
	
	def __repr__(self):
		return "AABB:%s - %s" % (str(self.vMin), str(self.vMax))

class _AABBNode(object):
	def __init__(self, aabb):
		self.child1 = None
		self.child2 = None
		self.parent = None
		self.height = 0
		self.aabb = aabb
	
	def isLeaf(self):
		return self.child1 == None
	
class AABBTree(object):
	def __init__(self):
		self.root = None
	
	def insert(self, aabb):
		newNode = _AABBNode(aabb)
		if self.root == None:
			self.root = newNode
			return
		
		node = self.root
		while not node.isLeaf():
			child1 = node.child1
			child2 = node.child2
			
			area = node.aabb.perimeter
			combinedAABB = node.aabb.combine(aabb)
			combinedArea = combinedAABB.perimeter
			
			cost = 2.0 * combinedArea
			inheritanceCost = 2.0 * (combinedArea - area)

			if child1.isLeaf():
				cost1 = aabb.combine(child1.aabb).perimeter + inheritanceCost
			else:
				oldArea = child1.aabb.perimeter
				newArea = aabb.combine(child1.aabb).perimeter
				cost1 = (newArea - oldArea) + inheritanceCost

			if child2.isLeaf():
				cost2 = aabb.combine(child1.aabb).perimeter + inheritanceCost
			else:
				oldArea = child2.aabb.perimeter
				newArea = aabb.combine(child2.aabb).perimeter
				cost2 = (newArea - oldArea) + inheritanceCost

			if cost < cost1 and cost < cost2:
				break

			if cost1 < cost2:
				node = child1
			else:
				node = child2

		sibling = node

		# Create a new parent.
		oldParent = sibling.parent
		newParent = _AABBNode(aabb.combine(sibling.aabb))
		newParent.parent = oldParent
		newParent.height = sibling.height + 1

		if oldParent != None:
			# The sibling was not the root.
			if oldParent.child1 == sibling:
				oldParent.child1 = newParent
			else:
				oldParent.child2 = newParent

			newParent.child1 = sibling
			newParent.child2 = newNode
			sibling.parent = newParent
			newNode.parent = newParent
		else:
			# The sibling was the root.
			newParent.child1 = sibling
			newParent.child2 = newNode
			sibling.parent = newParent
			newNode.parent = newParent
			self.root = newParent

		# Walk back up the tree fixing heights and AABBs
		node = newNode.parent
		while node != None:
			node = self._balance(node)

			child1 = node.child1
			child2 = node.child2

			node.height = 1 + max(child1.height, child2.height)
			node.aabb = child1.aabb.combine(child2.aabb)

			node = node.parent

	def _balance(self, A):
		if A.isLeaf() or A.height < 2:
			return A

		B = A.child1
		C = A.child2
		
		balance = C.height - B.height

		# Rotate C up
		if balance > 1:
			F = C.child1;
			G = C.child2;

			# Swap A and C
			C.child1 = A;
			C.parent = A.parent;
			A.parent = C;

			# A's old parent should point to C
			if C.parent != None:
				if C.parent.child1 == A:
					C.parent.child1 = C
				else:
					C.parent.child2 = C
			else:
				self.root = C

			# Rotate
			if F.height > G.height:
				C.child2 = F
				A.child2 = G
				G.parent = A
				A.aabb = B.aabb.combine(G.aabb)
				C.aabb = A.aabb.combine(F.aabb)

				A.height = 1 + max(B.height, G.height)
				C.height = 1 + max(A.height, F.height)
			else:
				C.child2 = G
				A.child2 = F
				F.parent = A
				A.aabb = B.aabb.combine(F.aabb)
				C.aabb = A.aabb.combine(G.aabb)

				A.height = 1 + max(B.height, F.height)
				C.height = 1 + max(A.height, G.height)

			return C;

		# Rotate B up
		if balance < -1:
			D = B.child1
			E = B.child2

			# Swap A and B
			B.child1 = A
			B.parent = A.parent
			A.parent = B

			# A's old parent should point to B
			if B.parent != None:
				if B.parent.child1 == A:
					B.parent.child1 = B
				else:
					B.parent.child2 = B
			else:
				self.root = B

			# Rotate
			if D.height > E.height:
				B.child2 = D
				A.child1 = E
				E.parent = A
				A.aabb = C.aabb.combine(E.aabb)
				B.aabb = A.aabb.combine(D.aabb)

				A.height = 1 + max(C.height, E.height)
				B.height = 1 + max(A.height, D.height)
			else:
				B.child2 = E
				A.child1 = D
				D.parent = A
				A.aabb = C.aabb.combine(D.aabb)
				B.aabb = A.aabb.combine(E.aabb)

				A.height = 1 + max(C.height, D.height)
				B.height = 1 + max(A.height, E.height)

			return B

		return A

	def query(self, aabb):
		resultList = []
		if self.root != None:
			self._query(self.root, aabb, resultList)
		return resultList
	
	def _query(self, node, aabb, resultList):
		if not aabb.overlap(node.aabb):
			return
		if node.isLeaf():
			resultList.append(node.aabb)
		else:
			self._query(node.child1, aabb, resultList)
			self._query(node.child2, aabb, resultList)

	def __repr__(self):
		s = "AABBTree:\n"
		s += str(self.root.aabb)
		return s

if __name__ == '__main__':
	tree = AABBTree()
	tree.insert(AABB(Vector3(0,0,0), Vector3(0,0,0)))
	tree.insert(AABB(Vector3(1,1,1), Vector3(1,1,1)))
	tree.insert(AABB(Vector3(0.5,0.5,0.5), Vector3(0.5,0.5,0.5)))
	print(tree)
	print(tree.query(AABB(Vector3(0,0,0), Vector3(0,0,0))))

