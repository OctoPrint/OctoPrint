"""
    pyRepRap is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 2 of the License, or
    (at your option) any later version.

    pyRepRap is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with pyRepRap.  If not, see <http://www.gnu.org/licenses/>.
"""

try:
	import serial	# Import the pySerial modules.
except:
	print('You do not have pySerial installed, which is needed to control the serial port.')
	print('Information on pySerial is at:\nhttp://pyserial.wiki.sourceforge.net/pySerial')


offset_payload = 5
offset_hdb1 = 2

#ackTimeout = 0.3	# unused
messageTimeout = 0.3	# used for ack also (possible to split?)
#messageTimeout = 2	# used for ack also (possible to split?)
retries = 3		# number of packet send retries allowed (for whatever failed reason

printOutgoingPackets = False
printIncomingPackets = False
printFailedPackets = False

#this is done again in full decode, but needed here so num bytes to expect is known.
def getPacketLen(buffer):	
	l = breakHDB1( buffer[offset_hdb1] )
	#l = buffer[offset_hdb1] & 0x0f;
	#if (l & 8) != 0:
	#	return 8 << (l & 7)
	return l

#PCaddress = 0

#wait for a packet on serial - note : packets addressed to something other than 0 get recieved if you try sending to a non existant pcb (looped round). should we delete or pass on? (they cause errors right now in getpacket)
def getPacket(ser):
	buffer = []
	while 1:
		byte = ser.read()							# read serial byte.
		if len(byte) > 0:
			buffer.append( ord (byte) )					# add serial byte to buffer.
		else:
			print "Error: Serial timeout"		#clear buffer on timeout?		
			return False							# timeout has occured.
		#TODO - add check for sync on first byte
		if len(buffer) > 4:							# one packet length is recieved (HDB1?).
			expectedLength = getPacketLen(buffer) + offset_payload + 1;	# read num data bytes.
			if len(buffer) >= expectedLength:				# check we have enough data, otherwise continue reading from serial.
				#print "############PR#############"
				p = SNAPPacket( ser, 0, 0, 0, 0, [] )			# create empty packet
				for b in buffer:
					p.addByte(b)					# add byte to packet
				p.decode()
				if printIncomingPackets:		
					print "###INCOMING PACKET##"
					p.printPacket()
					print "###END INCOMING PACKET##"
				return p						# return recieved packet
				#need to check if packet is for pc (0), if not send on.

#class for checksum calculator
class SNAPChecksum:
	def __init__(self):
		self.crc = 0
	def addData(self, data): 
		#byte i = (byte)(data ^ self.crc)
		i = data ^ self.crc
		self.crc = 0
		if((i & 1) != 0):
			self.crc ^= 0x5e
		if((i & 2) != 0):
			self.crc ^= 0xbc
		if((i & 4) != 0):
			self.crc ^= 0x61
		if((i & 8) != 0):
			self.crc ^= 0xc2
		if((i & 0x10) != 0):
			self.crc ^= 0x9d
		if((i & 0x20) != 0):
			self.crc ^= 0x23
		if((i & 0x40) != 0):
			self.crc ^= 0x46
		if((i & 0x80) != 0):
			self.crc ^= 0x8c
		return data
	def getResult(self):
		return self.crc


