from __future__ import absolute_import
import __init__

import wx, os, platform, types
import ConfigParser

from fabmetheus_utilities import settings

from newui import preview3d
from newui import sliceProgessPanel
from newui import alterationPanel
from newui import validators

def main():
	app = wx.App(False)
	mainWindow()
	app.MainLoop()

class mainWindow(wx.Frame):
	"Main user interface window"
	def __init__(self):
		super(mainWindow, self).__init__(None, title='SkeinPyPy')
		
		wx.EVT_CLOSE(self, self.OnClose)
		
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
		self.filename = getPreference('lastFile', None)
		self.progressPanelList = []
		self.settingControlList = []

		#Preview window
		self.preview3d = preview3d.previewPanel(self)

		#Main tabs
		nb = wx.Notebook(self)
		
		(left, right) = self.CreateConfigTab(nb, 'Print config')
		
		TitleRow(left, "Accuracy")
		c = SettingRow(left, "Layer height (mm)", 'layer_height', '0.2', 'Layer height in millimeters.\n0.2 is a good value for quick prints.\n0.1 gives high quality prints.')
		validators.validFloat(c, 0.0)
		validators.warningAbove(c, 0.31, "Thicker layers then 0.3mm usually give bad results and are not recommended.")
		c = SettingRow(left, "Wall thickness (mm)", 'wall_thickness', '0.8', 'Thickness of the walls.\nThis is used in combination with the nozzle size to define the number\nof perimeter lines and the thickness of those perimeter lines.')
		validators.validFloat(c, 0.0)
		validators.wallThicknessValidator(c)
		
		TitleRow(left, "Fill")
		c = SettingRow(left, "Bottom/Top thickness (mm)", 'solid_layer_thickness', '0.6', 'This controls the thickness of the bottom and top layers, the amount of solid layers put down is calculated by the layer thickness and this value.\nHaving this value a multiply of the layer thickness makes sense. And keep it near your wall thickness to make an evenly strong part.')
		validators.validFloat(c, 0.0)
		c = SettingRow(left, "Fill Density (%)", 'fill_density', '20', 'This controls how densily filled the insides of your print will be. For a solid part use 100%, for an empty part use 0%. A value around 20% is usually enough')
		validators.validFloat(c, 0.0, 100.0)
		
		TitleRow(left, "Skirt")
		c = SettingRow(left, "Line count", 'skirt_line_count', '1', 'The skirt is a line drawn around the object at the first layer. This helps to prime your extruder, and to see if the object fits on your platform.\nSetting this to 0 will disable the skirt.')
		validators.validInt(c, 0, 10)
		c = SettingRow(left, "Start distance (mm)", 'skirt_gap', '6.0', 'The distance between the skirt and the first layer.\nThis is the minimal distance, multiple skirt lines will be put outwards from this distance.')
		validators.validFloat(c, 0.0)

		TitleRow(right, "Speed")
		c = SettingRow(right, "Print speed (mm/s)", 'print_speed', '50')
		validators.validFloat(c, 1.0)
		validators.warningAbove(c, 150.0, "It is highly unlikely that your machine can achieve a printing speed above 150mm/s")
		
		#Printing temperature is a problem right now, as our start code depends on a heated head.
		#TitleRow(right, "Temperature")
		#c = SettingRow(right, "Printing temperature", 'print_temperature', '0', 'Temperature used for printing. Set at 0 to pre-heat yourself')
		#validators.validFloat(c, 0.0, 350.0)
		#validators.warningAbove(c, 260.0, "Temperatures above 260C could damage your machine.")
		
		TitleRow(right, "Support")
		c = SettingRow(right, "Support type", 'support', ['None', 'Exterior only', 'Everywhere', 'Empty layers only'], 'Type of support structure build.\nNone does not do any support.\nExterior only only creates support on the outside.\nEverywhere creates support even on the insides of the model.\nOnly on empty layers is for stacked objects.')
		
		(left, right) = self.CreateConfigTab(nb, 'Machine && Filament')
		
		TitleRow(left, "Machine size")
		c = SettingRow(left, "Machine center X (mm)", 'machine_center_x', '100', 'The center of your machine, your print will be placed at this location')
		validators.validInt(c, 10)
		settingNotify(c, self.preview3d.updateCenterX)
		c = SettingRow(left, "Machine center Y (mm)", 'machine_center_y', '100', 'The center of your machine, your print will be placed at this location')
		validators.validInt(c, 10)
		settingNotify(c, self.preview3d.updateCenterY)
		#self.AddSetting(left, "Width (mm)", settings.IntSpin().getFromValue(10, "machine_width", None, 1000, 205))
		#self.AddSetting(left, "Depth (mm)", settings.IntSpin().getFromValue(10, "machine_depth", None, 1000, 205))
		#self.AddSetting(left, "Height (mm)", settings.IntSpin().getFromValue(10, "machine_height", None, 1000, 200))

		TitleRow(left, "Machine nozzle")
		c = SettingRow(left, "Nozzle size (mm)", 'nozzle_size', '0.4')
		validators.validFloat(c, 0.1, 1.0)

		TitleRow(left, "Retraction")
		c = SettingRow(left, "Minimal travel (mm)", 'retraction_min_travel', '5.0')
		validators.validFloat(c, 0.0)
		c = SettingRow(left, "Speed (mm/s)", 'retraction_speed', '13.5')
		validators.validFloat(c, 0.1)
		c = SettingRow(left, "Distance (mm)", 'retraction_amount', '0.0')
		validators.validFloat(c, 0.0)
		c = SettingRow(left, "Extra length on start (mm)", 'retraction_extra', '0.0')
		validators.validFloat(c, 0.0)

		TitleRow(right, "Speed")
		c = SettingRow(right, "Travel speed (mm/s)", 'travel_speed', '150')
		validators.validFloat(c, 1.0)
		validators.warningAbove(c, 300.0, "It is highly unlikely that your machine can achieve a travel speed above 150mm/s")
		c = SettingRow(right, "Max Z speed (mm/s)", 'max_z_speed', '1.0')
		validators.validFloat(c, 0.5)
		c = SettingRow(right, "Bottom layer speed", 'bottom_layer_speed', '25')
		validators.validFloat(c, 0.0)

		TitleRow(right, "Cool")
		#c = SettingRow(right, "Cool type", self.plugins['cool'].preferencesDict['Cool_Type'])
		c = SettingRow(right, "Minimal layer time (sec)", 'cool_min_layer_time', '10', 'Minimum time spend in a layer, gives the layer time to cool down before the next layer is put on top. If the layer will be placed down too fast the printer will slow down to make sure it has spend atleast this amount of seconds printing this layer.')
		validators.validFloat(c, 0.0)

		TitleRow(right, "Filament")
		c = SettingRow(right, "Diameter (mm)", 'filament_diameter', '2.98', 'Diameter of your filament, as accurately as possible.\nIf you cannot measure this value you will have to callibrate it, a higher number means less extrusion, a smaller number generates more extrusion.')
		validators.validFloat(c, 1.0)
		c = SettingRow(right, "Packing Density", 'filament_density', '1.00', 'Packing density of your filament. This should be 1.00 for PLA and 0.85 for ABS')
		validators.validFloat(c, 0.5, 1.5)
		
		nb.AddPage(alterationPanel.alterationPanel(nb), "Start/End-GCode")

		# load and slice buttons.
		loadButton = wx.Button(self, -1, 'Load STL')
		sliceButton = wx.Button(self, -1, 'Slice to GCode')
		self.Bind(wx.EVT_BUTTON, self.OnLoadSTL, loadButton)
		self.Bind(wx.EVT_BUTTON, self.OnSlice, sliceButton)

		#Main sizer, to position the preview window, buttons and tab control
		sizer = wx.GridBagSizer()
		self.SetSizer(sizer)
		sizer.Add(nb, (0,0), span=(1,1), flag=wx.EXPAND)
		sizer.Add(self.preview3d, (0,1), span=(1,3), flag=wx.EXPAND)
		sizer.AddGrowableCol(2)
		sizer.AddGrowableRow(0)
		sizer.Add(loadButton, (1,1))
		sizer.Add(sliceButton, (1,2))
		self.sizer = sizer

		#Create the popup window
		self.popup = wx.PopupWindow(self, wx.BORDER_SIMPLE)
		self.popup.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_INFOBK))
		self.popup.text = wx.StaticText(self.popup, -1, '');
		self.popup.sizer = wx.BoxSizer()
		self.popup.sizer.Add(self.popup.text, flag=wx.EXPAND|wx.ALL, border=1)
		self.popup.SetSizer(self.popup.sizer)

		if self.filename != None:
			self.preview3d.loadModelFile(self.filename)
			self.lastPath = os.path.split(self.filename)[0]
		
		self.updateProfileToControls()

		self.Fit()
		self.Centre()
		self.Show(True)
	
	def CreateConfigTab(self, nb, name):
		configPanel = wx.Panel(nb);
		nb.AddPage(configPanel, name)
		leftConfigPanel = wx.Panel(configPanel)
		rightConfigPanel = wx.Panel(configPanel)
		sizer = wx.GridBagSizer(2, 2)
		leftConfigPanel.SetSizer(sizer)
		sizer = wx.GridBagSizer(2, 2)
		rightConfigPanel.SetSizer(sizer)
		sizer = wx.BoxSizer(wx.HORIZONTAL)
		configPanel.SetSizer(sizer)
		sizer.Add(leftConfigPanel)
		sizer.Add(rightConfigPanel)
		leftConfigPanel.main = self
		rightConfigPanel.main = self
		return leftConfigPanel, rightConfigPanel
	
	def OnPopupDisplay(self, setting):
		x, y = setting.ctrl.ClientToScreenXY(0, 0)
		sx, sy = setting.ctrl.GetSizeTuple()
		if setting.validationMsg != '':
			self.popup.text.SetLabel(setting.validationMsg + '\n\n' + setting.helpText)
		else:
			self.popup.text.SetLabel(setting.helpText)
		self.popup.text.Wrap(350)
		if platform.system() == "Windows":
			#for some reason, under windows, the popup is relative to the main window...
			wx, wy = self.ClientToScreenXY(0, 0)
			x -= wx
			y -= wy
		self.popup.SetPosition((x, y+sy))
		self.popup.Fit()
		self.popup.Show(True)
		
	def OnPopupHide(self, e):
		self.popup.Show(False)
	
	def OnSettingTextChange(self, e):
		for validator in self.validators:
			res, err = validator.validate()
			if res == validators.ERROR:
				validator.ctrl.SetBackgroundColour('Red')
			elif res == validators.WARNING:
				validator.ctrl.SetBackgroundColour('Orange')
			else:
				validator.ctrl.SetBackgroundColour(wx.NullColor)

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
		dlg.Destroy()
	
	def OnLoadSTL(self, e):
		dlg=wx.FileDialog(self, "Open file to print", self.lastPath, style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
		dlg.SetWildcard("OBJ, STL files (*.stl;*.obj)|*.stl;*.obj")
		if dlg.ShowModal() == wx.ID_OK:
			self.filename=dlg.GetPath()
			putPreference('lastFile', self.filename)
			if not(os.path.exists(self.filename)):
				return
			self.lastPath = os.path.split(self.filename)[0]
			self.preview3d.loadModelFile(self.filename)
		dlg.Destroy()
	
	def OnSlice(self, e):
		if self.filename == None:
			return
		settings.saveGlobalProfile(settings.getDefaultProfilePath())
		
		#Create a progress panel and add it to the window. The progress panel will start the Skein operation.
		spp = sliceProgessPanel.sliceProgessPanel(self, self, self.filename)
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
		for setting in self.settingControlList:
			setting.SetValue(settings.getSetting(setting.configName))

	def OnQuit(self, e):
		self.Close()
	
	def OnClose(self, e):
		settings.saveGlobalProfile(settings.getDefaultProfilePath())
		self.Destroy()

class TitleRow():
	def __init__(self, panel, name):
		"Add a title row to the configuration panel"
		sizer = panel.GetSizer()
		self.title = wx.StaticText(panel, -1, name)
		self.title.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.FONTWEIGHT_BOLD))
		sizer.Add(self.title, (sizer.GetRows(),sizer.GetCols()), (1,3), flag=wx.EXPAND)
		sizer.Add(wx.StaticLine(panel), (sizer.GetRows()+1,sizer.GetCols()), (1,3), flag=wx.EXPAND)
		sizer.SetRows(sizer.GetRows() + 2)

