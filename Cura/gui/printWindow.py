from __future__ import absolute_import
import __init__

import wx

printWindowHandle = None

def printFile(filename):
	global printWindowHandle
	print "Want to print: " + filename
	if printWindowHandle == None:
		printWindowHandle = printWindow()
	printWindowHandle.Show(True)
	printWindowHandle.Raise()

class printWindow(wx.Frame):
	"Main user interface window"
	def __init__(self):
		super(printWindow, self).__init__(None, -1, title='Printing')
		self.SetSizer(wx.BoxSizer())
		self.panel = wx.Panel(self)
		self.GetSizer().Add(self.panel, 1, flag=wx.EXPAND)
		self.sizer = wx.GridBagSizer(2, 2)
		self.panel.SetSizer(self.sizer)
		
		sb = wx.StaticBox(self.panel, label="Statistics")
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		boxsizer.Add(wx.StaticText(self.panel, -1, "Filament: #.##m #.##g"), flag=wx.LEFT, border=5)
		boxsizer.Add(wx.StaticText(self.panel, -1, "Print time: ##:##"), flag=wx.LEFT, border=5)
		
		self.sizer.Add(boxsizer, pos=(0,0), span=(4,1), flag=wx.EXPAND)
		
		self.sizer.Add(wx.Button(self.panel, -1, 'Connect'), pos=(0,1))
		self.sizer.Add(wx.Button(self.panel, -1, 'Load GCode'), pos=(1,1))
		self.sizer.Add(wx.Button(self.panel, -1, 'Print GCode'), pos=(2,1))
		self.sizer.Add(wx.Button(self.panel, -1, 'Cancel print'), pos=(3,1))
		self.sizer.Add(wx.Gauge(self.panel, -1), pos=(4,0), span=(1,2), flag=wx.EXPAND)
		self.sizer.AddGrowableRow(3)
		self.sizer.AddGrowableCol(0)
		
		self.Bind(wx.EVT_CLOSE, self.OnClose)
		
		self.Layout()
		self.Fit()
		self.Centre()
	
	def OnClose(self, e):
		global printWindowHandle
		printWindowHandle = None
		self.Destroy()
