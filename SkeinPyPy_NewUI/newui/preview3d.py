import sys
import math
import threading
import re

from wx.glcanvas import GLCanvas
import wx
try:
	from OpenGL.GLUT import *
	from OpenGL.GLU import *
	from OpenGL.GL import *
	hasOpenGLlibs = True
except:
	print "Failed to find PyOpenGL: http://pyopengl.sourceforge.net/"
	hasOpenGLlibs = False

from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
from fabmetheus_utilities.vector3 import Vector3
from newui import gcodeInterpreter

class previewPanel(wx.Panel):
	def __init__(self, parent):
		wx.Panel.__init__(self, parent,-1)
		
		self.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DDKSHADOW))
		self.SetMinSize((400,300))

		self.glCanvas = PreviewGLCanvas(self)
		self.init = 0
		self.triangleMesh = None
		self.pathList = None
		self.machineSize = Vector3(210, 210, 200)
		self.machineCenter = Vector3(0, 0, 0)
		
		tb = wx.ToolBar( self, -1 )
		self.ToolBar = tb
		tb.SetToolBitmapSize( ( 21, 21 ) )
		transparentButton = wx.Button(tb, -1, "T", size=(21,21))
		tb.AddControl(transparentButton)
		self.Bind(wx.EVT_BUTTON, self.OnConfigClick, transparentButton)

		button = wx.Button(tb, -1, "3D", size=(21*2,21))
		tb.AddControl(button)
		self.Bind(wx.EVT_BUTTON, self.On3DClick, button)
		
		button = wx.Button(tb, -1, "Top", size=(21*2,21))
		tb.AddControl(button)
		self.Bind(wx.EVT_BUTTON, self.OnTopClick, button)
		
		self.layerSpin = wx.SpinCtrl(tb, -1, '', size=(21*4,21), style=wx.SP_ARROW_KEYS)
		tb.AddControl(self.layerSpin)
		self.layerSpin.Show(False)

		tb.Realize()

		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(tb, 0, flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=1)
		sizer.Add(self.glCanvas, 1, flag=wx.EXPAND)
		self.SetSizer(sizer)

	def On3DClick(self, e):
		self.glCanvas.yaw = 30
		self.glCanvas.pitch = 60
		self.glCanvas.zoom = 150
		self.glCanvas.view3D = True
		self.glCanvas.Refresh()

	def OnTopClick(self, e):
		self.glCanvas.view3D = False
		self.glCanvas.zoom = 150
		self.glCanvas.offsetX = 0
		self.glCanvas.offsetY = 0
		self.glCanvas.Refresh()

	def updateCenterX(self, x):
		self.machineCenter.x = x
		self.moveModel()
		self.glCanvas.Refresh()

	def updateCenterY(self, y):
		self.machineCenter.y = y
		self.moveModel()
		self.glCanvas.Refresh()
	
	def loadModelFile(self, filename):
		self.modelFilename = filename
		#Do the STL file loading in a background thread so we don't block the UI.
		thread = threading.Thread(target=self.DoModelLoad)
		thread.start()

	def loadGCodeFile(self, filename):
		self.gcodeFilename = filename
		#Do the STL file loading in a background thread so we don't block the UI.
		thread = threading.Thread(target=self.DoGCodeLoad)
		thread.start()
	
	def DoModelLoad(self):
		self.modelDirty = False
		self.triangleMesh = fabmetheus_interpret.getCarving(self.modelFilename)
		self.pathList = None
		self.moveModel()
		wx.CallAfter(self.glCanvas.Refresh)
	
	def DoGCodeLoad(self):
		gcode = gcodeInterpreter.gcode(self.gcodeFilename)
		self.modelDirty = False
		self.pathList = gcode.pathList
		self.triangleMesh = None
		self.modelDirty = True
		wx.CallAfter(self.glCanvas.Refresh)
	
	def OnConfigClick(self, e):
		self.glCanvas.renderTransparent = not self.glCanvas.renderTransparent
		self.glCanvas.Refresh()
	
	def moveModel(self):
		if self.triangleMesh == None:
			return
		minZ = self.triangleMesh.getMinimumZ()
		min = self.triangleMesh.getCarveCornerMinimum()
		max = self.triangleMesh.getCarveCornerMaximum()
		for v in self.triangleMesh.vertexes:
			v.z -= minZ
			v.x -= min.x + (max.x - min.x) / 2
			v.y -= min.y + (max.y - min.y) / 2
			v.x += self.machineCenter.x
			v.y += self.machineCenter.y
		self.triangleMesh.getMinimumZ()
		self.modelDirty = True

