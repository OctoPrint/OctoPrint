from __future__ import absolute_import
import __init__

import wx

from newui import preview3d

def main():
	app = wx.App(False)
	mainWindow()
	app.MainLoop()

class mainWindow(wx.Frame):
	"Main user interface window"
	def __init__(self):
		super(mainWindow, self).__init__(None, title='SkeinPyPy')
		menubar = wx.MenuBar()
		fileMenu = wx.Menu()
		fitem = fileMenu.Append(wx.ID_EXIT, 'Quit', 'Quit application')
		menubar.Append(fileMenu, '&File')
		menubar.Append(wx.Menu(), 'Expert')
		self.SetMenuBar(menubar)
		
		p = wx.Panel(self)
		nb = wx.Notebook(p, size=(400,10))
		
		printConfig = wx.Panel(nb);
		wx.StaticText(printConfig, -1, "Test", (20,20))
		nb.AddPage(printConfig, "Print")
		nb.AddPage(wx.Panel(nb), "Machine")
		nb.AddPage(wx.Panel(nb), "Start/End-GCode")

		p3d = preview3d.myGLCanvas(p)
		
		loadButton = wx.Button(p, 1, 'Load STL')
		
		sizer = wx.GridBagSizer()
		sizer.Add(nb, (0,0), span=(2,1), flag=wx.EXPAND)
		sizer.Add(p3d, (0,1), flag=wx.EXPAND)
		sizer.Add(loadButton, (1,1))
		sizer.AddGrowableCol(1)
		sizer.AddGrowableRow(0)
		p.SetSizer(sizer)
		
		self.Bind(wx.EVT_MENU, self.OnQuit, fitem)

		self.SetSize((800, 400))
		self.Centre()
		self.Show(True)
	
	def OnQuit(self, e):
		self.Close()

