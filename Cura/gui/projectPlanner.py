from __future__ import absolute_import
import __init__

import wx, os, platform, types, webbrowser, math, subprocess
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

class projectPlanner(wx.Frame):
	"Main user interface window"
	def __init__(self):
		super(projectPlanner, self).__init__(None, title='Cura')
		
		self.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE))
		wx.EVT_CLOSE(self, self.OnClose)
		#self.SetIcon(icon.getMainIcon())
		
		menubar = wx.MenuBar()
		fileMenu = wx.Menu()
		i = fileMenu.Append(-1, 'Open Project...')
		self.Bind(wx.EVT_MENU, self.OnLoadProject, i)
		i = fileMenu.Append(-1, 'Save Project...')
		self.Bind(wx.EVT_MENU, self.OnSaveProject, i)
		fileMenu.AppendSeparator()
		i = fileMenu.Append(wx.ID_EXIT, 'Quit')
		self.Bind(wx.EVT_MENU, self.OnQuit, i)
		menubar.Append(fileMenu, '&File')
		self.SetMenuBar(menubar)
		
		self.list = []
		self.selection = None

		self.machineSize = util3d.Vector3(float(profile.getPreference('machine_width')), float(profile.getPreference('machine_depth')), float(profile.getPreference('machine_height')))
		self.headSizeMin = util3d.Vector3(70,16,0)
		self.headSizeMax = util3d.Vector3(16,35,0)

		self.toolbar = toolbarUtil.Toolbar(self)

		group = []
		toolbarUtil.RadioButton(self.toolbar, group, 'object-3d-on.png', 'object-3d-off.png', '3D view', callback=self.On3DClick)
		toolbarUtil.RadioButton(self.toolbar, group, 'object-top-on.png', 'object-top-off.png', 'Topdown view', callback=self.OnTopClick).SetValue(True)
		
		self.toolbar.Realize()
		
		sizer = wx.GridBagSizer(2,2)
		self.SetSizer(sizer)
		self.preview = PreviewGLCanvas(self)
		self.listbox = wx.ListBox(self, -1, choices=[])
		self.addButton = wx.Button(self, -1, "Add")
		self.remButton = wx.Button(self, -1, "Remove")
		self.sliceButton = wx.Button(self, -1, "Slice")
		
		sizer.Add(self.toolbar, (0,0), span=(1,1), flag=wx.EXPAND)
		sizer.Add(self.preview, (1,0), span=(3,1), flag=wx.EXPAND)
		sizer.Add(self.listbox, (0,1), span=(2,2), flag=wx.EXPAND)
		sizer.Add(self.addButton, (2,1), span=(1,1))
		sizer.Add(self.remButton, (2,2), span=(1,1))
		sizer.Add(self.sliceButton, (3,1), span=(1,1))
		sizer.AddGrowableCol(0)
		sizer.AddGrowableRow(1)
		
		self.addButton.Bind(wx.EVT_BUTTON, self.OnAddModel)
		self.remButton.Bind(wx.EVT_BUTTON, self.OnRemModel)
		self.sliceButton.Bind(wx.EVT_BUTTON, self.OnSlice)
		self.listbox.Bind(wx.EVT_LISTBOX, self.OnListSelect)
		
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
		self.selection = self.list[self.listbox.GetSelection()]
		self.preview.Refresh()

	def OnAddModel(self, e):
		dlg=wx.FileDialog(self, "Open file to print", os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
		dlg.SetWildcard("STL files (*.stl)|*.stl;*.STL")
		if dlg.ShowModal() == wx.ID_OK:
			item = stl.stlModel()
			item.filename=dlg.GetPath()
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
		self.listbox.Delete(self.listbox.GetSelection())
		self.selection = None
		self.preview.Refresh()

	def OnSlice(self, e):
		oldProfile = profile.getGlobalProfileString()
		
		put = profile.putProfileSetting

		put('model_multiply_x', '1')
		put('model_multiply_y', '1')
		put('skirt_line_count', '0')
		put('enable_raft', 'False')
		put('add_start_end_gcode', 'False')
		put('gcode_extension', 'project_tmp')
		
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
			
			item.sliceCmd = sliceRun.getSliceCommand(item.filename)
		
		#Restore the old profile.
		profile.loadGlobalProfileFromString(oldProfile)
		
		dlg=wx.FileDialog(self, "Save project gcode file", os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_SAVE)
		dlg.SetWildcard("GCode file (*.gcode)|*.gcode")
		if dlg.ShowModal() != wx.ID_OK:
			dlg.Destroy()
			return
		resultFile = open(dlg.GetPath(), "w")
		dlg.Destroy()
		
		i = 1
		maxZ = 0
		prevItem = None
		for item in self.list:
			subprocess.call(item.sliceCmd)
			
			maxZ = max(maxZ, item.getMaximum().z * item.scale)
			put('machine_center_x', item.centerX)
			put('machine_center_y', item.centerY)
			put('clear_z', maxZ)
			
			if prevItem == None:
				resultFile.write(';TYPE:CUSTOM\n')
				resultFile.write(profile.getAlterationFileContents('start.gcode'))
			else:
				#reset the extrusion length, and move to the next object center.
				resultFile.write(';TYPE:CUSTOM\n')
				resultFile.write(profile.getAlterationFileContents('nextobject.gcode'))
			resultFile.write(';PRINTNR:%d\n' % (i))
			profile.loadGlobalProfileFromString(oldProfile)
			
			f = open(item.filename[: item.filename.rfind('.')] + "_export.project_tmp", "r")
			data = f.read(4096)
			while data != '':
				resultFile.write(data)
				data = f.read(4096)
			f.close()
			os.remove(item.filename[: item.filename.rfind('.')] + "_export.project_tmp")
			i += 1
			
			prevItem = item
		
		resultFile.write(';TYPE:CUSTOM\n')
		resultFile.write(profile.getAlterationFileContents('end.gcode'))
		resultFile.close()
	
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

	def updateModelTransform(self, item):
		scale = item.scale
		rotate = item.rotate
		scaleX = scale
		scaleY = scale
		scaleZ = scale
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

		for item in self.parent.list:
			item.validPlacement = True
			item.gotHit = False
		
		for idx1 in xrange(0, len(self.parent.list)):
			item = self.parent.list[idx1]
			iMin1 = item.getMinimum() * item.scale + util3d.Vector3(item.centerX, item.centerY, 0) - self.parent.headSizeMin
			iMax1 = item.getMaximum() * item.scale + util3d.Vector3(item.centerX, item.centerY, 0) + self.parent.headSizeMax
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
			vMinHead = vMin - self.parent.headSizeMin
			vMaxHead = vMax + self.parent.headSizeMax

			glDisable(GL_LIGHTING)

			if self.parent.selection == item:
				if item.gotHit:
					glColor3f(1.0,0.3,0.0)
				else:
					glColor3f(1.0,1.0,0.0)
				opengl.DrawBox(vMin, vMax)
				if item.gotHit:
					glColor3f(1.0,0.0,0.3)
				else:
					glColor3f(1.0,0.0,1.0)
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

def main():
	app = wx.App(False)
	projectPlanner().Show(True)
	app.MainLoop()

if __name__ == '__main__':
	main()