class PreviewGLCanvas(GLCanvas):
	def __init__(self, parent):
		GLCanvas.__init__(self, parent)
		self.parent = parent
		wx.EVT_PAINT(self, self.OnPaint)
		wx.EVT_SIZE(self, self.OnSize)
		wx.EVT_ERASE_BACKGROUND(self, self.OnEraseBackground)
		wx.EVT_MOTION(self, self.OnMouseMotion)
		wx.EVT_MOUSEWHEEL(self, self.OnMouseWheel)
		self.yaw = 30
		self.pitch = 60
		self.zoom = 150
		self.offsetX = 0
		self.offsetY = 0
		self.view3D = True
		self.renderTransparent = False
		self.modelDisplayList = None

	def OnMouseMotion(self,e):
		if e.Dragging() and e.LeftIsDown():
			if self.view3D:
				self.yaw += e.GetX() - self.oldX
				self.pitch -= e.GetY() - self.oldY
				if self.pitch > 170:
					self.pitch = 170
				if self.pitch < 10:
					self.pitch = 10
			else:
				self.offsetX += float(e.GetX() - self.oldX) * self.zoom / self.GetSize().GetHeight() * 2
				self.offsetY -= float(e.GetY() - self.oldY) * self.zoom / self.GetSize().GetHeight() * 2
			self.Refresh()
		if e.Dragging() and e.RightIsDown():
			self.zoom += e.GetY() - self.oldY
			if self.zoom < 1:
				self.zoom = 1
			self.Refresh()
		self.oldX = e.GetX()
		self.oldY = e.GetY()
	
	def OnMouseWheel(self,e):
		self.zoom *= 1 - float(e.GetWheelRotation() / e.GetWheelDelta()) / 10
		if self.zoom < 1:
			self.zoom = 1
		self.Refresh()
	
	def OnEraseBackground(self,event):
		pass
	
	def OnSize(self,event):
		self.Refresh()
		return

	def OnPaint(self,event):
		dc = wx.PaintDC(self)
		if not hasOpenGLlibs:
			dc.Clear()
			dc.DrawText("No PyOpenGL installation found.\nNo preview window available.", 10, 10)
			return
		self.SetCurrent()
		self.InitGL()
		self.OnDraw()
		return

	def OnDraw(self):
		machineSize = self.parent.machineSize
		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
		
		glTranslate(-self.parent.machineCenter.x, -self.parent.machineCenter.y, 0)
		
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
		for i in xrange(0, machineSize.x, 10):
			glVertex3f(i, 0, 0)
			glVertex3f(i, machineSize.y, 0)
		for i in xrange(0, machineSize.y, 10):
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

		if self.parent.pathList != None:
			if self.modelDisplayList == None:
				self.modelDisplayList = glGenLists(1);
			if self.parent.modelDirty:
				self.parent.modelDirty = False
				glNewList(self.modelDisplayList, GL_COMPILE)
				for path in self.parent.pathList:
					if path['type'] == 'move':
						glColor3f(0,0,1)
					if path['type'] == 'extrude':
						if path['pathType'] == 'FILL':
							glColor3f(0.5,0.5,0)
						elif path['pathType'] == 'WALL-INNER':
							glColor3f(0,1,0)
						else:
							glColor3f(1,0,0)
					if path['type'] == 'retract':
						glColor3f(0,1,1)
					glBegin(GL_LINE_STRIP)
					for v in path['list']:
						glVertex3f(v.x, v.y, v.z)
					glEnd()
				glEndList()
			glCallList(self.modelDisplayList)
		
		if self.parent.triangleMesh != None:
			if self.modelDisplayList == None:
				self.modelDisplayList = glGenLists(1);
			if self.parent.modelDirty:
				self.parent.modelDirty = False
				glNewList(self.modelDisplayList, GL_COMPILE)
				glBegin(GL_TRIANGLES)
				for face in self.parent.triangleMesh.faces:
					v1 = self.parent.triangleMesh.vertexes[face.vertexIndexes[0]]
					v2 = self.parent.triangleMesh.vertexes[face.vertexIndexes[1]]
					v3 = self.parent.triangleMesh.vertexes[face.vertexIndexes[2]]
					if not hasattr(face, 'normal'):
						face.normal = (v2 - v1).cross(v3 - v1)
						face.normal.normalize()
					glNormal3f(face.normal.x, face.normal.y, face.normal.z)
					glVertex3f(v1.x, v1.y, v1.z)
					glVertex3f(v2.x, v2.y, v2.z)
					glVertex3f(v3.x, v3.y, v3.z)
				glEnd()
				glEndList()
			if self.renderTransparent:
				#If we want transparent, then first render a solid black model to remove the printer size lines.
				glDisable(GL_BLEND)
				glDisable(GL_LIGHTING)
				glColor3f(0,0,0)
				glCallList(self.modelDisplayList)
				glColor3f(1,1,1)
				#After the black model is rendered, render the model again but now with lighting and no depth testing.
				glDisable(GL_DEPTH_TEST)
				glEnable(GL_LIGHTING)
				glEnable(GL_BLEND)
				glBlendFunc(GL_ONE, GL_ONE)
				glEnable(GL_LIGHTING)
				glCallList(self.modelDisplayList)
			else:
				glEnable(GL_LIGHTING)
				glCallList(self.modelDisplayList)
		
		self.SwapBuffers()
		return

	def InitGL(self):
		# set viewing projection
		glMatrixMode(GL_MODELVIEW)
		glLoadIdentity()
		size = self.GetSize()
		glViewport(0,0, size.GetWidth(), size.GetHeight())
		
		if self.renderTransparent:
			glLightfv(GL_LIGHT0, GL_DIFFUSE,  [0.5, 0.4, 0.3, 1.0])
			glLightfv(GL_LIGHT0, GL_AMBIENT,  [0.1, 0.1, 0.1, 0.0])
		else:
			glLightfv(GL_LIGHT0, GL_DIFFUSE,  [1.0, 0.8, 0.6, 1.0])
			glLightfv(GL_LIGHT0, GL_AMBIENT,  [0.2, 0.2, 0.2, 0.0])
		glLightfv(GL_LIGHT0, GL_POSITION, [1.0, 1.0, 1.0, 0.0])

		glEnable(GL_LIGHTING)
		glEnable(GL_LIGHT0)
		glEnable(GL_DEPTH_TEST)
		glDisable(GL_BLEND)

		glClearColor(0.0, 0.0, 0.0, 1.0)
		glClearDepth(1.0)

		glMatrixMode(GL_PROJECTION)
		glLoadIdentity()
		aspect = float(self.GetSize().GetWidth()) / float(self.GetSize().GetHeight())
		if self.view3D:
			gluPerspective(90.0, aspect, 1.0, 1000.0)
		else:
			glOrtho(-self.zoom * aspect, self.zoom * aspect, -self.zoom, self.zoom, -1000.0, 1000.0)

		glMatrixMode(GL_MODELVIEW)
		glLoadIdentity()
		if self.view3D:
			glTranslate(0,0,-self.zoom)
			glRotate(-self.pitch, 1,0,0)
			glRotate(self.yaw, 0,0,1)
			if self.parent.triangleMesh != None:
				glTranslate(0,0,-self.parent.triangleMesh.getCarveCornerMaximum().z / 2)
		else:
			glTranslate(self.offsetX, self.offsetY, 0)

