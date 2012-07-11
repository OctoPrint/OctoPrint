from __future__ import absolute_import
import __init__

import os, glob, sys, time, math

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

def baudrateList():
	return [250000, 230400, 115200, 57600, 38400, 19200, 9600]

class VirtualPrinter():
	def __init__(self):
		self.readList = ['start\n', 'Marlin: Virtual Marlin!\n']
		self.temp = 0.0
		self.targetTemp = 0.0
		self.lastTempAt = time.time()
		self.bedTemp = 1.0
		self.bedTargetTemp = 1.0
	
	def write(self, data):
		if self.readList == None:
			return
		print "Send: %s" % (data.rstrip())
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
			self.readList.append("ok T:%.2f /%.2f B:%.2f /%.2f @:64\n" % (self.temp, self.targetTemp, self.bedTemp, self.bedTargetTemp))
		else:
			self.readList.append("ok\n")

	def readline(self):
		if self.readList == None:
			return ''
		n = 0
		timeDiff = self.lastTempAt - time.time()
		self.lastTempAt = time.time()
		if abs(self.temp - self.targetTemp) > 1:
			self.temp += math.copysign(timeDiff, self.targetTemp - self.temp)
		if abs(self.bedTemp - self.bedTargetTemp) > 1:
			self.bedTemp += math.copysign(timeDiff, self.bedTargetTemp - self.bedTemp)
		while len(self.readList) < 1:
			time.sleep(0.1)
			n += 1
			if n == 20:
				return ''
			if self.readList == None:
				return ''
		time.sleep(0.01)
		print "Recv: %s" % (self.readList[0].rstrip())
		return self.readList.pop(0)
	
	def close(self):
		self.readList = None

class MachineCom():
	def __init__(self, port = None, baudrate = None):
		if port == None:
			port = profile.getPreference('serial_port')
		if baudrate == None:
			if profile.getPreference('serial_baud') == 'AUTO':
				baudrate = 0
			else:
				baudrate = int(profile.getPreference('serial_baud'))
		self.serial = None
		if port == 'AUTO':
			programmer = stk500v2.Stk500v2()
			for port in serialList():
				try:
					print "Connecting to: %s" % (port)
					programmer.connect(port)
					programmer.close()
					time.sleep(1)
					self.serial = self._openPortWithBaudrate(port, baudrate)
					break
				except ispBase.IspError as (e):
					print "Error while connecting to %s" % (port)
					print e
					pass
				except:
					print "Unexpected error while connecting to serial port:" + port, sys.exc_info()[0]
			programmer.close()
		elif port == 'VIRTUAL':
			self.serial = VirtualPrinter()
		else:
			try:
				self.serial = self._openPortWithBaudrate(port, baudrate)
			except:
				print "Unexpected error while connecting to serial port:" + port, sys.exc_info()[0]
		print self.serial
	
	def _openPortWithBaudrate(self, port, baudrate):
		if baudrate != 0:
			return Serial(port, baudrate, timeout=2)
		for baudrate in baudrateList():
			try:
				ser = Serial(port, baudrate, timeout=2)
			except:
				print "Unexpected error while connecting to serial port:" + port, sys.exc_info()[0]
				continue
			ser.setDTR(1)
			time.sleep(0.1)
			ser.setDTR(0)
			time.sleep(0.2)
			starttime = time.time()
			for line in ser:
				if line.startswith('start'):
					ser.close()
					ser = Serial(port, baudrate, timeout=2)
					ser.setDTR(1)
					time.sleep(0.1)
					ser.setDTR(0)
					time.sleep(0.2)
					return ser
				if starttime - time.time() > 10:
					break
			ser.close()
		return None

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
