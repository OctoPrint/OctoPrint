# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import contextlib
import threading

try:
	import src.octoprint.util.comm.queue
except ImportError:
	import Queue as queue

from octoprint.util import TypedQueue, PrependableQueue, TypeAlreadyInQueue


class CommandQueue(TypedQueue):
	def __init__(self, *args, **kwargs):
		TypedQueue.__init__(self, *args, **kwargs)
		self._unblocked = threading.Event()
		self._unblocked.set()

	def block(self):
		self._unblocked.clear()

	def unblock(self):
		self._unblocked.set()

	@contextlib.contextmanager
	def blocked(self):
		self.block()
		try:
			yield
		finally:
			self.unblock()

	def get(self, *args, **kwargs):
		self._unblocked.wait()
		return TypedQueue.get(self, *args, **kwargs)

	def put(self, *args, **kwargs):
		self._unblocked.wait()
		return TypedQueue.put(self, *args, **kwargs)

	def clear(self):
		cleared = []
		while True:
			try:
				cleared.append(TypedQueue.get(self, False))
				TypedQueue.task_done(self)
			except src.octoprint.util.comm.queue.Empty:
				break
		return cleared