#class for snap packet	
class SNAPPacket:
	def __init__(self, serial, DAB, SAB, ACK, NAK, dataBytes):	#specify serial here, not reason not to
		self.SYNC = 0x54
		self.DAB = DAB
		self.SAB = SAB
		self.ACK = ACK
		self.NAK = NAK
		self.dataBytes = dataBytes
		
		self.bytes = []
		self.leftoverBytes = []
		self.encoded = False
		self.decoded = False
		self.valid = False
		self.serial = serial
	
	#manually add a byte to packet (unused)
	def addByte(self, byte):
		self.bytes.append(byte)

	#convert individual packet properties into table self.bytes (raw data packet)
	def encode(self):
		self.NDB = len(self.dataBytes)
		self.bytes = []
		self.bytes.insert( 0, 0xFF & self.SYNC )			#SYNC
		self.bytes.insert( 1, 0xFF & makeHDB2(self.ACK, self.NAK) )	#HDB2
		self.bytes.insert( 2, 0xFF & makeHDB1(self.NDB) )			#HDB1
		self.bytes.insert( 3, 0xFF & self.DAB )				#DAB
		self.bytes.insert( 4, 0xFF & self.SAB )				#SAB
		
		for d in self.dataBytes:	
			self.bytes.append( 0xFF & d )				#DATA

		checksum = SNAPChecksum()
		for d in self.bytes[1:]:
			checksum.addData(d)
		self.CRC = checksum.getResult()
		self.bytes.append( self.CRC )					#CRC
		#print self.bytes
		self.encoded = True

	#convert table self.bytes (raw data packet) into individual packet properties
	def decode(self):					
		self.SYNC = self.bytes[0]
		self.HDB2 = self.bytes[1]
		self.HDB1 = self.bytes[2]
		self.DAB = self.bytes[3]
		self.SAB = self.bytes[4]
		self.NDB = breakHDB1(self.HDB1)

		self.dataBytes = []
		for d in self.bytes[5:5 + self.NDB]:
			self.dataBytes.append(d)
		
		#print self.bytes, self.NDB
		self.CRC = self.bytes[5 + self.NDB::6 + self.NDB][0]
		numLeftoverBytes = len(self.bytes) - 6 - self.NDB
		self.leftoverBytes = self.bytes[6 + self.NDB:len(self.bytes)]
		if numLeftoverBytes > 0:
			print "leftover bytes", numLeftoverBytes, self.leftoverBytes
		self.ACK, self.NAK = breakHDB2(self.HDB2)
		self.bytes = self.bytes[:6 + self.NDB]
		#print "newb", self.bytes
		self.decoded = True

	#calculate checksum, compare to value in recieved packet
	def check(self):					
		newChecksum = SNAPChecksum()
		for d in self.bytes[1:-1]:
			newChecksum.addData(d)
		testCRC = newChecksum.getResult()
		if testCRC == self.CRC:
			self.valid = True
			return True
		else:
			self.valid = False
			return False, testCRC, self.CRC

	#actual sending of data packet (self.bytes)
	def sendBytes(self):
		if self.encoded == True:
			for d in self.bytes:
				#print "sending", d, chr(d)
				self.serial.write(chr(d))	
		else:
			print "Error: packet not encoded"
	
	#user send function, sends packet and awaits and checks acknoledgement.
	def send(self):
		self.encode()
		retriesLeft = retries
		while retriesLeft > 0:				# try sending define number of times only
			self.sendBytes()			# send data
			if printOutgoingPackets:
				print "###OUTGOING PACKET##"
				self.decode() #remove need for this (tidy up)
				self.printPacket()
				print "###END OUTGOING PACKET##"			
				
			ack = getPacket(self.serial)		# await ack, returns false on timout
			if ack:					
				ack.decode()
				if ack.ACK == 1 and ack.SAB == self.DAB:		# check that packet is an acknoledgement and that it is from the device we just messaged.
					return True
				#do some check on ack - TODO
				if printFailedPackets:
					print "###FAILED OUTGOING PACKET##"
					self.decode() #remove need for this (tidy up)
					self.printPacket()
					print "###END FAILED OUTGOING PACKET##"
			else:	
				print "Error: ACK not recieved"
				if printFailedPackets:
					print "###FAILED OUTGOING PACKET##"
					self.decode() #remove need for this (tidy up)
					self.printPacket()
					print "###END FAILED OUTGOING PACKET##"
				
			retriesLeft = retriesLeft - 1
		print "Error: Packet send FAILED (or reply)"
		return False
		
	# get a modules reply packet (not ack)
	def getReply(self):
		rep = getPacket(self.serial)
		return rep
	
	#print packet info to console
	def printPacket(self):
		if self.decoded == True:
			print self.bytes
			print "SNAP Packet:"
			if self.SYNC == 0x54:
				print "...Sync OK"
			else:
				print "...Sync Error"
			print "...Check: ", self.check()		
			print "...DATA", self.dataBytes
			print "...CRC", self.CRC
			print "...SAB", self.SAB
			print "...DAB", self.DAB
			print "...HDB1", self.HDB1, ":"	
			print "...........NDB", self.NDB	
			print "...HDB2", self.HDB2, ":"
			print "...........ACK", self.ACK
			print "...........NAK", self.NAK
			print "END OF PACKET"
		else:
			print "Error: packet not decoded"	



#create HDB2
def makeHDB2(ACK, NAK):
	SAB = 1			# Length of the Source Address Bytes, in Binary. RepRap currently only accepts source addresses of 1 byte length
	DAB = 1			# Length of the Destination Address Bytes, in Binary. RepRap currently only accepts destinations of 1 byte length
	PFB = 0			# Length of Protocol Flag Bytes. RepRap does not accept any protocol flag bytes, so this must be set to 00
	HDB2val = ((DAB & 0x3) * pow(2,6)) | ((SAB & 0x3) * pow(2,4)) | ((PFB & 0x3) * pow(2,2)) | ((ACK & 0x1) * pow(2,1)) | (NAK & 0x1)
	#print "HDB2 = '" + str(HDB2val) + "'"
	return HDB2val

def breakHDB2(HDB2):
	ACK = (HDB2 & 0x2) / pow(2,1)
	NAK = (HDB2 & 0x1)
	return ACK, NAK

#create HDB1
def makeHDB1(NDB):
	CMD = 0			# Command Mode Bit. Not implemented by RepRap and should be set to 0
	EMD = 0x3		# Currently RepRap only implements 8-bit self.crc. this should be set to 011
	HDB1val = ((CMD & 0x1) * pow(2,7)) | ((EMD & 0x7) * pow(2,4)) | (0xF & NDB)
	#print "HDB1 = '" + str(HDB1val) + "'"
	return HDB1val

def breakHDB1(HDB1):
	NDB = HDB1 & 0xF
	return NDB

	

