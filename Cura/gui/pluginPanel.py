import wx, wx.stc
import sys, math, threading, os, webbrowser
from wx.lib import scrolledpanel

from util import profile
from util import exporer

class pluginPanel(wx.Panel):
	def __init__(self, parent):
		wx.Panel.__init__(self, parent,-1)
		#Plugin page
		self.pluginList = profile.getPluginList()

		sizer = wx.GridBagSizer(2, 2)
		self.SetSizer(sizer)
		
		effectStringList = []
		for effect in self.pluginList:
			effectStringList.append(effect['name'])
		
		self.listbox = wx.ListBox(self, -1, choices=effectStringList)
		title = wx.StaticText(self, -1, "Plugins:")
		title.SetFont(wx.Font(wx.SystemSettings.GetFont(wx.SYS_ANSI_VAR_FONT).GetPointSize(), wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.FONTWEIGHT_BOLD))
		helpButton = wx.Button(self, -1, '?', style=wx.BU_EXACTFIT)
		addButton = wx.Button(self, -1, '>', style=wx.BU_EXACTFIT)
		openPluginLocationButton = wx.Button(self, -1, 'Open plugin location')
		sb = wx.StaticBox(self, label="Enabled plugins")
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		self.pluginEnabledPanel = scrolledpanel.ScrolledPanel(self)
		self.pluginEnabledPanel.SetupScrolling(False, True)
		
		sizer.Add(title, (0,0), border=10, flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT|wx.TOP)
		sizer.Add(helpButton, (0,1), border=10, flag=wx.ALIGN_RIGHT|wx.RIGHT|wx.TOP)
		sizer.Add(self.listbox, (1,0), span=(2,2), border=10, flag=wx.EXPAND|wx.LEFT|wx.RIGHT)
		sizer.Add(addButton, (1,2), border=5, flag=wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_BOTTOM)
		sizer.Add(boxsizer, (1,3), span=(2,1), border=10, flag=wx.EXPAND|wx.LEFT|wx.RIGHT)
		sizer.Add(openPluginLocationButton, (3, 0), span=(1,2), border=10, flag=wx.LEFT|wx.BOTTOM)
		boxsizer.Add(self.pluginEnabledPanel, 1, flag=wx.EXPAND)
		
		sizer.AddGrowableCol(3)
		sizer.AddGrowableRow(1)
		sizer.AddGrowableRow(2)
		
		sizer = wx.BoxSizer(wx.VERTICAL)
		self.pluginEnabledPanel.SetSizer(sizer)
		
		self.Bind(wx.EVT_BUTTON, self.OnAdd, addButton)
		self.Bind(wx.EVT_BUTTON, self.OnGeneralHelp, helpButton)
		self.Bind(wx.EVT_BUTTON, self.OnOpenPluginLocation, openPluginLocationButton)
		self.listbox.Bind(wx.EVT_LEFT_DCLICK, self.OnAdd)
		self.panelList = []
		self.updateProfileToControls()
	
	def updateProfileToControls(self):
		self.pluginConfig = profile.getPluginConfig()
		for p in self.panelList:
			p.Show(False)
			self.pluginEnabledPanel.GetSizer().Detach(p)
		self.panelList = []
		for pluginConfig in self.pluginConfig:
			self._buildPluginPanel(pluginConfig)
	
	def _buildPluginPanel(self, pluginConfig):
		plugin = None
		for pluginTest in self.pluginList:
			if pluginTest['filename'] == pluginConfig['filename']:
				plugin = pluginTest
		if plugin == None:
			return False
		
		pluginPanel = wx.Panel(self.pluginEnabledPanel)
		s = wx.GridBagSizer(2, 2)
		pluginPanel.SetSizer(s)
		title = wx.StaticText(pluginPanel, -1, plugin['name'])
		title.SetFont(wx.Font(wx.SystemSettings.GetFont(wx.SYS_ANSI_VAR_FONT).GetPointSize(), wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.FONTWEIGHT_BOLD))
		remButton = wx.Button(pluginPanel, -1, 'X', style=wx.BU_EXACTFIT)
		helpButton = wx.Button(pluginPanel, -1, '?', style=wx.BU_EXACTFIT)
		s.Add(title, pos=(0,1), span=(1,2), flag=wx.ALIGN_BOTTOM|wx.TOP|wx.LEFT|wx.RIGHT, border=5)
		s.Add(helpButton, pos=(0,0), span=(1,1), flag=wx.TOP|wx.LEFT|wx.ALIGN_RIGHT, border=5)
		s.Add(remButton, pos=(0,3), span=(1,1), flag=wx.TOP|wx.RIGHT|wx.ALIGN_RIGHT, border=5)
		s.Add(wx.StaticLine(pluginPanel), pos=(1,0), span=(1,4), flag=wx.EXPAND|wx.LEFT|wx.RIGHT,border=3)
		info = wx.StaticText(pluginPanel, -1, plugin['info'])
		info.Wrap(300)
		s.Add(info, pos=(2,0), span=(1,4), flag=wx.EXPAND|wx.LEFT|wx.RIGHT,border=3)
		
		pluginPanel.paramCtrls = {}
		i = 0
		for param in plugin['params']:
			value = param['default']
			if param['name'] in pluginConfig['params']:
				value = pluginConfig['params'][param['name']]
			
			ctrl = wx.TextCtrl(pluginPanel, -1, value)
			s.Add(wx.StaticText(pluginPanel, -1, param['description']), pos=(3+i,0), span=(1,2), flag=wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL,border=3)
			s.Add(ctrl, pos=(3+i,2), span=(1,2), flag=wx.EXPAND|wx.LEFT|wx.RIGHT,border=3)

			ctrl.Bind(wx.EVT_TEXT, self.OnSettingChange)
			
			pluginPanel.paramCtrls[param['name']] = ctrl
			
			i += 1
		s.Add(wx.StaticLine(pluginPanel), pos=(3+i,0), span=(1,4), flag=wx.EXPAND|wx.LEFT|wx.RIGHT,border=3)

		self.Bind(wx.EVT_BUTTON, self.OnRem, remButton)
		self.Bind(wx.EVT_BUTTON, self.OnHelp, helpButton)

		s.AddGrowableCol(1)
		pluginPanel.SetBackgroundColour(self.GetParent().GetBackgroundColour())
		self.pluginEnabledPanel.GetSizer().Add(pluginPanel, flag=wx.EXPAND)
		self.pluginEnabledPanel.Layout()
		self.pluginEnabledPanel.SetSize((1,1))
		self.Layout()
		self.pluginEnabledPanel.ScrollChildIntoView(pluginPanel)
		self.panelList.append(pluginPanel)
		return True
	
	def OnSettingChange(self, e):
		for panel in self.panelList:
			idx = self.panelList.index(panel)
			for k in panel.paramCtrls.keys():
				self.pluginConfig[idx]['params'][k] = panel.paramCtrls[k].GetValue()
		profile.setPluginConfig(self.pluginConfig)
	
	def OnAdd(self, e):
		if self.listbox.GetSelection() < 0:
			return
		plugin = self.pluginList[self.listbox.GetSelection()]
		newConfig = {'filename': plugin['filename'], 'params': {}}
		if not self._buildPluginPanel(newConfig):
			return
		self.pluginConfig.append(newConfig)
		profile.setPluginConfig(self.pluginConfig)

	def OnRem(self, e):
		panel = e.GetEventObject().GetParent()
		sizer = self.pluginEnabledPanel.GetSizer()
		idx = self.panelList.index(panel)
		
		panel.Show(False)
		for p in self.panelList:
			sizer.Detach(p)
		self.panelList.pop(idx)
		for p in self.panelList:
				sizer.Add(p, flag=wx.EXPAND)

		self.pluginEnabledPanel.Layout()
		self.pluginEnabledPanel.SetSize((1,1))
		self.Layout()

		self.pluginConfig.pop(idx)
		profile.setPluginConfig(self.pluginConfig)

	def OnHelp(self, e):
		panel = e.GetEventObject().GetParent()
		sizer = self.pluginEnabledPanel.GetSizer()
		idx = self.panelList.index(panel)
		
		fname = self.pluginConfig[idx]['filename'].lower()
		fname = fname[0].upper() + fname[1:]
		fname = fname[:fname.rfind('.')]
		webbrowser.open('http://wiki.ultimaker.com/CuraPlugin:_' + fname)
	
	def OnGeneralHelp(self, e):
		webbrowser.open('http://wiki.ultimaker.com/Category:CuraPlugin')
	
	def OnOpenPluginLocation(self, e):
		exporer.openExporerPath(profile.getPluginBasePaths()[0])
