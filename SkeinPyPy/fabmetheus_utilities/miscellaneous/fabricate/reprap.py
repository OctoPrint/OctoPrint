"""
    pyRepRap is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    pyRepRap is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with pyRepRap.  If not, see <http://www.gnu.org/licenses/>.
"""
"""    
    This is the main user imported module containing all end user functions    
"""

# add commands to switch to gcode mode to allow any script using this library to write gcode too.

try:
	import serial	# Import the pySerial modules.
except:
	print('You do not have pySerial installed, which is needed to control the serial port.')
	print('Information on pySerial is at:\nhttp://pyserial.wiki.sourceforge.net/pySerial')

import snap
import time


printDebug = False	# print debug info

# SNAP Control Commands - Taken from PIC code #

# extruder commands #
CMD_VERSION       =  0
CMD_FORWARD       =  1
CMD_REVERSE       =  2
CMD_SETPOS        =  3
CMD_GETPOS        =  4
CMD_SEEK          =  5
CMD_FREE          =  6
CMD_NOTIFY        =  7
CMD_ISEMPTY       =  8
CMD_SETHEAT       =  9
CMD_GETTEMP       = 10
CMD_SETCOOLER     = 11
CMD_PWMPERIOD     = 50
CMD_PRESCALER     = 51
CMD_SETVREF       = 52
CMD_SETTEMPSCALER = 53
CMD_GETDEBUGINFO  = 54
CMD_GETTEMPINFO   = 55

# stepper commands #
CMD_VERSION		=   0
CMD_FORWARD		=   1
CMD_REVERSE		=   2
CMD_SETPOS		=   3
CMD_GETPOS		=   4
CMD_SEEK		=   5
CMD_FREE		=   6
CMD_NOTIFY		=   7
CMD_SYNC		=   8
CMD_CALIBRATE		=   9
CMD_GETRANGE		=  10
CMD_DDA			=  11
CMD_FORWARD1		=  12
CMD_BACKWARD1		=  13
CMD_SETPOWER		=  14
CMD_GETSENSOR		=  15
CMD_HOMERESET		=  16
CMD_GETMODULETYPE	= 255

# sync modes #
sync_none	= 0	# no sync (default)
sync_seek	= 1	# synchronised seeking
sync_inc	= 2	# inc motor on each pulse
sync_dec	= 3	# dec motor on each pulse

snap.localAddress = 0		# local address of host PC. This will always be 0.
#global serialPort
#serialPort = False

def openSerial( port, rate, tout ):
	global serialPort
	try:
		serialPort = serial.Serial( port, rate, timeout = tout )
		return True
	except 13:
		print "You do not have permissions to use the serial port, try running as root"

def closeSerial():
	serialPort.close()

# Convert two 8 bit bytes to one integer
def bytes2int(LSB, MSB):		
	return int( (0x100 * int(MSB) ) | int(LSB) )

# Convert integer to two 8 bit bytes
def int2bytes(val):
	MSB = int( ( int(val) & 0xFF00) / 0x100 )
	LSB = int( int(val) & 0xFF )
	return LSB, MSB

#def loopTest():
#	p = snap.SNAPPacket( serial, snap.localAddress, snap.localAddress, 0, 1, [] )

# Scan reprap network for devices (incomplete) - this will be used by autoconfig functions when complete
def scanNetwork():
	devices = []
	for remoteAddress in range(1, 10):									# For every address in range. full range will be 255
		print "Trying address " + str(remoteAddress)
		p = snap.SNAPPacket( serialPort, remoteAddress, snap.localAddress, 0, 1, [CMD_GETMODULETYPE] )	# Create snap packet requesting module type
		#p = snap.SNAPPacket( serialPort, remoteAddress, snap.localAddress, 0, 1, [CMD_VERSION] )
		if p.send():											# Send snap packet, if sent ok then await reply
			rep = p.getReply()
			if rep:
				#devices[ rep.dataBytes[1] ] = remoteAddress
				devices.append( { 'address':remoteAddress, 'type':rep.dataBytes[1], 'subType':rep.dataBytes[2] } )	# If device replies then add to device list.
			else:
				"print na"
		else:
			print "scan no ack"
		time.sleep(0.5)
	for d in devices:
		#now get versions
		print "device", d

