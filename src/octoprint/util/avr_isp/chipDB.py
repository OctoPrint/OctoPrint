# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

avrChipDB = {
	'ATMega1280': {
		'signature': [0x1E, 0x97, 0x03],
		'pageSize': 128,
		'pageCount': 512,
	},
	'ATMega2560': {
		'signature': [0x1E, 0x98, 0x01],
		'pageSize': 128,
		'pageCount': 1024,
	},
}

def getChipFromDB(sig):
	for chip in avrChipDB.values():
		if chip['signature'] == sig:
			return chip
	return None

