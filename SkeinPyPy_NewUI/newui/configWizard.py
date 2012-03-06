from __future__ import absolute_import
import __init__

import wx, os, platform, types, webbrowser, threading
import wx.wizard

from fabmetheus_utilities import settings
from newui import machineCom

class InfoPage(wx.wizard.WizardPageSimple):
	def __init__(self, parent, title):
		wx.wizard.WizardPageSimple.__init__(self, parent)

		sizer = wx.BoxSizer(wx.VERTICAL)
		self.sizer = sizer
		self.SetSizer(sizer)

		title = wx.StaticText(self, -1, title)
		title.SetFont(wx.Font(18, wx.SWISS, wx.NORMAL, wx.BOLD))
		sizer.Add(title, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		sizer.Add(wx.StaticLine(self, -1), 0, wx.EXPAND|wx.ALL, 5)
	
	def AddText(self,info):
		text = wx.StaticText(self, -1, info)
		self.GetSizer().Add(text, 0, wx.LEFT|wx.RIGHT, 5)
		return text
	
	def AddSeperator(self):
		self.GetSizer().Add(wx.StaticLine(self, -1), 0, wx.EXPAND|wx.ALL, 5)
	
	def AddHiddenSeperator(self):
		self.AddText('')
	
	def AddRadioButton(self, label, style = 0):
		radio = wx.RadioButton(self, -1, label, style=style)
		self.GetSizer().Add(radio, 0, wx.EXPAND|wx.ALL, 5)
		return radio
	
	def AddDualButton(self, label1, label2):
		p = wx.Panel(self)
		p.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
		button1 = wx.Button(p, -1, label1)
		p.GetSizer().Add(button1, 0, wx.RIGHT, 8)
		button2 = wx.Button(p, -1, label2)
		p.GetSizer().Add(button2, 0)
		self.GetSizer().Add(p, 0)
		return button1, button2
	
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

class RepRapInfoPage(InfoPage):
	def __init__(self, parent):
		super(RepRapInfoPage, self).__init__(parent, "RepRap information")
		self.AddText('Sorry, but this wizard will not help you with\nconfiguring and calibrating your RepRap.')
		self.AddSeperator()
		self.AddText('You will have to manually install Marlin firmware\nand configure SkeinPyPy.')

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
		wx.wizard.WizardPageSimple.Chain(self, self.GetParent().repRapInfoPage)
	
	def StoreData(self):
		if self.UltimakerRadio.GetValue():
			settings.putPreference('machine_width', '205')
			settings.putPreference('machine_depth', '205')
			settings.putPreference('machine_height', '200')
			settings.putProfileSetting('nozzle_size', '0.4')
			settings.putProfileSetting('machine_center_x', '100')
			settings.putProfileSetting('machine_center_y', '100')
		else:
			settings.putPreference('machine_width', '80')
			settings.putPreference('machine_depth', '80')
			settings.putPreference('machine_height', '60')
			settings.putProfileSetting('nozzle_size', '0.4')
			settings.putProfileSetting('machine_center_x', '40')
			settings.putProfileSetting('machine_center_y', '40')

class FirmwareUpgradePage(InfoPage):
	def __init__(self, parent):
		super(FirmwareUpgradePage, self).__init__(parent, "Upgrade Ultimaker Firmware")
		self.AddText('Firmware is the piece of software running directly on your 3D printer.\nThis firmware controls the step motors, regulates the temperature\nand ultimately makes your printer work.')
		self.AddHiddenSeperator()
		self.AddText('The firmware shipping with new Ultimakers works, but upgrades\nhave been made to make better prints, and make calibration easier.')
		self.AddHiddenSeperator()
		self.AddText('SkeinPyPy requires these new features and thus\nyour firmware will most likely need to be upgraded.\nYou will get the chance to do so now.')
		b1, b2 = self.AddDualButton('Upgrade firmware', 'Skip upgrade')
		b1.Bind(wx.EVT_BUTTON, self.OnUpgradeClick)
		b2.Bind(wx.EVT_BUTTON, self.OnSkipClick)
		self.AddHiddenSeperator()
		self.AddText('Do not upgrade to this firmware if:')
		self.AddText('* You have an older machine based on ATMega1280')
		self.AddText('* Using an LCD panel')
		self.AddText('* Have other changes in the firmware')
		button = wx.Button(self, -1, 'Goto this page for a custom firmware')
		button.Bind(wx.EVT_BUTTON, self.OnUrlClick)
		self.GetSizer().Add(button, 0)
	
	def AllowNext(self):
		return False
	
	def OnUpgradeClick(self, e):
		if machineCom.InstallFirmware(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../firmware/default.hex")):
			self.GetParent().FindWindowById(wx.ID_FORWARD).Enable()
		
	def OnSkipClick(self, e):
		self.GetParent().FindWindowById(wx.ID_FORWARD).Enable()
	
	def OnUrlClick(self, e):
		webbrowser.open('http://daid.mine.nu/~daid/marlin_build/')

class UltimakerCheckupPage(InfoPage):
	def __init__(self, parent):
		super(UltimakerCheckupPage, self).__init__(parent, "Ultimaker Checkup")
		self.AddText('It is a good idea to do a few sanity checks\nnow on your Ultimaker. But you can skip these\nif you know your machine is functional.')
		b1, b2 = self.AddDualButton('Run checks', 'Skip checks')
		b1.Bind(wx.EVT_BUTTON, self.OnCheckClick)
		b2.Bind(wx.EVT_BUTTON, self.OnSkipClick)
		self.AddSeperator();
		self.checkPanel = None
	
	def AllowNext(self):
		return False
	
	def OnSkipClick(self, e):
		self.GetParent().FindWindowById(wx.ID_FORWARD).Enable()
		self.comm.serial.close()
	
	def OnCheckClick(self, e):
		if self.checkPanel != None:
			self.checkPanel.Destroy()
		self.checkPanel = wx.Panel(self)
		self.checkPanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		self.GetSizer().Add(self.checkPanel, 0, wx.LEFT|wx.RIGHT, 5)
		threading.Thread(target=self.OnRun).start()

	def AddProgressText(self, info):
		text = wx.StaticText(self.checkPanel, -1, info)
		self.checkPanel.GetSizer().Add(text, 0)
		self.checkPanel.Layout()
		self.Layout()
	
	def OnRun(self):
		wx.CallAfter(self.AddProgressText, "Connecting to machine...")
		comm = machineCom.MachineCom()
		self.comm = comm
		wx.CallAfter(self.AddProgressText, "Checking start message...")
		t = threading.Timer(5, self.OnSerialTimeout)
		t.start()
		line = comm.readline()
		hasStart = False
		while line != '':
			if line.startswith('start'):
				hasStart = True
				break
			line = comm.readline()
		t.cancel()
		if not hasStart:
			wx.CallAfter(self.AddProgressText, "Error: Missing start message.")
			comm.close()
			return
		wx.CallAfter(self.AddProgressText, "Done!")
		wx.CallAfter(self.GetParent().FindWindowById(wx.ID_FORWARD).Enable)
		comm.close()
		
	def OnSerialTimeout(self):
		self.comm.close()

class configWizard(wx.wizard.Wizard):
	def __init__(self):
		super(configWizard, self).__init__(None, -1, "Configuration Wizard")
		
		self.Bind(wx.wizard.EVT_WIZARD_PAGE_CHANGED, self.OnPageChanged)
		self.Bind(wx.wizard.EVT_WIZARD_PAGE_CHANGING, self.OnPageChanging)
		
		self.firstInfoPage = FirstInfoPage(self)
		self.machineSelectPage = MachineSelectPage(self)
		self.ultimakerFirmwareUpgradePage = FirmwareUpgradePage(self)
		self.ultimakerCheckupPage = UltimakerCheckupPage(self)
		self.repRapInfoPage = RepRapInfoPage(self)
		
		wx.wizard.WizardPageSimple.Chain(self.firstInfoPage, self.machineSelectPage)
		wx.wizard.WizardPageSimple.Chain(self.machineSelectPage, self.ultimakerFirmwareUpgradePage)
		wx.wizard.WizardPageSimple.Chain(self.ultimakerFirmwareUpgradePage, self.ultimakerCheckupPage)
		
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
