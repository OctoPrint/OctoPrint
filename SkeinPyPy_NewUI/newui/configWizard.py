from __future__ import absolute_import
import __init__

import wx, os, platform, types
import wx.wizard

from fabmetheus_utilities import settings

class InfoPage(wx.wizard.WizardPageSimple):
	def __init__(self, parent, title):
		"""Constructor"""
		wx.wizard.WizardPageSimple.__init__(self, parent)

		sizer = wx.BoxSizer(wx.VERTICAL)
		self.sizer = sizer
		self.SetSizer(sizer)

		title = wx.StaticText(self, -1, title)
		title.SetFont(wx.Font(18, wx.SWISS, wx.NORMAL, wx.BOLD))
		sizer.Add(title, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		sizer.Add(wx.StaticLine(self, -1), 0, wx.EXPAND|wx.ALL, 5)
	
	def AddText(self,info):
		self.GetSizer().Add(wx.StaticText(self, -1, info), 0, wx.LEFT|wx.RIGHT, 5)
	
	def AddSeperator(self):
		self.GetSizer().Add(wx.StaticLine(self, -1), 0, wx.EXPAND|wx.ALL, 5)
	
	def AddHiddenSeperator(self):
		self.AddText('')
	
	def AddRadioButton(self, label, style = 0):
		radio = wx.RadioButton(self, -1, label, style=style)
		self.GetSizer().Add(radio, 0, wx.EXPAND|wx.ALL, 5)
		return radio
	
	def AllowNext(self):
		return True
	
	def StoreData(self):
		pass

class FirstInfoPage(InfoPage):
	def __init__(self, parent):
		super(FirstInfoPage, self).__init__(parent, "First time run wizard")
		self.AddText('Welcome, and thanks for trying SkeinPyPy!')
		self.AddSeperator()
		self.AddText('This wizard will help you with the following steps:')
		self.AddText('* Configure SkeinPyPy for your machine')
		self.AddText('* Upgrade your firmware')
		self.AddText('* Calibrate your machine')
		#self.AddText('* Do your first print')

class MachineSelectPage(InfoPage):
	def __init__(self, parent):
		super(MachineSelectPage, self).__init__(parent, "Select your machine")
		self.AddText('What kind of machine do you have:')

		self.UltimakerRadio = self.AddRadioButton("Ultimaker", style=wx.RB_GROUP)
		self.UltimakerRadio.Bind(wx.EVT_RADIOBUTTON, self.OnUltimakerSelect)
		self.OtherRadio = self.AddRadioButton("Other (Ex: RepRap)")
		self.OtherRadio.Bind(wx.EVT_RADIOBUTTON, self.OnOtherSelect)
		
	def OnUltimakerSelect(self, e):
		wx.wizard.WizardPageSimple.Chain(self, self.GetParent().ultimakerFirmwareUpgradePage)
		
	def OnOtherSelect(self, e):
		wx.wizard.WizardPageSimple.Chain(self, self.GetParent().configureMachineDimensions)
	
	def StoreData(self):
		if self.UltimakerRadio.GetValue():
			settings.putPreference('machine_width', '205')
			settings.putPreference('machine_depth', '205')
			settings.putPreference('machine_height', '200')
			settings.putProfileSetting('nozzle_size', '0.4')
			settings.putProfileSetting('machine_center_x', '100')
			settings.putProfileSetting('machine_center_x', '100')

class FirmwareUpgradePage(InfoPage):
	def __init__(self, parent):
		super(FirmwareUpgradePage, self).__init__(parent, "Upgrade Ultimaker Firmware")
		self.AddText('Firmware is the piece of software running directly on your 3D printer.\nThis firmware controls the step motors, regulates the temperature\nand ultimately makes your printer work.')
		self.AddHiddenSeperator()
		self.AddText('The firmware shipping with new Ultimakers works, but upgrades\nhave been made to make better prints, and make calibration easier.')
		self.AddHiddenSeperator()
		self.AddText('SkeinPyPy requires these new features and thus\nyour firmware will most likely need to be upgraded.\nYou will get the chance to do so now.')
		self.AddHiddenSeperator()
		button = wx.Button(self, -1, 'Upgrade firmware')
		self.Bind(wx.EVT_BUTTON, self.OnUpgradeClick)
		self.GetSizer().Add(button, 0)
		self.AddHiddenSeperator()
		self.AddText('Do not upgrade to this firmware if:')
		self.AddText('* You have an older machine based on ATMega1280')
		self.AddText('* Using an LCD panel')
		self.AddText('* Have other changes in the firmware')
	
	def OnUpgradeClick(self, e):
		pass

class configWizard(wx.wizard.Wizard):
	def __init__(self):
		super(configWizard, self).__init__(None, -1, "Configuration Wizard")
		
		self.Bind(wx.wizard.EVT_WIZARD_PAGE_CHANGED, self.OnPageChanged)
		self.Bind(wx.wizard.EVT_WIZARD_PAGE_CHANGING, self.OnPageChanging)
		
		self.firstInfoPage = FirstInfoPage(self)
		self.machineSelectPage = MachineSelectPage(self)
		self.ultimakerFirmwareUpgradePage = FirmwareUpgradePage(self)
		self.configureMachineDimensions = InfoPage(self, 'BLA2')
		
		wx.wizard.WizardPageSimple.Chain(self.firstInfoPage, self.machineSelectPage)
		wx.wizard.WizardPageSimple.Chain(self.machineSelectPage, self.ultimakerFirmwareUpgradePage)
		
		self.FitToPage(self.firstInfoPage)
		self.GetPageAreaSizer().Add(self.firstInfoPage)
		
		self.RunWizard(self.firstInfoPage)
		self.Destroy()

	def OnPageChanging(self, e):
		e.GetPage().StoreData()

	def OnPageChanged(self, e):
		if e.GetPage().AllowNext():
			self.FindWindowById(wx.ID_FORWARD).Enable() 
		else:
			self.FindWindowById(wx.ID_FORWARD).Disable() 
		self.FindWindowById(wx.ID_BACKWARD).Disable() 
