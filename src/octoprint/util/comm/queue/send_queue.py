# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import contextlib
import threading

try:
	import src.octoprint.util.comm.queue
except ImportError:
	import Queue as queue

from octoprint.util import PrependableQueue, TypeAlreadyInQueue


class SendQueue(PrependableQueue):
	def __init__(self, maxsize=0):
		PrependableQueue.__init__(self, maxsize=maxsize)

		self._unblocked = threading.Event()
		self._unblocked.set()

		self._resend_queue = PrependableQueue()
		self._send_queue = PrependableQueue()
		self._lookup = set()

		self._resend_active = False

	@property
	def resend_active(self):
		return self._resend_active

	@resend_active.setter
	def resend_active(self, resend_active):
		with self.mutex:
			self._resend_active = resend_active

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

	def prepend(self,
				item,
				item_type=None,
				target=None,
				block=True,
				timeout=None):
		self._unblocked.wait()
		PrependableQueue.prepend(self, (item, item_type, target),
								 block=block,
								 timeout=timeout)

	def put(self, item, item_type=None, target=None, block=True, timeout=None):
		self._unblocked.wait()
		PrependableQueue.put(self, (item, item_type, target),
							 block=block,
							 timeout=timeout)

	def get(self, block=True, timeout=None):
		self._unblocked.wait()
		item, _, _ = PrependableQueue.get(self, block=block, timeout=timeout)
		return item

	def clear(self):
		cleared = []
		while True:
			try:
				cleared.append(PrependableQueue.get(self, False))
				PrependableQueue.task_done(self)
			except src.octoprint.util.comm.queue.Empty:
				break
		return cleared

	def _put(self, item):
		_, item_type, target = item
		if item_type is not None:
			if item_type in self._lookup:
				raise TypeAlreadyInQueue(
					item_type, "Type {} is already in queue".format(item_type))
			else:
				self._lookup.add(item_type)

		if target == "resend":
			self._resend_queue.put(item)
		else:
			self._send_queue.put(item)

		pass

	def _prepend(self, item):
		_, item_type, target = item
		if item_type is not None:
			if item_type in self._lookup:
				raise TypeAlreadyInQueue(
					item_type, "Type {} is already in queue".format(item_type))
			else:
				self._lookup.add(item_type)

		if target == "resend":
			self._resend_queue.prepend(item)
		else:
			self._send_queue.prepend(item)

	def _get(self):
		if self.resend_active:
			item = self._resend_queue.get(block=False)
		else:
			try:
				item = self._resend_queue.get(block=False)
			except src.octoprint.util.comm.queue.Empty:
				item = self._send_queue.get(block=False)

		_, item_type, _ = item
		if item_type is not None:
			if item_type in self._lookup:
				self._lookup.remove(item_type)

		return item

	def _qsize(self):
		if self.resend_active:
			return self._resend_queue.qsize()
		else:
			return self._resend_queue.qsize() + self._send_queue.qsize()


class QueueMarker(object):
	def __init__(self, callback):
		self.callback = callback

	def run(self):
		if callable(self.callback):
			try:
				self.callback()
			except Exception:
				_logger.exception(
					"Error while running callback of QueueMarker")


class SendQueueMarker(QueueMarker):
	pass
