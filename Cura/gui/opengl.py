
try:
	import OpenGL
	OpenGL.ERROR_CHECKING = False
	from OpenGL.GLU import *
	from OpenGL.GL import *
	hasOpenGLlibs = True
except:
	print "Failed to find PyOpenGL: http://pyopengl.sourceforge.net/"
	hasOpenGLlibs = False

def InitGL(window, view3D, zoom):
	# set viewing projection
	glMatrixMode(GL_MODELVIEW)
	glLoadIdentity()
	size = window.GetSize()
	glViewport(0,0, size.GetWidth(), size.GetHeight())
	
	glLightfv(GL_LIGHT0, GL_POSITION, [1.0, 1.0, 1.0, 0.0])

	glEnable(GL_LIGHTING)
	glEnable(GL_LIGHT0)
	glEnable(GL_DEPTH_TEST)
	glEnable(GL_CULL_FACE)
	glDisable(GL_BLEND)

	glClearColor(0.0, 0.0, 0.0, 1.0)
	glClearStencil(0)
	glClearDepth(1.0)

	glMatrixMode(GL_PROJECTION)
	glLoadIdentity()
	aspect = float(size.GetWidth()) / float(size.GetHeight())
	if view3D:
		gluPerspective(90.0, aspect, 1.0, 1000.0)
	else:
		glOrtho(-aspect, aspect, -1, 1, -1000.0, 1000.0)

	glMatrixMode(GL_MODELVIEW)
	glLoadIdentity()
	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT)

def DrawMachine(machineSize):
	glColor3f(1,1,1)
	glLineWidth(4)
	glDisable(GL_LIGHTING)
	glBegin(GL_LINE_LOOP)
	glVertex3f(0, 0, 0)
	glVertex3f(machineSize.x, 0, 0)
	glVertex3f(machineSize.x, machineSize.y, 0)
	glVertex3f(0, machineSize.y, 0)
	glEnd()
	glLineWidth(2)
	glBegin(GL_LINES)
	for i in xrange(0, int(machineSize.x), 10):
		glVertex3f(i, 0, 0)
		glVertex3f(i, machineSize.y, 0)
	for i in xrange(0, int(machineSize.y), 10):
		glVertex3f(0, i, 0)
		glVertex3f(machineSize.x, i, 0)
	glEnd()
	glLineWidth(1)
	glBegin(GL_LINE_LOOP)
	glVertex3f(0, 0, machineSize.z)
	glVertex3f(machineSize.x, 0, machineSize.z)
	glVertex3f(machineSize.x, machineSize.y, machineSize.z)
	glVertex3f(0, machineSize.y, machineSize.z)
	glEnd()
	glBegin(GL_LINES)
	glVertex3f(0, 0, 0)
	glVertex3f(0, 0, machineSize.z)
	glVertex3f(machineSize.x, 0, 0)
	glVertex3f(machineSize.x, 0, machineSize.z)
	glVertex3f(machineSize.x, machineSize.y, 0)
	glVertex3f(machineSize.x, machineSize.y, machineSize.z)
	glVertex3f(0, machineSize.y, 0)
	glVertex3f(0, machineSize.y, machineSize.z)
	glEnd()

def DrawSTL(mesh):
	for face in mesh.faces:
		glBegin(GL_TRIANGLES)
		v1 = face.v[0]
		v2 = face.v[1]
		v3 = face.v[2]
		glNormal3f(face.normal.x, face.normal.y, face.normal.z)
		glVertex3f(v1.x, v1.y, v1.z)
		glVertex3f(v2.x, v2.y, v2.z)
		glVertex3f(v3.x, v3.y, v3.z)
		glNormal3f(-face.normal.x, -face.normal.y, -face.normal.z)
		glVertex3f(v1.x, v1.y, v1.z)
		glVertex3f(v3.x, v3.y, v3.z)
		glVertex3f(v2.x, v2.y, v2.z)
		glEnd()
