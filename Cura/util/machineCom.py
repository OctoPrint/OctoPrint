from __future__ import absolute_import
import __init__

import os, glob, sys, time, math, traceback

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
		self.readList = ['start\n', 'Marlin: Virtual Marlin!\n', '\x80\n']
		self.temp = 0.0
		self.targetTemp = 0.0
		self.lastTempAt = time.time()
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
		#print "Recv: %s" % (self.readList[0].rstrip())
		return self.readList.pop(0)
	
	def close(self):
		self.readList = None

class MachineCom():
	def __init__(self, port = None, baudrate = None, logCallback = None):
		self._logCallback = logCallback
		if port == None:
			port = profile.getPreference('serial_port')
		if baudrate == None:
			if profile.getPreference('serial_baud') == 'AUTO':
				baudrate = 0
			else:
				baudrate = int(profile.getPreference('serial_baud'))
		self._serial = None
		if port == 'AUTO':
			programmer = stk500v2.Stk500v2()
			self._log("Serial port list: %s" % (str(serialList())))
			for port in serialList():
				try:
					self._log("Connecting to: %s" % (port))
					programmer.connect(port)
					self._serial = programmer.leaveISP()
					self._configureSerialWithBaudrate(baudrate)
					break
				except ispBase.IspError as (e):
					self._log("Error while connecting to %s: %s" % (port, str(e)))
					pass
				except:
					self._log("Unexpected error while connecting to serial port: %s %s" % (port, getExceptionString()))
			programmer.close()
		elif port == 'VIRTUAL':
			self._serial = VirtualPrinter()
		else:
			try:
				self._serial = Serial(port, 115200, timeout=2)
				self._configureSerialWithBaudrate(baudrate)
			except:
				self._log("Unexpected error while connecting to serial port: %s %s" % (port, getExceptionString()))
				print 
		print self._serial
	
	def _configureSerialWithBaudrate(self, baudrate):
		if baudrate != 0:
			self._serial.baudrate = baudrate
			return
		for baudrate in baudrateList():
			try:
				self._serial.baudrate = baudrate
				self._log("Trying baudrate: %d" % (baudrate))
			except:
				self._log("Unexpected error while setting baudrate: %d %s" % (baudrate, getExceptionString()))
				continue
			time.sleep(0.5)
			starttime = time.time()
			self.sendCommand("\nM105")
			for line in self._serial:
				self._log("Recv: %s" % (unicode(line, 'utf-8', 'replace').rstrip()))
				if 'start' in line:
					return
				if 'ok' in line:
					return
				#Timeout in case we get a lot of crap data from some random device.
				if starttime - time.time() > 5:
					break
		self._serial.close()
		self._serial = None
	
	def _log(self, message):
		if self._logCallback != None:
			self._logCallback(message)
		else:
			print(message)

	def readline(self):
		if self._serial == None:
			return None
		try:
			ret = self._serial.readline()
		except:
			self._log("Unexpected error while reading serial port: %s" % (getExceptionString()))
			return ''
		if ret != '':
			self._log("Recv: %s" % (unicode(ret, 'utf-8', 'replace').rstrip()))
		else:
			self._log("Recv: TIMEOUT")
		return ret
	
	def close(self):
		if self._serial != None:
			self._serial.close()
		self._serial = None
	
	def __del__(self):
		self.close()
	
	def isOpen(self):
		return self._serial != None
	
	def sendCommand(self, cmd):
		if self._serial == None:
			return
		self._log('Send: %s' % (cmd))
		try:
			self._serial.write(cmd)
			self._serial.write('\n')
		except:
			self._log("Unexpected error while writing serial port: %s" % (getExceptionString()))

def getExceptionString():
	locationInfo = traceback.extract_tb(sys.exc_info()[2])[0]
	return "%s: '%s' @ %s:%s:%d" % (str(sys.exc_info()[0].__name__), str(sys.exc_info()[1]), os.path.basename(locationInfo[0]), locationInfo[2], locationInfo[1])