def getNotification(serialPort):
	return snap.getPacket(serialPort)

class extruderClass:
	def __init__(self):
		self.address = 8
		self.active = False

	def getModuleType(self):	#note: do pics not support this yet? I can't see it in code and get no reply from pic
		if self.active:
			p = snap.SNAPPacket( serialPort, self.address, snap.localAddress, 0, 1, [CMD_GETMODULETYPE] )	# Create SNAP packet requesting module type
			if p.send():
				rep = p.getReply()
				data = checkReplyPacket( rep, 2, CMD_GETMODULETYPE )						# If packet sent ok and was acknoledged then await reply, otherwise return False
				if data:
					return data[1]								# If valid reply is recieved then return it, otherwise return False
		return False

	def getVersion(self):
		if self.active:
			p = snap.SNAPPacket( serialPort, self.address, snap.localAddress, 0, 1, [CMD_VERSION] )
			if p.send():
				rep = p.getReply()
				data = checkReplyPacket( rep, 3, CMD_VERSION )
				if data:
					return data[1], data[2]
		return False

	def setMotor(self, direction, speed):
		if self.active:
			p = snap.SNAPPacket( serialPort, self.address, snap.localAddress, 0, 1, [int(direction), int(speed)] ) ##no command being sent, whats going on?
			if p.send():
				return True
		return False

	def getTemp(self):
		if self.active:		
			p = snap.SNAPPacket( serialPort, self.address, snap.localAddress, 0, 1, [CMD_GETTEMP] )
			if p.send():
				rep = p.getReply()
				data = checkReplyPacket( rep, 2, CMD_GETTEMP )
				if data:
					return data[1]
		return False

	def setVoltateReference(self, val):
		if self.active:
			p = snap.SNAPPacket( serialPort, self.address, snap.localAddress, 0, 1, [CMD_SETVREF, int(val)] )
			if p.send():
				return True
		return False

	def setHeat(self, lowHeat, highHeat, tempTarget, tempMax):
		if self.active:	
			tempTargetMSB, tempTargetLSB = int2bytes( tempTarget )
			tempMaxMSB ,tempMaxLSB = int2bytes( tempMax )
			p = snap.SNAPPacket( serialPort, self.address, snap.localAddress, 0, 1, [CMD_SETHEAT, int(lowHeat), int(highHeat), tempTargetMSB, tempTargetLSB, tempMaxMSB, tempMaxLSB] )	# assumes MSB first (don't know this!)
			if p.send():
				return True
		return False

	def setCooler(self, speed):
		if self.active:
			p = snap.SNAPPacket( serialPort, self.address, snap.localAddress, 0, 1, [CMD_SETCOOLER, int(speed)] )
			if p.send():
				return True
		return False

	def freeMotor(self):
		if self.active:
			p = snap.SNAPPacket( serialPort, self.address, snap.localAddress, 0, 1, [CMD_FREE] )
			if p.send():
				return True
		return False

extruder = extruderClass()


def checkReplyPacket (packet, numExpectedBytes, command):
	if packet:
		if len( packet.dataBytes ) == numExpectedBytes:		# check correct number of data bytes have been recieved
			if packet.dataBytes[0] == command:			# check reply is a reply to sent command
				return packet.dataBytes
	return False
				

