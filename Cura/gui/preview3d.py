from __future__ import division

import sys
import math
import threading
import re
import time
import os

from wx import glcanvas
from wx.lib import buttons
import wx
try:
	import OpenGL
	OpenGL.ERROR_CHECKING = False
	from OpenGL.GLU import *
	from OpenGL.GL import *
	hasOpenGLlibs = True
except:
	print "Failed to find PyOpenGL: http://pyopengl.sourceforge.net/"
	hasOpenGLlibs = False

from gui import opengl

from util import profile
from util import gcodeInterpreter
from util import stl
from util import util3d

class ToggleButton(buttons.GenBitmapToggleButton):
	def __init__(self, parent, popupParent, profileSetting, bitmapFilenameOn, bitmapFilenameOff,
				 helpText='', id=-1, size=(20,20)):
		self.bitmapOn = wx.Bitmap(os.path.join(os.path.split(__file__)[0], "../images", bitmapFilenameOn))
		self.bitmapOff = wx.Bitmap(os.path.join(os.path.split(__file__)[0], "../images", bitmapFilenameOff))

		buttons.GenBitmapToggleButton.__init__(self, parent, id, self.bitmapOff, size=size)

		self.popupParent = popupParent
		self.profileSetting = profileSetting
		self.helpText = helpText

		self.bezelWidth = 1
		self.useFocusInd = False

		if self.profileSetting != '':
			self.SetValue(profile.getProfileSetting(self.profileSetting) == 'True')
			self.Bind(wx.EVT_BUTTON, self.OnButtonProfile)
		else:
			self.Bind(wx.EVT_BUTTON, self.OnButton)

		self.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseEnter)
		self.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseLeave)

	def SetBitmap(self, bool):
		if bool:
			buttons.GenBitmapToggleButton.SetBitmapLabel(self, self.bitmapOn, False)
		else:
			buttons.GenBitmapToggleButton.SetBitmapLabel(self, self.bitmapOff, False)

	def SetValue(self, bool):
		self.SetBitmap(bool)
		buttons.GenBitmapToggleButton.SetValue(self, bool)

	def OnButton(self, event):
		self.SetBitmap(buttons.GenBitmapToggleButton.GetValue(self))
		event.Skip()

	def OnButtonProfile(self, event):
		if buttons.GenBitmapToggleButton.GetValue(self):
			self.SetBitmap(True)
			profile.putProfileSetting(self.profileSetting, 'True')
		else:
			self.SetBitmap(False)
			profile.putProfileSetting(self.profileSetting, 'False')
		self.popupParent.updateModelTransform()
		event.Skip()

	def OnMouseEnter(self, event):
		self.popupParent.OnPopupDisplay(event)
		event.Skip()

	def OnMouseLeave(self, event):
		self.popupParent.OnPopupHide(event)
		event.Skip()

class NormalButton(buttons.GenBitmapButton):
	def __init__(self, parent, popupParent, bitmapFilename,
				 helpText='', id=-1, size=(20,20)):
		self.bitmap = wx.Bitmap(os.path.join(os.path.split(__file__)[0], "../images", bitmapFilename))
		buttons.GenBitmapButton.__init__(self, parent, id, self.bitmap, size=size)

		self.popupParent = popupParent
		self.helpText = helpText

		self.bezelWidth = 1
		self.useFocusInd = False

		self.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseEnter)
		self.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseLeave)

	def OnMouseEnter(self, event):
		self.popupParent.OnPopupDisplay(event)
		event.Skip()

	def OnMouseLeave(self, event):
		self.popupParent.OnPopupHide(event)
		event.Skip()

