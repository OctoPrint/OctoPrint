from __future__ import absolute_import
import __init__

import wx, os, platform, types
import ConfigParser

from gui import configBase
from gui import preview3d
from gui import sliceProgessPanel
from gui import alterationPanel
from gui import validators

class advancedConfigWindow(configBase.configWindowBase):
	"Advanced configuration window"
	def __init__(self):
		super(advancedConfigWindow, self).__init__(title='Expert config')

		wx.EVT_CLOSE(self, self.OnClose)

		left, right, main = self.CreateConfigPanel(self)
		
		configBase.TitleRow(left, "Accuracy")
		c = configBase.SettingRow(left, "Extra Wall thickness for bottom/top (mm)", 'extra_base_wall_thickness', '0.0', 'Additional wall thickness of the bottom and top layers.')
		validators.validFloat(c, 0.0)
		
		configBase.TitleRow(left, "Sequence")
		c = configBase.SettingRow(left, "Print order sequence", 'sequence', ['Loops > Perimeter > Infill', 'Loops > Infill > Perimeter', 'Infill > Loops > Perimeter', 'Infill > Perimeter > Loops', 'Perimeter > Infill > Loops', 'Perimeter > Loops > Infill'], 'Sequence of printing. The perimeter is the outer print edge, the loops are the insides of the walls, and the infill is the insides.');
		c = configBase.SettingRow(left, "Force first layer sequence", 'force_first_layer_sequence', True, 'This setting forces the order of the first layer to be \'Perimeter > Loops > Infill\'')

		configBase.TitleRow(left, "Cool")
		c = configBase.SettingRow(left, "Minimum feedrate (mm/s)", 'cool_min_feedrate', '5', 'The minimal layer time can cause the print to slow down so much it starts to ooze. The minimal feedrate protects against this. Even if a print gets slown down it will never be slower then this minimal feedrate.')
		validators.validFloat(c, 0.0)

		configBase.TitleRow(left, "Joris")
		c = configBase.SettingRow(left, "Joris the outer edge", 'joris', False, '[Joris] is a code name for smoothing out the Z move of the outer edge. This will create a steady Z increase over the whole print. It is intended to be used with a single walled wall thickness to make cups/vases.')

		configBase.TitleRow(left, "Raft (if enabled)")
		c = configBase.SettingRow(left, "Raft extra margin (mm)", 'raft_margin', '3.0', 'If the raft is enabled, this is the extra raft area around the object which is also rafted. Increasing this margin will create a stronger raft.')
		validators.validFloat(c, 0.0)
		c = configBase.SettingRow(left, "Raft base material amount (%)", 'raft_base_material_amount', '100', 'The base layer is the first layer put down as a raft. This layer has thick strong lines and is put firmly on the bed to prevent warping. This setting adjust the amount of material used for the base layer.')
		validators.validFloat(c, 0.0)
		c = configBase.SettingRow(left, "Raft interface material amount (%)", 'raft_interface_material_amount', '100', 'The interface layer is a weak thin layer between the base layer and the printed object. It is designed to has little material to make it easy to break the base off the printed object. This setting adjusts the amount of material used for the interface layer.')
		validators.validFloat(c, 0.0)

		configBase.TitleRow(right, "Infill")
		c = configBase.SettingRow(right, "Infill pattern", 'infill_type', ['Line', 'Grid Circular', 'Grid Hexagonal', 'Grid Rectangular'], 'Pattern of the none-solid infill. Line is default, but grids can provide a strong print.')
		c = configBase.SettingRow(right, "Solid infill top", 'solid_top', True, 'Create a solid top surface, if set to false the top is filled with the fill percentage. Useful for cups/vases.')
		c = configBase.SettingRow(right, "Infill overlap (%)", 'fill_overlap', '15', 'Amount of overlap between the infill and the walls. There is a slight overlap with the walls and the infill so the walls connect firmly to the infill.')
		validators.validFloat(c, 0.0)

		configBase.TitleRow(right, "Support")
		c = configBase.SettingRow(right, "Support material amount (%)", 'support_rate', '100', 'Amount of material used for support, less material gives a weaker support structure which is easier to remove.')
		validators.validFloat(c, 0.0)
		c = configBase.SettingRow(right, "Support distance from object (mm)", 'support_distance', '0.5', 'Distance between the support structure and the object.')
		validators.validFloat(c, 0.0)

		configBase.TitleRow(right, "Bridge")
		c = configBase.SettingRow(right, "Bridge speed (%)", 'bridge_speed', '100', 'Speed at which bridges are printed, compared to normal printing speed.')
		validators.validFloat(c, 0.0)
		c = configBase.SettingRow(right, "Bridge material (%)", 'bridge_material_amount', '100', 'Amount of material used for bridges, increase go extrude more material when printing a bridge.')
		validators.validFloat(c, 0.0)

		main.Fit()
		self.Fit()

	def OnClose(self, e):
		self.Destroy()
