from __future__ import absolute_import

import wx
import os

from wx import glcanvas

try:
	import OpenGL
	OpenGL.ERROR_CHECKING = False
	from OpenGL.GLU import *
	from OpenGL.GL import *
	hasOpenGLlibs = True
except:
	print "Failed to find PyOpenGL: http://pyopengl.sourceforge.net/"
	hasOpenGLlibs = False

from Cura.gui.util import toolbarUtil
from Cura.gui.util import opengl
from Cura.util import util3d
from Cura.util import svg
from Cura.util import profile
from Cura.util import version

class flatSlicerWindow(wx.Frame):
	"Cura 2D SVG slicer"
	def __init__(self):
		super(flatSlicerWindow, self).__init__(None, title='Cura - ' + version.getVersion())

		self.machineSize = util3d.Vector3(profile.getPreferenceFloat('machine_width'), profile.getPreferenceFloat('machine_depth'), profile.getPreferenceFloat('machine_height'))
		self.filename = None
		self.svg = None

		wx.EVT_CLOSE(self, self.OnClose)
		self.panel = wx.Panel(self, -1)
		self.SetSizer(wx.BoxSizer(wx.VERTICAL))
		self.GetSizer().Add(self.panel, 1, flag=wx.EXPAND)

		self.toolbar = toolbarUtil.Toolbar(self.panel)

		toolbarUtil.NormalButton(self.toolbar, self.OnOpenSVG, 'open.png', 'Open SVG')
		self.toolbar.AddSeparator()
		group = []
		toolbarUtil.RadioButton(self.toolbar, group, 'object-3d-on.png', 'object-3d-off.png', '3D view', callback=self.On3DClick)
		toolbarUtil.RadioButton(self.toolbar, group, 'object-top-on.png', 'object-top-off.png', 'Topdown view', callback=self.OnTopClick).SetValue(True)
		self.toolbar.AddSeparator()
		toolbarUtil.NormalButton(self.toolbar, self.OnQuit, 'exit.png', 'Close project planner')
		
		self.toolbar.Realize()
		
		sizer = wx.GridBagSizer(2,2)
		self.panel.SetSizer(sizer)
		self.preview = PreviewGLCanvas(self.panel, self)

		sizer.Add(self.toolbar, (0,0), span=(1,1), flag=wx.EXPAND|wx.LEFT|wx.RIGHT)
		sizer.Add(self.preview, (1,0), span=(5,1), flag=wx.EXPAND)

		sizer.AddGrowableCol(0)
		sizer.AddGrowableRow(1)

		self.SetSize((600,400))

	def OnClose(self, e):
		self.Destroy()

	def OnQuit(self, e):
		self.Close()

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

	def OnOpenSVG(self, e):
		dlg=wx.FileDialog(self, "Open SVG file", os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
		dlg.SetWildcard("SVG files (*.svg)|*.svg;*.SVG")
		if dlg.ShowModal() == wx.ID_OK:
			self.filename = dlg.GetPath()
			self.svg = svg.SVG(self.filename)
			self.svg.center(complex(profile.getPreferenceFloat('machine_width')/2, profile.getPreferenceFloat('machine_depth')/2))
			self.preview.Refresh()
		dlg.Destroy()

class PreviewGLCanvas(glcanvas.GLCanvas):
	def __init__(self, parent, realParent):
		attribList = (glcanvas.WX_GL_RGBA, glcanvas.WX_GL_DOUBLEBUFFER, glcanvas.WX_GL_DEPTH_SIZE, 24, glcanvas.WX_GL_STENCIL_SIZE, 8)
		glcanvas.GLCanvas.__init__(self, parent, attribList = attribList)
		self.parent = realParent
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
				self.offsetX += float(e.GetX() - self.oldX) * self.zoom / self.GetSize().GetHeight() * 2
				self.offsetY -= float(e.GetY() - self.oldY) * self.zoom / self.GetSize().GetHeight() * 2
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
		
		if self.parent.svg != None:
			for path in self.parent.svg.paths:
				glColor3f(1.0,0.8,0.6)
				glBegin(GL_LINE_STRIP)
				for p in path:
					glVertex3f(p.real, p.imag, 1)
				glEnd()
		
		glFlush()

def main():
	app = wx.App(False)
	flatSlicerWindow().Show(True)
	app.MainLoop()

if __name__ == '__main__':
	main()

