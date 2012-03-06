from __future__ import absolute_import
import __init__

import os, glob, wx

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
    return baselist+glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*') +glob.glob("/dev/tty.*")+glob.glob("/dev/cu.*")+glob.glob("/dev/rfcomm*")

def installFirmware(filename, port = 'AUTO'):
	hexFile = intelHex.readHex(filename)
	programmer = stk500v2.Stk500v2()
	if port == 'AUTO':
		for port in serialList():
			try:
				programmer.connect(port)
			except ispBase.IspError:
				pass
	else:
		programmer.connect(port)
	if programmer.isConnected():
		programmer.programChip(hexFile)
		programmer.close()
		return True
	wx.MessageBox('Failed to find machine for firmware upgrade\nIs your machine connected to the PC?', 'Firmware update', wx.OK | wx.ICON_ERROR)
	return False

def serialOpen(port = 'AUTO', baudrate = 115200):
	if port == 'AUTO':
		programmer = stk500v2.Stk500v2()
		for port in serialList():
			try:
				programmer.connect(port)
				programmer.close()
				return Serial(port, baudrate, timeout=5)
			except ispBase.IspError:
				pass
		programmer.close()
	else:
		return Serial(port, baudrate, timeout=5)
	return False

