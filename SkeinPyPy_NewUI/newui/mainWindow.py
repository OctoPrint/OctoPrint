from __future__ import absolute_import
import __init__

import wx, os, platform, types

from fabmetheus_utilities import settings

from newui import configBase
from newui import advancedConfig
from newui import preview3d
from newui import sliceProgessPanel
from newui import alterationPanel
from newui import validators
from newui import preferencesDialog
from newui import configWizard
from newui import machineCom

def main():
	app = wx.App(False)
	if settings.getPreference('wizardDone', 'False') == 'False':
		configWizard.configWizard()
		settings.putPreference("wizardDone", "True")
	mainWindow()
	app.MainLoop()

class mainWindow(configBase.configWindowBase):
	"Main user interface window"
	def __init__(self):
		super(mainWindow, self).__init__(title='SkeinPyPy')
		
		wx.EVT_CLOSE(self, self.OnClose)
		
		menubar = wx.MenuBar()
		fileMenu = wx.Menu()
		i = fileMenu.Append(-1, 'Load model file...')
		self.Bind(wx.EVT_MENU, self.OnLoadModel, i)
		fileMenu.AppendSeparator()
		i = fileMenu.Append(-1, 'Open Profile...')
		self.Bind(wx.EVT_MENU, self.OnLoadProfile, i)
		i = fileMenu.Append(-1, 'Save Profile...')
		self.Bind(wx.EVT_MENU, self.OnSaveProfile, i)
		fileMenu.AppendSeparator()
		i = fileMenu.Append(-1, 'Preferences...')
		self.Bind(wx.EVT_MENU, self.OnPreferences, i)
		fileMenu.AppendSeparator()
		i = fileMenu.Append(wx.ID_EXIT, 'Quit')
		self.Bind(wx.EVT_MENU, self.OnQuit, i)
		menubar.Append(fileMenu, '&File')
		
		expertMenu = wx.Menu()
		i = expertMenu.Append(-1, 'Open expert settings...')
		self.Bind(wx.EVT_MENU, self.OnExpertOpen, i)
		expertMenu.AppendSeparator()
		i = expertMenu.Append(-1, 'Install default Marlin firmware')
		self.Bind(wx.EVT_MENU, self.OnDefaultMarlinFirmware, i)
		i = expertMenu.Append(-1, 'Install custom firmware')
		self.Bind(wx.EVT_MENU, self.OnCustomFirmware, i)
		expertMenu.AppendSeparator()
		i = expertMenu.Append(-1, 'ReRun first run wizard...')
		self.Bind(wx.EVT_MENU, self.OnFirstRunWizard, i)
		menubar.Append(expertMenu, 'Expert')
		self.SetMenuBar(menubar)
		
		self.lastPath = ""
		self.filename = settings.getPreference('lastFile', "None")
		self.progressPanelList = []

		#Preview window
		self.preview3d = preview3d.previewPanel(self)

		#Main tabs
		nb = wx.Notebook(self)
		
		(left, right) = self.CreateConfigTab(nb, 'Print config')
		
		configBase.TitleRow(left, "Accuracy")
		c = configBase.SettingRow(left, "Layer height (mm)", 'layer_height', '0.2', 'Layer height in millimeters.\n0.2 is a good value for quick prints.\n0.1 gives high quality prints.')
		validators.validFloat(c, 0.0)
		validators.warningAbove(c, 0.31, "Thicker layers then 0.3mm usually give bad results and are not recommended.")
		c = configBase.SettingRow(left, "Wall thickness (mm)", 'wall_thickness', '0.8', 'Thickness of the walls.\nThis is used in combination with the nozzle size to define the number\nof perimeter lines and the thickness of those perimeter lines.')
		validators.validFloat(c, 0.0)
		validators.wallThicknessValidator(c)
		configBase.settingNotify(c, self.preview3d.updateWallLineWidth)
		
		configBase.TitleRow(left, "Fill")
		c = configBase.SettingRow(left, "Bottom/Top thickness (mm)", 'solid_layer_thickness', '0.6', 'This controls the thickness of the bottom and top layers, the amount of solid layers put down is calculated by the layer thickness and this value.\nHaving this value a multiply of the layer thickness makes sense. And keep it near your wall thickness to make an evenly strong part.')
		validators.validFloat(c, 0.0)
		c = configBase.SettingRow(left, "Fill Density (%)", 'fill_density', '20', 'This controls how densily filled the insides of your print will be. For a solid part use 100%, for an empty part use 0%. A value around 20% is usually enough')
		validators.validFloat(c, 0.0, 100.0)
		
		configBase.TitleRow(left, "Skirt")
		c = configBase.SettingRow(left, "Line count", 'skirt_line_count', '1', 'The skirt is a line drawn around the object at the first layer. This helps to prime your extruder, and to see if the object fits on your platform.\nSetting this to 0 will disable the skirt.')
		validators.validInt(c, 0, 10)
		c = configBase.SettingRow(left, "Start distance (mm)", 'skirt_gap', '6.0', 'The distance between the skirt and the first layer.\nThis is the minimal distance, multiple skirt lines will be put outwards from this distance.')
		validators.validFloat(c, 0.0)

		configBase.TitleRow(right, "Speed")
		c = configBase.SettingRow(right, "Print speed (mm/s)", 'print_speed', '50', 'Speed at which printing happens. A well adjusted Ultimaker can reach 150mm/s, but for good quality prints you want to print slower. Printing speed depends on a lot of factors. So you will be experimenting with optimal settings for this.')
		validators.validFloat(c, 1.0)
		validators.warningAbove(c, 150.0, "It is highly unlikely that your machine can achieve a printing speed above 150mm/s")
		
		configBase.TitleRow(right, "Temperature")
		c = configBase.SettingRow(right, "Printing temperature", 'print_temperature', '0', 'Temperature used for printing. Set at 0 to pre-heat yourself')
		validators.validFloat(c, 0.0, 340.0)
		validators.warningAbove(c, 260.0, "Temperatures above 260C could damage your machine, be careful!")
		
		configBase.TitleRow(right, "Support")
		c = configBase.SettingRow(right, "Support type", 'support', ['None', 'Exterior Only', 'Everywhere', 'Empty Layers Only'], 'Type of support structure build.\nNone does not do any support.\nExterior only only creates support on the outside.\nEverywhere creates support even on the insides of the model.\nOnly on empty layers is for stacked objects.')

		configBase.TitleRow(right, "Filament")
		c = configBase.SettingRow(right, "Diameter (mm)", 'filament_diameter', '2.89', 'Diameter of your filament, as accurately as possible.\nIf you cannot measure this value you will have to callibrate it, a higher number means less extrusion, a smaller number generates more extrusion.')
		validators.validFloat(c, 1.0)
		validators.warningAbove(c, 3.5, "Are you sure your filament is that thick? Normal filament is around 3mm or 1.75mm.")
		c = configBase.SettingRow(right, "Packing Density", 'filament_density', '1.00', 'Packing density of your filament. This should be 1.00 for PLA and 0.85 for ABS')
		validators.validFloat(c, 0.5, 1.5)
		
		(left, right) = self.CreateConfigTab(nb, 'Machine config')
		
		configBase.TitleRow(left, "Machine size")
		c = configBase.SettingRow(left, "Machine center X (mm)", 'machine_center_x', '100', 'The center of your machine, your print will be placed at this location')
		validators.validInt(c, 10)
		configBase.settingNotify(c, self.preview3d.updateCenterX)
		c = configBase.SettingRow(left, "Machine center Y (mm)", 'machine_center_y', '100', 'The center of your machine, your print will be placed at this location')
		validators.validInt(c, 10)
		configBase.settingNotify(c, self.preview3d.updateCenterY)

		configBase.TitleRow(left, "Machine nozzle")
		c = configBase.SettingRow(left, "Nozzle size (mm)", 'nozzle_size', '0.4', 'The nozzle size is very important, this is used to calculate the line width of the infill, and used to calculate the amount of outside wall lines and thickness for the wall thickness you entered in the print settings.')
		validators.validFloat(c, 0.1, 1.0)
		configBase.settingNotify(c, self.preview3d.updateWallLineWidth)
		configBase.settingNotify(c, self.preview3d.updateInfillLineWidth)

		configBase.TitleRow(left, "Retraction")
		c = configBase.SettingRow(left, "Minimal travel (mm)", 'retraction_min_travel', '5.0', 'Minimal amount of travel needed for a retraction to happen at all. To make sure you do not get a lot of retractions in a small area')
		validators.validFloat(c, 0.0)
		c = configBase.SettingRow(left, "Speed (mm/s)", 'retraction_speed', '13.5', 'Speed at which the filament is retracted')
		validators.validFloat(c, 0.1)
		c = configBase.SettingRow(left, "Distance (mm)", 'retraction_amount', '0.0', 'Amount of retraction, set at 0 for no retraction at all.')
		validators.validFloat(c, 0.0)
		c = configBase.SettingRow(left, "Extra length on start (mm)", 'retraction_extra', '0.0', 'Extra extrusion amount when restarting after a retraction, to better "Prime" your extruder')
		validators.validFloat(c, 0.0)

		configBase.TitleRow(right, "Speed")
		c = configBase.SettingRow(right, "Travel speed (mm/s)", 'travel_speed', '150', 'Speed at which travel moves are done')
		validators.validFloat(c, 1.0)
		validators.warningAbove(c, 300.0, "It is highly unlikely that your machine can achieve a travel speed above 150mm/s")
		c = configBase.SettingRow(right, "Max Z speed (mm/s)", 'max_z_speed', '1.0', 'Speed at which Z moves are done.')
		validators.validFloat(c, 0.5)
		c = configBase.SettingRow(right, "Bottom layer speed (mm/s)", 'bottom_layer_speed', '25', 'Print speed for the bottom layer, you want to print the first layer slower so it sticks better to the printer bed.')
		validators.validFloat(c, 0.0)

		configBase.TitleRow(right, "Cool")
		c = configBase.SettingRow(right, "Minimal layer time (sec)", 'cool_min_layer_time', '10', 'Minimum time spend in a layer, gives the layer time to cool down before the next layer is put on top. If the layer will be placed down too fast the printer will slow down to make sure it has spend atleast this amount of seconds printing this layer.')
		validators.validFloat(c, 0.0)

		nb.AddPage(alterationPanel.alterationPanel(nb), "Start/End-GCode")

		(left, right) = self.CreateConfigTab(nb, '3D Model')
		configBase.TitleRow(left, "Scale")
		c = configBase.SettingRow(left, "Scale", 'model_scale', '1.0', '')
		validators.validFloat(c, 0.01)
		configBase.settingNotify(c, self.preview3d.updateModelTransform)
		configBase.TitleRow(left, "Flip")
		c = configBase.SettingRow(left, "Flip X", 'flip_x', False, '')
		configBase.settingNotify(c, self.preview3d.updateModelTransform)
		c = configBase.SettingRow(left, "Flip Y", 'flip_y', False, '')
		configBase.settingNotify(c, self.preview3d.updateModelTransform)
		c = configBase.SettingRow(left, "Flip Z", 'flip_z', False, '')
		configBase.settingNotify(c, self.preview3d.updateModelTransform)
		configBase.TitleRow(right, "Rotate")
		c = configBase.SettingRow(right, "Rotate (deg)", 'model_rotate_base', '0', '')
		validators.validFloat(c)
		configBase.settingNotify(c, self.preview3d.updateModelTransform)

		# load and slice buttons.
		loadButton = wx.Button(self, -1, 'Load Model')
		sliceButton = wx.Button(self, -1, 'Slice to GCode')
		self.Bind(wx.EVT_BUTTON, self.OnLoadModel, loadButton)
		self.Bind(wx.EVT_BUTTON, self.OnSlice, sliceButton)
		#Also bind double clicking the 3D preview to load an STL file.
		self.preview3d.glCanvas.Bind(wx.EVT_LEFT_DCLICK, self.OnLoadModel, self.preview3d.glCanvas)

		#Main sizer, to position the preview window, buttons and tab control
		sizer = wx.GridBagSizer()
		self.SetSizer(sizer)
		sizer.Add(nb, (0,0), span=(1,1), flag=wx.EXPAND)
		sizer.Add(self.preview3d, (0,1), span=(1,3), flag=wx.EXPAND)
		sizer.AddGrowableCol(2)
		sizer.AddGrowableRow(0)
		sizer.Add(loadButton, (1,1), flag=wx.RIGHT, border=5)
		sizer.Add(sliceButton, (1,2))
		self.sizer = sizer

		if self.filename != "None":
			self.preview3d.loadModelFile(self.filename)
			self.lastPath = os.path.split(self.filename)[0]

		self.updateProfileToControls()

		self.Fit()
		self.Centre()
		self.Show(True)
	
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
	
	def OnPreferences(self, e):
		prefDialog = preferencesDialog.preferencesDialog(self)
		prefDialog.Centre()
		prefDialog.Show(True)
	
	def OnDefaultMarlinFirmware(self, e):
		machineCom.InstallFirmware(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../firmware/default.hex"), settings.getPreference('serial_port', 'AUTO'))

	def OnCustomFirmware(self, e):
		dlg=wx.FileDialog(self, "Open firmware to upload", self.lastPath, style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
		dlg.SetWildcard("HEX file (*.hex)|*.hex")
		if dlg.ShowModal() == wx.ID_OK:
			filename = dlg.GetPath()
			if not(os.path.exists(filename)):
				return
			#For some reason my Ubuntu 10.10 crashes here.
			machineCom.InstallFirmware(filename, settings.getPreference('serial_port', 'AUTO'))

	def OnFirstRunWizard(self, e):
		configWizard.configWizard()
		self.updateProfileToControls()

	def OnLoadModel(self, e):
		dlg=wx.FileDialog(self, "Open file to print", self.lastPath, style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
		dlg.SetWildcard("STL files (*.stl)|*.stl")
		if dlg.ShowModal() == wx.ID_OK:
			self.filename=dlg.GetPath()
			settings.putPreference('lastFile', self.filename)
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

	def OnExpertOpen(self, e):
		acw = advancedConfig.advancedConfigWindow()
		acw.Centre()
		acw.Show(True)

	def removeSliceProgress(self, spp):
		self.progressPanelList.remove(spp)
		newSize = self.GetSize();
		newSize.IncBy(0, -spp.GetSize().GetHeight())
		self.SetSize(newSize)
		self.sizer.Remove(spp)
		spp.Destroy()
		for spp in self.progressPanelList:
			self.sizer.Remove(spp)
		i = 2
		for spp in self.progressPanelList:
			self.sizer.Add(spp, (i,0), span=(1,4), flag=wx.EXPAND)
			i += 1
		self.sizer.Layout()

	def OnQuit(self, e):
		self.Close()
	
	def OnClose(self, e):
		settings.saveGlobalProfile(settings.getDefaultProfilePath())
		self.Destroy()
