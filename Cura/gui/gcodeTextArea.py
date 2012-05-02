import wx, wx.stc
import sys,math,os

from util import profile

class GcodeTextArea(wx.stc.StyledTextCtrl):
	def __init__(self, parent):
		super(GcodeTextArea, self).__init__(parent)

		self.SetLexer(wx.stc.STC_LEX_CONTAINER)
		self.Bind(wx.stc.EVT_STC_STYLENEEDED, self.OnStyle)
		
		fontSize = wx.SystemSettings.GetFont(wx.SYS_ANSI_VAR_FONT).GetPointSize()
		fontName = wx.Font(wx.SystemSettings.GetFont(wx.SYS_ANSI_VAR_FONT).GetPointSize(), wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL).GetFaceName()
		self.SetStyleBits(5)
		self.StyleSetSpec(wx.stc.STC_STYLE_DEFAULT,    "face:%s,size:%d" % (fontName, fontSize))
		self.StyleSetSpec(1,                           "fore:#008000,face:%s,size:%d" % (fontName, fontSize))
		
	def OnStyle(self, e):
		lineNr = self.LineFromPosition(self.GetEndStyled())
		while self.PositionFromLine(lineNr) > -1:
			line = self.GetLine(lineNr)
			self.StartStyling(self.PositionFromLine(lineNr), 31)
			self.SetStyling(self.LineLength(lineNr), wx.stc.STC_STYLE_DEFAULT)
			if ';' in line:
				pos = line.index(';')
				self.StartStyling(self.PositionFromLine(lineNr) + pos, 31)
				self.SetStyling(self.LineLength(lineNr) - pos, 1)
			lineNr += 1

	def GetValue(self):
		return self.GetText()
	
	def SetValue(self, s):
		self.SetText(s)

