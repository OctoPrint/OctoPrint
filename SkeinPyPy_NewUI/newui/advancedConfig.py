from __future__ import absolute_import
import __init__

import wx, os, platform, types
import ConfigParser

from fabmetheus_utilities import settings

from newui import configBase
from newui import preview3d
from newui import sliceProgessPanel
from newui import alterationPanel
from newui import validators

class advancedConfigWindow(configBase.configWindowBase):
	"Advanced configuration window"
	def __init__(self):
		super(advancedConfigWindow, self).__init__(title='Advanced config')

		wx.EVT_CLOSE(self, self.OnClose)

		left, right, main = self.CreateConfigPanel(self)
		
		configBase.TitleRow(left, "Accuracy")
		c = configBase.SettingRow(left, "Extra Wall thickness for bottom/top (mm)", 'extra_base_wall_thickness', '0.0', 'Additional wall thickness of the bottom and top layers.')
		validators.validFloat(c, 0.0)
		configBase.TitleRow(left, "Sequence")
		c = configBase.SettingRow(left, "Print order sequence", 'sequence', ['Loops > Perimeter > Infill', 'Loops > Infill > Perimeter', 'Infill > Loops > Perimeter', 'Infill > Perimeter > Loops', 'Perimeter > Infill > Loops', 'Perimeter > Loops > Infill'], 'Sequence of printing. The perimeter is the outer print edge, the loops are the insides of the walls, and the infill is the insides.');
		c = configBase.SettingRow(left, "Force first layer sequence", 'force_first_layer_sequence', True, 'This setting forces the order of the first layer to be \'Perimeter > Loops > Infill\'')

		configBase.TitleRow(left, "Infill")
		c = configBase.SettingRow(left, "Infill pattern", 'infill_type', ['Line', 'Grid Circular', 'Grid Hexagonal', 'Grid Rectangular'], 'Pattern of the none-solid infill. Line is default, but grids can provide a strong print.')
		c = configBase.SettingRow(left, "Solid infill top", 'solid_top', True, 'Create a solid top surface, if set to false the top is filled with the fill percentage. Useful for cups/vases.')
		c = configBase.SettingRow(left, "Infill overlap (%)", 'fill_overlap', '15', 'Amount of overlap between the infill and the walls. There is a slight overlap with the walls and the infill so the walls connect firmly to the infill.')

		configBase.TitleRow(left, "Joris")
		c = configBase.SettingRow(left, "Joris the outer edge", 'joris', False, '[Joris] is a code name for smoothing out the Z move of the outer edge. This will create a steady Z increase over the whole print. It is intended to be used with a single walled wall thickness to make cups/vases.')

		main.Fit()
		self.Fit()

	def OnClose(self, e):
		self.Destroy()
