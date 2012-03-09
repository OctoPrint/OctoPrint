from __future__ import absolute_import
import __init__

import wx, os, platform, types, webbrowser, threading, time, re
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
		upgradeButton, skipUpgradeButton = self.AddDualButton('Upgrade to Marlin firmware', 'Skip upgrade')
		upgradeButton.Bind(wx.EVT_BUTTON, self.OnUpgradeClick)
		skipUpgradeButton.Bind(wx.EVT_BUTTON, self.OnSkipClick)
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
		self.AddText('It is a good idea to do a few sanity checks now on your Ultimaker.\nYou can skip these if you know your machine is functional.')
		b1, b2 = self.AddDualButton('Run checks', 'Skip checks')
		b1.Bind(wx.EVT_BUTTON, self.OnCheckClick)
		b2.Bind(wx.EVT_BUTTON, self.OnSkipClick)
		self.AddSeperator();
		self.checkPanel = None
	
	def AllowNext(self):
		return False
	
	def OnSkipClick(self, e):
		self.GetParent().FindWindowById(wx.ID_FORWARD).Enable()
	
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
		self.comm = machineCom.MachineCom()

		wx.CallAfter(self.AddProgressText, "Checking start message...")
		if self.DoCommCommandWithTimeout(None, 'start') == False:
			wx.CallAfter(self.AddProgressText, "Error: Missing start message.")
			return
			
		wx.CallAfter(self.AddProgressText, "Disabling step motors...")
		if self.DoCommCommandWithTimeout('M84') == False:
			wx.CallAfter(self.AddProgressText, "Error: Missing reply to Deactivate steppers (M84).")
			wx.CallAfter(self.AddProgressText, "Possible cause: Temperature MIN/MAX.\nCheck temperature sensor connections.")
			return

		wx.MessageBox('Please move the printer head to the center of the machine\nalso move the platform so it is not at the highest or lowest position,\nand make sure the machine is powered on.', 'Machine check', wx.OK | wx.ICON_INFORMATION)
		
		idleTemp = self.readTemp()
		
		wx.CallAfter(self.AddProgressText, "Checking heater and temperature sensor...")
		wx.CallAfter(self.AddProgressText, "(This takes about 30 seconds)")
		if self.DoCommCommandWithTimeout("M104 S100") == False:
			wx.CallAfter(self.AddProgressText, "Failed to set temperature")
			return
		
		time.sleep(25)
		tempInc = self.readTemp() - idleTemp
		
		if self.DoCommCommandWithTimeout("M104 S0") == False:
			wx.CallAfter(self.AddProgressText, "Failed to set temperature")
			return
		
		if tempInc < 15:
			wx.CallAfter(self.AddProgressText, "Your temperature sensor or heater is not working!")
			return
		wx.CallAfter(self.AddProgressText, "Heater and temperature sensor working\nWarning: head might still be hot!")

		wx.CallAfter(self.AddProgressText, "Checking endstops")
		if self.DoCommCommandWithTimeout('M119', 'x_min') != "x_min:L x_max:L y_min:L y_max:L z_min:L z_max:L":
			wx.CallAfter(self.AddProgressText, "Error: There is a problem in your endstops!\nOne of them seems to be pressed while it shouldn't\ncheck the cable connections and the switches themselfs.")
			return
		wx.CallAfter(self.AddProgressText, "Please press the X end switch in the front left corner.")
		if not self.DoCommCommandAndWaitForReply('M119', 'x_min', "x_min:H x_max:L y_min:L y_max:L z_min:L z_max:L"):
			wx.CallAfter(self.AddProgressText, "Failed to check the x_min endstop!")
			return
		wx.CallAfter(self.AddProgressText, "Please press the X end switch in the front right corner.")
		if not self.DoCommCommandAndWaitForReply('M119', 'x_min', "x_min:L x_max:H y_min:L y_max:L z_min:L z_max:L"):
			wx.CallAfter(self.AddProgressText, "Failed to check the x_max endstop!")
			return
		wx.CallAfter(self.AddProgressText, "Please press the Y end switch in the front left corner.")
		if not self.DoCommCommandAndWaitForReply('M119', 'x_min', "x_min:L x_max:L y_min:H y_max:L z_min:L z_max:L"):
			wx.CallAfter(self.AddProgressText, "Failed to check the x_max endstop!")
			return
		wx.CallAfter(self.AddProgressText, "Please press the Y end switch in the back left corner.")
		if not self.DoCommCommandAndWaitForReply('M119', 'x_min', "x_min:L x_max:L y_min:L y_max:H z_min:L z_max:L"):
			wx.CallAfter(self.AddProgressText, "Failed to check the x_max endstop!")
			return
		wx.CallAfter(self.AddProgressText, "Please press the Z end switch in the top.")
		if not self.DoCommCommandAndWaitForReply('M119', 'x_min', "x_min:L x_max:L y_min:L y_max:L z_min:H z_max:L"):
			wx.CallAfter(self.AddProgressText, "Failed to check the x_max endstop!")
			return
		wx.CallAfter(self.AddProgressText, "Please press the Z end switch in the bottom.")
		if not self.DoCommCommandAndWaitForReply('M119', 'x_min', "x_min:L x_max:L y_min:L y_max:L z_min:L z_max:H"):
			wx.CallAfter(self.AddProgressText, "Failed to check the x_max endstop!")
			return
		wx.CallAfter(self.AddProgressText, "End stops are working.")

		wx.CallAfter(self.AddProgressText, "Done!")
		wx.CallAfter(self.GetParent().FindWindowById(wx.ID_FORWARD).Enable)
		self.comm.close()
		
	def readTemp(self):
		line = self.DoCommCommandWithTimeout("M105", "ok T:")
		if line == False:
			return -1
		return int(re.search('T:([0-9]*)', line).group(1))
	
	def DoCommCommandAndWaitForReply(self, cmd, replyStart, reply):
		while True:
			ret = self.DoCommCommandWithTimeout(cmd, replyStart)
			if ret == reply:
				return True
			if ret == False:
				return False
	
	def DoCommCommandWithTimeout(self, cmd = None, replyStart = 'ok'):
		if cmd != None:
			self.comm.sendCommand(cmd)
		t = threading.Timer(5, self.OnSerialTimeout)
		t.start()
		while True:
			line = self.comm.readline()
			if line == '':
				self.comm.close()
				return False
			if line.startswith(replyStart):
				break
		t.cancel()
		return line.rstrip()
	
	def OnSerialTimeout(self):
		self.comm.close()

