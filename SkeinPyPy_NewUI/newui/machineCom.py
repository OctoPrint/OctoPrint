from __future__ import absolute_import
import __init__

import os, glob, wx, threading

from serial import Serial

from avr_isp import stk500v2
from avr_isp import ispBase
from avr_isp import intelHex

try:
	import _winreg
except:
	pass

def serialList():
    baselist=[]
    if os.name=="nt":
        try:
            key=_winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,"HARDWARE\\DEVICEMAP\\SERIALCOMM")
            i=0
            while(1):
                baselist+=[_winreg.EnumValue(key,i)[1]]
                i+=1
        except:
            pass
    return baselist+glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*') +glob.glob("/dev/tty.usb*")+glob.glob("/dev/cu.*")+glob.glob("/dev/rfcomm*")

class InstallFirmware(wx.Dialog):
	def __init__(self, filename, port = 'AUTO'):
		super(InstallFirmware, self).__init__(parent=None, title="Firmware install", size=(250, 100))
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
			for self.port in serialList():
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
				wx.CallAfter(self.updateLabel, "Done!")
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

class MachineCom():
	def __init__(self, port = 'AUTO', baudrate = 250000):
		self.serial = None
		if port == 'AUTO':
			programmer = stk500v2.Stk500v2()
			for port in serialList():
				try:
					programmer.connect(port)
					programmer.close()
					self.serial = Serial(port, baudrate, timeout=5)
					break
				except ispBase.IspError:
					pass
			programmer.close()
		else:
			self.serial = Serial(port, baudrate, timeout=5)

	def readline(self):
		if self.serial == None:
			return ''
		ret = self.serial.readline()
		print "Recv: " + ret.rstrip()
		return ret
	
	def close(self):
		if self.serial != None:
			self.serial.close()
		self.serial = None
	
	def sendCommand(self, cmd):
		if self.serial == None:
			return
		self.serial.write(cmd + '\n')

