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
		c = configWindowBase.SettingRow(left, "Extra Wall thickness for bottom/top (mm)", 'extra_base_wall_thickness', '0.0', 'Additional perimeter thickness of the bottom layer.')
		validators.validFloat(c, 0.0)
		validators.wallThicknessValidator(c)

		configWindowBase.TitleRow(left, "Infill")
		c = configWindowBase.SettingRow(left, "Infill pattern", 'infill_type', ['Line', 'Grid Circular', 'Grid Hexagonal', 'Grid Rectangular'], 'Pattern of the none-solid infill. Line is default, but grids can provide a strong print.')
		c = configWindowBase.SettingRow(left, "Solid infill top", 'solid_top', ['True', 'False'], 'Create a solid top surface, if set to false the top is filled with the fill percentage. Useful for cups.')
		c = configWindowBase.SettingRow(left, "Force first layer sequence", 'force_first_layer_sequence', ['True', 'False'], 'This setting forces the order of the first layer to be \'Perimeter > Loops > Infill\'')

		main.Fit()
		self.Fit()

