from __future__ import absolute_import
import __init__

import wx, os, platform, types, webbrowser

from gui import configBase
from gui import preview3d
from gui import sliceProgessPanel
from gui import preferencesDialog
from gui import configWizard
from gui import firmwareInstall
from gui import printWindow
from gui import icon
from util import validators
from util import profile
from util import version
from util import sliceRun

class simpleModeWindow(configBase.configWindowBase):
	"Main user interface window for Quickprint mode"
	def __init__(self):
		super(simpleModeWindow, self).__init__(title='Cura - Quickprint - ' + version.getVersion())
		
		wx.EVT_CLOSE(self, self.OnClose)
		#self.SetIcon(icon.getMainIcon())
		
		menubar = wx.MenuBar()
		fileMenu = wx.Menu()
		i = fileMenu.Append(-1, 'Load model file...')
		self.Bind(wx.EVT_MENU, self.OnLoadModel, i)
		fileMenu.AppendSeparator()
		i = fileMenu.Append(-1, 'Preferences...')
		self.Bind(wx.EVT_MENU, self.OnPreferences, i)
		fileMenu.AppendSeparator()
		i = fileMenu.Append(wx.ID_EXIT, 'Quit')
		self.Bind(wx.EVT_MENU, self.OnQuit, i)
		menubar.Append(fileMenu, '&File')
		
		toolsMenu = wx.Menu()
		i = toolsMenu.Append(-1, 'Switch to Normal mode...')
		self.Bind(wx.EVT_MENU, self.OnNormalSwitch, i)
		menubar.Append(toolsMenu, 'Normal mode')
		
		helpMenu = wx.Menu()
		i = helpMenu.Append(-1, 'Online documentation...')
		self.Bind(wx.EVT_MENU, lambda e: webbrowser.open('https://daid.github.com/Cura'), i)
		i = helpMenu.Append(-1, 'Report a problem...')
		self.Bind(wx.EVT_MENU, lambda e: webbrowser.open('https://github.com/daid/Cura/issues'), i)
		menubar.Append(helpMenu, 'Help')
		self.SetMenuBar(menubar)
		
		if profile.getPreference('lastFile') != '':
			self.filelist = profile.getPreference('lastFile').split(';')
			self.SetTitle(self.filelist[-1] + ' - Cura - ' + version.getVersion())
		else:
			self.filelist = []
		self.progressPanelList = []

		#Preview window
		self.preview3d = preview3d.previewPanel(self)

		configPanel = wx.Panel(self)
		self.printTypeNormal = wx.RadioButton(configPanel, -1, 'Normal quality print', style=wx.RB_GROUP)
		self.printTypeLow = wx.RadioButton(configPanel, -1, 'Fast low quality print')
		self.printTypeHigh = wx.RadioButton(configPanel, -1, 'High quality print')
		self.printTypeJoris = wx.RadioButton(configPanel, -1, 'Thin walled cup or vase')

		self.printMaterialPLA = wx.RadioButton(configPanel, -1, 'PLA', style=wx.RB_GROUP)
		self.printMaterialABS = wx.RadioButton(configPanel, -1, 'ABS')
		self.printMaterialDiameter = wx.TextCtrl(configPanel, -1, profile.getProfileSetting('filament_diameter'))
		
		self.printSupport = wx.CheckBox(configPanel, -1, 'Print support structure')
		
		sizer = wx.GridBagSizer()
		configPanel.SetSizer(sizer)

		sb = wx.StaticBox(configPanel, label="Select a print type:")
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		boxsizer.Add(self.printTypeNormal)
		boxsizer.Add(self.printTypeLow)
		boxsizer.Add(self.printTypeHigh)
		boxsizer.Add(self.printTypeJoris)
		sizer.Add(boxsizer, (0,0), flag=wx.EXPAND)

		sb = wx.StaticBox(configPanel, label="Material:")
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		boxsizer.Add(self.printMaterialPLA)
		boxsizer.Add(self.printMaterialABS)
		boxsizer.Add(wx.StaticText(configPanel, -1, 'Diameter:'))
		boxsizer.Add(self.printMaterialDiameter)
		sizer.Add(boxsizer, (1,0), flag=wx.EXPAND)

		sb = wx.StaticBox(configPanel, label="Other:")
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		boxsizer.Add(self.printSupport)
		sizer.Add(boxsizer, (2,0), flag=wx.EXPAND)

		# load and slice buttons.
		loadButton = wx.Button(self, -1, 'Load Model')
		sliceButton = wx.Button(self, -1, 'Prepare print')
		printButton = wx.Button(self, -1, 'Print')
		self.Bind(wx.EVT_BUTTON, self.OnLoadModel, loadButton)
		self.Bind(wx.EVT_BUTTON, self.OnSlice, sliceButton)
		self.Bind(wx.EVT_BUTTON, self.OnPrint, printButton)
		#Also bind double clicking the 3D preview to load an STL file.
		self.preview3d.glCanvas.Bind(wx.EVT_LEFT_DCLICK, self.OnLoadModel, self.preview3d.glCanvas)

		#Main sizer, to position the preview window, buttons and tab control
		sizer = wx.GridBagSizer()
		self.SetSizer(sizer)
		sizer.Add(configPanel, (0,0), span=(1,1), flag=wx.EXPAND)
		sizer.Add(self.preview3d, (0,1), span=(1,3), flag=wx.EXPAND)
		sizer.AddGrowableCol(2)
		sizer.AddGrowableRow(0)
		sizer.Add(loadButton, (1,1), flag=wx.RIGHT, border=5)
		sizer.Add(sliceButton, (1,2), flag=wx.RIGHT, border=5)
		sizer.Add(printButton, (1,3), flag=wx.RIGHT, border=5)
		self.sizer = sizer

		if len(self.filelist) > 0:
			self.preview3d.loadModelFiles(self.filelist)

		self.updateProfileToControls()

		self.Fit()
		self.SetMinSize(self.GetSize())
		self.Centre()
		self.Show(True)
	
	def OnPreferences(self, e):
		prefDialog = preferencesDialog.preferencesDialog(self)
		prefDialog.Centre()
		prefDialog.Show(True)
	
	def OnDefaultMarlinFirmware(self, e):
		firmwareInstall.InstallFirmware()

	def OnCustomFirmware(self, e):
		dlg=wx.FileDialog(self, "Open firmware to upload", os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
		dlg.SetWildcard("HEX file (*.hex)|*.hex;*.HEX")
		if dlg.ShowModal() == wx.ID_OK:
			filename = dlg.GetPath()
			if not(os.path.exists(filename)):
				return
			#For some reason my Ubuntu 10.10 crashes here.
			firmwareInstall.InstallFirmware(filename)

	def OnFirstRunWizard(self, e):
		configWizard.configWizard()
		self.updateProfileToControls()

	def OnLoadModel(self, e):
		dlg=wx.FileDialog(self, "Open file to print", os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
		dlg.SetWildcard(meshLoader.wildcardFilter())
		if dlg.ShowModal() == wx.ID_OK:
			self.filelist = [dlg.GetPath()]
			profile.putPreference('lastFile', ';'.join(self.filelist))
			self.preview3d.loadModelFiles(self.filelist, True)
			self.preview3d.setViewMode("Normal")
		dlg.Destroy()
	
	def OnSlice(self, e):
		if len(self.filelist) < 1:
			wx.MessageBox('You need to load a file before you can slice it.', 'Print error', wx.OK | wx.ICON_INFORMATION)
			return
		#save the current profile so we can put it back latter
		oldProfile = profile.getGlobalProfileString()
		
		put = profile.putProfileSetting
		get = profile.getProfileSetting

		put('layer_height', '0.2')
		put('wall_thickness', '0.8')
		put('solid_layer_thickness', '0.6')
		put('fill_density', '20')
		put('skirt_line_count', '1')
		put('skirt_gap', '6.0')
		put('print_speed', '50')
		put('print_temperature', '220')
		put('support', 'None')
		#put('machine_center_x', '100')
		#put('machine_center_y', '100')
		put('retraction_enable', 'True')
		put('retraction_min_travel', '5.0')
		put('retraction_speed', '13.5')
		put('retraction_amount', '4.5')
		put('retraction_extra', '0.0')
		put('travel_speed', '150')
		put('max_z_speed', '3.0')
		put('bottom_layer_speed', '25')
		put('cool_min_layer_time', '10')
		put('fan_enabled', 'True')
		put('fan_layer', '1')
		put('fan_speed', '100')
		#put('model_scale', '1.0')
		#put('flip_x', 'False')
		#put('flip_y', 'False')
		#put('flip_z', 'False')
		#put('model_rotate_base', '0')
		#put('model_multiply_x', '1')
		#put('model_multiply_y', '1')
		put('extra_base_wall_thickness', '0.0')
		put('sequence', 'Loops > Perimeter > Infill')
		put('force_first_layer_sequence', 'True')
		put('infill_type', 'Line')
		put('solid_top', 'True')
		put('fill_overlap', '15')
		put('support_rate', '50')
		put('support_distance', '0.5')
		put('joris', 'False')
		put('cool_min_feedrate', '5')
		put('bridge_speed', '100')
		put('raft_margin', '5')
		put('raft_base_material_amount', '100')
		put('raft_interface_material_amount', '100')
		put('bottom_thickness', '0.0')

		if self.printSupport.GetValue():
			put('support', 'Exterior Only')

		nozzle_size = float(get('nozzle_size'))
		if self.printTypeNormal.GetValue():
			put('wall_thickness', nozzle_size * 2.0)
			put('layer_height', '0.2')
			put('fill_density', '20')
		elif self.printTypeLow.GetValue():
			put('wall_thickness', nozzle_size * 1.0)
			put('layer_height', '0.3')
			put('fill_density', '10')
			put('print_speed', '80')
			put('bottom_layer_speed', '40')
		elif self.printTypeHigh.GetValue():
			put('wall_thickness', nozzle_size * 2.0)
			put('layer_height', '0.1')
			put('fill_density', '30')
			put('bottom_layer_speed', '15')
			put('bottom_thickness', '0.2')
		elif self.printTypeJoris.GetValue():
			put('wall_thickness', nozzle_size * 1.5)
			put('layer_height', '0.3')
			put('solid_layer_thickness', '0.9')
			put('fill_density', '0')
			put('joris', 'True')
			put('extra_base_wall_thickness', '15.0')
			put('sequence', 'Infill > Loops > Perimeter')
			put('force_first_layer_sequence', 'False')
			put('solid_top', 'False')
			put('support', 'None')
			put('cool_min_layer_time', '3')

		put('filament_diameter', self.printMaterialDiameter.GetValue())
		if self.printMaterialPLA.GetValue():
			put('filament_density', '1.00')
			put('enable_raft', 'False')
			put('skirt_line_count', '1')
		if self.printMaterialABS.GetValue():
			put('filament_density', '0.85')
			put('enable_raft', 'True')
			put('skirt_line_count', '0')
			put('fan_layer', '1')
			put('bottom_thickness', '0.0')
			put('print_temperature', '260')
		
		#Create a progress panel and add it to the window. The progress panel will start the Skein operation.
		spp = sliceProgessPanel.sliceProgessPanel(self, self, self.filelist)
		self.sizer.Add(spp, (len(self.progressPanelList)+2,0), span=(1,4), flag=wx.EXPAND)
		self.sizer.Layout()
		newSize = self.GetSize();
		newSize.IncBy(0, spp.GetSize().GetHeight())
		self.SetSize(newSize)
		self.progressPanelList.append(spp)
		
		#Restore the old profile.
		profile.loadGlobalProfileFromString(oldProfile)
	
	def OnPrint(self, e):
		if len(self.filelist) < 1:
			wx.MessageBox('You need to load a file and slice it before you can print it.', 'Print error', wx.OK | wx.ICON_INFORMATION)
			return
		if not os.path.exists(sliceRun.getExportFilename(self.filelist[0])):
			wx.MessageBox('You need to slice the file to GCode before you can print it.', 'Print error', wx.OK | wx.ICON_INFORMATION)
			return
		printWindow.printFile(sliceRun.getExportFilename(self.filelist[0]))

	def OnNormalSwitch(self, e):
		from gui import mainWindow
		profile.putPreference('startMode', 'Normal')
		mainWindow.mainWindow()
		self.Close()

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
		self.Destroy()

	def updateProfileToControls(self):
		super(simpleModeWindow, self).updateProfileToControls()
		self.preview3d.updateProfileToControls()

