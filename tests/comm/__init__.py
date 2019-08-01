# coding=utf-8
from __future__ import absolute_import, unicode_literals, print_function, \
	division

"""
Unit tests for ``octoprint.comm.protocol``.
"""

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2019 The OctoPrint Project - Released under terms of the AGPLv3 License"


import time

from octoprint.comm.transport import Transport

from octoprint.util import monotonic_time, to_bytes

class TestTransport(Transport):

	def __init__(self, *args, **kwargs):
		super(TestTransport, self).__init__(*args, **kwargs)
		self.outgoing = bytearray()
		self.incoming = []

	@property
	def in_waiting(self):
		return len(self.outgoing)

	def do_read(self, size=None, timeout=None):
		if size is None:
			result = bytes(self.outgoing)

		else:
			if timeout is None:
				while self.in_waiting < size:
					time.sleep(0.1)
			else:
				start = time.time()
				while self.in_waiting < size and time.time() - start < timeout:
					time.sleep(0.1)

			if size < self.in_waiting:
				result = bytes(self.outgoing[0:size - 1])
				del self.outgoing[0:size - 1]
			else:
				result = bytes(self.outgoing)
				del self.outgoing[:]

		return result

	def do_write(self, data):
		self.incoming.append(data)

	def send(self, data):
		self.outgoing += bytearray(to_bytes(data))

	def expect(self, expected, timeout=10.0):
		if timeout is not None:
			stop = monotonic_time() + timeout
			timed_out = lambda: monotonic_time() >= stop
		else:
			timed_out = lambda: False

		while len(self.incoming) == 0 and not timed_out():
			time.sleep(0.1)

		try:
			actual = self.incoming.pop(0)
		except IndexError:
			raise ExpectTimeout()

		if callable(expected):
			expected = expected()

		if expected != actual:
			raise AssertionError("Expected {!r}, got {!r}".format(expected, actual))

		return actual

	def expect_and_send(self, expected, data, timeout=10.0):
		self.expect(expected, timeout=timeout)
		self.send(data)

class ExpectTimeout(Exception):
	pass