class previewPanel(wx.Panel):
	def __init__(self, parent):
		wx.Panel.__init__(self, parent,-1)
		
		self.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DDKSHADOW))
		self.SetMinSize((440,320))
		
		# Create popup window
		self.popup = wx.PopupWindow(self, flags=wx.BORDER_SIMPLE)
		self.popup.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_INFOBK))
		self.popup.text = wx.StaticText(self.popup, -1, '')
		self.popup.sizer = wx.BoxSizer()
		self.popup.sizer.Add(self.popup.text, flag=wx.EXPAND|wx.ALL, border=1)
		self.popup.SetSizer(self.popup.sizer)
		self.popupOwner = None
		
		self.glCanvas = PreviewGLCanvas(self)
		self.init = 0
		self.triangleMesh = None
		self.gcode = None
		self.modelFilename = None
		self.loadingProgressAmount = 0
		self.loadThread = None
		self.machineSize = util3d.Vector3(float(profile.getPreference('machine_width')), float(profile.getPreference('machine_depth')), float(profile.getPreference('machine_height')))
		self.machineCenter = util3d.Vector3(float(profile.getProfileSetting('machine_center_x')), float(profile.getProfileSetting('machine_center_y')), 0)
		
		self.toolbar = wx.ToolBar( self, -1 )
		self.toolbar.SetToolBitmapSize( ( 21, 21 ) )

		button = wx.Button(self.toolbar, -1, "3D", size=(21*2,21))
		self.toolbar.AddControl(button)
		self.Bind(wx.EVT_BUTTON, self.On3DClick, button)
		
		button = wx.Button(self.toolbar, -1, "Top", size=(21*2,21))
		self.toolbar.AddControl(button)
		self.Bind(wx.EVT_BUTTON, self.OnTopClick, button)

		self.viewSelect = wx.ComboBox(self.toolbar, -1, 'Model - Normal', choices=['Model - Normal', 'Model - Transparent', 'Model - X-Ray', 'GCode', 'Mixed'], style=wx.CB_DROPDOWN|wx.CB_READONLY)
		self.toolbar.AddControl(self.viewSelect)
		self.viewSelect.Bind(wx.EVT_COMBOBOX, self.OnViewChange)
		self.glCanvas.viewMode = self.viewSelect.GetValue()

		self.layerSpin = wx.SpinCtrl(self.toolbar, -1, '', size=(21*4,21), style=wx.SP_ARROW_KEYS)
		self.toolbar.AddControl(self.layerSpin)
		self.Bind(wx.EVT_SPINCTRL, self.OnLayerNrChange, self.layerSpin)
		
		self.toolbar2 = wx.ToolBar( self, -1, style = wx.TB_HORIZONTAL | wx.NO_BORDER )
		self.toolbar2.SetToolBitmapSize( ( 21, 21 ) )

		self.mirrorX = ToggleButton(self.toolbar2, self, 'flip_x', 'object-mirror-x-on.png', 'object-mirror-x-off.png', 'Mirror X')
		self.toolbar2.AddControl(self.mirrorX)

		self.mirrorY = ToggleButton(self.toolbar2, self, 'flip_y', 'object-mirror-y-on.png', 'object-mirror-y-off.png', 'Mirror Y')
		self.toolbar2.AddControl(self.mirrorY)

		self.mirrorZ = ToggleButton(self.toolbar2, self, 'flip_z', 'object-mirror-z-on.png', 'object-mirror-z-off.png', 'Mirror Z')
		self.toolbar2.AddControl(self.mirrorZ)

		self.toolbar2.AddSeparator()

		self.swapXZ = ToggleButton(self.toolbar2, self, 'swap_xz', 'object-swap-xz-on.png', 'object-swap-xz-off.png', 'Swap XZ')
		self.toolbar2.AddControl(self.swapXZ)

		self.swapYZ = ToggleButton(self.toolbar2, self, 'swap_yz', 'object-swap-yz-on.png', 'object-swap-yz-off.png', 'Swap YZ')
		self.toolbar2.AddControl(self.swapYZ)
		
		self.toolbar2.InsertSeparator(self.toolbar2.GetToolsCount())
		self.toolbar2.AddControl(wx.StaticText(self.toolbar2, -1, 'Scale'))
		self.scale = wx.TextCtrl(self.toolbar2, -1, profile.getProfileSetting('model_scale'), size=(21*2,21))
		self.toolbar2.AddControl(self.scale)
		self.Bind(wx.EVT_TEXT, self.OnScale, self.scale)

		self.toolbar2.InsertSeparator(self.toolbar2.GetToolsCount())
		self.toolbar2.AddControl(wx.StaticText(self.toolbar2, -1, 'Copy'))
		self.mulXsub = wx.Button(self.toolbar2, -1, '-', size=(21,21))
		self.toolbar2.AddControl(self.mulXsub)
		self.Bind(wx.EVT_BUTTON, self.OnMulXSubClick, self.mulXsub)
		self.mulXadd = wx.Button(self.toolbar2, -1, '+', size=(21,21))
		self.toolbar2.AddControl(self.mulXadd)
		self.Bind(wx.EVT_BUTTON, self.OnMulXAddClick, self.mulXadd)

		self.mulYsub = wx.Button(self.toolbar2, -1, '-', size=(21,21))
		self.toolbar2.AddControl(self.mulYsub)
		self.Bind(wx.EVT_BUTTON, self.OnMulYSubClick, self.mulYsub)
		self.mulYadd = wx.Button(self.toolbar2, -1, '+', size=(21,21))
		self.toolbar2.AddControl(self.mulYadd)
		self.Bind(wx.EVT_BUTTON, self.OnMulYAddClick, self.mulYadd)
		
		self.toolbar2.InsertSeparator(self.toolbar2.GetToolsCount())
		self.toolbar2.AddControl(wx.StaticText(self.toolbar2, -1, 'Rot'))
		self.rotate = wx.SpinCtrl(self.toolbar2, -1, profile.getProfileSetting('model_rotate_base'), size=(21*3,21), style=wx.SP_WRAP|wx.SP_ARROW_KEYS)
		self.rotate.SetRange(0, 360)
		self.toolbar2.AddControl(self.rotate)
		self.Bind(wx.EVT_SPINCTRL, self.OnRotate, self.rotate)

		self.scaleMax = NormalButton(self.toolbar, self, 'object-max-size.png', 'Scale object to fix machine size')
		self.toolbar.AddControl(self.scaleMax)
		self.Bind(wx.EVT_BUTTON, self.OnScaleMax, self.scaleMax)

		self.toolbar2.Realize()
		self.updateToolbar()
		
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.toolbar, 0, flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=1)
		sizer.Add(self.glCanvas, 1, flag=wx.EXPAND)
		sizer.Add(self.toolbar2, 0, flag=wx.EXPAND|wx.BOTTOM|wx.LEFT|wx.RIGHT, border=1)
		self.SetSizer(sizer)
	
	def OnPopupDisplay(self, e):
		self.UpdatePopup(e.GetEventObject())
		self.popup.Show(True)
	
	def OnPopupHide(self, e):
		if self.popupOwner == e.GetEventObject():
			self.popup.Show(False)
	
	def UpdatePopup(self, control):
		self.popupOwner = control
		self.popup.text.SetLabel(control.helpText)
		self.popup.text.Wrap(350)
		self.popup.Fit();
		if os.name == 'darwin':
			x, y = self.ClientToScreenXY(0, 0)
			sx, sy = self.GetClientSizeTuple()
		else:
			x, y = control.ClientToScreenXY(0, 0)
			sx, sy = control.GetSizeTuple()
		self.popup.SetPosition((x, y+sy))

	def OnMulXAddClick(self, e):
		profile.putProfileSetting('model_multiply_x', str(max(1, int(profile.getProfileSetting('model_multiply_x'))+1)))
		self.updateModelTransform()

	def OnMulXSubClick(self, e):
		profile.putProfileSetting('model_multiply_x', str(max(1, int(profile.getProfileSetting('model_multiply_x'))-1)))
		self.updateModelTransform()

	def OnMulYAddClick(self, e):
		profile.putProfileSetting('model_multiply_y', str(max(1, int(profile.getProfileSetting('model_multiply_y'))+1)))
		self.updateModelTransform()

	def OnMulYSubClick(self, e):
		profile.putProfileSetting('model_multiply_y', str(max(1, int(profile.getProfileSetting('model_multiply_y'))-1)))
		self.updateModelTransform()

	def OnScale(self, e):
		profile.putProfileSetting('model_scale', self.scale.GetValue())
		self.updateModelTransform()
	
	def OnScaleMax(self, e):
		if self.triangleMesh == None:
			return
		scale = float(self.scale.GetValue())
		vMin = self.triangleMesh.getMinimum() / scale
		vMax = self.triangleMesh.getMaximum() / scale
		scaleX1 = (self.machineSize.x - self.machineCenter.x) / ((vMax.x - vMin.x) / 2)
		scaleY1 = (self.machineSize.y - self.machineCenter.y) / ((vMax.y - vMin.y) / 2)
		scaleX2 = (self.machineCenter.x) / ((vMax.x - vMin.x) / 2)
		scaleY2 = (self.machineCenter.y) / ((vMax.y - vMin.y) / 2)
		scaleZ = self.machineSize.z / (vMax.z - vMin.z)
		scale = min(scaleX1, scaleY1, scaleX2, scaleY2, scaleZ)
		self.scale.SetValue(str(scale))
		profile.putProfileSetting('model_scale', self.scale.GetValue())
		self.updateModelTransform()
	
	def OnRotate(self, e):
		profile.putProfileSetting('model_rotate_base', self.rotate.GetValue())
		self.updateModelTransform()

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
		self.gcodeDirty = True
		self.glCanvas.Refresh()

	def updateCenterX(self, x):
		self.machineCenter.x = x
		self.moveModel()
		self.glCanvas.Refresh()

	def updateCenterY(self, y):
		self.machineCenter.y = y
		self.moveModel()
		self.glCanvas.Refresh()
	
	def setViewMode(self, mode):
		self.viewSelect.SetValue(mode)
		self.glCanvas.viewMode = self.viewSelect.GetValue()
		wx.CallAfter(self.glCanvas.Refresh)
	
	def loadModelFile(self, filename):
		if self.modelFilename != filename:
			self.modelFileTime = None
			self.gcodeFileTime = None
			self.logFileTime = None
		
		self.modelFilename = filename
		self.gcodeFilename = filename[: filename.rfind('.')] + "_export.gcode"
		self.logFilename = filename[: filename.rfind('.')] + "_export.log"
		#Do the STL file loading in a background thread so we don't block the UI.
		if self.loadThread != None and self.loadThread.isAlive():
			self.loadThread.join()
		self.loadThread = threading.Thread(target=self.doFileLoadThread)
		self.loadThread.daemon = True
		self.loadThread.start()
	
	def loadReModelFile(self, filename):
		#Only load this again if the filename matches the file we have already loaded (for auto loading GCode after slicing)
		if self.modelFilename != filename:
			return False
		self.loadModelFile(filename)
		return True
	
	def doFileLoadThread(self):
		if os.path.isfile(self.modelFilename) and self.modelFileTime != os.stat(self.modelFilename).st_mtime:
			self.modelFileTime = os.stat(self.modelFilename).st_mtime
			triangleMesh = stl.stlModel()
			triangleMesh.load(self.modelFilename)
			triangleMesh.origonalVertexes = list(triangleMesh.vertexes)
			for i in xrange(0, len(triangleMesh.origonalVertexes)):
				triangleMesh.origonalVertexes[i] = triangleMesh.origonalVertexes[i].copy()
			triangleMesh.getMinimumZ()
			self.modelDirty = False
			self.errorList = []
			self.triangleMesh = triangleMesh
			self.updateModelTransform()
			wx.CallAfter(self.updateToolbar)
			wx.CallAfter(self.glCanvas.Refresh)
		
		if os.path.isfile(self.gcodeFilename) and self.gcodeFileTime != os.stat(self.gcodeFilename).st_mtime:
			self.gcodeFileTime = os.stat(self.gcodeFilename).st_mtime
			gcode = gcodeInterpreter.gcode()
			gcode.progressCallback = self.loadProgress
			gcode.load(self.gcodeFilename)
			self.loadingProgressAmount = 0
			self.gcodeDirty = False
			self.errorList = []
			self.gcode = gcode
			self.gcodeDirty = True
			wx.CallAfter(self.updateToolbar)
			wx.CallAfter(self.glCanvas.Refresh)
		elif not os.path.isfile(self.gcodeFilename):
			self.gcode = None
		
		if os.path.isfile(self.logFilename):
			errorList = []
			for line in open(self.logFilename, "rt"):
				res = re.search('Model error\(([a-z ]*)\): \(([0-9\.\-e]*), ([0-9\.\-e]*), ([0-9\.\-e]*)\) \(([0-9\.\-e]*), ([0-9\.\-e]*), ([0-9\.\-e]*)\)', line)
				if res != None:
					v1 = util3d.Vector3(float(res.group(2)), float(res.group(3)), float(res.group(4)))
					v2 = util3d.Vector3(float(res.group(5)), float(res.group(6)), float(res.group(7)))
					errorList.append([v1, v2])
			self.errorList = errorList
			wx.CallAfter(self.glCanvas.Refresh)
	
	def loadProgress(self, progress):
		self.loadingProgressAmount = progress
		wx.CallAfter(self.glCanvas.Refresh)
	
	def updateToolbar(self):
		self.layerSpin.Show(self.gcode != None)
		if self.gcode != None:
			self.layerSpin.SetRange(1, len(self.gcode.layerList))
		self.toolbar.Realize()
	
	def OnViewChange(self, e):
		self.glCanvas.viewMode = self.viewSelect.GetValue()
		self.glCanvas.Refresh()
	
	def updateModelTransform(self, f=0):
		if self.triangleMesh == None:
			return
		scale = 1.0
		rotate = 0.0
		try:
			scale = profile.getProfileSettingFloat('model_scale')
			rotate = profile.getProfileSettingFloat('model_rotate_base') / 180.0 * math.pi
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
		swapXZ = profile.getProfileSetting('swap_xz') == 'True'
		swapYZ = profile.getProfileSetting('swap_yz') == 'True'
		mat00 = math.cos(rotate) * scaleX
		mat01 =-math.sin(rotate) * scaleY
		mat10 = math.sin(rotate) * scaleX
		mat11 = math.cos(rotate) * scaleY
		
		for i in xrange(0, len(self.triangleMesh.origonalVertexes)):
			x = self.triangleMesh.origonalVertexes[i].x
			y = self.triangleMesh.origonalVertexes[i].y
			z = self.triangleMesh.origonalVertexes[i].z
			if swapXZ:
				x, z = z, x
			if swapYZ:
				y, z = z, y
			self.triangleMesh.vertexes[i].x = x * mat00 + y * mat01
			self.triangleMesh.vertexes[i].y = x * mat10 + y * mat11
			self.triangleMesh.vertexes[i].z = z * scaleZ

		for face in self.triangleMesh.faces:
			v1 = face.v[0]
			v2 = face.v[1]
			v3 = face.v[2]
			face.normal = (v2 - v1).cross(v3 - v1)
			face.normal.normalize()

		self.moveModel()
	
	def moveModel(self):
		if self.triangleMesh == None:
			return
		minZ = self.triangleMesh.getMinimumZ()
		min = self.triangleMesh.getMinimum()
		max = self.triangleMesh.getMaximum()
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
		self.zoom = 300
		self.offsetX = 0
		self.offsetY = 0
		self.view3D = True
		self.modelDisplayList = None
		self.gcodeDisplayList = None
	
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
		#Workaround for windows background redraw flicker.
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
		opengl.InitGL(self, self.view3D, self.zoom)
		if self.view3D:
			glTranslate(0,0,-self.zoom)
			glRotate(-self.pitch, 1,0,0)
			glRotate(self.yaw, 0,0,1)
			if self.parent.triangleMesh != None:
				glTranslate(0,0,-self.parent.triangleMesh.getMaximum().z / 2)
		else:
			glScale(1.0/self.zoom, 1.0/self.zoom, 1.0)
			glTranslate(self.offsetX, self.offsetY, 0.0)
		glTranslate(-self.parent.machineCenter.x, -self.parent.machineCenter.y, 0)

		self.OnDraw()
		self.SwapBuffers()

	def OnDraw(self):
		machineSize = self.parent.machineSize
		opengl.DrawMachine(machineSize)

		if self.parent.gcode != None:
			if self.gcodeDisplayList == None:
				self.gcodeDisplayList = glGenLists(1);
			if self.parent.gcodeDirty:
				self.parent.gcodeDirty = False
				glNewList(self.gcodeDisplayList, GL_COMPILE)
				prevLayerZ = 0.0
				curLayerZ = 0.0
				
				layerThickness = 0.0
				filamentRadius = float(profile.getProfileSetting('filament_diameter')) / 2
				filamentArea = math.pi * filamentRadius * filamentRadius
				lineWidth = float(profile.getProfileSetting('nozzle_size')) / 2 / 10
				
				curLayerNum = 0
				for layer in self.parent.gcode.layerList:
					curLayerZ = layer[0].list[1].z
					layerThickness = curLayerZ - prevLayerZ
					prevLayerZ = layer[-1].list[-1].z
					for path in layer:
						c = 1.0
						if curLayerNum != self.parent.layerSpin.GetValue():
							if curLayerNum < self.parent.layerSpin.GetValue():
								c = 0.9 - (self.parent.layerSpin.GetValue() - curLayerNum) * 0.1
								if c < 0.4:
									c = 0.4
							else:
								break
						if path.type == 'move':
							glColor3f(0,0,c)
						if path.type == 'extrude':
							if path.pathType == 'FILL':
								glColor3f(c/2,c/2,0)
							elif path.pathType == 'WALL-INNER':
								glColor3f(0,c,0)
							elif path.pathType == 'SUPPORT':
								glColor3f(0,c,c)
							elif path.pathType == 'SKIRT':
								glColor3f(0,c/2,c/2)
							else:
								glColor3f(c,0,0)
						if path.type == 'retract':
							glColor3f(0,c,c)
						if c > 0.4 and path.type == 'extrude':
							for i in xrange(0, len(path.list)-1):
								v0 = path.list[i]
								v1 = path.list[i+1]

								# Calculate line width from ePerDistance (needs layer thickness and filament diameter)
								dist = (v0 - v1).vsize()
								if dist > 0 and layerThickness > 0:
									extrusionMMperDist = (v1.e - v0.e) / dist
									lineWidth = extrusionMMperDist * filamentArea / layerThickness / 2

								normal = (v0 - v1).cross(util3d.Vector3(0,0,1))
								normal.normalize()
								v2 = v0 + normal * lineWidth
								v3 = v1 + normal * lineWidth
								v0 = v0 - normal * lineWidth
								v1 = v1 - normal * lineWidth

								glBegin(GL_QUADS)
								if path.pathType == 'FILL':	#Remove depth buffer fighting on infill/wall overlap
									glVertex3f(v0.x, v0.y, v0.z - 0.02)
									glVertex3f(v1.x, v1.y, v1.z - 0.02)
									glVertex3f(v3.x, v3.y, v3.z - 0.02)
									glVertex3f(v2.x, v2.y, v2.z - 0.02)
								else:
									glVertex3f(v0.x, v0.y, v0.z - 0.01)
									glVertex3f(v1.x, v1.y, v1.z - 0.01)
									glVertex3f(v3.x, v3.y, v3.z - 0.01)
									glVertex3f(v2.x, v2.y, v2.z - 0.01)
								glEnd()
						
							#for v in path['list']:
							#	glBegin(GL_TRIANGLE_FAN)
							#	glVertex3f(v.x, v.y, v.z - 0.001)
							#	for i in xrange(0, 16+1):
							#		if path['pathType'] == 'FILL':	#Remove depth buffer fighting on infill/wall overlap
							#			glVertex3f(v.x + math.cos(math.pi*2/16*i) * lineWidth, v.y + math.sin(math.pi*2/16*i) * lineWidth, v.z - 0.02)
							#		else:
							#			glVertex3f(v.x + math.cos(math.pi*2/16*i) * lineWidth, v.y + math.sin(math.pi*2/16*i) * lineWidth, v.z - 0.01)
							#	glEnd()
						else:
							glBegin(GL_LINE_STRIP)
							for v in path.list:
								glVertex3f(v.x, v.y, v.z)
							glEnd()
					curLayerNum += 1
				glEndList()
			if self.viewMode == "GCode" or self.viewMode == "Mixed":
				glCallList(self.gcodeDisplayList)
		
		if self.parent.triangleMesh != None:
			if self.modelDisplayList == None:
				self.modelDisplayList = glGenLists(1);
			if self.parent.modelDirty:
				self.parent.modelDirty = False
				multiX = int(profile.getProfileSetting('model_multiply_x'))
				multiY = int(profile.getProfileSetting('model_multiply_y'))
				modelSize = self.parent.triangleMesh.getMaximum() - self.parent.triangleMesh.getMinimum()
				glNewList(self.modelDisplayList, GL_COMPILE)
				glPushMatrix()
				glTranslate(-(modelSize.x+10)*(multiX-1)/2,-(modelSize.y+10)*(multiY-1)/2, 0)
				for mx in xrange(0, multiX):
					for my in xrange(0, multiY):
						glPushMatrix()
						glTranslate((modelSize.x+10)*mx,(modelSize.y+10)*my, 0)
						opengl.DrawSTL(self.parent.triangleMesh)
						glPopMatrix()
				glPopMatrix()
				glEndList()
			
			if self.viewMode == "Model - Transparent" or self.viewMode == "Mixed":
				glLightfv(GL_LIGHT0, GL_DIFFUSE,  [0.5, 0.4, 0.3, 1.0])
				glLightfv(GL_LIGHT0, GL_AMBIENT,  [0.1, 0.1, 0.1, 0.0])
				#If we want transparent, then first render a solid black model to remove the printer size lines.
				if self.viewMode != "Mixed":
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
			elif self.viewMode == "Model - X-Ray":
				glColorMask(GL_FALSE, GL_FALSE, GL_FALSE, GL_FALSE)
				glDisable(GL_DEPTH_TEST)
				glEnable(GL_STENCIL_TEST);
				glStencilFunc(GL_ALWAYS, 1, 1)
				glStencilOp(GL_INCR, GL_INCR, GL_INCR)
				glCallList(self.modelDisplayList)
				glStencilOp (GL_KEEP, GL_KEEP, GL_KEEP);
				
				glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)
				glStencilFunc(GL_EQUAL, 0, 1);
				glColor(1, 1, 1)
				glCallList(self.modelDisplayList)
				glStencilFunc(GL_EQUAL, 1, 1);
				glColor(1, 0, 0)
				glCallList(self.modelDisplayList)

				glPushMatrix()
				glLoadIdentity()
				for i in xrange(2, 15, 2):
					glStencilFunc(GL_EQUAL, i, 0xFF);
					glColor(float(i)/10, float(i)/10, float(i)/5)
					glBegin(GL_QUADS)
					glVertex3f(-1000,-1000,-1)
					glVertex3f( 1000,-1000,-1)
					glVertex3f( 1000, 1000,-1)
					glVertex3f(-1000, 1000,-1)
					glEnd()
				for i in xrange(1, 15, 2):
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
			elif self.viewMode == "Model - Normal":
				glLightfv(GL_LIGHT0, GL_DIFFUSE,  [1.0, 0.8, 0.6, 1.0])
				glLightfv(GL_LIGHT0, GL_AMBIENT,  [0.2, 0.2, 0.2, 0.0])
				glEnable(GL_LIGHTING)
				glCallList(self.modelDisplayList)
			
			if self.viewMode == "Model - Normal" or self.viewMode == "Model - Transparent" or self.viewMode == "Model - X-Ray":
				glDisable(GL_LIGHTING)
				glDisable(GL_DEPTH_TEST)
				glDisable(GL_BLEND)
				glColor3f(1,0,0)
				glTranslate(self.parent.machineCenter.x, self.parent.machineCenter.y, 0)
				glBegin(GL_LINES)
				for err in self.parent.errorList:
					glVertex3f(err[0].x, err[0].y, err[0].z)
					glVertex3f(err[1].x, err[1].y, err[1].z)
				glEnd()
		
		glFlush()