class SettingRow():
	def __init__(self, panel, label, configName, defaultValue = '', helpText = 'Help: TODO'):
		"Add a setting to the configuration panel"
		sizer = panel.GetSizer()
		x = sizer.GetRows()
		y = sizer.GetCols()
		
		self.validators = []
		self.validationMsg = ''
		self.helpText = helpText
		self.configName = configName
		
		self.label = wx.StaticText(panel, -1, label)
		if isinstance(defaultValue, types.StringTypes):
			self.ctrl = wx.TextCtrl(panel, -1, settings.getSetting(configName, defaultValue))
		else:
			self.ctrl = wx.ComboBox(panel, -1, settings.getSetting(configName, defaultValue[0]), choices=defaultValue, style=wx.CB_DROPDOWN|wx.CB_READONLY)
		#self.helpButton = wx.Button(panel, -1, "?", style=wx.BU_EXACTFIT)
		#self.helpButton.SetToolTip(wx.ToolTip(help))
		
		self.ctrl.Bind(wx.EVT_TEXT, self.OnSettingTextChange)
		self.ctrl.Bind(wx.EVT_ENTER_WINDOW, lambda e: panel.main.OnPopupDisplay(self))
		self.ctrl.Bind(wx.EVT_LEAVE_WINDOW, panel.main.OnPopupHide)
		
		panel.main.settingControlList.append(self)
		
		sizer.Add(self.label, (x,y), flag=wx.ALIGN_CENTER_VERTICAL)
		sizer.Add(self.ctrl, (x,y+1), flag=wx.ALIGN_BOTTOM|wx.EXPAND)
		#sizer.Add(helpButton, (x,y+2))
		sizer.SetRows(x+1)

	def OnSettingTextChange(self, e):
		result = validators.SUCCESS
		msgs = []
		for validator in self.validators:
			res, err = validator.validate()
			if res == validators.ERROR:
				result = res
			elif res == validators.WARNING and result != validators.ERROR:
				result = res
			if res != validators.SUCCESS:
				print err
				msgs.append(err)
		if result == validators.ERROR:
			self.ctrl.SetBackgroundColour('Red')
		elif result == validators.WARNING:
			self.ctrl.SetBackgroundColour('Yellow')
		else:
			self.ctrl.SetBackgroundColour(wx.NullColour)
		self.ctrl.Refresh()
		settings.putSetting(self.configName, self.GetValue())
		self.validationMsg = '\n'.join(msgs)

	def GetValue(self):
		return self.ctrl.GetValue()

	def SetValue(self, value):
		self.ctrl.SetValue(value)

