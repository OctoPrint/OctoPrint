import wx, wx.stc
import sys,math,threading,os

from util import profile

class alterationPanel(wx.Panel):
	def __init__(self, parent):
		wx.Panel.__init__(self, parent,-1)

		self.alterationFileList = ['start.gcode', 'end.gcode', 'support_start.gcode', 'support_end.gcode', 'nextobject.gcode', 'replace.csv']
		self.currentFile = None

		#self.textArea = wx.TextCtrl(self, style=wx.TE_MULTILINE|wx.TE_DONTWRAP|wx.TE_PROCESS_TAB)
		#self.textArea.SetFont(wx.Font(wx.SystemSettings.GetFont(wx.SYS_ANSI_VAR_FONT).GetPointSize(), wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
		self.textArea = wx.stc.StyledTextCtrl(self)
		self.textArea.SetLexer(wx.stc.STC_LEX_CONTAINER)
		self.list = wx.ListBox(self, choices=self.alterationFileList, style=wx.LB_SINGLE)
		self.list.SetSelection(0)
		self.Bind(wx.EVT_LISTBOX, self.OnSelect, self.list)
		self.textArea.Bind(wx.EVT_KILL_FOCUS, self.OnFocusLost, self.textArea)
		self.textArea.Bind(wx.stc.EVT_STC_STYLENEEDED, self.OnStyle)
		
		fontSize = wx.SystemSettings.GetFont(wx.SYS_ANSI_VAR_FONT).GetPointSize()
		fontName = wx.Font(wx.SystemSettings.GetFont(wx.SYS_ANSI_VAR_FONT).GetPointSize(), wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL).GetFaceName()
		self.textArea.SetStyleBits(5)
		self.textArea.StyleSetSpec(wx.stc.STC_STYLE_DEFAULT,    "face:%s,size:%d" % (fontName, fontSize))
		self.textArea.StyleSetSpec(1,                           "fore:#008000,face:%s,size:%d" % (fontName, fontSize))
		
		sizer = wx.GridBagSizer()
		sizer.Add(self.list, (0,0), span=(1,1), flag=wx.EXPAND)
		sizer.Add(self.textArea, (0,1), span=(1,1), flag=wx.EXPAND)
		sizer.AddGrowableCol(1)
		sizer.AddGrowableRow(0)
		self.SetSizer(sizer)
		
		self.loadFile(self.alterationFileList[self.list.GetSelection()])
		self.currentFile = self.list.GetSelection()

	def OnSelect(self, e):
		self.loadFile(self.alterationFileList[self.list.GetSelection()])
		self.currentFile = self.list.GetSelection()

	def loadFile(self, filename):
		#self.textArea.SetValue(profile.getAlterationFile(filename))
		self.textArea.SetText(profile.getAlterationFile(filename))

	def OnFocusLost(self, e):
		if self.currentFile == self.list.GetSelection():
			#profile.setAlterationFile(self.alterationFileList[self.list.GetSelection()], self.textArea.GetValue())
			profile.setAlterationFile(self.alterationFileList[self.list.GetSelection()], self.textArea.GetText())

	def OnStyle(self, e):
		#for lineNr in xrange(0, 
		lineNr = self.textArea.LineFromPosition(self.textArea.GetEndStyled())
		while self.textArea.PositionFromLine(lineNr) > -1:
			line = self.textArea.GetLine(lineNr)
			self.textArea.StartStyling(self.textArea.PositionFromLine(lineNr), 31)
			self.textArea.SetStyling(self.textArea.LineLength(lineNr), wx.stc.STC_STYLE_DEFAULT)
			if ';' in line:
				pos = line.index(';')
				self.textArea.StartStyling(self.textArea.PositionFromLine(lineNr) + pos, 31)
				self.textArea.SetStyling(self.textArea.LineLength(lineNr) - pos, 1)
			lineNr += 1

