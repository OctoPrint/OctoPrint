from __future__ import absolute_import
import __init__

import os, glob, wx, threading, sys, time

from serial import Serial

from avr_isp import stk500v2
from avr_isp import ispBase
from avr_isp import intelHex

from util import profile

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
	def __init__(self, filename, port = None):
		super(InstallFirmware, self).__init__(parent=None, title="Firmware install", size=(250, 100))
		if port == None:
			port = profile.getPreference('serial_port')

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

class VirtualPrinter():
	def __init__(self):
		self.readList = ['start\n']
		self.temp = 0.0
		self.targetTemp = 0.0
	
	def write(self, data):
		if self.readList == None:
			return
		print "Send: %s" % (data.rstrip())
		if 'M104' in data:
			try:
				self.targetTemp = float(data[data.find('S')+1:])
			except:
				pass
		if 'M105' in data:
			self.readList.append("ok T:%f/%f\n" % (self.temp, self.targetTemp))
		else:
			self.readList.append("ok\n")

	def readline(self):
		if self.readList == None:
			return ''
		n = 0
		self.temp = (self.temp + self.targetTemp) / 2
		while len(self.readList) < 1:
			time.sleep(0.1)
			n += 1
			if n == 20:
				return ''
			if self.readList == None:
				return ''
		time.sleep(0.001)
		print "Recv: %s" % (self.readList[0].rstrip())
		return self.readList.pop(0)
	
	def close(self):
		self.readList = None

class MachineCom():
	def __init__(self, port = None, baudrate = None):
		if port == None:
			port = profile.getPreference('serial_port')
		if baudrate == None:
			baudrate = int(profile.getPreference('serial_baud'))
		self.serial = None
		if port == 'AUTO':
			programmer = stk500v2.Stk500v2()
			for port in serialList():
				try:
					print "Connecting to: %s %i" % (port, baudrate)
					programmer.connect(port)
					programmer.close()
					time.sleep(1)
					self.serial = Serial(port, baudrate, timeout=2)
					break
				except ispBase.IspError as (e):
					print "Error while connecting to %s %i" % (port, baudrate)
					print e
					pass
				except:
					print "Unexpected error while connecting to serial port:" + port, sys.exc_info()[0]
			programmer.close()
		elif port == 'VIRTUAL':
			self.serial = VirtualPrinter()
		else:
			try:
				self.serial = Serial(port, baudrate, timeout=2)
			except:
				print "Unexpected error while connecting to serial port:" + port, sys.exc_info()[0]
		print self.serial

	def readline(self):
		if self.serial == None:
			return None
		ret = self.serial.readline()
		#if ret != '':
		#	print "Recv: " + ret.rstrip()
		return ret
	
	def close(self):
		if self.serial != None:
			self.serial.close()
		self.serial = None
	
	def __del__(self):
		self.close()
	
	def isOpen(self):
		return self.serial != None
	
	def sendCommand(self, cmd):
		if self.serial == None:
			return
		#print 'Send: ' + cmd
		self.serial.write(cmd + '\n')

