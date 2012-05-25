from __future__ import absolute_import
import __init__

import sys, math, re, os, struct, time

from util import util3d
from util import mesh

class stlModel(mesh.mesh):
	def __init__(self):
		super(stlModel, self).__init__()

	def load(self, filename):
		f = open(filename, "rb")
		if f.read(6).lower() == "solid ":
			self._loadAscii(f)
			if len(self.faces) < 1:
				f.seek(6, os.SEEK_SET)
				self._loadBinary(f)
		else:
			self._loadBinary(f)
		f.close()
		
		self._postProcessAfterLoad()
		return self
	
	def _loadAscii(self, f):
		cnt = 0
		for line in f:
			if 'vertex' in line:
				data = line.split()
				if cnt == 0:
					v0 = util3d.Vector3(float(data[1]), float(data[2]), float(data[3]))
					cnt = 1
				elif cnt == 1:
					v1 = util3d.Vector3(float(data[1]), float(data[2]), float(data[3]))
					cnt = 2
				elif cnt == 2:
					v2 = util3d.Vector3(float(data[1]), float(data[2]), float(data[3]))
					self.addFace(v0, v1, v2)
					cnt = 0

	def _loadBinary(self, f):
		#Skip the header
		f.read(80-6)
		faceCount = struct.unpack('<I', f.read(4))[0]
		for idx in xrange(0, faceCount):
			data = struct.unpack("<ffffffffffffH", f.read(50))
			v0 = util3d.Vector3(data[3], data[4], data[5])
			v1 = util3d.Vector3(data[6], data[7], data[8])
			v2 = util3d.Vector3(data[9], data[10], data[11])
			self.addFace(v0, v1, v2)

def saveAsSTL(mesh, filename):
	f = open(filename, 'wb')
	#Write the STL binary header. This can contain any info, except for "SOLID" at the start.
	f.write(("CURA BINARY STL EXPORT. " + time.strftime('%a %d %b %Y %H:%M:%S')).ljust(80, '\000'))
	#Next follow 4 binary bytes containing the amount of faces, and then the face information.
	f.write(struct.pack("<I", len(mesh.faces)))
	for face in mesh.faces:
		v1 = face.v[0]
		v2 = face.v[1]
		v3 = face.v[2]
		normal = (v2 - v1).cross(v3 - v1)
		normal.normalize()
		f.write(struct.pack("<fff", normal.x, normal.y, normal.z))
		f.write(struct.pack("<fff", v1.x, v1.y, v1.z))
		f.write(struct.pack("<fff", v2.x, v2.y, v2.z))
		f.write(struct.pack("<fff", v3.x, v3.y, v3.z))
		f.write(struct.pack("<H", 0))
	f.close()

if __name__ == '__main__':
	for filename in sys.argv[1:]:
		m = stlModel().load(filename)
		print "Loaded %d faces" % (len(m.faces))
		parts = m.splitToParts()
		for p in parts:
			saveAsSTL(p, "export_%i.stl" % parts.index(p))

