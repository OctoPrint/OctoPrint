import wx
import sys
import math
import threading
import re

from wx.glcanvas import GLCanvas
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

class previewPanel(wx.Panel):
	def __init__(self, parent):
		wx.Panel.__init__(self, parent,-1)
		
		self.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DDKSHADOW))
		self.SetMinSize((400,300))

		self.glCanvas = GLCanvas(self, -1)
		wx.EVT_PAINT(self.glCanvas, self.OnPaint)
		wx.EVT_SIZE(self.glCanvas, self.OnSize)
		wx.EVT_ERASE_BACKGROUND(self.glCanvas, self.OnEraseBackground)
		wx.EVT_MOTION(self.glCanvas, self.OnMouseMotion)
		self.init = 0
		self.triangleMesh = None
		self.modelDisplayList = None
		self.pathList = None
		self.yaw = 30
		self.pitch = 60
		self.zoom = 150
		self.renderTransparent = False
		self.machineSize = Vector3(210, 210, 200)
		self.machineCenter = Vector3(105, 105, 0)
		
		tb = wx.ToolBar( self, -1 )
		self.ToolBar = tb
		tb.SetToolBitmapSize( ( 21, 21 ) )
		transparentButton = wx.Button(tb, -1, "T", size=(21,21))
		tb.AddControl(transparentButton)
		self.Bind(wx.EVT_BUTTON, self.OnConfigClick, transparentButton)
		tb.Realize()

		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(tb, 0, flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=1)
		sizer.Add(self.glCanvas, 1, flag=wx.EXPAND)
		self.SetSizer(sizer)

	
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
		self.moveModel()
		self.Refresh()
	
	def getCodeInt(self, str, id):
		m = re.search(id + '([^\s]+)', str)
		if m == None:
			return None
		try:
			return int(m.group(1))
		except:
			return None

	def getCodeFloat(self, str, id):
		m = re.search(id + '([^\s]+)', str)
		if m == None:
			return None
		try:
			return float(m.group(1))
		except:
			return None
	
	def DoGCodeLoad(self):
		f = open(self.gcodeFilename, 'r')
		pos = Vector3()
		posOffset = Vector3()
		currentE = 0
		pathList = []
		currentPath = {'type': 'move', 'list': [pos.copy()]}
		scale = 1.0
		posAbs = True
		for line in f:
			G = self.getCodeInt(line, 'G')
			if G is not None:
				if G == 0 or G == 1:	#Move
					x = self.getCodeFloat(line, 'X')
					y = self.getCodeFloat(line, 'Y')
					z = self.getCodeFloat(line, 'Z')
					e = self.getCodeFloat(line, 'E')
					if x is not None:
						if posAbs:
							pos.x = x * scale
						else:
							pos.x += x * scale
					if y is not None:
						if posAbs:
							pos.y = y * scale
						else:
							pos.y += y * scale
					if z is not None:
						if posAbs:
							pos.z = z * scale
						else:
							pos.z += z * scale
					newPoint = pos.copy()
					type = 'move'
					if e is not None:
						if e > currentE:
							type = 'extrude'
						if e < currentE:
							type = 'retract'
						currentE = e
					if currentPath['type'] != type:
						pathList.append(currentPath)
						currentPath = {'type': type, 'list': [currentPath['list'][-1]]}
					currentPath['list'].append(newPoint)
				elif G == 20:	#Units are inches
					scale = 25.4
				elif G == 21:	#Units are mm
					scale = 1.0
				elif G == 28:	#Home
					x = self.getCodeFloat(line, 'X')
					y = self.getCodeFloat(line, 'Y')
					z = self.getCodeFloat(line, 'Z')
					if x is None and y is None and z is None:
						pos = Vector3()
					else:
						if x is not None:
							pos.x = 0.0
						if y is not None:
							pos.y = 0.0
						if z is not None:
							pos.z = 0.0
				elif G == 90:	#Absolute position
					posAbs = True
				elif G == 91:	#Relative position
					posAbs = False
				elif G == 92:
					x = self.getCodeFloat(line, 'X')
					y = self.getCodeFloat(line, 'Y')
					z = self.getCodeFloat(line, 'Z')
					e = self.getCodeFloat(line, 'E')
					if e is not None:
						currentE = e
					if x is not None:
						posOffset.x = pos.x + x
					if y is not None:
						posOffset.y = pos.y + y
					if z is not None:
						posOffset.z = pos.z + z
				else:
					print "Unknown G code:" + str(G)
		self.pathList = pathList
		self.triangleMesh = None
		self.Refresh()
	
	def OnConfigClick(self, e):
		self.renderTransparent = not self.renderTransparent
		self.Refresh()
	
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
	
	def OnMouseMotion(self,e):
		if e.Dragging() and e.LeftIsDown():
			self.yaw += e.GetX() - self.oldX
			self.pitch -= e.GetY() - self.oldY
			if self.pitch > 170:
				self.pitch = 170
			if self.pitch < 10:
				self.pitch = 10
			self.Refresh()
		if e.Dragging() and e.RightIsDown():
			self.zoom += e.GetY() - self.oldY
			self.Refresh()
		self.oldX = e.GetX()
		self.oldY = e.GetY()
	
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
		self.glCanvas.SetCurrent()
		self.InitGL()
		self.OnDraw()
		return

	def OnDraw(self):
		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
		
		glTranslate(-self.machineCenter.x, -self.machineCenter.y, 0)
		
		glColor3f(1,1,1)
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

		if self.pathList != None:
			for path in self.pathList:
				if path['type'] == 'move':
					glColor3f(0,0,1)
				if path['type'] == 'extrude':
					glColor3f(1,0,0)
				if path['type'] == 'retract':
					glColor3f(0,1,0)
				glBegin(GL_LINE_STRIP)
				for v in path['list']:
					glVertex3f(v.x, v.y, v.z)
				glEnd()
		
		if self.triangleMesh != None:
			if self.modelDisplayList == None:
				self.modelDisplayList = glGenLists(1);
			if self.modelDirty:
				self.modelDirty = False
				glNewList(self.modelDisplayList, GL_COMPILE)
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
		
		self.glCanvas.SwapBuffers()
		return

	def InitGL(self):
		# set viewing projection
		glMatrixMode(GL_MODELVIEW)
		glLoadIdentity()
		size = self.glCanvas.GetSize()
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
		gluPerspective(90.0, float(self.GetSize().GetWidth()) / float(self.GetSize().GetHeight()), 1.0, 1000.0)

		glMatrixMode(GL_MODELVIEW)
		glLoadIdentity()
		glTranslate(0,0,-self.zoom)
		glRotate(-self.pitch, 1,0,0)
		glRotate(self.yaw, 0,0,1)
		if self.triangleMesh != None:
			glTranslate(0,0,-self.triangleMesh.getCarveCornerMaximum().z / 2)
		return
