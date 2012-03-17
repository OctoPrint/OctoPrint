import sys
import math
import threading
import re
import time

from wx import glcanvas
import wx
try:
	from OpenGL.GLU import *
	from OpenGL.GL import *
	hasOpenGLlibs = True
except:
	print "Failed to find PyOpenGL: http://pyopengl.sourceforge.net/"
	hasOpenGLlibs = False

from newui import profile
from newui import gcodeInterpreter
from newui import util3d

from fabmetheus_utilities import settings
from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
from fabmetheus_utilities.vector3 import Vector3

class previewPanel(wx.Panel):
	def __init__(self, parent):
		wx.Panel.__init__(self, parent,-1)
		
		self.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DDKSHADOW))
		self.SetMinSize((400,300))

		self.glCanvas = PreviewGLCanvas(self)
		self.init = 0
		self.triangleMesh = None
		self.gcode = None
		self.machineSize = Vector3(float(profile.getPreference('machine_width')), float(profile.getPreference('machine_depth')), float(profile.getPreference('machine_height')))
		self.machineCenter = Vector3(0, 0, 0)
		
		self.toolbar = wx.ToolBar( self, -1 )
		self.toolbar.SetToolBitmapSize( ( 21, 21 ) )

		button = wx.Button(self.toolbar, -1, "3D", size=(21*2,21))
		self.toolbar.AddControl(button)
		self.Bind(wx.EVT_BUTTON, self.On3DClick, button)
		
		button = wx.Button(self.toolbar, -1, "Top", size=(21*2,21))
		self.toolbar.AddControl(button)
		self.Bind(wx.EVT_BUTTON, self.OnTopClick, button)

		self.transparentButton = wx.Button(self.toolbar, -1, "T", size=(21,21))
		self.toolbar.AddControl(self.transparentButton)
		self.Bind(wx.EVT_BUTTON, self.OnTransparentClick, self.transparentButton)
		self.XRayButton = wx.Button(self.toolbar, -1, "X-RAY", size=(21*2,21))
		self.toolbar.AddControl(self.XRayButton)
		self.Bind(wx.EVT_BUTTON, self.OnXRayClick, self.XRayButton)
		
		self.layerSpin = wx.SpinCtrl(self.toolbar, -1, '', size=(21*4,21), style=wx.SP_ARROW_KEYS)
		self.toolbar.AddControl(self.layerSpin)
		self.Bind(wx.EVT_SPINCTRL, self.OnLayerNrChange, self.layerSpin)
		
		self.updateToolbar()
		
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.toolbar, 0, flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=1)
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
		self.glCanvas.zoom = 100
		self.glCanvas.offsetX = 0
		self.glCanvas.offsetY = 0
		self.glCanvas.Refresh()

	def OnLayerNrChange(self, e):
		self.modelDirty = True
		self.glCanvas.Refresh()

	def updateCenterX(self, x):
		self.machineCenter.x = x
		self.moveModel()
		self.glCanvas.Refresh()

	def updateCenterY(self, y):
		self.machineCenter.y = y
		self.moveModel()
		self.glCanvas.Refresh()
	
	def updateWallLineWidth(self, setting):
		#TODO: this shouldn't be needed, you can calculate the line width from the E values combined with the steps_per_E and the filament diameter (reverse volumatric)
		self.glCanvas.lineWidth = settings.calculateEdgeWidth(setting)
	
	def updateInfillLineWidth(self, setting):
		#TODO: this shouldn't be needed, you can calculate the line width from the E values combined with the steps_per_E and the filament diameter (reverse volumatric)
		self.glCanvas.infillLineWidth = profile.getProfileSetting('nozzle_size')
	
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
		triangleMesh = fabmetheus_interpret.getCarving(self.modelFilename)
		triangleMesh.origonalVertexes = list(triangleMesh.vertexes)
		for i in xrange(0, len(triangleMesh.origonalVertexes)):
			triangleMesh.origonalVertexes[i] = triangleMesh.origonalVertexes[i].copy()
		triangleMesh.getMinimumZ()
		self.triangleMesh = triangleMesh
		self.gcode = None
		self.updateModelTransform()
		wx.CallAfter(self.updateToolbar)
		wx.CallAfter(self.glCanvas.Refresh)
	
	def DoGCodeLoad(self):
		gcode = gcodeInterpreter.gcode(self.gcodeFilename)
		self.modelDirty = False
		self.gcode = gcode
		self.triangleMesh = None
		self.modelDirty = True
		wx.CallAfter(self.updateToolbar)
		wx.CallAfter(self.glCanvas.Refresh)
	
	def updateToolbar(self):
		self.transparentButton.Show(self.triangleMesh != None)
		self.XRayButton.Show(self.triangleMesh != None)
		self.layerSpin.Show(self.gcode != None)
		if self.gcode != None:
			self.layerSpin.SetRange(1, self.gcode.layerCount)
		self.toolbar.Realize()
	
	def OnTransparentClick(self, e):
		self.glCanvas.renderTransparent = not self.glCanvas.renderTransparent
		if self.glCanvas.renderTransparent:
			self.glCanvas.renderXRay = False
		self.glCanvas.Refresh()
	
	def OnXRayClick(self, e):
		self.glCanvas.renderXRay = not self.glCanvas.renderXRay
		if self.glCanvas.renderXRay:
			self.glCanvas.renderTransparent = False
		self.glCanvas.Refresh()
	
	def updateModelTransform(self, f=0):
		if self.triangleMesh == None:
			return
		scale = 1.0
		rotate = 0.0
		try:
			scale = float(profile.getProfileSetting('model_scale'))
			rotate = float(profile.getProfileSetting('model_rotate_base')) / 180 * math.pi
		except:
			pass
		scaleX = scale
		scaleY = scale
		scaleZ = scale
		if profile.getProfileSetting('flip_x') == 'True':
			scaleX = -scaleX
		if profile.getProfileSetting('flip_y') == 'True':
			scaleY = -scaleY
		if profile.getProfileSetting('flip_z') == 'True':
			scaleZ = -scaleZ
		mat00 = math.cos(rotate) * scaleX
		mat01 =-math.sin(rotate) * scaleY
		mat10 = math.sin(rotate) * scaleX
		mat11 = math.cos(rotate) * scaleY
		
		for i in xrange(0, len(self.triangleMesh.origonalVertexes)):
			self.triangleMesh.vertexes[i].x = self.triangleMesh.origonalVertexes[i].x * mat00 + self.triangleMesh.origonalVertexes[i].y * mat01
			self.triangleMesh.vertexes[i].y = self.triangleMesh.origonalVertexes[i].x * mat10 + self.triangleMesh.origonalVertexes[i].y * mat11
			self.triangleMesh.vertexes[i].z = self.triangleMesh.origonalVertexes[i].z * scaleZ

		for face in self.triangleMesh.faces:
			v1 = self.triangleMesh.vertexes[face.vertexIndexes[0]]
			v2 = self.triangleMesh.vertexes[face.vertexIndexes[1]]
			v3 = self.triangleMesh.vertexes[face.vertexIndexes[2]]
			face.normal = (v2 - v1).cross(v3 - v1)
			face.normal.normalize()

		self.moveModel()
	
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
		self.glCanvas.Refresh()