class axisClass:
	def __init__(self, address):
		self.address = address
		self.active = False	# when scanning network, set this, then in each func below, check alive before doing anything
		self.limit = 100000	# limit effectively disabled unless set
	#move axis one step forward
	def forward1(self):
		if self.active:
			p = snap.SNAPPacket( serialPort, self.address, snap.localAddress, 0, 1, [CMD_FORWARD1] ) 
			if p.send():
				return True
		return False

	#move axis one step backward
	def backward1(self):
		if self.active:
			p = snap.SNAPPacket( serialPort, self.address, snap.localAddress, 0, 1, [CMD_BACKWARD1] ) 
			if p.send():
				return True
		return False

	#spin axis forward at given speed
	def forward(self, speed):
		if self.active:
			p = snap.SNAPPacket( serialPort, self.address, snap.localAddress, 0, 1, [CMD_FORWARD, int(speed)] ) 
			if p.send():
				return True
		return False

	#spin axis backward at given speed
	def backward(self, speed):
		if self.active:
			p = snap.SNAPPacket( serialPort, self.address, snap.localAddress, 0, 1, [CMD_REVERSE, int(speed)] ) 
			if p.send():
				return True
		return False

	#debug only
	def getSensors(self):
		if self.active:
			p = snap.SNAPPacket( serialPort, self.address, snap.localAddress, 0, 1, [CMD_GETSENSOR] )
			if p.send():
				rep = p.getReply()
				data = checkReplyPacket( rep, 3, CMD_GETSENSOR )		# replace this with a proper object in SNAP module?
				if data:
					print data[1], data[2]
		return False

	#get current axis position
	def getPos(self):
		if self.active:
			p = snap.SNAPPacket( serialPort, self.address, snap.localAddress, 0, 1, [CMD_GETPOS] )
			if p.send():
				rep = p.getReply()
				data = checkReplyPacket( rep, 3, CMD_GETPOS )
				if data:
					pos = bytes2int( data[1], data[2] )
					return pos 						# return value
		return False

	#set current position (set variable not robot position)
	def setPos(self, pos):
		if self.active:
			posMSB ,posLSB = int2bytes( pos )
			p = snap.SNAPPacket( serialPort, self.address, snap.localAddress, 0, 1, [CMD_SETPOS, posMSB, posLSB] )
			if p.send():
				return True
		return False

	#power off coils on stepper
	def free(self):
		if self.active:
			p = snap.SNAPPacket( serialPort, self.address, snap.localAddress, 0, 1, [CMD_FREE] ) 
			if p.send():
				return True
		return False

	#seek to axis location. When waitArrival is True, funtion does not return until seek is compete
	def seek(self, pos, speed, waitArrival = True):
		if self.active and pos <= self.limit:
			posMSB ,posLSB = int2bytes( pos )
			p = snap.SNAPPacket( serialPort, self.address, snap.localAddress, 0, 1, [CMD_SEEK, int(speed), posMSB ,posLSB] ) 
			if p.send():
				if waitArrival:
					if printDebug: print "    wait notify"
					notif = getNotification( serialPort )
					if notif.dataBytes[0] == CMD_SEEK:
						if printDebug: print "    valid notification for seek"
					else:
						return False
					if printDebug: print "    rec notif"
				return True
		return False
	
	#goto 0 position. When waitArrival is True, funtion does not return until reset is compete
	def homeReset(self, speed, waitArrival = True):
		if self.active:
			p = snap.SNAPPacket( serialPort, self.address, snap.localAddress, 0, 1, [CMD_HOMERESET, int(speed)] ) 
			if p.send():
				if waitArrival:
					if printDebug: print "reset wait"
					notif = getNotification( serialPort )
					if notif.dataBytes[0] == CMD_HOMERESET:
						if printDebug: print "    valid notification for reset"
					else:
						return False
					if printDebug: print "reset done"
				return True
		return False

	def setNotify(self):
		#global serialPort
		if self.active:
			p = snap.SNAPPacket( serialPort, self.address, snap.localAddress, 0, 1, [CMD_NOTIFY, snap.localAddress] ) 	# set notifications to be sent to host
			if p.send():
				return True
		return False

	def setSync( self, syncMode ):
		if self.active:
			p = snap.SNAPPacket( serialPort, self.address, snap.localAddress, 0, 1, [CMD_SYNC, int(syncMode)] )
			if p.send():
				return True
		return False

	def DDA( self, speed, seekTo, slaveDelta, waitArrival = True):
		if self.active and seekTo <= self.limit:
			masterPosMSB, masterPosLSB = int2bytes( seekTo )
			slaveDeltaMSB, slaveDeltaLSB = int2bytes( slaveDelta )
			p = snap.SNAPPacket( serialPort, self.address, snap.localAddress, 0, 1, [CMD_DDA, int(speed), masterPosMSB ,masterPosLSB, slaveDeltaMSB, slaveDeltaLSB] ) 	#start sync
			if p.send():
				if waitArrival:
					notif = getNotification( serialPort )
					if notif.dataBytes[0] == CMD_DDA:
						if printDebug: print "    valid notification for DDA"	# todo: add actual enforement on wrong notification
					else:
						return False
				return True
		return False
	
	def setPower( self, power ):
		if self.active:
			p = snap.SNAPPacket( serialPort, self.address, snap.localAddress, 0, 1, [CMD_SETPOWER, int( power * 0.63 )] ) # This is a value from 0 to 63 (6 bits)
			if p.send():
				return True
		return False

