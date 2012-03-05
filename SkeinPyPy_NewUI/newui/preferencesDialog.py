from __future__ import absolute_import
import __init__

import wx, os, platform, types
import ConfigParser

from newui import configBase

class preferencesDialog(configBase.configWindowBase):
	def __init__(self, parent):
		super(preferencesDialog, self).__init__(title="Preferences")
		
		wx.EVT_CLOSE(self, self.OnClose)
		
		left, right, main = self.CreateConfigPanel(self)
		configBase.TitleRow(left, 'Machine settings')
		c = configBase.SettingRow(left, 'Steps per E', 'steps_per_e', '0', 'Amount of steps per mm filament extrusion', type = 'preference')
		validators.validFloat(c, 0.1)
		c = configBase.SettingRow(left, 'Machine width', 'machine_width', '205', 'Size of the machine in mm', type = 'preference')
		validators.validFloat(c, 10.0)
		c = configBase.SettingRow(left, 'Machine depth', 'machine_depth', '205', 'Size of the machine in mm', type = 'preference')
		validators.validFloat(c, 10.0)
		c = configBase.SettingRow(left, 'Machine height', 'machine_height', '200', 'Size of the machine in mm', type = 'preference')
		validators.validFloat(c, 10.0)

		configBase.TitleRow(left, 'Communication settings')
		c = configBase.SettingRow(left, 'Serial port', 'serial_port', 'AUTO', 'Serial port to use for communication with the printer', type = 'preference')
		c = configBase.SettingRow(left, 'Baudrate', 'serial_baud', '250000', 'Speed of the serial port communication\nNeeds to match your firmware settings', type = 'preference')
		
		self.MakeModal(True)
		main.Fit()
		self.Fit()

	def OnClose(self, e):
		self.MakeModal(False)
		self.Destroy()
