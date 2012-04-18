from __future__ import division

import os

import wx
from wx.lib import buttons

from util import profile

#######################################################
# toolbarUtil contains help classes and functions for
# toolbar buttons.
#######################################################

class Toolbar(wx.ToolBar):
	def __init__(self, parent):
		super(Toolbar, self).__init__(parent, -1, style=wx.TB_HORIZONTAL | wx.NO_BORDER)
		self.SetToolBitmapSize( ( 21, 21 ) )

		if not hasattr(parent, 'popup'):
			# Create popup window
			parent.popup = wx.PopupWindow(parent, flags=wx.BORDER_SIMPLE)
			parent.popup.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_INFOBK))
			parent.popup.text = wx.StaticText(parent.popup, -1, '')
			parent.popup.sizer = wx.BoxSizer()
			parent.popup.sizer.Add(parent.popup.text, flag=wx.EXPAND|wx.ALL, border=1)
			parent.popup.SetSizer(parent.popup.sizer)
			parent.popup.owner = None

	def OnPopupDisplay(self, e):
		self.UpdatePopup(e.GetEventObject())
		self.GetParent().popup.Show(True)
	
	def OnPopupHide(self, e):
		if self.GetParent().popup.owner == e.GetEventObject():
			self.GetParent().popup.Show(False)

	def UpdatePopup(self, control):
		popup = self.GetParent().popup
		popup.owner = control
		popup.text.SetLabel(control.helpText)
		popup.text.Wrap(350)
		popup.Fit();
		if os.name == 'darwin':
			x, y = self.GetParent().ClientToScreenXY(0, 0)
			sx, sy = self.GetParent().GetClientSizeTuple()
		else:
			x, y = control.ClientToScreenXY(0, 0)
			sx, sy = control.GetSizeTuple()
		popup.SetPosition((x, y+sy))

class ToggleButton(buttons.GenBitmapToggleButton):
	def __init__(self, parent, profileSetting, bitmapFilenameOn, bitmapFilenameOff,
				 helpText='', id=-1, callback=None, size=(20,20)):
		self.bitmapOn = wx.Bitmap(os.path.join(os.path.split(__file__)[0], "../images", bitmapFilenameOn))
		self.bitmapOff = wx.Bitmap(os.path.join(os.path.split(__file__)[0], "../images", bitmapFilenameOff))

		super(ToggleButton, self).__init__(parent, id, self.bitmapOff, size=size)

		self.callback = callback
		self.profileSetting = profileSetting
		self.helpText = helpText

		self.SetBezelWidth(1)
		self.SetUseFocusIndicator(False)

		if self.profileSetting != '':
			self.SetValue(profile.getProfileSetting(self.profileSetting) == 'True')
			self.Bind(wx.EVT_BUTTON, self.OnButtonProfile)
		else:
			self.Bind(wx.EVT_BUTTON, self.OnButton)

		self.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseEnter)
		self.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseLeave)
		
		parent.AddControl(self)

	def SetBitmap(self, boolValue):
		if boolValue:
			buttons.GenBitmapToggleButton.SetBitmapLabel(self, self.bitmapOn, False)
		else:
			buttons.GenBitmapToggleButton.SetBitmapLabel(self, self.bitmapOff, False)

	def SetValue(self, boolValue):
		self.SetBitmap(boolValue)
		buttons.GenBitmapToggleButton.SetValue(self, boolValue)

	def OnButton(self, event):
		self.SetBitmap(buttons.GenBitmapToggleButton.GetValue(self))
		event.Skip()

	def OnButtonProfile(self, event):
		if buttons.GenBitmapToggleButton.GetValue(self):
			self.SetBitmap(True)
			profile.putProfileSetting(self.profileSetting, 'True')
		else:
			self.SetBitmap(False)
			profile.putProfileSetting(self.profileSetting, 'False')
		self.callback()
		event.Skip()

	def OnMouseEnter(self, event):
		self.GetParent().OnPopupDisplay(event)
		event.Skip()

	def OnMouseLeave(self, event):
		self.GetParent().OnPopupHide(event)
		event.Skip()

class NormalButton(buttons.GenBitmapButton):
	def __init__(self, parent, callback, bitmapFilename,
				 helpText='', id=-1, size=(20,20)):
		self.bitmap = wx.Bitmap(os.path.join(os.path.split(__file__)[0], "../images", bitmapFilename))
		super(NormalButton, self).__init__(parent, id, self.bitmap, size=size)

		self.helpText = helpText

		self.SetBezelWidth(1)
		self.SetUseFocusIndicator(False)

		self.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseEnter)
		self.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseLeave)
		
		self.Bind(wx.EVT_BUTTON, callback)
		
		parent.AddControl(self)

	def OnMouseEnter(self, event):
		self.GetParent().OnPopupDisplay(event)
		event.Skip()

	def OnMouseLeave(self, event):
		self.GetParent().OnPopupHide(event)
		event.Skip()

