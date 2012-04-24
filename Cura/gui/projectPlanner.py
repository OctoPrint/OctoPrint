from __future__ import absolute_import
import __init__

import wx, os, platform, types, webbrowser, math, subprocess, threading, time
import ConfigParser

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
from gui import icon
from util import profile
from util import util3d
from util import stl
from util import sliceRun

class Action():
	pass

class projectPlanner(wx.Frame):
	"Main user interface window"
	def __init__(self):
		super(projectPlanner, self).__init__(None, title='Cura - Project Planner')
		
		self.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE))
		wx.EVT_CLOSE(self, self.OnClose)
		#self.SetIcon(icon.getMainIcon())
		
		self.list = []
		self.selection = None

		self.machineSize = util3d.Vector3(float(profile.getPreference('machine_width')), float(profile.getPreference('machine_depth')), float(profile.getPreference('machine_height')))
		self.headSizeMin = util3d.Vector3(70,16,0)
		self.headSizeMax = util3d.Vector3(16,35,0)

		self.toolbar = toolbarUtil.Toolbar(self)

		toolbarUtil.NormalButton(self.toolbar, self.OnLoadProject, 'open.png', 'Open project')
		toolbarUtil.NormalButton(self.toolbar, self.OnSaveProject, 'save.png', 'Save project')
		self.toolbar.AddSeparator()
		group = []
		toolbarUtil.RadioButton(self.toolbar, group, 'object-3d-on.png', 'object-3d-off.png', '3D view', callback=self.On3DClick)
		toolbarUtil.RadioButton(self.toolbar, group, 'object-top-on.png', 'object-top-off.png', 'Topdown view', callback=self.OnTopClick).SetValue(True)
		self.toolbar.AddSeparator()
		toolbarUtil.NormalButton(self.toolbar, self.OnQuit, 'exit.png', 'Close project planner')
		
		self.toolbar.Realize()
		
		sizer = wx.GridBagSizer(2,2)
		self.SetSizer(sizer)
		self.preview = PreviewGLCanvas(self)
		self.listbox = wx.ListBox(self, -1, choices=[])
		self.addButton = wx.Button(self, -1, "Add")
		self.remButton = wx.Button(self, -1, "Remove")
		self.sliceButton = wx.Button(self, -1, "Slice")
		self.autoPlaceButton = wx.Button(self, -1, "Auto Place")
		
		sizer.Add(self.toolbar, (0,0), span=(1,3), flag=wx.EXPAND)
		sizer.Add(self.preview, (1,0), span=(4,1), flag=wx.EXPAND)
		sizer.Add(self.listbox, (1,1), span=(1,2), flag=wx.EXPAND)
		sizer.Add(self.addButton, (2,1), span=(1,1))
		sizer.Add(self.remButton, (2,2), span=(1,1))
		sizer.Add(self.sliceButton, (3,1), span=(1,1))
		sizer.Add(self.autoPlaceButton, (3,2), span=(1,1))
		sizer.AddGrowableCol(0)
		sizer.AddGrowableRow(1)
		
		self.addButton.Bind(wx.EVT_BUTTON, self.OnAddModel)
		self.remButton.Bind(wx.EVT_BUTTON, self.OnRemModel)
		self.sliceButton.Bind(wx.EVT_BUTTON, self.OnSlice)
		self.autoPlaceButton.Bind(wx.EVT_BUTTON, self.OnAutoPlace)
		self.listbox.Bind(wx.EVT_LISTBOX, self.OnListSelect)

		panel = wx.Panel(self, -1)
		sizer.Add(panel, (4,1), span=(1,2))
		
		sizer = wx.GridBagSizer(2,2)
		panel.SetSizer(sizer)
		
		self.scaleCtrl = wx.TextCtrl(panel, -1, '')
		self.rotateCtrl = wx.SpinCtrl(panel, -1, '', size=(21*4,21), style=wx.SP_ARROW_KEYS)
		self.rotateCtrl.SetRange(0, 360)

		sizer.Add(wx.StaticText(panel, -1, 'Scale'), (0,0), flag=wx.ALIGN_CENTER_VERTICAL)
		sizer.Add(self.scaleCtrl, (0,1), flag=wx.ALIGN_BOTTOM|wx.EXPAND)
		sizer.Add(wx.StaticText(panel, -1, 'Rotate'), (1,0), flag=wx.ALIGN_CENTER_VERTICAL)
		sizer.Add(self.rotateCtrl, (1,1), flag=wx.ALIGN_BOTTOM|wx.EXPAND)

		self.scaleCtrl.Bind(wx.EVT_TEXT, self.OnScaleChange)
		self.rotateCtrl.Bind(wx.EVT_SPINCTRL, self.OnRotateChange)

		self.SetSize((800,600))

	def OnClose(self, e):
		self.Destroy()

	def OnQuit(self, e):
		self.Close()
	
	def OnSaveProject(self, e):
		dlg=wx.FileDialog(self, "Save project file", os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_SAVE)
		dlg.SetWildcard("Project files (*.curaproject)|*.curaproject")
		if dlg.ShowModal() == wx.ID_OK:
			cp = ConfigParser.ConfigParser()
			i = 0
			for item in self.list:
				section = 'model_%d' % (i)
				cp.add_section(section)
				cp.set(section, 'filename', item.filename.encode("utf-8"))
				cp.set(section, 'centerX', str(item.centerX))
				cp.set(section, 'centerY', str(item.centerY))
				cp.set(section, 'scale', str(item.scale))
				cp.set(section, 'rotate', str(item.rotate))
				cp.set(section, 'flipX', str(item.flipX))
				cp.set(section, 'flipY', str(item.flipY))
				cp.set(section, 'flipZ', str(item.flipZ))
				cp.set(section, 'swapXZ', str(item.swapXZ))
				cp.set(section, 'swapYZ', str(item.swapYZ))
				i += 1
			cp.write(open(dlg.GetPath(), "w"))
		dlg.Destroy()

	def OnLoadProject(self, e):
		dlg=wx.FileDialog(self, "Open project file", os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
		dlg.SetWildcard("Project files (*.curaproject)|*.curaproject")
		if dlg.ShowModal() == wx.ID_OK:
			cp = ConfigParser.ConfigParser()
			cp.read(dlg.GetPath())
			self.list = []
			self.listbox.Clear()
			i = 0
			while cp.has_section('model_%d' % (i)):
				section = 'model_%d' % (i)
				
				item = stl.stlModel()
				item.filename = unicode(cp.get(section, 'filename'), "utf-8")
				self.loadModelFile(item)
				item.centerX = float(cp.get(section, 'centerX'))
				item.centerY = float(cp.get(section, 'centerY'))
				item.scale = float(cp.get(section, 'scale'))
				item.rotate = float(cp.get(section, 'rotate'))
				cp.get(section, 'flipX')
				cp.get(section, 'flipY')
				cp.get(section, 'flipZ')
				cp.get(section, 'swapXZ')
				cp.get(section, 'swapYZ')
				i += 1
				
				self.list.append(item)
				self.listbox.AppendAndEnsureVisible(os.path.split(item.filename)[1])
			
			self.listbox.SetSelection(len(self.list)-1)
			self.OnListSelect(None)

		dlg.Destroy()

	def On3DClick(self):
		self.preview.yaw = 30
		self.preview.pitch = 60
		self.preview.zoom = 300
		self.preview.view3D = True
		self.preview.Refresh()

	def OnTopClick(self):
		self.preview.view3D = False
		self.preview.zoom = self.machineSize.x / 2 + 10
		self.preview.offsetX = 0
		self.preview.offsetY = 0
		self.preview.Refresh()

	def OnListSelect(self, e):
		if self.listbox.GetSelection() == -1:
			return
		self.selection = self.list[self.listbox.GetSelection()]
		self.scaleCtrl.SetValue(str(self.selection.scale))
		self.rotateCtrl.SetValue(int(self.selection.rotate))
		self.preview.Refresh()

	def OnAddModel(self, e):
		dlg=wx.FileDialog(self, "Open file to print", os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST|wx.FD_MULTIPLE)
		dlg.SetWildcard("STL files (*.stl)|*.stl;*.STL")
		if dlg.ShowModal() == wx.ID_OK:
			for filename in dlg.GetPaths():
				item = stl.stlModel()
				item.filename=filename
				profile.putPreference('lastFile', item.filename)
				if not(os.path.exists(item.filename)):
					return
				self.loadModelFile(item)
				self.list.append(item)
				self.listbox.AppendAndEnsureVisible(os.path.split(item.filename)[1])
				self.listbox.SetSelection(len(self.list)-1)
				self.OnListSelect(None)
		dlg.Destroy()
	
	def OnRemModel(self, e):
		if self.selection == None:
			return
		self.list.remove(self.selection)
		i = self.listbox.GetSelection()
		self.listbox.Delete(i)
		if len(self.list) > i:
			self.listbox.SetSelection(i)
		elif len(self.list) > 0:
			self.listbox.SetSelection(len(self.list) - 1)
		self.selection = None
		self.OnListSelect(None)
		self.preview.Refresh()
	
	def OnAutoPlace(self, e):
		bestAllowedSize = int(self.machineSize.y)
		bestArea = self._doAutoPlace(bestAllowedSize)
		for i in xrange(10, int(self.machineSize.y), 10):
			area = self._doAutoPlace(i)
			if area < bestArea:
				bestAllowedSize = i
				bestArea = area
		self._doAutoPlace(bestAllowedSize)
		self.preview.Refresh()
	
	def _doAutoPlace(self, allowedSizeY):
		extraSizeMin = self.headSizeMin
		extraSizeMax = self.headSizeMax
		if profile.getProfileSettingFloat('skirt_line_count') > 0:
			skirtSize = profile.getProfileSettingFloat('skirt_line_count') * profile.calculateEdgeWidth() + profile.getProfileSettingFloat('skirt_gap')
			extraSizeMin = extraSizeMin - util3d.Vector3(skirtSize, skirtSize, 0)
			extraSizeMax = extraSizeMax + util3d.Vector3(skirtSize, skirtSize, 0)

		posX = self.machineSize.x
		posY = 0
		minX = self.machineSize.x
		minY = self.machineSize.y
		maxX = 0
		maxY = 0
		dirX = -1
		dirY = 1
		for item in self.list:
			item.centerX = posX + item.getMaximum().x * item.scale * dirX
			item.centerY = posY + item.getMaximum().y * item.scale * dirY
			if item.centerY + item.getSize().y >= allowedSizeY:
				posX = minX - extraSizeMax.x - 1
				posY = 0
				item.centerX = posX + item.getMaximum().x * item.scale * dirX
				item.centerY = posY + item.getMaximum().y * item.scale * dirY
			posY += item.getSize().y  * item.scale * dirY + extraSizeMin.y + 1
			minX = min(minX, item.centerX - item.getSize().x * item.scale / 2)
			minY = min(minY, item.centerY - item.getSize().y * item.scale / 2)
			maxX = max(maxX, item.centerX + item.getSize().x * item.scale / 2)
			maxY = max(maxY, item.centerY + item.getSize().y * item.scale / 2)
		
		for item in self.list:
			item.centerX -= minX / 2
			item.centerY += (self.machineSize.y - maxY) / 2
		
		if minX < 0:
			return ((maxX - minX) + (maxY - minY)) * 100
		
		return (maxX - minX) + (maxY - minY)

	def OnSlice(self, e):
		oldProfile = profile.getGlobalProfileString()
		
		put = profile.putProfileSetting

		put('model_multiply_x', '1')
		put('model_multiply_y', '1')
		put('enable_raft', 'False')
		put('add_start_end_gcode', 'False')
		put('gcode_extension', 'project_tmp')
		
		clearZ = 0
		actionList = []
		for item in self.list:
			put('machine_center_x', item.centerX)
			put('machine_center_y', item.centerY)
			put('model_scale', item.scale)
			put('flip_x', item.flipX)
			put('flip_y', item.flipY)
			put('flip_z', item.flipZ)
			put('model_rotate_base', item.rotate)
			put('swap_xz', item.swapXZ)
			put('swap_yz', item.swapYZ)
			
			action = Action()
			action.sliceCmd = sliceRun.getSliceCommand(item.filename)
			action.centerX = item.centerX
			action.centerY = item.centerY
			action.filename = item.filename
			clearZ = max(clearZ, item.getMaximum().z * item.scale)
			action.clearZ = clearZ
			actionList.append(action)
		
		#Restore the old profile.
		profile.loadGlobalProfileFromString(oldProfile)
		
		dlg=wx.FileDialog(self, "Save project gcode file", os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_SAVE)
		dlg.SetWildcard("GCode file (*.gcode)|*.gcode")
		if dlg.ShowModal() != wx.ID_OK:
			dlg.Destroy()
			return
		resultFilename = dlg.GetPath()
		dlg.Destroy()
		
		pspw = ProjectSliceProgressWindow(actionList, resultFilename)
		pspw.Centre()
		pspw.Show(True)
	
	def loadModelFile(self, item):
		item.load(item.filename)
		item.origonalVertexes = list(item.vertexes)
		for i in xrange(0, len(item.origonalVertexes)):
			item.origonalVertexes[i] = item.origonalVertexes[i].copy()
		item.getMinimumZ()
		
		item.centerX = -item.getMinimum().x + 5
		item.centerY = -item.getMinimum().y + 5
		item.scale = 1.0
		item.rotate = 0.0
		item.flipX = False
		item.flipY = False
		item.flipZ = False
		item.swapXZ = False
		item.swapYZ = False
		
		item.modelDisplayList = None
		item.modelDirty = False
		
		self.updateModelTransform(item)

		item.centerX = -item.getMinimum().x + 5
		item.centerY = -item.getMinimum().y + 5

	def OnScaleChange(self, e):
		if self.selection == None:
			return
		try:
			self.selection.scale = float(self.scaleCtrl.GetValue())
		except ValueError:
			self.selection.scale = 1.0
		self.preview.Refresh()
	
	def OnRotateChange(self, e):
		if self.selection == None:
			return
		self.selection.rotate = float(self.rotateCtrl.GetValue())
		self.updateModelTransform(self.selection)

	def updateModelTransform(self, item):
		rotate = item.rotate / 180.0 * math.pi
		scaleX = 1.0
		scaleY = 1.0
		scaleZ = 1.0
		if item.flipX:
			scaleX = -scaleX
		if item.flipY:
			scaleY = -scaleY
		if item.flipZ:
			scaleZ = -scaleZ
		swapXZ = item.swapXZ
		swapYZ = item.swapYZ
		mat00 = math.cos(rotate) * scaleX
		mat01 =-math.sin(rotate) * scaleY
		mat10 = math.sin(rotate) * scaleX
		mat11 = math.cos(rotate) * scaleY
		
		for i in xrange(0, len(item.origonalVertexes)):
			x = item.origonalVertexes[i].x
			y = item.origonalVertexes[i].y
			z = item.origonalVertexes[i].z
			if swapXZ:
				x, z = z, x
			if swapYZ:
				y, z = z, y
			item.vertexes[i].x = x * mat00 + y * mat01
			item.vertexes[i].y = x * mat10 + y * mat11
			item.vertexes[i].z = z * scaleZ

		for face in item.faces:
			v1 = face.v[0]
			v2 = face.v[1]
			v3 = face.v[2]
			face.normal = (v2 - v1).cross(v3 - v1)
			face.normal.normalize()

		self.moveModel(item)
	
	def moveModel(self, item):
		minZ = item.getMinimumZ()
		min = item.getMinimum()
		max = item.getMaximum()
		for v in item.vertexes:
			v.z -= minZ
			v.x -= min.x + (max.x - min.x) / 2
			v.y -= min.y + (max.y - min.y) / 2
		item.getMinimumZ()
		item.modelDirty = True
		self.preview.Refresh()

class PreviewGLCanvas(glcanvas.GLCanvas):
	def __init__(self, parent):
		attribList = (glcanvas.WX_GL_RGBA, glcanvas.WX_GL_DOUBLEBUFFER, glcanvas.WX_GL_DEPTH_SIZE, 24, glcanvas.WX_GL_STENCIL_SIZE, 8)
		glcanvas.GLCanvas.__init__(self, parent, attribList = attribList)
		self.parent = parent
		self.context = glcanvas.GLContext(self)
		wx.EVT_PAINT(self, self.OnPaint)
		wx.EVT_SIZE(self, self.OnSize)
		wx.EVT_ERASE_BACKGROUND(self, self.OnEraseBackground)
		wx.EVT_LEFT_DOWN(self, self.OnMouseLeftDown)
		wx.EVT_MOTION(self, self.OnMouseMotion)
		wx.EVT_MOUSEWHEEL(self, self.OnMouseWheel)
		self.yaw = 30
		self.pitch = 60
		self.zoom = self.parent.machineSize.x / 2 + 10
		self.offsetX = 0
		self.offsetY = 0
		self.view3D = False
		self.allowDrag = False
	
	def OnMouseLeftDown(self,e):
		self.allowDrag = True
	
	def OnMouseMotion(self,e):
		if self.allowDrag and e.Dragging() and e.LeftIsDown():
			if self.view3D:
				self.yaw += e.GetX() - self.oldX
				self.pitch -= e.GetY() - self.oldY
				if self.pitch > 170:
					self.pitch = 170
				if self.pitch < 10:
					self.pitch = 10
			else:
				#self.offsetX += float(e.GetX() - self.oldX) * self.zoom / self.GetSize().GetHeight() * 2
				#self.offsetY -= float(e.GetY() - self.oldY) * self.zoom / self.GetSize().GetHeight() * 2
				item = self.parent.selection
				if item != None:
					item.centerX += float(e.GetX() - self.oldX) * self.zoom / self.GetSize().GetHeight() * 2
					item.centerY -= float(e.GetY() - self.oldY) * self.zoom / self.GetSize().GetHeight() * 2
					if item.centerX < -item.getMinimum().x * item.scale:
						item.centerX = -item.getMinimum().x * item.scale
					if item.centerY < -item.getMinimum().y * item.scale:
						item.centerY = -item.getMinimum().y * item.scale
					if item.centerX > self.parent.machineSize.x - item.getMaximum().x * item.scale:
						item.centerX = self.parent.machineSize.x - item.getMaximum().x * item.scale
					if item.centerY > self.parent.machineSize.y - item.getMaximum().y * item.scale:
						item.centerY = self.parent.machineSize.y - item.getMaximum().y * item.scale
			self.Refresh()
		else:
			self.allowDrag = False
		if e.Dragging() and e.RightIsDown():
			if self.view3D:
				self.zoom += e.GetY() - self.oldY
				if self.zoom < 1:
					self.zoom = 1
			self.Refresh()
		self.oldX = e.GetX()
		self.oldY = e.GetY()
	
	def OnMouseWheel(self,e):
		if self.view3D:
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
			if False: #self.parent.triangleMesh != None:
				glTranslate(0,0,-self.parent.triangleMesh.getMaximum().z / 2)
		else:
			glScale(1.0/self.zoom, 1.0/self.zoom, 1.0)
			glTranslate(self.offsetX, self.offsetY, 0.0)
		glTranslate(-self.parent.machineSize.x/2, -self.parent.machineSize.y/2, 0)

		self.OnDraw()
		self.SwapBuffers()

	def OnDraw(self):
		machineSize = self.parent.machineSize
		opengl.DrawMachine(machineSize)
		extraSizeMin = self.parent.headSizeMin
		extraSizeMax = self.parent.headSizeMax
		if profile.getProfileSettingFloat('skirt_line_count') > 0:
			skirtSize = profile.getProfileSettingFloat('skirt_line_count') * profile.calculateEdgeWidth() + profile.getProfileSettingFloat('skirt_gap')
			extraSizeMin = extraSizeMin - util3d.Vector3(skirtSize, skirtSize, 0)
			extraSizeMax = extraSizeMax + util3d.Vector3(skirtSize, skirtSize, 0)

		for item in self.parent.list:
			item.validPlacement = True
			item.gotHit = False
		
		for idx1 in xrange(0, len(self.parent.list)):
			item = self.parent.list[idx1]
			iMin1 = item.getMinimum() * item.scale + util3d.Vector3(item.centerX, item.centerY, 0) - extraSizeMin
			iMax1 = item.getMaximum() * item.scale + util3d.Vector3(item.centerX, item.centerY, 0) + extraSizeMax
			for idx2 in xrange(0, idx1):
				item2 = self.parent.list[idx2]
				iMin2 = item2.getMinimum() * item2.scale + util3d.Vector3(item2.centerX, item2.centerY, 0)
				iMax2 = item2.getMaximum() * item2.scale + util3d.Vector3(item2.centerX, item2.centerY, 0)
				if item != item2 and iMax1.x >= iMin2.x and iMin1.x <= iMax2.x and iMax1.y >= iMin2.y and iMin1.y <= iMax2.y:
					item.validPlacement = False
					item2.gotHit = True
		
		seenSelected = False
		for item in self.parent.list:
			if item == self.parent.selection:
				seenSelected = True
			if item.modelDisplayList == None:
				item.modelDisplayList = glGenLists(1);
			if item.modelDirty:
				item.modelDirty = False
				modelSize = item.getMaximum() - item.getMinimum()
				glNewList(item.modelDisplayList, GL_COMPILE)
				opengl.DrawSTL(item)
				glEndList()
			
			if item.validPlacement:
				if self.parent.selection == item:
					glLightfv(GL_LIGHT0, GL_DIFFUSE,  [1.0, 0.9, 0.7, 1.0])
					glLightfv(GL_LIGHT0, GL_AMBIENT,  [0.2, 0.3, 0.2, 0.0])
				else:
					glLightfv(GL_LIGHT0, GL_DIFFUSE,  [1.0, 0.8, 0.6, 1.0])
					glLightfv(GL_LIGHT0, GL_AMBIENT,  [0.2, 0.1, 0.1, 0.0])
			else:
				if self.parent.selection == item:
					glLightfv(GL_LIGHT0, GL_DIFFUSE,  [1.0, 0.0, 0.0, 0.0])
					glLightfv(GL_LIGHT0, GL_AMBIENT,  [0.2, 0.0, 0.0, 0.0])
				else:
					glLightfv(GL_LIGHT0, GL_DIFFUSE,  [1.0, 0.0, 0.0, 0.0])
					glLightfv(GL_LIGHT0, GL_AMBIENT,  [0.2, 0.0, 0.0, 0.0])
			glPushMatrix()
			
			glEnable(GL_LIGHTING)
			glTranslate(item.centerX, item.centerY, 0)
			glPushMatrix()
			glEnable(GL_NORMALIZE)
			glScalef(item.scale, item.scale, item.scale)
			glCallList(item.modelDisplayList)
			glPopMatrix()
			
			vMin = item.getMinimum() * item.scale
			vMax = item.getMaximum() * item.scale
			vMinHead = vMin - extraSizeMin
			vMaxHead = vMax + extraSizeMax

			glDisable(GL_LIGHTING)

			if self.parent.selection == item:
				if item.gotHit:
					glColor3f(1.0,0.0,0.3)
				else:
					glColor3f(1.0,0.0,1.0)
				opengl.DrawBox(vMin, vMax)
				if item.gotHit:
					glColor3f(1.0,0.3,0.0)
				else:
					glColor3f(1.0,1.0,0.0)
				opengl.DrawBox(vMinHead, vMaxHead)
			elif seenSelected:
				if item.gotHit:
					glColor3f(0.5,0.0,0.1)
				else:
					glColor3f(0.5,0.0,0.5)
				opengl.DrawBox(vMinHead, vMaxHead)
			else:
				if item.gotHit:
					glColor3f(0.7,0.1,0.0)
				else:
					glColor3f(0.7,0.7,0.0)
				opengl.DrawBox(vMin, vMax)
			
			glPopMatrix()
		
		glFlush()

class ProjectSliceProgressWindow(wx.Frame):
	def __init__(self, actionList, resultFilename):
		super(ProjectSliceProgressWindow, self).__init__(None, title='Cura')
		self.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE))
		
		self.actionList = actionList
		self.resultFilename = resultFilename
		self.abort = False
		self.prevStep = 'start'
		self.totalDoneFactor = 0.0
		self.startTime = time.time()
		
		#How long does each step take compared to the others. This is used to make a better scaled progress bar, and guess time left.
		# TODO: Duplicate with sliceProgressPanel, move to sliceRun.
		self.sliceStepTimeFactor = {
			'start': 3.3713991642,
			'slice': 15.4984838963,
			'preface': 5.17178297043,
			'inset': 116.362634182,
			'fill': 215.702672005,
			'multiply': 21.9536788464,
			'speed': 12.759510994,
			'raft': 31.4580039978,
			'skirt': 19.3436040878,
			'skin': 1.0,
			'joris': 1.0,
			'comb': 23.7805759907,
			'cool': 27.148763895,
			'dimension': 90.4914340973
		}
		self.totalRunTimeFactor = 0
		for v in self.sliceStepTimeFactor.itervalues():
			self.totalRunTimeFactor += v
		
		self.sizer = wx.GridBagSizer(2, 2) 
		self.statusText = wx.StaticText(self, -1, "Building: %s" % (resultFilename))
		self.progressGauge = wx.Gauge(self, -1)
		self.progressGauge.SetRange(10000)
		self.progressGauge2 = wx.Gauge(self, -1)
		self.progressGauge2.SetRange(len(self.actionList))
		self.abortButton = wx.Button(self, -1, "Abort")
		self.sizer.Add(self.statusText, (0,0), flag=wx.ALIGN_CENTER)
		self.sizer.Add(self.progressGauge, (1, 0), flag=wx.EXPAND)
		self.sizer.Add(self.progressGauge2, (2, 0), flag=wx.EXPAND)
		self.sizer.Add(self.abortButton, (3,0), flag=wx.ALIGN_CENTER)
		self.sizer.AddGrowableCol(0)
		self.sizer.AddGrowableRow(0)

		self.Bind(wx.EVT_BUTTON, self.OnAbort, self.abortButton)
		self.SetSizer(self.sizer)
		self.Layout()
		self.Fit()
		
		threading.Thread(target=self.OnRun).start()

	def OnAbort(self, e):
		if self.abort:
			self.Close()
		else:
			self.abort = True
			self.abortButton.SetLabel('Close')

	def SetProgress(self, stepName, layer, maxLayer):
		if self.prevStep != stepName:
			self.totalDoneFactor += self.sliceStepTimeFactor[self.prevStep]
			newTime = time.time()
			#print "#####" + str(newTime-self.startTime) + " " + self.prevStep + " -> " + stepName
			self.startTime = newTime
			self.prevStep = stepName
		
		progresValue = ((self.totalDoneFactor + self.sliceStepTimeFactor[stepName] * layer / maxLayer) / self.totalRunTimeFactor) * 10000
		self.progressGauge.SetValue(int(progresValue))
		self.statusText.SetLabel(stepName + " [" + str(layer) + "/" + str(maxLayer) + "]")
	
	def OnRun(self):
		resultFile = open(self.resultFilename, "w")
		put = profile.putProfileSetting
		for action in self.actionList:
			p = subprocess.Popen(action.sliceCmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
			line = p.stdout.readline()
		
			maxValue = 1
			self.progressLog = []
			while(len(line) > 0):
				line = line.rstrip()
				if line[0:9] == "Progress[" and line[-1:] == "]":
					progress = line[9:-1].split(":")
					if len(progress) > 2:
						maxValue = int(progress[2])
					wx.CallAfter(self.SetProgress, progress[0], int(progress[1]), maxValue)
				else:
					print line
					self.progressLog.append(line)
					wx.CallAfter(self.statusText.SetLabel, line)
				if self.abort:
					p.terminate()
					wx.CallAfter(self.statusText.SetLabel, "Aborted by user.")
					return
				line = p.stdout.readline()
			self.returnCode = p.wait()
			
			oldProfile = profile.getGlobalProfileString()
			put('machine_center_x', action.centerX)
			put('machine_center_y', action.centerY)
			put('clear_z', action.clearZ)
			
			if action == self.actionList[0]:
				resultFile.write(';TYPE:CUSTOM\n')
				resultFile.write(profile.getAlterationFileContents('start.gcode').encode('utf-8')
			else:
				#reset the extrusion length, and move to the next object center.
				resultFile.write(';TYPE:CUSTOM\n')
				resultFile.write(profile.getAlterationFileContents('nextobject.gcode').encode('utf-8')
			resultFile.write(';PRINTNR:%d\n' % self.actionList.index(action))
			profile.loadGlobalProfileFromString(oldProfile)
			
			f = open(action.filename[: action.filename.rfind('.')] + "_export.project_tmp", "r")
			data = f.read(4096)
			while data != '':
				resultFile.write(data)
				data = f.read(4096)
			f.close()
			os.remove(action.filename[: action.filename.rfind('.')] + "_export.project_tmp")
			
			wx.CallAfter(self.progressGauge.SetValue, 10000)
			wx.CallAfter(self.progressGauge2.SetValue, self.actionList.index(action) + 1)
		
		resultFile.write(';TYPE:CUSTOM\n')
		resultFile.write(profile.getAlterationFileContents('end.gcode').encode('utf-8')
		resultFile.close()
		self.abort = True
		wx.CallAfter(self.abortButton.SetLabel, 'Close')

def main():
	app = wx.App(False)
	projectPlanner().Show(True)
	app.MainLoop()

if __name__ == '__main__':
	main()
