from __future__ import absolute_import
import __init__

import os, glob, sys, time

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

class VirtualPrinter():
	def __init__(self):
		self.readList = ['start\n']
		self.temp = 0.0
		self.targetTemp = 0.0
		self.bedTemp = 1.0
		self.bedTargetTemp = 1.0
	
	def write(self, data):
		if self.readList == None:
			return
		#print "Send: %s" % (data.rstrip())
		if 'M104' in data or 'M109' in data:
			try:
				self.targetTemp = float(data[data.find('S')+1:])
			except:
				pass
		if 'M140' in data or 'M190' in data:
			try:
				self.bedTargetTemp = float(data[data.find('S')+1:])
			except:
				pass
		if 'M105' in data:
			self.readList.append("ok T:%f /%f B:%f /%f @:64\n" % (self.temp, self.targetTemp, self.bedTemp, self.bedTargetTemp))
		else:
			self.readList.append("ok\n")

	def readline(self):
		if self.readList == None:
			return ''
		n = 0
		self.temp = (self.temp + self.targetTemp) / 2
		self.bedTemp = (self.bedTemp + self.bedTargetTemp) / 2
		while len(self.readList) < 1:
			time.sleep(0.1)
			n += 1
			if n == 20:
				return ''
			if self.readList == None:
				return ''
		time.sleep(0.01)
		#print "Recv: %s" % (self.readList[0].rstrip())
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

