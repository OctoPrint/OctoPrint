from __future__ import absolute_import, division, print_function
import io
from builtins import range

def readHex(filename):
	data = []
	extraAddr = 0
	f = io.open(filename, "r")
	for line in f:
		line = line.strip()
		if line[0] != ':':
			raise Exception("Hex file has a line not starting with ':'")
		recLen = int(line[1:3], 16)
		addr = int(line[3:7], 16) + extraAddr
		recType = int(line[7:9], 16)
		if len(line) != recLen * 2 + 11:
			raise Exception("Error in hex file: " + line)
		checkSum = 0
		for i in range(0, recLen + 5):
			checkSum += int(line[i*2+1:i*2+3], 16)
		checkSum &= 0xFF
		if checkSum != 0:
			raise Exception("Checksum error in hex file: " + line)
		
		if recType == 0:#Data record
			while len(data) < addr + recLen:
				data.append(0)
			for i in range(0, recLen):
				data[addr + i] = int(line[i*2+9:i*2+11], 16)
		elif recType == 1:	#End Of File record
			pass
		elif recType == 2:	#Extended Segment Address Record
			extraAddr = int(line[9:13], 16) * 16
		else:
			print(recType, recLen, addr, checkSum, line)
	f.close()
	return data