from __future__ import absolute_import
import __init__

import wx, os, platform, types, string
import ConfigParser

from gui import configBase
from util import validators
from util import machineCom
from util import profile

class preferencesDialog(configBase.configWindowBase):
	def __init__(self, parent):
		super(preferencesDialog, self).__init__(title="Preferences")
		
		wx.EVT_CLOSE(self, self.OnClose)
		
		self.parent = parent
		self.oldExtruderAmount = int(profile.getPreference('extruder_amount'))
		
		left, right, main = self.CreateConfigPanel(self)
		configBase.TitleRow(left, 'Machine settings')
		c = configBase.SettingRow(left, 'Steps per E', 'steps_per_e', '0', 'Amount of steps per mm filament extrusion', type = 'preference')
		validators.validFloat(c, 0.1)
		c = configBase.SettingRow(left, 'Machine width (mm)', 'machine_width', '205', 'Size of the machine in mm', type = 'preference')
		validators.validFloat(c, 10.0)
		c = configBase.SettingRow(left, 'Machine depth (mm)', 'machine_depth', '205', 'Size of the machine in mm', type = 'preference')
		validators.validFloat(c, 10.0)
		c = configBase.SettingRow(left, 'Machine height (mm)', 'machine_height', '200', 'Size of the machine in mm', type = 'preference')
		validators.validFloat(c, 10.0)
		c = configBase.SettingRow(left, 'Extruder count', 'extruder_amount', ['1', '2', '3', '4'], 'Amount of extruders in your machine.', type = 'preference')
		c = configBase.SettingRow(left, 'Heated bed', 'has_heated_bed', False, 'If you have an heated bed, this enabled heated bed settings', type = 'preference')
		
		for i in xrange(1, self.oldExtruderAmount):
			configBase.TitleRow(left, 'Extruder %d' % (i+1))
			c = configBase.SettingRow(left, 'Offset X', 'extruder_offset_x%d' % (i), '0.0', 'The offset of your secondary extruder compared to the primary.', type = 'preference')
			validators.validFloat(c)
			c = configBase.SettingRow(left, 'Offset Y', 'extruder_offset_y%d' % (i), '0.0', 'The offset of your secondary extruder compared to the primary.', type = 'preference')
			validators.validFloat(c)

		configBase.TitleRow(left, 'Colours')
		c = configBase.SettingRow(left, 'Model colour', 'model_colour', wx.Colour(0,0,0), '', type = 'preference')
		for i in xrange(1, self.oldExtruderAmount):
			c = configBase.SettingRow(left, 'Model colour (%d)' % (i+1), 'model_colour%d' % (i+1), wx.Colour(0,0,0), '', type = 'preference')

		configBase.TitleRow(right, 'Filament settings')
		c = configBase.SettingRow(right, 'Filament density (kg/m3)', 'filament_density', '1300', 'Weight of the filament per m3. Around 1300 for PLA. And around 1040 for ABS. This value is used to estimate the weight if the filament used for the print.', type = 'preference')
		validators.validFloat(c, 500.0, 3000.0)
		c = configBase.SettingRow(right, 'Filament cost (price/kg)', 'filament_cost_kg', '0', 'Cost of your filament per kg, to estimate the cost of the final print.', type = 'preference')
		validators.validFloat(c, 0.0)
		c = configBase.SettingRow(right, 'Filament cost (price/m)', 'filament_cost_meter', '0', 'Cost of your filament per meter, to estimate the cost of the final print.', type = 'preference')
		validators.validFloat(c, 0.0)
		
		configBase.TitleRow(right, 'Communication settings')
		c = configBase.SettingRow(right, 'Serial port', 'serial_port', ['AUTO'] + machineCom.serialList(), 'Serial port to use for communication with the printer', type = 'preference')
		c = configBase.SettingRow(right, 'Baudrate', 'serial_baud', ['AUTO'] + map(str, machineCom.baudrateList()), 'Speed of the serial port communication\nNeeds to match your firmware settings\nCommon values are 250000, 115200, 57600', type = 'preference')

		configBase.TitleRow(right, 'Slicer settings')
		#c = configBase.SettingRow(right, 'Slicer selection', 'slicer', ['Cura (Skeinforge based)', 'Slic3r'], 'Which slicer to use to slice objects. Usually the Cura engine produces the best results. But Slic3r is developing fast and is faster with slicing.', type = 'preference')
		c = configBase.SettingRow(right, 'Save profile on slice', 'save_profile', False, 'When slicing save the profile as [stl_file]_profile.ini next to the model.', type = 'preference')

		configBase.TitleRow(right, 'SD Card settings')
		if len(getDrives()) > 1:
			c = configBase.SettingRow(right, 'SD card drive', 'sdpath', getDrives(), 'Location of your SD card, when using the copy to SD feature.', type = 'preference')
		else:
			c = configBase.SettingRow(right, 'SD card path', 'sdpath', '', 'Location of your SD card, when using the copy to SD feature.', type = 'preference')
		c = configBase.SettingRow(right, 'Copy to SD with 8.3 names', 'sdshortnames', False, 'Save the gcode files in short filenames, so they are properly shown on the UltiController', type = 'preference')

		self.okButton = wx.Button(right, -1, 'Ok')
		right.GetSizer().Add(self.okButton, (right.GetSizer().GetRows(), 0), flag=wx.BOTTOM, border=5)
		self.okButton.Bind(wx.EVT_BUTTON, self.OnClose)
		
		self.MakeModal(True)
		main.Fit()
		self.Fit()

	def OnClose(self, e):
		if self.oldExtruderAmount != int(profile.getPreference('extruder_amount')):
			wx.MessageBox('After changing the amount of extruders you need to restart Cura for full effect.', 'Extruder amount warning.', wx.OK | wx.ICON_INFORMATION)
		self.MakeModal(False)
		self.parent.updateProfileToControls()
		self.Destroy()

def getDrives():
	drives = ['']
	if platform.system() == "Windows":
		from ctypes import windll
		bitmask = windll.kernel32.GetLogicalDrives()
		for letter in string.uppercase:
			if bitmask & 1:
				drives.append(letter + ':/')
			bitmask >>= 1
	return drives
