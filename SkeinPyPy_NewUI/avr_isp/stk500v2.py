import os, struct, sys, time

from serial import Serial

import ispBase, intelHex

class Stk500v2(ispBase.IspBase):
	def __init__(self):
		self.serial = None
		self.seq = 1
		self.lastAddr = -1
	
	def connect(self, port = 'COM3', speed = 115200):
		if self.serial != None:
			self.serial.close()
		self.serial = Serial(port, speed, timeout=5)
		self.seq = 1
		
		#Reset the controller
		self.serial.setDTR(1)
		self.serial.setDTR(0)
		time.sleep(0.2)
		
		self.sendMessage([1])
		if self.sendMessage([0x10, 0xc8, 0x64, 0x19, 0x20, 0x00, 0x53, 0x03, 0xac, 0x53, 0x00, 0x00]) != [0x10, 0x00]:
			raise ispBase.IspError("Failed to enter programming mode")
	
	def sendISP(self, data):
		recv = self.sendMessage([0x1D, 4, 4, 0, data[0], data[1], data[2], data[3]])
		return recv[2:6]
	
	def writeFlash(self, flashData):
		#Set load addr to 0 (with more then 64k load)
		self.sendMessage([0x06, 0x80, 0x00, 0x00, 0x00])
		
		loadCount = (len(flashData) + 0xFF) / 0x100
		for i in xrange(0, loadCount):
			recv = self.sendMessage([0x13, 0x01, 0x00, 0xc1, 0x0a, 0x40, 0x4c, 0x20, 0x00, 0x00] + flashData[(i * 0x100):(i * 0x100 + 0x100)])
			print "#%i#%i#" % (i + 1, loadCount)
	
	def verifyFlash(self, flashData):
		#Set load addr to 0 (with more then 64k load)
		self.sendMessage([0x06, 0x80, 0x00, 0x00, 0x00])
		
		loadCount = (len(flashData) + 0xFF) / 0x100
		for i in xrange(0, loadCount):
			recv = self.sendMessage([0x14, 0x01, 0x00, 0x20])[2:0x102]
			print "#%i#%i#" % (i + 1, loadCount)
			for j in xrange(0, 0x100):
				if i * 0x100 + j < len(flashData) and flashData[i * 0x100 + j] != recv[j]:
					raise ispBase.IspError('Verify error at: 0x%x' % (i * 0x100 + j))

	def sendMessage(self, data):
		message = struct.pack(">BBHB", 0x1B, self.seq, len(data), 0x0E)
		for c in data:
			message += struct.pack(">B", c)
		checksum = 0
		for c in message:
			checksum ^= ord(c)
		message += struct.pack(">B", checksum)
		self.serial.write(message)
		self.serial.flush()
		self.seq = (self.seq + 1) & 0xFF
		return self.recvMessage()
	
	def recvMessage(self):
		state = 'Start'
		checksum = 0
		while True:
			s = self.serial.read()
			if len(s) < 1:
				raise ispBase.IspError("Timeout")
			b = struct.unpack(">B", s)[0]
			checksum ^= b
			#print hex(b)
			if state == 'Start':
				if b == 0x1B:
					state = 'GetSeq'
					checksum = 0x1B
			elif state == 'GetSeq':
				state = 'MsgSize1'
			elif state == 'MsgSize1':
				msgSize = b << 8
				state = 'MsgSize2'
			elif state == 'MsgSize2':
				msgSize |= b
				state = 'Token'
			elif state == 'Token':
				if b != 0x0E:
					state = 'Start'
				else:
					state = 'Data'
					data = []
			elif state == 'Data':
				data.append(b)
				if len(data) == msgSize:
					state = 'Checksum'
			elif state == 'Checksum':
				if checksum != 0:
					state = 'Start'
				else:
					return data


def main():
	programmer = Stk500v2()
	programmer.connect()
	programmer.programChip(intelHex.readHex("cfg_4f55234def059.hex"))
	sys.exit(1)

if __name__ == '__main__':
	main()
