from __future__ import absolute_import
import __init__

import wx, os, platform, types, webbrowser, shutil, glob

from gui import configBase
from gui import expertConfig
from gui import preview3d
from gui import sliceProgessPanel
from gui import alterationPanel
from gui import preferencesDialog
from gui import configWizard
from gui import firmwareInstall
from gui import printWindow
from gui import simpleMode
from gui import projectPlanner
from gui import batchRun
from gui import flatSlicerWindow
from gui import icon
from gui import dropTarget
from util import validators
from util import profile
from util import version
from util import sliceRun
from util import meshLoader

def main():
	#app = wx.App(False)
	if profile.getPreference('machine_type') == 'unknown':
		if platform.system() == "Darwin":
			#Check if we need to copy our examples
			exampleFile = os.path.expanduser('~/CuraExamples/UltimakerRobot_support.stl')
			if not os.path.isfile(examplePath):
				try:
					os.makedirs(os.path.dirname(examplePath))
				except:
					pass
				for filename in glob.glob(os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'example'))):
					shutil.copy(filename, os.path.join(os.path.dirname(examplePath), os.basename(filename)))
				profile.putPreference('lastFile', exampleFile)
		configWizard.configWizard()
	if profile.getPreference('startMode') == 'Simple':
		simpleMode.simpleModeWindow()
	else:
		mainWindow()
	#app.MainLoop()

class mainWindow(configBase.configWindowBase):
	"Main user interface window"
	def __init__(self):
		super(mainWindow, self).__init__(title='Cura - ' + version.getVersion())

		extruderCount = int(profile.getPreference('extruder_amount'))
		
		wx.EVT_CLOSE(self, self.OnClose)
		#self.SetIcon(icon.getMainIcon())
		
		self.SetDropTarget(dropTarget.FileDropTarget(self.OnDropFiles, meshLoader.supportedExtensions()))
		
		menubar = wx.MenuBar()
		fileMenu = wx.Menu()
		i = fileMenu.Append(-1, 'Load model file...')
		self.Bind(wx.EVT_MENU, lambda e: self._showModelLoadDialog(1), i)
		fileMenu.AppendSeparator()
		i = fileMenu.Append(-1, 'Open Profile...')
		self.Bind(wx.EVT_MENU, self.OnLoadProfile, i)
		i = fileMenu.Append(-1, 'Save Profile...')
		self.Bind(wx.EVT_MENU, self.OnSaveProfile, i)
		i = fileMenu.Append(-1, 'Load Profile from GCode...')
		self.Bind(wx.EVT_MENU, self.OnLoadProfileFromGcode, i)
		fileMenu.AppendSeparator()
		i = fileMenu.Append(-1, 'Reset Profile to default')
		self.Bind(wx.EVT_MENU, self.OnResetProfile, i)
		fileMenu.AppendSeparator()
		i = fileMenu.Append(-1, 'Preferences...')
		self.Bind(wx.EVT_MENU, self.OnPreferences, i)
		fileMenu.AppendSeparator()
		i = fileMenu.Append(wx.ID_EXIT, 'Quit')
		self.Bind(wx.EVT_MENU, self.OnQuit, i)
		menubar.Append(fileMenu, '&File')

		toolsMenu = wx.Menu()
		i = toolsMenu.Append(-1, 'Switch to Quickprint...')
		self.Bind(wx.EVT_MENU, self.OnSimpleSwitch, i)
		toolsMenu.AppendSeparator()
		i = toolsMenu.Append(-1, 'Batch run...')
		self.Bind(wx.EVT_MENU, self.OnBatchRun, i)
		i = toolsMenu.Append(-1, 'Project planner...')
		self.Bind(wx.EVT_MENU, self.OnProjectPlanner, i)
