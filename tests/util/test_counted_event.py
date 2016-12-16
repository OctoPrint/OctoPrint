# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"

import unittest
import time
import threading

from octoprint.util import CountedEvent

class CountedEventTest(unittest.TestCase):

	def test_set_once(self):
		"""The counter should go from 0 to 1."""

		event = CountedEvent()

		self.assertEqual(0, event._counter)
		self.assertFalse(event._event.is_set())

		event.set()

		self.assertEqual(1, event._counter)
		self.assertTrue(event._event.is_set())

	def test_set_more_than_max(self):
		"""The counter should never rise above max."""

		event = CountedEvent(max=1)

		self.assertEqual(0, event._counter)
		self.assertFalse(event._event.is_set())

		event.set()

		self.assertEqual(1, event._counter)
		self.assertTrue(event._event.is_set())

		event.set()

		self.assertEqual(1, event._counter)
		self.assertTrue(event._event.is_set())

	def test_clear_once(self):
		"""The counter should to from 1 to 0."""

		event = CountedEvent(1)

		self.assertEqual(1, event._counter)
		self.assertTrue(event._event.is_set())

		event.clear()

		self.assertEqual(0, event._counter)
		self.assertFalse(event._event.is_set())

	def test_clear_all(self):
		"""The counter should go from 10 to 0."""

		event = CountedEvent(10)

		self.assertEqual(10, event._counter)
		self.assertTrue(event._event.is_set())

		event.clear(completely=True)

		self.assertEqual(0, event._counter)
		self.assertFalse(event._event.is_set())

	def test_clear_more_than_available(self):
		"""The counter should never sink below 0."""

		event = CountedEvent(1)

		self.assertEqual(1, event._counter)
		self.assertTrue(event._event.is_set())

		event.clear()

		self.assertEqual(0, event._counter)
		self.assertFalse(event._event.is_set())

		event.clear()

		self.assertEqual(0, event._counter)
		self.assertFalse(event._event.is_set())

	def test_blocked(self):
		"""Blocked should only be true if the counter is 0."""

		event = CountedEvent(0)

		self.assertTrue(event.blocked())

		event.set()
		self.assertFalse(event.blocked())

		event.clear()
		self.assertTrue(event.blocked())

	def test_wait_immediately(self):
		"""Unblocked wait should immediately return."""

		event = CountedEvent(1)

		start = time.time()
		event.wait(timeout=2)
		duration = time.time() - start

		self.assertLess(duration, 1)

	def test_wait_blocking(self):
		"""Set should immediately have blocked wait return."""

		event = CountedEvent(0)

		def set_event():
			time.sleep(1)
			event.set()

		thread = threading.Thread(target=set_event)
		thread.daemon = True
		thread.start()

		start = time.time()
		event.wait(timeout=2)
		duration = time.time() - start

		self.assertLess(duration, 2)

	def test_wait_timeout(self):
		"""Blocked should only wait until timeout."""

		event = CountedEvent(0)

		start = time.time()
		event.wait(timeout=2)
		duration = time.time() - start

		self.assertGreaterEqual(duration, 2)
		self.assertLess(duration, 3)