class PreviewGLCanvas(glcanvas.GLCanvas):
	def __init__(self, parent):
		attribList = (glcanvas.WX_GL_RGBA, glcanvas.WX_GL_DOUBLEBUFFER, glcanvas.WX_GL_DEPTH_SIZE, 24, glcanvas.WX_GL_STENCIL_SIZE, 8)
		glcanvas.GLCanvas.__init__(self, parent, attribList = attribList)
		self.parent = parent
		self.context = glcanvas.GLContext(self)
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
		self.lineWidth = 0.4
		self.fillLineWidth = 0.4
		self.view3D = True
		self.renderTransparent = False
		self.renderXRay = False
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
		self.zoom *= 1.0 - float(e.GetWheelRotation() / e.GetWheelDelta()) / 10.0
		if self.zoom < 1.0:
			self.zoom = 1.0
		self.Refresh()
	
	def OnEraseBackground(self,event):
		pass
	
	def OnSize(self,event):
		self.Refresh()

	def OnPaint(self,event):
		dc = wx.PaintDC(self)
		if not hasOpenGLlibs:
			dc.Clear()
			dc.DrawText("No PyOpenGL installation found.\nNo preview window available.", 10, 10)
			return
		self.SetCurrent(self.context)
		self.InitGL()
		self.OnDraw()
		self.SwapBuffers()

	def OnDraw(self):
		machineSize = self.parent.machineSize
		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT)
		
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

		if self.parent.gcode != None:
			if self.modelDisplayList == None:
				self.modelDisplayList = glGenLists(1);
			if self.parent.modelDirty:
				self.parent.modelDirty = False
				glNewList(self.modelDisplayList, GL_COMPILE)
				for path in self.parent.gcode.pathList:
					c = 1.0
					if path['layerNr'] != self.parent.layerSpin.GetValue():
						if path['layerNr'] < self.parent.layerSpin.GetValue():
							c = 0.9 - (self.parent.layerSpin.GetValue() - path['layerNr']) * 0.1
							if c < 0.4:
								c = 0.4
						else:
							break
					if path['type'] == 'move':
						glColor3f(0,0,c)
					if path['type'] == 'extrude':
						if path['pathType'] == 'FILL':
							glColor3f(c/2,c/2,0)
						elif path['pathType'] == 'WALL-INNER':
							glColor3f(0,c,0)
						else:
							glColor3f(c,0,0)
					if path['type'] == 'retract':
						glColor3f(0,c,c)
					if c > 0.4 and path['type'] == 'extrude':
						if path['pathType'] == 'FILL':
							lineWidth = self.fillLineWidth / 2
						else:
							lineWidth = self.lineWidth / 2
						for i in xrange(0, len(path['list'])-1):
							v0 = path['list'][i]
							v1 = path['list'][i+1]
							normal = (v0 - v1).cross(util3d.Vector3(0,0,1))
							normal.normalize()
							v2 = v0 + normal * lineWidth
							v3 = v1 + normal * lineWidth
							v0 = v0 - normal * lineWidth
							v1 = v1 - normal * lineWidth

							glBegin(GL_QUADS)
							glVertex3f(v0.x, v0.y, v0.z - 0.001)
							glVertex3f(v1.x, v1.y, v1.z - 0.001)
							glVertex3f(v3.x, v3.y, v3.z - 0.001)
							glVertex3f(v2.x, v2.y, v2.z - 0.001)
							glEnd()
						for v in path['list']:
							glBegin(GL_TRIANGLE_FAN)
							glVertex3f(v.x, v.y, v.z - 0.001)
							for i in xrange(0, 16+1):
								glVertex3f(v.x + math.cos(math.pi*2/16*i) * lineWidth, v.y + math.sin(math.pi*2/16*i) * lineWidth, v.z - 0.001)
							glEnd()
					else:
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
				multiX = int(profile.getProfileSetting('model_multiply_x'))
				multiY = int(profile.getProfileSetting('model_multiply_y'))
				modelSize = self.parent.triangleMesh.getCarveCornerMaximum() - self.parent.triangleMesh.getCarveCornerMinimum()
				glNewList(self.modelDisplayList, GL_COMPILE)
				glPushMatrix()
				glTranslate(-(modelSize.x+self.lineWidth*15)*(multiX-1)/2,-(modelSize.y+self.lineWidth*15)*(multiY-1)/2, 0)
				for mx in xrange(0, multiX):
					for my in xrange(0, multiY):
						for face in self.parent.triangleMesh.faces:
							glPushMatrix()
							glTranslate((modelSize.x+self.lineWidth*15)*mx,(modelSize.y+self.lineWidth*15)*my, 0)
							glBegin(GL_TRIANGLES)
							v1 = self.parent.triangleMesh.vertexes[face.vertexIndexes[0]]
							v2 = self.parent.triangleMesh.vertexes[face.vertexIndexes[1]]
							v3 = self.parent.triangleMesh.vertexes[face.vertexIndexes[2]]
							glNormal3f(face.normal.x, face.normal.y, face.normal.z)
							glVertex3f(v1.x, v1.y, v1.z)
							glVertex3f(v2.x, v2.y, v2.z)
							glVertex3f(v3.x, v3.y, v3.z)
							glNormal3f(-face.normal.x, -face.normal.y, -face.normal.z)
							glVertex3f(v1.x, v1.y, v1.z)
							glVertex3f(v3.x, v3.y, v3.z)
							glVertex3f(v2.x, v2.y, v2.z)
							glEnd()
							glPopMatrix()
				glPopMatrix()
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
			elif self.renderXRay:
				glColorMask(GL_FALSE, GL_FALSE, GL_FALSE, GL_FALSE)
				glDisable(GL_DEPTH_TEST)
				glEnable(GL_STENCIL_TEST);
				glStencilFunc(GL_ALWAYS, 1, 1)
				glStencilOp(GL_INCR, GL_INCR, GL_INCR)
				glCallList(self.modelDisplayList)
				glStencilOp (GL_KEEP, GL_KEEP, GL_KEEP);
				
				glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)
				glStencilFunc(GL_EQUAL, 0, 1);
				glColor(0, 1, 0)
				glCallList(self.modelDisplayList)
				glStencilFunc(GL_EQUAL, 1, 1);
				glColor(1, 0, 0)
				glCallList(self.modelDisplayList)

				glPushMatrix()
				glLoadIdentity()
				for i in xrange(2, 20, 2):
					glStencilFunc(GL_EQUAL, i, 0xFF);
					glColor(0, float(i)/10, 0)
					glBegin(GL_QUADS)
					glVertex3f(-1000,-1000,-1)
					glVertex3f( 1000,-1000,-1)
					glVertex3f( 1000, 1000,-1)
					glVertex3f(-1000, 1000,-1)
					glEnd()
				for i in xrange(1, 20, 2):
					glStencilFunc(GL_EQUAL, i, 0xFF);
					glColor(float(i)/10, 0, 0)
					glBegin(GL_QUADS)
					glVertex3f(-1000,-1000,-1)
					glVertex3f( 1000,-1000,-1)
					glVertex3f( 1000, 1000,-1)
					glVertex3f(-1000, 1000,-1)
					glEnd()
				glPopMatrix()

				glDisable(GL_STENCIL_TEST);
				glEnable(GL_DEPTH_TEST)
			else:
				glEnable(GL_LIGHTING)
				glCallList(self.modelDisplayList)
		glFlush()

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
		glEnable(GL_CULL_FACE)
		glDisable(GL_BLEND)

		glClearColor(0.0, 0.0, 0.0, 1.0)
		glClearStencil(0)
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

