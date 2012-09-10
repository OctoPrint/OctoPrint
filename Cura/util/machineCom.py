from __future__ import absolute_import
import __init__

import os, glob, sys, time, math, re, traceback, threading
import Queue as queue

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
	baselist = baselist + glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*') + glob.glob("/dev/tty.usb*") + glob.glob("/dev/cu.*") + glob.glob("/dev/rfcomm*")
	prev = profile.getPreference('serial_port_auto')
	if prev in baselist:
		baselist.remove(prev)
		baselist.insert(0, prev)
	return baselist

def baudrateList():
	ret = [250000, 230400, 115200, 57600, 38400, 19200, 9600]
	if profile.getPreference('serial_baud_auto') != '':
		prev = int(profile.getPreference('serial_baud_auto'))
		if prev in ret:
			ret.remove(prev)
			ret.insert(0, prev)
	return ret

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
		elif len(data.strip()) > 0:
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

class MachineComPrintCallback(object):
	def mcLog(self, message):
		print(message)
	
	def mcTempUpdate(self, temp, bedTemp):
		pass
	
	def mcStateChange(self, state):
		pass
	
	def mcMessage(self, message):
		pass
	
	def mcProgress(self, lineNr):
		pass
	
	def mcZChange(self, newZ):
		pass

class MachineCom(object):
	STATE_NONE = 0
	STATE_DETECT_BAUDRATE = 1
	STATE_CONNECTING = 2
	STATE_OPERATIONAL = 3
	STATE_PRINTING = 4
	STATE_PAUSED = 5
	STATE_CLOSED = 6
	STATE_ERROR = 7
	STATE_CLOSED_WITH_ERROR = 8
	
	def __init__(self, port = None, baudrate = None, callbackObject = None):
		if port == None:
			port = profile.getPreference('serial_port')
		if baudrate == None:
			if profile.getPreference('serial_baud') == 'AUTO':
				baudrate = 0
			else:
				baudrate = int(profile.getPreference('serial_baud'))
		if callbackObject == None:
			callbackObject = MachineComPrintCallback()

		self._callback = callbackObject
		self._state = self.STATE_NONE
		self._serial = None
		self._baudrateDetectList = baudrateList()
		self._baudrateDetectRetry = 0
		self._temp = 0
		self._bedTemp = 0
		self._gcodeList = None
		self._gcodePos = 0
		self._commandQueue = queue.Queue()
		self._logQueue = queue.Queue(256)
		self._feedRateModifier = {}
		self._currentZ = -1
		
		if port == 'AUTO':
			programmer = stk500v2.Stk500v2()
			self._log("Serial port list: %s" % (str(serialList())))
			for port in serialList():
				try:
					self._log("Connecting to: %s" % (port))
					programmer.connect(port)
					self._serial = programmer.leaveISP()
					profile.putPreference('serial_port_auto', port)
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
				self._log("Connecting to: %s" % (port))
				if baudrate == 0:
					self._serial = Serial(port, 115200, timeout=0.1)
				else:
					self._serial = Serial(port, baudrate, timeout=2)
			except:
				self._log("Unexpected error while connecting to serial port: %s %s" % (port, getExceptionString()))
		self._log("Connected to: %s, starting monitor" % (self._serial))
		if baudrate == 0:
			self._changeState(self.STATE_DETECT_BAUDRATE)
		else:
			self._changeState(self.STATE_CONNECTING)
		self.thread = threading.Thread(target=self._monitor)
		self.thread.daemon = True
		self.thread.start()
	
	def _changeState(self, newState):
		if self._state == newState:
			return
		oldState = self.getStateString()
		self._state = newState
		self._log('Changing monitoring state from \'%s\' to \'%s\'' % (oldState, self.getStateString()))
		self._callback.mcStateChange(newState)
	
	def getState(self):
		return self._state
	
	def getStateString(self):
		if self._state == self.STATE_NONE:
			return "Offline"
		if self._state == self.STATE_DETECT_BAUDRATE:
			return "Detect baudrate"
		if self._state == self.STATE_CONNECTING:
			return "Connecting"
		if self._state == self.STATE_OPERATIONAL:
			return "Operational"
		if self._state == self.STATE_PRINTING:
			return "Printing"
		if self._state == self.STATE_PAUSED:
			return "Paused"
		if self._state == self.STATE_CLOSED:
			return "Closed"
		if self._state == self.STATE_ERROR:
			return "Error: %s" % (self._errorValue)
		if self._state == self.STATE_CLOSED_WITH_ERROR:
			return "Error: %s" % (self._errorValue)
		return "?%d?" % (self._state)
	
	def isClosedOrError(self):
		return self._state == self.STATE_ERROR or self._state == self.STATE_CLOSED_WITH_ERROR or self._state == self.STATE_CLOSED
	
	def isOperational(self):
		return self._state == self.STATE_OPERATIONAL or self._state == self.STATE_PRINTING or self._state == self.STATE_PAUSED
	
	def isPrinting(self):
		return self._state == self.STATE_PRINTING
	
	def getPrintPos(self):
		return self._gcodePos
	
	def isPaused(self):
		return self._state == self.STATE_PAUSED
	
	def getTemp(self):
		return self._temp
	
	def getBedTemp(self):
		return self._bedTemp
	
	def _monitor(self):
		timeout = time.time() + 5
		while True:
			line = self._readline()
			if line == None:
				break
			
			#No matter the state, if we see an error, goto the error state and store the error for reference.
			if line.startswith('Error: '):
				#Oh YEAH, consistency.
				# Marlin reports an MIN/MAX temp error as "Error: x\n: Extruder switched off. MAXTEMP triggered !\n"
				#	But a bed temp error is reported as "Error: Temperature heated bed switched off. MAXTEMP triggered !!"
				#	So we can have an extra newline in the most common case. Awesome work people.
				if re.match('Error: [0-9]\n', line):
					line = line.rstrip() + self._readline()
				self._errorValue = line
				self._changeState(self.STATE_ERROR)
			if 'T:' in line:
				self._temp = float(re.search("[0-9\.]*", line.split('T:')[1]).group(0))
				if 'B:' in line:
					self._bedTemp = float(re.search("[0-9\.]*", line.split('B:')[1]).group(0))
				self._callback.mcTempUpdate(self._temp, self._bedTemp)
			elif line.strip() != 'ok':
				self._callback.mcMessage(line)

			if self._state == self.STATE_DETECT_BAUDRATE:
				if line == '' or time.time() > timeout:
					if len(self._baudrateDetectList) < 1:
						self._log("No more baudrates to test, and no suitable baudrate found.")
						self.close()
					elif self._baudrateDetectRetry > 0:
						self._baudrateDetectRetry -= 1
						self._serial.write('\n')
						self._sendCommand("M105")
					else:
						baudrate = self._baudrateDetectList.pop(0)
						try:
							self._serial.baudrate = baudrate
							self._serial.timeout = 0.5
							self._log("Trying baudrate: %d" % (baudrate))
							self._baudrateDetectRetry = 5
							timeout = time.time() + 5
							self._serial.write('\n')
							self._sendCommand("M105")
						except:
							self._log("Unexpected error while setting baudrate: %d %s" % (baudrate, getExceptionString()))
				elif 'ok' in line:
					self._serial.timeout = 2
					profile.putPreference('serial_baud_auto', self._serial.baudrate)
					self._changeState(self.STATE_OPERATIONAL)
			elif self._state == self.STATE_CONNECTING:
				if line == '':
					self._sendCommand("M105")
				elif 'ok' in line:
					self._changeState(self.STATE_OPERATIONAL)
				if time.time() > timeout:
					self.close()
			elif self._state == self.STATE_OPERATIONAL:
				#Request the temperature on comm timeout (every 2 seconds) when we are not printing.
				if line == '':
					self._sendCommand("M105")
					tempRequestTimeout = time.time() + 5
			elif self._state == self.STATE_PRINTING:
				if line == '' and time.time() > timeout:
					self._log("Communication timeout during printing, forcing a line")
					line = 'ok'
				#Even when printing request the temperture every 5 seconds.
				if time.time() > tempRequestTimeout:
					self._commandQueue.put("M105")
					tempRequestTimeout = time.time() + 5
				if 'ok' in line:
					timeout = time.time() + 5
					if not self._commandQueue.empty():
						self._sendCommand(self._commandQueue.get())
					else:
						self._sendNext()
				elif "resend" in line.lower() or "rs" in line:
					try:
						self._gcodePos = int(line.replace("N:"," ").replace("N"," ").replace(":"," ").split()[-1])
					except:
						if "rs" in line:
							self._gcodePos = int(line.split()[1])
		self._log("Connection closed, closing down monitor")
	
	def _log(self, message):
		self._callback.mcLog(message)
		try:
			self._logQueue.put(message, False)
		except:
			#If the log queue is full, remove the first message and append the new message again
			self._logQueue.get()
			self._logQueue.put(message, False)

	def _readline(self):
		if self._serial == None:
			return None
		try:
			ret = self._serial.readline()
		except:
			self._log("Unexpected error while reading serial port: %s" % (getExceptionString()))
			self._errorValue = getExceptionString()
			self.close(True)
			return None
		if ret == '':
			#self._log("Recv: TIMEOUT")
			return ''
		self._log("Recv: %s" % (unicode(ret, 'ascii', 'replace').encode('ascii', 'replace').rstrip()))
		return ret
	
	def close(self, isError = False):
		if self._serial != None:
			self._serial.close()
			if isError:
				self._changeState(self.STATE_CLOSED_WITH_ERROR)
			else:
				self._changeState(self.STATE_CLOSED)
		self._serial = None
	
	def __del__(self):
		self.close()
	
	def _sendCommand(self, cmd):
		if self._serial == None:
			return
		self._log('Send: %s' % (cmd))
		try:
			self._serial.write(cmd)
			self._serial.write('\n')
		except:
			self._log("Unexpected error while writing serial port: %s" % (getExceptionString()))
			self._errorValue = getExceptionString()
			self.close(True)
	
	def _sendNext(self):
		if self._gcodePos >= len(self._gcodeList):
			self._changeState(self.STATE_OPERATIONAL)
			return
		line = self._gcodeList[self._gcodePos]
		if type(line) is tuple:
			self._printSection = line[1]
			line = line[0]
		try:
			if line == 'M0' or line == 'M1':
				self.setPause(True)
				line = 'M105'	#Don't send the M0 or M1 to the machine, as M0 and M1 are handled as an LCD menu pause.
			if self._printSection in self._feedRateModifier:
				line = re.sub('F([0-9]*)', lambda m: 'F' + str(int(int(m.group(1)) * self._feedRateModifier[self._printSection])), line)
			if ('G0' in line or 'G1' in line) and 'Z' in line:
				z = float(re.search('Z([0-9\.]*)', line).group(1))
				if self._currentZ != z:
					self._currentZ = z
					self._callback.mcZChange(z)
		except:
			self._log("Unexpected error: %s" % (getExceptionString()))
		checksum = reduce(lambda x,y:x^y, map(ord, "N%d%s" % (self._gcodePos, line)))
		self._sendCommand("N%d%s*%d" % (self._gcodePos, line, checksum))
		self._gcodePos += 1
		self._callback.mcProgress(self._gcodePos)
	
	def sendCommand(self, cmd):
		cmd = cmd.encode('ascii', 'replace')
		if self.isPrinting():
			self._commandQueue.put(cmd)
		elif self.isOperational():
			self._sendCommand(cmd)
	
	def printGCode(self, gcodeList):
		if not self.isOperational() or self.isPrinting():
			return
		self._gcodeList = gcodeList
		self._gcodePos = 0
		self._printSection = 'CUSTOM'
		self._changeState(self.STATE_PRINTING)
		for i in xrange(0, 6):
			self._sendNext()
	
	def cancelPrint(self):
		if self.isOperational():
			self._changeState(self.STATE_OPERATIONAL)
	
	def setPause(self, pause):
		if not pause and self.isPaused():
			self._changeState(self.STATE_PRINTING)
			for i in xrange(0, 6):
				self._sendNext()
		if pause and self.isPrinting():
			self._changeState(self.STATE_PAUSED)
	
	def setFeedrateModifier(self, type, value):
		self._feedRateModifier[type] = value

def getExceptionString():
	locationInfo = traceback.extract_tb(sys.exc_info()[2])[0]
	return "%s: '%s' @ %s:%s:%d" % (str(sys.exc_info()[0].__name__), str(sys.exc_info()[1]), os.path.basename(locationInfo[0]), locationInfo[2], locationInfo[1])