#		i = toolsMenu.Append(-1, 'Open SVG (2D) slicer...')
#		self.Bind(wx.EVT_MENU, self.OnSVGSlicerOpen, i)
		menubar.Append(toolsMenu, 'Tools')
		
		expertMenu = wx.Menu()
		i = expertMenu.Append(-1, 'Open expert settings...')
		self.Bind(wx.EVT_MENU, self.OnExpertOpen, i)
		expertMenu.AppendSeparator()
		if firmwareInstall.getDefaultFirmware() != None:
			i = expertMenu.Append(-1, 'Install default Marlin firmware')
			self.Bind(wx.EVT_MENU, self.OnDefaultMarlinFirmware, i)
		i = expertMenu.Append(-1, 'Install custom firmware')
		self.Bind(wx.EVT_MENU, self.OnCustomFirmware, i)
		expertMenu.AppendSeparator()
		i = expertMenu.Append(-1, 'ReRun first run wizard...')
		self.Bind(wx.EVT_MENU, self.OnFirstRunWizard, i)
		menubar.Append(expertMenu, 'Expert')
		
		helpMenu = wx.Menu()
		i = helpMenu.Append(-1, 'Online documentation...')
		self.Bind(wx.EVT_MENU, lambda e: webbrowser.open('https://daid.github.com/Cura'), i)
		i = helpMenu.Append(-1, 'Report a problem...')
		self.Bind(wx.EVT_MENU, lambda e: webbrowser.open('https://github.com/daid/Cura/issues'), i)
		menubar.Append(helpMenu, 'Help')
		self.SetMenuBar(menubar)
		
		if profile.getPreference('lastFile') != '':
			self.filelist = profile.getPreference('lastFile').split(';')
			self.SetTitle('Cura - %s - %s' % (version.getVersion(), self.filelist[-1]))
		else:
			self.filelist = []
		self.progressPanelList = []

		#Preview window
		self.preview3d = preview3d.previewPanel(self)

		#Main tabs
		nb = wx.Notebook(self)
		
		(left, right) = self.CreateConfigTab(nb, 'Print config')
		
		configBase.TitleRow(left, "Accuracy")
		c = configBase.SettingRow(left, "Layer height (mm)", 'layer_height', '0.2', 'Layer height in millimeters.\n0.2 is a good value for quick prints.\n0.1 gives high quality prints.')
		validators.validFloat(c, 0.0001)
		validators.warningAbove(c, lambda : (float(profile.getProfileSetting('nozzle_size')) * 80.0 / 100.0), "Thicker layers then %.2fmm (80%% nozzle size) usually give bad results and are not recommended.")
		c = configBase.SettingRow(left, "Wall thickness (mm)", 'wall_thickness', '0.8', 'Thickness of the walls.\nThis is used in combination with the nozzle size to define the number\nof perimeter lines and the thickness of those perimeter lines.')
		validators.validFloat(c, 0.0001)
		validators.wallThicknessValidator(c)
		c = configBase.SettingRow(left, "Enable retraction", 'retraction_enable', False, 'Retract the filament when the nozzle is moving over a none-printed area. Details about the retraction can be configured in the advanced tab.')
		
		configBase.TitleRow(left, "Fill")
		c = configBase.SettingRow(left, "Bottom/Top thickness (mm)", 'solid_layer_thickness', '0.6', 'This controls the thickness of the bottom and top layers, the amount of solid layers put down is calculated by the layer thickness and this value.\nHaving this value a multiply of the layer thickness makes sense. And keep it near your wall thickness to make an evenly strong part.')
		validators.validFloat(c, 0.0)
		c = configBase.SettingRow(left, "Fill Density (%)", 'fill_density', '20', 'This controls how densily filled the insides of your print will be. For a solid part use 100%, for an empty part use 0%. A value around 20% is usually enough')
		validators.validFloat(c, 0.0, 100.0)
		
		configBase.TitleRow(left, "Skirt")
		c = configBase.SettingRow(left, "Line count", 'skirt_line_count', '1', 'The skirt is a line drawn around the object at the first layer. This helps to prime your extruder, and to see if the object fits on your platform.\nSetting this to 0 will disable the skirt. Multiple skirt lines can help priming your extruder better for small objects.')
		validators.validInt(c, 0, 10)
		c = configBase.SettingRow(left, "Start distance (mm)", 'skirt_gap', '6.0', 'The distance between the skirt and the first layer.\nThis is the minimal distance, multiple skirt lines will be put outwards from this distance.')
		validators.validFloat(c, 0.0)

		configBase.TitleRow(right, "Speed && Temperature")
		c = configBase.SettingRow(right, "Print speed (mm/s)", 'print_speed', '50', 'Speed at which printing happens. A well adjusted Ultimaker can reach 150mm/s, but for good quality prints you want to print slower. Printing speed depends on a lot of factors. So you will be experimenting with optimal settings for this.')
		validators.validFloat(c, 1.0)
		validators.warningAbove(c, 150.0, "It is highly unlikely that your machine can achieve a printing speed above 150mm/s")
		validators.printSpeedValidator(c)
		
		#configBase.TitleRow(right, "Temperature")
		c = configBase.SettingRow(right, "Printing temperature", 'print_temperature', '0', 'Temperature used for printing. Set at 0 to pre-heat yourself')
		validators.validFloat(c, 0.0, 340.0)
		validators.warningAbove(c, 260.0, "Temperatures above 260C could damage your machine, be careful!")
		if profile.getPreference('has_heated_bed') == 'True':
			c = configBase.SettingRow(right, "Bed temperature", 'print_bed_temperature', '0', 'Temperature used for the heated printer bed. Set at 0 to pre-heat yourself')
			validators.validFloat(c, 0.0, 340.0)
		
		configBase.TitleRow(right, "Support structure")
		c = configBase.SettingRow(right, "Support type", 'support', ['None', 'Exterior Only', 'Everywhere'], 'Type of support structure build.\n"Exterior only" is the most commonly used support setting.\n\nNone does not do any support.\nExterior only only creates support where the support structure will touch the build platform.\nEverywhere creates support even on the insides of the model.')
		c = configBase.SettingRow(right, "Add raft", 'enable_raft', False, 'A raft is a few layers of lines below the bottom of the object. It prevents warping. Full raft settings can be found in the expert settings.\nFor PLA this is usually not required. But if you print with ABS it is almost required.')
		if extruderCount > 1:
			c = configBase.SettingRow(right, "Support dual extrusion", 'support_dual_extrusion', False, 'Print the support material with the 2nd extruder in a dual extrusion setup. The primary extruder will be used for normal material, while the second extruder is used to print support material.')

		configBase.TitleRow(right, "Filament")
		c = configBase.SettingRow(right, "Diameter (mm)", 'filament_diameter', '2.89', 'Diameter of your filament, as accurately as possible.\nIf you cannot measure this value you will have to callibrate it, a higher number means less extrusion, a smaller number generates more extrusion.')
		validators.validFloat(c, 1.0)
		validators.warningAbove(c, 3.5, "Are you sure your filament is that thick? Normal filament is around 3mm or 1.75mm.")
		c = configBase.SettingRow(right, "Packing Density", 'filament_density', '1.00', 'Packing density of your filament. This should be 1.00 for PLA and 0.85 for ABS')
		validators.validFloat(c, 0.5, 1.5)
		
		(left, right) = self.CreateConfigTab(nb, 'Advanced config')
		
		configBase.TitleRow(left, "Machine size")
		c = configBase.SettingRow(left, "Nozzle size (mm)", 'nozzle_size', '0.4', 'The nozzle size is very important, this is used to calculate the line width of the infill, and used to calculate the amount of outside wall lines and thickness for the wall thickness you entered in the print settings.')
		validators.validFloat(c, 0.1, 10.0)
		c = configBase.SettingRow(left, "Machine center X (mm)", 'machine_center_x', '100', 'The center of your machine, your print will be placed at this location')
		validators.validInt(c, 10)
		configBase.settingNotify(c, self.preview3d.updateCenterX)
		c = configBase.SettingRow(left, "Machine center Y (mm)", 'machine_center_y', '100', 'The center of your machine, your print will be placed at this location')
		validators.validInt(c, 10)
		configBase.settingNotify(c, self.preview3d.updateCenterY)

		configBase.TitleRow(left, "Retraction")
		c = configBase.SettingRow(left, "Minimal travel (mm)", 'retraction_min_travel', '5.0', 'Minimal amount of travel needed for a retraction to happen at all. To make sure you do not get a lot of retractions in a small area')
		validators.validFloat(c, 0.0)
		c = configBase.SettingRow(left, "Speed (mm/s)", 'retraction_speed', '40.0', 'Speed at which the filament is retracted, a higher retraction speed works better. But a very high retraction speed can lead to filament grinding.')
		validators.validFloat(c, 0.1)
		c = configBase.SettingRow(left, "Distance (mm)", 'retraction_amount', '0.0', 'Amount of retraction, set at 0 for no retraction at all. A value of 2.0mm seems to generate good results.')
		validators.validFloat(c, 0.0)
		c = configBase.SettingRow(left, "Extra length on start (mm)", 'retraction_extra', '0.0', 'Extra extrusion amount when restarting after a retraction, to better "Prime" your extruder after retraction.')
		validators.validFloat(c, 0.0)

		configBase.TitleRow(right, "Speed")
		c = configBase.SettingRow(right, "Travel speed (mm/s)", 'travel_speed', '150', 'Speed at which travel moves are done, a high quality build Ultimaker can reach speeds of 250mm/s. But some machines might miss steps then.')
		validators.validFloat(c, 1.0)
		validators.warningAbove(c, 300.0, "It is highly unlikely that your machine can achieve a travel speed above 300mm/s")
		c = configBase.SettingRow(right, "Max Z speed (mm/s)", 'max_z_speed', '1.0', 'Speed at which Z moves are done. When you Z axis is properly lubercated you can increase this for less Z blob.')
		validators.validFloat(c, 0.5)
		c = configBase.SettingRow(right, "Bottom layer speed (mm/s)", 'bottom_layer_speed', '25', 'Print speed for the bottom layer, you want to print the first layer slower so it sticks better to the printer bed.')
		validators.validFloat(c, 0.0)

		configBase.TitleRow(right, "Cool")
		c = configBase.SettingRow(right, "Minimal layer time (sec)", 'cool_min_layer_time', '10', 'Minimum time spend in a layer, gives the layer time to cool down before the next layer is put on top. If the layer will be placed down too fast the printer will slow down to make sure it has spend atleast this amount of seconds printing this layer.')
		validators.validFloat(c, 0.0)
		c = configBase.SettingRow(right, "Enable cooling fan", 'fan_enabled', True, 'Enable the cooling fan during the print. The extra cooling from the cooling fan is essensial during faster prints.')

		configBase.TitleRow(right, "Accuracy")
		c = configBase.SettingRow(right, "Initial layer thickness (mm)", 'bottom_thickness', '0.0', 'Layer thickness of the bottom layer. A thicker bottom layer makes sticking to the bed easier. Set to 0.0 to have the bottom layer thickness the same as the other layers.')
		validators.validFloat(c, 0.0)
		validators.warningAbove(c, lambda : (float(profile.getProfileSetting('nozzle_size')) * 3.0 / 4.0), "A bottom layer of more then %.2fmm (3/4 nozzle size) usually give bad results and is not recommended.")
		c = configBase.SettingRow(right, "Enable 'skin'", 'enable_skin', False, 'Skin prints the outer lines of the prints twice, each time with half the thickness. This gives the illusion of a higher print quality.')

		#Effects page
		self.effectList = profile.getEffectsList()
		if len(self.effectList) > 0:
			self.effectPanel = wx.Panel(nb)
			sizer = wx.GridBagSizer(2, 2)
			self.effectPanel.SetSizer(sizer)
			
			effectStringList = []
			for effect in self.effectList:
				effectStringList.append(effect['name'])
				
			self.listbox = wx.ListBox(self.effectPanel, -1, choices=effectStringList)
			title = wx.StaticText(self.effectPanel, -1, "Effects:")
			title.SetFont(wx.Font(wx.SystemSettings.GetFont(wx.SYS_ANSI_VAR_FONT).GetPointSize(), wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.FONTWEIGHT_BOLD))
			addButton = wx.Button(self.effectPanel, -1, '>', style=wx.BU_EXACTFIT)
			remButton = wx.Button(self.effectPanel, -1, '<', style=wx.BU_EXACTFIT)
			sizer.Add(self.listbox, (1,0), span=(2,1), border=10, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM)
			sizer.Add(title, (0,0), border=10, flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT|wx.TOP)
			sizer.Add(addButton, (1,1), border=5, flag=wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_BOTTOM)
			sizer.Add(remButton, (2,1), border=5, flag=wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_TOP)
			
			sizer.AddGrowableCol(2)
			sizer.AddGrowableRow(1)
			sizer.AddGrowableRow(2)
			nb.AddPage(self.effectPanel, "Effects")

		#Alteration page
		self.alterationPanel = alterationPanel.alterationPanel(nb)
		nb.AddPage(self.alterationPanel, "Start/End-GCode")

		# load and slice buttons.
		loadButton = wx.Button(self, -1, '&Load Model')
		sliceButton = wx.Button(self, -1, 'P&repare print')
		printButton = wx.Button(self, -1, '&Print')
		self.Bind(wx.EVT_BUTTON, lambda e: self._showModelLoadDialog(1), loadButton)
		self.Bind(wx.EVT_BUTTON, self.OnSlice, sliceButton)
		self.Bind(wx.EVT_BUTTON, self.OnPrint, printButton)

		if extruderCount > 1:
			loadButton2 = wx.Button(self, -1, 'Load Dual')
			self.Bind(wx.EVT_BUTTON, lambda e: self._showModelLoadDialog(2), loadButton2)
		if extruderCount > 2:
			loadButton3 = wx.Button(self, -1, 'Load Triple')
			self.Bind(wx.EVT_BUTTON, lambda e: self._showModelLoadDialog(3), loadButton3)
		if extruderCount > 3:
			loadButton4 = wx.Button(self, -1, 'Load Quad')
			self.Bind(wx.EVT_BUTTON, lambda e: self._showModelLoadDialog(4), loadButton4)

		#Also bind double clicking the 3D preview to load an STL file.
		self.preview3d.glCanvas.Bind(wx.EVT_LEFT_DCLICK, lambda e: self._showModelLoadDialog(1), self.preview3d.glCanvas)

		#Main sizer, to position the preview window, buttons and tab control
		sizer = wx.GridBagSizer()
		self.SetSizer(sizer)
		sizer.Add(nb, (0,0), span=(1,1), flag=wx.EXPAND)
		sizer.Add(self.preview3d, (0,1), span=(1,2+extruderCount), flag=wx.EXPAND)
		sizer.AddGrowableCol(2 + extruderCount)
		sizer.AddGrowableRow(0)
		sizer.Add(loadButton, (1,1), flag=wx.RIGHT|wx.BOTTOM|wx.TOP, border=5)
		if extruderCount > 1:
			sizer.Add(loadButton2, (1,2), flag=wx.RIGHT|wx.BOTTOM|wx.TOP, border=5)
		if extruderCount > 2:
			sizer.Add(loadButton3, (1,3), flag=wx.RIGHT|wx.BOTTOM|wx.TOP, border=5)
		if extruderCount > 3:
			sizer.Add(loadButton4, (1,4), flag=wx.RIGHT|wx.BOTTOM|wx.TOP, border=5)
		sizer.Add(sliceButton, (1,1+extruderCount), flag=wx.RIGHT|wx.BOTTOM|wx.TOP, border=5)
		sizer.Add(printButton, (1,2+extruderCount), flag=wx.RIGHT|wx.BOTTOM|wx.TOP, border=5)
		self.sizer = sizer

		if len(self.filelist) > 0:
			self.preview3d.loadModelFiles(self.filelist)

		self.updateProfileToControls()

		self.SetBackgroundColour(nb.GetBackgroundColour())

		self.SetAcceleratorTable(wx.AcceleratorTable([(wx.ACCEL_CTRL, ord('L'), loadButton.GetId()),
													  (wx.ACCEL_CTRL, ord('R'), sliceButton.GetId()),
													  (wx.ACCEL_CTRL, ord('P'), printButton.GetId())
													 ]))
		
		self.Fit()
		if wx.Display().GetClientArea().GetWidth() < self.GetSize().GetWidth():
			f = self.GetSize().GetWidth() - wx.Display().GetClientArea().GetWidth()
			self.preview3d.SetMinSize(self.preview3d.GetMinSize().DecBy(f, 0))
			self.Fit()
		self.preview3d.Fit()
		self.SetMinSize(self.GetSize())
		self.Centre()
		self.Show(True)
	
	def OnLoadProfile(self, e):
		dlg=wx.FileDialog(self, "Select profile file to load", os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
		dlg.SetWildcard("ini files (*.ini)|*.ini")
		if dlg.ShowModal() == wx.ID_OK:
			profileFile = dlg.GetPath()
			profile.loadGlobalProfile(profileFile)
			self.updateProfileToControls()
		dlg.Destroy()

	def OnLoadProfileFromGcode(self, e):
		dlg=wx.FileDialog(self, "Select gcode file to load profile from", os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
		dlg.SetWildcard("gcode files (*.gcode)|*.gcode;*.g")
		if dlg.ShowModal() == wx.ID_OK:
			gcodeFile = dlg.GetPath()
			f = open(gcodeFile, 'r')
			hasProfile = False
			for line in f:
				if line.startswith(';CURA_PROFILE_STRING:'):
					profile.loadGlobalProfileFromString(line[line.find(':')+1:].strip())
					hasProfile = True
			if hasProfile:
				self.updateProfileToControls()
			else:
				wx.MessageBox('No profile found in GCode file.\nThis feature only works with GCode files made by Cura 12.07 or newer.', 'Profile load error', wx.OK | wx.ICON_INFORMATION)
		dlg.Destroy()
	
	def OnSaveProfile(self, e):
		dlg=wx.FileDialog(self, "Select profile file to save", os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_SAVE)
		dlg.SetWildcard("ini files (*.ini)|*.ini")
		if dlg.ShowModal() == wx.ID_OK:
			profileFile = dlg.GetPath()
			profile.saveGlobalProfile(profileFile)
		dlg.Destroy()
	
	def OnResetProfile(self, e):
		dlg = wx.MessageDialog(self, 'This will reset all profile settings to defaults.\nUnless you have saved your current profile, all settings will be lost!\nDo you really want to reset?', 'Profile reset', wx.YES_NO | wx.ICON_QUESTION)
		result = dlg.ShowModal() == wx.ID_YES
		dlg.Destroy()
		if result:
			profile.resetGlobalProfile()
			if profile.getPreference('machine_type') == 'reprap':
				profile.putProfileSetting('nozzle_size', '0.5')
				profile.putProfileSetting('machine_center_x', '40')
				profile.putProfileSetting('machine_center_y', '40')
			self.updateProfileToControls()
	
	def OnBatchRun(self, e):
		br = batchRun.batchRunWindow(self)
		br.Centre()
		br.Show(True)
	
	def OnPreferences(self, e):
		prefDialog = preferencesDialog.preferencesDialog(self)
		prefDialog.Centre()
		prefDialog.Show(True)
	
	def OnSimpleSwitch(self, e):
		profile.putPreference('startMode', 'Simple')
		simpleMode.simpleModeWindow()
		self.Close()
	
	def OnDefaultMarlinFirmware(self, e):
		firmwareInstall.InstallFirmware()

	def OnCustomFirmware(self, e):
		if profile.getPreference('machine_type') == 'ultimaker':
			wx.MessageBox('Warning: Installing a custom firmware does not garantee that you machine will function correctly, and could damage your machine.', 'Firmware update', wx.OK | wx.ICON_EXCLAMATION)
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

	def _showOpenDialog(self, title, wildcard = meshLoader.wildcardFilter()):
		dlg=wx.FileDialog(self, title, os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
		dlg.SetWildcard(wildcard)
		if dlg.ShowModal() == wx.ID_OK:
			filename = dlg.GetPath()
			dlg.Destroy()
			if not(os.path.exists(filename)):
				return False
			profile.putPreference('lastFile', filename)
			return filename
		dlg.Destroy()
		return False

	def _showModelLoadDialog(self, amount):
		filelist = []
		for i in xrange(0, amount):
			filelist.append(self._showOpenDialog("Open file to print"))
			if filelist[-1] == False:
				return
		self._loadModels(filelist)
	
	def _loadModels(self, filelist):
		self.filelist = filelist
		self.SetTitle(filelist[-1] + ' - Cura - ' + version.getVersion())
		profile.putPreference('lastFile', ';'.join(self.filelist))
		self.preview3d.loadModelFiles(self.filelist, True)
		self.preview3d.setViewMode("Normal")

	def OnDropFiles(self, filenames):
		self._loadModels(filenames)

	def OnLoadModel(self, e):
		self._showModelLoadDialog(1)
	
	def OnLoadModel2(self, e):
		self._showModelLoadDialog(2)

	def OnLoadModel3(self, e):
		self._showModelLoadDialog(3)

	def OnLoadModel4(self, e):
		self._showModelLoadDialog(4)
	
	def OnSlice(self, e):
		if len(self.filelist) < 1:
			wx.MessageBox('You need to load a file before you can prepare it.', 'Print error', wx.OK | wx.ICON_INFORMATION)
			return
		#Create a progress panel and add it to the window. The progress panel will start the Skein operation.
		spp = sliceProgessPanel.sliceProgessPanel(self, self, self.filelist)
		self.sizer.Add(spp, (len(self.progressPanelList)+2,0), span=(1,4), flag=wx.EXPAND)
		self.sizer.Layout()
		newSize = self.GetSize();
		newSize.IncBy(0, spp.GetSize().GetHeight())
		if newSize.GetWidth() < wx.GetDisplaySize()[0]:
			self.SetSize(newSize)
		self.progressPanelList.append(spp)
	
	def OnPrint(self, e):
		if len(self.filelist) < 1:
			wx.MessageBox('You need to load a file and prepare it before you can print.', 'Print error', wx.OK | wx.ICON_INFORMATION)
			return
		if not os.path.exists(sliceRun.getExportFilename(self.filelist[0])):
			wx.MessageBox('You need to prepare a print before you can run the actual print.', 'Print error', wx.OK | wx.ICON_INFORMATION)
			return
		printWindow.printFile(sliceRun.getExportFilename(self.filelist[0]))

	def OnExpertOpen(self, e):
		ecw = expertConfig.expertConfigWindow()
		ecw.Centre()
		ecw.Show(True)
	
	def OnProjectPlanner(self, e):
		pp = projectPlanner.projectPlanner()
		pp.Centre()
		pp.Show(True)

	def OnSVGSlicerOpen(self, e):
		svgSlicer = flatSlicerWindow.flatSlicerWindow()
		svgSlicer.Centre()
		svgSlicer.Show(True)

	def removeSliceProgress(self, spp):
		self.progressPanelList.remove(spp)
		newSize = self.GetSize();
		newSize.IncBy(0, -spp.GetSize().GetHeight())
		if newSize.GetWidth() < wx.GetDisplaySize()[0]:
			self.SetSize(newSize)
		spp.Show(False)
		self.sizer.Detach(spp)
		for spp in self.progressPanelList:
			self.sizer.Detach(spp)
		i = 2
		for spp in self.progressPanelList:
			self.sizer.Add(spp, (i,0), span=(1,4), flag=wx.EXPAND)
			i += 1
		self.sizer.Layout()

	def OnQuit(self, e):
		self.Close()
	
	def OnClose(self, e):
		profile.saveGlobalProfile(profile.getDefaultProfilePath())
		self.Destroy()

	def updateProfileToControls(self):
		super(mainWindow, self).updateProfileToControls()
		self.preview3d.updateProfileToControls()
		self.alterationPanel.updateProfileToControls()
