from __future__ import absolute_import

import wx

from Cura.util import profile

class simpleModePanel(wx.Panel):
	"Main user interface window for Quickprint mode"
	def __init__(self, parent):
		super(simpleModePanel, self).__init__(parent)
		
		#toolsMenu = wx.Menu()
		#i = toolsMenu.Append(-1, 'Switch to Normal mode...')
		#self.Bind(wx.EVT_MENU, self.OnNormalSwitch, i)
		#self.menubar.Insert(1, toolsMenu, 'Normal mode')

		printTypePanel = wx.Panel(self)
		self.printTypeNormal = wx.RadioButton(printTypePanel, -1, 'Normal quality print', style=wx.RB_GROUP)
		self.printTypeLow = wx.RadioButton(printTypePanel, -1, 'Fast low quality print')
		self.printTypeHigh = wx.RadioButton(printTypePanel, -1, 'High quality print')
		self.printTypeJoris = wx.RadioButton(printTypePanel, -1, 'Thin walled cup or vase')

		printMaterialPanel = wx.Panel(self)
		self.printMaterialPLA = wx.RadioButton(printMaterialPanel, -1, 'PLA', style=wx.RB_GROUP)
		self.printMaterialABS = wx.RadioButton(printMaterialPanel, -1, 'ABS')
		self.printMaterialDiameter = wx.TextCtrl(printMaterialPanel, -1, profile.getProfileSetting('filament_diameter'))
		
		self.printSupport = wx.CheckBox(self, -1, 'Print support structure')
		
		sizer = wx.GridBagSizer()
		self.SetSizer(sizer)

		sb = wx.StaticBox(printTypePanel, label="Select a print type:")
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		boxsizer.Add(self.printTypeNormal)
		boxsizer.Add(self.printTypeLow)
		boxsizer.Add(self.printTypeHigh)
		boxsizer.Add(self.printTypeJoris)
		printTypePanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		printTypePanel.GetSizer().Add(boxsizer, flag=wx.EXPAND)
		sizer.Add(printTypePanel, (0,0), flag=wx.EXPAND)

		sb = wx.StaticBox(printMaterialPanel, label="Material:")
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		boxsizer.Add(self.printMaterialPLA)
		boxsizer.Add(self.printMaterialABS)
		boxsizer.Add(wx.StaticText(printMaterialPanel, -1, 'Diameter:'))
		boxsizer.Add(self.printMaterialDiameter)
		printMaterialPanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		printMaterialPanel.GetSizer().Add(boxsizer, flag=wx.EXPAND)
		sizer.Add(printMaterialPanel, (1,0), flag=wx.EXPAND)

		sb = wx.StaticBox(self, label="Other:")
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		boxsizer.Add(self.printSupport)
		sizer.Add(boxsizer, (2,0), flag=wx.EXPAND)

		self.printTypeNormal.SetValue(True)
		self.printMaterialPLA.SetValue(True)

	def setupSlice(self):
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
		put('retraction_enable', 'False')
		put('retraction_min_travel', '5.0')
		put('retraction_speed', '40.0')
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
			put('wall_thickness', nozzle_size * 1.4)
			put('layer_height', '0.25')
			put('fill_density', '10')
			put('print_speed', '80')
			put('cool_min_layer_time', '3')
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
		put('plugin_config', '')

	def updateProfileToControls(self):
		pass
