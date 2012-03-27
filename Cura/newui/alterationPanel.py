import wx
import sys,math,threading,os

from newui import profile

class alterationPanel(wx.Panel):
	def __init__(self, parent):
		wx.Panel.__init__(self, parent,-1)

		self.alterationFileList = ['start.gcode', 'end.gcode', 'cool_start.gcode', 'cool_end.gcode', 'replace.csv']
		self.currentFile = None

		self.textArea = wx.TextCtrl(self, style=wx.TE_MULTILINE|wx.TE_DONTWRAP|wx.TE_PROCESS_TAB)
		self.textArea.SetFont(wx.Font(wx.SystemSettings.GetFont(wx.SYS_ANSI_VAR_FONT).GetPointSize(), wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
		self.list = wx.ListBox(self, choices=self.alterationFileList, style=wx.LB_SINGLE)
		self.list.SetSelection(0)
		self.Bind(wx.EVT_LISTBOX, self.OnSelect, self.list)
		self.textArea.Bind(wx.EVT_KILL_FOCUS, self.OnFocusLost, self.textArea)
		
		sizer = wx.GridBagSizer()
		sizer.Add(self.list, (0,0), span=(1,1), flag=wx.EXPAND)
		sizer.Add(self.textArea, (0,1), span=(1,1), flag=wx.EXPAND)
		sizer.AddGrowableCol(1)
		sizer.AddGrowableRow(0)
		self.SetSizer(sizer)
		
		self.loadFile(self.alterationFileList[self.list.GetSelection()])

	def OnSelect(self, e):
		self.loadFile(self.alterationFileList[self.list.GetSelection()])
		self.currentFile = self.list.GetSelection()

	def loadFile(self, filename):
		self.textArea.SetValue(unicode(profile.getAlterationFileContents(filename, False), "utf-8"))

	def OnFocusLost(self, e):
		if self.currentFile == self.list.GetSelection():
			filename = profile.getAlterationFilePath(self.alterationFileList[self.list.GetSelection()])
			f = open(filename, "wb")
			f.write(self.textArea.GetValue().encode("utf-8"))
			f.close()
