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
		self.SetSizer(wx.GridBagSizer(2, 2))
		
		self.statsPanel = wx.Panel(self)
		self.GetSizer().Add(self.statsPanel, pos=(0,0), span=(4,1), flag=wx.EXPAND)
		
		self.GetSizer().Add(wx.Button(self, -1, 'Test'), pos=(0,1))
		self.GetSizer().Add(wx.Button(self, -1, 'Test'), pos=(1,1))
		self.GetSizer().Add(wx.Button(self, -1, 'Test'), pos=(2,1))
		
		self.Bind(wx.EVT_CLOSE, self.OnClose)
		
		self.Layout()
		self.Fit()
		self.Centre()
	
	def OnClose(self, e):
		global printWindowHandle
		printWindowHandle = None
		self.Destroy()
