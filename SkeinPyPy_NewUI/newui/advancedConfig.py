from __future__ import absolute_import
import __init__

import wx, os, platform, types
import ConfigParser

from fabmetheus_utilities import settings

from newui import configWindowBase
from newui import preview3d
from newui import sliceProgessPanel
from newui import alterationPanel
from newui import validators

class advancedConfigWindow(configWindowBase.configWindowBase):
	"Advanced configuration window"
	def __init__(self):
		super(advancedConfigWindow, self).__init__(title='Advanced config')

		left, right, main = self.CreateConfigPanel(self)
		
		configWindowBase.TitleRow(left, "Accuracy")
		c = configWindowBase.SettingRow(left, "Extra Wall thickness for bottom/top (mm)", 'extra_base_wall_thickness', '0.0', 'Additional wall thickness of the bottom and top layers.')
		validators.validFloat(c, 0.0)
		validators.wallThicknessValidator(c)
		configWindowBase.TitleRow(left, "Sequence")
		c = configWindowBase.SettingRow(left, "Print order sequence", 'sequence', ['Loops > Perimeter > Infill', 'Loops > Infill > Perimeter', 'Infill > Loops > Perimeter', 'Infill > Perimeter > Loops', 'Perimeter > Infill > Loops', 'Perimeter > Loops > Infill'], 'Sequence of printing. The perimeter is the outer print edge, the loops are the insides of the walls, and the infill is the insides.');
		c = configWindowBase.SettingRow(left, "Force first layer sequence", 'force_first_layer_sequence', ['True', 'False'], 'This setting forces the order of the first layer to be \'Perimeter > Loops > Infill\'')

		configWindowBase.TitleRow(left, "Infill")
		c = configWindowBase.SettingRow(left, "Infill pattern", 'infill_type', ['Line', 'Grid Circular', 'Grid Hexagonal', 'Grid Rectangular'], 'Pattern of the none-solid infill. Line is default, but grids can provide a strong print.')
		c = configWindowBase.SettingRow(left, "Solid infill top", 'solid_top', ['True', 'False'], 'Create a solid top surface, if set to false the top is filled with the fill percentage. Useful for cups/vases.')

		configWindowBase.TitleRow(left, "Joris")
		c = configWindowBase.SettingRow(left, "Joris the outer edge", 'joris', ['False', 'True'], '[Joris] is a code name for smoothing out the Z move of the outer edge. This will create a steady Z increase over the whole print. It is intended to be used with a single walled wall thickness to make cups/vases.')

		main.Fit()
		self.Fit()