class syncAxis:
	def __init__( self, axis, seekTo, delta, direction ):
		self.axis = axis
		self.seekTo = seekTo
		self.delta = delta
		self.direction = direction

		if self.direction > 0:
			self.syncMode = sync_inc
		else:
			self.syncMode = sync_dec


class cartesianClass:
	def __init__(self):
		# initiate axies with addresses
		self.x = axisClass(2)
		self.y = axisClass(3)
		self.z = axisClass(4)

	# goto home position (all axies)
	def homeReset(self, speed, waitArrival = True):
		if self.x.homeReset( speed, waitArrival ):		#setting these to true breaks waitArrival convention. need to rework waitArrival and possibly have each axis storing it's arrival flag and pos as variables?
			print "X Reset"		
		if self.y.homeReset( speed, waitArrival ):
			print "Y Reset"
		if self.z.homeReset( speed, waitArrival ):
			print "Z Reset"
		# add a way to collect all three notifications (in whatever order) then check they are all there. this will allow symultanious axis movement and use of waitArrival

	# seek to location (all axies). When waitArrival is True, funtion does not return until all seeks are compete
	# seek will automatically use syncSeek when it is required. Always use the seek function
	def seek(self, pos, speed, waitArrival = True):
		curX, curY, curZ = self.x.getPos(), self.y.getPos(), self.z.getPos()
		x, y, z = pos
		if x <= self.x.limit and y <= self.y.limit and z <= self.z.limit:
			if printDebug: print "seek from [", curX, curY, curZ, "] to [", x, y, z, "]"
			if x == curX or y == curY:
				if printDebug: print "    standard seek"
				self.x.seek( x, speed, True )			#setting these to true breaks waitArrival convention. need to rework waitArrival and possibly have each axis storing it's arrival flag and pos as variables?
				self.y.seek( y, speed, True )
			else:
				if printDebug: print "    sync seek"
				self.syncSeek( pos, speed, waitArrival )
			if z != curZ:
				self.z.seek( z, speed, True )
		else:
			print "Trying to print outside of limit, aborting seek"
	
	# perform syncronised x/y movement. This is called by seek when needed.
	def syncSeek(self, pos, speed, waitArrival = True):
		curX, curY = self.x.getPos(), self.y.getPos()
		newX, newY, nullZ = pos
		deltaX = abs( curX - newX )		# calc delta movements
		deltaY = abs( curY - newY )
		directionX = ( curX - newX ) / -deltaX	# gives direction -1 or 1
		directionY = ( curY - newY ) / -deltaY	
		if printDebug: print "    dx", deltaX, "dy", deltaY, "dirX", directionX, "dirY", directionY
		if printDebug: print "    using x master"

		master = syncAxis( self.x, newX, deltaX, directionX )	# create two swapable data structures, set x as master, y as slave
		slave = syncAxis( self.y, newY, deltaY, directionY )
		
		if slave.delta > master.delta:		# if y has the greater movement then make y master
			slave, master = master, slave
			if printDebug: print "    switching to y master"
		if printDebug: print "    masterPos", master.seekTo, "slaveDelta", slave.delta
		slave.axis.setSync( slave.syncMode )
		master.axis.DDA( speed, master.seekTo, slave.delta, True )
		time.sleep(0.1)
		slave.axis.setSync( sync_none )
		if printDebug: print "    sync seek complete"
	
	# get current position of all three axies	
	def getPos(self):
		return self.x.getPos(), self.y.getPos(), self.z.getPos()
	
	# stop all motors
	def stop(self):
		self.x.forward( 0 )
		self.y.forward( 0 )
		self.z.forward( 0 )

	# free all motors (no current on coils)
	def free(self):
		self.x.free()
		self.y.free()
		self.z.free()
	def setPower(self, power):
		self.x.setPower( power )
		self.y.setPower( power )
		self.z.setPower( power )
	#def lockout():
	#keep sending power down commands to all board every second

	
cartesian = cartesianClass()

#wait on serial only when after somthing? or do pics send messages without pc request?






