import wx
import sys,math,threading

from fabmetheus_utilities import settings

class alterationPanel(wx.Panel):
	def __init__(self, parent):
		wx.Panel.__init__(self, parent,-1)

		self.alterationFileList = ['start.gcode', 'end.gcode', 'cool_start.gcode', 'cool_end.gcode']

		self.textArea = wx.TextCtrl(self, style=wx.TE_MULTILINE)
		self.list = wx.ListBox(self, choices=self.alterationFileList, style=wx.LB_SINGLE)
		self.list.SetSelection(0)
		self.Bind(wx.EVT_LISTBOX, self.OnSelect, self.list)
		self.OnSelect(None)
		
		sizer = wx.GridBagSizer()
		sizer.Add(self.list, (0,0), span=(1,1), flag=wx.EXPAND)
		sizer.Add(self.textArea, (0,1), span=(1,1), flag=wx.EXPAND)
		sizer.AddGrowableCol(1)
		sizer.AddGrowableRow(0)
		self.SetSizer(sizer)

	def OnSelect(self, e):
		self.loadFile(self.alterationFileList[self.list.GetSelection()])

	def loadFile(self, filename):
		self.textArea.SetValue(settings.getAlterationFile(filename))
