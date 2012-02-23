from __future__ import absolute_import
import __init__

import wx, os

from fabmetheus_utilities import archive
from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_utilities import skeinforge_profile

from newui import preview3d
from newui import sliceProgessPanel
from newui import alterationPanel

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
		fitem = fileMenu.Append(-1, 'Open Profile...', 'Open Profile...')
		self.Bind(wx.EVT_MENU, self.OnLoadProfile, fitem)
		fitem = fileMenu.Append(-1, 'Save Profile...', 'Save Profile...')
		self.Bind(wx.EVT_MENU, self.OnSaveProfile, fitem)
		fitem = fileMenu.Append(wx.ID_EXIT, 'Quit', 'Quit application')
		self.Bind(wx.EVT_MENU, self.OnQuit, fitem)
		menubar.Append(fileMenu, '&File')
		#menubar.Append(wx.Menu(), 'Expert')
		self.SetMenuBar(menubar)
		
		wx.ToolTip.SetDelay(0)
		
		self.lastPath = ""
		self.filename = None
		self.progressPanelList = []
		self.controlList = []
		self.plugins = {}
		for m in skeinforge_profile.getCraftTypePluginModule().getCraftSequence():
			self.plugins[m] = archive.getModuleWithDirectoryPath(archive.getCraftPluginsDirectoryPath(), m).getNewRepository()
			settings.getReadRepository(self.plugins[m])
		
		skeinPyPySettingInfo = settings.getSkeinPyPyProfileInformation()

		for pluginName in self.plugins.keys():
			self.plugins[pluginName].preferencesDict = {}
			for pref in self.plugins[pluginName].preferences:
				if skeinPyPySettingInfo[pluginName][settings.safeConfigName(pref.name)] == 'save':
					self.plugins[pluginName].preferencesDict[settings.safeConfigName(pref.name)] = pref

		p = wx.Panel(self)
		nb = wx.Notebook(p, size=(500,10))
		
		configPanel = wx.Panel(nb);
		nb.AddPage(configPanel, "Print config")
		sizer = wx.GridBagSizer(2, 2)
		configPanel.SetSizer(sizer)
		
		self.AddTitle(configPanel, "Accuracy")
		self.AddSetting(configPanel, "Layer height (mm)", self.plugins['carve'].preferencesDict['Layer_Height_mm'], 'Layer height in millimeters.\n0.2 is a good value for quick prints.\n0.1 gives high quality prints.')
		self.AddTitle(configPanel, "Fill")
		self.AddSetting(configPanel, "Solid layers", self.plugins['fill'].preferencesDict['Solid_Surface_Thickness_layers'])
		self.AddSetting(configPanel, "Fill Density", self.plugins['fill'].preferencesDict['Infill_Solidity_ratio'])
		self.AddTitle(configPanel, "Skirt")
		self.AddSetting(configPanel, "Line count", self.plugins['skirt'].preferencesDict['Skirt_line_count'])
		self.AddSetting(configPanel, "Start distance (mm)", self.plugins['skirt'].preferencesDict['Gap_Width_mm'])
		self.AddTitle(configPanel, "Cool")
		#self.AddSetting(configPanel, "Cool type", self.plugins['cool'].preferencesDict['Cool_Type'])
		self.AddSetting(configPanel, "Minimal layer time", self.plugins['cool'].preferencesDict['Minimum_Layer_Time_seconds'])
		self.AddTitle(configPanel, "Retraction")
		self.AddSetting(configPanel, "Speed (mm/s)", self.plugins['dimension'].preferencesDict['Extruder_Retraction_Speed_mm/s'])
		self.AddSetting(configPanel, "Distance (mm)", self.plugins['dimension'].preferencesDict['Retraction_Distance_millimeters'])
		self.AddSetting(configPanel, "Extra length on start (mm)", self.plugins['dimension'].preferencesDict['Restart_Extra_Distance_millimeters'])
		self.AddSetting(configPanel, "Minimal travel (mm)", self.plugins['dimension'].preferencesDict['Minimum_Travel_for_Retraction_millimeters'])

		configPanel = wx.Panel(nb);
		nb.AddPage(configPanel, "Machine && Filament")
		sizer = wx.GridBagSizer(2, 2)
		configPanel.SetSizer(sizer)
		
		self.AddTitle(configPanel, "Machine size")
		self.AddSetting(configPanel, "Width (mm)", settings.IntSpin().getFromValue(10, "machine_width", None, 1000, 205))
		self.AddSetting(configPanel, "Depth (mm)", settings.IntSpin().getFromValue(10, "machine_depth", None, 1000, 205))
		self.AddSetting(configPanel, "Height (mm)", settings.IntSpin().getFromValue(10, "machine_height", None, 1000, 200))

		self.AddTitle(configPanel, "Machine nozzle")
		self.AddSetting(configPanel, "Nozzle size (mm)", self.plugins['carve'].preferencesDict['Edge_Width_mm'])

		self.AddTitle(configPanel, "Speed")
		self.AddSetting(configPanel, "Print speed (mm/s)", self.plugins['speed'].preferencesDict['Feed_Rate_mm/s'])
		self.AddSetting(configPanel, "Travel speed (mm/s)", self.plugins['speed'].preferencesDict['Travel_Feed_Rate_mm/s'])
		self.AddSetting(configPanel, "Max Z speed (mm/z)", self.plugins['speed'].preferencesDict['Maximum_Z_Feed_Rate_mm/s'])
		self.AddSetting(configPanel, "Bottom Layer Speed Ratio", self.plugins['speed'].preferencesDict['Object_First_Layer_Feed_Rate_Infill_Multiplier_ratio'])

		self.AddTitle(configPanel, "Filament")
		self.AddSetting(configPanel, "Diameter (mm)", self.plugins['dimension'].preferencesDict['Filament_Diameter_mm'])
		self.AddSetting(configPanel, "Packing Density", self.plugins['dimension'].preferencesDict['Filament_Packing_Density_ratio'])
		
		nb.AddPage(alterationPanel.alterationPanel(nb), "Start/End-GCode")

		#Preview window, load and slice buttons.
		self.preview3d = preview3d.previewPanel(p)
		
		loadButton = wx.Button(p, -1, 'Load STL')
		sliceButton = wx.Button(p, -1, 'Slice to GCode')
		self.Bind(wx.EVT_BUTTON, self.OnLoadSTL, loadButton)
		self.Bind(wx.EVT_BUTTON, self.OnSlice, sliceButton)

		sizer = wx.GridBagSizer()
		sizer.Add(nb, (0,0), span=(2,1), flag=wx.EXPAND)
		sizer.Add(self.preview3d, (0,1), span=(1,3), flag=wx.EXPAND)
		sizer.Add(loadButton, (1,1))
		sizer.Add(sliceButton, (1,2))
		sizer.AddGrowableCol(2)
		sizer.AddGrowableRow(0)
		p.SetSizer(sizer)

		self.panel = p
		self.sizer = sizer

		self.SetSize((800, 400))
		self.Centre()
		self.Show(True)
	
	def AddTitle(self, panel, name):
		"Add a title row to the configuration panel"
		sizer = panel.GetSizer()
		title = wx.StaticText(panel, -1, name)
		title.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.FONTWEIGHT_BOLD))
		sizer.Add(title, (sizer.GetRows(),1), (1,3), flag=wx.EXPAND)
		sizer.Add(wx.StaticLine(panel), (sizer.GetRows()+1,1), (1,3), flag=wx.EXPAND)
		sizer.SetRows(sizer.GetRows() + 2)
	
	def AddSetting(self, panel, name, setting, help = 'Help: TODO'):
		"Add a setting to the configuration panel"
		sizer = panel.GetSizer()
		sizer.Add(wx.StaticText(panel, -1, name), (sizer.GetRows(),1), flag=wx.ALIGN_CENTER_VERTICAL)
		ctrl = None
		if setting.__class__ is settings.FloatSpin:
			ctrl = wx.TextCtrl(panel, -1, str(setting.value))
		if setting.__class__ is settings.IntSpin:
			ctrl = wx.TextCtrl(panel, -1, str(setting.value))
		if setting.__class__ is settings.BooleanSetting:
			ctrl = wx.CheckBox(panel, -1, '')
			ctrl.SetValue(setting.value)
		if ctrl == None:
			print "No WX control for: " + str(setting), str(setting.__class__)
		else:
			ctrl.setting = setting
			self.controlList.append(ctrl)
			sizer.Add(ctrl, (sizer.GetRows(),2), flag=wx.ALIGN_BOTTOM|wx.EXPAND)
		helpButton = wx.Button(panel, -1, "?", style=wx.BU_EXACTFIT)
		sizer.Add(helpButton, (sizer.GetRows(),3))
		helpButton.SetToolTip(wx.ToolTip(help))
		sizer.SetRows(sizer.GetRows()+1)
		return ctrl

	def OnLoadProfile(self, e):
		dlg=wx.FileDialog(self, "Select profile file to load", self.lastPath, style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
		dlg.SetWildcard("ini files (*.ini)|*.ini")
		if dlg.ShowModal() == wx.ID_OK:
			profileFile = dlg.GetPath()
			self.lastPath = os.path.split(profileFile)[0]
			settings.loadGlobalProfile(profileFile)
			self.updateProfileToControls()
		dlg.Destroy()
	
	def OnSaveProfile(self, e):
		dlg=wx.FileDialog(self, "Select profile file to save", self.lastPath, style=wx.FD_SAVE)
		dlg.SetWildcard("ini files (*.ini)|*.ini")
		if dlg.ShowModal() == wx.ID_OK:
			profileFile = dlg.GetPath()
			self.lastPath = os.path.split(profileFile)[0]
			settings.saveGlobalProfile(profileFile)
			self.updateProfileFromControls()
		dlg.Destroy()
	
	def OnLoadSTL(self, e):
		dlg=wx.FileDialog(self, "Open file to print", self.lastPath, style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
		dlg.SetWildcard("OBJ, STL files (*.stl;*.obj)|*.stl;*.obj")
		if dlg.ShowModal() == wx.ID_OK:
			self.filename=dlg.GetPath()
			if not(os.path.exists(self.filename)):
				return
			self.lastPath = os.path.split(self.filename)[0]
			self.preview3d.loadModelFile(self.filename)
		dlg.Destroy()
	
	def OnSlice(self, e):
		if self.filename == None:
			return
		self.updateProfileFromControls()
		
		#Create a progress panel and add it to the window. The progress panel will start the Skein operation.
		spp = sliceProgessPanel.sliceProgessPanel(self, self.panel, self.filename)
		self.sizer.Add(spp, (len(self.progressPanelList)+2,0), span=(1,4), flag=wx.EXPAND)
		self.sizer.Layout()
		newSize = self.GetSize();
		newSize.IncBy(0, spp.GetSize().GetHeight())
		self.SetSize(newSize)
		self.progressPanelList.append(spp)

	def removeSliceProgress(self, spp):
		self.progressPanelList.remove(spp)
		newSize = self.GetSize();
		newSize.IncBy(0, -spp.GetSize().GetHeight())
		self.SetSize(newSize)
		spp.Destroy()
		for spp in self.progressPanelList:
			self.sizer.Remove(spp)
		i = 2
		for spp in self.progressPanelList:
			self.sizer.Add(spp, (i,0), span=(1,4), flag=wx.EXPAND)
			i += 1
		self.sizer.Layout()
	
	def updateProfileToControls(self):
		"Update the configuration wx controls to show the new configuration settings"
		for pluginName in self.plugins.keys():
			settings.getReadRepository(self.plugins[pluginName])
		settings.saveGlobalProfile(settings.getDefaultProfilePath())
		for ctrl in self.controlList:
			if ctrl.setting.__class__ is settings.BooleanSetting:
				ctrl.SetValue(ctrl.setting.value)
			else:
				ctrl.SetValue(str(ctrl.setting.value))

	def updateProfileFromControls(self):
		"Update the configuration settings with values from the wx controls"
		for ctrl in self.controlList:
			ctrl.setting.setValueToString(ctrl.GetValue())
		for pluginName in self.plugins.keys():
			settings.storeRepository(self.plugins[pluginName])
		settings.saveGlobalProfile(settings.getDefaultProfilePath())
	
	def OnQuit(self, e):
		self.Close()

