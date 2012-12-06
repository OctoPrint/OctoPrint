from __future__ import absolute_import

import os, wx, threading, sys

from Cura.avr_isp import stk500v2
from Cura.avr_isp import ispBase
from Cura.avr_isp import intelHex

from Cura.util import machineCom
from Cura.util import profile

def getDefaultFirmware():
	if profile.getPreference('machine_type') == 'ultimaker':
		if sys.platform.startswith('linux'):
			return os.path.join(os.path.dirname(os.path.abspath(__file__)), "../firmware/ultimaker_115200.hex")
		else:
			return os.path.join(os.path.dirname(os.path.abspath(__file__)), "../firmware/ultimaker_250000.hex")
	return None

class InstallFirmware(wx.Dialog):
	def __init__(self, filename = None, port = None):
		super(InstallFirmware, self).__init__(parent=None, title="Firmware install", size=(250, 100))
		if port == None:
			port = profile.getPreference('serial_port')
		if filename == None:
			filename = getDefaultFirmware()
		if filename == None:
			wx.MessageBox('Cura does not ship with a default firmware for your machine.', 'Firmware update', wx.OK | wx.ICON_ERROR)
			self.Destroy()
			return

		sizer = wx.BoxSizer(wx.VERTICAL)
		
		self.progressLabel = wx.StaticText(self, -1, 'Reading firmware...')
		sizer.Add(self.progressLabel, 0, flag=wx.ALIGN_CENTER)
		self.progressGauge = wx.Gauge(self, -1)
		sizer.Add(self.progressGauge, 0, flag=wx.EXPAND)
		self.okButton = wx.Button(self, -1, 'Ok')
		self.okButton.Disable()
		self.okButton.Bind(wx.EVT_BUTTON, self.OnOk)
		sizer.Add(self.okButton, 0, flag=wx.ALIGN_CENTER)
		self.SetSizer(sizer)
		
		self.filename = filename
		self.port = port
		
		threading.Thread(target=self.OnRun).start()
		
		self.ShowModal()
		self.Destroy()
		return

	def OnRun(self):
		hexFile = intelHex.readHex(self.filename)
		wx.CallAfter(self.updateLabel, "Connecting to machine...")
		programmer = stk500v2.Stk500v2()
		programmer.progressCallback = self.OnProgress
		if self.port == 'AUTO':
			for self.port in machineCom.serialList():
				try:
					programmer.connect(self.port)
					break
				except ispBase.IspError:
					pass
		else:
			try:
				programmer.connect(self.port)
			except ispBase.IspError:
				pass
				
		if programmer.isConnected():
			wx.CallAfter(self.updateLabel, "Uploading firmware...")
			try:
				programmer.programChip(hexFile)
				wx.CallAfter(self.updateLabel, "Done!\nInstalled firmware: %s" % (os.path.basename(self.filename)))
			except ispBase.IspError as e:
				wx.CallAfter(self.updateLabel, "Failed to write firmware.\n" + str(e))
				
			programmer.close()
			wx.CallAfter(self.okButton.Enable)
			return
		wx.MessageBox('Failed to find machine for firmware upgrade\nIs your machine connected to the PC?', 'Firmware update', wx.OK | wx.ICON_ERROR)
		wx.CallAfter(self.Close)
	
	def updateLabel(self, text):
		self.progressLabel.SetLabel(text)
		self.Layout()
	
	def OnProgress(self, value, max):
		wx.CallAfter(self.progressGauge.SetRange, max)
		wx.CallAfter(self.progressGauge.SetValue, value)

	def OnOk(self, e):
		self.Close()

	def OnClose(self, e):
		self.Destroy()

