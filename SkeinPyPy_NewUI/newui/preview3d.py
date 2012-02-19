from wxPython.glcanvas import wxGLCanvas
from wxPython.wx import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from OpenGL.GL import *
import sys,math

from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
from fabmetheus_utilities.vector3 import Vector3

class myGLCanvas(wxGLCanvas):
	def __init__(self, parent):
		wxGLCanvas.__init__(self, parent,-1)
		EVT_PAINT(self, self.OnPaint)
		EVT_SIZE(self, self.OnSize)
		EVT_ERASE_BACKGROUND(self, self.OnEraseBackground)
		EVT_MOTION(self, self.OnMouseMotion)
		self.init = 0
		self.triangleMesh = None
		self.yaw = 0
		self.pitch = 80
		self.zoom = 150
		self.machineSize = Vector3(210, 210, 200)
		self.machineCenter = Vector3(100, 100, 0)
		return
	
	def loadFile(self, filename):
		self.triangleMesh = fabmetheus_interpret.getCarving(filename)
		minZ = self.triangleMesh.getMinimumZ()
		min = self.triangleMesh.getCarveCornerMinimum()
		max = self.triangleMesh.getCarveCornerMaximum()
		
		for v in self.triangleMesh.vertexes:
			v.z -= minZ
			v.x -= min.x + (max.x - min.x) / 2
			v.y -= min.y + (max.y - min.y) / 2
			v.x += self.machineCenter.x
			v.y += self.machineCenter.y
	
	def OnMouseMotion(self,e):
		if e.Dragging() and e.LeftIsDown():
			self.yaw += e.GetX() - self.oldX
			self.pitch += e.GetY() - self.oldY
			if self.pitch > 170:
				self.pitch = 170
			if self.pitch < 10:
				self.pitch = 10
		if e.Dragging() and e.RightIsDown():
			self.zoom += e.GetY() - self.oldY
		self.oldX = e.GetX()
		self.oldY = e.GetY()
		self.Refresh()
	
	def OnEraseBackground(self,event):
		pass
	
	def OnSize(self,event):
		self.Refresh()
		return

	def OnPaint(self,event):
		dc = wxPaintDC(self)
		self.SetCurrent()
		self.InitGL()
		self.OnDraw()
		return

	def OnDraw(self):
		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
		
		glTranslate(-self.machineCenter.x, -self.machineCenter.y, 0)
		
		if self.triangleMesh != None:
			glBegin(GL_TRIANGLES)
			for face in self.triangleMesh.faces:
				v1 = self.triangleMesh.vertexes[face.vertexIndexes[0]]
				v2 = self.triangleMesh.vertexes[face.vertexIndexes[1]]
				v3 = self.triangleMesh.vertexes[face.vertexIndexes[2]]
				normal = (v2 - v1).cross(v3 - v1)
				normal.normalize()
				glNormal3f(normal.x, normal.y, normal.z)
				glVertex3f(v1.x, v1.y, v1.z)
				glVertex3f(v2.x, v2.y, v2.z)
				glVertex3f(v3.x, v3.y, v3.z)
			glEnd()
		
		glLineWidth(4)
		glDisable(GL_LIGHTING)
		glBegin(GL_LINE_LOOP)
		glVertex3f(0, 0, 0)
		glVertex3f(self.machineSize.x, 0, 0)
		glVertex3f(self.machineSize.x, self.machineSize.y, 0)
		glVertex3f(0, self.machineSize.y, 0)
		glEnd()
		glLineWidth(2)
		glBegin(GL_LINES)
		for i in xrange(0, self.machineSize.x, 10):
			glVertex3f(i, 0, 0)
			glVertex3f(i, self.machineSize.y, 0)
		for i in xrange(0, self.machineSize.y, 10):
			glVertex3f(0, i, 0)
			glVertex3f(self.machineSize.x, i, 0)
		glEnd()
		glLineWidth(1)
		glBegin(GL_LINE_LOOP)
		glVertex3f(0, 0, self.machineSize.z)
		glVertex3f(self.machineSize.x, 0, self.machineSize.z)
		glVertex3f(self.machineSize.x, self.machineSize.y, self.machineSize.z)
		glVertex3f(0, self.machineSize.y, self.machineSize.z)
		glEnd()
		glBegin(GL_LINES)
		glVertex3f(0, 0, 0)
		glVertex3f(0, 0, self.machineSize.z)
		glVertex3f(self.machineSize.x, 0, 0)
		glVertex3f(self.machineSize.x, 0, self.machineSize.z)
		glVertex3f(self.machineSize.x, self.machineSize.y, 0)
		glVertex3f(self.machineSize.x, self.machineSize.y, self.machineSize.z)
		glVertex3f(0, self.machineSize.y, 0)
		glVertex3f(0, self.machineSize.y, self.machineSize.z)
		glEnd()
		self.SwapBuffers()
		return

	def InitGL(self):
		# set viewing projection
		glMatrixMode(GL_MODELVIEW)
		glLoadIdentity()
		glViewport(0,0, self.GetSize().GetWidth(), self.GetSize().GetHeight())
		
		glLightfv(GL_LIGHT0, GL_DIFFUSE,  [1.0, 0.8, 0.6, 1.0])
		glLightfv(GL_LIGHT0, GL_POSITION, [1.0, 1.0, 1.0, 0.0])
		glLightfv(GL_LIGHT0, GL_AMBIENT,  [0.2, 0.2, 0.2, 0.0])

		glEnable(GL_LIGHTING)
		glEnable(GL_LIGHT0)
		glEnable(GL_DEPTH_TEST)
		glClearColor(0.0, 0.0, 0.0, 1.0)
		glClearDepth(1.0)

		glMatrixMode(GL_PROJECTION)
		glLoadIdentity()
		gluPerspective(90.0, float(self.GetSize().GetWidth()) / float(self.GetSize().GetHeight()), 1.0, 1000.0)

		glMatrixMode(GL_MODELVIEW)
		glLoadIdentity()
		glTranslate(0,0,-self.zoom)
		glRotate(-self.pitch, 1,0,0)
		glRotate(self.yaw, 0,0,1)
		#glRotate(90, 1,0,0)
		
		return
