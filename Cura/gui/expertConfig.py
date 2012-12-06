from __future__ import absolute_import

import wx

from Cura.gui import configBase
from Cura.util import validators

class expertConfigWindow(configBase.configWindowBase):
	"Expert configuration window"
	def __init__(self):
		super(expertConfigWindow, self).__init__(title='Expert config', style=wx.DEFAULT_DIALOG_STYLE)

		wx.EVT_CLOSE(self, self.OnClose)

		left, right, main = self.CreateConfigPanel(self)
		
		configBase.TitleRow(left, "Accuracy")
		c = configBase.SettingRow(left, "Extra Wall thickness for bottom/top (mm)", 'extra_base_wall_thickness', '0.0', 'Additional wall thickness of the bottom and top layers.')
		validators.validFloat(c, 0.0)
		
		configBase.TitleRow(left, "Cool")
		c = configBase.SettingRow(left, "Minimum feedrate (mm/s)", 'cool_min_feedrate', '5', 'The minimal layer time can cause the print to slow down so much it starts to ooze. The minimal feedrate protects against this. Even if a print gets slown down it will never be slower then this minimal feedrate.')
		validators.validFloat(c, 0.0)
		c = configBase.SettingRow(left, "Fan on layer number", 'fan_layer', '0', 'The layer at which the fan is turned on. The first layer is layer 0. The first layer can stick better if you turn on the fan on, on the 2nd layer.')
		validators.validInt(c, 0)
		c = configBase.SettingRow(left, "Fan speed min (%)", 'fan_speed', '100', 'When the fan is turned on, it is enabled at this speed setting. If cool slows down the layer, the fan is adjusted between the min and max speed. Minimal fan speed is used if the layer is not slowed down due to cooling.')
		validators.validInt(c, 0, 100)
		c = configBase.SettingRow(left, "Fan speed max (%)", 'fan_speed_max', '100', 'When the fan is turned on, it is enabled at this speed setting. If cool slows down the layer, the fan is adjusted between the min and max speed. Maximal fan speed is used if the layer is slowed down due to cooling by more then 200%.')
		validators.validInt(c, 0, 100)

		configBase.TitleRow(left, "Raft (if enabled)")
		c = configBase.SettingRow(left, "Extra margin (mm)", 'raft_margin', '3.0', 'If the raft is enabled, this is the extra raft area around the object which is also rafted. Increasing this margin will create a stronger raft.')
		validators.validFloat(c, 0.0)
		c = configBase.SettingRow(left, "Base material amount (%)", 'raft_base_material_amount', '100', 'The base layer is the first layer put down as a raft. This layer has thick strong lines and is put firmly on the bed to prevent warping. This setting adjust the amount of material used for the base layer.')
		validators.validFloat(c, 0.0)
		c = configBase.SettingRow(left, "Interface material amount (%)", 'raft_interface_material_amount', '100', 'The interface layer is a weak thin layer between the base layer and the printed object. It is designed to has little material to make it easy to break the base off the printed object. This setting adjusts the amount of material used for the interface layer.')
		validators.validFloat(c, 0.0)

		configBase.TitleRow(left, "Support")
		c = configBase.SettingRow(left, "Material amount (%)", 'support_rate', '100', 'Amount of material used for support, less material gives a weaker support structure which is easier to remove.')
		validators.validFloat(c, 0.0)
		c = configBase.SettingRow(left, "Distance from object (mm)", 'support_distance', '0.5', 'Distance between the support structure and the object. Empty gap in which no support structure is printed.')
		validators.validFloat(c, 0.0)

		configBase.TitleRow(right, "Infill")
		c = configBase.SettingRow(right, "Infill pattern", 'infill_type', ['Line', 'Grid Circular', 'Grid Hexagonal', 'Grid Rectangular'], 'Pattern of the none-solid infill. Line is default, but grids can provide a strong print.')
		c = configBase.SettingRow(right, "Solid infill top", 'solid_top', True, 'Create a solid top surface, if set to false the top is filled with the fill percentage. Useful for cups/vases.')
		c = configBase.SettingRow(right, "Infill overlap (%)", 'fill_overlap', '15', 'Amount of overlap between the infill and the walls. There is a slight overlap with the walls and the infill so the walls connect firmly to the infill.')
		validators.validFloat(c, 0.0)

		configBase.TitleRow(right, "Bridge")
		c = configBase.SettingRow(right, "Bridge speed (%)", 'bridge_speed', '100', 'Speed at which layers with bridges are printed, compared to normal printing speed.')
		validators.validFloat(c, 0.0)
		
		configBase.TitleRow(right, "Sequence")
		c = configBase.SettingRow(right, "Print order sequence", 'sequence', ['Loops > Perimeter > Infill', 'Loops > Infill > Perimeter', 'Infill > Loops > Perimeter', 'Infill > Perimeter > Loops', 'Perimeter > Infill > Loops', 'Perimeter > Loops > Infill'], 'Sequence of printing. The perimeter is the outer print edge, the loops are the insides of the walls, and the infill is the insides.');
		c = configBase.SettingRow(right, "Force first layer sequence", 'force_first_layer_sequence', True, 'This setting forces the order of the first layer to be \'Perimeter > Loops > Infill\'')

		configBase.TitleRow(right, "Joris")
		c = configBase.SettingRow(right, "Joris the outer edge", 'joris', False, '[Joris] is a code name for smoothing out the Z move of the outer edge. This will create a steady Z increase over the whole print. It is intended to be used with a single walled wall thickness to make cups/vases.')

		configBase.TitleRow(right, "Retraction")
		c = configBase.SettingRow(right, "Retract on jumps only", 'retract_on_jumps_only', True, 'Only retract when we are making a move that is over a hole in the model, else retract on every move. This effects print quality in different ways.')

		configBase.TitleRow(right, "Hop")
		c = configBase.SettingRow(right, "Enable hop on move", 'hop_on_move', False, 'When moving from print position to print position, raise the printer head 0.2mm so it does not knock off the print (experimental).')

		main.Fit()
		self.Fit()

	def OnClose(self, e):
		self.Destroy()
