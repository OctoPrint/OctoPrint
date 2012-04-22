
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
		gluPerspective(45.0, aspect, 1.0, 1000.0)
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

	glPushMatrix()
	glTranslate(-5,-5,0)
	glLineWidth(2)
	glColor3f(0.5,0,0)
	glBegin(GL_LINES)
	glVertex3f(0,0,0)
	glVertex3f(20,0,0)
	glEnd()
	glColor3f(0,0.5,0)
	glBegin(GL_LINES)
	glVertex3f(0,0,0)
	glVertex3f(0,20,0)
	glEnd()
	glColor3f(0,0,0.5)
	glBegin(GL_LINES)
	glVertex3f(0,0,0)
	glVertex3f(0,0,20)
	glEnd()

	glDisable(GL_DEPTH_TEST)
	#X
	glColor3f(1,0,0)
	glPushMatrix()
	glTranslate(23,0,0)
	noZ = ResetMatrixRotationAndScale()
	glBegin(GL_LINES)
	glVertex3f(-0.8,1,0)
	glVertex3f(0.8,-1,0)
	glVertex3f(0.8,1,0)
	glVertex3f(-0.8,-1,0)
	glEnd()
	glPopMatrix()

	#Y
	glColor3f(0,1,0)
	glPushMatrix()
	glTranslate(0,23,0)
	ResetMatrixRotationAndScale()
	glBegin(GL_LINES)
	glVertex3f(-0.8, 1,0)
	glVertex3f( 0.0, 0,0)
	glVertex3f( 0.8, 1,0)
	glVertex3f(-0.8,-1,0)
	glEnd()
	glPopMatrix()

	#Z
	if not noZ:
		glColor3f(0,0,1)
		glPushMatrix()
		glTranslate(0,0,23)
		ResetMatrixRotationAndScale()
		glBegin(GL_LINES)
		glVertex3f(-0.8, 1,0)
		glVertex3f( 0.8, 1,0)
		glVertex3f( 0.8, 1,0)
		glVertex3f(-0.8,-1,0)
		glVertex3f(-0.8,-1,0)
		glVertex3f( 0.8,-1,0)
		glEnd()
		glPopMatrix()

	glPopMatrix()
	glEnable(GL_DEPTH_TEST)
	
def ResetMatrixRotationAndScale():
	matrix = glGetFloatv(GL_MODELVIEW_MATRIX)

	for x in xrange(0, 4):
		s = ""
		for y in xrange(0, 4):
			s = s + " %8.8f" % (matrix[x][y])
		print s

	noZ = False
	scale2D = matrix[0][0]
	matrix[0][0] = 1.0
	matrix[1][0] = 0.0
	matrix[2][0] = 0.0
	matrix[0][1] = 0.0
	matrix[1][1] = 1.0
	matrix[2][1] = 0.0
	matrix[0][2] = 0.0
	matrix[1][2] = 0.0
	matrix[2][2] = 1.0
	
	if matrix[3][2] != 0.0:
		matrix[3][0] /= -matrix[3][2] / 100
		matrix[3][1] /= -matrix[3][2] / 100
		matrix[3][2] = -100
	else:
		matrix[0][0] = scale2D
		matrix[1][1] = scale2D
		matrix[2][2] = scale2D
		matrix[3][2] = -100
		noZ = True
	
	glLoadMatrixf(matrix)
	return noZ

def DrawBox(vMin, vMax):
	glBegin(GL_LINE_LOOP)
	glVertex3f(vMin.x, vMin.y, vMin.z)
	glVertex3f(vMax.x, vMin.y, vMin.z)
	glVertex3f(vMax.x, vMax.y, vMin.z)
	glVertex3f(vMin.x, vMax.y, vMin.z)
	glEnd()

	glBegin(GL_LINE_LOOP)
	glVertex3f(vMin.x, vMin.y, vMax.z)
	glVertex3f(vMax.x, vMin.y, vMax.z)
	glVertex3f(vMax.x, vMax.y, vMax.z)
	glVertex3f(vMin.x, vMax.y, vMax.z)
	glEnd()
	glBegin(GL_LINES)
	glVertex3f(vMin.x, vMin.y, vMin.z)
	glVertex3f(vMin.x, vMin.y, vMax.z)
	glVertex3f(vMax.x, vMin.y, vMin.z)
	glVertex3f(vMax.x, vMin.y, vMax.z)
	glVertex3f(vMax.x, vMax.y, vMin.z)
	glVertex3f(vMax.x, vMax.y, vMax.z)
	glVertex3f(vMin.x, vMax.y, vMin.z)
	glVertex3f(vMin.x, vMax.y, vMax.z)
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
