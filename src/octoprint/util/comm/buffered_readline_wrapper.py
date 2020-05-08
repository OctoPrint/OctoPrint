# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import wrapt
import serial

class BufferedReadlineWrapper(wrapt.ObjectProxy):
	def __init__(self, obj):
		wrapt.ObjectProxy.__init__(self, obj)
		self._buffered = bytearray()

	def readline(self, terminator=serial.LF):
		termlen = len(terminator)
		data = self._buffered
		timeout = serial.Timeout(self._timeout)

		while True:
			# make sure we always read everything that is waiting
			data += bytearray(self.read(self.in_waiting))

			# check for terminator, if it's there we have found our line
			termpos = data.find(terminator)
			if termpos >= 0:
				# line: everything up to and incl. the terminator
				line = data[:termpos + termlen]
				# buffered: everything after the terminator
				self._buffered = data[termpos + termlen:]
				return bytes(line)

			# check if timeout expired
			if timeout.expired():
				break

			# if we arrive here we so far couldn't read a full line, wait for more data
			c = self.read(1)
			if not c:
				# EOF
				break

			# add to data and loop
			data += bytearray(c)

		self._buffered = data
		return b""