#Settings notify works as a validator, but instead of validating anything, it calls another function, which can use the value.
class settingNotify():
	def __init__(self, setting, func):
		self.setting = setting
		self.setting.validators.append(self)
		self.func = func
	
	def validate(self):
		try:
			f = float(self.setting.GetValue())
			self.func(f)
			return validators.SUCCESS, ''
		except ValueError:
			return validators.SUCCESS, ''

def getPreferencePath():
	return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../preferences.ini"))

def getPreference(name, default):
	if not globals().has_key('globalPreferenceParser'):
		globalPreferenceParser = ConfigParser.ConfigParser()
		globalPreferenceParser.read(getPreferencePath())
	if not globalPreferenceParser.has_option('preference', name):
		if not globalPreferenceParser.has_section('preference'):
			globalPreferenceParser.add_section('preference')
		globalPreferenceParser.set('preference', name, str(default))
		print name + " not found in profile, so using default"
		return default
	return globalPreferenceParser.get('preference', name)

def putPreference(name, value):
	#Check if we have a configuration file loaded, else load the default.
	if not globals().has_key('globalPreferenceParser'):
		globalPreferenceParser = ConfigParser.ConfigParser()
		globalPreferenceParser.read(getPreferencePath())
	if not globalPreferenceParser.has_section('preference'):
		globalPreferenceParser.add_section('preference')
	globalPreferenceParser.set('preference', name, str(value))
	globalPreferenceParser.write(open(getPreferencePath(), 'w'))