class UltimakerCalibrationPage(InfoPage):
	def __init__(self, parent):
		super(UltimakerCalibrationPage, self).__init__(parent, "Ultimaker Calibration")
		
		self.AddText("Your Ultimaker requires some calibration.");
		self.AddText("This calibration is needed for a proper extrusion amount.");
		self.AddSeperator()
		self.AddText("The following values are needed:");
		self.AddText("* Diameter of filament");
		self.AddText("* Number of steps per mm of filament extrusion");
		self.AddSeperator()
		self.AddText("The better you have calibrated these values, the better your prints\nwill become.");
		self.AddSeperator()
		self.AddText("First we need the diameter of your filament:");
		self.filamentDiameter = wx.TextCtrl(self, -1, settings.getProfileSetting('filament_diameter', '2.89'))
		self.GetSizer().Add(self.filamentDiameter, 0, wx.LEFT, 5)
		self.AddText("If you do not own digital Calipers that can measure\nat least 2 digits then use 2.89mm.\nWhich is the average diameter of most filament.");
		self.AddText("Note: This value can be changed later at any time.");

	def StoreData(self):
		settings.putProfileSetting('filament_diameter', self.filamentDiameter.GetValue())

class UltimakerCalibrateStepsPerEPage(InfoPage):
	def __init__(self, parent):
		super(UltimakerCalibrateStepsPerEPage, self).__init__(parent, "Ultimaker Calibration")
		
		self.AddText("Calibrating the Steps Per E requires some manual actions.")
		self.AddText("First remove any filament from your machine.")
		self.AddText("Next put in your filament so the tip is aligned with the\ntop of the extruder drive.")
		self.AddText("We'll push the filament 100mm")
		self.AddText("[BUTTON:PUSH 100mm]")
		self.AddText("Now measure the amount of extruded filament:\n(this can be more or less then 100mm)")
		self.AddText("[INPUT:MEASUREMENT][BUTTON:SAVE]")
		self.AddText("This results in the following steps per E:")
		self.AddText("[INPUT:E_RESULT]")
		self.AddText("You can repeat these steps to get better calibration.")

class configWizard(wx.wizard.Wizard):
	def __init__(self):
		super(configWizard, self).__init__(None, -1, "Configuration Wizard")
		
		self.Bind(wx.wizard.EVT_WIZARD_PAGE_CHANGED, self.OnPageChanged)
		self.Bind(wx.wizard.EVT_WIZARD_PAGE_CHANGING, self.OnPageChanging)

		self.firstInfoPage = FirstInfoPage(self)
		self.machineSelectPage = MachineSelectPage(self)
		self.ultimakerFirmwareUpgradePage = FirmwareUpgradePage(self)
		self.ultimakerCheckupPage = UltimakerCheckupPage(self)
		self.ultimakerCalibrationPage = UltimakerCalibrationPage(self)
		self.ultimakerCalibrateStepsPerEPage = UltimakerCalibrateStepsPerEPage(self)
		self.repRapInfoPage = RepRapInfoPage(self)

		wx.wizard.WizardPageSimple.Chain(self.firstInfoPage, self.machineSelectPage)
		wx.wizard.WizardPageSimple.Chain(self.machineSelectPage, self.ultimakerFirmwareUpgradePage)
		wx.wizard.WizardPageSimple.Chain(self.ultimakerFirmwareUpgradePage, self.ultimakerCheckupPage)
		wx.wizard.WizardPageSimple.Chain(self.ultimakerCheckupPage, self.ultimakerCalibrationPage)
		wx.wizard.WizardPageSimple.Chain(self.ultimakerCalibrationPage, self.ultimakerCalibrateStepsPerEPage)
		
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
