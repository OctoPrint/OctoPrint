from __future__ import division

import sys, math, threading, re, time, os
import numpy

from wx import glcanvas
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
from gui import toolbarUtil

from util import profile
from util import gcodeInterpreter
from util import meshLoader
from util import util3d
from util import sliceRun

class previewObject():
	def __init__(self):
		self.mesh = None
		self.filename = None
		self.displayList = None
		self.dirty = False

class previewPanel(wx.Panel):
	def __init__(self, parent):
		super(previewPanel, self).__init__(parent,-1)
		
		self.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DDKSHADOW))
		self.SetMinSize((440,320))
		
		self.objectList = []
		self.errorList = []
		self.gcode = None
		self.objectsMinV = None
		self.objectsMaxV = None
		self.objectsBounderyCircleSize = None
		self.loadThread = None
		self.machineSize = util3d.Vector3(profile.getPreferenceFloat('machine_width'), profile.getPreferenceFloat('machine_depth'), profile.getPreferenceFloat('machine_height'))
		self.machineCenter = util3d.Vector3(self.machineSize.x / 2, self.machineSize.y / 2, 0)

		self.glCanvas = PreviewGLCanvas(self)
		#Create the popup window
		self.warningPopup = wx.PopupWindow(self, flags=wx.BORDER_SIMPLE)
		self.warningPopup.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_INFOBK))
		self.warningPopup.text = wx.StaticText(self.warningPopup, -1, 'Reset scale, rotation and mirror?')
		self.warningPopup.yesButton = wx.Button(self.warningPopup, -1, 'yes', style=wx.BU_EXACTFIT)
		self.warningPopup.noButton = wx.Button(self.warningPopup, -1, 'no', style=wx.BU_EXACTFIT)
		self.warningPopup.sizer = wx.BoxSizer(wx.HORIZONTAL)
		self.warningPopup.SetSizer(self.warningPopup.sizer)
		self.warningPopup.sizer.Add(self.warningPopup.text, 1, flag=wx.ALL|wx.ALIGN_CENTER_VERTICAL, border=1)
		self.warningPopup.sizer.Add(self.warningPopup.yesButton, 0, flag=wx.EXPAND|wx.ALL, border=1)
		self.warningPopup.sizer.Add(self.warningPopup.noButton, 0, flag=wx.EXPAND|wx.ALL, border=1)
		self.warningPopup.Fit()
		self.warningPopup.Layout()
		self.warningPopup.timer = wx.Timer(self)
		self.Bind(wx.EVT_TIMER, self.OnHideWarning, self.warningPopup.timer)
		
		self.Bind(wx.EVT_BUTTON, self.OnWarningPopup, self.warningPopup.yesButton)
		self.Bind(wx.EVT_BUTTON, self.OnHideWarning, self.warningPopup.noButton)
		parent.Bind(wx.EVT_MOVE, self.OnMove)
		parent.Bind(wx.EVT_SIZE, self.OnMove)
		
		self.toolbar = toolbarUtil.Toolbar(self)

		group = []
		toolbarUtil.RadioButton(self.toolbar, group, 'object-3d-on.png', 'object-3d-off.png', '3D view', callback=self.On3DClick)
		toolbarUtil.RadioButton(self.toolbar, group, 'object-top-on.png', 'object-top-off.png', 'Topdown view', callback=self.OnTopClick)
		self.toolbar.AddSeparator()

		self.showBorderButton = toolbarUtil.ToggleButton(self.toolbar, '', 'view-border-on.png', 'view-border-off.png', 'Show model borders', callback=self.OnViewChange)
		self.showSteepOverhang = toolbarUtil.ToggleButton(self.toolbar, '', 'steepOverhang-on.png', 'steepOverhang-off.png', 'Show steep overhang', callback=self.OnViewChange)
		self.toolbar.AddSeparator()

		group = []
		self.normalViewButton = toolbarUtil.RadioButton(self.toolbar, group, 'view-normal-on.png', 'view-normal-off.png', 'Normal model view', callback=self.OnViewChange)
		self.transparentViewButton = toolbarUtil.RadioButton(self.toolbar, group, 'view-transparent-on.png', 'view-transparent-off.png', 'Transparent model view', callback=self.OnViewChange)
		self.xrayViewButton = toolbarUtil.RadioButton(self.toolbar, group, 'view-xray-on.png', 'view-xray-off.png', 'X-Ray view', callback=self.OnViewChange)
		self.gcodeViewButton = toolbarUtil.RadioButton(self.toolbar, group, 'view-gcode-on.png', 'view-gcode-off.png', 'GCode view', callback=self.OnViewChange)
		self.mixedViewButton = toolbarUtil.RadioButton(self.toolbar, group, 'view-mixed-on.png', 'view-mixed-off.png', 'Mixed model/GCode view', callback=self.OnViewChange)
		self.toolbar.AddSeparator()

		self.layerSpin = wx.SpinCtrl(self.toolbar, -1, '', size=(21*4,21), style=wx.SP_ARROW_KEYS)
		self.toolbar.AddControl(self.layerSpin)
		self.Bind(wx.EVT_SPINCTRL, self.OnLayerNrChange, self.layerSpin)
		self.toolbar.AddSeparator()
		self.toolbarInfo = wx.TextCtrl(self.toolbar, -1, '', style=wx.TE_READONLY)
		self.toolbar.AddControl(self.toolbarInfo)

		self.toolbar2 = toolbarUtil.Toolbar(self)

		# Mirror
		self.mirrorX = toolbarUtil.ToggleButton(self.toolbar2, 'flip_x', 'object-mirror-x-on.png', 'object-mirror-x-off.png', 'Mirror X', callback=self.returnToModelViewAndUpdateModel)
		self.mirrorY = toolbarUtil.ToggleButton(self.toolbar2, 'flip_y', 'object-mirror-y-on.png', 'object-mirror-y-off.png', 'Mirror Y', callback=self.returnToModelViewAndUpdateModel)
		self.mirrorZ = toolbarUtil.ToggleButton(self.toolbar2, 'flip_z', 'object-mirror-z-on.png', 'object-mirror-z-off.png', 'Mirror Z', callback=self.returnToModelViewAndUpdateModel)
		self.toolbar2.AddSeparator()

		# Swap
		self.swapXZ = toolbarUtil.ToggleButton(self.toolbar2, 'swap_xz', 'object-swap-xz-on.png', 'object-swap-xz-off.png', 'Swap XZ', callback=self.returnToModelViewAndUpdateModel)
		self.swapYZ = toolbarUtil.ToggleButton(self.toolbar2, 'swap_yz', 'object-swap-yz-on.png', 'object-swap-yz-off.png', 'Swap YZ', callback=self.returnToModelViewAndUpdateModel)
		self.toolbar2.AddSeparator()

		# Scale
		self.scaleReset = toolbarUtil.NormalButton(self.toolbar2, self.OnScaleReset, 'object-scale.png', 'Reset model scale')
		self.scale = wx.TextCtrl(self.toolbar2, -1, profile.getProfileSetting('model_scale'), size=(21*2,21))
		self.toolbar2.AddControl(self.scale)
		self.scale.Bind(wx.EVT_TEXT, self.OnScale)
		self.scaleMax = toolbarUtil.NormalButton(self.toolbar2, self.OnScaleMax, 'object-max-size.png', 'Scale object to fit machine size')

		self.toolbar2.AddSeparator()

		# Multiply
		#self.mulXadd = toolbarUtil.NormalButton(self.toolbar2, self.OnMulXAddClick, 'object-mul-x-add.png', 'Increase number of models on X axis')
		#self.mulXsub = toolbarUtil.NormalButton(self.toolbar2, self.OnMulXSubClick, 'object-mul-x-sub.png', 'Decrease number of models on X axis')
		#self.mulYadd = toolbarUtil.NormalButton(self.toolbar2, self.OnMulYAddClick, 'object-mul-y-add.png', 'Increase number of models on Y axis')
		#self.mulYsub = toolbarUtil.NormalButton(self.toolbar2, self.OnMulYSubClick, 'object-mul-y-sub.png', 'Decrease number of models on Y axis')
		#self.toolbar2.AddSeparator()

		# Rotate
		self.rotateReset = toolbarUtil.NormalButton(self.toolbar2, self.OnRotateReset, 'object-rotate.png', 'Reset model rotation')
		self.rotate = wx.SpinCtrl(self.toolbar2, -1, profile.getProfileSetting('model_rotate_base'), size=(21*3,21), style=wx.SP_WRAP|wx.SP_ARROW_KEYS)
		self.rotate.SetRange(0, 360)
		self.rotate.Bind(wx.EVT_TEXT, self.OnRotate)
		self.toolbar2.AddControl(self.rotate)

		self.toolbar2.Realize()
		self.OnViewChange()
		
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.toolbar, 0, flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=1)
		sizer.Add(self.glCanvas, 1, flag=wx.EXPAND)
		sizer.Add(self.toolbar2, 0, flag=wx.EXPAND|wx.BOTTOM|wx.LEFT|wx.RIGHT, border=1)
		self.SetSizer(sizer)
	
	def returnToModelViewAndUpdateModel(self):
		if self.glCanvas.viewMode == 'GCode' or self.glCanvas.viewMode == 'Mixed':
			self.setViewMode('Normal')
		self.updateModelTransform()
	
	def OnMove(self, e = None):
		if e != None:
			e.Skip()
		x, y = self.glCanvas.ClientToScreenXY(0, 0)
		sx, sy = self.glCanvas.GetClientSizeTuple()
		self.warningPopup.SetPosition((x, y+sy-self.warningPopup.GetSize().height))
	
	def OnMulXAddClick(self, e):
		profile.putProfileSetting('model_multiply_x', str(max(1, int(profile.getProfileSetting('model_multiply_x'))+1)))
		self.glCanvas.Refresh()

	def OnMulXSubClick(self, e):
		profile.putProfileSetting('model_multiply_x', str(max(1, int(profile.getProfileSetting('model_multiply_x'))-1)))
		self.glCanvas.Refresh()

	def OnMulYAddClick(self, e):
		profile.putProfileSetting('model_multiply_y', str(max(1, int(profile.getProfileSetting('model_multiply_y'))+1)))
		self.glCanvas.Refresh()

	def OnMulYSubClick(self, e):
		profile.putProfileSetting('model_multiply_y', str(max(1, int(profile.getProfileSetting('model_multiply_y'))-1)))
		self.glCanvas.Refresh()

	def OnScaleReset(self, e):
		self.scale.SetValue('1.0')
		self.OnScale(None)

	def OnScale(self, e):
		scale = 1.0
		if self.scale.GetValue() != '':
			scale = self.scale.GetValue()
		profile.putProfileSetting('model_scale', scale)
		if self.glCanvas.viewMode == 'GCode' or self.glCanvas.viewMode == 'Mixed':
			self.setViewMode('Normal')
		self.glCanvas.Refresh()

		if self.objectsMaxV != None:
			size = (self.objectsMaxV - self.objectsMinV) * float(scale)
			self.toolbarInfo.SetValue('%0.1f %0.1f %0.1f' % (size[0], size[1], size[2]))

	def OnScaleMax(self, e = None, onlyScaleDown = False):
		if self.objectsMinV == None:
			return
		vMin = self.objectsMinV
		vMax = self.objectsMaxV
		skirtSize = 3
		if profile.getProfileSettingFloat('skirt_line_count') > 0:
			skirtSize = 3 + profile.getProfileSettingFloat('skirt_line_count') * profile.calculateEdgeWidth() + profile.getProfileSettingFloat('skirt_gap')
		scaleX1 = (self.machineSize.x - self.machineCenter.x - skirtSize) / ((vMax[0] - vMin[0]) / 2)
		scaleY1 = (self.machineSize.y - self.machineCenter.y - skirtSize) / ((vMax[1] - vMin[1]) / 2)
		scaleX2 = (self.machineCenter.x - skirtSize) / ((vMax[0] - vMin[0]) / 2)
		scaleY2 = (self.machineCenter.y - skirtSize) / ((vMax[1] - vMin[1]) / 2)
		scaleZ = self.machineSize.z / (vMax[2] - vMin[2])
		scale = min(scaleX1, scaleY1, scaleX2, scaleY2, scaleZ)
		if scale > 1.0 and onlyScaleDown:
			return
		self.scale.SetValue(str(scale))
		profile.putProfileSetting('model_scale', self.scale.GetValue())
		if self.glCanvas.viewMode == 'GCode' or self.glCanvas.viewMode == 'Mixed':
			self.setViewMode('Normal')
		self.glCanvas.Refresh()

	def OnRotateReset(self, e):
		self.rotate.SetValue(0)
		self.OnRotate(None)

	def OnRotate(self, e):
		profile.putProfileSetting('model_rotate_base', self.rotate.GetValue())
		self.returnToModelViewAndUpdateModel()

	def On3DClick(self):
		self.glCanvas.yaw = 30
		self.glCanvas.pitch = 60
		self.glCanvas.zoom = 300
		self.glCanvas.view3D = True
		self.glCanvas.Refresh()

	def OnTopClick(self):
		self.glCanvas.view3D = False
		self.glCanvas.zoom = 100
		self.glCanvas.offsetX = 0
		self.glCanvas.offsetY = 0
		self.glCanvas.Refresh()

	def OnLayerNrChange(self, e):
		self.glCanvas.Refresh()
	
	def setViewMode(self, mode):
		if mode == "Normal":
			self.normalViewButton.SetValue(True)
		if mode == "GCode":
			self.gcodeViewButton.SetValue(True)
		self.glCanvas.viewMode = mode
		wx.CallAfter(self.glCanvas.Refresh)
	
	def loadModelFiles(self, filelist, showWarning = False):
		while len(filelist) > len(self.objectList):
			self.objectList.append(previewObject())
		for idx in xrange(len(filelist), len(self.objectList)):
			self.objectList[idx].mesh = None
			self.objectList[idx].filename = None
		for idx in xrange(0, len(filelist)):
			obj = self.objectList[idx]
			if obj.filename != filelist[idx]:
				obj.fileTime = None
				self.gcodeFileTime = None
				self.logFileTime = None
			obj.filename = filelist[idx]
		
		self.gcodeFilename = sliceRun.getExportFilename(filelist[0])
		#Do the STL file loading in a background thread so we don't block the UI.
		if self.loadThread != None and self.loadThread.isAlive():
			self.loadThread.join()
		self.loadThread = threading.Thread(target=self.doFileLoadThread)
		self.loadThread.daemon = True
		self.loadThread.start()
		
		if showWarning:
			if profile.getProfileSettingFloat('model_scale') != 1.0 or profile.getProfileSettingFloat('model_rotate_base') != 0 or profile.getProfileSetting('flip_x') != 'False' or profile.getProfileSetting('flip_y') != 'False' or profile.getProfileSetting('flip_z') != 'False' or profile.getProfileSetting('swap_xz') != 'False' or profile.getProfileSetting('swap_yz') != 'False' or len(profile.getPluginConfig()) > 0:
				self.ShowWarningPopup('Reset scale, rotation, mirror and plugins?', self.OnResetAll)
	
	def loadReModelFiles(self, filelist):
		#Only load this again if the filename matches the file we have already loaded (for auto loading GCode after slicing)
		for idx in xrange(0, len(filelist)):
			if self.objectList[idx].filename != filelist[idx]:
				return False
		self.loadModelFiles(filelist)
		return True
	
	def doFileLoadThread(self):
		for obj in self.objectList:
			if obj.filename != None and os.path.isfile(obj.filename) and obj.fileTime != os.stat(obj.filename).st_mtime:
				obj.ileTime = os.stat(obj.filename).st_mtime
				mesh = meshLoader.loadMesh(obj.filename)
				obj.dirty = False
				obj.mesh = mesh
				self.updateModelTransform()
				self.OnScaleMax(None, True)
				scale = profile.getProfileSettingFloat('model_scale')
				size = (self.objectsMaxV - self.objectsMinV) * scale
				self.toolbarInfo.SetValue('%0.1f %0.1f %0.1f' % (size[0], size[1], size[2]))
				self.glCanvas.zoom = numpy.max(size) * 2.5
				self.errorList = []
				wx.CallAfter(self.updateToolbar)
				wx.CallAfter(self.glCanvas.Refresh)
		
		if os.path.isfile(self.gcodeFilename) and self.gcodeFileTime != os.stat(self.gcodeFilename).st_mtime:
			self.gcodeFileTime = os.stat(self.gcodeFilename).st_mtime
			gcode = gcodeInterpreter.gcode()
			gcode.progressCallback = self.loadProgress
			gcode.load(self.gcodeFilename)
			self.gcodeDirty = False
			self.gcode = gcode
			self.gcodeDirty = True

			errorList = []
			for line in open(self.gcodeFilename, "rt"):
				res = re.search(';Model error\(([a-z ]*)\): \(([0-9\.\-e]*), ([0-9\.\-e]*), ([0-9\.\-e]*)\) \(([0-9\.\-e]*), ([0-9\.\-e]*), ([0-9\.\-e]*)\)', line)
				if res != None:
					v1 = util3d.Vector3(float(res.group(2)), float(res.group(3)), float(res.group(4)))
					v2 = util3d.Vector3(float(res.group(5)), float(res.group(6)), float(res.group(7)))
					errorList.append([v1, v2])
			self.errorList = errorList

			wx.CallAfter(self.updateToolbar)
			wx.CallAfter(self.glCanvas.Refresh)
		elif not os.path.isfile(self.gcodeFilename):
			self.gcode = None
	
	def loadProgress(self, progress):
		pass

	def OnResetAll(self, e = None):
		profile.putProfileSetting('model_scale', '1.0')
		profile.putProfileSetting('model_rotate_base', '0')
		profile.putProfileSetting('flip_x', 'False')
		profile.putProfileSetting('flip_y', 'False')
		profile.putProfileSetting('flip_z', 'False')
		profile.putProfileSetting('swap_xz', 'False')
		profile.putProfileSetting('swap_yz', 'False')
		profile.setPluginConfig([])
		self.GetParent().updateProfileToControls()

	def ShowWarningPopup(self, text, callback = None):
		self.warningPopup.text.SetLabel(text)
		self.warningPopup.callback = callback
		if callback == None:
			self.warningPopup.yesButton.Show(False)
			self.warningPopup.noButton.SetLabel('ok')
		else:
			self.warningPopup.yesButton.Show(True)
			self.warningPopup.noButton.SetLabel('no')
		self.warningPopup.Fit()
		self.warningPopup.Layout()
		self.OnMove()
		self.warningPopup.Show(True)
		self.warningPopup.timer.Start(5000)
	
	def OnWarningPopup(self, e):
		self.warningPopup.Show(False)
		self.warningPopup.timer.Stop()
		self.warningPopup.callback()

	def OnHideWarning(self, e):
		self.warningPopup.Show(False)
		self.warningPopup.timer.Stop()

	def updateToolbar(self):
		self.gcodeViewButton.Show(self.gcode != None)
		self.mixedViewButton.Show(self.gcode != None)
		self.layerSpin.Show(self.glCanvas.viewMode == "GCode" or self.glCanvas.viewMode == "Mixed")
		if self.gcode != None:
			self.layerSpin.SetRange(1, len(self.gcode.layerList) - 1)
		self.toolbar.Realize()
		self.Update()
	
	def OnViewChange(self):
		if self.normalViewButton.GetValue():
			self.glCanvas.viewMode = "Normal"
		elif self.transparentViewButton.GetValue():
			self.glCanvas.viewMode = "Transparent"
		elif self.xrayViewButton.GetValue():
			self.glCanvas.viewMode = "X-Ray"
		elif self.gcodeViewButton.GetValue():
			self.glCanvas.viewMode = "GCode"
		elif self.mixedViewButton.GetValue():
			self.glCanvas.viewMode = "Mixed"
		self.glCanvas.drawBorders = self.showBorderButton.GetValue()
		self.glCanvas.drawSteepOverhang = self.showSteepOverhang.GetValue()
		self.updateToolbar()
		self.glCanvas.Refresh()
	
	def updateModelTransform(self, f=0):
		if len(self.objectList) < 1 or self.objectList[0].mesh == None:
			return
		
		rotate = profile.getProfileSettingFloat('model_rotate_base')
		mirrorX = profile.getProfileSetting('flip_x') == 'True'
		mirrorY = profile.getProfileSetting('flip_y') == 'True'
		mirrorZ = profile.getProfileSetting('flip_z') == 'True'
		swapXZ = profile.getProfileSetting('swap_xz') == 'True'
		swapYZ = profile.getProfileSetting('swap_yz') == 'True'

		for obj in self.objectList:
			if obj.mesh == None:
				continue
			obj.mesh.setRotateMirror(rotate, mirrorX, mirrorY, mirrorZ, swapXZ, swapYZ)
		
		minV = self.objectList[0].mesh.getMinimum()
		maxV = self.objectList[0].mesh.getMaximum()
		objectsBounderyCircleSize = self.objectList[0].mesh.bounderyCircleSize
		for obj in self.objectList:
			if obj.mesh == None:
				continue

			obj.mesh.getMinimumZ()
			minV = numpy.minimum(minV, obj.mesh.getMinimum())
			maxV = numpy.maximum(maxV, obj.mesh.getMaximum())
			objectsBounderyCircleSize = max(objectsBounderyCircleSize, obj.mesh.bounderyCircleSize)

		self.objectsMaxV = maxV
		self.objectsMinV = minV
		self.objectsBounderyCircleSize = objectsBounderyCircleSize
		for obj in self.objectList:
			if obj.mesh == None:
				continue

			obj.mesh.vertexes -= numpy.array([minV[0] + (maxV[0] - minV[0]) / 2, minV[1] + (maxV[1] - minV[1]) / 2, minV[2]])
			#for v in obj.mesh.vertexes:
			#	v[2] -= minV[2]
			#	v[0] -= minV[0] + (maxV[0] - minV[0]) / 2
			#	v[1] -= minV[1] + (maxV[1] - minV[1]) / 2
			obj.mesh.getMinimumZ()
			obj.dirty = True

		scale = profile.getProfileSettingFloat('model_scale')
		size = (self.objectsMaxV - self.objectsMinV) * scale
		self.toolbarInfo.SetValue('%0.1f %0.1f %0.1f' % (size[0], size[1], size[2]))

		self.glCanvas.Refresh()
	
	def updateProfileToControls(self):
		self.scale.SetValue(profile.getProfileSetting('model_scale'))
		self.rotate.SetValue(profile.getProfileSettingFloat('model_rotate_base'))
		self.mirrorX.SetValue(profile.getProfileSetting('flip_x') == 'True')
		self.mirrorY.SetValue(profile.getProfileSetting('flip_y') == 'True')
		self.mirrorZ.SetValue(profile.getProfileSetting('flip_z') == 'True')
		self.swapXZ.SetValue(profile.getProfileSetting('swap_xz') == 'True')
		self.swapYZ.SetValue(profile.getProfileSetting('swap_yz') == 'True')
		self.updateModelTransform()
		self.glCanvas.updateProfileToControls()

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
		self.gcodeDisplayList = None
		self.gcodeDisplayListMade = None
		self.gcodeDisplayListCount = 0
		self.objColor = [[1.0, 0.8, 0.6, 1.0], [0.2, 1.0, 0.1, 1.0], [1.0, 0.2, 0.1, 1.0], [0.1, 0.2, 1.0, 1.0]]
		self.oldX = 0
		self.oldY = 0
		self.dragType = ''
		self.tempRotate = 0
	
	def updateProfileToControls(self):
		self.objColor[0] = profile.getPreferenceColour('model_colour')
		self.objColor[1] = profile.getPreferenceColour('model_colour2')
		self.objColor[2] = profile.getPreferenceColour('model_colour3')
		self.objColor[3] = profile.getPreferenceColour('model_colour4')

	def OnMouseMotion(self,e):
		cursorXY = 100000
		radius = 0
		if self.parent.objectsMaxV != None:
			radius = self.parent.objectsBounderyCircleSize * profile.getProfileSettingFloat('model_scale')
			
			p0 = numpy.array(gluUnProject(e.GetX(), self.viewport[1] + self.viewport[3] - e.GetY(), 0, self.modelMatrix, self.projMatrix, self.viewport))
			p1 = numpy.array(gluUnProject(e.GetX(), self.viewport[1] + self.viewport[3] - e.GetY(), 1, self.modelMatrix, self.projMatrix, self.viewport))
			cursorZ0 = p0 - (p1 - p0) * (p0[2] / (p1[2] - p0[2]))
			cursorXY = math.sqrt((cursorZ0[0] * cursorZ0[0]) + (cursorZ0[1] * cursorZ0[1]))
			if cursorXY >= radius * 1.1 and cursorXY <= radius * 1.3:
				self.SetCursor(wx.StockCursor(wx.CURSOR_SIZING))
			else:
				self.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))

		if e.Dragging() and e.LeftIsDown():
			if self.dragType == '':
				#Define the drag type depending on the cursor position.
				if cursorXY >= radius * 1.1 and cursorXY <= radius * 1.3:
					self.dragType = 'modelRotate'
					self.dragStart = math.atan2(cursorZ0[0], cursorZ0[1])
				else:
					self.dragType = 'viewRotate'
				
			if self.dragType == 'viewRotate':
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
			elif self.dragType == 'modelRotate':
				angle = math.atan2(cursorZ0[0], cursorZ0[1])
				diff = self.dragStart - angle
				self.tempRotate = diff * 180 / math.pi
				rot = profile.getProfileSettingFloat('model_rotate_base')
				self.tempRotate = round((self.tempRotate + rot) / 15) * 15 - rot
			#Workaround for buggy ATI cards.
			size = self.GetSizeTuple()
			self.SetSize((size[0]+1, size[1]))
			self.SetSize((size[0], size[1]))
			self.Refresh()
		else:
			if self.tempRotate != 0:
				newRotation = profile.getProfileSettingFloat('model_rotate_base') + self.tempRotate
				while newRotation >= 360:
					newRotation -= 360
				while newRotation < 0:
					newRotation += 360
				profile.putProfileSetting('model_rotate_base', newRotation)
				self.parent.rotate.SetValue(newRotation)
				self.parent.updateModelTransform()
				self.tempRotate = 0
				
			self.dragType = ''
		if e.Dragging() and e.RightIsDown():
			self.zoom += e.GetY() - self.oldY
			if self.zoom < 1:
				self.zoom = 1
			if self.zoom > 500:
				self.zoom = 500
			self.Refresh()
		self.oldX = e.GetX()
		self.oldY = e.GetY()

		#self.Refresh()
		
	
	def OnMouseWheel(self,e):
		self.zoom *= 1.0 - float(e.GetWheelRotation() / e.GetWheelDelta()) / 10.0
		if self.zoom < 1.0:
			self.zoom = 1.0
		if self.zoom > 500:
			self.zoom = 500
		self.Refresh()
	
	def OnEraseBackground(self,event):
		#Workaround for windows background redraw flicker.
		pass
	
	def OnSize(self,e):
		self.Refresh()

	def OnPaint(self,e):
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
			if self.viewMode == "GCode" or self.viewMode == "Mixed":
				if self.parent.gcode != None and len(self.parent.gcode.layerList) > self.parent.layerSpin.GetValue() and len(self.parent.gcode.layerList[self.parent.layerSpin.GetValue()]) > 0:
					glTranslate(0,0,-self.parent.gcode.layerList[self.parent.layerSpin.GetValue()][0].list[-1].z)
			else:
				if self.parent.objectsMaxV != None:
					glTranslate(0,0,-(self.parent.objectsMaxV[2]-self.parent.objectsMinV[2]) * profile.getProfileSettingFloat('model_scale') / 2)
		else:
			glTranslate(self.offsetX, self.offsetY, 0)

		self.viewport = glGetIntegerv(GL_VIEWPORT);
		self.modelMatrix = glGetDoublev(GL_MODELVIEW_MATRIX);
		self.projMatrix = glGetDoublev(GL_PROJECTION_MATRIX);

		glTranslate(-self.parent.machineCenter.x, -self.parent.machineCenter.y, 0)

		self.OnDraw()
		self.SwapBuffers()

	def OnDraw(self):
		machineSize = self.parent.machineSize

		if self.parent.gcode != None and self.parent.gcodeDirty:
			if self.gcodeDisplayListCount < len(self.parent.gcode.layerList) or self.gcodeDisplayList == None:
				if self.gcodeDisplayList != None:
					glDeleteLists(self.gcodeDisplayList, self.gcodeDisplayListCount)
				self.gcodeDisplayList = glGenLists(len(self.parent.gcode.layerList));
				self.gcodeDisplayListCount = len(self.parent.gcode.layerList)
			self.parent.gcodeDirty = False
			self.gcodeDisplayListMade = 0
		
		if self.parent.gcode != None and self.gcodeDisplayListMade < len(self.parent.gcode.layerList):
			glNewList(self.gcodeDisplayList + self.gcodeDisplayListMade, GL_COMPILE)
			opengl.DrawGCodeLayer(self.parent.gcode.layerList[self.gcodeDisplayListMade])
			glEndList()
			self.gcodeDisplayListMade += 1
			wx.CallAfter(self.Refresh)
		
		glPushMatrix()
		glTranslate(self.parent.machineCenter.x, self.parent.machineCenter.y, 0)
		for obj in self.parent.objectList:
			if obj.mesh == None:
				continue
			if obj.displayList == None:
				obj.displayList = glGenLists(1)
				obj.steepDisplayList = glGenLists(1)
			if obj.dirty:
				obj.dirty = False
				glNewList(obj.displayList, GL_COMPILE)
				opengl.DrawMesh(obj.mesh)
				glEndList()
				glNewList(obj.steepDisplayList, GL_COMPILE)
				opengl.DrawMeshSteep(obj.mesh, 60)
				glEndList()
			
			if self.viewMode == "Mixed":
				glDisable(GL_BLEND)
				glColor3f(0.0,0.0,0.0)
				self.drawModel(obj)
				glColor3f(1.0,1.0,1.0)
				glClear(GL_DEPTH_BUFFER_BIT)
		
		glPopMatrix()
		
		if self.parent.gcode != None and (self.viewMode == "GCode" or self.viewMode == "Mixed"):
			glEnable(GL_COLOR_MATERIAL)
			glEnable(GL_LIGHTING)
			drawUpToLayer = min(self.gcodeDisplayListMade, self.parent.layerSpin.GetValue() + 1)
			starttime = time.time()
			for i in xrange(drawUpToLayer - 1, -1, -1):
				c = 1.0
				if i < self.parent.layerSpin.GetValue():
					c = 0.9 - (drawUpToLayer - i) * 0.1
					if c < 0.4:
						c = (0.4 + c) / 2
					if c < 0.1:
						c = 0.1
				glLightfv(GL_LIGHT0, GL_DIFFUSE, [0,0,0,0])
				glLightfv(GL_LIGHT0, GL_AMBIENT, [c,c,c,c])
				glCallList(self.gcodeDisplayList + i)
				if time.time() - starttime > 0.1:
					break

			glDisable(GL_LIGHTING)
			glDisable(GL_COLOR_MATERIAL)
			glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT, [0.2, 0.2, 0.2, 1.0]);
			glMaterialfv(GL_FRONT_AND_BACK, GL_DIFFUSE, [0.8, 0.8, 0.8, 1.0]);

		glColor3f(1.0,1.0,1.0)
		glPushMatrix()
		glTranslate(self.parent.machineCenter.x, self.parent.machineCenter.y, 0)
		for obj in self.parent.objectList:
			if obj.mesh == None:
				continue
			
			if self.viewMode == "Transparent" or self.viewMode == "Mixed":
				glLightfv(GL_LIGHT0, GL_DIFFUSE, map(lambda x: x / 2, self.objColor[self.parent.objectList.index(obj)]))
				glLightfv(GL_LIGHT0, GL_AMBIENT, map(lambda x: x / 10, self.objColor[self.parent.objectList.index(obj)]))
				#If we want transparent, then first render a solid black model to remove the printer size lines.
				if self.viewMode != "Mixed":
					glDisable(GL_BLEND)
					glColor3f(0.0,0.0,0.0)
					self.drawModel(obj)
					glColor3f(1.0,1.0,1.0)
				#After the black model is rendered, render the model again but now with lighting and no depth testing.
				glDisable(GL_DEPTH_TEST)
				glEnable(GL_LIGHTING)
				glEnable(GL_BLEND)
				glBlendFunc(GL_ONE, GL_ONE)
				glEnable(GL_LIGHTING)
				self.drawModel(obj)
				glEnable(GL_DEPTH_TEST)
			elif self.viewMode == "X-Ray":
				glColorMask(GL_FALSE, GL_FALSE, GL_FALSE, GL_FALSE)
				glDisable(GL_LIGHTING)
				glDisable(GL_DEPTH_TEST)
				glEnable(GL_STENCIL_TEST)
				glStencilFunc(GL_ALWAYS, 1, 1)
				glStencilOp(GL_INCR, GL_INCR, GL_INCR)
				self.drawModel(obj)
				glStencilOp (GL_KEEP, GL_KEEP, GL_KEEP);
				
				glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)
				glStencilFunc(GL_EQUAL, 0, 1)
				glColor(1, 1, 1)
				self.drawModel(obj)
				glStencilFunc(GL_EQUAL, 1, 1)
				glColor(1, 0, 0)
				self.drawModel(obj)

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

				glDisable(GL_STENCIL_TEST)
				glEnable(GL_DEPTH_TEST)
				
				#Fix the depth buffer
				glColorMask(GL_FALSE, GL_FALSE, GL_FALSE, GL_FALSE)
				self.drawModel(obj)
				glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)
			elif self.viewMode == "Normal":
				glLightfv(GL_LIGHT0, GL_DIFFUSE, self.objColor[self.parent.objectList.index(obj)])
				glLightfv(GL_LIGHT0, GL_AMBIENT, map(lambda x: x * 0.4, self.objColor[self.parent.objectList.index(obj)]))
				glEnable(GL_LIGHTING)
				self.drawModel(obj)

			if self.drawBorders and (self.viewMode == "Normal" or self.viewMode == "Transparent" or self.viewMode == "X-Ray"):
				glEnable(GL_DEPTH_TEST)
				glDisable(GL_LIGHTING)
				glColor3f(1,1,1)
				glPushMatrix()
				modelScale = profile.getProfileSettingFloat('model_scale')
				glScalef(modelScale, modelScale, modelScale)
				opengl.DrawMeshOutline(obj.mesh)
				glPopMatrix()
			
			if self.drawSteepOverhang:
				glDisable(GL_LIGHTING)
				glColor3f(1,1,1)
				glPushMatrix()
				modelScale = profile.getProfileSettingFloat('model_scale')
				glScalef(modelScale, modelScale, modelScale)
				glCallList(obj.steepDisplayList)
				glPopMatrix()
		
		glPopMatrix()	
		if self.viewMode == "Normal" or self.viewMode == "Transparent" or self.viewMode == "X-Ray":
			glDisable(GL_LIGHTING)
			glDisable(GL_DEPTH_TEST)
			glDisable(GL_BLEND)
			glColor3f(1,0,0)
			glBegin(GL_LINES)
			for err in self.parent.errorList:
				glVertex3f(err[0].x, err[0].y, err[0].z)
				glVertex3f(err[1].x, err[1].y, err[1].z)
			glEnd()
			glEnable(GL_DEPTH_TEST)

		glPushMatrix()
		glTranslate(self.parent.machineCenter.x, self.parent.machineCenter.y, 0)
		
		#Draw the rotate circle
		if self.parent.objectsMaxV != None:
			glDisable(GL_LIGHTING)
			glDisable(GL_CULL_FACE)
			glEnable(GL_BLEND)
			glRotate(self.tempRotate + profile.getProfileSettingFloat('model_rotate_base'), 0, 0, 1)
			radius = self.parent.objectsBounderyCircleSize * profile.getProfileSettingFloat('model_scale')
			glScalef(radius, radius, 1)
			glBegin(GL_TRIANGLE_STRIP)
			for i in xrange(0, 64+1):
				f = i if i < 64/2 else 64 - i
				glColor4ub(255,int(f*255/(64/2)),0,255)
				glVertex3f(1.1 * math.cos(i/32.0*math.pi), 1.1 * math.sin(i/32.0*math.pi),0.1)
				glColor4ub(  0,128,0,255)
				glVertex3f(1.3 * math.cos(i/32.0*math.pi), 1.3 * math.sin(i/32.0*math.pi),0.1)
			glEnd()
			glBegin(GL_TRIANGLES)
			glColor4ub(0,0,0,192)
			glVertex3f(1, 0.1,0.15)
			glVertex3f(1,-0.1,0.15)
			glVertex3f(1.4,0,0.15)
			glEnd()
			glEnable(GL_CULL_FACE)
		
		glPopMatrix()

		opengl.DrawMachine(machineSize)
		
		glFlush()
	
	def drawModel(self, obj):
		multiX = 1 #int(profile.getProfileSetting('model_multiply_x'))
		multiY = 1 #int(profile.getProfileSetting('model_multiply_y'))
		modelScale = profile.getProfileSettingFloat('model_scale')
		modelSize = (obj.mesh.getMaximum() - obj.mesh.getMinimum()) * modelScale
		glPushMatrix()
		glRotate(self.tempRotate, 0, 0, 1)
		glTranslate(-(modelSize[0]+10)*(multiX-1)/2,-(modelSize[1]+10)*(multiY-1)/2, 0)
		for mx in xrange(0, multiX):
			for my in xrange(0, multiY):
				glPushMatrix()
				glTranslate((modelSize[0]+10)*mx,(modelSize[1]+10)*my, 0)
				glScalef(modelScale, modelScale, modelScale)
				glCallList(obj.displayList)
				glPopMatrix()
		glPopMatrix()

