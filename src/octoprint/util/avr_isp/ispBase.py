# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import os, struct, sys, time

from serial import Serial

from . import chipDB

class IspBase():
	def programChip(self, flashData):
		self.curExtAddr = -1
		self.chip = chipDB.getChipFromDB(self.getSignature())
		if not self.chip:
			raise IspError("Chip with signature: " + str(self.getSignature()) + "not found")
		self.chipErase()
		
		print("Flashing %i bytes" % len(flashData))
		self.writeFlash(flashData)
		print("Verifying %i bytes" % len(flashData))
		self.verifyFlash(flashData)

	#low level ISP commands
	def getSignature(self):
		sig = []
		sig.append(self.sendISP([0x30, 0x00, 0x00, 0x00])[3])
		sig.append(self.sendISP([0x30, 0x00, 0x01, 0x00])[3])
		sig.append(self.sendISP([0x30, 0x00, 0x02, 0x00])[3])
		return sig
	
	def chipErase(self):
		self.sendISP([0xAC, 0x80, 0x00, 0x00])

class IspError(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)
